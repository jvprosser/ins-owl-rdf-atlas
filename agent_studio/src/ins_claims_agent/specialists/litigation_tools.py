"""Litigation worker tools."""

from __future__ import annotations

from typing import Any

from ins_claims_agent.mcp_facade import IcebergFacade


def get_litigation_view(
    claim_id: int | str,
    *,
    iceberg: IcebergFacade,
    database: str = "car_insurance_claims",
) -> dict[str, Any]:
    query = f"""
    SELECT litigation_case_id, litigation_status_code, docket_number,
           venue_name, plaintiff_party_id, filed_date, demand_amount
    FROM {database}.litigation_case
    WHERE claim_id = {int(claim_id)}
    """
    try:
        rows = iceberg.execute_query(query)
    except NotImplementedError:
        rows = {"columns": [], "rows": []}
    return {"claim_id": str(claim_id), "litigation_case": rows}
