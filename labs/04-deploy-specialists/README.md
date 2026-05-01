# Lab 4: Deploy Specialist Agents

Deploy three specialist agents to AgentCore Runtime. Two use the A2A protocol
for agent-to-agent communication, and one uses direct HTTP. This demonstrates
both communication patterns supported by AgentCore.

## What you'll learn

- How AgentCore supports both A2A and HTTP protocols for agent communication
- How to deploy agents with different `--protocol` flags
- How A2A Agent Cards enable automatic agent discovery
- How HTTP agents use the standard `/invocations` endpoint

## Two communication protocols

| | HTTP | A2A |
|---|---|---|
| Port | 8080 | 9000 |
| Path | /invocations | / |
| Discovery | None | Agent Card at /.well-known/agent-card.json |
| Protocol | JSON (custom) | JSON-RPC 2.0 |
| Use case | Simple request/response | Standardized agent interop |

## The specialists

| Agent | Framework | Protocol | CLI Flags |
|-------|-----------|----------|-----------|
| Pipeline Monitor | LangChain/LangGraph | HTTP | `--framework LangChain_LangGraph` (HTTP is default) |
| Data Quality | LangChain/LangGraph | HTTP | `--framework LangChain_LangGraph` (HTTP is default) |
| Schema Manager | Strands Agents SDK | A2A | `--protocol A2A --framework Strands` |

All use Amazon Bedrock (Claude Sonnet).

## Step 1: Register the specialists

Create `.env` files in each specialist agent directory with the Gateway
credentials. Copy the `.env.example` template and fill in the values:

```bash
# Pipeline Monitor
cp ../agents/pipeline-monitor-langchain/.env.example ../agents/pipeline-monitor-langchain/.env
# Edit agents/pipeline-monitor-langchain/.env with your values

# Data Quality
cp ../agents/data-quality-langchain/.env.example ../agents/data-quality-langchain/.env
# Edit agents/data-quality-langchain/.env with your values

# Schema Manager
cp ../agents/schema-manager-strands/.env.example ../agents/schema-manager-strands/.env
# Edit agents/schema-manager-strands/.env with your values
```

Fill in `GATEWAY_MCP_URL`, `TOKEN_ENDPOINT`, `CLIENT_ID`, and `CLIENT_SECRET`
from Labs 2 and 3.

Then add the agents

```bash
# Pipeline Monitor (LangChain/LangGraph) — HTTP protocol
agentcore add agent \
  --name PipelineMonitor \
  --type byo \
  --code-location ../agents/pipeline-monitor-langchain \
  --entrypoint agent.py \
  --framework LangChain_LangGraph \
  --model-provider Bedrock \
  --language Python \
  --authorizer-type CUSTOM_JWT \
  --discovery-url "$DISCOVERY_URL" \
  --allowed-clients "$CLIENT_ID" \
  --allowed-scopes pipeline-ops/access
```

```bash
# Data Quality Analyst (LangChain/LangGraph) — HTTP protocol
agentcore add agent \
  --name DataQualityAnalyst \
  --type byo \
  --code-location ../agents/data-quality-langchain \
  --entrypoint agent.py \
  --framework LangChain_LangGraph \
  --model-provider Bedrock \
  --language Python \
  --authorizer-type CUSTOM_JWT \
  --discovery-url "$DISCOVERY_URL" \
  --allowed-clients "$CLIENT_ID" \
  --allowed-scopes pipeline-ops/access  
```

```bash
# Schema Manager (Strands) — A2A protocol
agentcore add agent \
  --name SchemaManager \
  --type byo \
  --code-location ../agents/schema-manager-strands \
  --entrypoint agent.py \
  --protocol A2A \
  --framework Strands \
  --model-provider Bedrock \
  --language Python \
  --authorizer-type CUSTOM_JWT \
  --discovery-url "$DISCOVERY_URL" \
  --allowed-clients "$CLIENT_ID" \
  --allowed-scopes pipeline-ops/access
```

## Step 2: Dev(Local) Testing of Agents

### Test HTTP agents (Pipeline Monitor, Data Quality)

```bash
agentcore dev --runtime PipelineMonitor
```

In another terminal, test using standard HTTP:

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What pipelines failed recently?"}'
```

### Test A2A agent (Schema Manager)

```bash
agentcore dev --runtime SchemaManager
```

In another terminal, test using A2A JSON-RPC:

```bash
curl -X POST http://localhost:9000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-001",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Show me the schema for customer_orders"}],
        "messageId": "msg-001"
      }
    }
  }'
```

Verify the Agent Card:

```bash
curl http://localhost:9000/.well-known/agent-card.json | jq .
```

Notice the difference: HTTP uses port 8080 with a simple JSON payload, A2A uses
port 9000 with JSON-RPC.

## Step 3: Deploy all specialists

Deploy:

```bash
agentcore deploy -y
```

## Step 4: Verify and save runtime URLs

```bash
agentcore status
```

All three should show as deployed. Save the runtime invocation URL — you'll need them
in Lab 5 to configure the orchestrator.

Build the runtime endpoint URLs from the ARNs:

```bash
REGION="$AWS_DEFAULT_REGION"

# Get Runtime Invocation URLs (replace with your actual URLs from agentcore status output)
export PIPELINE_MONITOR_URL="<PipelineMonitor Invocation URL from status>"
export DATA_QUALITY_URL="<DataQualityAnalyst Invocation URL from status>"
export SCHEMA_MANAGER_URL="<SchemaManager Invocation URL from status>"

echo "PIPELINE_MONITOR_URL=$PIPELINE_MONITOR_URL"
echo "DATA_QUALITY_URL=$DATA_QUALITY_URL"
echo "SCHEMA_MANAGER_URL=$SCHEMA_MANAGER_URL"
```

Test each:

**NOTE:** In this workshop, we have one credential shared across all runtimes and gateway. Our credential is pipeline-ops-oauth but the auto-fetch expects PipelineMonitor-oauth (or PipelineMcp-oauth, etc.) like <runtime>-oauth. The --identity-name flag on fetch access bridges that gap, but invoke doesn't have that flag yet, so you need to fetch the token separately and pass it with --bearer-token.

```bash
TOKEN=$(curl -s -X POST "$TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&scope=${SCOPE}" \
  | jq -r '.access_token')
```

```bash
agentcore invoke --runtime PipelineMonitor --bearer-token "$TOKEN"\
  "What pipelines failed in the last 24 hours?" 
```
```bash
agentcore invoke --runtime DataQualityAnalyst  --bearer-token "$TOKEN"\
  "Check data quality for warehouse.orders.customer_orders" --bearer-token "$TOKEN"
```

Due to issue in agentcorecli (https://github.com/aws/agentcore-cli/issues/815), the bearerToken not being passed in the A2A path is a gap in the current implementation.

Invoke the A2A runtime directly via curl bypassing the agentcore invoke:

```bash
curl -s -X POST "$SCHEMA_MANAGER_URL" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "messageId": "msg-001",
        "role": "user",
        "parts": [{"kind": "text", "text": "list schemas"}]
      }
    },
    "id": "1"
  }'
```
The messageId is a required field in the A2A protocol message schema. You can use any unique string — a UUID works too if you want to be proper about it ($(uuidgen)).

---

Prev: [Lab 3: Set Up the Gateway](../03-setup-gateway/) | Next: [Lab 5: Deploy the Orchestrator](../05-deploy-orchestrator/)
