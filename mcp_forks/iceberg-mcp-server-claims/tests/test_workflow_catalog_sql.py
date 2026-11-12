"""Workflow Data SQL stays aligned with the claims MCP statement builders."""

from __future__ import annotations

from pathlib import Path

from iceberg_mcp_server_claims.tools import claim_sql

ROOT = Path(__file__).resolve().parents[3]


def _render(sql: str, bound: dict[str, str]) -> str:
    for key, value in bound.items():
        sql = sql.replace("${" + key + "}", value)
    return sql.strip()


def test_workflow_fnol_spine_sql_matches_mcp():
    text = (ROOT / "catalog" / "sql" / "get_fnol_spine.sql").read_text(encoding="utf-8")
    rendered = _render(text, {"database": "car_insurance_claims", "fnol_id": "88"})
    assert rendered == claim_sql.fnol_spine_sql(88, "car_insurance_claims")


def test_workflow_adjuster_sql_matches_mcp():
    text = (ROOT / "catalog" / "sql" / "list_adjuster_open_claims.sql").read_text(
        encoding="utf-8"
    )
    rendered = _render(text, {"database": "car_insurance_claims", "party_id": "4"})
    assert rendered == claim_sql.list_adjuster_open_claims_sql(4, "car_insurance_claims")
