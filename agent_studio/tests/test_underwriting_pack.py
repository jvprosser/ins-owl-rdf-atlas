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


def test_submission_9100_class_knockout(monkeypatch):
    _, decision = _route_case(monkeypatch, "SUB-9100")
    assert decision["next_step"] == "DECLINE_UNINSURABLE_CLASS"
    assert decision["coworker"] == "Underwriting Intake Specialist"
    assert decision["write"] == "write_submission_decline"
    assert decision["reason_code"] == "OUT_OF_APPETITE"
    assert decision["letter_on_request"] is True
    assert decision["playbook_version"] == "2.2.0"
    assert decision["checks"][-1]["probe_id"] == "P00_PROHIBITED_CLASS_CODE"


def test_submission_9101_ofac_hold(monkeypatch):
    report, decision = _route_case(monkeypatch, "SUB-9101")
    assert report["passed"] is True
    assert decision["next_step"] == "HOLD_COMPLIANCE_FREEZE"
    assert decision["coworker"] == "Underwriting Review Agent"
    assert decision["write"] == "write_audit_event"
    assert decision["checks"][-1]["probe_id"] == "P01_SANCTIONS_AND_OFAC_FLAG"


def test_submission_9102_loss_frequency_decline(monkeypatch):
    _, decision = _route_case(monkeypatch, "SUB-9102")
    assert decision["next_step"] == "DECLINE_ADVERSE_LOSS_HISTORY"
    assert decision["coworker"] == "Underwriting Intake Specialist"
    assert decision["write"] == "write_submission_decline"
    assert decision["checks"][-1]["probe_id"] == "P02_EXCESSIVE_LOSS_FREQUENCY"


def test_submission_9103_siu_review(monkeypatch):
    _, decision = _route_case(monkeypatch, "SUB-9103")
    assert decision["next_step"] == "REFER_TO_SPECIAL_INVESTIGATIONS"
    assert decision["coworker"] == "Underwriting Review Agent"
    assert decision["write"] == "write_audit_event"
    assert decision["checks"][-1]["probe_id"] == "P10_SIU_HIGH_RISK_TRIGGER"


def test_submission_9104_orders_survey(monkeypatch):
    _, decision = _route_case(monkeypatch, "SUB-9104")
    assert decision["next_step"] == "ORDER_RISK_ENGINEERING_SURVEY"
    assert decision["coworker"] == "Risk Engineering Specialist"
    assert decision["write"] == "write_data_enrichment_request"
    assert decision["task_type_code"] == "INSPECTION"
    assert decision["checks"][-1]["probe_id"] == "P20_HIGH_TIV_REQUIRES_RISK_ENGINEERING"

    signals = _payload("get_submission_routing_signals", "SUB-9104")
    signals["signals"]["has_survey_on_file"] = True
    _, referred = _route_case(monkeypatch, "SUB-9104", signals=signals)
    assert referred["next_step"] == "REFER_SENIOR_PROPERTY_UW"
    assert referred["coworker"] == "Senior Underwriter"
    assert referred["write"] == "write_referral_queue"


def test_submission_9105_protection_class(monkeypatch):
    _, decision = _route_case(monkeypatch, "SUB-9105")
    assert decision["next_step"] == "REFER_PROPERTY_FACULTATIVE_DESK"
    assert decision["coworker"] == "Senior Underwriter"
    assert decision["write"] == "write_referral_queue"
    assert decision["checks"][-1]["probe_id"] == "P31_SUBSTANDARD_PROTECTION_CLASS"


def test_submission_9106_high_value_referral(monkeypatch):
    _, decision = _route_case(monkeypatch, "SUB-9106")
    assert decision["next_step"] == "REFER_SENIOR_PROPERTY_UW"
    assert decision["coworker"] == "Senior Underwriter"
    assert decision["write"] == "write_referral_queue"
    assert decision["checks"][-1]["probe_id"] == "P30_HIGH_VALUE_OR_NON_STANDARD_CONSTRUCTION"


def test_unassigned_9100_still_declines(monkeypatch):
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["has_underwriter"] = False
    _, decision = _route_case(monkeypatch, "SUB-9100", signals=signals)
    assert decision["next_step"] == "DECLINE_UNINSURABLE_CLASS"
    assert decision["checks"][-1]["probe_id"] == "P00_PROHIBITED_CLASS_CODE"


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
    assert owned["next_step"] == "EXECUTE_AUTOMATED_BIND_AND_QUOTE"
    assert owned["write"] == "write_quote_issuance"
    assert owned["checks"][-1]["probe_id"] == "P40_ELIGIBLE_FOR_CLEAN_AUTO_BIND"


def test_wind_tier_orders_cat_model(monkeypatch):
    signals = _payload("get_submission_routing_signals", "SUB-9107")
    signals["signals"]["has_underwriter"] = True
    signals["signals"]["wind_tier"] = 1
    signals["signals"]["has_recent_cat_run"] = False
    _, decision = _route_case(monkeypatch, "SUB-9107", signals=signals)
    assert decision["next_step"] == "TRIGGER_CAT_MODEL_RUN"
    assert decision["coworker"] == "Risk Engineering Specialist"
    assert decision["checks"][-1]["probe_id"] == "P21_COASTAL_CONVECTIVE_CAT_MODEL_MISSING"
