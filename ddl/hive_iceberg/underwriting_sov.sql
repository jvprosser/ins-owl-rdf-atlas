-- =============================================================================
-- Statement of values — Cloudera Hive + Apache Iceberg DDL
-- =============================================================================
-- Engine target : CDP Hive / Impala Iceberg v2
-- Database      : underwriting
-- Prerequisite  : underwriting_iceberg.sql already applied
--
-- One row per subject of insurance at a location and building.
-- Oakridge_Plaza_Statement_of_Values.csv is location 001 / building 001:
--   Building                         4250000  RC   90%          deductible 5000
--   Business Income & Extra Expense   480000  ALS  1/3 Monthly  deductible 72
--   Equipment Breakdown              4250000  RC   N/A          deductible 5000
--   Outdoor Signs                      35000  RC   80%          deductible 1000
-- Equipment Breakdown repeats the building limit, so the routing total
-- excludes it: 4250000 + 480000 + 35000 = 4765000.
-- =============================================================================

USE underwriting;


CREATE TABLE IF NOT EXISTS underwriting.statement_of_values (
  sov_id                    STRING    COMMENT 'PK. One coverage line.',
  submission_id             BIGINT    COMMENT 'FK -> submissions.submission_id.',
  loc_number                STRING    COMMENT 'Location number, e.g. 001.',
  bldg_number               STRING    COMMENT 'Building number, e.g. 001.',
  named_insured             STRING    COMMENT 'Named insured on the schedule.',
  street_address            STRING    COMMENT 'Street address.',
  city                      STRING    COMMENT 'City.',
  state                     STRING    COMMENT 'State.',
  zip                       STRING    COMMENT 'ZIP code.',
  subject_of_insurance      STRING    COMMENT 'Building, Business Income & Extra Expense, Equipment Breakdown, Outdoor Signs.',
  occupancy                 STRING    COMMENT 'Occupancy description.',
  construction_type         STRING    COMMENT 'Schedule text, e.g. Masonry Non-Combustible (ISO 4).',
  year_built                INT       COMMENT 'Year built.',
  area_sq_ft                INT       COMMENT 'Building area in square feet.',
  sprinklered               BOOLEAN   COMMENT 'True when the schedule says Yes.',
  protection_class          STRING    COMMENT 'Public protection class as printed, e.g. 02.',
  limit_amount              BIGINT    COMMENT 'Coverage limit in whole currency units.',
  valuation                 STRING    COMMENT 'RC, ALS (12 Mos), or other valuation text.',
  coinsurance               STRING    COMMENT '90%, 80%, N/A, or 1/3 Monthly.',
  deductible                INT       COMMENT 'Deductible amount, or waiting period hours for business income.'
)
COMMENT 'Statement of values. One row per subject of insurance.'
PARTITIONED BY SPEC (
  submission_id
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'StatementOfValues',
  'llm.primary_key' = 'sov_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one subject of insurance at a location and building'
);
