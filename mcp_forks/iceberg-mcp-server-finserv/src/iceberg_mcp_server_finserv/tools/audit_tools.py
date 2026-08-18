"""Audit helpers for Impala (table-append mode; no Hive-style WAP branches)."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from iceberg_mcp_server_finserv.tools.sql import sql_quote, validate_ident

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _default_database(database: str | None) -> str:
    return database or os.getenv("IMPALA_DATABASE", "retirement_distributions")


def validate_run_id(run_id: str) -> str:
    rid = (run_id or "").strip()
    if not _RUN_ID_RE.match(rid):
        raise ValueError(
            "run_id must be 1–128 chars: alnum, underscore, dot, hyphen; "
            "must start with alnum"
        )
    return rid


def _json_field(value: Any, *, fallback: Any = None) -> str:
    if value is None:
        value = fallback
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return sql_quote(value)
    return sql_quote(json.dumps(value, default=str))


def insert_audit_event_sql(database: str, event: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    cols = [
        "run_id",
        "event_ts",
        "claim_id",
        "event_type",
        "next_step",
        "agent_role",
        "lane",
        "needs_llm",
        "terminal",
        "reason_probe_ids",
        "payload_json",
    ]
    values = [
        sql_quote(event.get("run_id")),
        f"CAST({sql_quote(event.get('event_ts'))} AS TIMESTAMP)"
        if event.get("event_ts")
        else "CURRENT_TIMESTAMP()",
        sql_quote(event.get("claim_id") or event.get("case_id")),
        sql_quote(event.get("event_type")),
        sql_quote(event.get("next_step")),
        sql_quote(event.get("agent_role")),
        sql_quote(event.get("lane")),
        sql_quote(event.get("needs_llm")),
        sql_quote(event.get("terminal")),
        _json_field(event.get("reason_probe_ids")),
        _json_field(event.get("payload_json"), fallback=event),
    ]
    return f"INSERT INTO {db}.agent_run_audit ({', '.join(cols)}) VALUES ({', '.join(values)})"


def insert_audit_evidence_sql(database: str, evidence: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    cols = [
        "run_id",
        "evidence_ts",
        "claim_id",
        "evidence_type",
        "probe_id",
        "content_format",
        "content_text",
        "content_uri",
    ]
    values = [
        sql_quote(evidence.get("run_id")),
        f"CAST({sql_quote(evidence.get('evidence_ts'))} AS TIMESTAMP)"
        if evidence.get("evidence_ts")
        else "CURRENT_TIMESTAMP()",
        sql_quote(evidence.get("claim_id") or evidence.get("case_id")),
        sql_quote(evidence.get("evidence_type")),
        sql_quote(evidence.get("probe_id")),
        sql_quote(evidence.get("content_format") or "json"),
        sql_quote(evidence.get("content_text") or json.dumps(evidence, default=str)),
        sql_quote(evidence.get("content_uri")),
    ]
    return (
        f"INSERT INTO {db}.agent_run_evidence ({', '.join(cols)}) "
        f"VALUES ({', '.join(values)})"
    )


def _parse_json_arg(raw: str | dict[str, Any], label: str) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def begin_agent_audit_run(
    run_id: str,
    database: str | None = None,
    source_branch: str | None = None,
) -> str:
    try:
        rid = validate_run_id(run_id)
        db = validate_ident(_default_database(database), "database")
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    return json.dumps(
        {
            "run_id": rid,
            "database": db,
            "mode": "table_append",
            "source_branch": source_branch or "main",
            "note": (
                "Impala path writes audit rows to main tables keyed by run_id. "
                "Hive WAP branches are not available on this server."
            ),
        }
    )


def append_agent_audit_event(
    run_id: str,
    event_json: str,
    database: str | None = None,
) -> str:
    from iceberg_mcp_server_finserv.tools.impala_tools import execute_dml

    try:
        rid = validate_run_id(run_id)
        db = validate_ident(_default_database(database), "database")
        event = _parse_json_arg(event_json, "event_json")
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    event = {**event, "run_id": rid}
    sql = insert_audit_event_sql(db, event)
    result = execute_dml(sql)
    if isinstance(result, str) and result.startswith("Error:"):
        return json.dumps({"error": result, "run_id": rid, "database": db})
    return json.dumps(
        {"ok": True, "run_id": rid, "database": db, "table": "agent_run_audit"}
    )


def append_agent_audit_evidence(
    run_id: str,
    evidence_json: str,
    database: str | None = None,
) -> str:
    from iceberg_mcp_server_finserv.tools.impala_tools import execute_dml

    try:
        rid = validate_run_id(run_id)
        db = validate_ident(_default_database(database), "database")
        evidence = _parse_json_arg(evidence_json, "evidence_json")
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    evidence = {**evidence, "run_id": rid}
    sql = insert_audit_evidence_sql(db, evidence)
    result = execute_dml(sql)
    if isinstance(result, str) and result.startswith("Error:"):
        return json.dumps({"error": result, "run_id": rid, "database": db})
    return json.dumps(
        {"ok": True, "run_id": rid, "database": db, "table": "agent_run_evidence"}
    )


def promote_agent_audit_run(
    run_id: str,
    database: str | None = None,
) -> str:
    try:
        rid = validate_run_id(run_id)
        db = validate_ident(_default_database(database), "database")
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    return json.dumps(
        {
            "ok": True,
            "run_id": rid,
            "database": db,
            "mode": "table_append",
            "note": "No branch promote on Impala; audit rows already on main.",
        }
    )


def abandon_agent_audit_run(
    run_id: str,
    database: str | None = None,
) -> str:
    from iceberg_mcp_server_finserv.tools.impala_tools import execute_dml

    try:
        rid = validate_run_id(run_id)
        db = validate_ident(_default_database(database), "database")
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    q_rid = sql_quote(rid)
    results = {}
    for table in ("agent_run_audit", "agent_run_evidence"):
        statement = f"DELETE FROM {db}.{table} WHERE run_id = {q_rid}"
        results[table] = execute_dml(statement)

    errors = {
        t: r for t, r in results.items() if isinstance(r, str) and r.startswith("Error:")
    }
    if errors:
        return json.dumps(
            {"ok": False, "run_id": rid, "database": db, "errors": errors}
        )
    return json.dumps(
        {
            "ok": True,
            "run_id": rid,
            "database": db,
            "mode": "table_append",
            "deleted_from": list(results.keys()),
        }
    )
