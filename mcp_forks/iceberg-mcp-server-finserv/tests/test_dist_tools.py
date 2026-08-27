"""Unit tests for distribution helpers (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_finserv.tools import dist_tools, sql


def test_spine_sql_contains_request_id_and_db():
    text = sql.distribution_spine_sql(7002, "retirement_distributions")
    assert "distribution_request_id = 7002" in text
    assert "retirement_distributions.distribution_request" in text


def test_signals_sql_is_hold_flag_only():
    text = sql.distribution_routing_signals_sql(7002, "retirement_distributions")
    assert "hold_or_aml_flag" in text
    assert "HARDSHIP_SUBSTANTIATION_MISSING" not in text
    assert "shortfall_amount > 0" not in text
    assert "COUNT(*) > 0" not in text


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
    def fake(query: str):
        if "distribution_exception" in query:
            return [{"reason_code": "HARDSHIP_SUBSTANTIATION_MISSING"}]
        if "distribution_rmd" in query:
            return [{"shortfall_amount": 0}]
        return [{"hold_or_aml_flag": 0}]

    payload = json.loads(
        dist_tools.get_distribution_routing_signals(
            "7002", "retirement_distributions", query_rows=fake
        )
    )
    assert payload["signals"]["hardship_reason_codes"] == [
        "HARDSHIP_SUBSTANTIATION_MISSING"
    ]
    assert payload["signals"]["hold_or_aml_flag"] is False
    assert payload["signals"]["rmd_shortfall_amount"] == 0


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
