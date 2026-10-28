"""Named writes: deny_fnol, close_fnol_incident_only, convert_fnol_to_claim, review_fnol."""

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
from iceberg_mcp_server_claims.tools.claim_sql import (
    fnol_converted_claim_id,
    fnol_matching_coverage_sql,
    fnol_status_sql,
    insert_converted_claim_sql,
    insert_converted_reserve_sql,
    parse_fnol_id,
    update_fnol_status_sql,
    validate_ident,
)


QueryFn = Callable[[str], list[dict[str, Any]]]
DmlFn = Callable[[str], str]

_DENY_STEPS = frozenset({"DenyFnolNoCoverage", "DenyFnolExcludedPeril"})
_CLOSE_STEPS = frozenset({"ConvertFnolToIncidentOnly"})
_CONVERT_STEPS = frozenset({"ConvertFnolToClaim"})
_REVIEW_STEPS = frozenset({"FnolAdjusterReview"})


def _default_database(database: str | None) -> str:
    return database or os.getenv("IMPALA_DATABASE", "car_insurance_claims")


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


def _fnol_id_from_body(body: dict[str, Any]) -> str | None:
    raw = body.get("fnol_id")
    if raw in (None, ""):
        raw = body.get("claim_id")
    if raw in (None, ""):
        return None
    return str(raw)


def _load_fnol(
    qr: QueryFn, db: str, fnol_id: str, rid: str
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        fid = parse_fnol_id(fnol_id)
    except (TypeError, ValueError) as exc:
        return None, json.dumps({"error": f"invalid fnol_id: {exc}", "run_id": rid})
    try:
        rows = qr(fnol_status_sql(fid, db))
    except Exception as exc:
        return None, json.dumps(
            {"error": str(exc), "run_id": rid, "database": db, "fnol_id": fid}
        )
    if not rows:
        return None, json.dumps(
            {
                "error": f"FNOL {fid} not found",
                "run_id": rid,
                "database": db,
                "fnol_id": fid,
            }
        )
    return rows[0], None


def _audit_and_ok(
    dml: DmlFn,
    db: str,
    rid: str,
    event: dict[str, Any],
    payload: dict[str, Any],
) -> str:
    audit_sql = insert_audit_event_sql(db, event)
    audit_result = dml(audit_sql)
    if isinstance(audit_result, str) and audit_result.startswith("Error:"):
        payload["ok"] = False
        payload["error"] = audit_result
        payload["audit_written"] = False
        return json.dumps(payload)
    payload["ok"] = True
    payload["audit_table"] = "agent_run_audit"
    payload["audit_written"] = True
    return json.dumps(payload)


def _stamp_status(
    *,
    run_id: str,
    event_json: str,
    database: str | None,
    allowed_steps: frozenset[str],
    status: str,
    table: str,
    agent_role: str,
    lane: str,
    terminal: bool,
    query_rows: QueryFn | None = None,
    execute_dml: DmlFn | None = None,
) -> str:
    qr = _need_query(query_rows)
    dml = _need_dml(execute_dml)
    try:
        rid = validate_run_id(run_id)
        db = validate_ident(_default_database(database), "database")
        body = _parse_json_arg(event_json, "event_json")
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    raw_id = _fnol_id_from_body(body)
    next_step = str(body.get("next_step") or "").strip()
    if raw_id is None:
        return json.dumps({"error": "event_json.fnol_id is required"})
    if next_step not in allowed_steps:
        return json.dumps(
            {
                "error": "event_json.next_step must be "
                + ", ".join(sorted(allowed_steps)),
            }
        )

    row, err = _load_fnol(qr, db, raw_id, rid)
    if err:
        return err
    fid = int(row["fnol_id"])
    current = str(row.get("triage_status_code") or "").upper()
    already = current == status
    if not already:
        result = dml(update_fnol_status_sql(db, fid, status))
        if isinstance(result, str) and result.startswith("Error:"):
            return json.dumps(
                {"error": result, "run_id": rid, "database": db, "fnol_id": fid}
            )

    payload = {
        "run_id": rid,
        "database": db,
        "table": table,
        "fnol_id": fid,
        "triage_status_code": status,
        "next_step": next_step,
        "agent_role": agent_role,
        "lane": lane,
        "terminal": terminal,
        "already_applied": already,
    }
    return _audit_and_ok(
        dml,
        db,
        rid,
        {
            "run_id": rid,
            "claim_id": str(fid),
            "event_type": next_step,
            "next_step": next_step,
            "agent_role": agent_role,
            "lane": lane,
            "terminal": terminal,
            "payload_json": {
                "fnol_id": fid,
                "triage_status_code": status,
                "next_step": next_step,
            },
        },
        payload,
    )


def deny_fnol(
    run_id: str,
    event_json: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
    execute_dml: DmlFn | None = None,
) -> str:
    return _stamp_status(
        run_id=run_id,
        event_json=event_json,
        database=database,
        allowed_steps=_DENY_STEPS,
        status="DENIED",
        table="fnol",
        agent_role="DenyAgent",
        lane="DENY",
        terminal=True,
        query_rows=query_rows,
        execute_dml=execute_dml,
    )


def close_fnol_incident_only(
    run_id: str,
    event_json: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
    execute_dml: DmlFn | None = None,
) -> str:
    return _stamp_status(
        run_id=run_id,
        event_json=event_json,
        database=database,
        allowed_steps=_CLOSE_STEPS,
        status="INCIDENT_ONLY",
        table="fnol",
        agent_role="FnolAgent",
        lane="FNOL",
        terminal=True,
        query_rows=query_rows,
        execute_dml=execute_dml,
    )


def review_fnol(
    run_id: str,
    event_json: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
    execute_dml: DmlFn | None = None,
) -> str:
    return _stamp_status(
        run_id=run_id,
        event_json=event_json,
        database=database,
        allowed_steps=_REVIEW_STEPS,
        status="ADJUSTER_REVIEW",
        table="fnol",
        agent_role="HumanReviewAgent",
        lane="GENERAL",
        terminal=True,
        query_rows=query_rows,
        execute_dml=execute_dml,
    )


def _reserve_id(run_id: str, claim_id: int) -> int:
    digest = hashlib.sha256(f"{run_id}:{claim_id}:fnol_reserve".encode()).hexdigest()
    return int(digest[:15], 16)


def convert_fnol_to_claim(
    run_id: str,
    event_json: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
    execute_dml: DmlFn | None = None,
) -> str:
    qr = _need_query(query_rows)
    dml = _need_dml(execute_dml)
    try:
        rid = validate_run_id(run_id)
        db = validate_ident(_default_database(database), "database")
        body = _parse_json_arg(event_json, "event_json")
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    raw_id = _fnol_id_from_body(body)
    next_step = str(body.get("next_step") or "").strip()
    if raw_id is None:
        return json.dumps({"error": "event_json.fnol_id is required"})
    if next_step not in _CONVERT_STEPS:
        return json.dumps({"error": "event_json.next_step must be ConvertFnolToClaim"})

    row, err = _load_fnol(qr, db, raw_id, rid)
    if err:
        return err
    fid = int(row["fnol_id"])
    existing = row.get("claim_id")
    if existing not in (None, ""):
        cid = int(existing)
        payload = {
            "run_id": rid,
            "database": db,
            "table": "claim",
            "fnol_id": fid,
            "claim_id": cid,
            "triage_status_code": "CONVERTED",
            "next_step": next_step,
            "agent_role": "FnolAgent",
            "lane": "FNOL",
            "terminal": True,
            "already_applied": True,
        }
        return _audit_and_ok(
            dml,
            db,
            rid,
            {
                "run_id": rid,
                "claim_id": str(cid),
                "event_type": next_step,
                "next_step": next_step,
                "agent_role": "FnolAgent",
                "lane": "FNOL",
                "terminal": True,
                "payload_json": {
                    "fnol_id": fid,
                    "claim_id": cid,
                    "already_applied": True,
                },
            },
            payload,
        )

    cid = fnol_converted_claim_id(fid)
    policy_id = row.get("policy_id")
    if policy_id in (None, ""):
        return json.dumps(
            {"error": f"FNOL {fid} has no policy_id", "run_id": rid, "fnol_id": fid}
        )
    cov_rows = qr(fnol_matching_coverage_sql(fid, db))
    cov = cov_rows[0] if cov_rows else {}
    amount = row.get("estimated_loss_amount")
    claim_row = {
        "claim_id": cid,
        "claim_number": f"CLM-2026-{cid}",
        "loss_event_id": row.get("loss_event_id"),
        "policy_id": int(policy_id),
        "insurable_object_id": row.get("insurable_object_id"),
        "policy_coverage_id": cov.get("policy_coverage_id"),
    }
    result = dml(insert_converted_claim_sql(db, claim_row))
    if isinstance(result, str) and result.startswith("Error:"):
        return json.dumps(
            {"error": result, "run_id": rid, "database": db, "fnol_id": fid}
        )
    reserve_written = False
    if amount not in (None, "") and cov.get("policy_coverage_id") not in (None, ""):
        reserve_result = dml(
            insert_converted_reserve_sql(
                db,
                {
                    "claim_reserve_id": _reserve_id(rid, cid),
                    "claim_id": cid,
                    "amount": amount,
                },
            )
        )
        if isinstance(reserve_result, str) and reserve_result.startswith("Error:"):
            return json.dumps(
                {
                    "ok": False,
                    "error": reserve_result,
                    "run_id": rid,
                    "database": db,
                    "fnol_id": fid,
                    "claim_id": cid,
                    "reserve_written": False,
                }
            )
        reserve_written = True

    stamp = dml(update_fnol_status_sql(db, fid, "CONVERTED", claim_id=cid))
    if isinstance(stamp, str) and stamp.startswith("Error:"):
        return json.dumps(
            {
                "ok": False,
                "error": stamp,
                "run_id": rid,
                "database": db,
                "fnol_id": fid,
                "claim_id": cid,
            }
        )

    payload = {
        "run_id": rid,
        "database": db,
        "table": "claim",
        "fnol_id": fid,
        "claim_id": cid,
        "triage_status_code": "CONVERTED",
        "reserve_written": reserve_written,
        "next_step": next_step,
        "agent_role": "FnolAgent",
        "lane": "FNOL",
        "terminal": True,
        "already_applied": False,
    }
    return _audit_and_ok(
        dml,
        db,
        rid,
        {
            "run_id": rid,
            "claim_id": str(cid),
            "event_type": next_step,
            "next_step": next_step,
            "agent_role": "FnolAgent",
            "lane": "FNOL",
            "terminal": True,
            "payload_json": {
                "fnol_id": fid,
                "claim_id": cid,
                "triage_status_code": "CONVERTED",
                "reserve_written": reserve_written,
            },
        },
        payload,
    )
