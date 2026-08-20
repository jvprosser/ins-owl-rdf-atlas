"""P0 claim helpers: get_claim_spine + get_claim_routing_signals."""

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


def get_claim_spine(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    """Return claim + loss + policy + vehicle + current roles + lifecycle.

    JSON shape::

        {
          "claim_id": ...,
          "spine": { ... spine columns ... },
          "roles": [ ... ],
          "database": "..."
        }
    """
    from iceberg_mcp_server_claims.tools.impala_tools import query_rows as _qr

    qr = query_rows or _qr
    db = claim_sql.validate_ident(_default_database(database), "database")
    cid = str(int(claim_id))

    try:
        spine_rows = qr(claim_sql.claim_spine_sql(cid, db))
        role_rows = qr(claim_sql.claim_roles_sql(cid, db))
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})

    if not spine_rows:
        return json.dumps(
            {
                "error": f"Claim {cid} not found",
                "claim_id": cid,
                "database": db,
            }
        )

    spine = _bool_fields(
        spine_rows[0],
        [
            "litigation_indicator",
            "subrogation_indicator",
            "fraudulent_claim_indicator",
            "total_loss_indicator",
            "policy_covers_vehicle",
        ],
    )
    roles = [
        _bool_fields(r, ["is_current_assignment"]) for r in role_rows
    ]
    return json.dumps(
        {
            "claim_id": int(cid),
            "database": db,
            "spine": spine,
            "roles": roles,
        },
        default=str,
    )


def get_claim_routing_signals(
    claim_id: str,
    database: str | None = None,
    *,
    query_rows: QueryFn | None = None,
) -> str:
    """Return existence / routing flags for playbook probe inputs.

    JSON shape::

        {
          "claim_id": ...,
          "signals": { ... },
          "injury_ids": [...],
          "offers": [...],
          "payment_ids": [...],
          "recovery_ids": [...],
          "database": "..."
        }
    """
    from iceberg_mcp_server_claims.tools.impala_tools import query_rows as _qr

    qr = query_rows or _qr
    db = claim_sql.validate_ident(_default_database(database), "database")
    cid = str(int(claim_id))

    bool_keys = [
        "has_subrogation_case",
        "has_litigation_case",
        "has_injury",
        "has_police_report",
        "has_fault_determination",
        "has_offer",
        "has_unresolved_offer",
        "has_accepted_offer",
        "has_loss_payment",
        "has_recovery",
        "has_current_reserve",
        "has_siu_suspected",
        "has_document",
        "missing_docket_or_counsel",
        "discovery_aging",
        "insured_operator_cited",
        "unlawful_operation_exclusion",
        "excluded_operator_exclusion",
        "policy_not_in_force_on_loss",
    ]

    try:
        if query_rows is None:
            from iceberg_mcp_server_claims.tools.impala_tools import refresh_table

            for table in ("loss_driver", "claim", "police_report", "fault_determination"):
                try:
                    refresh_table(db, table)
                except Exception:
                    pass
        signal_rows = qr(claim_sql.claim_routing_signals_sql(cid, db))
        injuries = qr(claim_sql.claim_injury_ids_sql(cid, db))
        offers = qr(claim_sql.claim_offers_sql(cid, db))
        payments = qr(claim_sql.claim_payment_ids_sql(cid, db))
        recoveries = qr(claim_sql.claim_recovery_ids_sql(cid, db))
    except Exception as exc:
        return json.dumps({"error": str(exc), "claim_id": cid, "database": db})

    signals = _bool_fields(signal_rows[0] if signal_rows else {}, bool_keys)
    return json.dumps(
        {
            "claim_id": int(cid),
            "database": db,
            "signals": signals,
            "injury_ids": [r.get("claim_injury_id") for r in injuries],
            "offers": offers,
            "payment_ids": [r.get("claim_payment_id") for r in payments],
            "recovery_ids": [r.get("claim_recovery_id") for r in recoveries],
        },
        default=str,
    )
