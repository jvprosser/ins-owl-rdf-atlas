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
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    row = rows[0] if rows else {}
    shortfall = 0
    if rmd_rows:
        raw_short = rmd_rows[0].get("shortfall_amount")
        try:
            shortfall = float(raw_short or 0)
        except (TypeError, ValueError):
            shortfall = 0
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
