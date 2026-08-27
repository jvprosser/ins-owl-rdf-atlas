"""Evaluate playbook CEL expressions against a case JSON document."""

from __future__ import annotations

from datetime import date
from typing import Any

import celpy
from celpy.adapter import json_to_cel

_ENV = celpy.Environment()
_PROGRAMS: dict[str, Any] = {}
_LIST_KEYS = (
    "coverage_type_codes",
    "insured_operators",
    "offers",
    "hardship_reason_codes",
    "roles",
)
_STR_KEYS = (
    "docket_number",
    "filed_date",
    "closed_date",
    "served_date",
    "litigation_status_code",
    "incident_report_number",
    "loss_date",
    "effective_date",
    "expiration_date",
    "cancellation_date",
    "policy_status_code",
    "defense_counsel_party_id",
    "plaintiff_counsel_party_id",
)


def flatten_case(case: dict[str, Any]) -> dict[str, Any]:
    """Lift nested signals onto the root the same way YAML get_path did."""
    out = {k: v for k, v in case.items() if k != "signals"}
    nested = case.get("signals")
    if isinstance(nested, dict):
        inner = nested.get("signals") if isinstance(nested.get("signals"), dict) else nested
        if isinstance(inner, dict):
            for key, val in inner.items():
                if key == "signals":
                    continue
                cur = out.get(key)
                empty = cur is None or cur is False or cur == [] or cur == ""
                if empty:
                    if val not in (None, False, "", []):
                        out[key] = val
                    elif cur is None:
                        out[key] = val
    for key in _LIST_KEYS:
        if not isinstance(out.get(key), list):
            out[key] = []
    for key in _STR_KEYS:
        value = out.get(key)
        if value in (None,):
            out[key] = ""
        elif not isinstance(value, (list, dict, bool)):
            out[key] = str(value).strip()
    raw_short = out.get("rmd_shortfall_amount")
    if isinstance(raw_short, bool) or raw_short in (None, ""):
        out["rmd_shortfall_amount"] = 0
    elif not isinstance(raw_short, (int, float)):
        try:
            out["rmd_shortfall_amount"] = float(raw_short)
        except (TypeError, ValueError):
            out["rmd_shortfall_amount"] = 0
    out["eval_date"] = date.today().isoformat()
    return out


def compile_cel(expr: str) -> Any:
    text = (expr or "").strip()
    if not text:
        raise ValueError("CEL expression is empty")
    program = _PROGRAMS.get(text)
    if program is None:
        program = _ENV.program(_ENV.compile(text))
        _PROGRAMS[text] = program
    return program


def eval_cel(expr: str, case: dict[str, Any]) -> bool:
    """Return True when the CEL expression is true on the flattened case JSON."""
    program = compile_cel(expr)
    activation = json_to_cel(flatten_case(case))
    result = program.evaluate(activation)
    return bool(result)
