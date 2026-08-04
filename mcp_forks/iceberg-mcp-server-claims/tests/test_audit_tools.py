"""Unit tests for audit helpers (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims.tools import audit_tools


def test_begin_agent_audit_run_table_append():
    raw = audit_tools.begin_agent_audit_run("run_demo_1", "car_insurance_claims")
    payload = json.loads(raw)
    assert payload["run_id"] == "run_demo_1"
    assert payload["mode"] == "table_append"
    assert payload["database"] == "car_insurance_claims"


def test_begin_rejects_bad_run_id():
    raw = audit_tools.begin_agent_audit_run("../evil", "car_insurance_claims")
    assert "error" in json.loads(raw)


def test_insert_audit_event_sql_targets_main_table():
    sql = audit_tools.insert_audit_event_sql(
        "car_insurance_claims",
        {
            "run_id": "r1",
            "claim_id": "401",
            "event_type": "ROUTE",
            "next_step": "subrogation",
            "needs_llm": False,
            "terminal": False,
        },
    )
    assert "INSERT INTO car_insurance_claims.agent_run_audit" in sql
    assert "branch_" not in sql
    assert "'r1'" in sql


def test_promote_is_noop_success():
    raw = audit_tools.promote_agent_audit_run("r1", "car_insurance_claims")
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["mode"] == "table_append"
