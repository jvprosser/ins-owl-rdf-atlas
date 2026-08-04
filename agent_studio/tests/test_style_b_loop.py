"""Style B loop controller offline tests."""

from __future__ import annotations

from ins_claims_agent.mcp_facade import IcebergFacade, from_tool_map
from ins_claims_agent.workflow.style_b_loop import run_style_b_loop


def _spine():
    return {
        "claim_id": 401,
        "claim_number": "CLM-2025-000401",
        "claim_status_code": "OPEN",
        "litigation_indicator": False,
        "subrogation_indicator": True,
        "fraudulent_claim_indicator": False,
        "total_loss_indicator": False,
        "loss_event_id": 301,
        "loss_cause_code": "COLLISION",
        "policy_id": 1001,
        "policy_number": "PA-1001",
        "insurable_object_id": 201,
        "vin": "VIN",
        "policy_covers_vehicle": True,
        "policy_coverage_id": 3001,
        "coverage_type_code": "COLLISION",
        "claim_lifecycle_id": 7001,
        "roles": [
            {"claim_party_role_id": 6002, "role_type_code": "ADJUSTER", "party_id": 4},
        ],
    }


def _recording_iceberg():
    log = []

    def create_iceberg_branch(**kwargs):
        log.append(("create", kwargs))
        return "ok"

    def execute_iceberg_branch_dml(**kwargs):
        log.append(("dml", kwargs))
        return "ok"

    def fast_forward_iceberg_branch(**kwargs):
        log.append(("ff", kwargs))
        return "ok"

    def drop_iceberg_branch(**kwargs):
        log.append(("drop", kwargs))
        return "ok"

    facade = IcebergFacade(
        from_tool_map(
            {
                "iceberg-mcp-server-claims.create_iceberg_branch": create_iceberg_branch,
                "iceberg-mcp-server-claims.execute_iceberg_branch_dml": execute_iceberg_branch_dml,
                "iceberg-mcp-server-claims.fast_forward_iceberg_branch": fast_forward_iceberg_branch,
                "iceberg-mcp-server-claims.drop_iceberg_branch": drop_iceberg_branch,
            }
        )
    )
    return facade, log


def test_loop_opens_subro_then_closes():
    facade, log = _recording_iceberg()

    def worker(decision, graph):
        if decision["next_step"] == "OpenSubrogationCase":
            return {
                "applied_signals": {
                    "has_subrogation_case": True,
                    "subrogation_case_id": 8801,
                    "subrogation_status_code": "OPEN",
                    "has_police_report": True,
                    "has_fault_determination": True,
                    "has_recovery": True,
                    "recovery_ids": [1],
                },
                "applied_spine": {"subrogation_indicator": True, "claim_status_code": "CLOSED"},
            }
        return {}

    result = run_style_b_loop(
        401,
        "loop-1",
        iceberg=facade,
        worker=worker,
        spine=_spine(),
        signals={
            "has_subrogation_case": False,
            "has_police_report": True,
            "has_fault_determination": True,
        },
        promote_on_success=True,
    )
    assert result.decisions[0]["next_step"] == "OpenSubrogationCase"
    assert result.decisions[-1]["next_step"] == "CloseoutAudit"
    assert result.stop_reason == "terminal"
    assert result.promoted is True
    assert any(kind == "ff" for kind, _ in log)


def test_loop_no_progress_abandons():
    facade, log = _recording_iceberg()

    def worker(decision, graph):
        # Worker does nothing → same next_step forever
        return {}

    result = run_style_b_loop(
        401,
        "loop-2",
        iceberg=facade,
        worker=worker,
        spine=_spine(),
        signals={
            "has_subrogation_case": False,
            "has_police_report": True,
            "has_fault_determination": True,
        },
        promote_on_success=True,
    )
    assert result.stop_reason == "no_progress"
    assert result.promoted is False
    assert any(kind == "drop" for kind, _ in log)
