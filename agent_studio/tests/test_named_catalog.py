"""Named catalog tool: allow-list, SQL files, handler dispatch."""

from __future__ import annotations

from pathlib import Path

from ins_claims_agent.named_catalog import HANDLER_NAMES, execute, load_catalog, render_sql

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog" / "catalog.yaml"


def test_claims_catalog_labels_are_handler_or_sql():
    catalog = load_catalog(CATALOG)
    assert catalog["database"] == "car_insurance_claims"
    labels = []
    for section in ("reads", "writes"):
        for label, spec in catalog[section].items():
            labels.append(label)
            assert ("handler" in spec) ^ ("sql" in spec)
            if "handler" in spec:
                assert spec["handler"] in HANDLER_NAMES
            else:
                assert (ROOT / "catalog" / spec["sql"]).is_file()
    assert "get_fnol_spine" in labels
    assert "convert_fnol_to_claim" in labels
    assert "get_distribution_spine" not in labels


def test_unknown_label_and_wrong_op_fail_closed():
    missing = execute(op="query", label="deny_claim", catalog_file=CATALOG, params={"claim_id": "401"})
    assert missing["ok"] is False
    assert "write" in missing["error"]
    unknown = execute(op="query", label="get_distribution_spine", catalog_file=CATALOG)
    assert unknown["ok"] is False
    assert unknown["error"] == "unknown label"


def test_fnol_spine_sql_shapes_the_collision_row():
    seen: list[str] = []

    def query_rows(sql: str):
        seen.append(sql)
        return [
            {
                "fnol_id": 88,
                "deductible_amount": 1000,
                "coverage_type_code": "COLLISION",
                "vehicle_listed_on_policy": "true",
                "peril_covered": 1,
            }
        ]

    result = execute(
        op="query",
        label="get_fnol_spine",
        params={"fnol_id": "FNOL-2026-00088"},
        catalog_file=CATALOG,
        query_rows=query_rows,
    )
    assert result["named_op"] == "get_fnol_spine"
    assert result["fnol_id"] == 88
    assert result["spine"]["deductible_amount"] == 1000
    assert result["spine"]["vehicle_listed_on_policy"] is True
    assert result["spine"]["peril_covered"] is True
    assert "pc.coverage_id = cov.coverage_id" in seen[0]
    assert "fnol_id = 88" in seen[0]
    assert "car_insurance_claims.fnol" in seen[0]


def test_sql_read_rejects_a_write_statement(tmp_path: Path):
    catalog = tmp_path / "catalog"
    sql_dir = catalog / "sql"
    sql_dir.mkdir(parents=True)
    (catalog / "catalog.yaml").write_text(
        "version: 1\ndatabase: car_insurance_claims\nreads:\n"
        "  bad:\n    required: [claim_id]\n    sql: sql/bad.sql\nwrites: {}\n",
        encoding="utf-8",
    )
    (sql_dir / "bad.sql").write_text(
        "DELETE FROM ${database}.claim WHERE claim_id = ${claim_id}\n",
        encoding="utf-8",
    )
    result = execute(
        op="query",
        label="bad",
        params={"claim_id": "401"},
        catalog_file=catalog / "catalog.yaml",
        query_rows=lambda sql: [],
    )
    assert result["ok"] is False
    assert "SELECT" in result["error"]


def test_handler_dispatch_does_not_call_other_labels():
    called: list[str] = []

    def get_claim_spine(params: dict) -> str:
        called.append(params["claim_id"])
        return '{"claim_id": 401, "spine": {}}'

    result = execute(
        op="query",
        label="get_claim_spine",
        params={"claim_id": "401"},
        catalog_file=CATALOG,
        handlers={"get_claim_spine": get_claim_spine},
    )
    assert called == ["401"]
    assert result["named_op"] == "get_claim_spine"
    assert result["spine"] == {}


def test_render_sql_rejects_a_second_statement():
    try:
        render_sql("SELECT 1; SELECT 2", {"database": "car_insurance_claims"})
    except ValueError as exc:
        assert "one statement" in str(exc)
    else:
        raise AssertionError("expected ValueError")
