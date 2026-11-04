"""Governed underwriting writes. Premium and reason codes are not LLM arguments."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from iceberg_mcp_server_underwriting.tools.audit_tools import (
    _parse_json_arg,
    insert_audit_event_sql,
    validate_run_id,
)
from iceberg_mcp_server_underwriting.tools.sql import (
    insert_decline_sql,
    insert_enrichment_sql,
    insert_quote_sql,
    insert_referral_sql,
)
from iceberg_mcp_server_underwriting.tools.uw_tools import load_snapshot

QueryFn = Callable[[str], list[dict[str, Any]]]
DmlFn = Callable[[str], str]

PLAYBOOK_VERSION = "1.0.0"

PROBE_CEL = {
    "P0_OUT_OF_APPETITE": (
        '["4812", "5921"].exists(c, c == class_code) || total_insured_value > 25000000'
    ),
    "P1_AWAITING_INSPECTION": (
        "total_insured_value > 2000000 && inspection_completed == false"
    ),
    "P2_SENIOR_UW_ESCALATION": (
        "is_in_flood_plain == true || prior_claims_count >= 3"
    ),
    "P3_STRAIGHT_THROUGH_BIND": (
        "is_in_flood_plain == false && prior_claims_count == 0.0"
    ),
}

_DECLINE_REASONS = frozenset({"OUT_OF_APPETITE"})
_PROVIDERS = frozenset({"INSPECTION"})
_PRICE_KEYS = frozenset({"premium_cents", "rating_tier"})

# Cents of premium per $100 of total insured value. Catalog-owned.
_RATE_CENTS_PER_100 = {"A": 15, "B": 25, "C": 40}
_DEFAULT_RATE_CENTS = 30

_META = {
    "P0_OUT_OF_APPETITE": {
        "next_step": "DECLINE_UNINSURABLE",
        "agent_role": "UnderwritingIntakeSpecialist",
        "lane": "DECLINE",
        "terminal": True,
    },
    "P1_AWAITING_INSPECTION": {
        "next_step": "TRIGGER_SURVEY",
        "agent_role": "RiskEngineeringSpecialist",
        "lane": "ENRICHMENT",
        "terminal": False,
    },
    "P2_SENIOR_UW_ESCALATION": {
        "next_step": "REFER_TO_SENIOR_UW",
        "agent_role": "SeniorUnderwriter",
        "lane": "REFERRAL",
        "terminal": False,
    },
    "P3_STRAIGHT_THROUGH_BIND": {
        "next_step": "AUTO_RATE_AND_BIND",
        "agent_role": "RatingSpecialist",
        "lane": "BIND",
        "terminal": True,
    },
}


def rate_quote(total_insured_value: int, financial_stability_tier: str | None) -> tuple[str, int]:
    """Return (rating_tier, premium_cents) from the fixed table."""
    tier = (financial_stability_tier or "").strip().upper()
    if tier in _RATE_CENTS_PER_100:
        rating_tier = tier
        rate = _RATE_CENTS_PER_100[tier]
    else:
        rating_tier = "STANDARD"
        rate = _DEFAULT_RATE_CENTS
    tiv = int(total_insured_value)
    if tiv < 0:
        raise ValueError("total_insured_value must be >= 0")
    return rating_tier, (tiv * rate) // 100


def _row_id(run_id: str, submission_id: str, kind: str) -> str:
    digest = hashlib.sha256(f"{run_id}:{submission_id}:{kind}".encode()).hexdigest()
    return digest[:16]


def _need_dml(execute_dml: DmlFn | None) -> DmlFn:
    if execute_dml is not None:
        return execute_dml
    from iceberg_mcp_server_underwriting.tools.impala_tools import execute_dml as _dml

    return _dml


def _error(message: str, **extra: Any) -> str:
    return json.dumps({"error": message, **extra})


def _governed(
    run_id: str,
    event_json: str,
    *,
    probe_id: str,
    database: str | None,
    query_rows: QueryFn | None,
) -> tuple[str, str, dict[str, Any], dict[str, Any]] | str:
    try:
        rid = validate_run_id(run_id)
        body = _parse_json_arg(event_json, "event_json")
    except ValueError as exc:
        return _error(str(exc))

    claim_id = body.get("claim_id") or body.get("submission_id")
    if claim_id in (None, ""):
        return _error("event_json.claim_id is required")
    if str(body.get("playbook_version") or "").strip() != PLAYBOOK_VERSION:
        return _error(f"playbook_version must be {PLAYBOOK_VERSION}")
    if str(body.get("probe_id") or "").strip() != probe_id:
        return _error(f"probe_id must be {probe_id}")
    cel = str(body.get("cel") or "").strip()
    if cel != PROBE_CEL[probe_id]:
        return _error("cel does not match the playbook probe")

    db, snap, err = load_snapshot(str(claim_id), database, query_rows=query_rows)
    if err or snap is None:
        return _error(err or "submission not found", claim_id=str(claim_id), database=db)
    return rid, db, body, snap


def _audit_and_write(
    *,
    dml: DmlFn,
    db: str,
    rid: str,
    snap: dict[str, Any],
    probe_id: str,
    business_sql: str,
    table: str,
    payload_extra: dict[str, Any],
) -> str:
    result = dml(business_sql)
    if isinstance(result, str) and result.startswith("Error:"):
        return _error(result, run_id=rid, database=db)
    meta = _META[probe_id]
    audit_event = {
        "run_id": rid,
        "claim_id": snap["submission_id"],
        "event_type": meta["next_step"],
        "next_step": meta["next_step"],
        "agent_role": meta["agent_role"],
        "lane": meta["lane"],
        "terminal": meta["terminal"],
        "reason_probe_ids": [probe_id],
        "payload_json": {
            "playbook_version": PLAYBOOK_VERSION,
            "probe_id": probe_id,
            "cel": PROBE_CEL[probe_id],
            "snapshot": snap,
            **payload_extra,
        },
    }
    audit_sql = insert_audit_event_sql(db, audit_event)
    audit_result = dml(audit_sql)
    if isinstance(audit_result, str) and audit_result.startswith("Error:"):
        return _error(audit_result, run_id=rid, database=db, table=table)
    return json.dumps(
        {
            "ok": True,
            "run_id": rid,
            "claim_id": snap["submission_id"],
            "submission_id": snap["submission_id"],
            "database": db,
            "table": table,
            "audit_table": "agent_run_audit",
            "playbook_version": PLAYBOOK_VERSION,
            "probe_id": probe_id,
            **payload_extra,
        }
    )


def write_submission_decline(
    run_id: str,
    event_json: str,
    database: str | None = None,
    *,
    execute_dml: DmlFn | None = None,
    query_rows: QueryFn | None = None,
) -> str:
    governed = _governed(
        run_id,
        event_json,
        probe_id="P0_OUT_OF_APPETITE",
        database=database,
        query_rows=query_rows,
    )
    if isinstance(governed, str):
        return governed
    rid, db, body, snap = governed
    reason = str(body.get("reason_code") or "").strip()
    if reason not in _DECLINE_REASONS:
        return _error("reason_code must be OUT_OF_APPETITE")
    row = {
        "decline_id": _row_id(rid, snap["submission_id"], "decline"),
        "submission_id": snap["submission_id"],
        "reason_code": reason,
        "run_id": rid,
    }
    return _audit_and_write(
        dml=_need_dml(execute_dml),
        db=db,
        rid=rid,
        snap=snap,
        probe_id="P0_OUT_OF_APPETITE",
        business_sql=insert_decline_sql(db, row),
        table="submission_decline",
        payload_extra={"reason_code": reason, "decline_id": row["decline_id"]},
    )


def write_data_enrichment_request(
    run_id: str,
    event_json: str,
    database: str | None = None,
    *,
    execute_dml: DmlFn | None = None,
    query_rows: QueryFn | None = None,
) -> str:
    governed = _governed(
        run_id,
        event_json,
        probe_id="P1_AWAITING_INSPECTION",
        database=database,
        query_rows=query_rows,
    )
    if isinstance(governed, str):
        return governed
    rid, db, body, snap = governed
    provider = str(body.get("provider_type") or "").strip()
    if provider not in _PROVIDERS:
        return _error("provider_type must be INSPECTION")
    row = {
        "enrichment_id": _row_id(rid, snap["submission_id"], "enrichment"),
        "submission_id": snap["submission_id"],
        "provider_type": provider,
        "run_id": rid,
    }
    return _audit_and_write(
        dml=_need_dml(execute_dml),
        db=db,
        rid=rid,
        snap=snap,
        probe_id="P1_AWAITING_INSPECTION",
        business_sql=insert_enrichment_sql(db, row),
        table="data_enrichment_request",
        payload_extra={"provider_type": provider, "enrichment_id": row["enrichment_id"]},
    )


def write_referral_queue(
    run_id: str,
    event_json: str,
    database: str | None = None,
    *,
    execute_dml: DmlFn | None = None,
    query_rows: QueryFn | None = None,
) -> str:
    governed = _governed(
        run_id,
        event_json,
        probe_id="P2_SENIOR_UW_ESCALATION",
        database=database,
        query_rows=query_rows,
    )
    if isinstance(governed, str):
        return governed
    rid, db, _body, snap = governed
    row = {
        "referral_id": _row_id(rid, snap["submission_id"], "referral"),
        "submission_id": snap["submission_id"],
        "queue_code": "SENIOR_UW",
        "run_id": rid,
    }
    return _audit_and_write(
        dml=_need_dml(execute_dml),
        db=db,
        rid=rid,
        snap=snap,
        probe_id="P2_SENIOR_UW_ESCALATION",
        business_sql=insert_referral_sql(db, row),
        table="referral_queue",
        payload_extra={"queue_code": "SENIOR_UW", "referral_id": row["referral_id"]},
    )


def write_quote_issuance(
    run_id: str,
    event_json: str,
    database: str | None = None,
    *,
    execute_dml: DmlFn | None = None,
    query_rows: QueryFn | None = None,
) -> str:
    try:
        body = _parse_json_arg(event_json, "event_json")
    except ValueError as exc:
        return _error(str(exc))
    supplied = sorted(_PRICE_KEYS.intersection(body))
    if supplied:
        return _error(
            "rating_tier and premium_cents are computed by the catalog",
            rejected=supplied,
        )
    governed = _governed(
        run_id,
        event_json,
        probe_id="P3_STRAIGHT_THROUGH_BIND",
        database=database,
        query_rows=query_rows,
    )
    if isinstance(governed, str):
        return governed
    rid, db, _body, snap = governed
    rating_tier, premium_cents = rate_quote(
        snap["total_insured_value"], snap["financial_stability_tier"]
    )
    row = {
        "quote_id": _row_id(rid, snap["submission_id"], "quote"),
        "submission_id": snap["submission_id"],
        "rating_tier": rating_tier,
        "premium_cents": premium_cents,
        "run_id": rid,
    }
    return _audit_and_write(
        dml=_need_dml(execute_dml),
        db=db,
        rid=rid,
        snap=snap,
        probe_id="P3_STRAIGHT_THROUGH_BIND",
        business_sql=insert_quote_sql(db, row),
        table="quote_issuance",
        payload_extra={
            "quote_id": row["quote_id"],
            "rating_tier": rating_tier,
            "premium_cents": premium_cents,
        },
    )
