"""Named write: insert one pd_task row (no free SQL)."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Callable

from iceberg_mcp_server_claims.tools.audit_tools import (
    _parse_json_arg,
    insert_audit_event_sql,
    validate_run_id,
)
from iceberg_mcp_server_claims.tools.claim_sql import sql_quote, validate_ident

QueryFn = Callable[[str], list[dict[str, Any]]]
DmlFn = Callable[[str], str]

_TASK_TYPES = frozenset(
    {
        "COLLECT_INCIDENT_NUMBER",
        "REQUEST_POLICE_REPORT",
        "DETERMINE_FAULT",
        "PD_REVIEW",
    }
)
_TASK_TO_STEP = {
    "COLLECT_INCIDENT_NUMBER": "CollectIncidentReportNumber",
    "REQUEST_POLICE_REPORT": "RequestPoliceReport",
    "DETERMINE_FAULT": "DetermineFault",
    "PD_REVIEW": "PdClaimsReview",
}
_SMS_BODY = (
    "Please open the claims app and enter the police incident report number "
    "so we can request the exchange slip from the agency."
)
_SMS_PURPOSE = "COLLECT_INCIDENT_REPORT_NUMBER"


def _default_database(database: str | None) -> str:
    return database or os.getenv("IMPALA_DATABASE", "car_insurance_claims")


def _task_id(run_id: str, claim_id: str, task_type: str) -> int:
    digest = hashlib.sha256(f"{run_id}:{claim_id}:{task_type}".encode()).hexdigest()
    return int(digest[:15], 16)


def _message_id(run_id: str, claim_id: str, purpose: str) -> int:
    digest = hashlib.sha256(f"{run_id}:{claim_id}:{purpose}".encode()).hexdigest()
    return int(digest[:15], 16)


def insured_phone_sql(database: str, claim_id: int) -> str:
    db = validate_ident(database, "database")
    return f"""
SELECT pe.phone_number
FROM {db}.claim_party_role cpr
INNER JOIN {db}.person pe ON pe.party_id = cpr.party_id
WHERE cpr.claim_id = {int(claim_id)}
  AND cpr.role_type_code = 'INSURED'
  AND cpr.is_current_assignment = TRUE
LIMIT 1
""".strip()


def police_report_count_sql(database: str, claim_id: int) -> str:
    db = validate_ident(database, "database")
    return (
        f"SELECT COUNT(*) AS cnt FROM {db}.police_report "
        f"WHERE claim_id = {int(claim_id)}"
    )


def intake_incident_number_sql(database: str, claim_id: int) -> str:
    db = validate_ident(database, "database")
    return f"""
SELECT incident_report_number
FROM {db}.claim_police_intake
WHERE claim_id = {int(claim_id)}
  AND incident_report_number IS NOT NULL
  AND TRIM(incident_report_number) <> ''
ORDER BY collected_at DESC
LIMIT 1
""".strip()


def insert_pd_task_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    loss_id = row.get("loss_event_id")
    loss_sql = "NULL" if loss_id in (None, "") else str(int(loss_id))
    due = row.get("due_date")
    due_sql = "NULL" if due in (None, "") else f"CAST({sql_quote(str(due)[:10])} AS DATE)"
    incident = row.get("incident_report_number")
    incident_sql = "NULL" if incident in (None, "") else sql_quote(str(incident).strip())
    return (
        f"INSERT INTO {db}.pd_task ("
        "pd_task_id, claim_id, loss_event_id, task_type_code, "
        "task_status_code, due_date, incident_report_number, run_id, created_at"
        ") VALUES ("
        f"{int(row['pd_task_id'])}, {int(row['claim_id'])}, {loss_sql}, "
        f"{sql_quote(row['task_type_code'])}, {sql_quote(row.get('task_status_code') or 'OPEN')}, "
        f"{due_sql}, {incident_sql}, {sql_quote(row['run_id'])}, CURRENT_TIMESTAMP()"
        ")"
    )


def insert_outbound_message_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    return (
        f"INSERT INTO {db}.claim_outbound_message ("
        "message_id, claim_id, channel_code, to_phone, body_text, "
        "purpose_code, run_id, created_at"
        ") VALUES ("
        f"{int(row['message_id'])}, {int(row['claim_id'])}, "
        f"{sql_quote(row.get('channel_code') or 'SMS')}, "
        f"{sql_quote(row.get('to_phone'))}, {sql_quote(row['body_text'])}, "
        f"{sql_quote(row['purpose_code'])}, {sql_quote(row['run_id'])}, "
        "CURRENT_TIMESTAMP()"
        ")"
    )


def _need_query(query_rows: QueryFn | None) -> QueryFn:
    if query_rows is not None:
        return query_rows
    from iceberg_mcp_server_claims.tools.impala_tools import query_rows as _qr

    return _qr


def _need_dml(execute_dml: DmlFn | None) -> DmlFn:
    if execute_dml is not None:
        return execute_dml
    from iceberg_mcp_server_claims.tools.impala_tools import execute_dml as _dml

    return _dml


def create_pd_task(
    run_id: str,
    event_json: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
    execute_dml: DmlFn | None = None,
) -> str:
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
                "error": "event_json.task_type_code must be COLLECT_INCIDENT_NUMBER, "
                "REQUEST_POLICE_REPORT, DETERMINE_FAULT, or PD_REVIEW",
            }
        )

    cid = int(claim_id)
    incident = None
    sms_body = None
    to_phone = None

    if task_type == "REQUEST_POLICE_REPORT":
        qr = _need_query(query_rows)
        try:
            police_rows = qr(police_report_count_sql(db, cid))
        except Exception as exc:
            return json.dumps({"error": str(exc), "run_id": rid, "database": db})
        police_cnt = 0
        if police_rows:
            try:
                police_cnt = int(police_rows[0].get("cnt") or 0)
            except (TypeError, ValueError):
                police_cnt = 0
        if police_cnt > 0:
            return json.dumps(
                {
                    "error": "police_report already on file; do not REQUEST_POLICE_REPORT. "
                    "Re-run structured claim intake (expect DetermineFault).",
                    "run_id": rid,
                    "database": db,
                    "claim_id": cid,
                    "has_police_report": True,
                }
            )
        try:
            intake_rows = qr(intake_incident_number_sql(db, cid))
        except Exception as exc:
            return json.dumps({"error": str(exc), "run_id": rid, "database": db})
        incident = (intake_rows[0].get("incident_report_number") if intake_rows else None)
        if isinstance(incident, str):
            incident = incident.strip()
        if not incident:
            return json.dumps(
                {
                    "error": "incident_report_number is required on claim_police_intake "
                    "before REQUEST_POLICE_REPORT",
                    "run_id": rid,
                    "database": db,
                    "claim_id": cid,
                }
            )

    row = {
        "pd_task_id": _task_id(rid, str(claim_id), task_type),
        "claim_id": cid,
        "loss_event_id": body.get("loss_event_id"),
        "task_type_code": task_type,
        "task_status_code": "OPEN",
        "due_date": body.get("due_date"),
        "incident_report_number": incident,
        "run_id": rid,
    }
    dml = _need_dml(execute_dml)
    sql = insert_pd_task_sql(db, row)
    result = dml(sql)
    if isinstance(result, str) and result.startswith("Error:"):
        return json.dumps({"error": result, "run_id": rid, "database": db})

    if task_type == "COLLECT_INCIDENT_NUMBER":
        try:
            phone_rows = _need_query(query_rows)(insured_phone_sql(db, cid))
        except Exception as exc:
            return json.dumps({"error": str(exc), "run_id": rid, "database": db})
        to_phone = phone_rows[0].get("phone_number") if phone_rows else None
        sms_body = _SMS_BODY
        msg = {
            "message_id": _message_id(rid, str(claim_id), _SMS_PURPOSE),
            "claim_id": cid,
            "channel_code": "SMS",
            "to_phone": to_phone,
            "body_text": sms_body,
            "purpose_code": _SMS_PURPOSE,
            "run_id": rid,
        }
        sms_sql = insert_outbound_message_sql(db, msg)
        sms_result = dml(sms_sql)
        if isinstance(sms_result, str) and sms_result.startswith("Error:"):
            return json.dumps(
                {
                    "ok": False,
                    "error": sms_result,
                    "run_id": rid,
                    "database": db,
                    "table": "pd_task",
                    "pd_task_id": row["pd_task_id"],
                    "sms_written": False,
                }
            )

    step = _TASK_TO_STEP[task_type]
    payload_json: dict[str, Any] = {
        "pd_task_id": row["pd_task_id"],
        "task_type_code": task_type,
        "task_status_code": "OPEN",
    }
    if incident:
        payload_json["incident_report_number"] = incident
    if task_type == "COLLECT_INCIDENT_NUMBER":
        payload_json["channel_code"] = "SMS"
        payload_json["to_phone"] = to_phone
    audit_event = {
        "run_id": rid,
        "claim_id": str(claim_id),
        "event_type": step,
        "next_step": step,
        "agent_role": "PdClaimsAgent",
        "lane": "PD",
        "terminal": False,
        "payload_json": payload_json,
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
                "table": "pd_task",
                "pd_task_id": row["pd_task_id"],
                "audit_written": False,
            }
        )
    out: dict[str, Any] = {
        "ok": True,
        "run_id": rid,
        "database": db,
        "table": "pd_task",
        "audit_table": "agent_run_audit",
        "pd_task_id": row["pd_task_id"],
        "claim_id": row["claim_id"],
        "task_type_code": task_type,
        "task_status_code": "OPEN",
        "next_step": step,
    }
    if incident:
        out["incident_report_number"] = incident
    if task_type == "COLLECT_INCIDENT_NUMBER":
        out["sms_table"] = "claim_outbound_message"
        out["sms_body"] = sms_body
        out["to_phone"] = to_phone
        out["channel_code"] = "SMS"
    return json.dumps(out)

