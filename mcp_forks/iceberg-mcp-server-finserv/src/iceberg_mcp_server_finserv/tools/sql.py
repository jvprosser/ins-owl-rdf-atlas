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
  r.hold_or_aml_flag
FROM {db}.distribution_request r
WHERE r.distribution_request_id = {cid}
LIMIT 1
""".strip()


def distribution_routing_signals_sql(claim_id: int | str, database: str) -> str:
    """One-row flags. Avoid scalar COUNT(*)>0 subqueries (Impala Iceberg)."""
    db = validate_ident(database, "database")
    cid = int(claim_id)
    return f"""
WITH
req AS (
  SELECT hold_or_aml_flag
  FROM {db}.distribution_request
  WHERE distribution_request_id = {cid}
),
exc AS (
  SELECT COUNT(*) AS cnt
  FROM {db}.distribution_exception
  WHERE distribution_request_id = {cid}
    AND reason_code = 'HARDSHIP_SUBSTANTIATION_MISSING'
),
rmd AS (
  SELECT COUNT(*) AS cnt
  FROM {db}.distribution_rmd
  WHERE distribution_request_id = {cid}
    AND shortfall_amount > 0
)
SELECT
  COALESCE(req.hold_or_aml_flag, FALSE) AS hold_or_aml_flag,
  (exc.cnt > 0) AS hardship_substantiation_missing,
  (rmd.cnt > 0) AS rmd_underpaid
FROM req
CROSS JOIN exc
CROSS JOIN rmd
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
