"""Compile every playbook CEL probe; YAML match remains a fallback only."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from ins_claims_agent.graph.cel_rules import compile_cel, eval_cel, flatten_case

REPO = Path(__file__).resolve().parents[2]
PLAYBOOKS = [
    REPO / "playbook" / "playbook.yaml",
    REPO / "packs" / "retirement_distributions" / "playbook" / "playbook.yaml",
    REPO / "packs" / "retirement_rollovers" / "playbook" / "playbook.yaml",
]


_R24 = (
    'distribution_type_code == "HARDSHIP" && size(hardship_category) > 0 && '
    '!(["MEDICAL","PRINCIPAL_RESIDENCE","TUITION","EVICTION_FORECLOSURE",'
    '"FUNERAL","CASUALTY_REPAIR","FED_DISASTER"].exists(cat, cat == hardship_category))'
)


def test_hardship_category_cel():
    assert eval_cel(_R24, {"distribution_type_code": "HARDSHIP", "hardship_category": "VACATION"})
    assert eval_cel(_R24, {"distribution_type_code": "HARDSHIP", "hardship_category": "MEDICAL"}) is False
    assert eval_cel(_R24, {"distribution_type_code": "TERMINATION", "hardship_category": "VACATION"}) is False


def test_flatten_defaults_pending_court_orders():
    flat = flatten_case({"case_exists": True})
    assert flat["pending_court_orders"] == []
    assert flat["hardship_category"] == ""
    assert flat["requested_amount"] == 0
    assert flat["has_participant_self_certified"] is False


def test_exists_on_missing_coverage_list_is_false():
    assert eval_cel(
        'coverage_type_codes.exists(c, c == "COLLISION")',
        {"claim_exists": True},
    ) is False


def test_flatten_lifts_nested_signals():
    case = {
        "has_police_report": False,
        "signals": {"has_incident_report_number": True, "incident_report_number": "SPD-1"},
    }
    flat = flatten_case(case)
    assert flat["has_incident_report_number"] is True
    assert eval_cel(
        "has_police_report == false && has_incident_report_number == true", case
    )


def test_discovery_aging_cel_uses_eval_date():
    expr = (
        '(litigation_indicator == true || has_litigation_case == true) && '
        'litigation_status_code == "IN_DISCOVERY" && size(closed_date) == 0 && '
        'size(filed_date) > 0 && timestamp(filed_date + "T00:00:00Z") + '
        'duration("2160h") < timestamp(eval_date + "T00:00:00Z")'
    )
    assert eval_cel(
        expr,
        {
            "has_litigation_case": True,
            "litigation_status_code": "IN_DISCOVERY",
            "filed_date": "2025-08-01",
            "closed_date": "",
        },
    ) is True
    assert eval_cel(
        expr,
        {
            "has_litigation_case": True,
            "litigation_status_code": "IN_DISCOVERY",
            "filed_date": date.today().isoformat(),
            "closed_date": "",
        },
    ) is False


def test_operator_exists_cel():
    ops = [
        {
            "was_cited_indicator": False,
            "impairment_suspected_indicator": True,
            "license_status_code": "VALID",
            "on_policy": True,
            "is_excluded_driver": False,
        }
    ]
    assert eval_cel(
        "insured_operators.exists(d, d.impairment_suspected_indicator == true)",
        {"insured_operators": ops},
    )
    assert eval_cel(
        "insured_operators.exists(d, d.was_cited_indicator == true)",
        {"insured_operators": ops},
    ) is False
    for path in PLAYBOOKS:
        playbook = yaml.safe_load(path.read_text(encoding="utf-8"))
        probes = playbook.get("probes") or {}
        missing = [pid for pid, cfg in probes.items() if not str(cfg.get("cel") or "").strip()]
        assert missing == [], f"{path} probes missing cel: {missing}"
        for pid, cfg in probes.items():
            compile_cel(str(cfg["cel"]))
            assert str(cfg.get("form") or "ASK").upper() == "ASK", pid
