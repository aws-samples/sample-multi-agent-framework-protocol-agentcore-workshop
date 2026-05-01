"""Catalog MCP Server — tools for searching and inspecting table schemas and metadata."""

import json
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP("catalog-mcp-server")

DATA_DIR = Path(__file__).resolve().parent / "data"


def _load(filename: str) -> list:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


@mcp.tool()
def search_tables(keyword: str) -> dict:
    """Search for tables by name, schema, or description."""
    tables = _load("tables.json")
    results = []
    kw = keyword.lower()
    for t in tables:
        searchable = f"{t['database']}.{t['schema']}.{t['table']} {t['description']}".lower()
        if kw in searchable:
            results.append({
                "full_name": f"{t['database']}.{t['schema']}.{t['table']}",
                "description": t["description"],
                "row_count": t["row_count"],
                "last_updated": t["last_updated"]
            })
    return {"total": len(results), "tables": results}


@mcp.tool()
def get_table_schema(database: str, table: str) -> dict:
    """Get the full schema (columns, types, partitions) for a table."""
    tables = _load("tables.json")
    for t in tables:
        if t["table"] == table and t["database"] == database:
            return {
                "full_name": f"{t['database']}.{t['schema']}.{t['table']}",
                "columns": t["columns"],
                "partitioned_by": t["partitioned_by"],
                "description": t["description"]
            }
    # Try matching by table name alone
    for t in tables:
        if t["table"] == table:
            return {
                "full_name": f"{t['database']}.{t['schema']}.{t['table']}",
                "columns": t["columns"],
                "partitioned_by": t["partitioned_by"],
                "description": t["description"]
            }
    return {"error": f"Table {database}.{table} not found"}


@mcp.tool()
def get_table_stats(database: str, table: str) -> dict:
    """Get statistics for a table: row count, size, last updated, partition count."""
    tables = _load("tables.json")
    for t in tables:
        if t["table"] == table and t["database"] == database:
            return {
                "full_name": f"{t['database']}.{t['schema']}.{t['table']}",
                "row_count": t["row_count"],
                "size_mb": t["size_mb"],
                "last_updated": t["last_updated"],
                "partition_count": len(t["partitioned_by"]),
                "column_count": len(t["columns"])
            }
    return {"error": f"Table {database}.{table} not found"}


@mcp.tool()
def list_databases() -> dict:
    """List all available databases and their tables."""
    tables = _load("tables.json")
    dbs = {}
    for t in tables:
        key = f"{t['database']}.{t['schema']}"
        if key not in dbs:
            dbs[key] = []
        dbs[key].append(t["table"])
    return {"databases": [{"name": k, "tables": v} for k, v in dbs.items()]}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0")
