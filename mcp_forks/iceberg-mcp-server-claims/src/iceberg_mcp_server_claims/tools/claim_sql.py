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


def sql_bool_truthy(expr: str) -> str:
    """Match Iceberg/Impala booleans that SELECT shows as true but ``= TRUE`` misses.

    Hive-written Iceberg booleans may arrive as TRUE, 1, or the strings
    ``true`` / ``1``. ``CAST(... AS STRING)`` covers those encodings.
    """
    return f"UPPER(TRIM(CAST({expr} AS STRING))) IN ('TRUE', '1', 'T')"


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
  le.loss_date,
  c.policy_id,
  p.policy_number,
  p.policy_status_code,
  p.effective_date,
  p.expiration_date,
  p.cancellation_date,
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


def list_adjuster_open_claims_sql(party_id: int | str, database: str) -> str:
    """Claims currently assigned to an adjuster and not CLOSED."""
    db = validate_ident(database, "database")
    pid = int(party_id)
    return f"""
SELECT
  c.claim_id,
  c.claim_number,
  c.claim_status_code,
  pe.first_name,
  pe.last_name
FROM {db}.claim c
INNER JOIN {db}.claim_party_role r
  ON r.claim_id = c.claim_id
 AND r.role_type_code = 'ADJUSTER'
 AND r.is_current_assignment = TRUE
 AND r.party_id = {pid}
LEFT JOIN {db}.person pe ON pe.party_id = r.party_id
WHERE UPPER(COALESCE(c.claim_status_code, '')) <> 'CLOSED'
ORDER BY c.claim_id
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


def claim_insured_operators_sql(claim_id: int | str, database: str) -> str:
    """Insured-operator rows for playbook CEL (citation / exclusion / unlawful)."""
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
SELECT
  ld.driver_id,
  ld.was_cited_indicator,
  ld.impairment_suspected_indicator,
  d.license_status_code,
  CASE WHEN pd.driver_id IS NOT NULL THEN TRUE ELSE FALSE END AS on_policy,
  pd.is_excluded_driver
FROM {db}.loss_driver ld
LEFT JOIN {db}.driver d ON d.driver_id = ld.driver_id
INNER JOIN {db}.claim c ON c.claim_id = ld.claim_id
LEFT JOIN {db}.policy_driver pd
  ON pd.policy_id = c.policy_id
 AND pd.driver_id = ld.driver_id
 AND pd.expiration_date IS NULL
WHERE ld.claim_id = {cid}
  AND ld.driver_role_code = 'INSURED_OPERATOR'
""".strip()


def claim_routing_signals_sql(claim_id: int | str, database: str) -> str:
    """Impala-friendly signals SQL (no scalar COUNT(*)>0 subqueries).

    Nested ``(SELECT COUNT(*) > 0 …)`` plans frequently hang or mis-optimize
    on Iceberg V2 under Impala. Aggregate CTEs + CROSS JOIN stay one row each.
    Playbook CEL evaluates docket/discovery/operator/policy predicates from
    projected columns plus ``claim_insured_operators_sql``.
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
  SELECT COUNT(*) AS cnt,
         MIN(litigation_case_id) AS litigation_case_id,
         MIN(docket_number) AS docket_number,
         MIN(defense_counsel_party_id) AS defense_counsel_party_id,
         MIN(plaintiff_counsel_party_id) AS plaintiff_counsel_party_id,
         MIN(served_date) AS served_date,
         MIN(filed_date) AS filed_date,
         MIN(closed_date) AS closed_date,
         MIN(litigation_status_code) AS litigation_status_code
  FROM {db}.litigation_case WHERE claim_id = {cid}
),
inj AS (
  SELECT COUNT(*) AS cnt FROM {db}.claim_injury WHERE claim_id = {cid}
),
pr AS (
  SELECT COUNT(*) AS cnt, MIN(police_report_id) AS police_report_id
  FROM {db}.police_report WHERE claim_id = {cid}
),
intake AS (
  SELECT COUNT(*) AS cnt,
         MIN(incident_report_number) AS incident_report_number
  FROM {db}.claim_police_intake
  WHERE claim_id = {cid}
    AND incident_report_number IS NOT NULL
    AND TRIM(incident_report_number) <> ''
),
sms AS (
  SELECT COUNT(*) AS cnt
  FROM {db}.claim_outbound_message
  WHERE claim_id = {cid}
    AND purpose_code = 'COLLECT_INCIDENT_REPORT_NUMBER'
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
  lit.docket_number,
  lit.defense_counsel_party_id,
  lit.plaintiff_counsel_party_id,
  lit.served_date,
  lit.filed_date,
  lit.closed_date,
  lit.litigation_status_code,
  (inj.cnt > 0) AS has_injury,
  (pr.cnt > 0) AS has_police_report,
  pr.police_report_id,
  (fd.cnt > 0) AS has_fault_determination,
  fd.fault_determination_id,
  (intake.cnt > 0) AS has_incident_report_number,
  intake.incident_report_number,
  (sms.cnt > 0) AS has_collect_incident_sms,
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
CROSS JOIN intake
CROSS JOIN sms
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


def parse_fnol_id(value: int | str) -> int:
    """Accept 88 or FNOL-2026-00088 (trailing numeric group)."""
    text = str(value).strip()
    if text.upper().startswith("FNOL-"):
        tail = text.rsplit("-", 1)[-1]
        return int(tail)
    return int(text)


def fnol_converted_claim_id(fnol_id: int) -> int:
    return 80000 + int(fnol_id)


def fnol_spine_sql(fnol_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    fid = parse_fnol_id(fnol_id)
    return f"""
SELECT
  f.fnol_id,
  f.fnol_number,
  f.report_timestamp,
  f.reported_by_relationship,
  f.intake_channel,
  f.intake_purpose_code,
  f.triage_status_code,
  f.estimated_loss_amount,
  f.claim_id,
  f.policy_id,
  f.insurable_object_id,
  f.loss_event_id,
  p.policy_number,
  p.policy_status_code,
  p.effective_date,
  p.expiration_date,
  p.cancellation_date,
  le.loss_cause_code,
  le.loss_date,
  v.vin,
  CASE WHEN pio.policy_id IS NOT NULL THEN TRUE ELSE FALSE END AS vehicle_listed_on_policy,
  pc.policy_coverage_id,
  cov.coverage_type_code,
  pc.deductible_amount,
  CASE WHEN pc.policy_coverage_id IS NOT NULL THEN TRUE ELSE FALSE END AS peril_covered
FROM {db}.fnol f
LEFT JOIN {db}.loss_event le ON f.loss_event_id = le.loss_event_id
LEFT JOIN {db}.insurance_policy p ON f.policy_id = p.policy_id
LEFT JOIN {db}.vehicle v ON f.insurable_object_id = v.insurable_object_id
LEFT JOIN {db}.policy_insurable_object pio
  ON pio.policy_id = f.policy_id
 AND pio.insurable_object_id = f.insurable_object_id
 AND pio.expiration_date IS NULL
LEFT JOIN {db}.policy_coverage pc
  ON pc.policy_id = f.policy_id
 AND pc.is_active = TRUE
 AND pc.expiration_date IS NULL
LEFT JOIN {db}.coverage cov ON cov.coverage_id = pc.coverage_id
 AND (
   (UPPER(COALESCE(le.loss_cause_code, '')) = 'COLLISION'
    AND cov.coverage_type_code = 'COLLISION')
   OR (UPPER(COALESCE(le.loss_cause_code, '')) <> 'COLLISION'
    AND cov.coverage_type_code = 'COMPREHENSIVE')
 )
WHERE f.fnol_id = {fid}
LIMIT 1
""".strip()


def fnol_routing_signals_sql(fnol_id: int | str, database: str) -> str:
    """Impala-friendly FNOL signals (aggregate CTEs; no scalar COUNT(*)>0)."""
    db = validate_ident(database, "database")
    fid = parse_fnol_id(fnol_id)
    return f"""
WITH
inj AS (
  SELECT COUNT(*) AS cnt FROM {db}.fnol_injury WHERE fnol_id = {fid}
),
tpv AS (
  SELECT COUNT(*) AS cnt FROM {db}.fnol_third_party_vehicle WHERE fnol_id = {fid}
),
unl AS (
  SELECT COUNT(*) AS cnt
  FROM {db}.fnol f
  INNER JOIN {db}.loss_driver ld
    ON ld.loss_event_id = f.loss_event_id
   AND ld.driver_role_code = 'INSURED_OPERATOR'
  LEFT JOIN {db}.policy_driver pd
    ON pd.policy_id = f.policy_id
   AND pd.driver_id = ld.driver_id
   AND pd.expiration_date IS NULL
  WHERE f.fnol_id = {fid}
    AND pd.driver_id IS NULL
)
SELECT
  (inj.cnt > 0) AS has_injury,
  (tpv.cnt > 0) AS has_third_party_vehicle,
  (unl.cnt > 0) AS has_unlisted_insured_operator
FROM inj
CROSS JOIN tpv
CROSS JOIN unl
""".strip()


def fnol_status_sql(fnol_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    fid = parse_fnol_id(fnol_id)
    return (
        "SELECT fnol_id, fnol_number, triage_status_code, claim_id, "
        "policy_id, insurable_object_id, loss_event_id, estimated_loss_amount, "
        "report_timestamp, intake_purpose_code "
        f"FROM {db}.fnol WHERE fnol_id = {fid} LIMIT 1"
    )


def fnol_matching_coverage_sql(fnol_id: int | str, database: str) -> str:
    db = validate_ident(database, "database")
    fid = parse_fnol_id(fnol_id)
    return f"""
SELECT pc.policy_coverage_id, pc.deductible_amount, cov.coverage_type_code
FROM {db}.fnol f
INNER JOIN {db}.loss_event le ON le.loss_event_id = f.loss_event_id
INNER JOIN {db}.policy_coverage pc
  ON pc.policy_id = f.policy_id
 AND pc.is_active = TRUE
 AND pc.expiration_date IS NULL
INNER JOIN {db}.coverage cov ON cov.coverage_id = pc.coverage_id
 AND (
   (UPPER(COALESCE(le.loss_cause_code, '')) = 'COLLISION'
    AND cov.coverage_type_code = 'COLLISION')
   OR (UPPER(COALESCE(le.loss_cause_code, '')) <> 'COLLISION'
    AND cov.coverage_type_code = 'COMPREHENSIVE')
 )
WHERE f.fnol_id = {fid}
LIMIT 1
""".strip()


def update_fnol_status_sql(
    database: str, fnol_id: int, status: str, *, claim_id: int | None = None
) -> str:
    db = validate_ident(database, "database")
    fid = int(fnol_id)
    claim_set = (
        f", claim_id = {int(claim_id)}" if claim_id is not None else ""
    )
    return (
        f"UPDATE {db}.fnol SET triage_status_code = {sql_quote(status)}{claim_set} "
        f"WHERE fnol_id = {fid} "
        "AND UPPER(COALESCE(triage_status_code, '')) IN "
        "('OPEN', 'ADJUSTER_REVIEW')"
    )


def insert_converted_claim_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    cov = row.get("policy_coverage_id")
    cov_sql = "NULL" if cov in (None, "") else str(int(cov))
    loss = row.get("loss_event_id")
    loss_sql = "NULL" if loss in (None, "") else str(int(loss))
    obj = row.get("insurable_object_id")
    obj_sql = "NULL" if obj in (None, "") else str(int(obj))
    return (
        f"INSERT INTO {db}.claim ("
        "claim_id, claim_number, loss_event_id, policy_id, insurable_object_id, "
        "policy_coverage_id, fnol_report_datetime, claim_status_code, "
        "fraudulent_claim_indicator, litigation_indicator, "
        "subrogation_indicator, total_loss_indicator, created_at"
        ") VALUES ("
        f"{int(row['claim_id'])}, {sql_quote(row['claim_number'])}, {loss_sql}, "
        f"{int(row['policy_id'])}, {obj_sql}, {cov_sql}, "
        "CURRENT_TIMESTAMP(), 'OPEN', FALSE, FALSE, FALSE, FALSE, "
        "CURRENT_TIMESTAMP())"
    )


def insert_converted_reserve_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    amount = row["amount"]
    return (
        f"INSERT INTO {db}.claim_reserve ("
        "claim_reserve_id, claim_id, reserve_status_code, currency_code, "
        "initial_loss_reserve_amount, revised_reserve_total_amount, "
        "is_current, last_updated_at, created_at"
        ") VALUES ("
        f"{int(row['claim_reserve_id'])}, {int(row['claim_id'])}, 'OPEN', 'USD', "
        f"{amount}, {amount}, TRUE, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())"
    )
