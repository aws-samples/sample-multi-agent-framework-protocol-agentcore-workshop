# Lab 2: Deploy MCP Servers to AgentCore Runtime

Deploy all three MCP servers as managed containers on AgentCore Runtime.

## What is AgentCore Runtime?

**AgentCore Runtime** is a managed, serverless execution environment for AI agents and tools. It handles packaging your code into containers, deploying them to AWS, auto-scaling, session isolation, and OAuth2 authentication — so you focus on the agent logic, not the infrastructure. Each runtime gets a dedicated HTTPS endpoint and runs your code in an isolated environment per session.

## What you'll learn

- How to create a Cognito User Pool for OAuth2 authentication
- How to register MCP servers with the AgentCore CLI
- How AgentCore Runtime hosts and secures your servers

## Step 1: Create a Cognito User Pool

All runtimes and the Gateway share a single Cognito User Pool for
OAuth2 authentication. Create it with the AWS CLI:

```bash
# Create the user pool
aws cognito-idp create-user-pool \
  --pool-name pipeline-ops-pool \
  --auto-verified-attributes email \
  --query 'UserPool.Id' --output text
```

Save the Pool ID from the output (e.g., `us-east-1_aBcDeFgHi`).

```bash
export POOL_ID="<your-pool-id>"
```

Create a domain for the token endpoint:

```bash
aws cognito-idp create-user-pool-domain \
  --domain "pipeline-ops-$(aws sts get-caller-identity --query Account --output text)" \
  --user-pool-id "$POOL_ID"
```

Create a resource server with a scope:

```bash
aws cognito-idp create-resource-server \
  --user-pool-id "$POOL_ID" \
  --identifier pipeline-ops \
  --name "Pipeline Ops" \
  --scopes ScopeName=access,ScopeDescription="Access Pipeline Ops"
```

Create an app client with client credentials grant:

```bash
aws cognito-idp create-user-pool-client \
  --user-pool-id "$POOL_ID" \
  --client-name pipeline-ops-client \
  --generate-secret \
  --allowed-o-auth-flows client_credentials \
  --allowed-o-auth-scopes pipeline-ops/access \
  --allowed-o-auth-flows-user-pool-client \
  --query 'UserPoolClient.[ClientId,ClientSecret]' --output text
```

Save the Client ID and Client Secret from the output:

```bash
export CLIENT_ID="<your-client-id>"
export CLIENT_SECRET="<your-client-secret>"
```

Build the Discovery URL and Token Endpoint:

```bash
REGION="$AWS_DEFAULT_REGION"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

export DISCOVERY_URL="https://cognito-idp.${REGION}.amazonaws.com/${POOL_ID}/.well-known/openid-configuration"
export TOKEN_ENDPOINT="https://pipeline-ops-${ACCOUNT_ID}.auth.${REGION}.amazoncognito.com/oauth2/token"

echo "Discovery URL: $DISCOVERY_URL"
echo "Token Endpoint: $TOKEN_ENDPOINT"
```

### Verify

| Check | Expected result |
|-------|----------------|
| Pool ID set | `echo $POOL_ID` returns a value like `us-east-1_aBcDeFgHi` |
| Client ID set | `echo $CLIENT_ID` returns a value |
| Discovery URL accessible | `curl -s $DISCOVERY_URL \| jq .issuer` returns the pool URL |

## Step 2: Register MCP servers

From your AgentCore project directory, register all three MCP servers
using the same Cognito pool:

```bash
cd pipelineops
```

The AgentCore CLI uses `aws-targets.json` to know which AWS account and region to deploy to. You need your AWS Account ID for this.

Update the `agentcore/aws-targets.json` file with your account ID:

```bash
[
  {
    "name": "default",
    "description": "AgentCore Workshop AWS Account",
    "account": "<YOUR_AWS_ACCOUNT_ID>",
    "region": "<your-workshop-region>"
  }
]
```

```bash
# Pipeline MCP
agentcore add agent \
  --name PipelineMcp \
  --type byo \
  --code-location ../mcp-servers/pipeline-mcp \
  --entrypoint server.py \
  --protocol MCP \
  --language Python \
  --authorizer-type CUSTOM_JWT \
  --discovery-url "$DISCOVERY_URL" \
  --allowed-clients "$CLIENT_ID" \
  --allowed-scopes pipeline-ops/access
```

```bash
# Data Quality MCP
agentcore add agent \
  --name DataQualityMcp \
  --type byo \
  --code-location ../mcp-servers/data-quality-mcp \
  --entrypoint server.py \
  --protocol MCP \
  --language Python \
  --authorizer-type CUSTOM_JWT \
  --discovery-url "$DISCOVERY_URL" \
  --allowed-clients "$CLIENT_ID" \
  --allowed-scopes pipeline-ops/access
```

```bash
# Catalog MCP
agentcore add agent \
  --name CatalogMcp \
  --type byo \
  --code-location ../mcp-servers/catalog-mcp \
  --entrypoint server.py \
  --protocol MCP \
  --language Python \
  --authorizer-type CUSTOM_JWT \
  --discovery-url "$DISCOVERY_URL" \
  --allowed-clients "$CLIENT_ID" \
  --allowed-scopes pipeline-ops/access
```

## Step 3: Install dependencies and test locally

Install dependencies for each MCP server:

```bash
cd ../mcp-servers/pipeline-mcp && uv sync && cd -
cd ../mcp-servers/data-quality-mcp && uv sync && cd -
cd ../mcp-servers/catalog-mcp && uv sync && cd -
```

Then test each server:

```bash
agentcore dev --runtime PipelineMcp
agentcore dev --runtime DataQualityMcp
agentcore dev --runtime CatalogMcp
```

Verify each server lists its tools correctly.

## Step 4: Deploy

```bash
agentcore deploy -y
```

If you see "Role validation failed", wait 30 seconds and retry.

## Step 5: Verify

```bash
agentcore status --type agent
```

All three should show `Deployed` with `Runtime: READY`.

---

Prev: [Lab 1: Explore MCP Servers](../01-explore-mcp-servers/) | Next: [Lab 3: Set Up the Gateway](../03-setup-gateway/)
