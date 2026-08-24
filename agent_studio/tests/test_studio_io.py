"""Payload normalize + session paths."""

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


def test_normalize_spine_lowercases_keys():
    raw = {
        "Spine": {
            "Claim_Number": "CLM-402",
            "POLICY_ID": 1001,
            "INSURABLE_OBJECT_ID": 201,
        },
        "Roles": [],
    }
    spine = normalize_spine_payload(raw)
    assert spine["policy_id"] == 1001
    assert spine["insurable_object_id"] == 201


def test_assert_spine_triangle_fields():
    from ins_claims_agent.studio_io import assert_spine_has_triangle_fields

    assert_spine_has_triangle_fields({"policy_id": 1, "insurable_object_id": 2})
    try:
        assert_spine_has_triangle_fields({"policy_id": 1})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "insurable_object_id" in str(exc)


def test_assert_signals_intake_fields_when_police_missing():
    from ins_claims_agent.studio_io import assert_signals_has_intake_fields

    assert_signals_has_intake_fields(
        {"has_police_report": False, "has_incident_report_number": True}
    )
    assert_signals_has_intake_fields({"has_police_report": True})
    try:
        assert_signals_has_intake_fields({"has_police_report": False})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "has_incident_report_number" in str(exc)


def test_assert_signals_json_requires_mcp_named_op():
    from ins_claims_agent.studio_io import (
        assert_signals_json_is_mcp_observation,
        normalize_signals_payload,
    )

    mcp = {
        "named_op": "get_claim_routing_signals",
        "named_op_kind": "read",
        "catalog_version": 1,
        "signals": {
            "has_police_report": False,
            "has_incident_report_number": True,
            "incident_report_number": "SPD-25-11887",
        },
        "injury_ids": [],
        "offers": [],
        "payment_ids": [],
        "recovery_ids": [],
    }
    observation = assert_signals_json_is_mcp_observation(mcp)
    signals = normalize_signals_payload(observation)
    assert signals["has_incident_report_number"] is True
    assert signals["incident_report_number"] == "SPD-25-11887"

    wrapped = assert_signals_json_is_mcp_observation({"tool_output": mcp})
    assert wrapped["named_op"] == "get_claim_routing_signals"

    case = {
        "has_incident_report_number": False,
        "incident_report_number": None,
        "spine": {"claim_id": 401},
        "signals": {
            "has_incident_report_number": False,
            "incident_report_number": None,
            "has_police_report": False,
        },
    }
    try:
        assert_signals_json_is_mcp_observation(case)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "case JSON" in str(exc)

    try:
        assert_signals_json_is_mcp_observation(
            {"has_police_report": False, "has_incident_report_number": False}
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "named_op" in str(exc)


def test_mcp_observation_intake_reaches_case_json():
    from ins_claims_agent.studio_io import (
        assert_signals_json_is_mcp_observation,
        normalize_signals_payload,
    )

    observation = assert_signals_json_is_mcp_observation(
        {
            "named_op": "get_claim_routing_signals",
            "signals": {
                "has_police_report": False,
                "has_incident_report_number": True,
                "incident_report_number": "SPD-25-11887",
            },
        }
    )
    case = build_claim_graph(
        401,
        spine={
            "claim_id": 401,
            "claim_status_code": "OPEN",
            "policy_id": 1001,
            "insurable_object_id": 201,
            "policy_covers_vehicle": True,
            "coverage_type_code": "COLLISION",
            "roles": [
                {"claim_party_role_id": 6002, "role_type_code": "ADJUSTER", "party_id": 4}
            ],
        },
        signals=normalize_signals_payload(observation),
    )
    assert case["has_incident_report_number"] is True
    assert case["incident_report_number"] == "SPD-25-11887"


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
    case = build_claim_graph(401, spine=spine, signals=signals)
    report = validate_claim_graph(case, 401)
    assert report["passed"] is True


def test_save_claim_letter_writes_txt(tmp_path, monkeypatch):
    from ins_claims_agent.studio_io import save_claim_letter

    monkeypatch.setenv("SESSION_DIRECTORY", str(tmp_path))
    body = "Subject: Claim 402 hold\n\nDiscovery is open; file is complete."
    saved = save_claim_letter("402", body, run_id="demo-402-letter")
    path = tmp_path / "claim_402_letter.txt"
    assert path.is_file()
    assert saved["letter_artifact"] == str(path.resolve())
    assert "Discovery is open" in path.read_text(encoding="utf-8")
    assert saved["bytes"] > 0


def test_save_claim_letter_sms_copy(tmp_path, monkeypatch):
    from ins_claims_agent.studio_io import save_claim_letter

    monkeypatch.setenv("SESSION_DIRECTORY", str(tmp_path))
    body = "Please open the claims app and enter the police incident report number."
    saved = save_claim_letter(
        "401",
        body,
        run_id="demo-401-pd",
        next_step="CollectIncidentReportNumber",
    )
    path = tmp_path / "claim_401_sms.txt"
    assert path.is_file()
    assert saved["sms_artifact"] == str(path.resolve())
    assert saved["letter_artifact"] == str(path.resolve())
    assert not (tmp_path / "claim_401_letter.txt").exists()
    assert "claims app" in path.read_text(encoding="utf-8")


def test_save_claim_letter_rejects_empty_body(tmp_path, monkeypatch):
    from ins_claims_agent.studio_io import save_claim_letter

    monkeypatch.setenv("SESSION_DIRECTORY", str(tmp_path))
    try:
        save_claim_letter("402", "   ")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "body" in str(exc)


def test_save_claim_letter_rejects_unsafe_claim_id(tmp_path, monkeypatch):
    from ins_claims_agent.studio_io import save_claim_letter

    monkeypatch.setenv("SESSION_DIRECTORY", str(tmp_path))
    try:
        save_claim_letter("../etc", "hello")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "safe" in str(exc)
