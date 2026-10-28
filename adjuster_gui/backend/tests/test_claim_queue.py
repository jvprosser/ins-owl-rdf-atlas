"""Adjuster open-claim list (static fallback vs live SQL)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.claim_queue import list_adjuster_open_claims_sql, load_claims_payload


class ClaimQueueTests(unittest.TestCase):
    def test_sql_excludes_closed_and_binds_party(self) -> None:
        sql = list_adjuster_open_claims_sql(4, "car_insurance_claims")
        self.assertIn("party_id = 4", sql)
        self.assertIn("<> 'CLOSED'", sql)
        self.assertIn("ADJUSTER", sql)

    def test_live_rows_drop_closed(self) -> None:
        def fake_query(sql: str):
            self.assertIn("party_id = 4", sql)
            return [
                {"claim_id": 401, "claim_status_code": "OPEN"},
                {"claim_id": 402, "claim_status_code": "IN_LITIGATION"},
                {"claim_id": 404, "claim_status_code": "OPEN"},
            ]

        payload = load_claims_payload(party_id=4, query_rows=fake_query)
        self.assertEqual(payload["claims"], ["401", "402", "404"])
        self.assertNotIn("403", payload["claims"])

    def test_fallback_when_impala_host_unset(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "IMPALA_HOST"}
        with patch.dict(os.environ, env, clear=True):
            payload = load_claims_payload()
        self.assertIn("401", payload["claims"])
        self.assertIn("403", payload["claims"])

    def test_fallback_when_query_fails(self) -> None:
        def boom(sql: str):
            raise RuntimeError("impala down")

        payload = load_claims_payload(party_id=4, query_rows=boom)
        self.assertIn("401", payload["claims"])
        self.assertIn("403", payload["claims"])
