"""Unit tests for specialist view helpers (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims.tools import view_tools


def _select_list(sql: str) -> str:
    return sql.split("FROM", 1)[0]


def test_get_litigation_view_shapes():
    def fake(sql: str):
        select = _select_list(sql)
        assert "litigation_case" in sql
        assert "402" in sql
        assert "docket_number" in select
        assert "venue_country_subdivision_code" in select
        assert "currency_code" in select
        assert "created_at" in select
        assert "litigation_case_id" not in select
        assert "defense_counsel_party_id" not in select
        return [
            {
                "litigation_status_code": "IN_DISCOVERY",
                "docket_number": "2025-CV-4412",
            }
        ]

    raw = view_tools.get_litigation_view("402", "car_insurance_claims", query_rows=fake)
    payload = json.loads(raw)
    assert payload["claim_id"] == 402
    assert payload["litigation_cases"][0]["docket_number"] == "2025-CV-4412"


def test_get_bi_view_shapes():
    def fake(sql: str):
        select = _select_list(sql)
        assert "claim_injury" in sql
        assert "injury_description" in select
        assert "claim_injury_id" not in select
        assert "injured_party_id" not in select
        return [{"injury_severity_code": "MODERATE", "injury_description": "Cervical strain"}]

    raw = view_tools.get_bi_view("402", query_rows=fake)
    assert json.loads(raw)["injuries"][0]["injury_description"] == "Cervical strain"


def test_get_subrogation_view_shapes():
    def fake(sql: str):
        select = _select_list(sql)
        assert "subrogation_case" in sql
        assert "statute_limitations_date" in select
        assert "subrogation_case_id" not in select
        assert "adverse_party_id" not in select
        return [{"subrogation_status_code": "NEGOTIATING", "demand_amount": 5100}]

    raw = view_tools.get_subrogation_view("401", query_rows=fake)
    assert json.loads(raw)["subrogation_cases"][0]["subrogation_status_code"] == "NEGOTIATING"


def test_get_pd_view_shapes():
    def fake(sql: str):
        select = _select_list(sql)
        if "police_report" in sql:
            assert "401" in sql
            assert "narrative_summary" in select
            assert "report_number" in select
            assert "police_report_id" not in select
            assert "loss_event_id" not in select
            assert "agency_party_id" not in select
            return [
                {
                    "report_number": "PD-301",
                    "narrative_summary": "Rear-end collision.",
                }
            ]
        if "fault_determination" in sql:
            assert "notes" in select
            assert "fault_determination_id" not in select
            assert "at_fault_driver_id" not in select
            return [{"insured_fault_percent": 20, "notes": "Adverse primarily at fault."}]
        raise AssertionError(sql)

    raw = view_tools.get_pd_view("401", "car_insurance_claims", query_rows=fake)
    payload = json.loads(raw)
    assert payload["claim_id"] == 401
    assert payload["police_reports"][0]["narrative_summary"] == "Rear-end collision."
    assert payload["fault_determinations"][0]["notes"] == "Adverse primarily at fault."
