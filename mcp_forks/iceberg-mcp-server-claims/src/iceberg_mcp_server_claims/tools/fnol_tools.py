"""Named reads: get_fnol_spine + get_fnol_routing_signals."""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from iceberg_mcp_server_claims.tools import claim_sql


QueryFn = Callable[[str], list[dict[str, Any]]]


def _default_database(database: str | None) -> str:
    return database or os.getenv("IMPALA_DATABASE", "car_insurance_claims")


def _bool_fields(row: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    out = dict(row)
    for key in keys:
        if key in out:
            out[key] = claim_sql.coerce_bool(out[key])
    return out


def get_fnol_spine(
    fnol_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    qr = query_rows
    if qr is None:
        from iceberg_mcp_server_claims.tools.impala_tools import query_rows as _qr

        qr = _qr
    db = claim_sql.validate_ident(_default_database(database), "database")
    try:
        fid = str(claim_sql.parse_fnol_id(fnol_id))
    except (TypeError, ValueError) as exc:
        return json.dumps({"error": f"invalid fnol_id: {exc}", "fnol_id": fnol_id})

    try:
        spine_rows = qr(claim_sql.fnol_spine_sql(fid, db))
    except Exception as exc:
        return json.dumps({"error": str(exc), "fnol_id": int(fid), "database": db})

    if not spine_rows:
        return json.dumps(
            {
                "error": f"FNOL {fid} not found",
                "fnol_id": int(fid),
                "database": db,
            }
        )

    spine = _bool_fields(
        spine_rows[0],
        ["vehicle_listed_on_policy", "peril_covered"],
    )
    return json.dumps(
        {
            "fnol_id": int(fid),
            "database": db,
            "spine": spine,
        },
        default=str,
    )


def get_fnol_routing_signals(
    fnol_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    qr = query_rows
    if qr is None:
        from iceberg_mcp_server_claims.tools.impala_tools import query_rows as _qr

        qr = _qr
    db = claim_sql.validate_ident(_default_database(database), "database")
    try:
        fid = str(claim_sql.parse_fnol_id(fnol_id))
    except (TypeError, ValueError) as exc:
        return json.dumps({"error": f"invalid fnol_id: {exc}", "fnol_id": fnol_id})

    bool_keys = [
        "has_injury",
        "has_third_party_vehicle",
        "has_unlisted_insured_operator",
        "vehicle_listed_on_policy",
        "peril_covered",
    ]
    try:
        signal_rows = qr(claim_sql.fnol_routing_signals_sql(fid, db))
        spine_rows = qr(claim_sql.fnol_spine_sql(fid, db))
    except Exception as exc:
        return json.dumps({"error": str(exc), "fnol_id": int(fid), "database": db})

    if not spine_rows:
        return json.dumps(
            {
                "error": f"FNOL {fid} not found",
                "fnol_id": int(fid),
                "database": db,
            }
        )

    signals = _bool_fields(signal_rows[0] if signal_rows else {}, bool_keys[:3])
    spine = _bool_fields(spine_rows[0], bool_keys[3:])
    signals["vehicle_listed_on_policy"] = spine.get("vehicle_listed_on_policy")
    signals["peril_covered"] = spine.get("peril_covered")
    signals["estimated_loss_amount"] = spine.get("estimated_loss_amount")
    signals["deductible_amount"] = spine.get("deductible_amount")
    signals["intake_purpose_code"] = spine.get("intake_purpose_code")
    signals["triage_status_code"] = spine.get("triage_status_code")
    signals["fnol_exists"] = True
    return json.dumps(
        {
            "fnol_id": int(fid),
            "database": db,
            "signals": signals,
        },
        default=str,
    )
