# server.py
import os
from typing import Any, Dict, List, Optional
from fastmcp import FastMCP
from sqlalchemy import create_engine, text

mcp = FastMCP("MSSQL MCP")

# --- DB Engine (1x pro Prozess; Connection-Pool übernimmt SQLAlchemy) ---
DB_URL = os.getenv(
    "DATABASE_URL",
    # Beispiel: mssql+pyodbc://user:pass@HOST:1433/DB?driver=ODBC+Driver+17+for+SQL+Server
    "mssql+pyodbc://pack_user:A_Strong_Passw0rd@SQLSERVER_HOSTNAME:1433/WideWorldImporters?driver=ODBC+Driver+17+for+SQL+Server"
)
engine = create_engine(DB_URL, pool_pre_ping=True, future=True)

# --- READ: generische SELECT-Query ---
@mcp.tool(
    description="Run a parameterized SELECT query against MSSQL and return rows as JSON.",
    annotations={"external": True, "destructive": False}
)
def sql_select(query: str, params: Optional[Dict[str, Any]] = None, limit: Optional[int] = 200) -> List[Dict[str, Any]]:
    """
    Use **named** parameters like :name in the SQL and pass {'name': 'value'} in params.
    LIMIT wird nur angewandt, wenn sinnvoll (füge TOP n / OFFSET FETCH je nach Stil ein).
    """
    with engine.begin() as conn:
        q = text(query)
        rows = conn.execute(q, params or {}).mappings().fetchmany(limit) if limit else conn.execute(q, params or {}).mappings().all()
        return [dict(r) for r in rows]

# --- WRITE: INSERT/UPDATE/DELETE (kennzeichne als 'destructive') ---
@mcp.tool(
    description="Execute a parameterized INSERT/UPDATE/DELETE statement.",
    annotations={"external": True, "destructive": True}
)
def sql_execute(query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    with engine.begin() as conn:
        res = conn.execute(text(query), params or {})
        return {"rowcount": res.rowcount}

# --- Komfort-Tool: Hole die ersten N Zeilen aus schema.table ---
@mcp.tool(
    description="Preview first N rows from a table.",
    annotations={"external": True, "destructive": False}
)
def table_preview(db_schema: str, table: str, top: int = 50) -> List[Dict[str, Any]]:
    q = text(f"SELECT TOP (:top) * FROM [{db_schema}].[{table}]")
    with engine.begin() as conn:
        rows = conn.execute(q, {"top": top}).mappings().all()
        return [dict(r) for r in rows]

@mcp.tool(
    description="List available schemas in the current database.",
    annotations={"external": True, "destructive": False}
)
def list_schemas() -> list[str]:
    q = text("SELECT name FROM sys.schemas ORDER BY name")
    with engine.begin() as conn:
        return [r[0] for r in conn.execute(q).all()]

@mcp.tool(
    description="List tables for a given schema.",
    annotations={"external": True, "destructive": False}
)
def list_tables(db_schema: str) -> list[str]:
    q = text("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = :schema
        ORDER BY TABLE_NAME
    """)
    with engine.begin() as conn:
        return [r[0] for r in conn.execute(q, {"schema": db_schema}).all()]

@mcp.tool(
    description="Describe columns of a table (name, type, nullable).",
    annotations={"external": True, "destructive": False}
)
def describe_table(db_schema: str, table: str) -> list[dict]:
    q = text("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table
        ORDER BY ORDINAL_POSITION
    """)
    with engine.begin() as conn:
        return [dict(r) for r in conn.execute(q, {"schema": db_schema, "table": table}).mappings().all()]


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8001,
        path="/mcp/sql"
    )
