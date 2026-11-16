"""First-match playbook probes (CEL, with YAML match/SELECT fallback) + actions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ins_claims_agent.graph.cel_rules import eval_cel
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
    """Run playbook probes in priority order; return next step / agent / tools."""
    if not isinstance(case, dict):
        raise TypeError("route_claim expects a case JSON dict")
    playbook = _load_playbook(playbook_path)
    if playbook.get("exception_probes"):
        return _route_with_exceptions(case, claim_id, playbook)
    priorities = list(playbook.get("priorities") or [])
    probes = playbook.get("probes") or {}
    matched: list[dict[str, Any]] = []
    for idx, probe_id in enumerate(priorities):
        probe_cfg = probes[probe_id]
        form = str(probe_cfg.get("form") or "ASK").upper()
        if str(probe_cfg.get("cel") or "").strip():
            form = "ASK"
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
                playbook_version=_playbook_version(playbook),
            )

    default = playbook.get("default_action", {})
    return _decision(
        claim_id,
        default,
        matched,
        remaining=[],
        terminal=bool(default.get("terminal", True)),
        playbook_version=_playbook_version(playbook),
        reason_text=_default_disposition_reason(case),
    )


def _route_with_exceptions(
    case: dict[str, Any],
    claim_id: int | str,
    playbook: dict[str, Any],
) -> dict[str, Any]:
    """Score every exception probe, then first-match the disposition."""
    priorities = list(playbook.get("priorities") or [])
    probes = playbook.get("probes") or {}
    exception_ids = set(playbook.get("exception_probes") or [])
    trace: list[dict[str, Any]] = []
    found: list[dict[str, Any]] = []
    version = _playbook_version(playbook)

    for idx, probe_id in enumerate(priorities):
        probe_cfg = probes[probe_id]
        form = str(probe_cfg.get("form") or "ASK").upper()
        if str(probe_cfg.get("cel") or "").strip():
            form = "ASK"
        result = _exec_probe(case, probe_cfg, form)
        action = _match_action(playbook, probe_id, form, result)
        entry = _trace_entry(probe_id, probe_cfg, form, result, action is not None)
        trace.append(entry)
        if probe_id in exception_ids:
            if action is not None:
                found.append(_exception_item(case, probe_id, probe_cfg, action, entry))
            continue
        if action is None:
            continue
        if found:
            return _exception_decision(
                claim_id,
                playbook,
                trace,
                found,
                action,
                remaining=priorities[idx + 1 :],
                playbook_version=version,
            )
        return _decision(
            claim_id,
            action,
            trace,
            remaining=priorities[idx + 1 :],
            terminal=bool(action.get("terminal")),
            playbook_version=version,
        )

    default = playbook.get("default_action", {})
    if found:
        return _exception_decision(
            claim_id,
            playbook,
            trace,
            found,
            default,
            remaining=[],
            playbook_version=version,
            case=case,
        )
    return _decision(
        claim_id,
        default,
        trace,
        remaining=[],
        terminal=bool(default.get("terminal", True)),
        playbook_version=version,
        reason_text=_default_disposition_reason(case),
    )


def _exception_item(
    case: dict[str, Any],
    probe_id: str,
    probe_cfg: dict[str, Any],
    action: dict[str, Any],
    entry: dict[str, Any],
) -> dict[str, Any]:
    item = {
        "probe_id": probe_id,
        "next_step": action.get("step"),
        "detail": entry["detail"],
    }
    if entry.get("cel"):
        item["cel"] = entry["cel"]
    fields = {}
    for key in probe_cfg.get("detail_fields") or []:
        if key in case:
            fields[str(key)] = case[key]
    if fields:
        item["fields"] = fields
    return item


def _exception_decision(
    claim_id: int | str,
    playbook: dict[str, Any],
    probe_trace: list[dict[str, Any]],
    found: list[dict[str, Any]],
    disposition_action: dict[str, Any],
    *,
    remaining: list[str],
    playbook_version: str | None,
    case: dict[str, Any] | None = None,
) -> dict[str, Any]:
    review = playbook.get("exception_review") or {}
    decision = _decision(
        claim_id,
        review,
        probe_trace,
        remaining=remaining,
        terminal=bool(review.get("terminal", True)),
        playbook_version=playbook_version,
    )
    decision["exceptions"] = found
    disposition = {
        "next_step": disposition_action.get("step"),
        "agent_role": disposition_action.get("agent"),
        "coworker": _optional_str(disposition_action, "coworker", "coworker_role"),
        "lane": disposition_action.get("lane"),
        "write": _optional_str(disposition_action, "write", "write_label"),
    }
    reason_code = _optional_str(disposition_action, "reason_code")
    if reason_code:
        disposition["reason_code"] = reason_code
    decision["disposition"] = disposition
    decision.pop("reason_code", None)
    decision.pop("matched_cel", None)
    details = "; ".join(str(item["detail"]) for item in found)
    step = review.get("step")
    decision["routing_reason"] = f"{details} → {step}."
    note = f"Disposition if these exceptions are cleared: {disposition['next_step']}."
    default_step = (playbook.get("default_action") or {}).get("step")
    if case is not None and disposition["next_step"] == default_step:
        note = f"{note} {_default_disposition_reason(case)}"
    decision["disposition_note"] = note
    decision["routing_summary"] = format_routing_summary(decision)
    return decision


def _default_disposition_reason(case: dict[str, Any]) -> str:
    """Why straight-through bind missed, using the values on this case."""
    rule = (
        "Straight-through bind needs total insured value at or under 5000000, "
        "zero claims in 36 months, a financial score of at least 680, and a "
        "flood zone other than A or V."
    )
    gaps: list[str] = []
    tiv = _as_float(case.get("total_insured_value"))
    if tiv is not None and tiv > 5_000_000:
        gaps.append(f"total insured value {_num(tiv)}")
    claims = _as_float(case.get("claims_count_36m"))
    if claims is None:
        gaps.append("claims in 36 months missing")
    elif claims != 0:
        label = "claim" if claims == 1 else "claims"
        gaps.append(f"{_num(claims)} {label} in 36 months")
    score = case.get("financial_score")
    score_n = None if score in (None, "") else _as_float(score)
    if score_n is None:
        gaps.append("no financial score")
    elif score_n < 680:
        gaps.append(f"financial score {_num(score_n)}")
    zone = str(case.get("flood_zone") or "").strip()
    if zone in {"A", "V"}:
        gaps.append(f"flood zone {zone}")
    if not gaps:
        return "No decline, referral, or straight-through bind check matched."
    return f"{rule} This file has {'; '.join(gaps)}."


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _num(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return str(value)


def _playbook_version(playbook: dict[str, Any]) -> str | None:
    version = playbook.get("version")
    if version is None:
        return None
    text = str(version).strip()
    return text or None


def _load_playbook(playbook_path: str | Path | None) -> dict[str, Any]:
    path = Path(playbook_path) if playbook_path else default_playbook_path()
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _exec_probe(case: dict[str, Any], probe_cfg: dict[str, Any], form: str) -> Any:
    cel = probe_cfg.get("cel")
    if cel is not None and str(cel).strip():
        return eval_cel(str(cel), case)
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
    entry = {
        "probe_id": probe_id,
        "form": form,
        "result": result,
        "title": title,
        "status": "assigned" if assigned else "did_not_apply",
        "detail": _detail(probe_id, probe_cfg, form, result, assigned=assigned),
    }
    cel = str(probe_cfg.get("cel") or "").strip()
    if cel:
        entry["cel"] = cel
    return entry


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
    playbook_version: str | None = None,
    reason_text: str | None = None,
) -> dict[str, Any]:
    step = action.get("step")
    assigned = next((p for p in probe_trace if p.get("status") == "assigned"), None)
    if assigned:
        reason = f"{assigned['detail']} → {step}."
    elif reason_text:
        reason = f"{reason_text} → {step}."
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
    if playbook_version:
        decision["playbook_version"] = playbook_version
    reason_code = _optional_str(action, "reason_code")
    if reason_code:
        decision["reason_code"] = reason_code
    if assigned and assigned.get("cel"):
        decision["matched_cel"] = assigned["cel"]
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
    if decision.get("disposition_note"):
        lines.extend(["", str(decision["disposition_note"])])
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
