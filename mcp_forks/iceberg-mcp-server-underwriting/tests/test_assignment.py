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
