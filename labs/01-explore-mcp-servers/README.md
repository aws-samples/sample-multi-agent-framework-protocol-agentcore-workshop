# Lab 1: Explore the MCP Servers

In this lab you'll run the three MCP servers locally and understand what
tools they provide. The code is already written — you're exploring, not building.

## What you'll learn

- How FastMCP 3.0 servers are structured
- What tools each server exposes
- How to test MCP tools locally

## The three MCP servers

| Server | Tools | Purpose |
|--------|-------|---------|
| pipeline-mcp | list_pipelines, get_pipeline_run, get_pipeline_logs, list_failed_runs, retry_pipeline | Monitor and manage data pipelines |
| data-quality-mcp | get_quality_report, run_quality_check, compare_snapshots, get_lineage | Check data quality and trace lineage |
| catalog-mcp | search_tables, get_table_schema, get_table_stats, list_databases | Search and inspect table metadata |

## Step 1: Install dependencies

From the repo root:

```bash
pip install -r mcp-servers/pipeline-mcp/requirements.txt
pip install -r mcp-servers/data-quality-mcp/requirements.txt
pip install -r mcp-servers/catalog-mcp/requirements.txt
```

## Step 2: Run each server locally

Open three terminal tabs and start each server:

```bash
# Terminal 1
python -m mcp-servers.pipeline-mcp.server

# Terminal 2
python -m mcp-servers.data-quality-mcp.server

# Terminal 3
python -m mcp-servers.catalog-mcp.server
```

Each server starts on port 8000 by default. Since you can't run all
three on the same port simultaneously, either:
- Test one at a time (stop and start)
- Or use the AgentCore dev server in Lab 2

## Step 3: Explore the code

Look at each server's `server.py`. Notice the pattern:

1. Load mock data from the server's own `data/` subfolder
2. Define tools with `@mcp.tool()` decorators
3. Return structured dicts from every tool
4. Run with `mcp.run(transport="streamable-http", host="0.0.0.0")`

Each MCP server has its own `data/` subfolder with mock JSON files that simulate a real data engineering
environment with pipelines, quality reports, table schemas, and lineage.

## Step 4: Understand the mock data

Each MCP server has its own `data/` folder:

| Server | File | What it contains |
|--------|------|-----------------|
| pipeline-mcp | `data/pipelines.json` | 5 ETL pipelines (2 failed, 3 succeeded) |
| pipeline-mcp | `data/pipeline-runs.json` | Run history with logs and error messages |
| data-quality-mcp | `data/quality-reports.json` | Quality scores and rule results for 4 tables |
| data-quality-mcp | `data/lineage.json` | Upstream/downstream dependencies |
| catalog-mcp | `data/tables.json` | Schema definitions for 4 warehouse tables |

The key scenario: `customer_orders` (PL-001) failed because the source
added a `discount_type` column that doesn't exist in the target schema.

---

Prev: [Lab 0: Prerequisites](../00-prerequisites/) | Next: [Lab 2: Deploy MCP Servers](../02-deploy-mcp-servers/)
