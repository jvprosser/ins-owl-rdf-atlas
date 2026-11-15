-- =============================================================================
-- ACORD 810 rental value worksheet — Cloudera Hive + Apache Iceberg DDL
-- =============================================================================
-- Engine target : CDP Hive / Impala Iceberg v2
-- Database      : underwriting
-- Prerequisite  : underwriting_iceberg.sql and underwriting_sov.sql applied
--
-- businessincome-rentalvalue-scanned.json is one ACORD 810 (2015/12) page
-- for Oakridge Plaza, premises 001 / building 001. Coverage basis is
-- Rental Value Only. Net rental value and the selected limit are both
-- 480000, which is the business income line on the statement of values.
-- The rent roll sums to annual gross rent 435000 and to 18500 square feet.
-- Word scores stay on ocr_word. On this page the words under 0.8 are
-- Rostova 0.658, Elena 0.712, and 1/3 0.742.
-- =============================================================================

USE underwriting;


CREATE TABLE IF NOT EXISTS underwriting.rental_value_worksheet (
  worksheet_id                  STRING    COMMENT 'PK. One ACORD 810 worksheet.',
  submission_id                 STRING    COMMENT 'FK -> submissions.submission_id.',
  form_number                   STRING    COMMENT 'ACORD 810.',
  form_edition                  STRING    COMMENT '2015/12.',
  worksheet_date                STRING    COMMENT 'Worksheet date, ISO-8601.',
  named_insured                 STRING    COMMENT 'Named insured.',
  premises_number               STRING    COMMENT 'Premises number, e.g. 001.',
  building_number               STRING    COMMENT 'Building number, e.g. 001.',
  premises_address              STRING    COMMENT 'Address printed on the worksheet.',
  coverage_type                 STRING    COMMENT 'Rental Value Only, Business Income, or BI & Extra Expense.',
  financial_period              STRING    COMMENT 'Projection period printed on the worksheet.',
  annual_gross_rent             BIGINT    COMMENT 'Occupied-space annual gross rent.',
  tenant_contributions          BIGINT    COMMENT 'Tenant taxes, CAM, and insurance contributions.',
  fair_rental_value_vacant      BIGINT    COMMENT 'Fair rental value of vacant space.',
  total_gross_rental_income     BIGINT    COMMENT 'Sum of gross rent, contributions, and vacant rental value.',
  janitorial_services           BIGINT    COMMENT 'Non-continuing janitorial expense.',
  landscaping_and_snow_removal  BIGINT    COMMENT 'Non-continuing landscaping and snow removal.',
  utilities                     BIGINT    COMMENT 'Non-continuing utilities.',
  ordinary_payroll              BIGINT    COMMENT 'Non-continuing ordinary payroll.',
  property_management_fees      BIGINT    COMMENT 'Variable property management fees.',
  total_deductions              BIGINT    COMMENT 'Sum of the non-continuing expenses.',
  net_rental_value              BIGINT    COMMENT 'Total gross rental income minus total deductions.',
  selected_limit                BIGINT    COMMENT 'Selected limit of insurance.',
  monthly_limitation            STRING    COMMENT 'Monthly limitation fraction, e.g. 1/3.',
  coinsurance_percentage        STRING    COMMENT 'Coinsurance percent, or empty when the worksheet says N/A.'
)
PARTITIONED BY SPEC (
  submission_id
)
COMMENT 'ACORD 810 business income / extra expense / rental value worksheet.'
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'RentalValueWorksheet',
  'llm.primary_key' = 'worksheet_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one rental value worksheet'
);


CREATE TABLE IF NOT EXISTS underwriting.rental_value_tenant (
  tenant_id                     STRING    COMMENT 'PK. One rent-roll unit.',
  worksheet_id                  STRING    COMMENT 'FK -> rental_value_worksheet.worksheet_id.',
  submission_id                 STRING    COMMENT 'FK -> submissions.submission_id.',
  unit                          STRING    COMMENT 'Unit letter or number.',
  tenant_name                   STRING    COMMENT 'Tenant name.',
  square_footage                INT       COMMENT 'Unit area in square feet.',
  annual_base_rent              BIGINT    COMMENT 'Annual base rent.'
)
PARTITIONED BY SPEC (
  submission_id
)
COMMENT 'Rent roll lines on an ACORD 810 worksheet.'
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'RentalValueTenant',
  'llm.primary_key' = 'tenant_id',
  'llm.foreign_keys' = 'worksheet_id->rental_value_worksheet.worksheet_id;submission_id->submissions.submission_id',
  'llm.grain' = 'one tenant on a rental value worksheet'
);
