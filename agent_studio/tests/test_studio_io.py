"""Path A payload normalize + session paths."""

from __future__ import annotations

import json

from ins_claims_agent.graph.build_claim_graph import build_claim_graph
from ins_claims_agent.graph.validate_graph import validate_claim_graph
from ins_claims_agent.studio_io import (
    normalize_signals_payload,
    normalize_spine_payload,
)


def test_normalize_fork_spine_envelope():
    raw = {
        "claim_id": 401,
        "database": "car_insurance_claims",
        "spine": {
            "claim_id": 401,
            "claim_number": "CLM-401",
            "claim_status_code": "OPEN",
            "subrogation_indicator": True,
            "policy_id": 1,
            "insurable_object_id": 2,
            "policy_covers_vehicle": True,
        },
        "roles": [{"claim_party_role_id": 9, "party_id": 4, "role_type_code": "ADJUSTER"}],
    }
    spine = normalize_spine_payload(json.dumps(raw))
    assert spine["claim_number"] == "CLM-401"
    assert spine["roles"][0]["role_type_code"] == "ADJUSTER"


def test_normalize_fork_signals_envelope():
    raw = {
        "claim_id": 401,
        "signals": {"has_subrogation_case": True, "subrogation_case_id": 501},
        "injury_ids": [11],
        "offers": [{"claim_offer_id": 21, "offer_status_code": "EXTENDED"}],
        "payment_ids": [],
        "recovery_ids": [],
    }
    signals = normalize_signals_payload(raw)
    assert signals["has_subrogation_case"] is True
    assert signals["injury_ids"] == [11]
    assert signals["offers"][0]["offer_status_code"] == "EXTENDED"


def test_build_accepts_fork_envelope():
    spine = {
        "claim_id": 401,
        "database": "car_insurance_claims",
        "spine": {
            "claim_id": 401,
            "claim_number": "CLM-2025-000401",
            "claim_status_code": "OPEN",
            "litigation_indicator": False,
            "subrogation_indicator": True,
            "fraudulent_claim_indicator": False,
            "total_loss_indicator": False,
            "loss_event_id": 301,
            "loss_cause_code": "COLLISION",
            "policy_id": 1001,
            "policy_number": "PA-1001",
            "insurable_object_id": 201,
            "vin": "VIN",
            "policy_covers_vehicle": True,
            "policy_coverage_id": 3001,
            "coverage_type_code": "COLLISION",
            "claim_lifecycle_id": 7001,
        },
        "roles": [{"claim_party_role_id": 6002, "role_type_code": "ADJUSTER", "party_id": 4}],
    }
    signals = {
        "signals": {
            "has_subrogation_case": False,
            "has_police_report": True,
            "has_fault_determination": True,
        },
        "injury_ids": [],
        "offers": [],
        "payment_ids": [],
        "recovery_ids": [],
    }
    g = build_claim_graph(401, spine=spine, signals=signals)
    report = validate_claim_graph(g, 401)
    assert report["passed"] is True
