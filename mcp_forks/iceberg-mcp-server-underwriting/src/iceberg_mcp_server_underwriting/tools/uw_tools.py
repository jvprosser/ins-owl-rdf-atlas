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
        "naics_code": str(row.get("naics_code") or ""),
        "total_insured_value": _as_int(row.get("total_insured_value")),
        "submission_status_code": row.get("submission_status_code") or "",
        "has_ofac_match": bool(uw_sql.coerce_bool(row.get("has_ofac_match"))),
        "siu_score": _as_int(row.get("siu_score")),
        "tax_lien_unresolved": bool(uw_sql.coerce_bool(row.get("tax_lien_unresolved"))),
        "is_in_flood_plain": bool(uw_sql.coerce_bool(row.get("is_in_flood_plain"))),
        "inspection_completed": bool(uw_sql.coerce_bool(row.get("inspection_completed"))),
        "flood_zone": row.get("flood_zone") or "",
        "has_survey_on_file": bool(uw_sql.coerce_bool(row.get("has_survey_on_file"))),
        "survey_age_months": _as_int(row.get("survey_age_months")),
        "wind_tier": _as_int(row.get("wind_tier")),
        "has_recent_cat_run": bool(uw_sql.coerce_bool(row.get("has_recent_cat_run"))),
        "construction_type": str(row.get("construction_type") or ""),
        "year_built": _as_int(row.get("year_built")),
        "wiring_updated": bool(uw_sql.coerce_bool(row.get("wiring_updated"))),
        "protection_class": str(row.get("protection_class") or ""),
        "has_sprinklers": bool(uw_sql.coerce_bool(row.get("has_sprinklers"))),
        "square_footage": _as_int(row.get("square_footage")),
        "prior_claims_count": _as_int(row.get("prior_claims_count")),
        "claims_count_36m": _as_int(row.get("claims_count_36m")),
        "total_incurred_36m": _as_int(row.get("total_incurred_36m")),
        "has_open_loss_past_36m": bool(
            uw_sql.coerce_bool(row.get("has_open_loss_past_36m"))
        ),
        "financial_stability_tier": str(row.get("financial_stability_tier") or ""),
        "financial_score": _as_int(row.get("financial_score")),
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
                "naics_code": str(row.get("naics_code") or ""),
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
                "naics_code": snap["naics_code"],
                "has_ofac_match": snap["has_ofac_match"],
                "siu_score": snap["siu_score"],
                "tax_lien_unresolved": snap["tax_lien_unresolved"],
                "is_in_flood_plain": snap["is_in_flood_plain"],
                "has_open_loss_past_36m": snap["has_open_loss_past_36m"],
                "prior_claims_count": snap["prior_claims_count"],
                "claims_count_36m": snap["claims_count_36m"],
                "total_incurred_36m": snap["total_incurred_36m"],
                "financial_stability_tier": snap["financial_stability_tier"],
                "financial_score": snap["financial_score"],
                "inspection_completed": snap["inspection_completed"],
                "flood_zone": snap["flood_zone"],
                "has_survey_on_file": snap["has_survey_on_file"],
                "survey_age_months": snap["survey_age_months"],
                "wind_tier": snap["wind_tier"],
                "has_recent_cat_run": snap["has_recent_cat_run"],
                "construction_type": snap["construction_type"],
                "year_built": snap["year_built"],
                "wiring_updated": snap["wiring_updated"],
                "protection_class": snap["protection_class"],
                "has_sprinklers": snap["has_sprinklers"],
                "square_footage": snap["square_footage"],
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


def list_low_confidence_fields(
    claim_id: str,
    database: str | None = None,
    *,
    min_confidence_score: Any = None,
    query_rows: QueryFn | None = None,
) -> str:
    """Return document fields that contain a word below min_confidence_score."""
    from iceberg_mcp_server_underwriting.tools.impala_tools import query_rows as _qr

    qr = query_rows or _qr
    try:
        sid = uw_sql.validate_submission_id(claim_id)
        score = uw_sql.validate_min_confidence(min_confidence_score)
        db = uw_sql.validate_ident(_default_database(database), "database")
        rows = qr(uw_sql.list_low_confidence_fields_sql(sid, db, score))
    except Exception as exc:
        return json.dumps(
            {
                "error": str(exc),
                "claim_id": str(claim_id),
                "min_confidence_score": min_confidence_score,
            }
        )
    fields = [
        {
            "document_id": r.get("document_id"),
            "page_index": r.get("page_index"),
            "word_text": r.get("word_text"),
            "confidence": r.get("confidence"),
            "field_path": r.get("field_path"),
            "field_value": r.get("field_value"),
        }
        for r in rows
    ]
    return json.dumps(
        {
            "claim_id": sid,
            "case_id": sid,
            "submission_id": sid,
            "database": db,
            "min_confidence_score": score,
            "fields": fields,
        },
        default=str,
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
