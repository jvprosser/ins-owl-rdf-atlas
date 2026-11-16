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
    assert decision["playbook_version"] == "2.10.0"
    assert decision["checks"][-1]["probe_id"] == "P00_PROHIBITED_CLASS_CODE"


def test_low_ocr_confidence_routes_before_class_knockout(monkeypatch):
    monkeypatch.setenv("PACK_ROOT", str(UW))
    pack = load_pack(UW)
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["ocr_document_present"] = True
    signals["signals"]["min_ocr_confidence"] = 0.691
    signals["signals"]["low_ocr_spans"] = (
        "page 8 Rostova 0.691; page 8 Elena 0.738; page 6 55.28 0.768; page 8 Vance 0.795"
    )
    graph = build_case_graph(
        "SUB-9100",
        pack=pack,
        spine=_payload("get_submission_spine", "SUB-9100"),
        signals=signals,
    )
    assert "Rostova" in graph["low_ocr_spans"]
    assert "Elena" in graph["low_ocr_spans"]
    assert "55.28" in graph["low_ocr_spans"]
    assert "Vance" in graph["low_ocr_spans"]
    decision = route_claim(graph, "SUB-9100")
    assert decision["next_step"] == "RESOLVE_DOCUMENT_EXCEPTIONS"
    assert decision["coworker"] == "Underwriting Review Agent"
    assert decision["write"] == "write_audit_event"
    assert decision["lane"] == "REVIEW"
    assert decision["exceptions"][0]["probe_id"] == "P0C_LOW_OCR_CONFIDENCE"
    assert decision["exceptions"][0]["next_step"] == "RESOLVE_LOW_CONFIDENCE_OCR"
    assert "Rostova" in decision["exceptions"][0]["fields"]["low_ocr_spans"]
    assert decision["disposition"]["next_step"] == "DECLINE_UNINSURABLE_CLASS"
    assert decision["checks"][-1]["probe_id"] == "P00_PROHIBITED_CLASS_CODE"


def test_sov_coinsurance_under_80_routes_before_class_knockout(monkeypatch):
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["sov_present"] = True
    signals["signals"]["sov_schedule_incomplete"] = False
    signals["signals"]["sov_min_coinsurance_pct"] = 70
    _, decision = _route_case(monkeypatch, "SUB-9100", signals=signals)
    assert decision["next_step"] == "RESOLVE_DOCUMENT_EXCEPTIONS"
    assert decision["exceptions"][0]["next_step"] == "RESOLVE_SOV_SCHEDULE"
    assert decision["exceptions"][0]["fields"]["sov_min_coinsurance_pct"] == 70
    assert decision["disposition"]["next_step"] == "DECLINE_UNINSURABLE_CLASS"
    assert decision["coworker"] == "Underwriting Review Agent"
    assert decision["write"] == "write_audit_event"


def test_rental_worksheet_mismatch_routes_before_class_knockout(monkeypatch):
    monkeypatch.setenv("PACK_ROOT", str(UW))
    pack = load_pack(UW)
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["rental_worksheet_present"] = True
    signals["signals"]["rental_needs_review"] = True
    signals["signals"]["rental_review_detail"] = (
        "selected limit does not match the business income schedule"
    )
    graph = build_case_graph(
        "SUB-9100",
        pack=pack,
        spine=_payload("get_submission_spine", "SUB-9100"),
        signals=signals,
    )
    assert "business income schedule" in graph["rental_review_detail"]
    decision = route_claim(graph, "SUB-9100")
    assert decision["next_step"] == "RESOLVE_DOCUMENT_EXCEPTIONS"
    assert decision["exceptions"][0]["next_step"] == "RESOLVE_RENTAL_VALUE_WORKSHEET"
    assert "business income schedule" in decision["exceptions"][0]["fields"]["rental_review_detail"]
    assert decision["disposition"]["next_step"] == "DECLINE_UNINSURABLE_CLASS"
    assert decision["coworker"] == "Underwriting Review Agent"


def test_oakridge_rental_worksheet_keeps_class_knockout(monkeypatch):
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["rental_worksheet_present"] = True
    signals["signals"]["rental_needs_review"] = False
    signals["signals"]["rental_review_detail"] = ""
    _, decision = _route_case(monkeypatch, "SUB-9100", signals=signals)
    assert decision["next_step"] == "DECLINE_UNINSURABLE_CLASS"
    assert decision["checks"][-1]["probe_id"] == "P00_PROHIBITED_CLASS_CODE"


def test_four_point_aluminum_routes_before_class_knockout(monkeypatch):
    monkeypatch.setenv("PACK_ROOT", str(UW))
    pack = load_pack(UW)
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["four_point_present"] = True
    signals["signals"]["four_point_needs_review"] = True
    signals["signals"]["four_point_review_detail"] = "electrical notes report aluminum wiring"
    graph = build_case_graph(
        "SUB-9100",
        pack=pack,
        spine=_payload("get_submission_spine", "SUB-9100"),
        signals=signals,
    )
    assert "aluminum" in graph["four_point_review_detail"]
    decision = route_claim(graph, "SUB-9100")
    assert decision["next_step"] == "RESOLVE_DOCUMENT_EXCEPTIONS"
    assert decision["exceptions"][0]["next_step"] == "RESOLVE_FOUR_POINT_INSPECTION"
    assert "aluminum" in decision["exceptions"][0]["fields"]["four_point_review_detail"]
    assert decision["disposition"]["next_step"] == "DECLINE_UNINSURABLE_CLASS"


def test_oakridge_four_point_keeps_class_knockout(monkeypatch):
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["four_point_present"] = True
    signals["signals"]["four_point_needs_review"] = False
    signals["signals"]["four_point_review_detail"] = ""
    _, decision = _route_case(monkeypatch, "SUB-9100", signals=signals)
    assert decision["next_step"] == "DECLINE_UNINSURABLE_CLASS"
    assert decision["checks"][-1]["probe_id"] == "P00_PROHIBITED_CLASS_CODE"


def test_unsigned_loss_run_routes_before_class_knockout(monkeypatch):
    monkeypatch.setenv("PACK_ROOT", str(UW))
    pack = load_pack(UW)
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["loss_run_present"] = True
    signals["signals"]["loss_run_needs_review"] = True
    signals["signals"]["loss_run_review_detail"] = "loss run has no authorized signature"
    graph = build_case_graph(
        "SUB-9100",
        pack=pack,
        spine=_payload("get_submission_spine", "SUB-9100"),
        signals=signals,
    )
    assert "authorized signature" in graph["loss_run_review_detail"]
    decision = route_claim(graph, "SUB-9100")
    assert decision["next_step"] == "RESOLVE_DOCUMENT_EXCEPTIONS"
    assert decision["exceptions"][0]["next_step"] == "RESOLVE_LOSS_RUN"
    assert "authorized signature" in decision["exceptions"][0]["fields"]["loss_run_review_detail"]
    assert decision["disposition"]["next_step"] == "DECLINE_UNINSURABLE_CLASS"


def test_signed_loss_run_keeps_class_knockout(monkeypatch):
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["loss_run_present"] = True
    signals["signals"]["loss_run_needs_review"] = False
    signals["signals"]["loss_run_review_detail"] = ""
    _, decision = _route_case(monkeypatch, "SUB-9100", signals=signals)
    assert decision["next_step"] == "DECLINE_UNINSURABLE_CLASS"
    assert decision["checks"][-1]["probe_id"] == "P00_PROHIBITED_CLASS_CODE"


def test_large_loss_invoice_routes_before_class_knockout(monkeypatch):
    monkeypatch.setenv("PACK_ROOT", str(UW))
    pack = load_pack(UW)
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["large_loss_present"] = True
    signals["signals"]["large_loss_needs_review"] = True
    signals["signals"]["large_loss_review_detail"] = "invoice lines do not match the invoice total"
    graph = build_case_graph(
        "SUB-9100",
        pack=pack,
        spine=_payload("get_submission_spine", "SUB-9100"),
        signals=signals,
    )
    assert "invoice total" in graph["large_loss_review_detail"]
    decision = route_claim(graph, "SUB-9100")
    assert decision["next_step"] == "RESOLVE_DOCUMENT_EXCEPTIONS"
    assert decision["exceptions"][0]["next_step"] == "RESOLVE_LARGE_LOSS_NARRATIVE"
    assert "invoice total" in decision["exceptions"][0]["fields"]["large_loss_review_detail"]
    assert decision["disposition"]["next_step"] == "DECLINE_UNINSURABLE_CLASS"


def test_oakridge_large_loss_keeps_class_knockout(monkeypatch):
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["large_loss_present"] = True
    signals["signals"]["large_loss_needs_review"] = False
    signals["signals"]["large_loss_review_detail"] = ""
    _, decision = _route_case(monkeypatch, "SUB-9100", signals=signals)
    assert decision["next_step"] == "DECLINE_UNINSURABLE_CLASS"
    assert decision["checks"][-1]["probe_id"] == "P00_PROHIBITED_CLASS_CODE"


def test_tenant_roster_mismatch_routes_before_class_knockout(monkeypatch):
    monkeypatch.setenv("PACK_ROOT", str(UW))
    pack = load_pack(UW)
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["tenant_roster_present"] = True
    signals["signals"]["tenant_roster_needs_review"] = True
    signals["signals"]["tenant_roster_review_detail"] = "roster does not match the rental value rent roll"
    graph = build_case_graph(
        "SUB-9100",
        pack=pack,
        spine=_payload("get_submission_spine", "SUB-9100"),
        signals=signals,
    )
    assert "rent roll" in graph["tenant_roster_review_detail"]
    decision = route_claim(graph, "SUB-9100")
    assert decision["next_step"] == "RESOLVE_DOCUMENT_EXCEPTIONS"
    assert decision["exceptions"][0]["next_step"] == "RESOLVE_TENANT_ROSTER"
    assert "rent roll" in decision["exceptions"][0]["fields"]["tenant_roster_review_detail"]
    assert decision["disposition"]["next_step"] == "DECLINE_UNINSURABLE_CLASS"


def test_ocr_and_loss_run_exceptions_are_both_returned(monkeypatch):
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["ocr_document_present"] = True
    signals["signals"]["min_ocr_confidence"] = 0.658
    signals["signals"]["low_ocr_spans"] = "page 0 Rostova 0.658"
    signals["signals"]["loss_run_present"] = True
    signals["signals"]["loss_run_needs_review"] = True
    signals["signals"]["loss_run_review_detail"] = "loss run has no authorized signature"
    _, decision = _route_case(monkeypatch, "SUB-9100", signals=signals)
    steps = [item["next_step"] for item in decision["exceptions"]]
    assert steps == ["RESOLVE_LOW_CONFIDENCE_OCR", "RESOLVE_LOSS_RUN"]
    assert decision["next_step"] == "RESOLVE_DOCUMENT_EXCEPTIONS"
    assert decision["coworker"] == "Underwriting Review Agent"
    assert decision["disposition"]["next_step"] == "DECLINE_UNINSURABLE_CLASS"
    assert decision["disposition"]["write"] == "write_submission_decline"


def test_oakridge_tenant_roster_keeps_class_knockout(monkeypatch):
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["tenant_roster_present"] = True
    signals["signals"]["tenant_roster_needs_review"] = False
    signals["signals"]["tenant_roster_review_detail"] = ""
    _, decision = _route_case(monkeypatch, "SUB-9100", signals=signals)
    assert decision["next_step"] == "DECLINE_UNINSURABLE_CLASS"
    assert decision["checks"][-1]["probe_id"] == "P00_PROHIBITED_CLASS_CODE"


def test_oakridge_sov_keeps_class_knockout(monkeypatch):
    signals = _payload("get_submission_routing_signals", "SUB-9100")
    signals["signals"]["sov_present"] = True
    signals["signals"]["sov_schedule_incomplete"] = False
    signals["signals"]["sov_min_coinsurance_pct"] = 80
    signals["signals"]["total_insured_value"] = 4765000
    signals["signals"]["construction_type"] = "MASONRY"
    signals["signals"]["year_built"] = 2004
    signals["signals"]["square_footage"] = 18500
    signals["signals"]["protection_class"] = "2"
    signals["signals"]["has_sprinklers"] = True
    _, decision = _route_case(monkeypatch, "SUB-9100", signals=signals)
    assert decision["next_step"] == "DECLINE_UNINSURABLE_CLASS"
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


def test_manual_triage_names_the_straight_through_gap(monkeypatch):
    signals = _payload("get_submission_routing_signals", "SUB-9107")
    signals["signals"]["has_underwriter"] = True
    signals["signals"]["claims_count_36m"] = 1
    signals["signals"]["financial_score"] = None
    signals["signals"]["ocr_document_present"] = True
    signals["signals"]["min_ocr_confidence"] = 0.658
    signals["signals"]["low_ocr_spans"] = "page 0 Rostova 0.658"
    _, decision = _route_case(monkeypatch, "SUB-9107", signals=signals)
    assert decision["next_step"] == "RESOLVE_DOCUMENT_EXCEPTIONS"
    assert decision["disposition"]["next_step"] == "HOLD_FOR_MANUAL_TRIAGE"
    note = decision["disposition_note"]
    assert "HOLD_FOR_MANUAL_TRIAGE" in note
    assert "1 claim in 36 months" in note
    assert "no financial score" in note


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
