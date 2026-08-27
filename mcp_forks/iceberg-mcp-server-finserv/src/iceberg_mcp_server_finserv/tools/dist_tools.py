"""Distribution named reads (spine, signals, exception view, RMD view)."""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from iceberg_mcp_server_finserv.tools import sql as dist_sql

QueryFn = Callable[[str], list[dict[str, Any]]]


def _default_database(database: str | None) -> str:
    return database or os.getenv("IMPALA_DATABASE", "retirement_distributions")


def _cid(claim_id: str) -> str:
    return str(int(claim_id))


def _as_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_required_docs(raw: Any) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    text = str(raw).strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            pass
    return [part.strip() for part in text.split(",") if part.strip()]


def get_distribution_spine(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    from iceberg_mcp_server_finserv.tools.impala_tools import query_rows as _qr

    qr = query_rows or _qr
    db = dist_sql.validate_ident(_default_database(database), "database")
    cid = _cid(claim_id)
    try:
        rows = qr(dist_sql.distribution_spine_sql(cid, db))
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    if not rows:
        return json.dumps(
            {"error": f"Distribution request {cid} not found", "claim_id": cid, "database": db}
        )
    row = rows[0]
    return json.dumps(
        {
            "claim_id": cid,
            "case_id": cid,
            "database": db,
            "spine": {
                "request_status_code": row.get("request_status_code"),
                "distribution_type_code": row.get("distribution_type_code"),
                "plan_id": row.get("plan_id"),
                "participant_id": row.get("participant_id"),
                "requested_amount": _as_float(row.get("requested_amount")),
            },
        },
        default=str,
    )


def get_distribution_routing_signals(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    from iceberg_mcp_server_finserv.tools.impala_tools import query_rows as _qr

    qr = query_rows or _qr
    db = dist_sql.validate_ident(_default_database(database), "database")
    cid = _cid(claim_id)
    try:
        rows = qr(dist_sql.distribution_routing_signals_sql(cid, db))
        exception_rows = qr(dist_sql.distribution_exception_view_sql(cid, db))
        rmd_rows = qr(dist_sql.distribution_rmd_view_sql(cid, db))
        court_rows = qr(dist_sql.distribution_court_orders_sql(cid, db))
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    row = rows[0] if rows else {}
    shortfall = _as_float(rmd_rows[0].get("shortfall_amount") if rmd_rows else 0)
    return json.dumps(
        {
            "claim_id": cid,
            "case_id": cid,
            "database": db,
            "signals": {
                "hold_or_aml_flag": bool(dist_sql.coerce_bool(row.get("hold_or_aml_flag"))),
                "hardship_reason_codes": [
                    r.get("reason_code")
                    for r in exception_rows
                    if r.get("reason_code") not in (None, "")
                ],
                "rmd_shortfall_amount": shortfall,
                "requested_amount": _as_float(row.get("requested_amount")),
                "hardship_category": row.get("hardship_category") or "",
                "documented_financial_need_amount": _as_float(
                    row.get("documented_financial_need_amount")
                ),
                "estimated_tax_withholding_amount": _as_float(
                    row.get("estimated_tax_withholding_amount")
                ),
                "has_participant_self_certified": bool(
                    dist_sql.coerce_bool(row.get("has_participant_self_certified"))
                ),
                "requires_substantiation_audit": bool(
                    dist_sql.coerce_bool(row.get("requires_substantiation_audit"))
                ),
                "plan_subject_to_qjsa": bool(
                    dist_sql.coerce_bool(row.get("plan_subject_to_qjsa"))
                ),
                "plan_mandates_loan_exhaustion": bool(
                    dist_sql.coerce_bool(row.get("plan_mandates_loan_exhaustion"))
                ),
                "participant_marital_status": row.get("participant_marital_status") or "",
                "spousal_consent_verified": bool(
                    dist_sql.coerce_bool(row.get("spousal_consent_verified"))
                ),
                "available_plan_loan_capacity": _as_float(
                    row.get("available_plan_loan_capacity")
                ),
                "has_active_qdro_hold": bool(
                    dist_sql.coerce_bool(row.get("has_active_qdro_hold"))
                ),
                "prior_emergency_distributions_this_year": _as_int(
                    row.get("prior_emergency_distributions_this_year")
                ),
                "pending_court_orders": [
                    {
                        "court_order_id": c.get("court_order_id"),
                        "docket_number": c.get("docket_number"),
                    }
                    for c in court_rows
                ],
            },
        },
        default=str,
    )


def get_distribution_exception_view(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    from iceberg_mcp_server_finserv.tools.impala_tools import query_rows as _qr

    qr = query_rows or _qr
    db = dist_sql.validate_ident(_default_database(database), "database")
    cid = _cid(claim_id)
    try:
        rows = qr(dist_sql.distribution_exception_view_sql(cid, db))
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    exceptions = [
        {
            "exception_id": r.get("exception_id"),
            "reason_code": r.get("reason_code"),
            "queue": r.get("queue"),
            "required_docs": _parse_required_docs(r.get("required_docs")),
        }
        for r in rows
    ]
    return json.dumps(
        {
            "claim_id": cid,
            "case_id": cid,
            "database": db,
            "exceptions": exceptions,
        },
        default=str,
    )


def get_rmd_view(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    from iceberg_mcp_server_finserv.tools.impala_tools import query_rows as _qr

    qr = query_rows or _qr
    db = dist_sql.validate_ident(_default_database(database), "database")
    cid = _cid(claim_id)
    try:
        rows = qr(dist_sql.distribution_rmd_view_sql(cid, db))
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    rmd = None
    if rows:
        row = rows[0]
        rmd = {
            "tax_year": row.get("tax_year"),
            "required_amount": row.get("required_amount"),
            "paid_amount": row.get("paid_amount"),
            "shortfall_amount": row.get("shortfall_amount"),
            "deadline": row.get("deadline"),
        }
    return json.dumps(
        {
            "claim_id": cid,
            "case_id": cid,
            "database": db,
            "rmd": rmd,
        },
        default=str,
    )


def get_compliance_view(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    from iceberg_mcp_server_finserv.tools.impala_tools import query_rows as _qr

    qr = query_rows or _qr
    db = dist_sql.validate_ident(_default_database(database), "database")
    cid = _cid(claim_id)
    try:
        rows = qr(dist_sql.distribution_compliance_view_sql(cid, db))
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    row = rows[0] if rows else {}
    return json.dumps(
        {
            "claim_id": cid,
            "case_id": cid,
            "database": db,
            "compliance": {
                "plan_id": row.get("plan_id"),
                "participant_id": row.get("participant_id"),
                "plan_subject_to_qjsa": bool(
                    dist_sql.coerce_bool(row.get("plan_subject_to_qjsa"))
                ),
                "plan_mandates_loan_exhaustion": bool(
                    dist_sql.coerce_bool(row.get("plan_mandates_loan_exhaustion"))
                ),
                "participant_marital_status": row.get("participant_marital_status"),
                "spousal_consent_verified": bool(
                    dist_sql.coerce_bool(row.get("spousal_consent_verified"))
                ),
            },
        },
        default=str,
    )


def get_loan_summary_view(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    from iceberg_mcp_server_finserv.tools.impala_tools import query_rows as _qr

    qr = query_rows or _qr
    db = dist_sql.validate_ident(_default_database(database), "database")
    cid = _cid(claim_id)
    try:
        rows = qr(dist_sql.distribution_loan_summary_view_sql(cid, db))
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    loan = None
    if rows:
        row = rows[0]
        loan = {
            "available_plan_loan_capacity": _as_float(row.get("available_plan_loan_capacity")),
            "outstanding_loan_balance": _as_float(row.get("outstanding_loan_balance")),
            "max_loan_amount": _as_float(row.get("max_loan_amount")),
        }
    return json.dumps(
        {
            "claim_id": cid,
            "case_id": cid,
            "database": db,
            "loan": loan,
        },
        default=str,
    )


def get_qdro_details_view(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    from iceberg_mcp_server_finserv.tools.impala_tools import query_rows as _qr

    qr = query_rows or _qr
    db = dist_sql.validate_ident(_default_database(database), "database")
    cid = _cid(claim_id)
    try:
        qdro_rows = qr(dist_sql.distribution_qdro_details_view_sql(cid, db))
        court_rows = qr(dist_sql.distribution_court_orders_sql(cid, db))
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    qdro = [
        {
            "qdro_id": r.get("qdro_id"),
            "is_active": bool(dist_sql.coerce_bool(r.get("is_active"))),
            "order_status_code": r.get("order_status_code"),
            "alternate_payee_name": r.get("alternate_payee_name"),
            "hold_reason": r.get("hold_reason"),
        }
        for r in qdro_rows
    ]
    return json.dumps(
        {
            "claim_id": cid,
            "case_id": cid,
            "database": db,
            "qdro": qdro,
            "pending_court_orders": [
                {
                    "court_order_id": c.get("court_order_id"),
                    "docket_number": c.get("docket_number"),
                }
                for c in court_rows
            ],
        },
        default=str,
    )
