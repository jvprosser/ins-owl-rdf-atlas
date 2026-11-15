"""Underwriter assignment list: current role, open files only."""

from __future__ import annotations

import json

from iceberg_mcp_server_underwriting.tools import sql as uw_sql
from iceberg_mcp_server_underwriting.tools import uw_tools


def test_list_sql_filters_role_and_terminal_status():
    statement = uw_sql.list_underwriter_open_submissions_sql(14, "underwriting")
    assert "role_type_code = 'UNDERWRITER'" in statement
    assert "is_current_assignment = TRUE" in statement
    assert "r.party_id = 14" in statement
    assert "NOT IN ('DECLINED', 'QUOTED')" in statement
    assert "underwriting.submission_party_role" in statement
    assert "underwriting.person" in statement


def test_list_handler_returns_name_and_rows():
    def query_rows(sql):
        assert "party_id = 14" in sql
        return [
            {
                "submission_id": "SUB-9101",
                "line_of_business": "COMMERCIAL_PROPERTY",
                "submission_status_code": "OPEN",
                "first_name": "Riley",
                "last_name": "Cho",
            },
            {
                "submission_id": "SUB-9103",
                "line_of_business": "COMMERCIAL_PROPERTY",
                "submission_status_code": "OPEN",
                "first_name": "Riley",
                "last_name": "Cho",
            },
        ]

    payload = json.loads(
        uw_tools.list_underwriter_open_submissions("14", query_rows=query_rows)
    )
    assert payload["party_id"] == 14
    assert payload["underwriter_name"] == "Riley Cho"
    assert payload["submissions"] == [
        {
            "submission_id": "SUB-9101",
            "line_of_business": "COMMERCIAL_PROPERTY",
            "submission_status_code": "OPEN",
        },
        {
            "submission_id": "SUB-9103",
            "line_of_business": "COMMERCIAL_PROPERTY",
            "submission_status_code": "OPEN",
        },
    ]


def test_snapshot_sql_projects_current_underwriter():
    statement = uw_sql.submission_snapshot_sql("SUB-9107", "underwriting")
    assert "has_underwriter" in statement
    assert "role_type_code = 'UNDERWRITER'" in statement
    assert "is_current_assignment = TRUE" in statement
    assert "'SUB-9107'" in statement
    assert "ocr_document_present" in statement
    assert "min_ocr_confidence" in statement
    assert "low_ocr_spans" in statement
    assert "confidence < 0.8" in statement
    assert "COALESCE(ocr.min_ocr_confidence, 1.0)" in statement
    assert "statement_of_values" in statement
    assert "Equipment Breakdown" in statement
    assert "sov_present" in statement
    assert "sov_min_coinsurance_pct" in statement
    assert "sov_schedule_incomplete" in statement
    assert "iso 4" in statement
    assert "rental_value_worksheet" in statement
    assert "rental_value_tenant" in statement
    assert "rental_needs_review" in statement
    assert "rental_review_detail" in statement
    assert "four_point_inspection" in statement
    assert "four_point_system" in statement
    assert "four_point_needs_review" in statement
    assert "no aluminum" in statement
    assert "no polybutylene" in statement
    assert "loss_run_report" in statement
    assert "loss_run_policy" in statement
    assert "loss_run_needs_review" in statement
    assert "loss run has no authorized signature" in statement
    assert "large_loss_narrative" in statement
    assert "large_loss_invoice_line" in statement
    assert "large_loss_needs_review" in statement
    assert "loss date falls in a loss run period that shows no losses" in statement
    assert "tenant_roster" in statement
    assert "tenant_roster_unit" in statement
    assert "tenant_roster_needs_review" in statement
    assert "no commercial cooking" in statement
