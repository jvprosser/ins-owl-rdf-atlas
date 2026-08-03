"""Direct HiveServer2 execute_query compatible with IcebergFacade SQL fallbacks."""

from __future__ import annotations

import json
from typing import Any, Callable

READONLY_PREFIXES = frozenset({"select", "show", "describe", "with", "explain"})


def make_execute_query(config: Any) -> Callable[..., str]:
    """Return ``execute_query(query) -> JSON str`` using impyla (same shape as MCP)."""

    def execute_query(query: str) -> str:
        stripped = query.strip().lower()
        if not stripped or stripped.split()[0] not in READONLY_PREFIXES:
            return "Only read-only queries are allowed."
        try:
            from impala.dbapi import connect
        except ImportError as exc:
            raise RuntimeError(
                "impyla is required for Hive access in Agent Studio tools. "
                "Add impyla to the tool requirements.txt."
            ) from exc

        conn = None
        try:
            conn = connect(
                host=config.hive_host,
                port=int(config.hive_port),
                user=config.hive_user,
                password=config.hive_password,
                database=config.hive_database,
                auth_mechanism=config.hive_auth_mechanism,
                use_http_transport=bool(config.hive_use_http_transport),
                http_path=config.hive_http_path,
                use_ssl=bool(config.hive_use_ssl),
            )
            cur = conn.cursor()
            cur.execute(query)
            if cur.description:
                columns = [col[0] for col in cur.description]
                rows = cur.fetchall()
                cur.close()
                return json.dumps({"columns": columns, "rows": rows}, default=str)
            cur.close()
            return json.dumps({"columns": [], "rows": []})
        except Exception as exc:
            return f"Error: {exc}"
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    return execute_query
