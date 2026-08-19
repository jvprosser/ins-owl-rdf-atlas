"""Named write: set claim_status_code = DENIED and insert an audit receipt."""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from iceberg_mcp_server_claims.tools.audit_tools import (
    _parse_json_arg,
    insert_audit_event_sql,
    validate_run_id,
)
from iceberg_mcp_server_claims.tools.claim_sql import validate_ident

QueryFn = Callable[[str], list[dict[str, Any]]]
DmlFn = Callable[[str], str]

_DENY_STEPS = frozenset(
    {"DenyUnlawfulOperation", "DenyExcludedDriver", "DenyLapsedPolicy"}
)


def _default_database(database: str | None) -> str:
    return database or os.getenv("IMPALA_DATABASE", "car_insurance_claims")


def update_claim_denied_sql(database: str, claim_id: int) -> str:
    db = validate_ident(database, "database")
    return (
        f"UPDATE {db}.claim SET claim_status_code = 'DENIED' "
        f"WHERE claim_id = {int(claim_id)} "
        f"AND UPPER(COALESCE(claim_status_code, '')) NOT IN ('CLOSED', 'DENIED')"
    )


def deny_claim(
    run_id: str,
    event_json: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
    execute_dml: DmlFn | None = None,
) -> str:
    from iceberg_mcp_server_claims.tools.impala_tools import (
        execute_dml as _dml,
        query_rows as _qr,
    )

    qr = query_rows or _qr
    dml = execute_dml or _dml
    try:
        rid = validate_run_id(run_id)
        db = validate_ident(_default_database(database), "database")
        body = _parse_json_arg(event_json, "event_json")
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    claim_id = body.get("claim_id")
    next_step = str(body.get("next_step") or "").strip()
    if claim_id in (None, ""):
        return json.dumps({"error": "event_json.claim_id is required"})
    if next_step not in _DENY_STEPS:
        return json.dumps(
            {
                "error": "event_json.next_step must be DenyUnlawfulOperation, "
                "DenyExcludedDriver, or DenyLapsedPolicy",
            }
        )

    cid = int(claim_id)
    status_sql = f"SELECT claim_status_code FROM {db}.claim WHERE claim_id = {cid}"
    try:
        rows = qr(status_sql)
    except Exception as exc:
        return json.dumps({"error": str(exc), "run_id": rid, "database": db})

    if not rows:
        return json.dumps(
            {
                "error": f"claim {cid} not found",
                "run_id": rid,
                "database": db,
            }
        )

    status = str(rows[0].get("claim_status_code") or "").strip().upper()
    if status == "CLOSED":
        return json.dumps(
            {
                "error": "claim is CLOSED (approved); deny_claim refused",
                "run_id": rid,
                "database": db,
                "claim_id": cid,
                "claim_status_code": "CLOSED",
            }
        )
    if status == "DENIED":
        return json.dumps(
            {
                "error": "claim is already DENIED; do not call deny_claim on DenyAudit",
                "run_id": rid,
                "database": db,
                "claim_id": cid,
                "claim_status_code": "DENIED",
            }
        )

    update_sql = update_claim_denied_sql(db, cid)
    result = dml(update_sql)
    if isinstance(result, str) and result.startswith("Error:"):
        return json.dumps({"error": result, "run_id": rid, "database": db})

    audit_event = {
        "run_id": rid,
        "claim_id": str(cid),
        "event_type": next_step,
        "next_step": next_step,
        "agent_role": "DenyAgent",
        "lane": "DENY",
        "terminal": True,
        "payload_json": {"claim_status_code": "DENIED", "next_step": next_step},
    }
    audit_sql = insert_audit_event_sql(db, audit_event)
    audit_result = dml(audit_sql)
    if isinstance(audit_result, str) and audit_result.startswith("Error:"):
        return json.dumps(
            {
                "ok": False,
                "error": audit_result,
                "run_id": rid,
                "database": db,
                "claim_id": cid,
                "claim_status_code": "DENIED",
                "audit_written": False,
            }
        )
    return json.dumps(
        {
            "ok": True,
            "run_id": rid,
            "database": db,
            "table": "claim",
            "audit_table": "agent_run_audit",
            "claim_id": cid,
            "claim_status_code": "DENIED",
            "next_step": next_step,
            "agent_role": "DenyAgent",
            "lane": "DENY",
            "terminal": True,
        }
    )
