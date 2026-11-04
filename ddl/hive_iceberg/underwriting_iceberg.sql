-- =============================================================================
-- Underwriting submissions — Cloudera Hive + Apache Iceberg DDL
-- =============================================================================
-- Engine target : CDP Hive / Impala Iceberg v2
-- Database      : underwriting
-- Demo cases    : SUB-9100 decline class, SUB-9101 inspection boundary,
--                 SUB-9102 survey then flood referral, SUB-9103 straight-through,
--                 SUB-9104 senior referral, SUB-9105 human review,
--                 SUB-9106 TIV knockout, SUB-9107 unassigned (then bind)
--
-- JSON contract (Studio / MCP): packs/underwriting/fixtures/
-- CREATE TABLE shape: not EXTERNAL; COMMENT before PARTITIONED BY SPEC.
-- =============================================================================

CREATE DATABASE IF NOT EXISTS underwriting;
USE underwriting;


CREATE TABLE IF NOT EXISTS underwriting.submissions (
  submission_id             STRING    COMMENT 'PK. Studio claim_id (SUB-9102).',
  producer_id               STRING    COMMENT 'Producer / broker identifier.',
  applicant_tax_id          STRING    COMMENT 'Applicant tax id (demo values only).',
  line_of_business          STRING    COMMENT 'Primary line, e.g. COMMERCIAL_PROPERTY.',
  class_code                STRING    COMMENT 'Appetite class code.',
  total_insured_value       BIGINT    COMMENT 'Total insured value in whole currency units.',
  submission_timestamp      TIMESTAMP COMMENT 'When the submission was ingested.',
  submission_status_code    STRING    COMMENT 'OPEN | DECLINED | QUOTED | REFERRED.'
)
COMMENT 'Underwriting submission spine (one row per Studio claim_id).'
PARTITIONED BY SPEC (
  submission_status_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'Submission',
  'llm.primary_key' = 'submission_id',
  'llm.grain' = 'one submission'
);


CREATE TABLE IF NOT EXISTS underwriting.mvr_reports (
  mvr_id                    STRING    COMMENT 'PK. Motor vehicle report id.',
  submission_id             STRING    COMMENT 'FK -> submissions.submission_id.',
  violation_count           INT       COMMENT 'Count of violations on the report.',
  major_violation           BOOLEAN   COMMENT 'True when a major violation is present.',
  report_status_code        STRING    COMMENT 'ON_FILE | REQUESTED.'
)
COMMENT 'Motor vehicle report rows for a submission.'
PARTITIONED BY SPEC (
  report_status_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'MvrReport',
  'llm.primary_key' = 'mvr_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one MVR report'
);


CREATE TABLE IF NOT EXISTS underwriting.property_risk_scores (
  risk_score_id             STRING    COMMENT 'PK. Property risk score id.',
  submission_id             STRING    COMMENT 'FK -> submissions.submission_id.',
  is_in_flood_plain         BOOLEAN   COMMENT 'True when the location is in a flood plain.',
  inspection_completed      BOOLEAN   COMMENT 'True when the property inspection is on file.',
  flood_zone                STRING    COMMENT 'Flood zone code, or NONE.'
)
COMMENT 'Property flood and inspection flags for CEL routing.'
PARTITIONED BY SPEC (
  flood_zone
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'PropertyRiskScore',
  'llm.primary_key' = 'risk_score_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one property risk score'
);


CREATE TABLE IF NOT EXISTS underwriting.loss_history_summary (
  loss_summary_id           STRING    COMMENT 'PK. Loss history summary id.',
  submission_id             STRING    COMMENT 'FK -> submissions.submission_id.',
  prior_claims_count        INT       COMMENT 'Prior claims counted for referral and bind.',
  has_open_loss_past_36m    BOOLEAN   COMMENT 'True when an open loss exists in the past 36 months.',
  financial_stability_tier  STRING    COMMENT 'A | B | C. Rating table key.'
)
COMMENT 'Loss history and financial stability tier for a submission.'
PARTITIONED BY SPEC (
  financial_stability_tier
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'LossHistorySummary',
  'llm.primary_key' = 'loss_summary_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one loss history summary'
);


CREATE TABLE IF NOT EXISTS underwriting.appetite_class_codes (
  class_code                STRING    COMMENT 'PK. Class code (4812 and 5921 are prohibited).',
  appetite_status_code      STRING    COMMENT 'PROHIBITED | ACCEPT.'
)
COMMENT 'Governed appetite list. Playbook CEL is the runtime knockout.'
PARTITIONED BY SPEC (
  appetite_status_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'AppetiteClassCode',
  'llm.primary_key' = 'class_code',
  'llm.grain' = 'one class code'
);


CREATE TABLE IF NOT EXISTS underwriting.submission_decline (
  decline_id                STRING    COMMENT 'PK. Decline row id.',
  submission_id             STRING    COMMENT 'FK -> submissions.submission_id.',
  reason_code               STRING    COMMENT 'Allow-listed reason. OUT_OF_APPETITE.',
  run_id                    STRING    COMMENT 'Agent run id.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Playbook decline write (write_submission_decline).'
PARTITIONED BY SPEC (
  reason_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'SubmissionDecline',
  'llm.primary_key' = 'decline_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one decline'
);


CREATE TABLE IF NOT EXISTS underwriting.quote_issuance (
  quote_id                  STRING    COMMENT 'PK. Indicative quote id.',
  submission_id             STRING    COMMENT 'FK -> submissions.submission_id.',
  rating_tier               STRING    COMMENT 'A | B | C | STANDARD. Computed by the catalog.',
  premium_cents             BIGINT    COMMENT 'Premium in cents. Computed by the catalog.',
  run_id                    STRING    COMMENT 'Agent run id.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Indicative quote write (write_quote_issuance). Premium is not an agent argument.'
PARTITIONED BY SPEC (
  rating_tier
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'QuoteIssuance',
  'llm.primary_key' = 'quote_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one indicative quote'
);


CREATE TABLE IF NOT EXISTS underwriting.data_enrichment_request (
  enrichment_id             STRING    COMMENT 'PK. Third-party data request id.',
  submission_id             STRING    COMMENT 'FK -> submissions.submission_id.',
  provider_type             STRING    COMMENT 'Allow-listed provider. INSPECTION.',
  run_id                    STRING    COMMENT 'Agent run id.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Inspection / data order (write_data_enrichment_request).'
PARTITIONED BY SPEC (
  provider_type
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'DataEnrichmentRequest',
  'llm.primary_key' = 'enrichment_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one enrichment request'
);


CREATE TABLE IF NOT EXISTS underwriting.referral_queue (
  referral_id               STRING    COMMENT 'PK. Referral row id.',
  submission_id             STRING    COMMENT 'FK -> submissions.submission_id.',
  queue_code                STRING    COMMENT 'SENIOR_UW.',
  run_id                    STRING    COMMENT 'Agent run id.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Senior underwriter queue (write_referral_queue).'
PARTITIONED BY SPEC (
  queue_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'ReferralQueue',
  'llm.primary_key' = 'referral_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one referral'
);


CREATE TABLE IF NOT EXISTS underwriting.person (
  party_id                  BIGINT    COMMENT 'PK. Demo underwriter party id (14 = Riley Cho).',
  first_name                STRING    COMMENT 'Given name.',
  last_name                 STRING    COMMENT 'Family name.'
)
COMMENT 'Person rows for underwriter assignment. Demo owner is party 14.'
PARTITIONED BY SPEC (
  party_id
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'Person',
  'llm.primary_key' = 'party_id',
  'llm.grain' = 'one person'
);


CREATE TABLE IF NOT EXISTS underwriting.submission_party_role (
  submission_party_role_id  STRING    COMMENT 'PK. Surrogate for a party playing a role on a submission.',
  submission_id             STRING    COMMENT 'FK -> submissions.submission_id.',
  party_id                  BIGINT    COMMENT 'FK -> person.party_id.',
  role_type_code            STRING    COMMENT 'UNDERWRITER.',
  assigned_at               TIMESTAMP COMMENT 'When the role assignment started.',
  unassigned_at             TIMESTAMP COMMENT 'When the role assignment ended; NULL if current.',
  is_current_assignment     BOOLEAN   COMMENT 'True for the active assignment of this role type.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Current and historical underwriter assignment. Authoritative owner of a submission.'
PARTITIONED BY SPEC (
  role_type_code,
  is_current_assignment
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'SubmissionPartyRole',
  'llm.primary_key' = 'submission_party_role_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id;party_id->person.party_id',
  'llm.grain' = 'one role assignment on a submission'
);


CREATE TABLE IF NOT EXISTS underwriting.agent_run_audit (
  run_id                    STRING    COMMENT 'PK part. Agent Studio / workflow run id.',
  event_ts                  TIMESTAMP COMMENT 'Event timestamp UTC.',
  claim_id                  STRING    COMMENT 'Studio claim_id / submission id.',
  event_type                STRING    COMMENT 'Playbook next_step or audit event type.',
  next_step                 STRING    COMMENT 'Playbook step id.',
  agent_role                STRING    COMMENT 'Worker role id.',
  lane                      STRING    COMMENT 'Routing lane.',
  needs_llm                 BOOLEAN   COMMENT 'Whether LLM tools were allowed.',
  terminal                  BOOLEAN   COMMENT 'Whether router marked terminal.',
  reason_probe_ids          STRING    COMMENT 'JSON array of probe ids.',
  payload_json              STRING    COMMENT 'playbook_version, cel, and lake snapshot.'
)
COMMENT 'Append-only underwriting decision audit (Impala table-append).'
PARTITIONED BY SPEC (
  run_id
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting_agent',
  'llm.ontology_class' = 'AgentRunAuditEvent'
);


CREATE TABLE IF NOT EXISTS underwriting.agent_run_evidence (
  run_id                    STRING    COMMENT 'FK/logical -> agent_run_audit.run_id.',
  evidence_ts               TIMESTAMP COMMENT 'Evidence timestamp UTC.',
  claim_id                  STRING    COMMENT 'Studio claim_id / submission id.',
  evidence_type             STRING    COMMENT 'VALIDATION|WORKER_OUTPUT|other.',
  probe_id                  STRING    COMMENT 'Optional probe id.',
  content_format            STRING    COMMENT 'json|text.',
  content_text              STRING    COMMENT 'Evidence payload.',
  content_uri               STRING    COMMENT 'Optional external URI.'
)
COMMENT 'Evidence artifacts for an underwriting agent run.'
PARTITIONED BY SPEC (
  run_id
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting_agent',
  'llm.ontology_class' = 'AgentRunEvidence'
);
