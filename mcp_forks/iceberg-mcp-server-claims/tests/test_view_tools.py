"""Unit tests for specialist view helpers (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims.tools import view_tools


def test_get_litigation_view_shapes():
    def fake(sql: str):
        assert "litigation_case" in sql
        assert "402" in sql
        return [
            {
                "litigation_case_id": 9101,
                "litigation_status_code": "IN_DISCOVERY",
                "docket_number": "2025-CV-4412",
            }
        ]

    raw = view_tools.get_litigation_view("402", "car_insurance_claims", query_rows=fake)
    payload = json.loads(raw)
    assert payload["claim_id"] == 402
    assert payload["litigation_cases"][0]["litigation_case_id"] == 9101


def test_get_bi_view_shapes():
    def fake(sql: str):
        assert "claim_injury" in sql
        return [{"claim_injury_id": 5501, "injury_severity_code": "MODERATE"}]

    raw = view_tools.get_bi_view("402", query_rows=fake)
    assert json.loads(raw)["injuries"][0]["claim_injury_id"] == 5501


def test_get_subrogation_view_shapes():
    def fake(sql: str):
        assert "subrogation_case" in sql
        return [{"subrogation_case_id": 8801, "subrogation_status_code": "NEGOTIATING"}]

    raw = view_tools.get_subrogation_view("401", query_rows=fake)
    assert json.loads(raw)["subrogation_cases"][0]["subrogation_case_id"] == 8801
