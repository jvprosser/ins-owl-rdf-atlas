"""Offline tests: no MCP required (inject spine dicts)."""

from __future__ import annotations

from ins_claims_agent.graph.build_claim_graph import build_claim_graph
from ins_claims_agent.graph.route_claim import route_claim
from ins_claims_agent.graph.validate_graph import validate_claim_graph


def _spine_401() -> dict:
    return {
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
        "vin": "1HGBH41JXMN109186",
        "policy_covers_vehicle": True,
        "policy_coverage_id": 3001,
        "coverage_type_code": "COLLISION",
        "claim_lifecycle_id": 7001,
        "roles": [
            {"claim_party_role_id": 6001, "role_type_code": "INSURED", "party_id": 1},
            {"claim_party_role_id": 6002, "role_type_code": "ADJUSTER", "party_id": 4},
        ],
    }


def _signals_ready_for_subro() -> dict:
    """Police/fault present so R2 gaps do not preempt R4.1."""
    return {
        "has_subrogation_case": False,
        "has_police_report": True,
        "police_report_id": 5301,
        "has_fault_determination": True,
        "fault_determination_id": 5401,
    }


def test_build_and_validate_spine():
    case = build_claim_graph(401, spine=_spine_401(), signals=_signals_ready_for_subro())
    report = validate_claim_graph(case, 401)
    assert report["passed"] is True
    assert case["claim_exists"] is True


def test_route_subrogation_gap():
    case = build_claim_graph(401, spine=_spine_401(), signals=_signals_ready_for_subro())
    decision = route_claim(case, 401)
    assert decision["next_step"] == "OpenSubrogationCase"
    assert decision["agent_role"] == "SubrogationAgent"
    assert decision["terminal"] is False


def test_route_litigation():
    spine = _spine_401()
    spine["litigation_indicator"] = True
    spine["subrogation_indicator"] = False
    case = build_claim_graph(402, spine=spine, signals={})
    decision = route_claim(case, 402)
    assert decision["next_step"] == "LitigationSupport"
    assert decision["agent_role"] == "LitigationAgent"


def test_route_closed_terminal():
    spine = _spine_401()
    spine["claim_status_code"] = "CLOSED"
    spine["subrogation_indicator"] = False
    case = build_claim_graph(403, spine=spine, signals={})
    decision = route_claim(case, 403)
    assert decision["next_step"] == "CloseoutAudit"
    assert decision["terminal"] is True


def test_route_missing_police_report():
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        401,
        spine=spine,
        signals={"has_police_report": False, "has_fault_determination": True},
    )
    decision = route_claim(case, 401)
    assert decision["next_step"] == "RequestPoliceReport"


def test_route_siu_suspected():
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        401,
        spine=spine,
        signals={
            "has_siu_suspected": True,
            "fraud_assessment_id": 9302,
            "fraud_outcome_code": "SUSPECTED",
            "has_police_report": True,
            "has_fault_determination": True,
        },
    )
    decision = route_claim(case, 401)
    assert decision["next_step"] == "SiuInvestigation"
    assert decision["lane"] == "SIU"


def test_route_unresolved_offer():
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        401,
        spine=spine,
        signals={
            "has_police_report": True,
            "has_fault_determination": True,
            "offers": [{"claim_offer_id": 9, "offer_status_code": "EXTENDED"}],
        },
    )
    decision = route_claim(case, 401)
    assert decision["next_step"] == "FollowUpOffer"


def test_route_pd_lane():
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        401,
        spine=spine,
        signals={
            "has_police_report": True,
            "has_fault_determination": True,
        },
    )
    decision = route_claim(case, 401)
    assert decision["next_step"] == "PdClaimsReview"
    assert decision["lane"] == "PD"
