# Lab 9: Evaluate Agent Quality with AgentCore Evaluations

Measure how well your agents perform using AgentCore Evaluations.
Run built-in evaluators against real agent interactions to score
helpfulness, correctness, tool selection accuracy, and more.

## What you'll learn

- How AgentCore Evaluations assesses agent quality
- How to run on-demand evaluations against specific sessions
- How to interpret evaluation scores and explanations
- Built-in evaluators vs custom evaluators

## What is AgentCore Evaluations?

**AgentCore Evaluations** is a managed service that scores your agent's responses across multiple quality dimensions using an LLM-as-a-Judge approach. It works by analyzing the OpenTelemetry traces emitted during agent invocations — the same traces used for observability — so no additional instrumentation is needed.

Two evaluation modes:

| Mode | When to use | How it works |
|------|-------------|-------------|
| On-demand | Development and testing | You pick specific sessions to evaluate |
| Online | Production monitoring | Continuously samples and scores live traffic |

In this lab you'll use on-demand evaluation to score the orchestrator's
responses from Lab 8.

## Built-in evaluators

| Evaluator | Level | What it measures |
|-----------|-------|-----------------|
| `Builtin.Helpfulness` | Trace | How helpful and complete the response is |
| `Builtin.Correctness` | Trace | Whether the response is factually accurate |
| `Builtin.Relevance` | Trace | How relevant the response is to the question |
| `Builtin.ToolSelectionAccuracy` | Tool call | Whether the agent picked the right tool |
| `Builtin.InstructionFollowing` | Trace | How well the agent followed its system prompt |
| `Builtin.Safety` | Trace | Whether the response is safe and appropriate |
| `Builtin.Consistency` | Session | Whether responses are consistent across turns |

## Prerequisites

- Orchestrator deployed and tested (Lab 8 completed)
- `aws-opentelemetry-distro` in your agent's requirements.txt

## Step 1: Generate test sessions

Run a few scenarios through the orchestrator to create traces:

```bash
# Scenario 1: Pipeline failure investigation
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN \
  --session-id "eval-session-pipeline-failure-001" \
  "The customer_orders pipeline failed at 3am. What happened and what data is affected?"
```

```bash
# Scenario 2: Data quality check
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN \
  --session-id "eval-session-quality-check-001" \
  "Run a full data quality check on warehouse.orders.customer_orders"
```

```bash
# Scenario 3: Schema exploration
agentcore invoke --runtime PipelineOpsOrchestrator --bearer-token $TOKEN  \
  --session-id "eval-session-schema-explore-001" \
  "What tables exist in the warehouse? Which ones have quality issues?"
```

Wait 2-3 minutes for the traces to populate in CloudWatch.

## Step 2: Run on-demand evaluation with AgentCore CLI

The AgentCore CLI handles downloading spans from CloudWatch and calling
the Evaluate API for you:

```bash
agentcore run eval --runtime PipelineOpsOrchestrator \
  --session-id "eval-session-pipeline-failure-001" \
  --evaluator Builtin.Correctness Builtin.ToolSelectionAccuracy Builtin.InstructionFollowing
```
This returns a score (0-1) with an explanation of why the agent received
that score.

Sample Response:

```bash
agentcore run eval --runtime PipelineOpsOrchestrator \
  --session-id "eval-session-pipeline-failure-001" \
  --evaluator Builtin.Correctness Builtin.ToolSelectionAccuracy Builtin.InstructionFollowing


Agent: PipelineOpsOrchestrator | Apr 20, 2026, 03:30 PM | Sessions: 1 | Lookback: 7d

  Builtin.Correctness: 1.00
  Builtin.ToolSelectionAccuracy: 1.00
  Builtin.InstructionFollowing: 1.00
```
## Step 3: Run multiple evaluators

Evaluate the same session across different quality dimensions:

```bash
# Correctness — did the agent get the facts right?
agentcore run eval --runtime PipelineOpsOrchestrator \
  --session-id "eval-session-pipeline-failure-001" \
  --evaluator Builtin.Correctness
```

```bash
# Tool selection — did the agent call the right specialists?
agentcore run eval --runtime PipelineOpsOrchestrator \
  --session-id "eval-session-pipeline-failure-001" \
  --evaluator Builtin.ToolSelectionAccuracy 
```

```bash
# Instruction following — did the agent follow its system prompt?
agentcore run eval --runtime PipelineOpsOrchestrator \
  --session-id "eval-session-pipeline-failure-001" \
  --evaluator Builtin.InstructionFollowing
```

## Step 4: Interpret the results

Each evaluation result includes:

| Field | What it means |
|-------|--------------|
| `value` | Score from 0.0 to 1.0 (higher is better) |
| `label` | Human-readable label (e.g., "Very Helpful", "Mostly Correct") |
| `explanation` | LLM-generated explanation of why the score was given |
| `spanContext` | Which session/trace/span was evaluated |
| `tokenUsage` | How many tokens the evaluation consumed |

For the pipeline failure scenario, look for:
- Helpfulness > 0.7 — the agent provided actionable diagnosis
- ToolSelectionAccuracy > 0.8 — the agent called the right specialists
- Correctness > 0.7 — the agent correctly identified the schema mismatch

## Step 5: Ground truth evaluations

Ground truth evaluations let you compare the agent's actual behavior against known correct answers. Instead of relying solely on LLM-as-a-Judge scoring, you provide the expected response, expected tool trajectory, or assertions — and the evaluator measures how closely the agent matched.

### Ground truth evaluators

| Evaluator | Level | Ground truth field | Scoring |
|-----------|-------|--------------------|---------|
| `Builtin.Correctness` | Trace | `expectedResponse` | LLM-as-a-Judge |
| `Builtin.GoalSuccessRate` | Session | `assertions` | LLM-as-a-Judge |
| `Builtin.TrajectoryExactOrderMatch` | Session | `expectedTrajectory` | Programmatic (no LLM) |
| `Builtin.TrajectoryInOrderMatch` | Session | `expectedTrajectory` | Programmatic |
| `Builtin.TrajectoryAnyOrderMatch` | Session | `expectedTrajectory` | Programmatic |


Run ground truth evaluation using the CLI:

```bash
agentcore run eval \
  --runtime PipelineOpsOrchestrator \
  --session-id "eval-session-pipeline-failure-001" \
  --evaluator Builtin.Correctness \
  --evaluator Builtin.GoalSuccessRate \
  --evaluator Builtin.TrajectoryInOrderMatch \
  --assertion "The agent identified the SchemaValidationError as the root cause" \
  --assertion "The agent checked data lineage to find affected downstream tables" \
  --assertion "The agent mentioned at least 2 downstream tables that are impacted" \
  --assertion "The agent suggested whether a retry would fix the issue" \
  --expected-trajectory "ask_pipeline_monitor" \
  --expected-trajectory "ask_schema_manager" \
  --expected-trajectory "ask_data_quality_analyst" \
  --expected-response "The customer_orders pipeline (PL-001) failed due to a SchemaValidationError. The source added a new column 'discount_type' that doesn't exist in the target schema. 3 downstream tables are affected."
```

Its response:

```bash
Agent: PipelineOpsOrchestrator | Apr 30, 2026, 02:31 PM | Sessions: 1 | Lookback: 7d
Reference inputs: 4 assertion(s), expected response, 1 trajectory step(s)

  Builtin.Correctness: 1.00
  Builtin.GoalSuccessRate: 1.00
  Builtin.TrajectoryInOrderMatch: 1.00

```

The three trajectory evaluators differ in strictness:
- `TrajectoryExactOrderMatch` — same tools, same order, no extras
- `TrajectoryInOrderMatch` — expected tools appear in order, extras allowed between them
- `TrajectoryAnyOrderMatch` — all expected tools present, any order, extras allowed

For more details, see the [Ground Truth Evaluations documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/ground-truth-evaluations.html).

## What you learned

- AgentCore Evaluations scores agent quality using OpenTelemetry traces
- Built-in evaluators cover helpfulness, correctness, tool selection, safety, and more
- Ground truth evaluations compare agent behavior against known correct answers
- Trajectory matching verifies the agent called the right tools in the right order
- Goal success rate validates natural language assertions about agent behavior
- On-demand evaluation is useful during development; online evaluation monitors production

---

Prev: [Lab 7: Add Policy](../07-add-policy/) | Next: [Lab 10: Test End-to-End](../10-test-end-to-end/)
