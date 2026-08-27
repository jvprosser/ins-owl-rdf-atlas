"""Unit tests for deny_claim named write (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims.tools import deny_claim


def test_update_claim_denied_sql():
    sql = deny_claim.update_claim_denied_sql("car_insurance_claims", 404)
    assert "UPDATE car_insurance_claims.claim" in sql
    assert "claim_status_code = 'DENIED'" in sql
    assert "claim_id = 404" in sql
    assert "CLOSED" in sql
    assert "DENIED" in sql


def test_deny_claim_ok():
    captured: list[str] = []

    def fake_query(sql: str):
        assert "claim_status_code" in sql
        assert "404" in sql
        return [{"claim_status_code": "OPEN"}]

    def fake_dml(sql: str):
        captured.append(sql)
        return "OK"

    raw = deny_claim.deny_claim(
        "demo-404-deny",
        json.dumps(
            {"claim_id": "404", "next_step": "DenyUnlawfulOperation"}
        ),
        "car_insurance_claims",
        query_rows=fake_query,
        execute_dml=fake_dml,
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["claim_status_code"] == "DENIED"
    assert payload["next_step"] == "DenyUnlawfulOperation"
    assert payload["agent_role"] == "DenyAgent"
    assert payload["lane"] == "DENY"
    assert payload["terminal"] is True
    assert payload["audit_table"] == "agent_run_audit"
    assert len(captured) == 2
    assert "UPDATE car_insurance_claims.claim" in captured[0]
    assert "INSERT INTO car_insurance_claims.agent_run_audit" in captured[1]
    assert "DenyUnlawfulOperation" in captured[1]


def test_deny_claim_does_not_python_refuse_closed():
    captured: list[str] = []

    def fake_dml(sql: str):
        captured.append(sql)
        return "OK"

    raw = deny_claim.deny_claim(
        "demo-403-deny",
        json.dumps({"claim_id": "403", "next_step": "DenyLapsedPolicy"}),
        "car_insurance_claims",
        query_rows=lambda _sql: [{"claim_status_code": "CLOSED"}],
        execute_dml=fake_dml,
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert "NOT IN ('CLOSED', 'DENIED')" in captured[0]


def test_deny_claim_does_not_python_refuse_already_denied():
    captured: list[str] = []

    def fake_dml(sql: str):
        captured.append(sql)
        return "OK"

    raw = deny_claim.deny_claim(
        "demo-404-deny",
        json.dumps({"claim_id": "404", "next_step": "DenyExcludedDriver"}),
        "car_insurance_claims",
        query_rows=lambda _sql: [{"claim_status_code": "DENIED"}],
        execute_dml=fake_dml,
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert "NOT IN ('CLOSED', 'DENIED')" in captured[0]


def test_deny_claim_missing_claim():
    raw = deny_claim.deny_claim(
        "demo-404-deny",
        json.dumps({"claim_id": "999", "next_step": "DenyUnlawfulOperation"}),
        "car_insurance_claims",
        query_rows=lambda _sql: [],
        execute_dml=lambda _sql: "OK",
    )
    assert "not found" in json.loads(raw)["error"]


def test_deny_claim_rejects_deny_audit_step():
    raw = deny_claim.deny_claim(
        "demo-404-deny",
        json.dumps({"claim_id": "404", "next_step": "DenyAudit"}),
    )
    payload = json.loads(raw)
    assert "next_step" in payload["error"]


def test_deny_claim_requires_claim_id():
    raw = deny_claim.deny_claim(
        "demo-404-deny",
        json.dumps({"next_step": "DenyUnlawfulOperation"}),
    )
    assert "claim_id" in json.loads(raw)["error"]


def test_deny_claim_reports_audit_failure():
    def fake_dml(sql: str):
        if "agent_run_audit" in sql:
            return "Error: audit table missing"
        return "OK"

    raw = deny_claim.deny_claim(
        "demo-404-deny",
        json.dumps({"claim_id": "404", "next_step": "DenyLapsedPolicy"}),
        "car_insurance_claims",
        query_rows=lambda _sql: [{"claim_status_code": "OPEN"}],
        execute_dml=fake_dml,
    )
    payload = json.loads(raw)
    assert payload["ok"] is False
    assert payload["audit_written"] is False
    assert "audit table missing" in payload["error"]
