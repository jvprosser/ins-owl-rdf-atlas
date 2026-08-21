"""Unit tests for claim helpers (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims.tools import claim_sql, claim_tools


def test_claim_spine_sql_contains_claim_id_and_db():
    sql = claim_sql.claim_spine_sql(401, "car_insurance_claims")
    assert "claim_id = 401" in sql
    assert "car_insurance_claims.claim" in sql
    assert "policy_covers_vehicle" in sql


def test_claim_routing_signals_sql_uses_cte_not_scalar_count_gt():
    sql = claim_sql.claim_routing_signals_sql(402, "car_insurance_claims")
    assert sql.lstrip().upper().startswith("WITH")
    assert "COUNT(*) > 0" not in sql
    assert "CROSS JOIN" in sql
    assert "claim_id = 402" in sql
    assert "docket_number" in sql
    assert "missing_docket_or_counsel" in sql
    assert "discovery_aging" in sql
    assert "DATEDIFF" in sql
    assert "insured_operator_cited" in sql
    assert "unlawful_operation_exclusion" in sql
    assert "CAST(ld.impairment_suspected_indicator AS STRING)" in sql
    assert "excluded_operator_exclusion" in sql
    assert "policy_not_in_force_on_loss" in sql
    assert "has_incident_report_number" in sql
    assert "claim_police_intake" in sql
    assert "INSURED_OPERATOR" in sql


def test_get_claim_spine_shapes_payload():
    def fake_query(sql: str):
        if "claim_party_role" in sql:
            return [
                {
                    "claim_party_role_id": 1,
                    "party_id": 10,
                    "role_type_code": "ADJUSTER",
                    "is_current_assignment": True,
                }
            ]
        return [
            {
                "claim_id": 401,
                "claim_number": "CLM-401",
                "claim_status_code": "OPEN",
                "litigation_indicator": 0,
                "subrogation_indicator": 1,
                "fraudulent_claim_indicator": False,
                "total_loss_indicator": "false",
                "loss_event_id": 1,
                "loss_cause_code": "COLLISION",
                "policy_id": 100,
                "policy_number": "P-100",
                "insurable_object_id": 50,
                "vin": "VIN1",
                "policy_covers_vehicle": True,
                "policy_coverage_id": 9,
                "coverage_type_code": "PD",
                "claim_lifecycle_id": 7,
            }
        ]

    raw = claim_tools.get_claim_spine("401", "car_insurance_claims", query_rows=fake_query)
    payload = json.loads(raw)
    assert payload["claim_id"] == 401
    assert payload["spine"]["claim_number"] == "CLM-401"
    assert payload["spine"]["subrogation_indicator"] is True
    assert payload["spine"]["litigation_indicator"] is False
    assert len(payload["roles"]) == 1


def test_get_claim_spine_not_found():
    raw = claim_tools.get_claim_spine(
        "999", "car_insurance_claims", query_rows=lambda _sql: []
    )
    payload = json.loads(raw)
    assert "error" in payload
    assert "not found" in payload["error"].lower()


def test_get_claim_routing_signals_shapes_payload():
    def fake_query(sql: str):
        # Match narrow id/list queries first; signals SQL also mentions these tables.
        if sql.strip().startswith("SELECT claim_injury_id"):
            return [{"claim_injury_id": 11}]
        if "SELECT claim_offer_id, offer_status_code" in sql:
            return [{"claim_offer_id": 21, "offer_status_code": "EXTENDED"}]
        if sql.strip().startswith("SELECT claim_payment_id"):
            return [{"claim_payment_id": 31}]
        if sql.strip().startswith("SELECT claim_recovery_id"):
            return []
        assert "has_subrogation_case" in sql
        return [
            {
                "has_subrogation_case": 1,
                "subrogation_case_id": 501,
                "subrogation_status_code": "OPEN",
                "has_litigation_case": 0,
                "litigation_case_id": None,
                "has_injury": 1,
                "has_police_report": 0,
                "police_report_id": None,
                "has_fault_determination": 0,
                "fault_determination_id": None,
                "has_offer": 1,
                "has_unresolved_offer": 1,
                "has_accepted_offer": 0,
                "has_loss_payment": 1,
                "has_recovery": 0,
                "has_current_reserve": 1,
                "has_siu_suspected": 0,
                "fraud_assessment_id": None,
                "fraud_outcome_code": None,
                "has_document": 1,
            }
        ]

    raw = claim_tools.get_claim_routing_signals(
        "401", "car_insurance_claims", query_rows=fake_query
    )
    payload = json.loads(raw)
    assert payload["signals"]["has_subrogation_case"] is True
    assert payload["signals"]["has_litigation_case"] is False
    assert payload["injury_ids"] == [11]
    assert payload["payment_ids"] == [31]
    assert payload["offers"][0]["offer_status_code"] == "EXTENDED"


def test_invalid_database_rejected():
    try:
        claim_sql.validate_ident("bad;drop", "database")
        assert False, "expected ValueError"
    except ValueError:
        pass
