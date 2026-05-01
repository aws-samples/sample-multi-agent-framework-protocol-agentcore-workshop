# Lab 0: Prerequisites

## What you need

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) |
| AgentCore CLI | Latest | [github.com/aws/agentcore-cli](https://github.com/aws/agentcore-cli) |
| AWS CLI | 2.x | [aws.amazon.com/cli](https://aws.amazon.com/cli/) |
| Git | Any | [git-scm.com](https://git-scm.com/) |

## AWS account setup

You need an AWS account with:
- Amazon Bedrock model access enabled for Claude Sonnet (`us.anthropic.claude-sonnet-4-20250514-v1:0`)
- IAM permissions for AgentCore, ECR, Cognito, KMS, and CloudWatch Logs

### Enable Bedrock model access

1. Open the [Amazon Bedrock console](https://console.aws.amazon.com/bedrock/)
2. Go to **Model access** in the left nav
3. Request access to **Anthropic Claude Sonnet**
4. Wait for approval (usually instant)

### Configure AWS credentials

```bash
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>
export AWS_DEFAULT_REGION=us-east-1
export AWS_SESSION_TOKEN=<your-token>  # if using temporary credentials
```

## Clone the repo

```bash
git clone https://github.com/<org>/agentcore-multiagent-workshop.git
cd agentcore-multiagent-workshop
```

## Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

## Initialize the AgentCore project

```bash
agentcore create --name pipelineops --no-agent
```

This creates the AgentCore project structure. You'll register MCP servers
and agents in the following labs.

---

Next: [Lab 1: Explore MCP Servers](../01-explore-mcp-servers/)
