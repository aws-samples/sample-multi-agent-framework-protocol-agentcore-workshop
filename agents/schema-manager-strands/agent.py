"""Schema Manager A2A Server — built with Strands Agents SDK.

Uses A2A protocol (JSON-RPC on port 9000) for AgentCore Runtime.
Connects to the AgentCore Gateway via MCP for tool discovery.
OAuth tokens are refreshed automatically.
"""

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import os
import json
import time
import httpx
from functools import partial
from strands import Agent
from strands.tools.mcp import MCPClient
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from bedrock_agentcore.runtime import serve_a2a
from mcp.client.streamable_http import streamablehttp_client

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")

GATEWAY_URL = os.environ.get("GATEWAY_MCP_URL")
if not GATEWAY_URL:
    raise RuntimeError("GATEWAY_MCP_URL environment variable is required")

SYSTEM_PROMPT = """You are a Schema Manager specialist. You help users understand table
structures, find tables, and investigate schema changes. Be precise about column names,
types, and nullable constraints."""


class OAuthTokenProvider:
    def __init__(self, token_url, client_id, client_secret, scopes=""):
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._scopes = scopes
        self._access_token = None
        self._token_expiry = 0

    def get_token(self) -> str:
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
        resp = httpx.post(self._token_url, data={
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": self._scopes,
        })
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


def gateway_transport():
    """Create MCP transport to the Gateway with OAuth token."""
    token = oauth.get_token()
    return streamablehttp_client(
        url=GATEWAY_URL,
        headers={"Authorization": f"Bearer {token}"},
    )


# Create the Strands agent with MCP tools from the Gateway
gateway_client = MCPClient(gateway_transport)

agent = Agent(
    model=MODEL_ID,
    system_prompt=SYSTEM_PROMPT,
    tools=[gateway_client]
)

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(agent, enable_a2a_compliant_streaming=True))
