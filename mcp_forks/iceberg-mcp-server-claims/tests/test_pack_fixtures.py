"""Pack fixture catalog merge (no Impala)."""

from __future__ import annotations

import json
from pathlib import Path

from iceberg_mcp_server_claims.pack_fixtures import merge_pack_catalog

REPO = Path(__file__).resolve().parents[3]
DIST = REPO / "packs" / "retirement_distributions"


def test_merge_distribution_fixtures(monkeypatch):
    monkeypatch.setenv("PACK_ROOT", str(DIST))
    reads: dict = {}
    writes: dict = {}
    pack_id = merge_pack_catalog(reads, writes)
    assert pack_id == "retirement_distributions"
    assert "get_distribution_spine" in reads
    assert "write_audit_event" in writes

    payload = json.loads(reads["get_distribution_spine"]["handler"]({"claim_id": "7002"}))
    assert payload["fixture"] is True
    assert payload["spine"]["distribution_type_code"] == "HARDSHIP"

    write = json.loads(writes["write_audit_event"]["handler"]({"run_id": "demo-7002-exc"}))
    assert write["ok"] is True
    assert write["fixture"] is True


def test_no_pack_root_is_noop(monkeypatch):
    monkeypatch.delenv("PACK_ROOT", raising=False)
    monkeypatch.delenv("INS_CLAIMS_REPO_ROOT", raising=False)
    reads: dict = {}
    writes: dict = {}
    assert merge_pack_catalog(reads, writes) is None
    assert reads == {}
    assert writes == {}
