"""Underwriting pack: generic graph + playbook route. Claims 402 path stays default."""

from __future__ import annotations

import json
from pathlib import Path

from ins_claims_agent.graph.build_case_graph import build_case_graph
from ins_claims_agent.graph.route_claim import route_claim
from ins_claims_agent.graph.validate_graph import validate_claim_graph
from ins_claims_agent.pack import load_pack

REPO = Path(__file__).resolve().parents[2]
UW = REPO / "packs" / "underwriting"


def _payload(label: str, case_id: str) -> dict:
    path = UW / "fixtures" / label / f"{case_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _route_case(monkeypatch, case_id: str, signals: dict | None = None):
    monkeypatch.setenv("PACK_ROOT", str(UW))
    pack = load_pack(UW)
    graph = build_case_graph(
        case_id,
        pack=pack,
        spine=_payload("get_submission_spine", case_id),
        signals=signals if signals is not None else _payload("get_submission_routing_signals", case_id),
    )
    report = validate_claim_graph(graph, case_id)
    decision = route_claim(graph, case_id)
    return report, decision


def test_submission_9101_inspection_boundary(monkeypatch):
    report, decision = _route_case(monkeypatch, "SUB-9101")
    assert report["passed"] is True
    assert decision["next_step"] == "TRIGGER_SURVEY"
    assert decision["agent_role"] == "RiskEngineeringSpecialist"
    assert decision["coworker"] == "Risk Engineering Specialist"
    assert decision["write"] == "write_data_enrichment_request"
    assert decision["task_type_code"] == "INSPECTION"
    assert decision["letter_on_request"] is False
    assert "P1_AWAITING_INSPECTION" in decision["reason_probe_ids"]
    assert decision["checks"][-1]["probe_id"] == "P1_AWAITING_INSPECTION"
    assert decision["checks"][-1]["status"] == "assigned"
    assert decision["playbook_version"] == "1.0.0"
    assert "inspection_completed == false" in decision["matched_cel"]


def test_submission_9103_falls_through_to_bind(monkeypatch):
    report, decision = _route_case(monkeypatch, "SUB-9103")
    assert report["passed"] is True
    assert decision["next_step"] == "AUTO_RATE_AND_BIND"
    assert decision["agent_role"] == "RatingSpecialist"
    assert decision["coworker"] == "Rating Specialist"
    assert decision["write"] == "write_quote_issuance"
    assert "P3_STRAIGHT_THROUGH_BIND" in decision["reason_probe_ids"]
    assert decision["checks"][-1]["probe_id"] == "P3_STRAIGHT_THROUGH_BIND"
    assert decision["checks"][-1]["status"] == "assigned"
    assert decision["matched_cel"] == (
        "is_in_flood_plain == false && prior_claims_count == 0.0"
    )


def test_submission_9100_class_knockout(monkeypatch):
    _, decision = _route_case(monkeypatch, "SUB-9100")
    assert decision["next_step"] == "DECLINE_UNINSURABLE"
    assert decision["coworker"] == "Underwriting Intake Specialist"
    assert decision["write"] == "write_submission_decline"
    assert decision["reason_code"] == "OUT_OF_APPETITE"
    assert decision["letter_on_request"] is True
    assert decision["checks"][-1]["probe_id"] == "P0_OUT_OF_APPETITE"


def test_submission_9106_tiv_beats_inspection(monkeypatch):
    _, decision = _route_case(monkeypatch, "SUB-9106")
    assert decision["next_step"] == "DECLINE_UNINSURABLE"
    assert decision["reason_code"] == "OUT_OF_APPETITE"
    assert decision["checks"][-1]["probe_id"] == "P0_OUT_OF_APPETITE"
    assert "P1_AWAITING_INSPECTION" not in [
        c["probe_id"] for c in decision["checks"] if c["status"] == "assigned"
    ]


def test_submission_9102_survey_then_flood_referral(monkeypatch):
    _, first = _route_case(monkeypatch, "SUB-9102")
    assert first["next_step"] == "TRIGGER_SURVEY"
    assert first["checks"][-1]["probe_id"] == "P1_AWAITING_INSPECTION"

    signals = _payload("get_submission_routing_signals", "SUB-9102")
    signals["signals"]["inspection_completed"] = True
    _, second = _route_case(monkeypatch, "SUB-9102", signals=signals)
    assert second["next_step"] == "REFER_TO_SENIOR_UW"
    assert second["coworker"] == "Senior Underwriter"
    assert second["write"] == "write_referral_queue"
    assert second["checks"][-1]["probe_id"] == "P2_SENIOR_UW_ESCALATION"


def test_submission_9104_senior_referral(monkeypatch):
    _, decision = _route_case(monkeypatch, "SUB-9104")
    assert decision["next_step"] == "REFER_TO_SENIOR_UW"
    assert decision["write"] == "write_referral_queue"
    assert decision["checks"][-1]["probe_id"] == "P2_SENIOR_UW_ESCALATION"


def test_unassigned_9100_still_declines(monkeypatch):
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["has_underwriter"] = False
    _, decision = _route_case(monkeypatch, "SUB-9100", signals=signals)
    assert decision["next_step"] == "DECLINE_UNINSURABLE"
    assert decision["checks"][-1]["probe_id"] == "P0_OUT_OF_APPETITE"


def test_submission_9107_assign_then_bind(monkeypatch):
    _, missing = _route_case(monkeypatch, "SUB-9107")
    assert missing["next_step"] == "AssignUnderwriter"
    assert missing["agent_role"] == "DataQualityAgent"
    assert missing["coworker"] is None
    assert missing["write"] == "write_audit_event"
    assert missing["lane"] == "DATA_QUALITY"
    assert missing["checks"][-1]["probe_id"] == "U0_ASSIGN_UNDERWRITER"

    signals = _payload("get_submission_routing_signals", "SUB-9107")
    signals["signals"]["has_underwriter"] = True
    _, owned = _route_case(monkeypatch, "SUB-9107", signals=signals)
    assert owned["next_step"] == "AUTO_RATE_AND_BIND"
    assert owned["write"] == "write_quote_issuance"


def test_submission_9105_human_review(monkeypatch):
    _, decision = _route_case(monkeypatch, "SUB-9105")
    assert decision["next_step"] == "HUMAN_UW_REVIEW"
    assert decision["coworker"] == "Underwriting Review Agent"
    assert decision["write"] == "write_audit_event"
    assert decision["lane"] == "REVIEW"
    assert "matched_cel" not in decision
    assert decision["playbook_version"] == "1.0.0"
    assert {c["status"] for c in decision["checks"]} == {"did_not_apply"}
