"""Data Quality MCP Server — tools for checking and reporting on data quality."""

import json
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP("data-quality-mcp-server")

DATA_DIR = Path(__file__).resolve().parent / "data"


def _load(filename: str) -> list:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


@mcp.tool()
def get_quality_report(table: str) -> dict:
    """Get the latest data quality report for a table (e.g. warehouse.orders.customer_orders)."""
    reports = _load("quality-reports.json")
    for r in reports:
        if r["table"] == table:
            return r
    return {"error": f"No quality report found for {table}"}


@mcp.tool()
def run_quality_check(table: str, rules: list[str] = None) -> dict:
    """Run quality checks on a table. Rules: not_null, unique, freshness, range_check, etc."""
    reports = _load("quality-reports.json")
    for r in reports:
        if r["table"] == table:
            if rules:
                filtered = [rule for rule in r["rules"] if rule["rule"] in rules]
            else:
                filtered = r["rules"]
            passed = sum(1 for rule in filtered if rule["passed"])
            return {
                "table": table,
                "rules_checked": len(filtered),
                "rules_passed": passed,
                "rules_failed": len(filtered) - passed,
                "score": round((passed / len(filtered)) * 100, 1) if filtered else 0,
                "results": filtered
            }
    return {"error": f"No quality data found for {table}"}


@mcp.tool()
def compare_snapshots(table: str, date1: str, date2: str) -> dict:
    """Compare data quality between two dates for a table."""
    reports = _load("quality-reports.json")
    for r in reports:
        if r["table"] == table:
            return {
                "table": table,
                "date1": date1,
                "date2": date2,
                "score_date1": r["overall_score"] - 2.1,
                "score_date2": r["overall_score"],
                "change": "+2.1",
                "new_failures": [],
                "resolved_failures": ["freshness check on updated_at"],
                "note": "Simulated comparison based on current report"
            }
    return {"error": f"No data found for {table}"}


@mcp.tool()
def get_lineage(table: str) -> dict:
    """Get upstream and downstream data lineage for a table."""
    lineage = _load("lineage.json")
    for entry in lineage:
        if entry["table"] == table:
            return entry
    return {"error": f"No lineage found for {table}"}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0")
