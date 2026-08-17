"""Case JSON validation (required fields; not SPARQL)."""

from __future__ import annotations

from typing import Any

from ins_claims_agent.paths import current_pack


def validate_claim_graph(case: dict[str, Any], claim_id: int | str) -> dict[str, Any]:
    """Return a simple validation report for spine integrity."""
    if not isinstance(case, dict):
        raise TypeError("validate_claim_graph expects a case JSON dict")
    pack = current_pack()
    if pack is not None and pack.graph.get("builder") == "generic":
        ok = bool(case.get("case_exists"))
        return {
            "claim_id": str(claim_id),
            "passed": ok,
            "checks": [{"check": "case_exists", "passed": ok}],
        }

    checks = [
        {"check": "claim_exists", "passed": bool(case.get("claim_exists"))},
        {"check": "has_policy", "passed": bool(case.get("has_policy"))},
        {"check": "has_vehicle", "passed": bool(case.get("has_vehicle"))},
        {"check": "triangle", "passed": bool(case.get("triangle"))},
    ]
    return {
        "claim_id": str(claim_id),
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
    }
