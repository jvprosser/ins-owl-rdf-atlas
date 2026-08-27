"""Unit tests for distribution helpers (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_finserv.tools import dist_tools, sql


def test_spine_sql_contains_request_id_and_db():
    text = sql.distribution_spine_sql(7002, "retirement_distributions")
    assert "distribution_request_id = 7002" in text
    assert "retirement_distributions.distribution_request" in text


def test_signals_sql_selects_ingredients_not_derived_booleans():
    text = sql.distribution_routing_signals_sql(7002, "retirement_distributions")
    assert "hold_or_aml_flag" in text
    assert "hardship_category" in text
    assert "requested_amount" in text
    assert "HARDSHIP_SUBSTANTIATION_MISSING" not in text
    assert "shortfall_amount > 0" not in text
    assert "VACATION" not in text


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
                "requested_amount": 8000,
            }
        ]

    payload = json.loads(
        dist_tools.get_distribution_spine("7002", "retirement_distributions", query_rows=fake)
    )
    assert payload["claim_id"] == "7002"
    assert payload["spine"]["distribution_type_code"] == "HARDSHIP"
    assert payload["spine"]["plan_id"] == "401k-alpha"
    assert payload["spine"]["requested_amount"] == 8000.0


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
        if "distribution_court_order" in query:
            return []
        return [
            {
                "hold_or_aml_flag": 0,
                "requested_amount": 8000,
                "hardship_category": "MEDICAL",
                "documented_financial_need_amount": 8000,
                "estimated_tax_withholding_amount": 0,
                "has_participant_self_certified": True,
                "requires_substantiation_audit": True,
                "plan_subject_to_qjsa": False,
                "plan_mandates_loan_exhaustion": False,
                "participant_marital_status": "SINGLE",
                "spousal_consent_verified": False,
                "available_plan_loan_capacity": 0,
                "has_active_qdro_hold": False,
                "prior_emergency_distributions_this_year": 0,
            }
        ]

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
    assert payload["signals"]["hardship_category"] == "MEDICAL"
    assert payload["signals"]["requested_amount"] == 8000.0
    assert payload["signals"]["has_participant_self_certified"] is True
    assert payload["signals"]["requires_substantiation_audit"] is True
    assert payload["signals"]["pending_court_orders"] == []


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


def test_compliance_view_shapes_payload():
    def fake(_query: str):
        return [
            {
                "plan_id": "401k-qjsa",
                "participant_id": "P-7014",
                "plan_subject_to_qjsa": True,
                "plan_mandates_loan_exhaustion": False,
                "participant_marital_status": "MARRIED",
                "spousal_consent_verified": False,
            }
        ]

    payload = json.loads(
        dist_tools.get_compliance_view("7014", "retirement_distributions", query_rows=fake)
    )
    assert payload["compliance"]["plan_subject_to_qjsa"] is True
    assert payload["compliance"]["participant_marital_status"] == "MARRIED"


def test_loan_summary_view_shapes_payload():
    def fake(_query: str):
        return [{"available_plan_loan_capacity": 5000, "outstanding_loan_balance": 0, "max_loan_amount": 50000}]

    payload = json.loads(
        dist_tools.get_loan_summary_view("7015", "retirement_distributions", query_rows=fake)
    )
    assert payload["loan"]["available_plan_loan_capacity"] == 5000.0


def test_qdro_details_view_shapes_payload():
    def fake(query: str):
        if "distribution_court_order" in query:
            return [{"court_order_id": 7801, "docket_number": "2026-DR-4412"}]
        return [
            {
                "qdro_id": 7701,
                "is_active": True,
                "order_status_code": "ACTIVE",
                "alternate_payee_name": "Alternate Payee",
                "hold_reason": "Domestic relations order hold",
            }
        ]

    payload = json.loads(
        dist_tools.get_qdro_details_view("7017", "retirement_distributions", query_rows=fake)
    )
    assert payload["qdro"][0]["qdro_id"] == 7701
    assert payload["pending_court_orders"][0]["docket_number"] == "2026-DR-4412"
