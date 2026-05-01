# Lab 8: Test End-to-End

Run the full multi-agent system and see everything working together.

## What you built

```
User ──▶ Orchestrator (Strands)
              │
              ├──▶ Pipeline Monitor (LangChain)      [HTTP]  ──▶ Gateway ──▶ Pipeline MCP
              ├──▶ Data Quality (LangChain)              [HTTP]  ──▶ Gateway ──▶ Data Quality MCP
              └──▶ Schema Manager (Strands)              [A2A]   ──▶ Gateway ──▶ Catalog MCP
              │
              ├── AgentCore Memory (STM + LTM)
              └── AgentCore Policy (Cedar)
```

## Scenario 1: Pipeline failure investigation

```bash
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN \
  --session-id "end2end-agentcore-lab-test-session-001" \
  "The customer_orders pipeline failed at 3am. What happened, what data is affected, and can you fix it?"
```

Expected flow:
1. Orchestrator asks Pipeline Monitor → finds SchemaValidationError
2. Orchestrator asks Schema Manager → checks customer_orders schema
3. Orchestrator asks Data Quality → checks upstream quality and lineage
4. Orchestrator synthesizes: schema mismatch, 3 downstream tables affected

## Scenario 2: Multi-turn investigation

```bash
# Turn 1
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN \
  --session-id "end2end-agentcore-lab-test-session-001" \
  "What about the inventory_snapshot pipeline? That also failed."
```

```bash
# Turn 2
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN \
  --session-id "end2end-agentcore-lab-test-session-001" \
  "Give me a summary of all issues found today"
```

## Scenario 3: Data quality deep dive

```bash
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN \
  --session-id "end2end-agentcore-lab-test-session-002" \
  "Run a full data quality check on all warehouse tables and rank them by quality score"
```

## Scenario 4: Schema exploration

```bash
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN \
  --session-id "end2end-agentcore-lab-test-session-003" \
  "What tables exist in the warehouse? Show me the ones related to orders."
```

## Verify the full stack

| Component | Check | Command |
|-----------|-------|---------|
| MCP Servers | All 3 deployed | `agentcore status --type agent` |
| Gateway | All 3 targets | `agentcore status --type gateway` |
| Specialists | All 3 responding | `agentcore invoke --runtime PipelineMonitor "list failed pipelines"` |
| Orchestrator | Delegates correctly | Run Scenario 1 above |
| Memory | Remembers across turns | Run Scenario 2 above |
| Policy | Blocks retry | `agentcore invoke --runtime PipelineOpsOrchestrator "retry customer_orders"` |

## Cleanup

Remove all deployed resources:

```bash
agentcore remove all
agentcore deploy -y
```

## What you learned

- **AgentCore Runtime** hosts agents and MCP servers as managed containers
- **AgentCore Gateway** unifies multiple MCP servers behind one URL
- **AgentCore Memory** gives agents short-term and long-term memory
- **AgentCore Policy** enforces business rules with Cedar at the Gateway
- **Multi-framework support** — Strands and LangChain deploy the same way
- **Agent-as-a-tool** — the orchestrator calls specialists via HTTP, each running independently

The same patterns work for any domain: customer support, DevOps, finance, healthcare.
Replace the MCP servers and specialists, keep the AgentCore infrastructure.

---

Prev: [Lab 9: Evaluations](../09-evaluations/)
