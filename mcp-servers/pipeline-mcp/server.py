"""Pipeline MCP Server — tools for monitoring and managing data pipelines."""

import json
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP("pipeline-mcp-server")

DATA_DIR = Path(__file__).resolve().parent / "data"


def _load(filename: str) -> list:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


@mcp.tool()
def list_pipelines(status: str = None) -> dict:
    """List all data pipelines, optionally filtered by status (SUCCEEDED, FAILED, RUNNING)."""
    pipelines = _load("pipelines.json")
    if status:
        pipelines = [p for p in pipelines if p["status"].upper() == status.upper()]
    return {"total": len(pipelines), "pipelines": pipelines}


@mcp.tool()
def get_pipeline_details(pipeline_id: str) -> dict:
    """Get full details for a specific pipeline by its ID (e.g. PL-001)."""
    pipelines = _load("pipelines.json")
    for p in pipelines:
        if p["pipeline_id"] == pipeline_id:
            return p
    return {"error": f"Pipeline {pipeline_id} not found"}


@mcp.tool()
def get_pipeline_run(run_id: str) -> dict:
    """Get detailed run information including logs, duration, and error messages."""
    runs = _load("pipeline-runs.json")
    for r in runs:
        if r["run_id"] == run_id:
            return r
    return {"error": f"Run {run_id} not found"}


@mcp.tool()
def get_pipeline_logs(pipeline_name: str, run_id: str) -> dict:
    """Get log entries for a specific pipeline run."""
    runs = _load("pipeline-runs.json")
    for r in runs:
        if r["run_id"] == run_id and r["pipeline_name"] == pipeline_name:
            return {"run_id": run_id, "pipeline": pipeline_name, "logs": r.get("logs", [])}
    return {"error": f"No logs found for {pipeline_name} run {run_id}"}


@mcp.tool()
def list_failed_runs(hours: int = 24) -> dict:
    """List all failed pipeline runs from the recent period."""
    runs = _load("pipeline-runs.json")
    failed = [r for r in runs if r["status"] == "FAILED"]
    return {"total_failed": len(failed), "runs": failed}


@mcp.tool()
def retry_pipeline(pipeline_name: str) -> dict:
    """Trigger a retry for a failed pipeline. Returns a new run ID."""
    pipelines = _load("pipelines.json")
    for p in pipelines:
        if p["name"] == pipeline_name:
            return {
                "status": "RETRY_INITIATED",
                "pipeline": pipeline_name,
                "new_run_id": f"RUN-{pipeline_name[:4].upper()}-RETRY-001",
                "message": f"Retry initiated for {pipeline_name}. Monitor with get_pipeline_run()."
            }
    return {"error": f"Pipeline {pipeline_name} not found"}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0")
