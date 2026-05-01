"""Pipeline Monitor Agent — built with LangChain/LangGraph, using Bedrock.

Connects to the AgentCore Gateway via MCP streamable-HTTP transport.
Tools are discovered dynamically. OAuth tokens refresh automatically.
"""

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import os
import json
import time
import asyncio
import logging
import httpx
from langchain_aws import ChatBedrock
from langchain.agents import create_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Configure AWS OpenTelemetry to emit spans to CloudWatch aws/spans
try:
    from aws_opentelemetry_distro import configure_aws_telemetry
    from opentelemetry.instrumentation.langchain import LangchainInstrumentor
    configure_aws_telemetry()
    LangchainInstrumentor().instrument()
except Exception:
    pass  # Observability is optional — agent still works without it

logger = logging.getLogger(__name__)

GATEWAY_URL = os.environ.get("GATEWAY_MCP_URL")
if not GATEWAY_URL:
    raise RuntimeError("GATEWAY_MCP_URL environment variable is required")

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")

SYSTEM_PROMPT = """You are a Pipeline Monitor specialist. You diagnose data pipeline failures
by checking run history, reading logs, and identifying root causes. When investigating:
1. Check the pipeline status and recent runs
2. Read the error logs for the failed run
3. Identify the root cause from the error messages
4. Suggest a fix and whether a retry would help
Be precise and technical. Reference specific error messages and timestamps."""

app = BedrockAgentCoreApp()


class OAuthTokenProvider:
    """Fetches and caches an OAuth Bearer token via client credentials flow."""

    def __init__(self, token_url: str, client_id: str, client_secret: str, scopes: str = ""):
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._scopes = scopes
        self._access_token: str | None = None
        self._token_expiry: float = 0

    async def get_token(self) -> str:
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": self._scopes,
                },
            )
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data["access_token"]
            self._token_expiry = time.time() + token_data.get("expires_in", 3600) - 60
            return self._access_token


oauth = OAuthTokenProvider(
    token_url=os.environ.get("TOKEN_ENDPOINT", ""),
    client_id=os.environ.get("CLIENT_ID", ""),
    client_secret=os.environ.get("CLIENT_SECRET", ""),
    scopes=os.environ.get("OAUTH_SCOPE", "pipeline-ops/access"),
)


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime handler."""
    # Note: prompt is passed from authenticated callers via AgentCore Runtime.
    # Input validation is handled at the infrastructure level by OAuth2 auth.
    prompt = payload.get("prompt", "")
    llm = ChatBedrock(model_id=MODEL_ID, region_name=os.environ.get("AWS_REGION", "us-east-1"))

    async def run_agent():
        token = await oauth.get_token()
        async with streamablehttp_client(
            url=GATEWAY_URL,
            headers={"Authorization": f"Bearer {token}"},
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
                agent = create_agent(llm, tools, system_prompt=SYSTEM_PROMPT)
                result = await agent.ainvoke(
                    {"messages": [{"role": "user", "content": prompt}]}
                )
                return result

    result = asyncio.run(run_agent())
    return {"response": result["messages"][-1].content}


if __name__ == "__main__":
    app.run()
