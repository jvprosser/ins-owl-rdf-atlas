"""Unit tests for distribution helpers (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_finserv.tools import dist_tools, sql


def test_spine_sql_contains_request_id_and_db():
    text = sql.distribution_spine_sql(7002, "retirement_distributions")
    assert "distribution_request_id = 7002" in text
    assert "retirement_distributions.distribution_request" in text


def test_signals_sql_uses_cte_not_scalar_count_gt():
    text = sql.distribution_routing_signals_sql(7002, "retirement_distributions")
    assert text.lstrip().upper().startswith("WITH")
    assert "COUNT(*) > 0" not in text
    assert "CROSS JOIN" in text
    assert "HARDSHIP_SUBSTANTIATION_MISSING" in text


def test_get_distribution_spine_shapes_payload():
    def fake(_query: str):
        return [
            {
                "distribution_request_id": 7002,
                "request_status_code": "OPEN",
                "distribution_type_code": "HARDSHIP",
                "plan_id": "401k-alpha",
                "participant_id": "P-7002",
                "hold_or_aml_flag": False,
            }
        ]

    payload = json.loads(
        dist_tools.get_distribution_spine("7002", "retirement_distributions", query_rows=fake)
    )
    assert payload["claim_id"] == "7002"
    assert payload["spine"]["distribution_type_code"] == "HARDSHIP"
    assert payload["spine"]["plan_id"] == "401k-alpha"


def test_get_distribution_spine_not_found():
    payload = json.loads(
        dist_tools.get_distribution_spine(
            "9999", "retirement_distributions", query_rows=lambda _q: []
        )
    )
    assert "error" in payload
    assert "not found" in payload["error"].lower()


def test_get_routing_signals_shapes_payload():
    def fake(_query: str):
        return [
            {
                "hold_or_aml_flag": 0,
                "hardship_substantiation_missing": 1,
                "rmd_underpaid": 0,
            }
        ]

    payload = json.loads(
        dist_tools.get_distribution_routing_signals(
            "7002", "retirement_distributions", query_rows=fake
        )
    )
    assert payload["signals"]["hardship_substantiation_missing"] is True
    assert payload["signals"]["hold_or_aml_flag"] is False
    assert payload["signals"]["rmd_underpaid"] is False


def test_exception_view_parses_required_docs_json():
    def fake(_query: str):
        return [
            {
                "exception_id": "EX-7002",
                "reason_code": "HARDSHIP_SUBSTANTIATION_MISSING",
                "queue": "ExceptionQueue",
                "required_docs": '["medical_bills","hardship_attestation"]',
            }
        ]

    payload = json.loads(
        dist_tools.get_distribution_exception_view(
            "7002", "retirement_distributions", query_rows=fake
        )
    )
    assert payload["exceptions"][0]["exception_id"] == "EX-7002"
    assert payload["exceptions"][0]["required_docs"] == [
        "medical_bills",
        "hardship_attestation",
    ]


def test_rmd_view_shapes_payload():
    def fake(_query: str):
        return [
            {
                "tax_year": 2026,
                "required_amount": 12500.0,
                "paid_amount": 8000.0,
                "shortfall_amount": 4500.0,
                "deadline": "2026-12-31",
            }
        ]

    payload = json.loads(
        dist_tools.get_rmd_view("7003", "retirement_distributions", query_rows=fake)
    )
    assert payload["rmd"]["shortfall_amount"] == 4500.0
    assert payload["rmd"]["tax_year"] == 2026
