"""Named query/write catalog (no Impala)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from iceberg_mcp_server_underwriting import catalog
from iceberg_mcp_server_underwriting.tools import uw_writes

REPO = Path(__file__).resolve().parents[3]


def test_unknown_read_label():
    payload = json.loads(catalog.run_named_query("invent_sql", "{}"))
    assert payload["error"] is True
    assert "get_submission_spine" in payload["known_labels"]
    assert "get_claim_spine" not in payload["known_labels"]
    assert "get_distribution_spine" not in payload["known_labels"]


def test_write_label_rejected_on_query():
    payload = json.loads(catalog.run_named_query("write_quote_issuance", "{}"))
    assert payload["error"] is True
    assert "run_named_write" in payload["message"]


def test_missing_required_param():
    payload = json.loads(catalog.run_named_query("get_submission_spine", "{}"))
    assert payload["missing"] == ["claim_id"]


def test_extra_param_rejected():
    payload = json.loads(
        catalog.run_named_query(
            "get_submission_spine",
            json.dumps({"claim_id": "SUB-9102", "select": "*"}),
        )
    )
    assert payload["extra"] == ["select"]


def test_submission_id_alias(monkeypatch):
    monkeypatch.setattr(
        catalog.uw_tools,
        "get_submission_spine",
        lambda claim_id, database=None: json.dumps({"claim_id": str(claim_id), "spine": {}}),
    )
    payload = json.loads(
        catalog.run_named_query(
            "get_submission_spine",
            json.dumps({"submission_id": "SUB-9102"}),
        )
    )
    assert payload["named_op"] == "get_submission_spine"
    assert payload["claim_id"] == "SUB-9102"


def test_list_named_queries_is_underwriting_only():
    listing = catalog.list_catalog()
    reads = {row["label"] for row in listing["reads"]}
    writes = {row["label"] for row in listing["writes"]}
    assert {
        "get_submission_spine",
        "get_submission_routing_signals",
        "get_senior_uw_referral_context",
        "list_underwriter_open_submissions",
        "get_schema",
    } <= reads
    assert {
        "write_submission_decline",
        "write_quote_issuance",
        "write_data_enrichment_request",
        "write_referral_queue",
        "write_audit_event",
        "promote_audit_run",
    } <= writes
    assert "get_claim_spine" not in reads
    assert "send_client_notice" not in writes


def test_list_requires_party_id():
    payload = json.loads(catalog.run_named_query("list_underwriter_open_submissions", "{}"))
    assert payload["error"] is True
    assert payload["missing"] == ["party_id"]
    reads = {row["label"] for row in catalog.list_catalog()["reads"]}
    assert "get_claim_spine" not in reads


def test_probe_cel_matches_playbook():
    playbook = yaml.safe_load(
        (REPO / "packs" / "underwriting" / "playbook" / "playbook.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert str(playbook["version"]) == uw_writes.PLAYBOOK_VERSION
    for probe_id, expr in uw_writes.PROBE_CEL.items():
        assert playbook["probes"][probe_id]["cel"].strip() == expr
