"""Impala connectivity (based on cloudera/iceberg-mcp-server; returns columns+rows)."""

from __future__ import annotations

import json
import os
from typing import Any

from impala.dbapi import connect

READONLY_PREFIXES = frozenset({"select", "show", "describe", "with", "explain"})
DML_PREFIXES = frozenset({"insert", "update", "delete"})


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_db_connection():
    host = os.getenv("IMPALA_HOST", "coordinator-default-impala.example.com")
    port = int(os.getenv("IMPALA_PORT", "443"))
    user = os.getenv("IMPALA_USER", "username")
    password = os.getenv("IMPALA_PASSWORD", "password")
    database = os.getenv("IMPALA_DATABASE", "default")
    auth_mechanism = os.getenv("IMPALA_AUTH_MECHANISM", "LDAP")
    use_http_transport = _env_bool("IMPALA_USE_HTTP_TRANSPORT", True)
    http_path = os.getenv("IMPALA_HTTP_PATH", "cliservice")
    use_ssl = _env_bool("IMPALA_USE_SSL", True)

    return connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        auth_mechanism=auth_mechanism,
        use_http_transport=use_http_transport,
        http_path=http_path,
        use_ssl=use_ssl,
    )


def _close(conn) -> None:
    if conn is None:
        return
    try:
        conn.close()
    except Exception:
        pass


def _execute(query: str) -> dict[str, Any] | str:
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        if cur.description:
            columns = [col[0] for col in cur.description]
            rows = cur.fetchall()
            cur.close()
            return {"columns": columns, "rows": [list(r) for r in rows]}
        try:
            conn.commit()
        except Exception:
            pass
        cur.close()
        return "Query executed successfully."
    except Exception as exc:
        return f"Error: {exc}"
    finally:
        _close(conn)


def execute_query(query: str) -> str:
    """Read-only SQL → JSON ``{columns, rows}``."""
    stripped = query.strip().lower()
    if not stripped or stripped.split()[0] not in READONLY_PREFIXES:
        return "Only read-only queries are allowed."
    result = _execute(query)
    if isinstance(result, str):
        return result
    return json.dumps(result, default=str)


def execute_dml(statement: str) -> str:
    """Allow-listed DML (INSERT/UPDATE/DELETE) for audit helpers only."""
    stripped = statement.strip().lower()
    if not stripped or stripped.split()[0] not in DML_PREFIXES:
        return "Error: only INSERT, UPDATE, and DELETE are allowed"
    result = _execute(statement)
    if isinstance(result, str):
        return result
    return json.dumps(result, default=str)


def get_schema(database: str | None = None) -> str:
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if database:
            cur.execute(f"SHOW TABLES IN `{database}`")
        else:
            cur.execute("SHOW TABLES")
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        return json.dumps(
            {
                "database": database or os.getenv("IMPALA_DATABASE", "default"),
                "tables": tables,
            }
        )
    except Exception as exc:
        return f"Error: {exc}"
    finally:
        _close(conn)


def query_rows(query: str) -> list[dict[str, Any]]:
    """Execute read-only SQL and return list of row dicts (raises on error)."""
    raw = execute_query(query)
    if isinstance(raw, str) and (raw.startswith("Error:") or raw.startswith("Only read-only")):
        raise RuntimeError(raw)
    payload = json.loads(raw)
    columns = payload.get("columns") or []
    rows = payload.get("rows") or []
    out: list[dict[str, Any]] = []
    # Impala may return mixed-case column names; normalize for tool consumers.
    cols = [str(c).lower() for c in columns]
    for row in rows:
        out.append({cols[i]: row[i] for i in range(min(len(cols), len(row)))})
    return out
