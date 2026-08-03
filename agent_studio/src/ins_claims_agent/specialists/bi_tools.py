"""BI claims worker tools."""

from __future__ import annotations

from typing import Any

from ins_claims_agent.mcp_facade import IcebergFacade


def get_bi_view(
    claim_id: int | str,
    *,
    iceberg: IcebergFacade,
    database: str = "car_insurance_claims",
) -> dict[str, Any]:
    query = f"""
    SELECT claim_injury_id, injured_party_id, injury_severity_code,
           body_region_code, medical_provider_party_id
    FROM {database}.claim_injury
    WHERE claim_id = {int(claim_id)}
    """
    try:
        rows = iceberg.execute_query(query)
    except NotImplementedError:
        rows = {"columns": [], "rows": []}
    return {"claim_id": str(claim_id), "injuries": rows}
