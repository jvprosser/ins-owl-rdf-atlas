"""Adjuster open-claim ids. Same SQL as MCP list_adjuster_open_claims."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_GUI_ROOT = Path(__file__).resolve().parents[2]
_STATIC_CLAIMS = _GUI_ROOT / "claims.json"
DEFAULT_PARTY_ID = 4


def list_adjuster_open_claims_sql(party_id: int | str, database: str) -> str:
    if not _IDENT_RE.match(database):
        raise ValueError(f"Invalid database: {database!r}")
    pid = int(party_id)
    return f"""
SELECT
  c.claim_id,
  c.claim_number,
  c.claim_status_code,
  pe.first_name,
  pe.last_name
FROM {database}.claim c
INNER JOIN {database}.claim_party_role r
  ON r.claim_id = c.claim_id
 AND r.role_type_code = 'ADJUSTER'
 AND r.is_current_assignment = TRUE
 AND r.party_id = {pid}
LEFT JOIN {database}.person pe ON pe.party_id = r.party_id
WHERE UPPER(COALESCE(c.claim_status_code, '')) <> 'CLOSED'
ORDER BY c.claim_id
""".strip()


def _static_payload() -> dict[str, Any]:
    return json.loads(_STATIC_CLAIMS.read_text(encoding="utf-8"))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _query_impala(sql: str) -> list[dict[str, Any]]:
    from impala.dbapi import connect

    host = os.getenv("IMPALA_HOST")
    conn = connect(
        host=host,
        port=int(os.getenv("IMPALA_PORT", "443")),
        user=os.getenv("IMPALA_USER", "username"),
        password=os.getenv("IMPALA_PASSWORD", "password"),
        database=os.getenv("IMPALA_DATABASE", "car_insurance_claims"),
        auth_mechanism=os.getenv("IMPALA_AUTH_MECHANISM", "LDAP"),
        use_http_transport=_env_bool("IMPALA_USE_HTTP_TRANSPORT", True),
        http_path=os.getenv("IMPALA_HTTP_PATH", "cliservice"),
        use_ssl=_env_bool("IMPALA_USE_SSL", True),
    )
    try:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [str(col[0]).lower() for col in (cur.description or [])]
        rows = cur.fetchall()
        cur.close()
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append({columns[i]: row[i] for i in range(min(len(columns), len(row)))})
        return out
    finally:
        conn.close()


def load_claims_payload(
    *,
    party_id: int | str | None = None,
    query_rows: Callable[[str], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Return ``{"claims": ["401", ...]}``. Lake when IMPALA_HOST is set; else static file."""
    pid = int(party_id or os.getenv("ADJUSTER_PARTY_ID") or DEFAULT_PARTY_ID)
    database = os.getenv("IMPALA_DATABASE", "car_insurance_claims")
    sql = list_adjuster_open_claims_sql(pid, database)
    if query_rows is None and not os.getenv("IMPALA_HOST"):
        return _static_payload()
    try:
        rows = query_rows(sql) if query_rows is not None else _query_impala(sql)
    except Exception:
        return _static_payload()
    ids = [str(r["claim_id"]) for r in rows if r.get("claim_id") not in (None, "")]
    return {"claims": ids}
