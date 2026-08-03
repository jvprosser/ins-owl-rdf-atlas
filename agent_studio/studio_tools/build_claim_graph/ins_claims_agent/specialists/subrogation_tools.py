"""Subrogation worker tools — Iceberg reads only in Phase 1 scaffold."""

from __future__ import annotations

from typing import Any

from ins_claims_agent.mcp_facade import IcebergFacade


def get_subrogation_view(
    claim_id: int | str,
    *,
    iceberg: IcebergFacade,
    database: str = "car_insurance_claims",
) -> dict[str, Any]:
    """Fetch subrogation-oriented facts for the specialist agent."""
    # Prefer fork helper when available; fall back to explicit SQL via execute_query.
    try:
        signals = iceberg.get_claim_routing_signals(claim_id, database=database)
    except NotImplementedError:
        signals = {}
    query = f"""
    SELECT s.subrogation_case_id, s.subrogation_status_code, s.demand_amount,
           s.recovered_amount, s.adverse_party_id, s.adverse_carrier_party_id
    FROM {database}.subrogation_case s
    WHERE s.claim_id = {int(claim_id)}
    """
    try:
        rows = iceberg.execute_query(query)
    except NotImplementedError:
        rows = {"columns": [], "rows": []}
    return {"claim_id": str(claim_id), "signals": signals, "subrogation_case": rows}
