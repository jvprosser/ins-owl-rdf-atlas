-- =============================================================================
-- 4-point system update verification — Cloudera Hive + Apache Iceberg DDL
-- =============================================================================
-- Engine target : CDP Hive / Impala Iceberg v2
-- Database      : underwriting
-- Prerequisite  : underwriting_iceberg.sql already applied
--
-- 4-point-inspection-scanned.json is one page for Oakridge Plaza, built 2004.
-- Roof: TPO membrane, full replacement 2021.
-- Plumbing: copper / PVC, original 2004, no polybutylene.
-- Electrical: copper 800-amp, original 2004, no aluminum branch wiring.
-- HVAC: rooftop units, partial replacement 2023.
-- Word scores stay on ocr_word. On this page the words under 0.8 are
-- OConnor 0.718 and James 0.742.
-- =============================================================================

USE underwriting;


CREATE TABLE IF NOT EXISTS underwriting.four_point_inspection (
  inspection_id             STRING    COMMENT 'PK. One 4-point inspection.',
  submission_id             STRING    COMMENT 'FK -> submissions.submission_id.',
  form_title                STRING    COMMENT '4-POINT SYSTEM UPDATE VERIFICATION.',
  inspection_date           STRING    COMMENT 'Inspection date, ISO-8601.',
  property_address          STRING    COMMENT 'Address printed on the inspection.',
  named_insured             STRING    COMMENT 'Named insured.',
  year_built                INT       COMMENT 'Year built printed on the inspection.',
  inspector_name            STRING    COMMENT 'Inspector name.',
  license_number            STRING    COMMENT 'Inspector license number.',
  company_name              STRING    COMMENT 'Inspection company.',
  signature_detected        BOOLEAN   COMMENT 'True when a signature is detected.',
  date_signed               STRING    COMMENT 'Signature date, ISO-8601.'
)
COMMENT '4-point roof, plumbing, electrical, and HVAC inspection.'
PARTITIONED BY SPEC (
  submission_id
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'FourPointInspection',
  'llm.primary_key' = 'inspection_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one 4-point inspection'
);


CREATE TABLE IF NOT EXISTS underwriting.four_point_system (
  system_id                 STRING    COMMENT 'PK. One inspected system.',
  inspection_id             STRING    COMMENT 'FK -> four_point_inspection.inspection_id.',
  submission_id             STRING    COMMENT 'FK -> submissions.submission_id.',
  system_name               STRING    COMMENT 'roof, plumbing, electrical, or hvac.',
  system_type               STRING    COMMENT 'System description printed on the form.',
  year_last_updated         INT       COMMENT 'Year the system was last updated.',
  update_type               STRING    COMMENT 'Full Replacement, Partial Replacement, or Original.',
  notes                     STRING    COMMENT 'Inspector notes for the system.'
)
COMMENT 'Roof, plumbing, electrical, and HVAC rows on a 4-point inspection.'
PARTITIONED BY SPEC (
  submission_id
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'FourPointSystem',
  'llm.primary_key' = 'system_id',
  'llm.foreign_keys' = 'inspection_id->four_point_inspection.inspection_id;submission_id->submissions.submission_id',
  'llm.grain' = 'one system on a 4-point inspection'
);
