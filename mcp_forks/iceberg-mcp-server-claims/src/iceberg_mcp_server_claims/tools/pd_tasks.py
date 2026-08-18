"""Named write: insert one pd_task row (no free SQL)."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from iceberg_mcp_server_claims.tools.audit_tools import _parse_json_arg, validate_run_id
from iceberg_mcp_server_claims.tools.claim_sql import sql_quote, validate_ident

_TASK_TYPES = frozenset({"REQUEST_POLICE_REPORT", "DETERMINE_FAULT", "PD_REVIEW"})


def _default_database(database: str | None) -> str:
    return database or os.getenv("IMPALA_DATABASE", "car_insurance_claims")


def _task_id(run_id: str, claim_id: str, task_type: str) -> int:
    digest = hashlib.sha256(f"{run_id}:{claim_id}:{task_type}".encode()).hexdigest()
    return int(digest[:15], 16)


def insert_pd_task_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    loss_id = row.get("loss_event_id")
    loss_sql = "NULL" if loss_id in (None, "") else str(int(loss_id))
    due = row.get("due_date")
    due_sql = "NULL" if due in (None, "") else f"CAST({sql_quote(str(due)[:10])} AS DATE)"
    return (
        f"INSERT INTO {db}.pd_task ("
        "pd_task_id, claim_id, loss_event_id, task_type_code, "
        "task_status_code, due_date, run_id, created_at"
        ") VALUES ("
        f"{int(row['pd_task_id'])}, {int(row['claim_id'])}, {loss_sql}, "
        f"{sql_quote(row['task_type_code'])}, {sql_quote(row.get('task_status_code') or 'OPEN')}, "
        f"{due_sql}, {sql_quote(row['run_id'])}, CURRENT_TIMESTAMP()"
        ")"
    )


def create_pd_task(
    run_id: str,
    event_json: str,
    database: str | None = None,
) -> str:
    from iceberg_mcp_server_claims.tools.impala_tools import execute_dml

    try:
        rid = validate_run_id(run_id)
        db = validate_ident(_default_database(database), "database")
        body = _parse_json_arg(event_json, "event_json")
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    claim_id = body.get("claim_id")
    task_type = str(body.get("task_type_code") or "").strip().upper()
    if claim_id in (None, ""):
        return json.dumps({"error": "event_json.claim_id is required"})
    if task_type not in _TASK_TYPES:
        return json.dumps(
            {
                "error": "event_json.task_type_code must be REQUEST_POLICE_REPORT, "
                "DETERMINE_FAULT, or PD_REVIEW",
            }
        )

    row = {
        "pd_task_id": _task_id(rid, str(claim_id), task_type),
        "claim_id": int(claim_id),
        "loss_event_id": body.get("loss_event_id"),
        "task_type_code": task_type,
        "task_status_code": "OPEN",
        "due_date": body.get("due_date"),
        "run_id": rid,
    }
    sql = insert_pd_task_sql(db, row)
    result = execute_dml(sql)
    if isinstance(result, str) and result.startswith("Error:"):
        return json.dumps({"error": result, "run_id": rid, "database": db})
    return json.dumps(
        {
            "ok": True,
            "run_id": rid,
            "database": db,
            "table": "pd_task",
            "pd_task_id": row["pd_task_id"],
            "claim_id": row["claim_id"],
            "task_type_code": task_type,
            "task_status_code": "OPEN",
        }
    )
