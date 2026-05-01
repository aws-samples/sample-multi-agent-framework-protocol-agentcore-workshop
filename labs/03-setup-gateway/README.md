# Lab 3: Set Up the AgentCore Gateway

Unify all three MCP servers behind a single Gateway URL.

## What is AgentCore Gateway?

**AgentCore Gateway** is a managed API layer that unifies multiple MCP servers (or other backends) behind a single URL. Instead of configuring every agent and client with separate endpoints for each tool server, the Gateway exposes all tools through one endpoint. It handles request routing to the correct backend, manages outbound authentication to each runtime, and is the enforcement point for Cedar authorization policies. Clients authenticate once with the Gateway; the Gateway authenticates with each backend on their behalf.

## What you'll learn

- How AgentCore Gateway routes tool calls to the right backend
- Inbound vs outbound authentication
- How to add targets and credentials

## Step 1: Create the Gateway

The Gateway uses the same Cognito pool from Lab 2 for inbound auth:

```bash
agentcore add gateway \
  --name pipeline-ops-gateway \
  --authorizer-type CUSTOM_JWT \
  --discovery-url "$DISCOVERY_URL" \
  --allowed-clients "$CLIENT_ID"
```

Deploy:

```bash
agentcore deploy -y
```

Verify:

```bash
agentcore status --type gateway
```

The gateway show show `Deployed`

The specialists need the Gateway URL to call MCP tools. Get it from Lab 3:

**Note:** Please note down the Gateway Id. It is required to construct the Gateway MCP URL.

Save the Gateway URL:

```bash
export GATEWAY_MCP_URL="https://<gateway-id>.gateway.bedrock-agentcore.<REGION>.amazonaws.com/mcp"
```

## Step 2: Add outbound credential

The Gateway needs a credential to authenticate with each backend runtime.
Since all runtimes share the same Cognito pool, you only need one credential:

```bash
agentcore add credential \
  --name pipeline-ops-oauth \
  --type oauth \
  --discovery-url "$DISCOVERY_URL" \
  --client-id "$CLIENT_ID" \
  --client-secret "$CLIENT_SECRET" \
  --scopes pipeline-ops/access
```

Deploy:

```bash
agentcore deploy -y
```
Verify:

```bash
agentcore status --type credential
```

The credential show show `Deployed`

## Step 3: Add Gateway targets

Link each runtime to the Gateway:

```bash
# Get runtime ARNs
agentcore status --type agent
```

Add targets (replace endpoints with your runtime URLs):

```bash
agentcore add gateway-target \
  --name pipeline \
  --type mcp-server \
  --gateway pipeline-ops-gateway \
  --outbound-auth oauth \
  --credential-name pipeline-ops-oauth \
  --endpoint <PIPELINE_RUNTIME_ENDPOINT>
```

```bash
agentcore add gateway-target \
  --name data-quality \
  --type mcp-server \
  --gateway pipeline-ops-gateway \
  --outbound-auth oauth \
  --credential-name pipeline-ops-oauth \
  --endpoint <DATAQUALITY_RUNTIME_ENDPOINT>
```

```bash
agentcore add gateway-target \
  --name catalog \
  --type mcp-server \
  --gateway pipeline-ops-gateway \
  --outbound-auth oauth \
  --credential-name pipeline-ops-oauth \
  --endpoint <CATALOG_RUNTIME_ENDPOINT>
```

Deploy:

```bash
agentcore deploy -y
```

## Step 4: Get a bearer token

```bash
TOKEN=$(curl -s -X POST "$TOKEN_ENDPOINT" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$CLIENT_ID&client_secret=$CLIENT_SECRET&scope=pipeline-ops/access" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Bearer token saved to \$TOKEN"
```

## Architecture so far

```
┌──────────────────────────┐     ┌──────────────────┐
│  AgentCore Gateway       │────▶│ Pipeline MCP     │
│  (single URL)            │     └──────────────────┘
│                          │────▶┌──────────────────┐
│  pipeline-ops-gateway    │     │ Data Quality MCP │
│                          │     └──────────────────┘
│                          │────▶┌──────────────────┐
└──────────────────────────┘     │ Catalog MCP      │
                                 └──────────────────┘
```

---

Prev: [Lab 2: Deploy MCP Servers](../02-deploy-mcp-servers/) | Next: [Lab 4: Deploy Specialist Agents](../04-deploy-specialists/)
