-- Additive PD intake / SMS tables for an already-loaded car_insurance_claims lake.
-- Fresh full seed: tables are in car_insurance_claims_iceberg.sql.

USE car_insurance_claims;

CREATE TABLE IF NOT EXISTS car_insurance_claims.claim_police_intake (
  claim_id                  BIGINT    COMMENT 'FK -> claim.claim_id.',
  incident_report_number    STRING    COMMENT 'Agency incident / exchange-slip number from the policyholder.',
  source_code               STRING    COMMENT 'POLICYHOLDER_APP.',
  collected_at              TIMESTAMP COMMENT 'When the policyholder submitted the number.',
  run_id                    STRING    COMMENT 'Optional agent run that prompted collection.'
)
COMMENT 'Policyholder-supplied police incident report number before a police_report row exists.'
PARTITIONED BY SPEC (
  YEAR(collected_at)
)
STORED BY ICEBERG
TBLPROPERTIES ('format-version' = '2');

CREATE TABLE IF NOT EXISTS car_insurance_claims.claim_outbound_message (
  message_id                BIGINT    COMMENT 'PK. Surrogate outbound message id.',
  claim_id                  BIGINT    COMMENT 'FK -> claim.claim_id.',
  channel_code              STRING    COMMENT 'SMS.',
  to_phone                  STRING    COMMENT 'PII. Destination phone (E.164 when possible).',
  body_text                 STRING    COMMENT 'Curated message body. No carrier send.',
  purpose_code              STRING    COMMENT 'COLLECT_INCIDENT_REPORT_NUMBER.',
  run_id                    STRING    COMMENT 'Agent run that created the message.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Demo evidence for outbound SMS (no carrier).'
PARTITIONED BY SPEC (
  purpose_code,
  YEAR(created_at)
)
STORED BY ICEBERG
TBLPROPERTIES ('format-version' = '2');

-- Existing pd_task tables: add the incident-number column (no-op if already present).
ALTER TABLE car_insurance_claims.pd_task
ADD COLUMNS (
  incident_report_number STRING COMMENT 'Agency incident number for REQUEST_POLICE_REPORT.'
);

INVALIDATE METADATA car_insurance_claims.claim_police_intake;
INVALIDATE METADATA car_insurance_claims.claim_outbound_message;
INVALIDATE METADATA car_insurance_claims.pd_task;
