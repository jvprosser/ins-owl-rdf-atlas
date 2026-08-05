"""Curated Impala SQL for claim spine + routing signals (no free-form joins)."""

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


def claim_spine_sql(claim_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
SELECT
  c.claim_id,
  c.claim_number,
  c.claim_status_code,
  c.litigation_indicator,
  c.subrogation_indicator,
  c.fraudulent_claim_indicator,
  c.total_loss_indicator,
  c.loss_event_id,
  le.loss_cause_code,
  c.policy_id,
  p.policy_number,
  c.insurable_object_id,
  v.vin,
  CASE WHEN pio.policy_id IS NOT NULL THEN TRUE ELSE FALSE END AS policy_covers_vehicle,
  c.policy_coverage_id,
  cov.coverage_type_code,
  cl.claim_lifecycle_id
FROM {db}.claim c
LEFT JOIN {db}.loss_event le ON c.loss_event_id = le.loss_event_id
LEFT JOIN {db}.insurance_policy p ON c.policy_id = p.policy_id
LEFT JOIN {db}.vehicle v ON c.insurable_object_id = v.insurable_object_id
LEFT JOIN {db}.policy_insurable_object pio
  ON pio.policy_id = c.policy_id
 AND pio.insurable_object_id = c.insurable_object_id
 AND pio.expiration_date IS NULL
LEFT JOIN {db}.policy_coverage pc ON c.policy_coverage_id = pc.policy_coverage_id
LEFT JOIN {db}.coverage cov ON pc.coverage_id = cov.coverage_id
LEFT JOIN {db}.claim_lifecycle cl ON cl.claim_id = c.claim_id
WHERE c.claim_id = {cid}
LIMIT 1
""".strip()


def claim_roles_sql(claim_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
SELECT claim_party_role_id, party_id, role_type_code, is_current_assignment
FROM {db}.claim_party_role
WHERE claim_id = {cid}
  AND is_current_assignment = TRUE
""".strip()


def claim_routing_signals_sql(claim_id: int | str, database: str) -> str:
    """Impala-friendly signals SQL (no scalar COUNT(*)>0 subqueries).

    Nested ``(SELECT COUNT(*) > 0 …)`` plans frequently hang or mis-optimize
    on Iceberg V2 under Impala. Aggregate CTEs + CROSS JOIN stay one row each.
    """
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
WITH
sub AS (
  SELECT COUNT(*) AS cnt,
         MIN(subrogation_case_id) AS subrogation_case_id,
         MIN(subrogation_status_code) AS subrogation_status_code
  FROM {db}.subrogation_case WHERE claim_id = {cid}
),
lit AS (
  SELECT COUNT(*) AS cnt, MIN(litigation_case_id) AS litigation_case_id
  FROM {db}.litigation_case WHERE claim_id = {cid}
),
inj AS (
  SELECT COUNT(*) AS cnt FROM {db}.claim_injury WHERE claim_id = {cid}
),
pr AS (
  SELECT COUNT(*) AS cnt, MIN(police_report_id) AS police_report_id
  FROM {db}.police_report WHERE claim_id = {cid}
),
fd AS (
  SELECT COUNT(*) AS cnt, MIN(fault_determination_id) AS fault_determination_id
  FROM {db}.fault_determination WHERE claim_id = {cid}
),
ofr AS (
  SELECT COUNT(*) AS cnt,
         SUM(CASE WHEN offer_status_code = 'EXTENDED' THEN 1 ELSE 0 END) AS extended_cnt,
         SUM(CASE WHEN offer_status_code = 'ACCEPTED' THEN 1 ELSE 0 END) AS accepted_cnt
  FROM {db}.claim_offer WHERE claim_id = {cid}
),
pay AS (
  SELECT COUNT(*) AS cnt FROM {db}.claim_payment WHERE claim_id = {cid}
),
rec AS (
  SELECT COUNT(*) AS cnt FROM {db}.claim_recovery WHERE claim_id = {cid}
),
res AS (
  SELECT COUNT(*) AS cnt FROM {db}.claim_reserve
  WHERE claim_id = {cid} AND is_current = TRUE
),
fa AS (
  SELECT COUNT(*) AS cnt,
         MIN(fraud_assessment_id) AS fraud_assessment_id,
         MIN(outcome_code) AS fraud_outcome_code
  FROM {db}.fraud_assessment
  WHERE claim_id = {cid} AND outcome_code IN ('SUSPECTED', 'PENDING')
),
doc AS (
  SELECT COUNT(*) AS cnt FROM {db}.claim_document WHERE claim_id = {cid}
)
SELECT
  (sub.cnt > 0) AS has_subrogation_case,
  sub.subrogation_case_id,
  sub.subrogation_status_code,
  (lit.cnt > 0) AS has_litigation_case,
  lit.litigation_case_id,
  (inj.cnt > 0) AS has_injury,
  (pr.cnt > 0) AS has_police_report,
  pr.police_report_id,
  (fd.cnt > 0) AS has_fault_determination,
  fd.fault_determination_id,
  (ofr.cnt > 0) AS has_offer,
  (COALESCE(ofr.extended_cnt, 0) > 0) AS has_unresolved_offer,
  (COALESCE(ofr.accepted_cnt, 0) > 0) AS has_accepted_offer,
  (pay.cnt > 0) AS has_loss_payment,
  (rec.cnt > 0) AS has_recovery,
  (res.cnt > 0) AS has_current_reserve,
  (fa.cnt > 0) AS has_siu_suspected,
  fa.fraud_assessment_id,
  fa.fraud_outcome_code,
  (doc.cnt > 0) AS has_document
FROM sub
CROSS JOIN lit
CROSS JOIN inj
CROSS JOIN pr
CROSS JOIN fd
CROSS JOIN ofr
CROSS JOIN pay
CROSS JOIN rec
CROSS JOIN res
CROSS JOIN fa
CROSS JOIN doc
""".strip()


def claim_injury_ids_sql(claim_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"SELECT claim_injury_id FROM {db}.claim_injury WHERE claim_id = {cid}"


def claim_offers_sql(claim_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
SELECT claim_offer_id, offer_status_code
FROM {db}.claim_offer
WHERE claim_id = {cid}
""".strip()


def claim_payment_ids_sql(claim_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"SELECT claim_payment_id FROM {db}.claim_payment WHERE claim_id = {cid}"


def claim_recovery_ids_sql(claim_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"SELECT claim_recovery_id FROM {db}.claim_recovery WHERE claim_id = {cid}"
