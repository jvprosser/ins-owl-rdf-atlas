"""WAP audit orchestration via Iceberg MCP branch helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ins_claims_agent.mcp_facade import IcebergFacade


def begin_audit_run(
    run_id: str,
    *,
    iceberg: IcebergFacade,
    database: str = "car_insurance_claims",
    source_branch: str | None = None,
) -> Any:
    return iceberg.begin_agent_audit_run(run_id, database=database, source_branch=source_branch)


def write_audit_event(
    run_id: str,
    event: dict[str, Any],
    *,
    iceberg: IcebergFacade,
) -> Any:
    payload = {
        "run_id": run_id,
        "event_ts": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    return iceberg.append_agent_audit_event(run_id, json.dumps(payload))


def write_audit_evidence(
    run_id: str,
    evidence: dict[str, Any],
    *,
    iceberg: IcebergFacade,
) -> Any:
    payload = {
        "run_id": run_id,
        "evidence_ts": datetime.now(timezone.utc).isoformat(),
        **evidence,
    }
    return iceberg.append_agent_audit_evidence(run_id, json.dumps(payload))


def promote_audit_run(run_id: str, *, iceberg: IcebergFacade) -> Any:
    return iceberg.promote_agent_audit_run(run_id)


def abandon_audit_run(run_id: str, *, iceberg: IcebergFacade) -> Any:
    return iceberg.abandon_agent_audit_run(run_id)
