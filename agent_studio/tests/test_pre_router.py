"""Unstructured pre-router: cosine vs LLM-fallback flag."""

from __future__ import annotations

from ins_claims_agent.pre_router.route_text import (
    DEFAULT_THRESHOLD,
    route_unstructured,
)


def test_litigation_phrase_matches_without_llm():
    result = route_unstructured(
        "We were served a civil complaint; the lawsuit is in discovery."
    )
    assert result["needs_llm"] is False
    assert result["method"] == "cosine"
    assert result["label"] == "LITIGATION"
    assert result["coworker"] == "Litigation Agent"
    assert result["score"] >= DEFAULT_THRESHOLD
    assert result["structured_intake_supersedes"] is False


def test_general_claims_phrase_matches_without_llm():
    result = route_unstructured(
        "FNOL collision; insured needs a body shop repair estimate."
    )
    assert result["needs_llm"] is False
    assert result["label"] == "GENERAL_CLAIMS"
    assert result["coworker"] == "Manager agent"
    assert result["next_step"] == "StructuredIntake"


def test_unrelated_text_requests_llm():
    result = route_unstructured("what time is lunch in the cafeteria")
    assert result["needs_llm"] is True
    assert result["method"] == "below_threshold"
    assert result["label"] is None
    assert result["coworker"] is None


def test_empty_text_requests_llm():
    result = route_unstructured("   ")
    assert result["needs_llm"] is True
    assert result["score"] == 0.0


def test_claim_id_is_advisory_only():
    result = route_unstructured(
        "Plaintiff filed suit; docket assigned in circuit court.",
        claim_id="402",
    )
    assert result["claim_id"] == "402"
    assert result["structured_intake_supersedes"] is True
    assert result["authority"] == "advisory"
    assert result["label"] == "LITIGATION"
    assert "structured claim intake" in result["notes"]


def test_self_exemplar_roundtrip_litigation():
    result = route_unstructured(
        "Complaint filed in circuit court; summons served; docket number assigned to the lawsuit."
    )
    assert result["label"] == "LITIGATION"
    assert result["matched_exemplar_id"] == "L01"
    assert result["score"] > 0.9
