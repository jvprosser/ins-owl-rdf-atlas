"""Git-reviewed named query/write catalog (allow-listed labels, no free SQL)."""

from __future__ import annotations

import json
from typing import Any, Callable

from iceberg_mcp_server_claims.pack_fixtures import merge_pack_catalog
from iceberg_mcp_server_claims.tools import (
    audit_tools,
    claim_tools,
    impala_tools,
    litigation_tasks,
    pd_tasks,
    view_tools,
)

CATALOG_VERSION = 1

# Required / optional param names. Labels match existing MCP / playbook names.
READ_OPS: dict[str, dict[str, Any]] = {
    "get_claim_spine": {
        "required": ("claim_id",),
        "optional": ("database",),
        "summary": "Claim spine for graph build",
        "handler": lambda p: claim_tools.get_claim_spine(
            str(p["claim_id"]), p.get("database")
        ),
    },
    "get_claim_routing_signals": {
        "required": ("claim_id",),
        "optional": ("database",),
        "summary": "Routing/existence signals",
        "handler": lambda p: claim_tools.get_claim_routing_signals(
            str(p["claim_id"]), p.get("database")
        ),
    },
    "get_litigation_view": {
        "required": ("claim_id",),
        "optional": ("database",),
        "summary": "Litigation case business columns (no PK/FK)",
        "handler": lambda p: view_tools.get_litigation_view(
            str(p["claim_id"]), p.get("database")
        ),
    },
    "get_bi_view": {
        "required": ("claim_id",),
        "optional": ("database",),
        "summary": "Injury business columns (no PK/FK)",
        "handler": lambda p: view_tools.get_bi_view(
            str(p["claim_id"]), p.get("database")
        ),
    },
    "get_subrogation_view": {
        "required": ("claim_id",),
        "optional": ("database",),
        "summary": "Subrogation case business columns (no PK/FK)",
        "handler": lambda p: view_tools.get_subrogation_view(
            str(p["claim_id"]), p.get("database")
        ),
    },
    "get_pd_view": {
        "required": ("claim_id",),
        "optional": ("database",),
        "summary": "Police report and fault business columns (no PK/FK)",
        "handler": lambda p: view_tools.get_pd_view(
            str(p["claim_id"]), p.get("database")
        ),
    },
    "get_schema": {
        "required": (),
        "optional": ("database",),
        "summary": "List tables",
        "handler": lambda p: impala_tools.get_schema(p.get("database")),
    },
}

WRITE_OPS: dict[str, dict[str, Any]] = {
    "write_audit_event": {
        "required": ("run_id", "event_json"),
        "optional": ("database",),
        "summary": "Insert one audit event (playbook name)",
        "handler": lambda p: audit_tools.append_agent_audit_event(
            str(p["run_id"]),
            _as_json_string(p["event_json"]),
            p.get("database"),
        ),
    },
    "append_agent_audit_event": {
        "required": ("run_id", "event_json"),
        "optional": ("database",),
        "summary": "Insert one audit event",
        "handler": lambda p: audit_tools.append_agent_audit_event(
            str(p["run_id"]),
            _as_json_string(p["event_json"]),
            p.get("database"),
        ),
    },
    "append_agent_audit_evidence": {
        "required": ("run_id", "evidence_json"),
        "optional": ("database",),
        "summary": "Insert one audit evidence row",
        "handler": lambda p: audit_tools.append_agent_audit_evidence(
            str(p["run_id"]),
            _as_json_string(p["evidence_json"]),
            p.get("database"),
        ),
    },
    "begin_agent_audit_run": {
        "required": ("run_id",),
        "optional": ("database", "source_branch"),
        "summary": "Begin audit run (table-append mode)",
        "handler": lambda p: audit_tools.begin_agent_audit_run(
            str(p["run_id"]),
            p.get("database"),
            p.get("source_branch"),
        ),
    },
    "promote_audit_run": {
        "required": ("run_id",),
        "optional": ("database",),
        "summary": "Promote audit run (playbook name)",
        "handler": lambda p: audit_tools.promote_agent_audit_run(
            str(p["run_id"]), p.get("database")
        ),
    },
    "promote_agent_audit_run": {
        "required": ("run_id",),
        "optional": ("database",),
        "summary": "Promote audit run",
        "handler": lambda p: audit_tools.promote_agent_audit_run(
            str(p["run_id"]), p.get("database")
        ),
    },
    "abandon_agent_audit_run": {
        "required": ("run_id",),
        "optional": ("database",),
        "summary": "Delete audit rows for run_id",
        "handler": lambda p: audit_tools.abandon_agent_audit_run(
            str(p["run_id"]), p.get("database")
        ),
    },
    "create_litigation_task": {
        "required": ("run_id", "event_json"),
        "optional": ("database",),
        "summary": "Insert one litigation_task row (COMPLETE_FILE | ESCALATE_DISCOVERY | DRAFT_HOLD)",
        "handler": lambda p: litigation_tasks.create_litigation_task(
            str(p["run_id"]),
            _as_json_string(p["event_json"]),
            p.get("database"),
        ),
    },
    "create_pd_task": {
        "required": ("run_id", "event_json"),
        "optional": ("database",),
        "summary": "Insert one pd_task row and one agent_run_audit receipt",
        "handler": lambda p: pd_tasks.create_pd_task(
            str(p["run_id"]),
            _as_json_string(p["event_json"]),
            p.get("database"),
        ),
    },
}

# Env-gated: PACK_ROOT / pack.yaml + catalog_fixtures.json (demo packs).
PACK_ID = merge_pack_catalog(READ_OPS, WRITE_OPS)

_ALIAS_KEYS = frozenset({"case_id", "claim_id"})


def _as_json_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


def _parse_params(params_json: str | dict[str, Any] | None) -> dict[str, Any]:
    if params_json is None or params_json == "":
        return {}
    if isinstance(params_json, dict):
        return params_json
    try:
        payload = json.loads(params_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"params_json must be a JSON object: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("params_json must be a JSON object")
    return payload


def _error(**fields: Any) -> str:
    return json.dumps({"error": True, **fields})


def _annotate(raw: str, *, kind: str, label: str) -> str:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if not isinstance(payload, dict):
        return raw
    payload.setdefault("named_op", label)
    payload.setdefault("named_op_kind", kind)
    payload.setdefault("catalog_version", CATALOG_VERSION)
    return json.dumps(payload, default=str)


def list_catalog() -> dict[str, Any]:
    def _entries(ops: dict[str, dict[str, Any]], kind: str) -> list[dict[str, Any]]:
        rows = []
        for label, spec in ops.items():
            rows.append(
                {
                    "label": label,
                    "kind": kind,
                    "required": list(spec["required"]),
                    "optional": list(spec["optional"]),
                    "summary": spec["summary"],
                }
            )
        return rows

    return {
        "catalog_version": CATALOG_VERSION,
        "reads": _entries(READ_OPS, "read"),
        "writes": _entries(WRITE_OPS, "write"),
        "notes": (
            "Call run_named_query or run_named_write with a catalog label. "
            "Do not invent SQL. Per-label MCP tools and execute_query are not registered."
        ),
    }


def list_named_queries() -> str:
    return json.dumps(list_catalog(), indent=2)


def _merge_params(
    params_json: str | dict[str, Any] | None,
    flat: dict[str, Any],
) -> dict[str, Any]:
    params = _parse_params(params_json)
    for key, value in flat.items():
        if value is None or value == "":
            continue
        params.setdefault(key, value)
    if not params.get("claim_id") and params.get("case_id"):
        params["claim_id"] = params["case_id"]
    if not params.get("case_id") and params.get("claim_id"):
        params["case_id"] = params["claim_id"]
    return params


def _dispatch(
    label: str,
    params_json: str | dict[str, Any] | None,
    *,
    ops: dict[str, dict[str, Any]],
    kind: str,
    other_ops: dict[str, dict[str, Any]],
    other_kind: str,
    extra_params: dict[str, Any] | None = None,
) -> str:
    name = (label or "").strip()
    if name in other_ops:
        return _error(
            label=name,
            message=f"'{name}' is a {other_kind} op; use run_named_{other_kind}",
        )
    spec = ops.get(name)
    if spec is None:
        known = sorted(ops)
        return _error(
            label=name or None,
            message="unknown label",
            known_labels=known,
        )
    try:
        params = _merge_params(params_json, extra_params or {})
    except ValueError as exc:
        return _error(label=name, message=str(exc))
    missing = [k for k in spec["required"] if params.get(k) in (None, "")]
    if missing:
        return _error(
            label=name,
            message="missing required params",
            missing=missing,
            required=list(spec["required"]),
        )
    extra = [
        k
        for k in params
        if k not in spec["required"]
        and k not in spec["optional"]
        and k not in _ALIAS_KEYS
    ]
    if extra:
        return _error(
            label=name,
            message="unknown params",
            extra=extra,
            allowed=list(spec["required"]) + list(spec["optional"]),
        )
    handler: Callable[[dict[str, Any]], str] = spec["handler"]
    return _annotate(handler(params), kind=kind, label=name)


def run_named_query(
    label: str,
    params_json: str | dict[str, Any] | None = None,
    *,
    claim_id: str | None = None,
    case_id: str | None = None,
    database: str | None = None,
) -> str:
    """Run a catalog read by label. Flat claim_id / case_id is Studio-safe."""
    cid = claim_id or case_id
    return _dispatch(
        label,
        params_json,
        ops=READ_OPS,
        kind="read",
        other_ops=WRITE_OPS,
        other_kind="write",
        extra_params={"claim_id": cid, "case_id": cid, "database": database},
    )


def run_named_write(
    label: str,
    params_json: str | dict[str, Any] | None = None,
    *,
    run_id: str | None = None,
    event_json: str | None = None,
    evidence_json: str | None = None,
    database: str | None = None,
    source_branch: str | None = None,
) -> str:
    """Run a catalog write by label. Flat run_id/event_json is Studio-safe."""
    return _dispatch(
        label,
        params_json,
        ops=WRITE_OPS,
        kind="write",
        other_ops=READ_OPS,
        other_kind="query",
        extra_params={
            "run_id": run_id,
            "event_json": event_json,
            "evidence_json": evidence_json,
            "database": database,
            "source_branch": source_branch,
        },
    )
