"""Unit tests for Iceberg SQL/branch fallbacks (no live Hive)."""

from __future__ import annotations

import json

from ins_claims_agent.mcp_facade import IcebergFacade, from_tool_map
from ins_claims_agent.mcp_facade import iceberg_sql as sql


def _columns_rows(columns, rows):
    return json.dumps({"columns": columns, "rows": rows})


def test_parse_query_result_json_string():
    raw = _columns_rows(["a", "b"], [[1, "x"], [2, "y"]])
    assert sql.parse_query_result(raw) == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]


def test_audit_branch_name():
    assert sql.audit_branch_name("run-42") == "agent_run_run_42"


def test_get_claim_spine_sql_fallback():
    calls: list[str] = []

    def execute_query(query: str):
        calls.append(query)
        if "FROM car_insurance_claims.claim c" in query:
            return _columns_rows(
                [
                    "claim_id",
                    "claim_number",
                    "claim_status_code",
                    "litigation_indicator",
                    "subrogation_indicator",
                    "fraudulent_claim_indicator",
                    "total_loss_indicator",
                    "loss_event_id",
                    "loss_cause_code",
                    "policy_id",
                    "policy_number",
                    "insurable_object_id",
                    "vin",
                    "policy_covers_vehicle",
                    "policy_coverage_id",
                    "coverage_type_code",
                    "claim_lifecycle_id",
                ],
                [
                    [
                        401,
                        "CLM-2025-000401",
                        "OPEN",
                        False,
                        True,
                        False,
                        False,
                        301,
                        "COLLISION",
                        1001,
                        "PA-1001",
                        201,
                        "VIN1",
                        True,
                        3001,
                        "COLLISION",
                        7001,
                    ]
                ],
            )
        if "claim_party_role" in query:
            return _columns_rows(
                ["claim_party_role_id", "party_id", "role_type_code", "is_current_assignment"],
                [[6002, 4, "ADJUSTER", True]],
            )
        raise AssertionError(f"unexpected query: {query}")

    facade = IcebergFacade(
        from_tool_map(
            {
                "iceberg-mcp-server-hive.execute_query": execute_query,
            }
        )
    )
    spine = facade.get_claim_spine(401)
    assert spine["claim_id"] == 401
    assert spine["coverage_type_code"] == "COLLISION"
    assert spine["roles"][0]["role_type_code"] == "ADJUSTER"
    assert spine["_source"] == "execute_query_fallback"
    assert any("claim c" in c for c in calls)


def test_get_routing_signals_sql_fallback():
    def execute_query(query: str):
        if "has_subrogation_case" in query:
            return _columns_rows(
                [
                    "has_subrogation_case",
                    "subrogation_case_id",
                    "subrogation_status_code",
                    "has_litigation_case",
                    "litigation_case_id",
                    "has_injury",
                    "has_police_report",
                    "police_report_id",
                    "has_fault_determination",
                    "fault_determination_id",
                    "has_offer",
                    "has_unresolved_offer",
                    "has_accepted_offer",
                    "has_loss_payment",
                    "has_recovery",
                    "has_current_reserve",
                    "has_siu_suspected",
                    "fraud_assessment_id",
                    "fraud_outcome_code",
                    "has_document",
                ],
                [
                    [
                        True,
                        8801,
                        "NEGOTIATING",
                        False,
                        None,
                        False,
                        True,
                        5301,
                        True,
                        5401,
                        True,
                        False,
                        True,
                        True,
                        True,
                        True,
                        False,
                        None,
                        None,
                        True,
                    ]
                ],
            )
        if "claim_injury" in query:
            return _columns_rows(["claim_injury_id"], [])
        if "claim_offer" in query:
            return _columns_rows(
                ["claim_offer_id", "offer_status_code"], [[9001, "ACCEPTED"]]
            )
        if "claim_payment" in query:
            return _columns_rows(["claim_payment_id"], [[9201]])
        if "claim_recovery" in query:
            return _columns_rows(["claim_recovery_id"], [[8901]])
        raise AssertionError(query)

    facade = IcebergFacade(
        from_tool_map({"iceberg-mcp-server-hive.execute_query": execute_query})
    )
    signals = facade.get_claim_routing_signals(401)
    assert signals["has_subrogation_case"] is True
    assert signals["subrogation_case_id"] == 8801
    assert signals["offers"][0]["offer_status_code"] == "ACCEPTED"
    assert signals["payment_ids"] == [9201]


def test_begin_audit_run_branch_fallback():
    created = []

    def create_iceberg_branch(database, table, branch_name, **kwargs):
        created.append((database, table, branch_name))
        return "ok"

    facade = IcebergFacade(
        from_tool_map(
            {"iceberg-mcp-server-hive.create_iceberg_branch": create_iceberg_branch}
        )
    )
    result = facade.begin_agent_audit_run("abc-1", database="car_insurance_claims")
    assert result["branch_name"] == "agent_run_abc_1"
    assert {t for _, t, _ in created} == {"agent_run_audit", "agent_run_evidence"}


def test_append_audit_event_branch_dml():
    statements = []

    def execute_iceberg_branch_dml(database, table, branch_name, statement):
        statements.append((database, table, branch_name, statement))
        return "Query executed successfully."

    facade = IcebergFacade(
        from_tool_map(
            {
                "iceberg-mcp-server-hive.execute_iceberg_branch_dml": execute_iceberg_branch_dml,
            }
        )
    )
    facade.append_agent_audit_event(
        "run1",
        {
            "run_id": "run1",
            "event_ts": "2025-08-03T12:00:00+00:00",
            "claim_id": "401",
            "event_type": "ROUTE_DECISION",
            "next_step": "OpenSubrogationCase",
            "reason_probe_ids": ["R4.1"],
            "payload_json": {"ok": True},
        },
    )
    assert len(statements) == 1
    db, table, branch, stmt = statements[0]
    assert table == "agent_run_audit"
    assert branch == "agent_run_run1"
    assert "INSERT INTO car_insurance_claims.agent_run_audit.branch_agent_run_run1" in stmt
    assert "OpenSubrogationCase" in stmt
