"""Unit tests for send_client_notice (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_finserv.tools import notice_tools, sql


def test_insert_outbound_notice_sql():
    statement = sql.insert_outbound_notice_sql(
        "retirement_distributions",
        {
            "notice_id": 1,
            "distribution_request_id": 7013,
            "purpose_code": "REQUEST_SELF_CERTIFICATION",
            "channel_code": "LETTER",
            "body_text": "Please sign the hardship self-certification.",
            "run_id": "demo-7013-notice",
        },
    )
    assert "INSERT INTO retirement_distributions.distribution_outbound_notice" in statement
    assert "7013" in statement
    assert "REQUEST_SELF_CERTIFICATION" in statement


def test_send_client_notice_inserts_notice_and_audit():
    statements: list[str] = []

    def fake_dml(statement: str) -> str:
        statements.append(statement)
        return "ok"

    payload = json.loads(
        notice_tools.send_client_notice(
            "demo-7013-notice",
            json.dumps({"claim_id": "7013", "next_step": "RequestSelfCertification"}),
            "retirement_distributions",
            execute_dml=fake_dml,
        )
    )
    assert payload["ok"] is True
    assert payload["claim_id"] == 7013
    assert payload["next_step"] == "RequestSelfCertification"
    assert payload["purpose_code"] == "REQUEST_SELF_CERTIFICATION"
    assert payload["table"] == "distribution_outbound_notice"
    assert len(statements) == 2
    assert "distribution_outbound_notice" in statements[0]
    assert "agent_run_audit" in statements[1]


def test_send_client_notice_rejects_other_next_step():
    payload = json.loads(
        notice_tools.send_client_notice(
            "demo-7013-notice",
            json.dumps({"claim_id": "7013", "next_step": "RequestSubstantiation"}),
            "retirement_distributions",
            execute_dml=lambda _s: "ok",
        )
    )
    assert "error" in payload
    assert "RequestSelfCertification" in payload["error"]
