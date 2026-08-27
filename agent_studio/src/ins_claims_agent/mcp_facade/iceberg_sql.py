"""SQL helpers for IcebergFacade fallbacks when fork P0 tools are unavailable.

Upstream ``execute_query`` returns JSON ``{"columns": [...], "rows": [...]}``
(often as a string). Branch DML must target ``db.table.branch_<name>``.
"""

from __future__ import annotations

import json
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


def sql_bool_truthy(expr: str) -> str:
    """Match Iceberg/Impala booleans that SELECT shows as true but ``= TRUE`` misses."""
    return f"UPPER(TRIM(CAST({expr} AS STRING))) IN ('TRUE', '1', 'T')"


def audit_branch_name(run_id: str) -> str:
    """Logical branch name (Hive ref becomes ``branch_<name>``)."""
    safe = re.sub(r"[^A-Za-z0-9_]", "_", run_id.strip())
    if not safe:
        raise ValueError("run_id must yield a non-empty branch name")
    if safe[0].isdigit():
        safe = f"r_{safe}"
    return validate_ident(f"agent_run_{safe}", "branch")


def parse_query_result(raw: Any) -> list[dict[str, Any]]:
    """Normalize MCP execute_query output into a list of row dicts."""
    if raw is None:
        return []
    if isinstance(raw, list):
        if not raw:
            return []
        if isinstance(raw[0], dict):
            return raw
        return []
    if isinstance(raw, str):
        text = raw.strip()
        if not text or text.startswith("Error:") or text.startswith("Only read-only"):
            if text.startswith("Error:") or text.startswith("Only read-only"):
                raise RuntimeError(text)
            return []
        raw = json.loads(text)
    if not isinstance(raw, dict):
        return []
    if "error" in raw and not raw.get("columns"):
        raise RuntimeError(str(raw["error"]))
    columns = raw.get("columns") or []
    rows = raw.get("rows") or raw.get("data") or []
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
        elif isinstance(row, (list, tuple)):
            out.append({columns[i]: row[i] for i in range(min(len(columns), len(row)))})
    return out


def first_row(raw: Any) -> dict[str, Any] | None:
    rows = parse_query_result(raw)
    return rows[0] if rows else None


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
    """Impala-friendly signals SQL (aggregate CTEs; avoid scalar COUNT(*)>0)."""
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


def _json_field(value: Any, *, fallback: Any = None) -> str:
    if value is None:
        value = fallback
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return sql_quote(value)
    return sql_quote(json.dumps(value, default=str))


def insert_audit_event_sql(
    database: str,
    branch_name: str,
    event: dict[str, Any],
) -> str:
    db = validate_ident(database, "database")
    branch = validate_ident(branch_name, "branch")
    ref = f"{db}.agent_run_audit.branch_{branch}"
    cols = [
        "run_id",
        "event_ts",
        "claim_id",
        "event_type",
        "next_step",
        "agent_role",
        "lane",
        "needs_llm",
        "terminal",
        "reason_probe_ids",
        "payload_json",
    ]
    values = [
        sql_quote(event.get("run_id")),
        f"CAST({sql_quote(event.get('event_ts'))} AS TIMESTAMP)"
        if event.get("event_ts")
        else "CURRENT_TIMESTAMP()",
        sql_quote(event.get("claim_id")),
        sql_quote(event.get("event_type")),
        sql_quote(event.get("next_step")),
        sql_quote(event.get("agent_role")),
        sql_quote(event.get("lane")),
        sql_quote(event.get("needs_llm")),
        sql_quote(event.get("terminal")),
        _json_field(event.get("reason_probe_ids")),
        _json_field(event.get("payload_json"), fallback=event),
    ]
    return f"INSERT INTO {ref} ({', '.join(cols)}) VALUES ({', '.join(values)})"


def insert_audit_evidence_sql(
    database: str,
    branch_name: str,
    evidence: dict[str, Any],
) -> str:
    db = validate_ident(database, "database")
    branch = validate_ident(branch_name, "branch")
    ref = f"{db}.agent_run_evidence.branch_{branch}"
    cols = [
        "run_id",
        "evidence_ts",
        "claim_id",
        "evidence_type",
        "probe_id",
        "content_format",
        "content_text",
        "content_uri",
    ]
    values = [
        sql_quote(evidence.get("run_id")),
        f"CAST({sql_quote(evidence.get('evidence_ts'))} AS TIMESTAMP)"
        if evidence.get("evidence_ts")
        else "CURRENT_TIMESTAMP()",
        sql_quote(evidence.get("claim_id")),
        sql_quote(evidence.get("evidence_type")),
        sql_quote(evidence.get("probe_id")),
        sql_quote(evidence.get("content_format") or "json"),
        sql_quote(evidence.get("content_text") or json.dumps(evidence, default=str)),
        sql_quote(evidence.get("content_uri")),
    ]
    return f"INSERT INTO {ref} ({', '.join(cols)}) VALUES ({', '.join(values)})"


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
