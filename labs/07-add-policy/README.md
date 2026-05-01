# Lab 7: Add Governance with AgentCore Policy

Add Cedar policies to enforce access control at the Gateway level.

## What is AgentCore Policy?

**AgentCore Policy** lets you define authorization rules for your Gateway using [Cedar](https://www.cedarpolicy.com/), an open-source policy language created by AWS. Cedar policies are declarative — you state what is permitted, and everything else is denied by default. A policy engine holds your Cedar policies and attaches to a Gateway. When a tool call arrives, the Gateway evaluates it against the policies before forwarding it to the backend runtime. If the call violates a policy, the Gateway rejects it without ever reaching the tool server. This gives you fine-grained, centralized control over what agents can do, enforced at the infrastructure level.

## What you'll learn

- How AgentCore Policy enforces business rules with Cedar
- How to create a policy engine and attach it to the Gateway
- How to write permit rules for specific tools

## The scenario: read-only vs write operations

In a real data engineering team, not every agent or user should be able to trigger pipeline retries. A monitoring agent should be able to read pipeline status and logs, but only an authorized operations agent should be able to retry a failed pipeline.

This lab enforces that separation at the Gateway:

| Tool | Access | Why |
|------|--------|-----|
| `list_pipelines` | ✅ Permitted | Safe read — no side effects |
| `get_pipeline_run` | ✅ Permitted | Safe read — no side effects |
| `get_pipeline_logs` | ✅ Permitted | Safe read — no side effects |
| `list_failed_runs` | ✅ Permitted | Safe read — no side effects |
| `retry_pipeline` | ❌ Denied | Write operation — triggers pipeline execution |
| `run_quality_check` | ✅ Permitted | Read-only analysis |
| `get_quality_report` | ✅ Permitted | Read-only analysis |
| `get_lineage` | ✅ Permitted | Read-only analysis |
| `search_tables` | ✅ Permitted | Read-only catalog lookup |
| `get_table_schema` | ✅ Permitted | Read-only catalog lookup |

Cedar denies everything by default. You only need to write `permit` statements for what you want to allow.

## Step 1: Get the Gateway ARN

```bash
agentcore status --type gateway
```

Save the Gateway ARN from the output:

```bash
export GATEWAY_ARN="<your-gateway-arn>"
```

## Step 2: Create a policy engine

```bash
agentcore add policy-engine \
  --name pipeline_ops_policy \
  --description "Pipeline Ops Policy Engine" \
  --attach-to-gateways pipeline-ops-gateway \
  --attach-mode ENFORCE
```

Deploy:

```bash
agentcore deploy -y
```

Verify:

```bash
agentcore status
```

You should see `pipeline_ops_policy` deployed and attached to the Gateway.

## Step 3: Create the read-access policy

Permit all read-only tools across all three MCP servers:

```bash
agentcore add policy \
  --engine pipeline_ops_policy \
  --name allow_read_operations \
  --description "Permit all read-only tools — pipeline monitoring, quality checks, and catalog lookups" \
  --statement 'permit (
    principal,
    action in [
      AgentCore::Action::"pipeline___list_pipelines",
      AgentCore::Action::"pipeline___get_pipeline_run",
      AgentCore::Action::"pipeline___get_pipeline_logs",
      AgentCore::Action::"pipeline___list_failed_runs",
      AgentCore::Action::"data-quality___get_quality_report",
      AgentCore::Action::"data-quality___run_quality_check",
      AgentCore::Action::"data-quality___get_lineage",
      AgentCore::Action::"data-quality___compare_snapshots",
      AgentCore::Action::"catalog___search_tables",
      AgentCore::Action::"catalog___get_table_schema",
      AgentCore::Action::"catalog___get_table_stats",
      AgentCore::Action::"catalog___list_databases"
    ],
    resource == AgentCore::Gateway::"<GATEWAY_ARN>"
  );'
```
Get the Gateway ARN from agentcore status --type gateway

Get the Gateway ARN from gateway name - arn:aws:bedrock-agentcore:{REGION}:{ACCOUNTID}:gateway/{Gateway name from above command}. Replace REGION and ACCOUNTID accordingly.

Deploy:

```bash
agentcore deploy -y
```

Notice that `retry_pipeline` is **not** in the permit list. Cedar denies it by default.

## Step 4: Test the policies

### Read operations — should succeed

```bash
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN\
  "What pipelines failed in the last 24 hours?"
```

```bash
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN\
  "Check the data quality of warehouse.orders.customer_orders"
```

Both should return results — the Gateway permits these tool calls.

### Write operation — should be denied

```bash
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN\
  "Retry the customer_orders pipeline"
```

The orchestrator will ask the Pipeline Monitor to call `retry_pipeline`. The Gateway will block it with a policy violation error before it reaches the MCP server. The agent should report that the retry was not permitted.

Sample response:

```bash
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN\
  "Retry the customer_orders pipeline"
{
  "response": {
    "role": "assistant",
    "content": [
      {
        "text": "## 🚫 **RECOMMENDATION: DO NOT RETRY YET**\n\nBased on my investigation with the specialist teams, I must strongly advise **against retrying the customer_orders pipeline (PL-001)** until critical issues are resolved. Here's my comprehensive diagnosis:\n\n## 📊 **Current Pipeline Status: FAILED**\n\n### 🔴 **PRIMARY BLOCKER: Schema Evolution Error**\n- **Root Cause:** Source data now contains a new `discount_type` column (VARCHAR) that doesn't exist in the target schema\n- **Impact:** Pipeline fails at validation step - 0 records processed despite 45,230 input records\n- **Timeline:** Started failing April 10, 2026 when the new column appeared\n\n### ⚠️ **SECONDARY ISSUE: Data Quality Problems**\n- **Orphaned Records:** 23 customer_ids (0.055% of 42,100 records) don't exist in customer profiles\n- **Downstream Impact:** Affects revenue analytics, customer LTV calculations, and executive reporting\n- **Risk:** Data integrity compromised for production-critical analytics\n\n## 🛠️ **REQUIRED ACTIONS BEFORE RETRY:**\n\n### 1. **IMMEDIATE - Fix Schema Issue**\n```sql\n-- Add the missing column to target table\nALTER TABLE warehouse.orders.customer_orders \nADD COLUMN discount_type VARCHAR(50);\n```\n\n### 2. **URGENT - Address Data Quality**\n- Investigate the 23 orphaned customer_ids\n- Implement referential integrity validation\n- Set up quality monitoring with <0.1% orphan threshold\n\n### 3. **CRITICAL - Update Pipeline Configuration**\n- Modify pipeline to handle the new `discount_type` column in transformations\n- Add schema validation checks for future changes\n- Coordinate with source system team on schema change management\n\n## 🎯 **RECOMMENDED SEQUENCE:**\n1. **Schema Manager:** Update target table schema\n2. **Data Quality Analyst:** Resolve orphaned customer_ids  \n3. **Pipeline Monitor:** Update pipeline configuration\n4. **Test run** with recent data\n5. **Full retry** once all issues are resolved\n\n**Retrying now will result in the same schema validation failure.** The pipeline is correctly protecting data integrity by preventing writes when schema mismatches occur.\n\nWould you like me to coordinate with the teams to start implementing these fixes?"
      }
    ],
    "metadata": {
      "usage": {
        "inputTokens": 2830,
        "outputTokens": 543,
        "totalTokens": 3373
      },
      "metrics": {
        "latencyMs": 8604,
        "timeToFirstByteMs": 798
      }
    }
  }
}
```

### Why this matters

The policy is enforced at the Gateway — not in the agent code, not in the MCP server. Even if someone builds a different agent that connects to the same Gateway, the `retry_pipeline` tool is blocked for everyone. This is the key value of infrastructure-level policy enforcement.

---

Prev: [Lab 6: Add Memory](../06-add-memory/) | Next: [Lab 9: Evaluations](../09-evaluations/)
