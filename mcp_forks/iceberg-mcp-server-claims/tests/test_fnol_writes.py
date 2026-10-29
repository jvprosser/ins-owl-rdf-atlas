"""FNOL named writes (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims.tools import fnol_writes


def _fnol_row(**overrides: object) -> dict:
    row = {
        "fnol_id": 88,
        "fnol_number": "FNOL-2026-00088",
        "triage_status_code": "OPEN",
        "claim_id": None,
        "policy_id": 1088,
        "insurable_object_id": 288,
        "loss_event_id": 388,
        "estimated_loss_amount": 450,
        "intake_purpose_code": "RECORD_ONLY_NOTIFICATION",
    }
    row.update(overrides)
    return row


def test_deny_fnol_updates_status():
    dml_sql: list[str] = []

    def qr(sql: str):
        return [_fnol_row()]

    def dml(sql: str):
        dml_sql.append(sql)
        return "ok"

    raw = fnol_writes.deny_fnol(
        "demo-fnol-88-deny",
        json.dumps({"fnol_id": "88", "next_step": "DenyFnolNoCoverage"}),
        "car_insurance_claims",
        query_rows=qr,
        execute_dml=dml,
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["triage_status_code"] == "DENIED"
    assert payload["table"] == "fnol"
    assert any("triage_status_code = 'DENIED'" in s for s in dml_sql)
    assert any("agent_run_audit" in s for s in dml_sql)


def test_close_fnol_incident_only():
    def qr(sql: str):
        return [_fnol_row()]

    def dml(sql: str):
        return "ok"

    raw = fnol_writes.close_fnol_incident_only(
        "demo-fnol-88-e2e",
        json.dumps({"fnol_id": 88, "next_step": "ConvertFnolToIncidentOnly"}),
        "car_insurance_claims",
        query_rows=qr,
        execute_dml=dml,
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["triage_status_code"] == "INCIDENT_ONLY"


def test_convert_fnol_to_claim_inserts_then_is_idempotent():
    state = {"claim_id": None}
    dml_sql: list[str] = []

    def qr(sql: str):
        if "policy_coverage" in sql:
            return [{"policy_coverage_id": 3088, "deductible_amount": 1000}]
        if "policy_party_role" in sql:
            return [{"party_id": 15}]
        return [_fnol_row(claim_id=state["claim_id"])]

    def dml(sql: str):
        dml_sql.append(sql)
        if "INSERT INTO" in sql and ".claim (" in sql:
            state["claim_id"] = 80088
        if "triage_status_code = 'CONVERTED'" in sql:
            state["claim_id"] = 80088
        return "ok"

    first = json.loads(
        fnol_writes.convert_fnol_to_claim(
            "demo-fnol-88-convert",
            json.dumps({"fnol_id": "88", "next_step": "ConvertFnolToClaim"}),
            "car_insurance_claims",
            query_rows=qr,
            execute_dml=dml,
        )
    )
    assert first["ok"] is True
    assert first["claim_id"] == 80088
    assert first["already_applied"] is False
    assert first["reserve_written"] is True
    assert any("INSERT INTO" in s and ".claim (" in s for s in dml_sql)
    role_sql = [s for s in dml_sql if "claim_party_role" in s]
    assert len(role_sql) == 2
    assert any("'INSURED'" in s and "15" in s for s in role_sql)
    assert any("'ADJUSTER'" in s and "4" in s for s in role_sql)

    dml_sql.clear()
    second = json.loads(
        fnol_writes.convert_fnol_to_claim(
            "demo-fnol-88-convert-2",
            json.dumps({"fnol_id": "88", "next_step": "ConvertFnolToClaim"}),
            "car_insurance_claims",
            query_rows=qr,
            execute_dml=dml,
        )
    )
    assert second["ok"] is True
    assert second["claim_id"] == 80088
    assert second["already_applied"] is True
    assert not any("INSERT INTO" in s and ".claim (" in s for s in dml_sql)
