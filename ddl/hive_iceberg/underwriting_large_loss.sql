-- =============================================================================
-- Large loss narrative — Cloudera Hive + Apache Iceberg DDL
-- =============================================================================
-- Engine target : CDP Hive / Impala Iceberg v2
-- Database      : underwriting
-- Prerequisite  : underwriting_iceberg.sql already applied
--
-- large-loss-narrative-scanned.json is a signed narrative for Oakridge Plaza.
-- Loss date 2024-02-18, amount 14250. The Apex invoice lines sum to 14250
-- and the invoice is paid in full. That date is before the Hartford loss
-- run terms that start 12/01/2024.
-- Word scores stay on ocr_word. The words under 0.8 are Rostova 0.741 and
-- Elena 0.768.
-- =============================================================================

USE underwriting;


CREATE TABLE IF NOT EXISTS underwriting.large_loss_narrative (
  narrative_id              STRING    COMMENT 'PK. One large loss narrative.',
  submission_id             STRING    COMMENT 'FK -> submissions.submission_id.',
  named_insured             STRING    COMMENT 'Named insured.',
  date_prepared             STRING    COMMENT 'Date prepared, ISO-8601.',
  related_claim_date        STRING    COMMENT 'Date of loss, ISO-8601.',
  related_claim_amount      BIGINT    COMMENT 'Claim amount in whole currency units.',
  author                    STRING    COMMENT 'Narrative author.',
  author_title              STRING    COMMENT 'Author title.',
  claim_description         STRING    COMMENT 'Loss narrative.',
  future_mitigation         STRING    COMMENT 'Steps taken to prevent recurrence.',
  signature_detected        BOOLEAN   COMMENT 'True when the narrative signature is detected.',
  contractor_name           STRING    COMMENT 'Invoice contractor.',
  invoice_number            STRING    COMMENT 'Invoice number.',
  invoice_date              STRING    COMMENT 'Invoice date, ISO-8601.',
  invoice_total             BIGINT    COMMENT 'Invoice total in whole currency units.',
  invoice_status            STRING    COMMENT 'Paid in Full or another status printed on the invoice.'
)
COMMENT 'Large loss narrative and the remediation invoice header.'
PARTITIONED BY SPEC (
  submission_id
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'LargeLossNarrative',
  'llm.primary_key' = 'narrative_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one large loss narrative'
);


CREATE TABLE IF NOT EXISTS underwriting.large_loss_invoice_line (
  line_id                   STRING    COMMENT 'PK. One invoice line.',
  narrative_id              STRING    COMMENT 'FK -> large_loss_narrative.narrative_id.',
  submission_id             STRING    COMMENT 'FK -> submissions.submission_id.',
  description               STRING    COMMENT 'Line description.',
  amount                    BIGINT    COMMENT 'Line amount in whole currency units.'
)
COMMENT 'Remediation invoice lines for a large loss narrative.'
PARTITIONED BY SPEC (
  submission_id
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'LargeLossInvoiceLine',
  'llm.primary_key' = 'line_id',
  'llm.foreign_keys' = 'narrative_id->large_loss_narrative.narrative_id;submission_id->submissions.submission_id',
  'llm.grain' = 'one remediation invoice line'
);


CREATE TABLE IF NOT EXISTS underwriting.large_loss_remediation (
  action_id                 STRING    COMMENT 'PK. One remediation step.',
  narrative_id              STRING    COMMENT 'FK -> large_loss_narrative.narrative_id.',
  submission_id             STRING    COMMENT 'FK -> submissions.submission_id.',
  action_text               STRING    COMMENT 'Remediation action.'
)
COMMENT 'Remediation steps listed on a large loss narrative.'
PARTITIONED BY SPEC (
  submission_id
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'LargeLossRemediation',
  'llm.primary_key' = 'action_id',
  'llm.foreign_keys' = 'narrative_id->large_loss_narrative.narrative_id;submission_id->submissions.submission_id',
  'llm.grain' = 'one remediation step'
);
