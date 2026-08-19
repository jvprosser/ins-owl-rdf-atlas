"""Facade for iceberg-mcp-server-claims (+ claims fork P0 tools when available)."""

from __future__ import annotations

import json
from typing import Any

from . import iceberg_sql as sql
from .base import McpToolCaller

# Studio registration name for the Impala claims fork.
SERVER = "iceberg-mcp-server-claims"
AUDIT_TABLES = ("agent_run_audit", "agent_run_evidence")


class IcebergFacade(McpToolCaller):
    """Iceberg / Hive MCP access for claim facts and WAP audit branches."""

    # --- upstream tools ---

    def execute_query(self, query: str) -> Any:
        return self.call(SERVER, "execute_query", query=query)

    def get_schema(self, database: str | None = None) -> Any:
        kwargs = {} if database is None else {"database": database}
        return self.call(SERVER, "get_schema", **kwargs)

    def list_databases(self) -> Any:
        return self.call(SERVER, "list_databases")

    def create_iceberg_branch(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "create_iceberg_branch", **kwargs)

    def query_iceberg_branch(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "query_iceberg_branch", **kwargs)

    def execute_iceberg_branch_dml(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "execute_iceberg_branch_dml", **kwargs)

    def fast_forward_iceberg_branch(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "fast_forward_iceberg_branch", **kwargs)

    def drop_iceberg_branch(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "drop_iceberg_branch", **kwargs)

    def list_iceberg_refs(self, database: str, table: str) -> Any:
        return self.call(SERVER, "list_iceberg_refs", database=database, table=table)

    # --- claims fork P0 with SQL/branch composition fallbacks ---

    def get_claim_spine(self, claim_id: int | str, database: str = "car_insurance_claims") -> Any:
        try:
            return self.call(
                SERVER,
                "get_claim_spine",
                claim_id=str(claim_id),
                database=database,
            )
        except Exception as exc:
            if not _is_missing_tool(exc, "get_claim_spine"):
                raise
            return self._get_claim_spine_via_sql(claim_id, database=database)

    def get_claim_routing_signals(
        self, claim_id: int | str, database: str = "car_insurance_claims"
    ) -> Any:
        try:
            return self.call(
                SERVER,
                "get_claim_routing_signals",
                claim_id=str(claim_id),
                database=database,
            )
        except Exception as exc:
            if not _is_missing_tool(exc, "get_claim_routing_signals"):
                raise
            return self._get_claim_routing_signals_via_sql(claim_id, database=database)

    def begin_agent_audit_run(
        self, run_id: str, database: str = "car_insurance_claims", source_branch: str | None = None
    ) -> Any:
        try:
            kwargs: dict[str, Any] = {"run_id": run_id, "database": database}
            if source_branch is not None:
                kwargs["source_branch"] = source_branch
            return self.call(SERVER, "begin_agent_audit_run", **kwargs)
        except Exception as exc:
            if not _is_missing_tool(exc, "begin_agent_audit_run"):
                raise
            return self._begin_agent_audit_run_via_branches(
                run_id, database=database, source_branch=source_branch
            )

    def append_agent_audit_event(self, run_id: str, event_json: str | dict[str, Any]) -> Any:
        try:
            return self.call(SERVER, "append_agent_audit_event", run_id=run_id, event_json=event_json)
        except Exception as exc:
            if not _is_missing_tool(exc, "append_agent_audit_event"):
                raise
            return self._append_audit_event_via_dml(run_id, event_json)

    def append_agent_audit_evidence(self, run_id: str, evidence_json: str | dict[str, Any]) -> Any:
        try:
            return self.call(
                SERVER, "append_agent_audit_evidence", run_id=run_id, evidence_json=evidence_json
            )
        except Exception as exc:
            if not _is_missing_tool(exc, "append_agent_audit_evidence"):
                raise
            return self._append_audit_evidence_via_dml(run_id, evidence_json)

    def promote_agent_audit_run(self, run_id: str) -> Any:
        try:
            return self.call(SERVER, "promote_agent_audit_run", run_id=run_id)
        except Exception as exc:
            if not _is_missing_tool(exc, "promote_agent_audit_run"):
                raise
            return self._promote_agent_audit_run_via_branches(run_id)

    def abandon_agent_audit_run(self, run_id: str) -> Any:
        try:
            return self.call(SERVER, "abandon_agent_audit_run", run_id=run_id)
        except Exception as exc:
            if not _is_missing_tool(exc, "abandon_agent_audit_run"):
                raise
            return self._abandon_agent_audit_run_via_branches(run_id)

    # --- private SQL / branch composition ---

    def _get_claim_spine_via_sql(
        self, claim_id: int | str, *, database: str
    ) -> dict[str, Any]:
        row = sql.first_row(self.execute_query(sql.claim_spine_sql(claim_id, database)))
        if row is None:
            raise KeyError(f"Claim {claim_id} not found in {database}.claim")
        roles_raw = sql.parse_query_result(
            self.execute_query(sql.claim_roles_sql(claim_id, database))
        )
        spine = {
            "claim_id": row.get("claim_id"),
            "claim_number": row.get("claim_number"),
            "claim_status_code": row.get("claim_status_code"),
            "litigation_indicator": sql.coerce_bool(row.get("litigation_indicator")),
            "subrogation_indicator": sql.coerce_bool(row.get("subrogation_indicator")),
            "fraudulent_claim_indicator": sql.coerce_bool(row.get("fraudulent_claim_indicator")),
            "total_loss_indicator": sql.coerce_bool(row.get("total_loss_indicator")),
            "loss_event_id": row.get("loss_event_id"),
            "loss_cause_code": row.get("loss_cause_code"),
            "policy_id": row.get("policy_id"),
            "policy_number": row.get("policy_number"),
            "insurable_object_id": row.get("insurable_object_id"),
            "vin": row.get("vin"),
            "policy_covers_vehicle": sql.coerce_bool(row.get("policy_covers_vehicle")),
            "policy_coverage_id": row.get("policy_coverage_id"),
            "coverage_type_code": row.get("coverage_type_code"),
            "claim_lifecycle_id": row.get("claim_lifecycle_id"),
            "roles": [
                {
                    "claim_party_role_id": r.get("claim_party_role_id"),
                    "party_id": r.get("party_id"),
                    "role_type_code": r.get("role_type_code"),
                }
                for r in roles_raw
            ],
            "_source": "execute_query_fallback",
        }
        return spine

    def _get_claim_routing_signals_via_sql(
        self, claim_id: int | str, *, database: str
    ) -> dict[str, Any]:
        row = sql.first_row(self.execute_query(sql.claim_routing_signals_sql(claim_id, database)))
        if row is None:
            row = {}
        injury_ids = [
            r.get("claim_injury_id")
            for r in sql.parse_query_result(
                self.execute_query(sql.claim_injury_ids_sql(claim_id, database))
            )
            if r.get("claim_injury_id") is not None
        ]
        offers = sql.parse_query_result(self.execute_query(sql.claim_offers_sql(claim_id, database)))
        payment_ids = [
            r.get("claim_payment_id")
            for r in sql.parse_query_result(
                self.execute_query(sql.claim_payment_ids_sql(claim_id, database))
            )
            if r.get("claim_payment_id") is not None
        ]
        recovery_ids = [
            r.get("claim_recovery_id")
            for r in sql.parse_query_result(
                self.execute_query(sql.claim_recovery_ids_sql(claim_id, database))
            )
            if r.get("claim_recovery_id") is not None
        ]
        return {
            "has_subrogation_case": bool(sql.coerce_bool(row.get("has_subrogation_case"))),
            "subrogation_case_id": row.get("subrogation_case_id"),
            "subrogation_status_code": row.get("subrogation_status_code"),
            "has_litigation_case": bool(sql.coerce_bool(row.get("has_litigation_case"))),
            "litigation_case_id": row.get("litigation_case_id"),
            "docket_number": row.get("docket_number"),
            "defense_counsel_party_id": row.get("defense_counsel_party_id"),
            "plaintiff_counsel_party_id": row.get("plaintiff_counsel_party_id"),
            "served_date": row.get("served_date"),
            "filed_date": row.get("filed_date"),
            "closed_date": row.get("closed_date"),
            "litigation_status_code": row.get("litigation_status_code"),
            "missing_docket_or_counsel": bool(
                sql.coerce_bool(row.get("missing_docket_or_counsel"))
            ),
            "discovery_aging": bool(sql.coerce_bool(row.get("discovery_aging"))),
            "has_injury": bool(sql.coerce_bool(row.get("has_injury"))),
            "injury_ids": injury_ids,
            "has_police_report": bool(sql.coerce_bool(row.get("has_police_report"))),
            "police_report_id": row.get("police_report_id"),
            "has_fault_determination": bool(sql.coerce_bool(row.get("has_fault_determination"))),
            "fault_determination_id": row.get("fault_determination_id"),
            "has_offer": bool(sql.coerce_bool(row.get("has_offer"))),
            "has_unresolved_offer": bool(sql.coerce_bool(row.get("has_unresolved_offer"))),
            "has_accepted_offer": bool(sql.coerce_bool(row.get("has_accepted_offer"))),
            "offers": [
                {
                    "claim_offer_id": o.get("claim_offer_id"),
                    "offer_status_code": o.get("offer_status_code"),
                }
                for o in offers
            ],
            "has_loss_payment": bool(sql.coerce_bool(row.get("has_loss_payment"))),
            "payment_ids": payment_ids,
            "has_recovery": bool(sql.coerce_bool(row.get("has_recovery"))),
            "recovery_ids": recovery_ids,
            "has_current_reserve": bool(sql.coerce_bool(row.get("has_current_reserve"))),
            "has_siu_suspected": bool(sql.coerce_bool(row.get("has_siu_suspected"))),
            "fraud_assessment_id": row.get("fraud_assessment_id"),
            "fraud_outcome_code": row.get("fraud_outcome_code"),
            "has_document": bool(sql.coerce_bool(row.get("has_document"))),
            "insured_operator_cited": bool(
                sql.coerce_bool(row.get("insured_operator_cited"))
            ),
            "unlawful_operation_exclusion": bool(
                sql.coerce_bool(row.get("unlawful_operation_exclusion"))
            ),
            "excluded_operator_exclusion": bool(
                sql.coerce_bool(row.get("excluded_operator_exclusion"))
            ),
            "policy_not_in_force_on_loss": bool(
                sql.coerce_bool(row.get("policy_not_in_force_on_loss"))
            ),
            "_source": "execute_query_fallback",
        }

    def _begin_agent_audit_run_via_branches(
        self,
        run_id: str,
        *,
        database: str,
        source_branch: str | None,
    ) -> dict[str, Any]:
        branch = sql.audit_branch_name(run_id)
        # source_branch is retained for fork API parity; upstream create uses current head.
        _ = source_branch
        created = []
        for table in AUDIT_TABLES:
            result = self.create_iceberg_branch(
                database=database,
                table=table,
                branch_name=branch,
            )
            created.append({"table": table, "result": result})
        return {
            "run_id": run_id,
            "database": database,
            "branch_name": branch,
            "tables": list(AUDIT_TABLES),
            "created": created,
            "_source": "branch_fallback",
        }

    def _append_audit_event_via_dml(self, run_id: str, event_json: str | dict[str, Any]) -> Any:
        event = _as_dict(event_json)
        event.setdefault("run_id", run_id)
        database = event.pop("database", None) or "car_insurance_claims"
        branch = sql.audit_branch_name(run_id)
        statement = sql.insert_audit_event_sql(database, branch, event)
        return self.execute_iceberg_branch_dml(
            database=database,
            table="agent_run_audit",
            branch_name=branch,
            statement=statement,
        )

    def _append_audit_evidence_via_dml(
        self, run_id: str, evidence_json: str | dict[str, Any]
    ) -> Any:
        evidence = _as_dict(evidence_json)
        evidence.setdefault("run_id", run_id)
        database = evidence.pop("database", None) or "car_insurance_claims"
        branch = sql.audit_branch_name(run_id)
        statement = sql.insert_audit_evidence_sql(database, branch, evidence)
        return self.execute_iceberg_branch_dml(
            database=database,
            table="agent_run_evidence",
            branch_name=branch,
            statement=statement,
        )

    def _promote_agent_audit_run_via_branches(
        self, run_id: str, database: str = "car_insurance_claims"
    ) -> dict[str, Any]:
        branch = sql.audit_branch_name(run_id)
        results = []
        for table in AUDIT_TABLES:
            # Advance main to the audit branch tip.
            result = self.fast_forward_iceberg_branch(
                database=database,
                table=table,
                source_branch="main",
                target_branch=branch,
            )
            results.append({"table": table, "result": result})
        return {
            "run_id": run_id,
            "branch_name": branch,
            "promoted": results,
            "_source": "branch_fallback",
        }

    def _abandon_agent_audit_run_via_branches(
        self, run_id: str, database: str = "car_insurance_claims"
    ) -> dict[str, Any]:
        branch = sql.audit_branch_name(run_id)
        results = []
        for table in AUDIT_TABLES:
            result = self.drop_iceberg_branch(
                database=database,
                table=table,
                branch_name=branch,
                if_exists=True,
            )
            results.append({"table": table, "result": result})
        return {
            "run_id": run_id,
            "branch_name": branch,
            "abandoned": results,
            "_source": "branch_fallback",
        }


def _as_dict(payload: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, dict):
        return dict(payload)
    return json.loads(payload)


def _is_missing_tool(exc: BaseException, tool_name: str) -> bool:
    """True when the fork tool is absent / unbound; false for real MCP/SQL failures."""
    if isinstance(exc, NotImplementedError):
        # Caller unbound — do not pretend SQL can run either.
        return False
    text = str(exc).lower()
    tool = tool_name.lower()
    missing_signals = (
        "unknown tool",
        "no tool",
        "invalid tool",
        "tool not",
        "unavailable",
        "does not exist",
    )
    if any(s in text for s in missing_signals) and tool in text:
        return True
    if f"tool '{tool}'" in text or f'tool "{tool}"' in text:
        return True
    if isinstance(exc, (AttributeError, KeyError, LookupError)):
        return tool in text
    return False
