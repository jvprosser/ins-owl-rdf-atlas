"""Curated Impala SQL for submission spine, signals, and governed writes."""

from __future__ import annotations

import re
from typing import Any

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SUBMISSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def validate_ident(name: str, kind: str = "identifier") -> str:
    if not _IDENT_RE.match(name):
        raise ValueError(f"Invalid {kind}: {name!r}")
    return name


def validate_submission_id(value: Any) -> str:
    sid = str(value or "").strip()
    if not _SUBMISSION_RE.match(sid):
        raise ValueError(
            "submission id must be 1–64 chars: letters, digits, underscore, hyphen"
        )
    return sid


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


def submission_spine_sql(submission_id: str, database: str) -> str:
    db = validate_ident(database, "database")
    sid = sql_quote(validate_submission_id(submission_id))
    return f"""
SELECT
  s.submission_id,
  s.producer_id,
  s.applicant_tax_id,
  s.line_of_business,
  s.class_code,
  s.naics_code,
  s.total_insured_value,
  s.submission_timestamp,
  s.submission_status_code
FROM {db}.submissions s
WHERE s.submission_id = {sid}
LIMIT 1
""".strip()


def submission_snapshot_sql(submission_id: str, database: str) -> str:
    """Spine plus the signal columns the playbook and rate table read."""
    db = validate_ident(database, "database")
    sid = sql_quote(validate_submission_id(submission_id))
    return f"""
SELECT
  s.submission_id,
  s.line_of_business,
  s.class_code,
  s.naics_code,
  s.total_insured_value,
  s.submission_status_code,
  COALESCE(s.has_ofac_match, FALSE) AS has_ofac_match,
  COALESCE(s.siu_score, 0) AS siu_score,
  COALESCE(s.tax_lien_unresolved, FALSE) AS tax_lien_unresolved,
  COALESCE(p.is_in_flood_plain, FALSE) AS is_in_flood_plain,
  COALESCE(p.inspection_completed, FALSE) AS inspection_completed,
  p.flood_zone,
  COALESCE(p.has_survey_on_file, FALSE) AS has_survey_on_file,
  COALESCE(p.survey_age_months, 0) AS survey_age_months,
  COALESCE(p.wind_tier, 0) AS wind_tier,
  COALESCE(p.has_recent_cat_run, FALSE) AS has_recent_cat_run,
  p.construction_type,
  COALESCE(p.year_built, 0) AS year_built,
  COALESCE(p.wiring_updated, FALSE) AS wiring_updated,
  p.protection_class,
  COALESCE(p.has_sprinklers, FALSE) AS has_sprinklers,
  COALESCE(p.square_footage, 0) AS square_footage,
  COALESCE(l.prior_claims_count, 0) AS prior_claims_count,
  COALESCE(l.claims_count_36m, 0) AS claims_count_36m,
  COALESCE(l.total_incurred_36m, 0) AS total_incurred_36m,
  COALESCE(l.has_open_loss_past_36m, FALSE) AS has_open_loss_past_36m,
  l.financial_stability_tier,
  COALESCE(l.financial_score, 0) AS financial_score,
  CASE WHEN r.party_id IS NOT NULL THEN TRUE ELSE FALSE END AS has_underwriter
FROM {db}.submissions s
LEFT JOIN {db}.property_risk_scores p
  ON p.submission_id = s.submission_id
LEFT JOIN {db}.loss_history_summary l
  ON l.submission_id = s.submission_id
LEFT JOIN {db}.submission_party_role r
  ON r.submission_id = s.submission_id
 AND r.role_type_code = 'UNDERWRITER'
 AND r.is_current_assignment = TRUE
WHERE s.submission_id = {sid}
LIMIT 1
""".strip()


def list_underwriter_open_submissions_sql(party_id: int | str, database: str) -> str:
    """Open submissions currently assigned to an underwriter.

    DECLINED and QUOTED are terminal and stay off the list.
    """
    db = validate_ident(database, "database")
    pid = int(party_id)
    return f"""
SELECT
  s.submission_id,
  s.line_of_business,
  s.submission_status_code,
  pe.first_name,
  pe.last_name
FROM {db}.submissions s
INNER JOIN {db}.submission_party_role r
  ON r.submission_id = s.submission_id
 AND r.role_type_code = 'UNDERWRITER'
 AND r.is_current_assignment = TRUE
 AND r.party_id = {pid}
LEFT JOIN {db}.person pe ON pe.party_id = r.party_id
WHERE UPPER(COALESCE(s.submission_status_code, '')) NOT IN ('DECLINED', 'QUOTED')
ORDER BY s.submission_id
""".strip()


def insert_decline_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    return (
        f"INSERT INTO {db}.submission_decline ("
        "decline_id, submission_id, reason_code, run_id, created_at"
        ") VALUES ("
        f"{sql_quote(row['decline_id'])}, {sql_quote(row['submission_id'])}, "
        f"{sql_quote(row['reason_code'])}, {sql_quote(row['run_id'])}, "
        "CURRENT_TIMESTAMP())"
    )


def insert_quote_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    return (
        f"INSERT INTO {db}.quote_issuance ("
        "quote_id, submission_id, rating_tier, premium_cents, run_id, created_at"
        ") VALUES ("
        f"{sql_quote(row['quote_id'])}, {sql_quote(row['submission_id'])}, "
        f"{sql_quote(row['rating_tier'])}, {int(row['premium_cents'])}, "
        f"{sql_quote(row['run_id'])}, CURRENT_TIMESTAMP())"
    )


def insert_enrichment_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    return (
        f"INSERT INTO {db}.data_enrichment_request ("
        "enrichment_id, submission_id, provider_type, run_id, created_at"
        ") VALUES ("
        f"{sql_quote(row['enrichment_id'])}, {sql_quote(row['submission_id'])}, "
        f"{sql_quote(row['provider_type'])}, {sql_quote(row['run_id'])}, "
        "CURRENT_TIMESTAMP())"
    )


def insert_referral_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    return (
        f"INSERT INTO {db}.referral_queue ("
        "referral_id, submission_id, queue_code, run_id, created_at"
        ") VALUES ("
        f"{sql_quote(row['referral_id'])}, {sql_quote(row['submission_id'])}, "
        f"{sql_quote(row['queue_code'])}, {sql_quote(row['run_id'])}, "
        "CURRENT_TIMESTAMP())"
    )
