# AgentCore Multi-Agent Workshop: Data Pipeline Ops

Build and deploy a multi-agent AI system on Amazon Bedrock AgentCore. An orchestrator agent delegates to specialist agents — each built with a different framework — to diagnose, analyze, and fix data pipeline issues.


⚠️ **AWS Account Required** — This workshop runs in your own AWS account and will incur costs for services like Amazon Bedrock, AgentCore Runtime, Amazon ECR, Amazon Cognito, and CloudWatch. Clean up all resources when you're done (see Lab 10) to avoid ongoing charges. For a typical run-through, expect total costs under **$10**.

## The Story

> "My customer_orders pipeline failed at 3am. What happened, what data is affected, and can you fix it?"

A single prompt triggers a multi-agent workflow:

```
                    ┌──────────────────────────-┐
                    │   Pipeline Ops Agent      │
                    │   (Strands - Orchestrator)│
                    └──────────┬───────────────-┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
  ┌─────────────────┐ ┌────────────────┐ ┌─────────────────┐
  │ Pipeline Monitor│ │ Data Quality   │ │ Schema Manager  │
  │ (LangChain)     │ │ (LangChain)    │ │ (Strands)       │
  │  [HTTP]         │ │  [HTTP]        │ │  [A2A]          │
  └────────┬────────┘ └───────┬────────┘ └────────┬────────┘
           ▼                  ▼                    ▼
  ┌─────────────────┐ ┌────────────────┐ ┌─────────────────┐
  │ Pipeline MCP    │ │ Data Quality   │ │ Catalog MCP     │
  │ Server          │ │ MCP Server     │ │ Server          │
  └─────────────────┘ └────────────────┘ └─────────────────┘
```

## What You'll Learn

- **AgentCore Runtime**: Deploy agents and MCP servers as managed containers
- **AgentCore Gateway**: Unify multiple MCP servers behind a single URL
- **AgentCore Memory**: Add short-term and long-term memory to agents
- **AgentCore Policy**: Enforce business rules with Cedar policies
- **AgentCore Evaluations**: Measure agent quality with built-in evaluators
- **Multi-framework agents**: Strands and LangChain/LangGraph — all on Bedrock
- **A2A protocol**: Agent-to-Agent communication for multi-agent orchestration
- **MCP servers**: Build tools with FastMCP 3.0 that any agent can call

## Architecture

Each specialist agent runs on AgentCore Runtime — two using HTTP protocol and one using A2A. The orchestrator communicates with them using both protocols. All agents use Amazon Bedrock for LLM inference. MCP servers provide the tools (pipeline data, quality checks, schema catalog) through an AgentCore Gateway.

Key protocols:
- **MCP** — connects agents to tools (via Gateway)
- **A2A** — connects agents to agents (orchestrator ↔ Schema Manager)
- **HTTP** — connects agents to agents (orchestrator ↔ Pipeline Monitor, Data Quality)

## Repository Structure

```
agentcore-multiagent-workshop/
├── README.md
├── LICENSE                          # MIT-0
├── mcp-servers/                     # MCP tool servers (FastMCP 3.0)
│   ├── pipeline-mcp/               # Pipeline monitoring tools + data
│   ├── data-quality-mcp/           # Data quality check tools + data
│   └── catalog-mcp/                # Schema and catalog tools + data
├── agents/                          # Agent implementations
│   ├── orchestrator-strands/        # Orchestrator (Strands Agents SDK)
│   ├── pipeline-monitor-langchain/  # Specialist (LangChain/LangGraph)
│   ├── data-quality-langchain/       # Specialist (LangChain/LangGraph)
│   └── schema-manager-strands/          # Specialist (Strands Agents SDK)
└── labs/                            # Step-by-step workshop guide
    ├── 00-prerequisites/
    ├── 01-explore-mcp-servers/
    ├── 02-deploy-mcp-servers/
    ├── 03-setup-gateway/
    ├── 04-deploy-specialists/
    ├── 05-deploy-orchestrator/
    ├── 06-add-memory/
    ├── 07-add-policy/
    ├── 09-evaluations/
    └── 10-test-end-to-end/
```

## Prerequisites

- Python 3.11+
- AWS account with Bedrock model access (Claude Sonnet)
- [AgentCore CLI](https://github.com/aws/agentcore-cli) installed
- AWS credentials configured

## Quick Start

```bash
# Clone the repo
git clone https://github.com/<org>/agentcore-multiagent-workshop.git
cd agentcore-multiagent-workshop
```

## 👉 Start Here

**[→ Lab 0: Prerequisites](labs/00-prerequisites/README.md)** — Install tools, configure AWS credentials, and set up the project.

Then follow the labs in order:

| Lab | What you build |
|-----|---------------|
| [Lab 0: Prerequisites](labs/00-prerequisites/README.md) | Install AgentCore CLI, configure AWS |
| [Lab 1: Explore MCP Servers](labs/01-explore-mcp-servers/README.md) | Understand the FastMCP tool servers |
| [Lab 2: Deploy MCP Servers](labs/02-deploy-mcp-servers/README.md) | Deploy to AgentCore Runtime with OAuth2 |
| [Lab 3: Set Up Gateway](labs/03-setup-gateway/README.md) | Unify servers behind a single URL |
| [Lab 4: Deploy Specialists](labs/04-deploy-specialists/README.md) | Deploy LangChain (HTTP) and Strands (A2A) agents |
| [Lab 5: Deploy Orchestrator](labs/05-deploy-orchestrator/README.md) | Deploy the Strands orchestrator |
| [Lab 6: Add Memory](labs/06-add-memory/README.md) | Add STM and LTM to the orchestrator |
| [Lab 7: Add Policy](labs/07-add-policy/README.md) | Enforce Cedar policies at the Gateway |
| [Lab 9: Evaluations](labs/09-evaluations/README.md) | Score agent quality with built-in evaluators |
| [Lab 10: Test End-to-End](labs/10-test-end-to-end/README.md) | Run the full multi-agent system |

## Frameworks Used

| Component | Framework | AgentCore CLI Flag |
|-----------|-----------|-------------------|
| Orchestrator | Strands Agents SDK | `--framework Strands` |
| Pipeline Monitor | LangChain/LangGraph | `--framework LangChain_LangGraph` |
| Data Quality | LangChain/LangGraph | `--framework LangChain_LangGraph` |
| Schema Manager | Strands Agents SDK | `--framework Strands` |
| MCP Servers | FastMCP 3.0 | N/A (BYO protocol MCP) |

All agents use Amazon Bedrock (Claude Sonnet) for LLM inference.

## License

This project is licensed under the MIT-0 License. See [LICENSE](LICENSE).
