"""Execute Git-managed SPARQL probes + playbook actions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from rdflib import Graph

from ins_claims_agent.paths import default_playbook_path, default_probes_dir, repo_path


def route_claim(
    graph: Graph,
    claim_id: int | str,
    *,
    playbook_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run probes in priority order; return next step / agent / tools decision."""
    playbook = _load_playbook(playbook_path)
    probes_dir = repo_path(playbook.get("probes_relpath", "probes"))
    if not probes_dir.exists():
        probes_dir = default_probes_dir()

    iri_template = playbook.get("case_iri_template") or playbook.get(
        "claim_iri_template"
    )
    matched: list[dict[str, Any]] = []
    for probe_id in playbook.get("priorities", []):
        probe_cfg = playbook["probes"][probe_id]
        query = _load_probe_query(
            probes_dir / probe_cfg["file"],
            claim_id,
            iri_template=iri_template,
        )
        form = probe_cfg.get("form", "ASK").upper()
        result = _exec_probe(graph, query, form)
        matched.append({"probe_id": probe_id, "form": form, "result": result})

        action = _match_action(playbook, probe_id, form, result)
        if action is not None:
            return _decision(claim_id, action, matched, terminal=bool(action.get("terminal")))

        if probe_cfg.get("stop_on_match") and _truthy_probe(form, result):
            # stop_on_match without action → continue unless configured otherwise
            pass

    default = playbook.get("default_action", {})
    return _decision(claim_id, default, matched, terminal=bool(default.get("terminal", True)))


def _load_playbook(playbook_path: str | Path | None) -> dict[str, Any]:
    path = Path(playbook_path) if playbook_path else default_playbook_path()
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_probe_query(
    path: Path,
    claim_id: int | str,
    *,
    iri_template: str | None = None,
) -> str:
    text = path.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("#")]
    query = "\n".join(lines)
    template = iri_template or "https://example.org/ins/id/Claim/{case_id}"
    iri = template.format(case_id=claim_id, claim_id=claim_id)
    return (
        query.replace("{{claim_id}}", str(claim_id))
        .replace("{{case_id}}", str(claim_id))
        .replace("{{claim_iri}}", iri)
        .replace("{{case_iri}}", iri)
    )


def _exec_probe(graph: Graph, query: str, form: str) -> Any:
    qres = graph.query(query)
    if form == "ASK":
        return bool(qres)
    if form == "SELECT":
        rows = []
        for row in qres:
            rows.append({str(k): (v.toPython() if hasattr(v, "toPython") else str(v)) for k, v in row.asdict().items()})
        return rows
    if form == "CONSTRUCT":
        return qres.serialize(format="turtle")
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


def _truthy_probe(form: str, result: Any) -> bool:
    if form == "ASK":
        return bool(result)
    if form == "SELECT":
        return bool(result)
    return result is not None


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
