"""Unit tests for audit helpers (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_finserv.tools import audit_tools


def test_begin_agent_audit_run_table_append():
    raw = audit_tools.begin_agent_audit_run("run_demo_1", "retirement_distributions")
    payload = json.loads(raw)
    assert payload["run_id"] == "run_demo_1"
    assert payload["mode"] == "table_append"
    assert payload["database"] == "retirement_distributions"


def test_begin_rejects_bad_run_id():
    raw = audit_tools.begin_agent_audit_run("../evil", "retirement_distributions")
    assert "error" in json.loads(raw)


def test_insert_audit_event_sql_targets_main_table():
    statement = audit_tools.insert_audit_event_sql(
        "retirement_distributions",
        {
            "run_id": "r1",
            "claim_id": "7002",
            "event_type": "ROUTE",
            "next_step": "RequestSubstantiation",
            "needs_llm": False,
            "terminal": False,
        },
    )
    assert "INSERT INTO retirement_distributions.agent_run_audit" in statement
    assert "branch_" not in statement
    assert "'r1'" in statement


def test_promote_is_noop_success():
    raw = audit_tools.promote_agent_audit_run("r1", "retirement_distributions")
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["mode"] == "table_append"
