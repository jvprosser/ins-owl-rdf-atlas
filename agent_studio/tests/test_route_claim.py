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
    assert case["missing_docket_or_counsel"] is True
    assert case["discovery_aging"] is False
    assert decision["next_step"] == "CompleteLitigationFile"
    assert decision["agent_role"] == "LitigationAgent"
    assert "needs_llm" not in decision
    assert "create_litigation_task" in decision["allowed_tools"]


def _signals_litigation_file_complete(**overrides: object) -> dict:
    row = {
        "has_litigation_case": True,
        "litigation_case_id": 9101,
        "docket_number": "2025-CV-4412",
        "defense_counsel_party_id": 9,
        "plaintiff_counsel_party_id": 9,
        "served_date": "2025-08-05",
        "filed_date": "2025-08-01",
        "closed_date": None,
        "litigation_status_code": "IN_DISCOVERY",
        "has_police_report": True,
        "has_fault_determination": True,
    }
    row.update(overrides)
    return row


def test_route_litigation_discovery_aging():
    spine = _spine_401()
    spine["litigation_indicator"] = True
    spine["subrogation_indicator"] = False
    case = build_claim_graph(402, spine=spine, signals=_signals_litigation_file_complete())
    decision = route_claim(case, 402)
    assert case["missing_docket_or_counsel"] is False
    assert case["discovery_aging"] is True
    assert decision["next_step"] == "EscalateDiscovery"
    assert decision["agent_role"] == "LitigationAgent"
    assert "R1.2b" in decision["reason_probe_ids"]
    assert decision["routing_reason"] == (
        "Discovery has been open more than 90 days → EscalateDiscovery."
    )
    assigned = [c for c in decision["checks"] if c["status"] == "assigned"]
    assert len(assigned) == 1
    assert assigned[0]["probe_id"] == "R1.2b"
    assert assigned[0]["detail"] == "Discovery has been open more than 90 days"
    assert decision["later_checks_not_run"] is True
    assert decision["later_checks_note"] == "Later playbook checks were not run."


def test_route_litigation_support_letter():
    spine = _spine_401()
    spine["litigation_indicator"] = True
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        402,
        spine=spine,
        signals=_signals_litigation_file_complete(
            litigation_status_code="ANSWERED",
            filed_date="2026-08-01",
        ),
    )
    decision = route_claim(case, 402)
    assert case["missing_docket_or_counsel"] is False
    assert case["discovery_aging"] is False
    assert decision["next_step"] == "LitigationSupport"
    assert decision["agent_role"] == "LitigationAgent"
    assert "needs_llm" not in decision
    assert decision["letter_on_request"] is True
    assert "save_claim_letter" in decision["allowed_tools"]
    assert "will not be drafted unless you ask" in (decision["letter_note"] or "")
    assert "will not be drafted unless you ask" in decision["routing_summary"]


def test_route_closed_terminal():
    spine = _spine_401()
    spine["claim_status_code"] = "CLOSED"
    spine["subrogation_indicator"] = False
    case = build_claim_graph(403, spine=spine, signals={})
    decision = route_claim(case, 403)
    assert decision["next_step"] == "CloseoutAudit"
    assert decision["terminal"] is True
    assert decision["routing_reason"] == "Claim is closed → CloseoutAudit."
    assert decision["checks"][-1]["status"] == "assigned"
    assert decision["checks"][-1]["detail"] == "Claim is closed"
    assert {c["status"] for c in decision["checks"][:-1]} == {"did_not_apply"}
    assert decision["later_checks_not_run"] is True


def test_route_denied_terminal():
    spine = _spine_401()
    spine["claim_status_code"] = "DENIED"
    spine["subrogation_indicator"] = False
    case = build_claim_graph(401, spine=spine, signals={"insured_operator_cited": True})
    decision = route_claim(case, 401)
    assert decision["next_step"] == "DenyAudit"
    assert decision["agent_role"] == "DenyAgent"
    assert decision["lane"] == "DENY"
    assert decision["terminal"] is True
    assert decision["letter_on_request"] is True
    assert "get_deny_view" in decision["allowed_tools"]
    assert "deny_claim" not in decision["allowed_tools"]
    assert "save_claim_letter" in decision["allowed_tools"]
    assert "promote_audit_run" in decision["allowed_tools"]
    assert decision["routing_reason"] == "Claim is denied → DenyAudit."
    assert "will not be drafted unless you ask" in decision["routing_summary"]
    assert "R1.1d" in decision["reason_probe_ids"]


def test_route_closed_beats_denied_and_exclusions():
    spine = _spine_401()
    spine["claim_status_code"] = "CLOSED"
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        403,
        spine=spine,
        signals={
            "insured_operator_cited": True,
            "unlawful_operation_exclusion": True,
        },
    )
    decision = route_claim(case, 403)
    assert decision["next_step"] == "CloseoutAudit"
    assert decision["agent_role"] == "CloseoutAgent"
    assert "deny_claim" not in decision["allowed_tools"]


def test_route_insured_cited_human_review():
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        401,
        spine=spine,
        signals={
            "insured_operator_cited": True,
            "unlawful_operation_exclusion": True,
            "has_police_report": True,
            "has_fault_determination": True,
        },
    )
    decision = route_claim(case, 401)
    assert case["insured_operator_cited"] is True
    assert decision["next_step"] == "HumanCitationReview"
    assert decision["agent_role"] == "HumanReviewAgent"
    assert decision["terminal"] is True
    assert decision["letter_on_request"] is False
    assert "get_deny_view" in decision["allowed_tools"]
    assert "write_audit_event" in decision["allowed_tools"]
    assert "deny_claim" not in decision["allowed_tools"]
    assert "save_claim_letter" not in decision["allowed_tools"]
    assert decision["routing_reason"] == (
        "Insured operator was cited → HumanCitationReview."
    )
    assert "R5.2" in decision["reason_probe_ids"]


def test_route_unlawful_operation_deny():
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        401,
        spine=spine,
        signals={"unlawful_operation_exclusion": True},
    )
    decision = route_claim(case, 401)
    assert decision["next_step"] == "DenyUnlawfulOperation"
    assert decision["agent_role"] == "DenyAgent"
    assert decision["lane"] == "DENY"
    assert decision["terminal"] is True
    assert decision["letter_on_request"] is True
    assert "deny_claim" in decision["allowed_tools"]
    assert "get_deny_view" in decision["allowed_tools"]
    assert "save_claim_letter" in decision["allowed_tools"]
    assert decision["routing_reason"] == (
        "Insured operator has an unlawful-operation exclusion → DenyUnlawfulOperation."
    )
    assert "R6.1" in decision["reason_probe_ids"]


def test_route_lifts_deny_flag_from_nested_signals():
    """build_claim_graph pin 8f60419 nested MCP signals but omitted R6 fields."""
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        404,
        spine=spine,
        signals={
            "unlawful_operation_exclusion": True,
            "has_police_report": True,
            "has_fault_determination": True,
        },
    )
    stale = dict(case)
    for key in (
        "unlawful_operation_exclusion",
        "excluded_operator_exclusion",
        "policy_not_in_force_on_loss",
        "insured_operator_cited",
    ):
        stale.pop(key, None)
    assert "unlawful_operation_exclusion" not in stale
    assert stale["signals"]["unlawful_operation_exclusion"] is True
    decision = route_claim(stale, 404)
    assert decision["next_step"] == "DenyUnlawfulOperation"
    assert decision["agent_role"] == "DenyAgent"
    assert "R6.1" in decision["reason_probe_ids"]


def test_route_lifts_intake_flag_from_nested_signals():
    """Root default false must not steal R2.0 when nested MCP signals have the number."""
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        401,
        spine=spine,
        signals={
            "has_police_report": False,
            "has_incident_report_number": True,
            "incident_report_number": "SPD-25-11887",
        },
    )
    stale = dict(case)
    stale["has_incident_report_number"] = False
    stale["incident_report_number"] = None
    decision = route_claim(stale, 401)
    assert decision["next_step"] == "RequestPoliceReport"
    assert "R2.1" in decision["reason_probe_ids"]


def test_route_excluded_operator_deny():
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        401,
        spine=spine,
        signals={"excluded_operator_exclusion": True},
    )
    decision = route_claim(case, 401)
    assert decision["next_step"] == "DenyExcludedDriver"
    assert decision["agent_role"] == "DenyAgent"
    assert "deny_claim" in decision["allowed_tools"]
    assert "R6.2" in decision["reason_probe_ids"]


def test_route_lapsed_policy_deny():
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        401,
        spine=spine,
        signals={"policy_not_in_force_on_loss": True},
    )
    decision = route_claim(case, 401)
    assert decision["next_step"] == "DenyLapsedPolicy"
    assert decision["agent_role"] == "DenyAgent"
    assert "deny_claim" in decision["allowed_tools"]
    assert decision["routing_reason"] == (
        "Policy was not in force on the loss date → DenyLapsedPolicy."
    )
    assert "R6.3" in decision["reason_probe_ids"]


def test_route_missing_police_report():
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        401,
        spine=spine,
        signals={
            "has_police_report": False,
            "has_incident_report_number": True,
            "incident_report_number": "SPD-25-11887",
            "has_fault_determination": True,
        },
    )
    decision = route_claim(case, 401)
    assert decision["next_step"] == "RequestPoliceReport"
    assert "get_pd_view" in decision["allowed_tools"]
    assert "create_pd_task" in decision["allowed_tools"]
    assert "save_claim_letter" in decision["allowed_tools"]
    assert decision["letter_on_request"] is True
    assert "police-report request letter" in (decision["letter_note"] or "")
    assert decision["routing_reason"] == "No police report on file → RequestPoliceReport."
    assert decision["checks"][-1]["probe_id"] == "R2.1"
    assert decision["checks"][-1]["status"] == "assigned"
    assert "not_checked" not in {c["status"] for c in decision["checks"]}
    assert decision["later_checks_not_run"] is True
    summary = decision["routing_summary"]
    assert "Why this routing: No police report on file → RequestPoliceReport." in summary
    assert "will not be drafted unless you ask" in summary
    assert "assigned this work" in summary
    assert "R2.1" not in summary


def test_police_report_id_counts_as_report_on_file():
    """Omitted/false has_police_report must not steal R2.1 when MCP sent an id."""
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        401,
        spine=spine,
        signals={
            "has_police_report": False,
            "police_report_id": 5301,
            "has_incident_report_number": True,
            "incident_report_number": "SPD-25-11887",
            "has_fault_determination": False,
        },
    )
    assert case["has_police_report"] is True
    decision = route_claim(case, 401)
    assert decision["next_step"] == "DetermineFault"
    assert decision["checks"][-1]["probe_id"] == "R2.2"
    assert decision["checks"][-1]["status"] == "assigned"


def test_route_collect_incident_report_number():
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        401,
        spine=spine,
        signals={"has_police_report": False, "has_incident_report_number": False},
    )
    decision = route_claim(case, 401)
    assert decision["next_step"] == "CollectIncidentReportNumber"
    assert decision["agent_role"] == "PdClaimsAgent"
    assert "create_pd_task" in decision["allowed_tools"]
    assert "save_claim_letter" in decision["allowed_tools"]
    assert decision["letter_on_request"] is False
    assert "incident report number" in (decision["letter_note"] or "")
    assert "only if you ask" not in (decision["letter_note"] or "")
    assert "only if you ask" not in decision["routing_summary"]
    assert "R2.0" in decision["reason_probe_ids"]
    assert decision["checks"][-1]["probe_id"] == "R2.0"


def test_route_determine_fault():
    spine = _spine_401()
    spine["subrogation_indicator"] = False
    case = build_claim_graph(
        401,
        spine=spine,
        signals={"has_police_report": True, "has_fault_determination": False},
    )
    decision = route_claim(case, 401)
    assert decision["next_step"] == "DetermineFault"
    assert decision["agent_role"] == "PdClaimsAgent"
    assert "get_pd_view" in decision["allowed_tools"]
    assert "create_pd_task" in decision["allowed_tools"]
    assert "save_claim_letter" not in decision["allowed_tools"]
    assert decision["letter_on_request"] is False
    assert decision["letter_note"] is None


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
    assert "get_pd_view" in decision["allowed_tools"]
    assert "create_pd_task" in decision["allowed_tools"]
    assert decision["routing_reason"] == (
        "Collision or comprehensive coverage is present → PdClaimsReview."
    )
    assert decision["later_checks_not_run"] is False
    assert decision["later_checks_note"] is None
    assert decision["checks"][-1]["status"] == "assigned"
