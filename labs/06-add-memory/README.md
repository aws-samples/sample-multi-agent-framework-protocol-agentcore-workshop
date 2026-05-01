# Lab 6: Add Memory to the Orchestrator

Add AgentCore Memory so the orchestrator remembers past investigations.

## What is AgentCore Memory?

**AgentCore Memory** is a managed service that gives agents the ability to remember information across invocations. It provides two types of memory:

- **Short-term memory (STM)** stores the raw conversation turns within a session. The agent can reference what was said earlier in the same conversation without re-investigating. Retention is configurable (default 90 days).

- **Long-term memory (LTM)** extracts meaningful facts, preferences, and summaries from conversations and persists them across sessions. When a new session starts, the agent retrieves relevant long-term memories to inform its responses. LTM uses configurable strategies: semantic (facts), summarization (session summaries), and user preference (learned preferences).

## What you'll learn

- How AgentCore Memory provides short-term and long-term memory
- How to create a memory resource and attach it to an agent
- How memory improves multi-turn conversations

## Why memory matters for pipeline ops

Without memory, every conversation starts from scratch. With memory:
- The agent remembers that `customer_orders` breaks when marketing adds columns
- It recalls which pipelines you've already investigated today
- It learns your preferences (e.g., "always check lineage first")

## Step 1: Create a memory resource

```bash
agentcore add memory \
  --name PipelineOpsMemory \
  --strategies SEMANTIC,SUMMARIZATION,USER_PREFERENCE \
  --expiry 30
```

Deploy:

```bash
agentcore deploy -y
```

## Step 2: Verify

```bash
agentcore status --type memory
```

Save the memory ID from the output.

## Step 3: Update the orchestrator

Add the memory ID to the orchestrator's `.env` file:

```bash
# Edit agents/orchestrator-strands/.env and add:
BEDROCK_AGENTCORE_MEMORY_ID=<MEMORY_ID from Step 2>
```

The orchestrator code already supports memory — when `BEDROCK_AGENTCORE_MEMORY_ID`
is set, it creates an `AgentCoreMemorySessionManager` and passes it to the Strands
Agent. When the env var is not set, memory is disabled.

Redeploy:

```bash
agentcore deploy -y
```

## Step 4: Test short-term memory

Send multiple messages in the same session:

```bash
# Turn 1
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN \
  --session-id "pipeline-ops-debug-session-000001" \
  "The customer_orders pipeline failed. Investigate."
```

Sample response:

```bash
{
  "response": {
    "role": "assistant",
    "content": [
      {
        "text": "## Investigation Summary\n\nI've coordinated with my specialist agents to investigate the customer_orders pipeline failure. Here's the complete diagnosis:\n\n### **Root Cause: Schema Evolution Issue**\n\nThe customer_orders pipeline (PL-001) failed due to a **schema mismatch**. The source data now contains a new `discount_type` column (15 columns total) that doesn't exist in the target table `warehouse.orders.customer_orders` (14 columns).\n\n### **Failure Details**\n- **Failed At:** 2026-04-10T02:12:43Z\n- **Error:** `SchemaValidationError: Column 'discount_type' not found in target schema`\n- **Impact:** Zero records processed, complete pipeline failure\n- **Source Records:** 45,230 records were successfully read but couldn't be written\n\n### **Current State & Dependencies**\n- The table currently has 42,100 records with 23 orphaned customer_ids\n- 3 critical downstream pipelines depend on this table and are now blocked\n- Data quality score has dropped to 83.3% due to existing referential integrity issues\n\n### **Recommended Action Plan**\n\n1. **Immediate Fix - Add Missing Column:**\n   ```sql\n   ALTER TABLE warehouse.orders.customer_orders \n   ADD COLUMN discount_type VARCHAR(50) NULL;\n   ```\n\n2. **Pre-requisites:**\n   - First resolve the 23 orphaned customer_ids issue\n   - Update pipeline mapping to include the new field\n   - Test schema change in development environment\n\n3. **Downstream Impact Mitigation:**\n   - Update 3 dependent pipelines (revenue_rollup, ltv_calculation, reporting_refresh)\n   - Implement data quality checks for the new discount_type field\n\n4. **Execute Recovery:**\n   - Apply schema changes\n   - Retry the failed pipeline run\n   - Monitor downstream pipeline execution\n\n### **Prevention:**\nThis appears to be an uncoordinated schema evolution from the upstream source system. Implement schema change notifications and coordination processes to prevent future failures.\n\n**Priority:** **CRITICAL** - This is blocking daily reporting and revenue calculations. The fix should be implemented immediately."
      }
    ]
  }
}
```

# Turn 2 (same session)

```bash
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN\
  --session-id "pipeline-ops-debug-session-000001" \
  "What about the downstream tables? Are they affected?"
```

Sample response:

```bash
{
  "response": {
    "role": "assistant",
    "content": [
      {
        "text": "## Downstream Impact Assessment\n\nBased on my investigation with the specialist agents, here's what I found about the downstream tables affected by the customer_orders pipeline failure:\n\n### **Critical Discovery: Missing Downstream Infrastructure**\n\nThe three expected downstream tables:\n- `warehouse.analytics.revenue_daily`\n- `warehouse.analytics.customer_ltv` \n- `warehouse.reporting.order_summary`\n\n**Do not currently exist in the warehouse catalog.** This suggests a more significant issue than just pipeline failures.\n\n### **Current Impact Status**\n\n**Primary Issue:**\n- The `customer_orders` table has been **stale for 2+ days** (since 2026-04-10)\n- Approximately **45,230 new order records** from April 10th onwards are missing\n- Data quality has degraded from 94.2% to 83.3%\n\n**Downstream Pipeline Status:**\n- The expected pipelines (PL-010, PL-011, PL-012) are **not active** in the system\n- Only 5 total pipelines are currently running in the environment\n- This suggests the downstream analytics infrastructure was either:\n  - Never fully implemented\n  - Decommissioned due to previous failures\n  - Deployed in a different environment\n\n### **Business Impact**\n\nWithout the downstream tables, you're missing:\n- ❌ **Revenue reporting** - No daily revenue aggregations\n- ❌ **Customer analytics** - No lifetime value calculations  \n- ❌ **Order summaries** - No reporting layer for business users\n- ❌ **Historical trends** - Gap in analytics since April 10th\n\n### **Recommended Action Plan**\n\n**Immediate (High Priority):**\n1. **Fix the schema issue** in customer_orders first:\n   ```sql\n   ALTER TABLE warehouse.orders.customer_orders \n   ADD COLUMN discount_type VARCHAR(50) NULL;\n   ```\n\n2. **Retry the customer_orders pipeline** to restore data freshness\n\n**Medium Priority:**\n3. **Investigate downstream infrastructure** - Determine if the analytics tables and pipelines were never built or were removed\n4. **Design/rebuild the analytics layer** if it doesn't exist\n5. **Implement proper data lineage monitoring** to track dependencies\n\n**The good news:** Since the downstream tables don't exist, you don't have additional failed pipelines to fix. **The bad news:** You're missing critical business analytics infrastructure entirely.\n\nWould you like me to help design the missing downstream analytics architecture?"
      }
    ]
  }
}
```

```bash
# Turn 3 (same session)
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN\
  --session-id "pipeline-ops-debug-session-000001" \
  "Should we retry the pipeline?"
```

The agent should reference context from earlier turns without re-investigating.


## Step 5: Test long-term memory

Wait 60 seconds, then start a new session:

```bash
 agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN\
  --session-id "pipeline-ops-debug-session-000002" \
  "Any recurring issues with the customer_orders pipeline?"
```
Sample response:

```bash
{
  "response": {
    "role": "assistant",
    "content": [
      {
        "text": "Based on the Pipeline Monitor's investigation, there are significant recurring issues with the customer_orders pipeline that need immediate attention:\n\n## **Key Recurring Issues Identified:**\n\n### 🚨 **Critical Current Problem: Schema Evolution**\n- The pipeline is currently **FAILED** due to a schema mismatch\n- Source data contains a new `discount_type` column that doesn't exist in the target warehouse.orders.customer_orders table\n- This is causing complete pipeline failure with 0 records processed\n\n### 📊 **Data Quality Degradation**\n- **23 orphaned customer_ids** (matching your context) - these customer IDs don't exist in the upstream customer profiles table\n- Data quality score at 94.2%, indicating ongoing referential integrity issues\n- This suggests timing or synchronization problems with upstream customer data\n\n### 🔄 **Downstream Impact**\nThe customer_orders pipeline feeds **3 critical downstream systems**:\n- Revenue analytics (daily rollups)\n- Customer lifetime value calculations  \n- Executive reporting dashboards\n\nWhen this pipeline fails, it cascades to all revenue and customer analytics.\n\n## **Immediate Actions Required:**\n\n1. **Fix Schema Issue** (blocking current runs):\n   - Add the `discount_type VARCHAR` column to warehouse.orders.customer_orders\n   - Update transformation logic to handle the new field\n\n2. **Resolve Orphaned Customer IDs**:\n   - Investigate why 23 customer_ids don't exist in the customer profiles table\n   - Implement dependency checking to ensure customer data is available before processing orders\n\n3. **Prevent Future Occurrences**:\n   - Implement schema evolution strategy with automatic detection\n   - Add pre-flight validation checks for data dependencies\n   - Set up schema registry for source data contracts\n\n**Priority: CRITICAL** - This pipeline is production-critical and currently blocking all revenue analytics. The schema issue must be resolved before any retry attempts.\n\nWould you like me to have the Schema Manager investigate the specific schema changes needed, or have the Data Quality Analyst dig deeper into the orphaned customer ID issue?"
      }
    ]
  }
}
```
The agent should recall insights from the previous session and you can notice in the output that it has used the interactions of the earlier session (pipeline-ops-debug-session-000001)

**Note:** The session id should be greater than or equal to 33 characters

---

Prev: [Lab 5: Deploy the Orchestrator](../05-deploy-orchestrator/) | Next: [Lab 7: Add Policy](../07-add-policy/)
