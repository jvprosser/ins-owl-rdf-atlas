"""First-match YAML probes + playbook actions on a case JSON document."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ins_claims_agent.graph.yaml_rules import eval_match, get_path
from ins_claims_agent.paths import default_playbook_path

_LATER_NOTE = "Later playbook checks were not run."
_DEFAULT_TITLE = "No earlier check assigned work"


def route_claim(
    case: dict[str, Any],
    claim_id: int | str,
    *,
    playbook_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run YAML probes in priority order; return next step / agent / tools."""
    if not isinstance(case, dict):
        raise TypeError("route_claim expects a case JSON dict")
    playbook = _load_playbook(playbook_path)
    priorities = list(playbook.get("priorities") or [])
    probes = playbook.get("probes") or {}
    matched: list[dict[str, Any]] = []
    for idx, probe_id in enumerate(priorities):
        probe_cfg = probes[probe_id]
        form = str(probe_cfg.get("form") or "ASK").upper()
        result = _exec_probe(case, probe_cfg, form)
        action = _match_action(playbook, probe_id, form, result)
        assigned = action is not None
        matched.append(_trace_entry(probe_id, probe_cfg, form, result, assigned))
        if action is not None:
            return _decision(
                claim_id,
                action,
                matched,
                remaining=priorities[idx + 1 :],
                terminal=bool(action.get("terminal")),
            )

    default = playbook.get("default_action", {})
    return _decision(
        claim_id,
        default,
        matched,
        remaining=[],
        terminal=bool(default.get("terminal", True)),
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


def _select_value(result: Any) -> str:
    if isinstance(result, list) and result and isinstance(result[0], dict):
        value = result[0].get("value")
        if value is not None:
            return str(value)
    return ""


def _detail(
    probe_id: str,
    probe_cfg: dict[str, Any],
    form: str,
    result: Any,
    *,
    assigned: bool,
) -> str:
    title = str(probe_cfg.get("title") or probe_id)
    if form == "ASK":
        key = "when_true" if result is True else "when_false"
        return str(probe_cfg.get(key) or title)
    if form == "SELECT":
        value = _select_value(result)
        key = "when_equals" if assigned else "otherwise"
        text = str(probe_cfg.get(key) or title)
        return text.replace("{value}", value)
    return title


def _trace_entry(
    probe_id: str,
    probe_cfg: dict[str, Any],
    form: str,
    result: Any,
    assigned: bool,
) -> dict[str, Any]:
    title = str(probe_cfg.get("title") or probe_id)
    return {
        "probe_id": probe_id,
        "form": form,
        "result": result,
        "title": title,
        "status": "assigned" if assigned else "did_not_apply",
        "detail": _detail(probe_id, probe_cfg, form, result, assigned=assigned),
    }


def _optional_str(action: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = action.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _decision(
    claim_id: int | str,
    action: dict[str, Any],
    probe_trace: list[dict[str, Any]],
    *,
    remaining: list[str],
    terminal: bool,
) -> dict[str, Any]:
    step = action.get("step")
    assigned = next((p for p in probe_trace if p.get("status") == "assigned"), None)
    if assigned:
        reason = f"{assigned['detail']} → {step}."
    else:
        fallback = str(action.get("title") or _DEFAULT_TITLE)
        reason = f"{fallback} → {step}."
    later = bool(remaining)
    letter_on_request = bool(action.get("letter_on_request", False))
    letter_note = str(action.get("letter_note") or "").strip() or None
    if letter_on_request and not letter_note:
        letter_note = (
            "A letter is recommended as the next step. "
            "It will not be drafted unless you ask."
        )
    checks = [
        {
            "probe_id": p["probe_id"],
            "title": p["title"],
            "status": p["status"],
            "detail": p["detail"],
        }
        for p in probe_trace
    ]
    decision = {
        "claim_id": str(claim_id),
        "lane": action.get("lane"),
        "next_step": step,
        "agent_role": action.get("agent"),
        "coworker": _optional_str(action, "coworker", "coworker_role"),
        "write": _optional_str(action, "write", "write_label"),
        "task_type_code": _optional_str(action, "task_type_code"),
        "allowed_tools": list(action.get("tools") or []),
        "letter_on_request": letter_on_request,
        "letter_note": letter_note,
        "terminal": terminal,
        "reason_probe_ids": [p["probe_id"] for p in probe_trace],
        "probe_trace": probe_trace,
        "routing_reason": reason,
        "checks": checks,
        "later_checks_not_run": later,
        "later_checks_note": _LATER_NOTE if later else None,
    }
    decision["routing_summary"] = format_routing_summary(decision)
    return decision


def format_routing_summary(decision: dict[str, Any]) -> str:
    """Plain-language block for Studio Observation / Final Answer (no probe ids)."""
    lines = [
        f"Next step: {decision.get('next_step')}",
        f"Lane: {decision.get('lane')}",
        f"Assigned agent: {decision.get('agent_role')}",
        "",
        f"Why this routing: {decision.get('routing_reason')}",
    ]
    if decision.get("letter_note"):
        lines.extend(["", str(decision["letter_note"])])
    lines.extend(
        [
            "",
            "Checks on this snapshot:",
        ]
    )
    for check in decision.get("checks") or []:
        tag = (
            "assigned this work"
            if check.get("status") == "assigned"
            else "did not apply"
        )
        lines.append(f"- {check.get('title')}: {check.get('detail')} ({tag})")
    if decision.get("later_checks_not_run"):
        lines.append("")
        lines.append(str(decision.get("later_checks_note") or _LATER_NOTE))
    return "\n".join(lines)
