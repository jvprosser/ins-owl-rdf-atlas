"""Finserv packs: generic graph + playbook route. Claims 402 path stays default."""

from __future__ import annotations

import json
from pathlib import Path

from ins_claims_agent.graph.build_case_graph import build_case_graph
from ins_claims_agent.graph.route_claim import route_claim
from ins_claims_agent.graph.validate_graph import validate_claim_graph
from ins_claims_agent.pack import load_pack
from ins_claims_agent.pre_router.route_text import route_unstructured

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / "packs" / "retirement_distributions"
ROLL = REPO / "packs" / "retirement_rollovers"


def _payload(pack_root: Path, label: str, case_id: str) -> dict:
    path = pack_root / "fixtures" / label / f"{case_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _route_case(monkeypatch, pack_root: Path, case_id: str, spine_label: str, signals_label: str):
    monkeypatch.setenv("PACK_ROOT", str(pack_root))
    pack = load_pack(pack_root)
    graph = build_case_graph(
        case_id,
        pack=pack,
        spine=_payload(pack_root, spine_label, case_id),
        signals=_payload(pack_root, signals_label, case_id),
    )
    report = validate_claim_graph(graph, case_id)
    decision = route_claim(graph, case_id)
    return report, decision


def test_distribution_7001_ops(monkeypatch):
    report, decision = _route_case(
        monkeypatch, DIST, "7001", "get_distribution_spine", "get_distribution_routing_signals"
    )
    assert report["passed"] is True
    assert decision["next_step"] == "ProcessDistribution"
    assert decision["agent_role"] == "DistributionOpsAgent"
    assert decision["lane"] == "DISTRIBUTION"


def test_distribution_7002_exception(monkeypatch):
    report, decision = _route_case(
        monkeypatch, DIST, "7002", "get_distribution_spine", "get_distribution_routing_signals"
    )
    assert report["passed"] is True
    assert decision["next_step"] == "RequestSubstantiation"
    assert decision["agent_role"] == "ExceptionQueueAgent"
    assert "R2.2" in decision["reason_probe_ids"]


def test_distribution_7003_rmd(monkeypatch):
    _, decision = _route_case(
        monkeypatch, DIST, "7003", "get_distribution_spine", "get_distribution_routing_signals"
    )
    assert decision["next_step"] == "RmdReview"
    assert decision["agent_role"] == "RmdOpsAgent"


def test_rollover_8001_erisa(monkeypatch):
    report, decision = _route_case(
        monkeypatch, ROLL, "8001", "get_rollover_spine", "get_rollover_routing_signals"
    )
    assert report["passed"] is True
    assert decision["next_step"] == "ErisaReview"
    assert decision["agent_role"] == "ErisaReviewAgent"
    assert "R2.1" in decision["reason_probe_ids"]


def test_rollover_8002_ops(monkeypatch):
    _, decision = _route_case(
        monkeypatch, ROLL, "8002", "get_rollover_spine", "get_rollover_routing_signals"
    )
    assert decision["next_step"] == "ProcessRollover"
    assert decision["agent_role"] == "RolloverOpsAgent"


def test_distribution_cosine_exception():
    result = route_unstructured(
        "Hardship withdrawal is missing medical bills and the hardship attestation.",
        exemplars_path=DIST / "exemplars.yaml",
    )
    assert result["needs_llm"] is False
    assert result["label"] == "EXCEPTION"
    assert result["coworker"] == "Exception Queue Agent"


def test_legacy_claims_root_without_pack_env(monkeypatch):
    monkeypatch.delenv("PACK_ROOT", raising=False)
    monkeypatch.delenv("INS_CLAIMS_REPO_ROOT", raising=False)
    monkeypatch.delenv("WORKFLOW_DATA_DIRECTORY", raising=False)
    from ins_claims_agent.paths import current_pack, default_ontology_path

    assert current_pack() is None
    assert default_ontology_path().name == "claims_mvt.ttl"
