"""Pipeline Ops Orchestrator — built with Strands Agents SDK.

Communicates with specialist agents using two protocols:
- HTTP protocol: Pipeline Monitor (LangChain) and Data Quality (LangChain)
- A2A protocol: Schema Manager (Strands)

OAuth tokens for calling specialists are refreshed automatically.
"""

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import os
import json
import time
import asyncio
import concurrent.futures
import logging
import httpx
from typing import Optional
from uuid import uuid4
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import (
    Message as A2AMessage, Part as A2APart, TextPart as A2ATextPart, Role as A2ARole
)

logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

# Agent cache: keyed by session_id/actor_id, reused across turns within a session
_agent_cache: dict[str, Agent] = {}
_MAX_CACHE_SIZE = 100

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
MEMORY_ID = os.environ.get("BEDROCK_AGENTCORE_MEMORY_ID")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# Specialist runtime URLs — required at startup
PIPELINE_MONITOR_URL = os.environ["PIPELINE_MONITOR_URL"]
DATA_QUALITY_URL = os.environ["DATA_QUALITY_URL"]
SCHEMA_MANAGER_URL = os.environ["SCHEMA_MANAGER_URL"]


# ---------------------------------------------------------------------------
# OAuth token provider
# ---------------------------------------------------------------------------

class OAuthTokenProvider:
    """Fetches and caches OAuth tokens via client_credentials flow."""

    def __init__(self, token_url: str, client_id: str, client_secret: str, scopes: str = ""):
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._scopes = scopes
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0

    def _token_data(self) -> dict:
        return {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": self._scopes,
        }

    def get_token(self) -> str:
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
        resp = httpx.post(self._token_url, data=self._token_data(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600) - 60
        return self._access_token

    async def get_token_async(self) -> str:
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self._token_url, data=self._token_data())
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            self._token_expiry = time.time() + data.get("expires_in", 3600) - 60
            return self._access_token


oauth = OAuthTokenProvider(
    token_url=os.environ.get("TOKEN_ENDPOINT", ""),
    client_id=os.environ.get("CLIENT_ID", ""),
    client_secret=os.environ.get("CLIENT_SECRET", ""),
    scopes=os.environ.get("OAUTH_SCOPE", "pipeline-ops/access"),
)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the Pipeline Ops Orchestrator. You coordinate specialist agents to
diagnose and resolve data pipeline issues. You have three specialists:

1. **Pipeline Monitor** — checks pipeline status, reads logs, identifies failures
2. **Data Quality Analyst** — runs quality checks, traces lineage, assesses impact
3. **Schema Manager** — looks up table schemas, finds tables, checks metadata

When a user reports a pipeline issue:
1. Ask the Pipeline Monitor to investigate the failure
2. Ask the Schema Manager to check if the source schema changed
3. Ask the Data Quality Analyst to check upstream data quality
4. Synthesize findings into a clear diagnosis with recommended actions

Always delegate to the right specialist. Do not guess — use the tools."""


# ---------------------------------------------------------------------------
# Specialist callers
# ---------------------------------------------------------------------------

def _call_http_specialist(url: str, prompt: str) -> str:
    """Call an HTTP specialist agent with a Bearer token."""
    try:
        token = oauth.get_token()
        resp = httpx.post(
            url,
            json={"prompt": prompt},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()
        response = result.get("response", json.dumps(result))
        return response.strip() or "Specialist returned an empty response."
    except httpx.HTTPStatusError as e:
        return f"Specialist HTTP error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error calling specialist: {e}"


async def _call_a2a_specialist(base_url: str, prompt: str) -> str:
    """Call an A2A specialist agent with a Bearer token."""
    token = await oauth.get_token_async()
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": str(uuid4()),
    }

    async with httpx.AsyncClient(timeout=300, headers=headers) as client:
        resolver = A2ACardResolver(httpx_client=client, base_url=base_url)
        agent_card = await resolver.get_agent_card()

        a2a_client = ClientFactory(ClientConfig(httpx_client=client, streaming=False)).create(agent_card)

        msg = A2AMessage(
            kind="message",
            role=A2ARole.user,
            parts=[A2APart(root=A2ATextPart(kind="text", text=prompt))],
            messageId=uuid4().hex,
        )

        async for event in a2a_client.send_message(msg):
            if isinstance(event, A2AMessage):
                for part in event.parts or []:
                    text = (
                        getattr(getattr(part, "root", None), "text", None)
                        or getattr(part, "text", None)
                        or ""
                    ).strip()
                    if text:
                        return text
                fallback = str(event).strip()
                return fallback or "Specialist returned an empty message."
            elif isinstance(event, tuple) and len(event) == 2:
                task, _ = event
                for artifact in getattr(task, "artifacts", None) or []:
                    for part in artifact.parts or []:
                        text = getattr(getattr(part, "root", None), "text", "").strip()
                        if text:
                            return text
                fallback = str(task).strip()
                return fallback or "Specialist returned an empty task result."

    return "No response from specialist."


def _call_a2a_sync(url: str, prompt: str) -> str:
    """Run the async A2A call in a dedicated thread to avoid event-loop conflicts."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, _call_a2a_specialist(url, prompt)).result()


# ---------------------------------------------------------------------------
# Strands tools
# ---------------------------------------------------------------------------

@tool
def ask_pipeline_monitor(question: str) -> str:
    """Ask the Pipeline Monitor to investigate pipeline status, failures, and logs."""
    return _call_http_specialist(PIPELINE_MONITOR_URL, question)


@tool
def ask_data_quality_analyst(question: str) -> str:
    """Ask the Data Quality Analyst to check data quality, run validations, and trace lineage."""
    return _call_http_specialist(DATA_QUALITY_URL, question)


@tool
def ask_schema_manager(question: str) -> str:
    """Ask the Schema Manager to look up table schemas, search for tables, and check metadata."""
    return _call_a2a_sync(SCHEMA_MANAGER_URL, question)


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

def get_memory_session_manager(session_id: str, actor_id: str) -> Optional[AgentCoreMemorySessionManager]:
    """Return a session manager if BEDROCK_AGENTCORE_MEMORY_ID is configured."""
    if not MEMORY_ID:
        return None

    retrieval_config = {
        f"/summaries/{actor_id}/{session_id}": RetrievalConfig(top_k=3, relevance_score=0.5),
        f"/users/{actor_id}/facts": RetrievalConfig(top_k=3, relevance_score=0.5),
    }

    return AgentCoreMemorySessionManager(
        AgentCoreMemoryConfig(
            memory_id=MEMORY_ID,
            session_id=session_id,
            actor_id=actor_id,
            retrieval_config=retrieval_config,
        ),
        REGION,
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

@app.entrypoint
def invoke(payload: dict, context=None) -> dict:
    """AgentCore Runtime invoke endpoint."""
    session_id = getattr(context, "session_id", None) or f"local-{os.urandom(16).hex()}"
    actor_id = getattr(context, "user_id", None) or payload.get("user_id", "default-user")
    prompt = payload.get("prompt", "")

    if not prompt.strip():
        return {"response": "No prompt provided."}

    cache_key = f"{session_id}/{actor_id}"

    # Evict oldest entry if cache is full
    if cache_key not in _agent_cache and len(_agent_cache) >= _MAX_CACHE_SIZE:
        oldest = next(iter(_agent_cache))
        del _agent_cache[oldest]
        logger.warning("Agent cache full, evicted session: %s", oldest)

    if cache_key not in _agent_cache:
        session_manager = get_memory_session_manager(session_id, actor_id)
        _agent_cache[cache_key] = Agent(
            model=MODEL_ID,
            system_prompt=SYSTEM_PROMPT,
            tools=[ask_pipeline_monitor, ask_data_quality_analyst, ask_schema_manager],
            session_manager=session_manager,
        )

    result = _agent_cache[cache_key](prompt)
    return {"response": result.message}


if __name__ == "__main__":
    app.run()
