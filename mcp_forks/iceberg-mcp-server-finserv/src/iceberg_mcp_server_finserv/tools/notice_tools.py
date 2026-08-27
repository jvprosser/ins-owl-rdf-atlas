"""Named write: insert one outbound client notice plus an audit receipt."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Callable

from iceberg_mcp_server_finserv.tools.audit_tools import (
    _parse_json_arg,
    insert_audit_event_sql,
    validate_run_id,
)
from iceberg_mcp_server_finserv.tools.sql import insert_outbound_notice_sql, validate_ident

QueryFn = Callable[[str], list[dict[str, Any]]]
DmlFn = Callable[[str], str]

_NOTICE_STEPS = frozenset({"RequestSelfCertification"})
_DEFAULT_BODY = (
    "Please sign the hardship self-certification that you have an immediate "
    "and heavy financial need so we can continue processing your request."
)
_PURPOSE = "REQUEST_SELF_CERTIFICATION"


def _default_database(database: str | None) -> str:
    return database or os.getenv("IMPALA_DATABASE", "retirement_distributions")


def _notice_id(run_id: str, claim_id: str, purpose: str) -> int:
    digest = hashlib.sha256(f"{run_id}:{claim_id}:{purpose}".encode()).hexdigest()
    return int(digest[:15], 16)


def _need_dml(execute_dml: DmlFn | None) -> DmlFn:
    if execute_dml is not None:
        return execute_dml
    from iceberg_mcp_server_finserv.tools.impala_tools import execute_dml as _dml

    return _dml


def send_client_notice(
    run_id: str,
    event_json: str,
    database: str | None = None,
    *,
    execute_dml: DmlFn | None = None,
) -> str:
    try:
        rid = validate_run_id(run_id)
        db = validate_ident(_default_database(database), "database")
        body = _parse_json_arg(event_json, "event_json")
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    claim_id = body.get("claim_id")
    next_step = str(body.get("next_step") or "RequestSelfCertification").strip()
    if claim_id in (None, ""):
        return json.dumps({"error": "event_json.claim_id is required"})
    if next_step not in _NOTICE_STEPS:
        return json.dumps(
            {"error": "event_json.next_step must be RequestSelfCertification"}
        )

    cid = int(claim_id)
    text = str(body.get("body") or _DEFAULT_BODY).strip() or _DEFAULT_BODY
    row = {
        "notice_id": _notice_id(rid, str(claim_id), _PURPOSE),
        "distribution_request_id": cid,
        "purpose_code": _PURPOSE,
        "channel_code": str(body.get("channel_code") or "LETTER"),
        "body_text": text,
        "run_id": rid,
    }
    dml = _need_dml(execute_dml)
    notice_sql = insert_outbound_notice_sql(db, row)
    result = dml(notice_sql)
    if isinstance(result, str) and result.startswith("Error:"):
        return json.dumps({"error": result, "run_id": rid, "database": db})

    audit_event = {
        "run_id": rid,
        "claim_id": str(cid),
        "event_type": next_step,
        "next_step": next_step,
        "agent_role": "ClientCommunicationsAgent",
        "lane": "CUSTOMER_REMEDIATION",
        "terminal": False,
        "payload_json": {
            "notice_id": row["notice_id"],
            "purpose_code": _PURPOSE,
            "channel_code": row["channel_code"],
        },
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
                "table": "distribution_outbound_notice",
                "notice_id": row["notice_id"],
                "audit_written": False,
            }
        )
    return json.dumps(
        {
            "ok": True,
            "run_id": rid,
            "database": db,
            "table": "distribution_outbound_notice",
            "audit_table": "agent_run_audit",
            "notice_id": row["notice_id"],
            "claim_id": cid,
            "purpose_code": _PURPOSE,
            "channel_code": row["channel_code"],
            "body_text": text,
            "next_step": next_step,
            "agent_role": "ClientCommunicationsAgent",
            "lane": "CUSTOMER_REMEDIATION",
        }
    )
