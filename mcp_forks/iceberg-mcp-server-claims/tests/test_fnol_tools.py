"""FNOL named reads (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims.tools import claim_sql, fnol_tools


def test_parse_fnol_id_accepts_number_and_business_key():
    assert claim_sql.parse_fnol_id(88) == 88
    assert claim_sql.parse_fnol_id("88") == 88
    assert claim_sql.parse_fnol_id("FNOL-2026-00088") == 88


def test_fnol_signals_sql_uses_cte_not_scalar_count_gt():
    sql = claim_sql.fnol_routing_signals_sql(88, "car_insurance_claims")
    assert sql.lstrip().upper().startswith("WITH")
    assert "COUNT(*) > 0" not in sql
    assert "CROSS JOIN" in sql
    assert "fnol_id = 88" in sql
    assert "fnol_injury" in sql
    assert "fnol_third_party_vehicle" in sql
    spine = claim_sql.fnol_spine_sql("FNOL-2026-00088", "car_insurance_claims")
    assert "fnol_id = 88" in spine
    assert "vehicle_listed_on_policy" in spine
    assert "peril_covered" in spine


def test_get_fnol_spine_shapes_payload():
    def fake_query(sql: str):
        return [
            {
                "fnol_id": 88,
                "fnol_number": "FNOL-2026-00088",
                "triage_status_code": "OPEN",
                "intake_purpose_code": "RECORD_ONLY_NOTIFICATION",
                "estimated_loss_amount": 450,
                "deductible_amount": 1000,
                "policy_id": 1088,
                "insurable_object_id": 288,
                "vehicle_listed_on_policy": True,
                "peril_covered": 1,
            }
        ]

    raw = fnol_tools.get_fnol_spine("88", "car_insurance_claims", query_rows=fake_query)
    payload = json.loads(raw)
    assert payload["fnol_id"] == 88
    assert payload["spine"]["fnol_number"] == "FNOL-2026-00088"
    assert payload["spine"]["vehicle_listed_on_policy"] is True
    assert payload["spine"]["peril_covered"] is True


def test_get_fnol_routing_signals_shapes_payload():
    def fake_query(sql: str):
        if sql.lstrip().upper().startswith("WITH"):
            return [
                {
                    "has_injury": False,
                    "has_third_party_vehicle": 0,
                    "has_unlisted_insured_operator": "false",
                }
            ]
        return [
            {
                "fnol_id": 88,
                "intake_purpose_code": "RECORD_ONLY_NOTIFICATION",
                "triage_status_code": "OPEN",
                "estimated_loss_amount": 450,
                "deductible_amount": 1000,
                "vehicle_listed_on_policy": True,
                "peril_covered": True,
            }
        ]

    raw = fnol_tools.get_fnol_routing_signals(
        "FNOL-2026-00088", "car_insurance_claims", query_rows=fake_query
    )
    payload = json.loads(raw)
    assert payload["fnol_id"] == 88
    signals = payload["signals"]
    assert signals["fnol_exists"] is True
    assert signals["has_injury"] is False
    assert signals["has_third_party_vehicle"] is False
    assert signals["has_unlisted_insured_operator"] is False
    assert signals["estimated_loss_amount"] == 450
    assert signals["deductible_amount"] == 1000
