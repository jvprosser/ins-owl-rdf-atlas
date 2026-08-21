"""Unit tests for create_pd_task named write (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims.tools import pd_tasks


def test_insert_pd_task_sql():
    sql = pd_tasks.insert_pd_task_sql(
        "car_insurance_claims",
        {
            "pd_task_id": 1,
            "claim_id": 401,
            "loss_event_id": 301,
            "task_type_code": "REQUEST_POLICE_REPORT",
            "task_status_code": "OPEN",
            "due_date": None,
            "run_id": "demo-401-pd",
        },
    )
    assert "INSERT INTO car_insurance_claims.pd_task" in sql
    assert "incident_report_number" in sql
    assert "REQUEST_POLICE_REPORT" in sql
    assert "401" in sql
    assert "301" in sql


def test_create_pd_task_ok():
    captured: list[str] = []

    def fake_dml(sql: str):
        captured.append(sql)
        return "OK"

    raw = pd_tasks.create_pd_task(
        "demo-401-pd",
        json.dumps(
            {
                "claim_id": "401",
                "task_type_code": "DETERMINE_FAULT",
                "loss_event_id": 301,
            }
        ),
        "car_insurance_claims",
        execute_dml=fake_dml,
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["task_type_code"] == "DETERMINE_FAULT"
    assert payload["claim_id"] == 401
    assert payload["table"] == "pd_task"
    assert payload["audit_table"] == "agent_run_audit"
    assert payload["next_step"] == "DetermineFault"
    assert len(captured) == 2
    assert "INSERT INTO car_insurance_claims.pd_task" in captured[0]
    assert "INSERT INTO car_insurance_claims.agent_run_audit" in captured[1]
    assert "DetermineFault" in captured[1]


def test_create_pd_task_reports_audit_failure():
    captured: list[str] = []

    def fake_dml(sql: str):
        captured.append(sql)
        if "agent_run_audit" in sql:
            return "Error: audit table missing"
        return "OK"

    raw = pd_tasks.create_pd_task(
        "demo-401-pd",
        json.dumps({"claim_id": "401", "task_type_code": "PD_REVIEW"}),
        "car_insurance_claims",
        execute_dml=fake_dml,
    )
    payload = json.loads(raw)
    assert payload["ok"] is False
    assert payload["audit_written"] is False
    assert payload["table"] == "pd_task"
    assert "audit table missing" in payload["error"]


def test_create_pd_task_rejects_bad_type():
    raw = pd_tasks.create_pd_task(
        "demo-401-pd",
        json.dumps({"claim_id": "401", "task_type_code": "INVENT"}),
        execute_dml=lambda _sql: "OK",
    )
    payload = json.loads(raw)
    assert "error" in payload
    assert "task_type_code" in payload["error"]


def test_create_pd_task_requires_claim_id():
    raw = pd_tasks.create_pd_task(
        "demo-401-pd",
        json.dumps({"task_type_code": "PD_REVIEW"}),
        execute_dml=lambda _sql: "OK",
    )
    assert "claim_id" in json.loads(raw)["error"]


def test_create_pd_task_collect_sends_sms():
    captured: list[str] = []

    def fake_dml(sql: str):
        captured.append(sql)
        return "OK"

    def fake_query(sql: str):
        assert "phone_number" in sql
        return [{"phone_number": "+1-555-0101"}]

    raw = pd_tasks.create_pd_task(
        "demo-401-pd",
        json.dumps({"claim_id": "401", "task_type_code": "COLLECT_INCIDENT_NUMBER"}),
        "car_insurance_claims",
        query_rows=fake_query,
        execute_dml=fake_dml,
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["next_step"] == "CollectIncidentReportNumber"
    assert payload["to_phone"] == "+1-555-0101"
    assert "claims app" in payload["sms_body"]
    assert payload["sms_table"] == "claim_outbound_message"
    assert any("claim_outbound_message" in s for s in captured)
    assert len(captured) == 3
    assert "401" not in payload["sms_body"]
    assert "CLM-" not in payload["sms_body"]


def test_create_pd_task_request_requires_incident_number():
    raw = pd_tasks.create_pd_task(
        "demo-401-pd",
        json.dumps({"claim_id": "401", "task_type_code": "REQUEST_POLICE_REPORT"}),
        "car_insurance_claims",
        query_rows=lambda _sql: [],
        execute_dml=lambda _sql: "OK",
    )
    payload = json.loads(raw)
    assert "incident_report_number" in payload["error"]


def test_create_pd_task_request_stores_incident_number():
    captured: list[str] = []

    def fake_dml(sql: str):
        captured.append(sql)
        return "OK"

    raw = pd_tasks.create_pd_task(
        "demo-401-pd",
        json.dumps({"claim_id": "401", "task_type_code": "REQUEST_POLICE_REPORT"}),
        "car_insurance_claims",
        query_rows=lambda _sql: [{"incident_report_number": "SPD-25-11887"}],
        execute_dml=fake_dml,
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["incident_report_number"] == "SPD-25-11887"
    assert "SPD-25-11887" in captured[0]
    assert "SPD-25-11887" in captured[1]
