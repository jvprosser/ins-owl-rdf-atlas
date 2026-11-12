"""Studio stand-in for run_named_query / run_named_write.

The allow-list is ``catalog/catalog.yaml`` under Workflow Data. A label is
either one SQL file (``sql:``) or a claims procedure (``handler:``). Handlers
are the same functions the claims MCP calls. This module does not start MCP.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable

import yaml

from ins_claims_agent.studio_io import workflow_data_dir

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_READ_PREFIXES = ("select", "with", "show", "describe")
_WRITE_PREFIXES = ("insert", "update", "delete")
_ALIAS_KEYS = frozenset({"case_id", "claim_id", "fnol_id", "party_id"})

HANDLER_NAMES = frozenset(
    {
        "get_claim_spine",
        "get_claim_routing_signals",
        "get_litigation_view",
        "get_bi_view",
        "get_subrogation_view",
        "get_pd_view",
        "get_deny_view",
        "get_schema",
        "get_fnol_routing_signals",
        "write_audit_event",
        "append_agent_audit_event",
        "append_agent_audit_evidence",
        "begin_agent_audit_run",
        "promote_audit_run",
        "promote_agent_audit_run",
        "abandon_agent_audit_run",
        "create_litigation_task",
        "create_pd_task",
        "deny_claim",
        "deny_fnol",
        "close_fnol_incident_only",
        "convert_fnol_to_claim",
        "review_fnol",
    }
)

QueryFn = Callable[[str], list[dict[str, Any]]]
DmlFn = Callable[[str], str]


def catalog_path(root: Path | None = None) -> Path:
    base = root if root is not None else workflow_data_dir()
    return Path(base) / "catalog" / "catalog.yaml"


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    file = path or catalog_path()
    if not file.is_file():
        raise FileNotFoundError(f"named catalog not found: {file}")
    raw = yaml.safe_load(file.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"named catalog must be a mapping: {file}")
    raw["_path"] = file
    return raw


def execute(
    *,
    op: str,
    label: str | None = None,
    params: dict[str, Any] | None = None,
    catalog_file: Path | None = None,
    handlers: dict[str, Callable[[dict[str, Any]], str]] | None = None,
    query_rows: QueryFn | None = None,
    execute_dml: DmlFn | None = None,
) -> dict[str, Any]:
    """Run one allow-listed label. ``op`` is query, write, or list."""
    try:
        catalog = load_catalog(catalog_file)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        return _error(str(exc))

    kind = (op or "").strip().lower()
    if kind in {"list", "list_named_queries"}:
        return _list_payload(catalog)
    if kind not in {"query", "read", "write"}:
        return _error("op must be query, write, or list", op=kind or None)

    section = "reads" if kind in {"query", "read"} else "writes"
    name = (label or "").strip()
    reads = catalog.get("reads") or {}
    writes = catalog.get("writes") or {}
    if not isinstance(reads, dict) or not isinstance(writes, dict):
        return _error("catalog reads and writes must be mappings")
    if name in (writes if section == "reads" else reads):
        other_op = "write" if section == "reads" else "query"
        return _error(f"'{name}' is a {other_op} label", label=name)
    spec = (reads if section == "reads" else writes).get(name)
    if not isinstance(spec, dict):
        known = sorted((reads if section == "reads" else writes))
        return _error("unknown label", label=name or None, known_labels=known)

    try:
        bound = _bind_params(catalog, spec, params or {})
    except ValueError as exc:
        return _error(str(exc), label=name)

    missing = [key for key in spec.get("required") or [] if bound.get(key) in (None, "")]
    if missing:
        return _error("missing required params", label=name, missing=missing)

    if "handler" in spec and "sql" in spec:
        return _error("label sets both handler and sql", label=name)
    if "handler" in spec:
        return _run_handler(
            name,
            spec,
            bound,
            kind="read" if section == "reads" else "write",
            handlers=handlers,
        )
    if "sql" in spec:
        return _run_sql(
            catalog,
            name,
            spec,
            bound,
            kind="read" if section == "reads" else "write",
            query_rows=query_rows,
            execute_dml=execute_dml,
        )
    return _error("label needs handler or sql", label=name)


def render_sql(sql: str, bound: dict[str, Any]) -> str:
    """Substitute ${name} placeholders. Values are already validated."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in bound or bound[key] in (None, ""):
            raise ValueError(f"SQL placeholder ${{{key}}} has no value")
        return str(bound[key])

    rendered = _PLACEHOLDER.sub(repl, sql)
    if "${" in rendered or ";" in rendered:
        raise ValueError("SQL must be one statement with known placeholders only")
    return rendered.strip()


def _bind_params(catalog: dict[str, Any], spec: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    bound = {key: value for key, value in params.items() if value not in (None, "")}
    if not bound.get("claim_id") and bound.get("case_id"):
        bound["claim_id"] = bound["case_id"]
    if not bound.get("case_id") and bound.get("claim_id"):
        bound["case_id"] = bound["claim_id"]
    if not bound.get("fnol_id") and bound.get("claim_id"):
        bound["fnol_id"] = bound["claim_id"]
    if "database" not in bound:
        bound["database"] = catalog.get("database") or os.getenv(
            "IMPALA_DATABASE", "car_insurance_claims"
        )
    allowed = set(spec.get("required") or []) | set(spec.get("optional") or []) | _ALIAS_KEYS
    allowed.add("database")
    extra = [key for key in bound if key not in allowed]
    if extra:
        raise ValueError("unknown params: " + ", ".join(sorted(extra)))
    if not _IDENT.match(str(bound["database"])):
        raise ValueError("invalid database")
    for key in ("claim_id", "party_id"):
        if key in bound and key in allowed:
            bound[key] = str(int(bound[key]))
    if "fnol_id" in bound and "fnol_id" in allowed:
        bound["fnol_id"] = str(_parse_fnol_id(bound["fnol_id"]))
    if "run_id" in bound:
        bound["run_id_sql"] = "'" + str(bound["run_id"]).replace("'", "''") + "'"
    return bound


def _parse_fnol_id(value: Any) -> int:
    text = str(value).strip()
    if text.upper().startswith("FNOL-"):
        text = text.rsplit("-", 1)[-1]
    return int(text)


def _run_handler(
    name: str,
    spec: dict[str, Any],
    bound: dict[str, Any],
    *,
    kind: str,
    handlers: dict[str, Callable[[dict[str, Any]], str]] | None,
) -> dict[str, Any]:
    handler_name = str(spec["handler"])
    if handler_name not in HANDLER_NAMES:
        return _error("unknown handler", label=name, handler=handler_name)
    registry = handlers if handlers is not None else _default_handlers()
    handler = registry.get(handler_name)
    if handler is None:
        return _error("handler is not registered", label=name, handler=handler_name)
    raw = handler(bound)
    payload = _as_payload(raw)
    payload.setdefault("named_op", name)
    payload.setdefault("named_op_kind", kind)
    return payload


def _run_sql(
    catalog: dict[str, Any],
    name: str,
    spec: dict[str, Any],
    bound: dict[str, Any],
    *,
    kind: str,
    query_rows: QueryFn | None,
    execute_dml: DmlFn | None,
) -> dict[str, Any]:
    root = Path(catalog["_path"]).parent
    sql_path = root / str(spec["sql"])
    if not sql_path.is_file():
        return _error(f"SQL file not found: {spec['sql']}", label=name)
    try:
        statement = render_sql(sql_path.read_text(encoding="utf-8"), bound)
    except ValueError as exc:
        return _error(str(exc), label=name)
    prefix = statement.split(None, 1)[0].lower() if statement else ""
    if kind == "read" and prefix not in _READ_PREFIXES:
        return _error("read SQL must start with SELECT, WITH, SHOW, or DESCRIBE", label=name)
    if kind == "write" and prefix not in _WRITE_PREFIXES:
        return _error("write SQL must start with INSERT, UPDATE, or DELETE", label=name)
    try:
        if kind == "read":
            rows = (query_rows or _default_query_rows())(statement)
        else:
            message = (execute_dml or _default_execute_dml())(statement)
            if isinstance(message, str) and message.startswith("Error:"):
                return _error(message, label=name)
            return {
                "named_op": name,
                "named_op_kind": "write",
                "database": bound["database"],
                "ok": True,
                "result": message,
            }
    except Exception as exc:
        return _error(str(exc), label=name)
    return _shape_rows(str(spec.get("shape") or "rows"), name, bound, rows)


def _shape_rows(
    shape: str, name: str, bound: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    database = bound["database"]
    if shape == "rows":
        return {
            "named_op": name,
            "named_op_kind": "read",
            "database": database,
            "rows": rows,
        }
    if shape == "fnol_spine":
        if not rows:
            return _error(f"FNOL {bound.get('fnol_id')} not found", label=name, database=database)
        spine = dict(rows[0])
        for key in ("vehicle_listed_on_policy", "peril_covered"):
            if key in spine:
                spine[key] = _coerce_bool(spine[key])
        return {
            "named_op": name,
            "named_op_kind": "read",
            "fnol_id": int(bound["fnol_id"]),
            "database": database,
            "spine": spine,
        }
    if shape == "adjuster_claims":
        claims = [
            {
                "claim_id": row.get("claim_id"),
                "claim_number": row.get("claim_number"),
                "claim_status_code": row.get("claim_status_code"),
            }
            for row in rows
        ]
        first = rows[0] if rows else {}
        parts = [
            str(part).strip()
            for part in (first.get("first_name"), first.get("last_name"))
            if part not in (None, "")
        ]
        return {
            "named_op": name,
            "named_op_kind": "read",
            "party_id": int(bound["party_id"]),
            "adjuster_name": " ".join(parts) if parts else None,
            "database": database,
            "claims": claims,
        }
    return _error(f"unknown shape: {shape}", label=name)


def _list_payload(catalog: dict[str, Any]) -> dict[str, Any]:
    def entries(section: str, kind: str) -> list[dict[str, Any]]:
        rows = []
        for label, spec in (catalog.get(section) or {}).items():
            if not isinstance(spec, dict):
                continue
            rows.append(
                {
                    "label": label,
                    "kind": kind,
                    "required": list(spec.get("required") or []),
                    "optional": list(spec.get("optional") or []),
                    "summary": spec.get("summary"),
                    "source": "sql" if spec.get("sql") else "handler",
                }
            )
        return rows

    return {
        "catalog_version": catalog.get("version"),
        "database": catalog.get("database"),
        "reads": entries("reads", "read"),
        "writes": entries("writes", "write"),
    }


def _default_handlers() -> dict[str, Callable[[dict[str, Any]], str]]:
    from iceberg_mcp_server_claims.tools import (
        audit_tools,
        claim_tools,
        deny_claim,
        fnol_tools,
        fnol_writes,
        impala_tools,
        litigation_tasks,
        pd_tasks,
        view_tools,
    )

    def event(params: dict[str, Any]) -> str:
        return _json_arg(params.get("event_json"))

    def database(params: dict[str, Any]) -> Any:
        return params.get("database")

    return {
        "get_claim_spine": lambda p: claim_tools.get_claim_spine(str(p["claim_id"]), database(p)),
        "get_claim_routing_signals": lambda p: claim_tools.get_claim_routing_signals(
            str(p["claim_id"]), database(p)
        ),
        "get_litigation_view": lambda p: view_tools.get_litigation_view(str(p["claim_id"]), database(p)),
        "get_bi_view": lambda p: view_tools.get_bi_view(str(p["claim_id"]), database(p)),
        "get_subrogation_view": lambda p: view_tools.get_subrogation_view(
            str(p["claim_id"]), database(p)
        ),
        "get_pd_view": lambda p: view_tools.get_pd_view(str(p["claim_id"]), database(p)),
        "get_deny_view": lambda p: view_tools.get_deny_view(str(p["claim_id"]), database(p)),
        "get_schema": lambda p: impala_tools.get_schema(database(p)),
        "get_fnol_routing_signals": lambda p: fnol_tools.get_fnol_routing_signals(
            str(p["fnol_id"]), database(p)
        ),
        "write_audit_event": lambda p: audit_tools.append_agent_audit_event(
            str(p["run_id"]), event(p), database(p)
        ),
        "append_agent_audit_event": lambda p: audit_tools.append_agent_audit_event(
            str(p["run_id"]), event(p), database(p)
        ),
        "append_agent_audit_evidence": lambda p: audit_tools.append_agent_audit_evidence(
            str(p["run_id"]), _json_arg(p.get("evidence_json")), database(p)
        ),
        "begin_agent_audit_run": lambda p: audit_tools.begin_agent_audit_run(
            str(p["run_id"]), database(p), p.get("source_branch")
        ),
        "promote_audit_run": lambda p: audit_tools.promote_agent_audit_run(str(p["run_id"]), database(p)),
        "promote_agent_audit_run": lambda p: audit_tools.promote_agent_audit_run(
            str(p["run_id"]), database(p)
        ),
        "abandon_agent_audit_run": lambda p: audit_tools.abandon_agent_audit_run(
            str(p["run_id"]), database(p)
        ),
        "create_litigation_task": lambda p: litigation_tasks.create_litigation_task(
            str(p["run_id"]), event(p), database(p)
        ),
        "create_pd_task": lambda p: pd_tasks.create_pd_task(str(p["run_id"]), event(p), database(p)),
        "deny_claim": lambda p: deny_claim.deny_claim(str(p["run_id"]), event(p), database(p)),
        "deny_fnol": lambda p: fnol_writes.deny_fnol(str(p["run_id"]), event(p), database(p)),
        "close_fnol_incident_only": lambda p: fnol_writes.close_fnol_incident_only(
            str(p["run_id"]), event(p), database(p)
        ),
        "convert_fnol_to_claim": lambda p: fnol_writes.convert_fnol_to_claim(
            str(p["run_id"]), event(p), database(p)
        ),
        "review_fnol": lambda p: fnol_writes.review_fnol(str(p["run_id"]), event(p), database(p)),
    }


def _default_query_rows() -> QueryFn:
    from iceberg_mcp_server_claims.tools.impala_tools import query_rows

    return query_rows


def _default_execute_dml() -> DmlFn:
    from iceberg_mcp_server_claims.tools.impala_tools import execute_dml

    return execute_dml


def _json_arg(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value if value is not None else {}, default=str)


def _as_payload(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "error": raw}
    if isinstance(payload, dict):
        return payload
    return {"ok": False, "error": raw}


def _coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "t", "1", "yes"}:
        return True
    if text in {"false", "f", "0", "no"}:
        return False
    return bool(value)


def _error(message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"ok": False, "error": message}
    payload.update(extra)
    return payload
