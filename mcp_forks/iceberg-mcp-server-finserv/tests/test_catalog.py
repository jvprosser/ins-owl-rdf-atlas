"""Named query/write catalog (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_finserv import catalog


def test_unknown_read_label():
    payload = json.loads(catalog.run_named_query("invent_sql", "{}"))
    assert payload["error"] is True
    assert "get_distribution_spine" in payload["known_labels"]
    assert "get_claim_spine" not in payload["known_labels"]
    assert "get_rollover_spine" not in payload["known_labels"]


def test_write_label_rejected_on_query():
    payload = json.loads(catalog.run_named_query("write_audit_event", "{}"))
    assert payload["error"] is True
    assert "run_named_write" in payload["message"]


def test_missing_required_param():
    payload = json.loads(catalog.run_named_query("get_distribution_spine", "{}"))
    assert payload["missing"] == ["claim_id"]


def test_bad_params_json():
    payload = json.loads(catalog.run_named_query("get_distribution_spine", "not-json"))
    assert payload["error"] is True
    assert "JSON object" in payload["message"]


def test_extra_param_rejected():
    payload = json.loads(
        catalog.run_named_query(
            "get_distribution_spine",
            json.dumps({"claim_id": "7002", "select": "*"}),
        )
    )
    assert payload["extra"] == ["select"]


def test_read_dispatches_to_spine(monkeypatch):
    monkeypatch.setattr(
        catalog.dist_tools,
        "get_distribution_spine",
        lambda claim_id, database=None: json.dumps(
            {
                "claim_id": str(claim_id),
                "spine": {"distribution_type_code": "HARDSHIP"},
            }
        ),
    )
    payload = json.loads(
        catalog.run_named_query("get_distribution_spine", '{"claim_id":"7002"}')
    )
    assert payload["named_op"] == "get_distribution_spine"
    assert payload["named_op_kind"] == "read"
    assert payload["spine"]["distribution_type_code"] == "HARDSHIP"


def test_flat_claim_id_without_params_json(monkeypatch):
    monkeypatch.setattr(
        catalog.dist_tools,
        "get_distribution_spine",
        lambda claim_id, database=None: json.dumps(
            {"claim_id": str(claim_id), "spine": {}}
        ),
    )
    payload = json.loads(catalog.run_named_query("get_distribution_spine", claim_id="7002"))
    assert payload["named_op"] == "get_distribution_spine"
    assert payload["claim_id"] == "7002"


def test_write_dispatches(monkeypatch):
    monkeypatch.setattr(
        catalog.audit_tools,
        "append_agent_audit_event",
        lambda run_id, event_json, database=None: json.dumps(
            {"ok": True, "run_id": run_id, "table": "agent_run_audit"}
        ),
    )
    payload = json.loads(
        catalog.run_named_write(
            "write_audit_event",
            json.dumps(
                {
                    "run_id": "demo-7002",
                    "event_json": {"event_type": "RequestSubstantiation", "claim_id": "7002"},
                }
            ),
        )
    )
    assert payload["ok"] is True
    assert payload["named_op"] == "write_audit_event"


def test_write_dispatches_send_client_notice(monkeypatch):
    monkeypatch.setattr(
        catalog.notice_tools,
        "send_client_notice",
        lambda run_id, event_json, database=None: json.dumps(
            {"ok": True, "run_id": run_id, "table": "distribution_outbound_notice"}
        ),
    )
    payload = json.loads(
        catalog.run_named_write(
            "send_client_notice",
            json.dumps(
                {
                    "run_id": "demo-7013",
                    "event_json": {
                        "claim_id": "7013",
                        "next_step": "RequestSelfCertification",
                    },
                }
            ),
        )
    )
    assert payload["ok"] is True
    assert payload["named_op"] == "send_client_notice"


def test_list_named_queries_is_distributions_only():
    listing = catalog.list_catalog()
    reads = {row["label"] for row in listing["reads"]}
    writes = {row["label"] for row in listing["writes"]}
    assert {
        "get_distribution_spine",
        "get_distribution_routing_signals",
        "get_distribution_exception_view",
        "get_rmd_view",
        "get_compliance_view",
        "get_loan_summary_view",
        "get_qdro_details_view",
        "get_schema",
    } <= reads
    assert {"write_audit_event", "promote_audit_run", "send_client_notice"} <= writes
    assert "get_claim_spine" not in reads
    assert "create_litigation_task" not in writes
