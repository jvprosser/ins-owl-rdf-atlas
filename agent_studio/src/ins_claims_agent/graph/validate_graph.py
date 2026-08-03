"""Lightweight graph validation (SPARQL ASK checks; OWL reasoner optional later)."""

from __future__ import annotations

from typing import Any

from rdflib import Graph

from ins_claims_agent.graph.iri import claim_iri


def validate_claim_graph(graph: Graph, claim_id: int | str) -> dict[str, Any]:
    """Return a simple validation report for spine integrity."""
    claim = claim_iri(claim_id)
    checks: list[dict[str, Any]] = []

    def ask(name: str, query: str) -> None:
        ok = bool(graph.query(query))
        checks.append({"check": name, "passed": ok})

    ask(
        "claim_exists",
        f"ASK {{ <{claim}> a <https://example.org/ins/AutoClaim> }}",
    )
    ask(
        "has_policy",
        f"ASK {{ <{claim}> <https://example.org/ins/arisesFromPolicy> ?p }}",
    )
    ask(
        "has_vehicle",
        f"ASK {{ <{claim}> <https://example.org/ins/involvesVehicle> ?v }}",
    )
    ask(
        "triangle",
        f"""
        ASK {{
          <{claim}> <https://example.org/ins/arisesFromPolicy> ?p ;
                    <https://example.org/ins/involvesVehicle> ?v .
          ?p <https://example.org/ins/coversVehicle> ?v .
        }}
        """,
    )

    passed = all(c["passed"] for c in checks)
    return {"claim_id": str(claim_id), "passed": passed, "checks": checks}
