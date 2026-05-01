# Lab 5: Deploy the Orchestrator Agent

Deploy the Strands orchestrator that communicates with
specialist agents using both HTTP and A2A protocols.

## What you'll learn

- How the orchestrator calls HTTP specialists via POST /invocations
- How the orchestrator discovers A2A specialists via Agent Cards
- How to wire up multi-agent communication through AgentCore

## Architecture

```
User ──▶ Orchestrator (Strands, HTTP)
              │
              ├──▶ Pipeline Monitor (LangChain)  [HTTP]  ──▶ Gateway ──▶ Pipeline MCP
              ├──▶ Data Quality (LangChain)      [HTTP]  ──▶ Gateway ──▶ Data Quality MCP
              └──▶ Schema Manager (Strands)       [A2A]  ──▶ Gateway ──▶ Catalog MCP
```

The orchestrator uses two communication patterns:
- **HTTP** (POST /invocations on port 8080): Pipeline Monitor and Data Quality
- **A2A** (JSON-RPC on port 9000): Schema Manager

## Step 1: Verify specialist endpoints from Lab 4

You should have these env vars set from Lab 4 Step 4 (via agentcore status command):

```bash
echo "PIPELINE_MONITOR_URL=$PIPELINE_MONITOR_URL"
echo "DATA_QUALITY_URL=$DATA_QUALITY_URL"
echo "SCHEMA_MANAGER_URL=$SCHEMA_MANAGER_URL"
```

If they're not set, go back to Lab 4 Step 4 and build them from the runtime ARNs.

## Step 2: Register the orchestrator

The orchestrator uses standard HTTP protocol (not A2A) since it's the
entry point that users call directly:

```bash
agentcore add agent \
  --name PipelineOpsOrchestrator \
  --type byo \
  --code-location ../agents/orchestrator-strands \
  --entrypoint agent.py \
  --framework Strands \
  --model-provider Bedrock \
  --language Python \
  --authorizer-type CUSTOM_JWT \
  --discovery-url "$DISCOVERY_URL" \ 
  --allowed-clients "$CLIENT_ID" \
  --allowed-scopes pipeline-ops/access
```

## Step 3: Test locally

Start the orchestrator:

```bash
agentcore dev --runtime PipelineOpsOrchestrator
```

Test:

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "The customer_orders pipeline failed last night. What happened, what data is affected, and should we retry?"}'
```

The orchestrator should:
1. Discover each specialist's Agent Card
2. Send A2A messages to investigate the failure
3. Synthesize a diagnosis from all three specialists

Here's the sample response:

```bash
{"response": {"role": "assistant", "content": [{"text": "## Diagnosis Summary\n\nBased on my investigation with the specialist teams, here's what happened with the customer_orders pipeline failure:\n\n### **Root Cause: Schema Evolution Issue**\nThe pipeline failed last night at 02:12:43Z due to a **schema validation error**. The source data from S3 now contains a new column `discount_type` (15 columns total), but the target table `warehouse.orders.customer_orders` still expects the old schema (14 columns). This is a controlled failure - the pipeline properly detected the mismatch and rolled back to prevent data corruption.\n\n### **What Data is Affected**\n- **Immediate Impact**: 45,230 order records from 2026-04-09 are stuck in the pipeline and haven't been processed\n- **Downstream Impact**: Three critical systems are now missing the latest data:\n  - Revenue daily analytics (`warehouse.analytics.revenue_daily`)\n  - Customer lifetime value calculations (`warehouse.analytics.customer_ltv`) \n  - Management order summary reports (`warehouse.reporting.order_summary`)\n- **No Data Loss**: The transaction was properly rolled back, so no corrupted data exists\n\n### **Additional Issue Discovered**\nThe Data Quality Analyst found a secondary problem: 23 orphaned customer IDs in existing data that don't match customer profiles, suggesting potential referential integrity issues.\n\n### **Should You Retry?**\n**❌ DO NOT RETRY** until the schema is fixed. The same error will occur again.\n\n### **Recommended Action Plan**\n1. **Immediate (Priority 1)**: Update the target table schema to add the `discount_type VARCHAR` column\n2. **Test**: Validate the schema change in development first\n3. **Retry**: Once schema is updated, retry the pipeline to process the 45,230 pending records\n4. **Follow-up**: Investigate the 23 orphaned customer IDs for data integrity\n5. **Prevention**: Implement schema change alerts from upstream sources\n\nThe good news is this was a clean failure with no data corruption. Once the schema is updated, the pipeline should process successfully."}]}}%
```

## Step 4: Deploy

```bash
agentcore deploy -y
```

Verify:

```bash
agentcore status
```

You should see the Orchestrator Agent Deployed and has runtime invocation url

## Step 5: Test end-to-end

The agent PipelineOpsOrchestrator has been configured with Inbound oauth, hence we need to pass the bearer token to test it.

Obtain the token (if expired):

```bash
CLIENT_ID=<CLIENT_ID>
CLIENT_SECRET=<CLIENT_SECRET>
TOKEN_URL=<TOKEN_URL>
SCOPE="pipeline-ops/access"

TOKEN=$(curl -s -X POST "$TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&scope=${SCOPE}" \
  | jq -r '.access_token')
```

```bash
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN  "The customer_orders pipeline failed last night. What happened?"  
```

Sample response: 

```bash
{
  "response": {
    "role": "assistant",
    "content": [
      {
        "text": "## Diagnosis Summary\n\nBased on my investigation with the specialist agents, here's what happened to the customer_orders pipeline last night:\n\n### **Root Cause: Schema Mismatch**\nThe pipeline failed due to a **schema validation error** caused by an unexpected new column called `discount_type` (VARCHAR) that appeared in the source data from April 9th, 2026, but doesn't exist in the target schema.\n\n### **Failure Timeline:**\n- **02:00:15Z** - Pipeline started normally\n- **02:01:30Z** - Successfully read 45,230 records from source\n- **02:10:20Z** - Schema mismatch detected (15 columns found vs 14 expected)\n- **02:12:43Z** - Pipeline failed with SchemaValidationError\n\n### **Contributing Factor:**\nThe Data Quality Analyst also identified 23 orphaned customer_ids (0.05% of records) that don't exist in the customer profiles table, which could cause additional downstream issues once the schema problem is resolved.\n\n### **Recommended Actions:**\n\n1. **Immediate Fix (Required):**\n   - Update the target schema to include the new `discount_type` VARCHAR column\n   - Modify pipeline transformation logic to handle this new field\n   - **Do NOT retry the pipeline until the schema is updated**\n\n2. **Data Quality Fix:**\n   - Investigate the 23 orphaned customer_ids to determine if they're legitimate new customers or data issues\n   - Consider updating downstream pipelines to handle missing customer references gracefully\n\n3. **Prevention:**\n   - Coordinate with upstream data providers to get advance notice of schema changes\n   - Implement automated schema drift detection\n\nWould you like me to help coordinate the schema update or investigate the orphaned customer_ids further?"
      }
    ]
  }
}

```
Try more scenarios:

```bash
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN \
  "Check the data quality of all tables and give me a summary"

agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN \
  "What tables are in the warehouse and which ones have quality issues?"
```

---

Prev: [Lab 4: Deploy Specialist Agents](../04-deploy-specialists/) | Next: [Lab 6: Add Memory](../06-add-memory/)
