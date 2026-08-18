-- =============================================================================
-- Retirement distributions — Cloudera Hive + Apache Iceberg DDL
-- =============================================================================
-- Engine target : CDP Hive / Impala Iceberg v2
-- Database      : retirement_distributions
-- Demo cases    : 7001 termination, 7002 hardship substantiation, 7003 RMD
--
-- JSON contract (Studio / MCP): packs/retirement_distributions/fixtures/
-- CREATE TABLE shape: not EXTERNAL; COMMENT before PARTITIONED BY SPEC.
-- =============================================================================

CREATE DATABASE IF NOT EXISTS retirement_distributions;
USE retirement_distributions;


CREATE TABLE IF NOT EXISTS retirement_distributions.distribution_request (
  distribution_request_id   BIGINT    COMMENT 'PK. Studio claim_id / case_id (7001, 7002, 7003).',
  request_status_code       STRING    COMMENT 'OPEN | CLOSED.',
  distribution_type_code    STRING    COMMENT 'TERMINATION | HARDSHIP | RMD.',
  plan_id                   STRING    COMMENT 'Plan identifier (e.g. 401k-alpha).',
  participant_id            STRING    COMMENT 'Participant business key.',
  hold_or_aml_flag          BOOLEAN   COMMENT 'True when request is on hold / AML review.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Retirement distribution request spine (one row per Studio claim_id).'
PARTITIONED BY SPEC (
  request_status_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'retirement_distributions',
  'llm.ontology_class' = 'DistributionRequest',
  'llm.primary_key' = 'distribution_request_id',
  'llm.grain' = 'one distribution request'
);


CREATE TABLE IF NOT EXISTS retirement_distributions.distribution_exception (
  exception_id              STRING    COMMENT 'PK. Exception business key (e.g. EX-7002).',
  distribution_request_id   BIGINT    COMMENT 'FK -> distribution_request.distribution_request_id.',
  reason_code               STRING    COMMENT 'HARDSHIP_SUBSTANTIATION_MISSING | HOLD_AML | other.',
  queue                     STRING    COMMENT 'Exception queue name (e.g. ExceptionQueue).',
  required_docs             STRING    COMMENT 'JSON array of required document codes.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Open exception on a distribution request (Exception Queue view).'
PARTITIONED BY SPEC (
  reason_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'retirement_distributions',
  'llm.ontology_class' = 'DistributionException',
  'llm.primary_key' = 'exception_id',
  'llm.foreign_keys' = 'distribution_request_id->distribution_request.distribution_request_id',
  'llm.grain' = 'one exception on a request'
);


CREATE TABLE IF NOT EXISTS retirement_distributions.distribution_rmd (
  rmd_id                    BIGINT    COMMENT 'PK. Surrogate RMD assessment id.',
  distribution_request_id   BIGINT    COMMENT 'FK -> distribution_request.distribution_request_id.',
  tax_year                  INT       COMMENT 'RMD tax year.',
  required_amount           DECIMAL(18,2) COMMENT 'Required minimum distribution amount.',
  paid_amount               DECIMAL(18,2) COMMENT 'Amount already paid for the tax year.',
  shortfall_amount          DECIMAL(18,2) COMMENT 'required_amount - paid_amount.',
  deadline                  DATE      COMMENT 'RMD deadline date.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'RMD required vs paid amounts for a distribution request (RMD Ops view).'
PARTITIONED BY SPEC (
  tax_year
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'retirement_distributions',
  'llm.ontology_class' = 'DistributionRmd',
  'llm.primary_key' = 'rmd_id',
  'llm.foreign_keys' = 'distribution_request_id->distribution_request.distribution_request_id',
  'llm.grain' = 'one RMD assessment on a request'
);


CREATE TABLE IF NOT EXISTS retirement_distributions.agent_run_audit (
  run_id                    STRING    COMMENT 'PK part. Agent Studio / workflow run id.',
  event_ts                  TIMESTAMP COMMENT 'Event timestamp UTC.',
  claim_id                  STRING    COMMENT 'Studio claim_id / case_id as string.',
  event_type                STRING    COMMENT 'ROUTE_DECISION|WORKER_START|WORKER_END|ERROR|STOP.',
  next_step                 STRING    COMMENT 'Playbook step id.',
  agent_role                STRING    COMMENT 'Worker role id.',
  lane                      STRING    COMMENT 'Routing lane.',
  needs_llm                 BOOLEAN   COMMENT 'Whether LLM tools were allowed.',
  terminal                  BOOLEAN   COMMENT 'Whether router marked terminal.',
  reason_probe_ids          STRING    COMMENT 'JSON array of probe ids.',
  payload_json              STRING    COMMENT 'Full decision / event JSON.'
)
COMMENT 'Append-only agent routing/worker audit events (Impala table-append).'
PARTITIONED BY SPEC (
  run_id
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'retirement_distributions_agent',
  'llm.ontology_class' = 'AgentRunAuditEvent'
);


CREATE TABLE IF NOT EXISTS retirement_distributions.agent_run_evidence (
  run_id                    STRING    COMMENT 'FK/logical -> agent_run_audit.run_id.',
  evidence_ts               TIMESTAMP COMMENT 'Evidence timestamp UTC.',
  claim_id                  STRING    COMMENT 'Studio claim_id / case_id as string.',
  evidence_type             STRING    COMMENT 'VALIDATION|WORKER_OUTPUT|other.',
  probe_id                  STRING    COMMENT 'Optional probe id.',
  content_format            STRING    COMMENT 'json|text.',
  content_text              STRING    COMMENT 'Evidence payload.',
  content_uri               STRING    COMMENT 'Optional external URI.'
)
COMMENT 'Evidence artifacts for an agent run. Keep PII out of payloads.'
PARTITIONED BY SPEC (
  run_id
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'retirement_distributions_agent',
  'llm.ontology_class' = 'AgentRunEvidence'
);
