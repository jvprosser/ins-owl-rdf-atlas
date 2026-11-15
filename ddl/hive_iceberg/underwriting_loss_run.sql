-- =============================================================================
-- Carrier loss run — Cloudera Hive + Apache Iceberg DDL
-- =============================================================================
-- Engine target : CDP Hive / Impala Iceberg v2
-- Database      : underwriting
-- Prerequisite  : underwriting_iceberg.sql already applied
--
-- loss-run-report.json is a Hartford loss run for Oakridge Plaza Holdings,
-- policy 42-UEN-88412. The two terms from 12/01/2024 through 12/01/2026
-- each show 0 claims and 0 incurred, and the aggregate matches.
-- claims_detail is empty, so detail_claim_count is 0.
-- The certification has no authorized signature.
-- Word scores stay on ocr_word. The lowest word on the sample page is
-- "reported" at 0.942.
-- This two-year run does not replace claims_count_36m or total_incurred_36m.
-- =============================================================================

USE underwriting;


CREATE TABLE IF NOT EXISTS underwriting.loss_run_report (
  report_id                     STRING    COMMENT 'PK. One carrier loss run.',
  submission_id                 STRING    COMMENT 'FK -> submissions.submission_id.',
  carrier                       STRING    COMMENT 'Reporting carrier.',
  named_insured                 STRING    COMMENT 'Named insured.',
  valuation_date                STRING    COMMENT 'Valuation date, ISO-8601.',
  report_run_date               STRING    COMMENT 'Report run date, ISO-8601.',
  total_claims_count            INT       COMMENT 'Aggregate claim count.',
  detail_claim_count            INT       COMMENT 'Length of claims_detail.',
  total_paid_indemnity          BIGINT    COMMENT 'Aggregate paid indemnity.',
  total_paid_expense            BIGINT    COMMENT 'Aggregate paid expense.',
  total_outstanding_reserve     BIGINT    COMMENT 'Aggregate outstanding reserve.',
  total_gross_incurred          BIGINT    COMMENT 'Aggregate gross incurred.',
  signature_detected            BOOLEAN   COMMENT 'True when an authorized signature is detected.',
  certification_statement       STRING    COMMENT 'Certification text printed on the report.'
)
COMMENT 'Carrier loss run header and account totals.'
PARTITIONED BY SPEC (
  submission_id
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'LossRunReport',
  'llm.primary_key' = 'report_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one carrier loss run'
);


CREATE TABLE IF NOT EXISTS underwriting.loss_run_policy (
  policy_row_id                 STRING    COMMENT 'PK. One policy term on a loss run.',
  report_id                     STRING    COMMENT 'FK -> loss_run_report.report_id.',
  submission_id                 STRING    COMMENT 'FK -> submissions.submission_id.',
  policy_number                 STRING    COMMENT 'Policy number.',
  policy_term                   STRING    COMMENT 'Term as printed, e.g. 12/01/2024 to 12/01/2025.',
  line_of_business              STRING    COMMENT 'Line of business as printed.',
  total_claims                  INT       COMMENT 'Claims in the term.',
  total_incurred                BIGINT    COMMENT 'Incurred in the term.',
  total_paid                    BIGINT    COMMENT 'Paid in the term.',
  total_reserved                BIGINT    COMMENT 'Reserved in the term.',
  total_recovered               BIGINT    COMMENT 'Recovered in the term.'
)
COMMENT 'Policy-term totals on a carrier loss run.'
PARTITIONED BY SPEC (
  submission_id
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'LossRunPolicy',
  'llm.primary_key' = 'policy_row_id',
  'llm.foreign_keys' = 'report_id->loss_run_report.report_id;submission_id->submissions.submission_id',
  'llm.grain' = 'one policy term on a loss run'
);
