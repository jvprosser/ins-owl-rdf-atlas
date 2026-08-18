"""Playbook-aligned specialist views (curated SQL; no free-form joins)."""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from iceberg_mcp_server_claims.tools.claim_sql import validate_ident

QueryFn = Callable[[str], list[dict[str, Any]]]


def _default_database(database: str | None) -> str:
    return database or os.getenv("IMPALA_DATABASE", "car_insurance_claims")


def _qr() -> QueryFn:
    from iceberg_mcp_server_claims.tools.impala_tools import query_rows

    return query_rows


def get_litigation_view(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    """Litigation case rows for LitigationAgent (playbook: get_litigation_view)."""
    qr = query_rows or _qr()
    db = validate_ident(_default_database(database), "database")
    cid = str(int(claim_id))
    sql = f"""
SELECT litigation_case_id, litigation_status_code, docket_number,
       venue_name, venue_country_subdivision_code,
       plaintiff_party_id, defendant_party_id,
       plaintiff_counsel_party_id, defense_counsel_party_id,
       filed_date, served_date, closed_date, demand_amount, currency_code
FROM {db}.litigation_case
WHERE claim_id = {cid}
""".strip()
    try:
        rows = qr(sql)
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    return json.dumps(
        {"claim_id": int(cid), "database": db, "litigation_cases": rows},
        default=str,
    )


def get_bi_view(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    """Injury rows for BiClaimsAgent (playbook: get_bi_view)."""
    qr = query_rows or _qr()
    db = validate_ident(_default_database(database), "database")
    cid = str(int(claim_id))
    sql = f"""
SELECT claim_injury_id, injured_party_id, injury_severity_code,
       body_region_code, medical_provider_party_id
FROM {db}.claim_injury
WHERE claim_id = {cid}
""".strip()
    try:
        rows = qr(sql)
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    return json.dumps(
        {"claim_id": int(cid), "database": db, "injuries": rows},
        default=str,
    )


def get_subrogation_view(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    """Subrogation case rows for SubrogationAgent (playbook: get_subrogation_view)."""
    qr = query_rows or _qr()
    db = validate_ident(_default_database(database), "database")
    cid = str(int(claim_id))
    sql = f"""
SELECT subrogation_case_id, subrogation_status_code, demand_amount,
       recovered_amount, adverse_party_id, adverse_carrier_party_id
FROM {db}.subrogation_case
WHERE claim_id = {cid}
""".strip()
    try:
        rows = qr(sql)
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    return json.dumps(
        {"claim_id": int(cid), "database": db, "subrogation_cases": rows},
        default=str,
    )


def get_pd_view(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    """Police report + fault rows for PdClaimsAgent (playbook: get_pd_view)."""
    qr = query_rows or _qr()
    db = validate_ident(_default_database(database), "database")
    cid = str(int(claim_id))
    police_sql = f"""
SELECT police_report_id, loss_event_id, report_number, agency_name,
       report_date, citation_issued_indicator
FROM {db}.police_report
WHERE claim_id = {cid}
""".strip()
    fault_sql = f"""
SELECT fault_determination_id, loss_event_id, at_fault_driver_id,
       insured_fault_percent, adverse_fault_percent, fault_basis_code,
       determination_status_code
FROM {db}.fault_determination
WHERE claim_id = {cid}
""".strip()
    try:
        police_reports = qr(police_sql)
        fault_determinations = qr(fault_sql)
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    return json.dumps(
        {
            "claim_id": int(cid),
            "database": db,
            "police_reports": police_reports,
            "fault_determinations": fault_determinations,
        },
        default=str,
    )
