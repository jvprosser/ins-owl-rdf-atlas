"""Curated Impala SQL for distribution spine, signals, and specialist views."""

from __future__ import annotations

import re
from typing import Any

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_ident(name: str, kind: str = "identifier") -> str:
    if not _IDENT_RE.match(name):
        raise ValueError(f"Invalid {kind}: {name!r}")
    return name


def sql_quote(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "t", "1", "yes"}:
        return True
    if text in {"false", "f", "0", "no"}:
        return False
    return bool(value)


def distribution_spine_sql(claim_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
SELECT
  r.distribution_request_id,
  r.request_status_code,
  r.distribution_type_code,
  r.plan_id,
  r.participant_id,
  r.hold_or_aml_flag,
  r.requested_amount
FROM {db}.distribution_request r
WHERE r.distribution_request_id = {cid}
LIMIT 1
""".strip()


def distribution_routing_signals_sql(claim_id: int | str, database: str) -> str:
    """One-row ingredients for playbook CEL. Lists are separate SELECTs."""
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
WITH
qdro AS (
  SELECT COUNT(*) AS cnt
  FROM {db}.distribution_qdro
  WHERE distribution_request_id = {cid}
    AND is_active = TRUE
),
emer AS (
  SELECT COALESCE(MAX(prior_count), 0) AS prior_count
  FROM {db}.distribution_emergency_ytd
  WHERE distribution_request_id = {cid}
)
SELECT
  COALESCE(r.hold_or_aml_flag, FALSE) AS hold_or_aml_flag,
  r.requested_amount,
  h.hardship_category,
  h.documented_financial_need_amount,
  h.estimated_tax_withholding_amount,
  h.has_participant_self_certified,
  h.requires_substantiation_audit,
  COALESCE(p.plan_subject_to_qjsa, FALSE) AS plan_subject_to_qjsa,
  COALESCE(p.plan_mandates_loan_exhaustion, FALSE) AS plan_mandates_loan_exhaustion,
  part.participant_marital_status,
  COALESCE(part.spousal_consent_verified, FALSE) AS spousal_consent_verified,
  COALESCE(ln.available_plan_loan_capacity, 0) AS available_plan_loan_capacity,
  (qdro.cnt > 0) AS has_active_qdro_hold,
  emer.prior_count AS prior_emergency_distributions_this_year
FROM {db}.distribution_request r
LEFT JOIN {db}.distribution_hardship h
  ON h.distribution_request_id = r.distribution_request_id
LEFT JOIN {db}.distribution_plan p ON p.plan_id = r.plan_id
LEFT JOIN {db}.distribution_participant part
  ON part.participant_id = r.participant_id
LEFT JOIN {db}.distribution_loan ln
  ON ln.distribution_request_id = r.distribution_request_id
CROSS JOIN qdro
CROSS JOIN emer
WHERE r.distribution_request_id = {cid}
LIMIT 1
""".strip()


def distribution_exception_view_sql(claim_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
SELECT exception_id, reason_code, queue, required_docs
FROM {db}.distribution_exception
WHERE distribution_request_id = {cid}
""".strip()


def distribution_rmd_view_sql(claim_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
SELECT tax_year, required_amount, paid_amount, shortfall_amount, deadline
FROM {db}.distribution_rmd
WHERE distribution_request_id = {cid}
LIMIT 1
""".strip()


def distribution_court_orders_sql(claim_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
SELECT court_order_id, docket_number, status_code
FROM {db}.distribution_court_order
WHERE distribution_request_id = {cid}
  AND UPPER(COALESCE(status_code, '')) = 'PENDING'
""".strip()


def distribution_compliance_view_sql(claim_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
SELECT
  r.distribution_request_id,
  r.plan_id,
  r.participant_id,
  COALESCE(p.plan_subject_to_qjsa, FALSE) AS plan_subject_to_qjsa,
  COALESCE(p.plan_mandates_loan_exhaustion, FALSE) AS plan_mandates_loan_exhaustion,
  part.participant_marital_status,
  COALESCE(part.spousal_consent_verified, FALSE) AS spousal_consent_verified
FROM {db}.distribution_request r
LEFT JOIN {db}.distribution_plan p ON p.plan_id = r.plan_id
LEFT JOIN {db}.distribution_participant part
  ON part.participant_id = r.participant_id
WHERE r.distribution_request_id = {cid}
LIMIT 1
""".strip()


def distribution_loan_summary_view_sql(claim_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
SELECT available_plan_loan_capacity, outstanding_loan_balance, max_loan_amount
FROM {db}.distribution_loan
WHERE distribution_request_id = {cid}
LIMIT 1
""".strip()


def distribution_qdro_details_view_sql(claim_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
SELECT qdro_id, is_active, order_status_code, alternate_payee_name, hold_reason
FROM {db}.distribution_qdro
WHERE distribution_request_id = {cid}
""".strip()


def insert_outbound_notice_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    return (
        f"INSERT INTO {db}.distribution_outbound_notice ("
        "notice_id, distribution_request_id, purpose_code, channel_code, "
        "body_text, run_id, created_at"
        ") VALUES ("
        f"{int(row['notice_id'])}, {int(row['distribution_request_id'])}, "
        f"{sql_quote(row.get('purpose_code') or 'REQUEST_SELF_CERTIFICATION')}, "
        f"{sql_quote(row.get('channel_code') or 'LETTER')}, "
        f"{sql_quote(row['body_text'])}, {sql_quote(row['run_id'])}, "
        "CURRENT_TIMESTAMP()"
        ")"
    )
