-- =============================================================================
-- Agent run audit tables (WAP branches via Iceberg MCP)
-- Prerequisite for begin_agent_audit_run / append_* / promote_* helpers.
-- =============================================================================

USE car_insurance_claims;

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.agent_run_audit (
  run_id              STRING  COMMENT 'PK part. Agent Studio / workflow run id',
  event_ts            TIMESTAMP COMMENT 'Event timestamp UTC',
  claim_id            STRING  COMMENT 'Claim surrogate id as string',
  event_type          STRING  COMMENT 'ROUTE_DECISION|WORKER_START|WORKER_END|ERROR|STOP',
  next_step           STRING  COMMENT 'Playbook step id',
  agent_role          STRING  COMMENT 'Worker role id',
  lane                STRING  COMMENT 'Routing lane',
  needs_llm           BOOLEAN COMMENT 'Whether LLM tools were allowed',
  terminal            BOOLEAN COMMENT 'Whether router marked terminal',
  reason_probe_ids    STRING  COMMENT 'JSON array of probe ids',
  payload_json        STRING  COMMENT 'Full decision / event JSON'
)
COMMENT 'Append-only agent routing/worker audit events. Writes should target Iceberg branches branch_agent_run_<run_id>.'
PARTITIONED BY SPEC (
  run_id
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'write.format.default' = 'parquet',
  'llm.domain' = 'personal_auto_pc_claims_agent',
  'llm.ontology_class' = 'AgentRunAuditEvent',
  'llm.notes' = 'WAP: agents write on audit branches; promote after accepted run.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.agent_run_evidence (
  run_id              STRING  COMMENT 'FK/logical -> agent_run_audit.run_id',
  evidence_ts         TIMESTAMP COMMENT 'Evidence timestamp UTC',
  claim_id            STRING,
  evidence_type       STRING  COMMENT 'SPARQL_TRACE|VALIDATION|GRAPH_TTL|WORKER_OUTPUT',
  probe_id            STRING  COMMENT 'Optional probe id',
  content_format      STRING  COMMENT 'json|turtle|text',
  content_text        STRING  COMMENT 'Evidence payload',
  content_uri         STRING  COMMENT 'Optional external URI if payload stored elsewhere'
)
COMMENT 'Evidence artifacts for an agent run (probe traces, validation, graph excerpts). Branch-write via Iceberg MCP.'
PARTITIONED BY SPEC (
  run_id
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'write.format.default' = 'parquet',
  'llm.domain' = 'personal_auto_pc_claims_agent',
  'llm.ontology_class' = 'AgentRunEvidence',
  'llm.notes' = 'Keep PII out of evidence payloads unless required and masked via Ranger.'
);
