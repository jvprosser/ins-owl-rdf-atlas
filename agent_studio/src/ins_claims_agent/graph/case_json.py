"""Normalize MCP spine/signals into one case JSON document for YAML probes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ins_claims_agent.mcp_facade import IcebergFacade
from ins_claims_agent.pack import Pack
from ins_claims_agent.studio_io import normalize_signals_payload, normalize_spine_payload

DISCOVERY_AGING_DAYS = 90


def build_claim_graph(
    claim_id: int | str,
    *,
    iceberg: IcebergFacade | None = None,
    spine: dict[str, Any] | str | None = None,
    signals: dict[str, Any] | str | None = None,
    database: str = "car_insurance_claims",
) -> dict[str, Any]:
    """Return a case JSON document (Studio tool name unchanged)."""
    if spine is None:
        if iceberg is None:
            raise ValueError("Provide iceberg facade or spine dict")
        spine = iceberg.get_claim_spine(claim_id, database=database)
    if signals is None and iceberg is not None:
        signals = iceberg.get_claim_routing_signals(claim_id, database=database)
    return build_claim_case(claim_id, spine=spine, signals=signals or {})


def build_case_graph(
    case_id: int | str,
    *,
    pack: Pack,
    spine: dict[str, Any] | str | None = None,
    signals: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Pack-driven case JSON (Studio still calls this via build_claim_graph)."""
    return build_pack_case(case_id, pack=pack, spine=spine or {}, signals=signals or {})


def build_claim_case(
    claim_id: int | str,
    *,
    spine: dict[str, Any] | str | None = None,
    signals: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    spine = normalize_spine_payload(spine)
    signals = normalize_signals_payload(signals or {})

    coverage_codes = list(spine.get("coverage_type_codes") or [])
    if spine.get("coverage_type_code") and spine["coverage_type_code"] not in coverage_codes:
        coverage_codes.insert(0, spine["coverage_type_code"])

    roles = list(spine.get("roles") or [])
    offers = list(signals.get("offers") or [])
    if not offers:
        if signals.get("has_unresolved_offer"):
            offers = [{"offer_status_code": "EXTENDED"}]
        elif signals.get("has_accepted_offer"):
            offers = [{"offer_status_code": "ACCEPTED"}]
        elif signals.get("has_offer"):
            offers = [{"offer_status_code": "UNKNOWN"}]

    offer_status_codes = [o.get("offer_status_code") for o in offers if o.get("offer_status_code")]
    injury_ids = list(signals.get("injury_ids") or [])
    payment_ids = list(signals.get("payment_ids") or [])
    recovery_ids = list(signals.get("recovery_ids") or [])

    fraud_code = signals.get("fraud_outcome_code")
    if signals.get("has_siu_suspected") and not fraud_code:
        fraud_code = "SUSPECTED"

    policy_id = spine.get("policy_id")
    vehicle_id = spine.get("insurable_object_id")
    covers = spine.get("policy_covers_vehicle")
    if covers is None:
        covers = bool(policy_id is not None and vehicle_id is not None)
    has_policy = policy_id is not None and policy_id != ""
    has_vehicle = vehicle_id is not None and vehicle_id != ""

    has_subrogation_case = bool(
        signals.get("has_subrogation_case") or signals.get("subrogation_case_id") is not None
    )
    litigation_indicator = _as_bool(spine.get("litigation_indicator"))
    has_litigation_case = bool(
        signals.get("has_litigation_case") or signals.get("litigation_case_id") is not None
    )
    missing_docket_or_counsel, discovery_aging = _litigation_probe_flags(
        signals,
        in_litigation=litigation_indicator or has_litigation_case,
    )
    has_injury = bool(signals.get("has_injury") or injury_ids)
    has_loss_payment = bool(signals.get("has_loss_payment") or payment_ids)
    has_recovery = bool(signals.get("has_recovery") or recovery_ids)

    return {
        "claim_id": str(claim_id),
        "claim_exists": True,
        "claim_number": spine.get("claim_number"),
        "claim_status_code": spine.get("claim_status_code"),
        "litigation_indicator": litigation_indicator,
        "has_litigation_case": has_litigation_case,
        "litigation_case_id": signals.get("litigation_case_id"),
        "docket_number": signals.get("docket_number"),
        "defense_counsel_party_id": signals.get("defense_counsel_party_id"),
        "plaintiff_counsel_party_id": signals.get("plaintiff_counsel_party_id"),
        "served_date": signals.get("served_date"),
        "filed_date": signals.get("filed_date"),
        "closed_date": signals.get("closed_date"),
        "litigation_status_code": signals.get("litigation_status_code"),
        "missing_docket_or_counsel": missing_docket_or_counsel,
        "discovery_aging": discovery_aging,
        "subrogation_indicator": _as_bool(spine.get("subrogation_indicator")),
        "fraudulent_claim_indicator": _as_bool(spine.get("fraudulent_claim_indicator")),
        "total_loss_indicator": _as_bool(spine.get("total_loss_indicator")),
        "policy_id": policy_id,
        "policy_number": spine.get("policy_number"),
        "insurable_object_id": vehicle_id,
        "vin": spine.get("vin"),
        "policy_covers_vehicle": _as_bool(covers),
        "has_policy": has_policy,
        "has_vehicle": has_vehicle,
        "triangle": bool(has_policy and has_vehicle and covers),
        "coverage_type_codes": coverage_codes,
        "roles": roles,
        "has_adjuster": any(
            (r.get("role_type_code") or "").upper() == "ADJUSTER" for r in roles
        ),
        "has_police_report": _as_bool(signals.get("has_police_report")),
        "has_fault_determination": _as_bool(signals.get("has_fault_determination")),
        "injury_ids": injury_ids,
        "has_injury": has_injury,
        "offers": offers,
        "offer_status_codes": offer_status_codes,
        "has_extended_offer": "EXTENDED" in offer_status_codes,
        "has_accepted_offer": "ACCEPTED" in offer_status_codes,
        "payment_ids": payment_ids,
        "has_loss_payment": has_loss_payment,
        "recovery_ids": recovery_ids,
        "has_recovery": has_recovery,
        "has_subrogation_case": has_subrogation_case,
        "subrogation_case_id": signals.get("subrogation_case_id"),
        "subrogation_status_code": signals.get("subrogation_status_code"),
        "fraud_outcome_code": fraud_code,
        "has_siu_suspected": fraud_code in ("SUSPECTED", "PENDING"),
        "spine": spine,
        "signals": signals,
    }


def build_pack_case(
    case_id: int | str,
    *,
    pack: Pack,
    spine: dict[str, Any] | str | None = None,
    signals: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    spine = normalize_spine_payload(spine or {})
    signals = normalize_signals_payload(signals or {})
    merged: dict[str, Any] = {}
    if isinstance(spine, dict):
        inner = spine.get("spine") if isinstance(spine.get("spine"), dict) else spine
        merged.update(inner)
    if isinstance(signals, dict):
        inner_s = signals.get("signals") if isinstance(signals.get("signals"), dict) else signals
        merged.update(inner_s)

    case: dict[str, Any] = {
        "claim_id": str(case_id),
        "case_id": str(case_id),
        "case_exists": True,
        "case_class": str(pack.graph.get("case_class") or "Case"),
    }
    for field in _field_names(pack.graph.get("literals")):
        case[field] = merged.get(field)
    for field in _field_names(pack.graph.get("booleans")):
        case[field] = _as_bool(merged.get(field))
    case["spine"] = spine
    case["signals"] = signals
    case.update({k: v for k, v in merged.items() if k not in case})
    return case


def _field_names(mapping_or_list: Any) -> list[str]:
    if isinstance(mapping_or_list, dict):
        return [str(k) for k in mapping_or_list]
    return [str(x) for x in (mapping_or_list or [])]


def _as_bool(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes"}


def _blank(value: Any) -> bool:
    return value in (None, "", [], {})


def _days_since(value: Any) -> int | None:
    if _blank(value):
        return None
    if isinstance(value, datetime):
        filed = value.date()
    elif isinstance(value, date):
        filed = value
    else:
        try:
            filed = date.fromisoformat(str(value)[:10])
        except ValueError:
            return None
    return (date.today() - filed).days


def _litigation_probe_flags(
    signals: dict[str, Any],
    *,
    in_litigation: bool,
) -> tuple[bool, bool]:
    """Compute R1.2a / R1.2b flags from routing signals (not specialist Goal)."""
    has_file_fields = any(
        key in signals
        for key in (
            "docket_number",
            "defense_counsel_party_id",
            "plaintiff_counsel_party_id",
            "filed_date",
            "closed_date",
            "litigation_status_code",
        )
    )
    if has_file_fields or in_litigation:
        missing_docket = _blank(signals.get("docket_number"))
        missing_counsel = _blank(signals.get("defense_counsel_party_id")) and _blank(
            signals.get("plaintiff_counsel_party_id")
        )
        missing = in_litigation and (missing_docket or missing_counsel)
    else:
        missing = _as_bool(signals.get("missing_docket_or_counsel"))

    if has_file_fields:
        status = str(signals.get("litigation_status_code") or "").strip().upper()
        days = _days_since(signals.get("filed_date"))
        aging = (
            in_litigation
            and status == "IN_DISCOVERY"
            and _blank(signals.get("closed_date"))
            and days is not None
            and days > DISCOVERY_AGING_DAYS
        )
    else:
        aging = _as_bool(signals.get("discovery_aging"))
    return missing, aging
