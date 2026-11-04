"""Submission named reads (spine, routing signals, senior UW context)."""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from iceberg_mcp_server_underwriting.tools import sql as uw_sql

QueryFn = Callable[[str], list[dict[str, Any]]]


def _default_database(database: str | None) -> str:
    return database or os.getenv("IMPALA_DATABASE", "underwriting")


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "submission_id": row.get("submission_id"),
        "line_of_business": row.get("line_of_business") or "",
        "class_code": str(row.get("class_code") or ""),
        "total_insured_value": _as_int(row.get("total_insured_value")),
        "submission_status_code": row.get("submission_status_code") or "",
        "is_in_flood_plain": bool(uw_sql.coerce_bool(row.get("is_in_flood_plain"))),
        "inspection_completed": bool(uw_sql.coerce_bool(row.get("inspection_completed"))),
        "flood_zone": row.get("flood_zone") or "",
        "prior_claims_count": _as_int(row.get("prior_claims_count")),
        "has_open_loss_past_36m": bool(
            uw_sql.coerce_bool(row.get("has_open_loss_past_36m"))
        ),
        "financial_stability_tier": str(row.get("financial_stability_tier") or ""),
        "has_underwriter": bool(uw_sql.coerce_bool(row.get("has_underwriter"))),
    }


def load_snapshot(
    submission_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> tuple[str, dict[str, Any] | None, str | None]:
    """Return (database, snapshot or None, error or None)."""
    from iceberg_mcp_server_underwriting.tools.impala_tools import query_rows as _qr

    qr = query_rows or _qr
    try:
        sid = uw_sql.validate_submission_id(submission_id)
        db = uw_sql.validate_ident(_default_database(database), "database")
        rows = qr(uw_sql.submission_snapshot_sql(sid, db))
    except Exception as exc:
        return _default_database(database), None, str(exc)
    if not rows:
        return db, None, f"Submission {sid} not found"
    snap = _snapshot(rows[0])
    snap["submission_id"] = sid
    return db, snap, None


def get_submission_spine(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    from iceberg_mcp_server_underwriting.tools.impala_tools import query_rows as _qr

    qr = query_rows or _qr
    try:
        sid = uw_sql.validate_submission_id(claim_id)
        db = uw_sql.validate_ident(_default_database(database), "database")
        rows = qr(uw_sql.submission_spine_sql(sid, db))
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": str(claim_id)})
    if not rows:
        return json.dumps(
            {"error": f"Submission {sid} not found", "claim_id": sid, "database": db}
        )
    row = rows[0]
    return json.dumps(
        {
            "claim_id": sid,
            "case_id": sid,
            "submission_id": sid,
            "database": db,
            "spine": {
                "producer_id": row.get("producer_id"),
                "applicant_tax_id": row.get("applicant_tax_id"),
                "line_of_business": row.get("line_of_business"),
                "class_code": str(row.get("class_code") or ""),
                "total_insured_value": _as_int(row.get("total_insured_value")),
                "submission_status_code": row.get("submission_status_code"),
            },
        },
        default=str,
    )


def get_submission_routing_signals(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    db, snap, err = load_snapshot(claim_id, database, query_rows=query_rows)
    if err or snap is None:
        return json.dumps({"error": err, "claim_id": str(claim_id), "database": db})
    sid = snap["submission_id"]
    return json.dumps(
        {
            "claim_id": sid,
            "case_id": sid,
            "submission_id": sid,
            "database": db,
            "signals": {
                "is_in_flood_plain": snap["is_in_flood_plain"],
                "has_open_loss_past_36m": snap["has_open_loss_past_36m"],
                "prior_claims_count": snap["prior_claims_count"],
                "financial_stability_tier": snap["financial_stability_tier"],
                "inspection_completed": snap["inspection_completed"],
                "has_underwriter": snap["has_underwriter"],
            },
        }
    )


def get_senior_uw_referral_context(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    db, snap, err = load_snapshot(claim_id, database, query_rows=query_rows)
    if err or snap is None:
        return json.dumps({"error": err, "claim_id": str(claim_id), "database": db})
    sid = snap["submission_id"]
    return json.dumps(
        {
            "claim_id": sid,
            "case_id": sid,
            "submission_id": sid,
            "database": db,
            "referral": {
                "line_of_business": snap["line_of_business"],
                "class_code": snap["class_code"],
                "total_insured_value": snap["total_insured_value"],
                "is_in_flood_plain": snap["is_in_flood_plain"],
                "flood_zone": snap["flood_zone"],
                "prior_claims_count": snap["prior_claims_count"],
                "inspection_completed": snap["inspection_completed"],
                "financial_stability_tier": snap["financial_stability_tier"],
            },
        }
    )


def list_underwriter_open_submissions(
    party_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    """Return non-terminal submissions currently assigned to an underwriter."""
    from iceberg_mcp_server_underwriting.tools.impala_tools import query_rows as _qr

    qr = query_rows or _qr
    try:
        pid = int(party_id)
    except (TypeError, ValueError) as exc:
        return json.dumps({"error": f"invalid party_id: {exc}", "party_id": party_id})
    try:
        db = uw_sql.validate_ident(_default_database(database), "database")
        rows = qr(uw_sql.list_underwriter_open_submissions_sql(pid, db))
    except Exception as exc:
        return json.dumps({"error": str(exc), "party_id": pid, "database": database})
    submissions = [
        {
            "submission_id": r.get("submission_id"),
            "line_of_business": r.get("line_of_business"),
            "submission_status_code": r.get("submission_status_code"),
        }
        for r in rows
    ]
    first = rows[0] if rows else {}
    parts = [
        str(p).strip()
        for p in (first.get("first_name"), first.get("last_name"))
        if p not in (None, "")
    ]
    return json.dumps(
        {
            "party_id": pid,
            "underwriter_name": " ".join(parts) if parts else None,
            "database": db,
            "submissions": submissions,
        },
        default=str,
    )
