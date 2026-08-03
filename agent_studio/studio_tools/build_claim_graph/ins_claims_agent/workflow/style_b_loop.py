"""Style B controller: Route → Worker → refresh → Route until stop."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
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
from ins_claims_agent.mcp_facade import IcebergFacade
from ins_claims_agent.paths import default_playbook_path


WorkerFn = Callable[[Dict[str, Any], Graph], Optional[Dict[str, Any]]]


@dataclass
class LoopResult:
    claim_id: str
    run_id: str
    decisions: list[dict[str, Any]] = field(default_factory=list)
    worker_outputs: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str = ""
    promoted: bool = False
    validation: dict[str, Any] | None = None


def load_loop_config(playbook_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(playbook_path) if playbook_path else default_playbook_path()
    with path.open(encoding="utf-8") as f:
        playbook = yaml.safe_load(f) or {}
    loop = playbook.get("loop") or {}
    return {
        "max_route_passes": int(loop.get("max_route_passes", 8)),
        "no_progress_limit": int(loop.get("no_progress_limit", 2)),
    }


def run_style_b_loop(
    claim_id: int | str,
    run_id: str,
    *,
    iceberg: IcebergFacade,
    worker: WorkerFn | None = None,
    database: str = "car_insurance_claims",
    playbook_path: str | Path | None = None,
    promote_on_success: bool = True,
    validate: bool = True,
    spine: dict[str, Any] | None = None,
    signals: dict[str, Any] | None = None,
) -> LoopResult:
    """Execute the Style B route loop for one claim.

    ``worker(decision, graph)`` performs the routed step. Optional return:
    ``{\"applied_signals\": {...}, \"applied_spine\": {...}}`` merges into the
    next offline graph rebuild (when ``spine`` was provided).
    """
    cfg = load_loop_config(playbook_path)
    result = LoopResult(claim_id=str(claim_id), run_id=run_id)

    begin_audit_run(run_id, iceberg=iceberg, database=database)

    local_spine = dict(spine) if spine is not None else None
    local_signals = dict(signals or {}) if signals is not None or spine is not None else None

    graph = _build(
        claim_id,
        iceberg=iceberg,
        database=database,
        spine=local_spine,
        signals=local_signals,
    )

    if validate:
        result.validation = validate_claim_graph(graph, claim_id)
        write_audit_evidence(
            run_id,
            {
                "claim_id": str(claim_id),
                "evidence_type": "VALIDATION",
                "content_format": "json",
                "content_text": str(result.validation),
            },
            iceberg=iceberg,
        )

    recent_steps: list[str] = []
    stop_reason = "max_route_passes"

    try:
        for _pass in range(cfg["max_route_passes"]):
            decision = route_claim(graph, claim_id, playbook_path=playbook_path)
            result.decisions.append(decision)
            write_audit_event(
                run_id,
                {
                    "claim_id": str(claim_id),
                    "event_type": "ROUTE_DECISION",
                    "next_step": decision.get("next_step"),
                    "agent_role": decision.get("agent_role"),
                    "lane": decision.get("lane"),
                    "needs_llm": decision.get("needs_llm"),
                    "terminal": decision.get("terminal"),
                    "reason_probe_ids": decision.get("reason_probe_ids"),
                    "payload_json": decision,
                },
                iceberg=iceberg,
            )

            step = str(decision.get("next_step") or "")
            recent_steps.append(step)
            if _no_progress(recent_steps, cfg["no_progress_limit"]):
                stop_reason = "no_progress"
                break

            if decision.get("terminal"):
                stop_reason = "terminal"
                break

            if worker is None:
                stop_reason = "no_worker"
                break

            write_audit_event(
                run_id,
                {
                    "claim_id": str(claim_id),
                    "event_type": "WORKER_START",
                    "next_step": step,
                    "agent_role": decision.get("agent_role"),
                    "lane": decision.get("lane"),
                },
                iceberg=iceberg,
            )
            worker_out = worker(decision, graph) or {}
            result.worker_outputs.append(worker_out)
            write_audit_evidence(
                run_id,
                {
                    "claim_id": str(claim_id),
                    "evidence_type": "WORKER_OUTPUT",
                    "content_format": "json",
                    "content_text": str(worker_out),
                },
                iceberg=iceberg,
            )
            write_audit_event(
                run_id,
                {
                    "claim_id": str(claim_id),
                    "event_type": "WORKER_END",
                    "next_step": step,
                    "agent_role": decision.get("agent_role"),
                    "lane": decision.get("lane"),
                },
                iceberg=iceberg,
            )

            if local_signals is not None and isinstance(worker_out.get("applied_signals"), dict):
                local_signals.update(worker_out["applied_signals"])
            if local_spine is not None and isinstance(worker_out.get("applied_spine"), dict):
                local_spine.update(worker_out["applied_spine"])

            graph = _build(
                claim_id,
                iceberg=iceberg,
                database=database,
                spine=local_spine,
                signals=local_signals,
            )

        result.stop_reason = stop_reason
        if promote_on_success and stop_reason == "terminal":
            promote_audit_run(run_id, iceberg=iceberg)
            result.promoted = True
        else:
            abandon_audit_run(run_id, iceberg=iceberg)
            result.promoted = False
    except Exception:
        abandon_audit_run(run_id, iceberg=iceberg)
        raise

    return result


def _build(
    claim_id: int | str,
    *,
    iceberg: IcebergFacade,
    database: str,
    spine: dict[str, Any] | None,
    signals: dict[str, Any] | None,
) -> Graph:
    if spine is not None:
        return build_claim_graph(claim_id, spine=spine, signals=signals or {})
    return build_claim_graph(claim_id, iceberg=iceberg, database=database)


def _no_progress(recent_steps: list[str], limit: int) -> bool:
    if limit <= 0 or len(recent_steps) < limit:
        return False
    tail = recent_steps[-limit:]
    return len(set(tail)) == 1 and bool(tail[0])
