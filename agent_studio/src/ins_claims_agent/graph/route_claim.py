"""First-match YAML probes + playbook actions on a case JSON document."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ins_claims_agent.graph.yaml_rules import eval_match, get_path
from ins_claims_agent.paths import default_playbook_path


def route_claim(
    case: dict[str, Any],
    claim_id: int | str,
    *,
    playbook_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run YAML probes in priority order; return next step / agent / tools."""
    if not isinstance(case, dict):
        raise TypeError("route_claim expects a case JSON dict, not an RDF graph")
    playbook = _load_playbook(playbook_path)
    matched: list[dict[str, Any]] = []
    for probe_id in playbook.get("priorities", []):
        probe_cfg = playbook["probes"][probe_id]
        form = str(probe_cfg.get("form") or "ASK").upper()
        result = _exec_probe(case, probe_cfg, form)
        matched.append({"probe_id": probe_id, "form": form, "result": result})

        action = _match_action(playbook, probe_id, form, result)
        if action is not None:
            return _decision(
                claim_id, action, matched, terminal=bool(action.get("terminal"))
            )

    default = playbook.get("default_action", {})
    return _decision(
        claim_id, default, matched, terminal=bool(default.get("terminal", True))
    )


def _load_playbook(playbook_path: str | Path | None) -> dict[str, Any]:
    path = Path(playbook_path) if playbook_path else default_playbook_path()
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _exec_probe(case: dict[str, Any], probe_cfg: dict[str, Any], form: str) -> Any:
    if form == "ASK":
        return eval_match(probe_cfg.get("match") or {}, case)
    if form == "SELECT":
        path = probe_cfg.get("path") or "claim_status_code"
        value = get_path(case, str(path))
        return [] if value is None else [{"value": value}]
    raise ValueError(f"Unsupported probe form: {form}")


def _match_action(
    playbook: dict[str, Any], probe_id: str, form: str, result: Any
) -> dict[str, Any] | None:
    for action in playbook.get("actions", {}).get(probe_id, []):
        when = action.get("when") or action.get("on")
        if when == "ASK_TRUE" and form == "ASK" and result is True:
            return action
        if when == "ASK_FALSE" and form == "ASK" and result is False:
            return action
        if when == "SELECT_EQUALS" and form == "SELECT":
            expected = action.get("match_value")
            for row in result or []:
                if expected in row.values():
                    return action
        if when == "ALWAYS":
            return action
    return None


def _decision(
    claim_id: int | str,
    action: dict[str, Any],
    probe_trace: list[dict[str, Any]],
    *,
    terminal: bool,
) -> dict[str, Any]:
    return {
        "claim_id": str(claim_id),
        "lane": action.get("lane"),
        "next_step": action.get("step"),
        "agent_role": action.get("agent"),
        "allowed_tools": list(action.get("tools") or []),
        "needs_llm": bool(action.get("needs_llm", False)),
        "terminal": terminal,
        "reason_probe_ids": [p["probe_id"] for p in probe_trace],
        "probe_trace": probe_trace,
    }
