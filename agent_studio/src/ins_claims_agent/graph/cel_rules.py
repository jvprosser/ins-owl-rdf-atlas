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
    "pending_court_orders",
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
    "hardship_category",
    "participant_marital_status",
    "distribution_type_code",
    "request_status_code",
)
_NUM_KEYS = (
    "rmd_shortfall_amount",
    "requested_amount",
    "documented_financial_need_amount",
    "estimated_tax_withholding_amount",
    "available_plan_loan_capacity",
    "prior_emergency_distributions_this_year",
)
_BOOL_KEYS = (
    "hold_or_aml_flag",
    "has_participant_self_certified",
    "requires_substantiation_audit",
    "plan_subject_to_qjsa",
    "plan_mandates_loan_exhaustion",
    "spousal_consent_verified",
    "has_active_qdro_hold",
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
    for key in _NUM_KEYS:
        raw = out.get(key)
        if isinstance(raw, bool) or raw in (None, ""):
            out[key] = 0
        elif not isinstance(raw, (int, float)):
            try:
                out[key] = float(raw)
            except (TypeError, ValueError):
                out[key] = 0
    for key in _BOOL_KEYS:
        value = out.get(key)
        if value in (None, ""):
            out[key] = False
        elif not isinstance(value, bool):
            out[key] = str(value).strip().lower() in {"true", "1", "yes"}
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
