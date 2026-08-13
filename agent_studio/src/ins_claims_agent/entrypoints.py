"""Stable function names for Cloudera Agent Studio custom tool registration."""

from __future__ import annotations

from typing import Any

from rdflib import Graph

from ins_claims_agent.audit.write_audit import (
    abandon_audit_run,
    begin_audit_run,
    promote_audit_run,
    write_audit_event,
    write_audit_evidence,
)
from ins_claims_agent.graph.build_claim_graph import build_claim_graph
from ins_claims_agent.graph.route_claim import route_claim
from ins_claims_agent.graph.validate_graph import validate_claim_graph
from ins_claims_agent.mcp_facade import (
    AtlasFacade,
    IcebergFacade,
    RangerFacade,
    bind_facades,
    from_agent_studio_mcp,
)
from ins_claims_agent.specialists import get_bi_view, get_litigation_view, get_subrogation_view
from ins_claims_agent.pre_router.route_text import route_unstructured
from ins_claims_agent.workflow.style_b_loop import run_style_b_loop

# Module-level facades; Agent Studio should inject MCP callers at startup.
iceberg = IcebergFacade()
atlas = AtlasFacade()
ranger = RangerFacade()

# Optional in-memory graph cache for a single workflow run
_GRAPH_CACHE: dict[str, Graph] = {}


def tool_build_claim_graph(claim_id: str, database: str = "car_insurance_claims") -> dict[str, Any]:
    g = build_claim_graph(claim_id, iceberg=iceberg, database=database)
    _GRAPH_CACHE[str(claim_id)] = g
    return {
        "claim_id": str(claim_id),
        "triple_count": len(g),
        "cached": True,
    }


def tool_route_claim(claim_id: str) -> dict[str, Any]:
    g = _GRAPH_CACHE.get(str(claim_id))
    if g is None:
        raise KeyError(f"No cached graph for claim {claim_id}; call tool_build_claim_graph first")
    return route_claim(g, claim_id)


def tool_validate_claim_graph(claim_id: str) -> dict[str, Any]:
    g = _GRAPH_CACHE.get(str(claim_id))
    if g is None:
        raise KeyError(f"No cached graph for claim {claim_id}; call tool_build_claim_graph first")
    return validate_claim_graph(g, claim_id)


def tool_begin_audit_run(run_id: str, database: str = "car_insurance_claims") -> Any:
    return begin_audit_run(run_id, iceberg=iceberg, database=database)


def tool_write_audit_event(run_id: str, event: dict[str, Any]) -> Any:
    return write_audit_event(run_id, event, iceberg=iceberg)


def tool_write_audit_evidence(run_id: str, evidence: dict[str, Any]) -> Any:
    return write_audit_evidence(run_id, evidence, iceberg=iceberg)


def tool_promote_audit_run(run_id: str) -> Any:
    return promote_audit_run(run_id, iceberg=iceberg)


def tool_abandon_audit_run(run_id: str) -> Any:
    return abandon_audit_run(run_id, iceberg=iceberg)


def tool_get_subrogation_view(claim_id: str) -> dict[str, Any]:
    return get_subrogation_view(claim_id, iceberg=iceberg)


def tool_get_bi_view(claim_id: str) -> dict[str, Any]:
    return get_bi_view(claim_id, iceberg=iceberg)


def tool_get_litigation_view(claim_id: str) -> dict[str, Any]:
    return get_litigation_view(claim_id, iceberg=iceberg)


def tool_pre_route_text(
    text: str,
    claim_id: str | None = None,
    threshold: float | None = None,
    margin: float | None = None,
) -> dict[str, Any]:
    """NL triage only. Structured claim intake is authoritative when claim_id is set."""
    kwargs: dict[str, Any] = {}
    if threshold is not None:
        kwargs["threshold"] = threshold
    if margin is not None:
        kwargs["margin"] = margin
    return route_unstructured(text, claim_id=claim_id, **kwargs)


def tool_run_style_b_loop(
    claim_id: str,
    run_id: str,
    database: str = "car_insurance_claims",
    promote_on_success: bool = True,
) -> dict[str, Any]:
    """Run Route→Worker→refresh until terminal (worker must be wired by host).

    This entrypoint routes and audits only; Agent Studio should wrap it with a
    worker dispatcher, or call ``run_style_b_loop`` from workflow code with a
    ``worker`` callable.
    """
    result = run_style_b_loop(
        claim_id,
        run_id,
        iceberg=iceberg,
        worker=None,
        database=database,
        promote_on_success=promote_on_success,
    )
    return {
        "claim_id": result.claim_id,
        "run_id": result.run_id,
        "stop_reason": result.stop_reason,
        "promoted": result.promoted,
        "decisions": result.decisions,
        "validation": result.validation,
    }


def bind_mcp_caller(caller: Any) -> None:
    """Inject ``caller(server, tool_name, **kwargs)`` into all facades."""
    bind_facades(caller, iceberg, atlas, ranger)


def bind_agent_studio_mcp(call_tool: Any, *, arg_style: str = "kwargs") -> None:
    """Convenience: adapt Agent Studio's MCP bridge and bind facades."""
    bind_mcp_caller(from_agent_studio_mcp(call_tool, arg_style=arg_style))
