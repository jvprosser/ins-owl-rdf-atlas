"""Playbook-aligned specialist views (curated SQL; no free-form joins).

Select business columns only: omit the table PK and FK columns. ``claim_id``
stays on the JSON envelope and in WHERE.
"""

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
SELECT litigation_status_code, docket_number, venue_name,
       venue_country_subdivision_code, filed_date, served_date, closed_date,
       demand_amount, currency_code, created_at
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
SELECT injury_severity_code, body_region_code, injury_description,
       treatment_start_date, treatment_end_date, ambulance_used_indicator,
       hospitalization_indicator, created_at
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
SELECT subrogation_status_code, demand_amount, recovered_amount, currency_code,
       opened_date, closed_date, statute_limitations_date, created_at
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
    """Police report + fault + intake number for PdClaimsAgent (playbook: get_pd_view)."""
    qr = query_rows or _qr()
    db = validate_ident(_default_database(database), "database")
    cid = str(int(claim_id))
    police_sql = f"""
SELECT report_number, agency_name, report_datetime, report_date,
       citation_issued_indicator, narrative_summary, created_at
FROM {db}.police_report
WHERE claim_id = {cid}
""".strip()
    fault_sql = f"""
SELECT insured_fault_percent, adverse_fault_percent, fault_basis_code,
       determination_status_code, determination_datetime, notes, created_at
FROM {db}.fault_determination
WHERE claim_id = {cid}
""".strip()
    intake_sql = f"""
SELECT incident_report_number
FROM {db}.claim_police_intake
WHERE claim_id = {cid}
  AND incident_report_number IS NOT NULL
  AND TRIM(incident_report_number) <> ''
ORDER BY collected_at DESC
LIMIT 1
""".strip()
    sms_sql = f"""
SELECT to_phone, body_text, created_at
FROM {db}.claim_outbound_message
WHERE claim_id = {cid}
  AND purpose_code = 'COLLECT_INCIDENT_REPORT_NUMBER'
ORDER BY created_at DESC
LIMIT 1
""".strip()
    try:
        police_reports = qr(police_sql)
        fault_determinations = qr(fault_sql)
        intake_rows = qr(intake_sql)
        sms_rows = qr(sms_sql)
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    incident = None
    if intake_rows:
        incident = intake_rows[0].get("incident_report_number")
    return json.dumps(
        {
            "claim_id": int(cid),
            "database": db,
            "incident_report_number": incident,
            "last_sms": sms_rows[0] if sms_rows else None,
            "police_reports": police_reports,
            "fault_determinations": fault_determinations,
        },
        default=str,
    )


def get_deny_view(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    """Operator, policy, and police facts for Deny Agent / Human Review.

    Business columns only (no PK/FK). Envelope still has ``claim_id``.
    """
    qr = query_rows or _qr()
    db = validate_ident(_default_database(database), "database")
    cid = str(int(claim_id))
    operators_sql = f"""
SELECT ld.driver_role_code, ld.was_cited_indicator,
       ld.impairment_suspected_indicator, d.license_status_code,
       (pd.is_excluded_driver IS NOT NULL) AS listed_on_policy,
       COALESCE(pd.is_excluded_driver, FALSE) AS is_excluded_driver
FROM {db}.loss_driver ld
LEFT JOIN {db}.driver d ON d.driver_id = ld.driver_id
INNER JOIN {db}.claim c ON c.claim_id = ld.claim_id
LEFT JOIN {db}.policy_driver pd
  ON pd.policy_id = c.policy_id
 AND pd.driver_id = ld.driver_id
 AND pd.expiration_date IS NULL
WHERE ld.claim_id = {cid}
""".strip()
    policy_sql = f"""
SELECT c.claim_status_code, c.claim_number, p.policy_number,
       p.policy_status_code, p.effective_date, p.expiration_date,
       p.cancellation_date, le.loss_date
FROM {db}.claim c
INNER JOIN {db}.insurance_policy p ON p.policy_id = c.policy_id
INNER JOIN {db}.loss_event le ON le.loss_event_id = c.loss_event_id
WHERE c.claim_id = {cid}
""".strip()
    police_sql = f"""
SELECT report_number, agency_name, narrative_summary
FROM {db}.police_report
WHERE claim_id = {cid}
""".strip()
    try:
        operators = qr(operators_sql)
        policy_rows = qr(policy_sql)
        police_reports = qr(police_sql)
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})
    return json.dumps(
        {
            "claim_id": int(cid),
            "database": db,
            "operators": operators,
            "policy": policy_rows[0] if policy_rows else None,
            "police_reports": police_reports,
        },
        default=str,
    )
