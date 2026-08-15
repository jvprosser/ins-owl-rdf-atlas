"""Lightweight graph validation (SPARQL ASK checks; OWL reasoner optional later)."""

from __future__ import annotations

from typing import Any

from rdflib import Graph

from ins_claims_agent.graph.iri import claim_iri
from ins_claims_agent.pack import Pack
from ins_claims_agent.paths import current_pack


def validate_claim_graph(graph: Graph, claim_id: int | str) -> dict[str, Any]:
    """Return a simple validation report for spine integrity."""
    pack = current_pack()
    if pack is not None and pack.graph.get("builder") == "generic":
        return _validate_generic_case(graph, claim_id, pack)

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


def _validate_generic_case(
    graph: Graph, case_id: int | str, pack: Pack
) -> dict[str, Any]:
    iri = pack.case_iri(case_id)
    case_class = str(pack.graph.get("case_class") or "Case")
    checks: list[dict[str, Any]] = []
    ok = bool(
        graph.query(f"ASK {{ <{iri}> a <https://example.org/ins/{case_class}> }}")
    )
    checks.append({"check": "case_exists", "passed": ok})
    return {"claim_id": str(case_id), "passed": ok, "checks": checks}
