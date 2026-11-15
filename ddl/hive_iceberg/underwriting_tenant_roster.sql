-- =============================================================================
-- Tenant roster — Cloudera Hive + Apache Iceberg DDL
-- =============================================================================
-- Engine target : CDP Hive / Impala Iceberg v2
-- Database      : underwriting
-- Prerequisite  : underwriting_iceberg.sql already applied
--
-- tenant-roster-scanned.json is the Oakridge Plaza roster as of 2026-11-15.
-- Four units total 18500 sq ft, vacancy is 0, and the signature is present.
-- Units A–D and their areas match the ACORD 810 rent roll.
-- Unit A states there is no commercial cooking.
-- Word scores stay on ocr_word. The lowest word on the page is Manager at 0.812.
-- =============================================================================

USE underwriting;


CREATE TABLE IF NOT EXISTS underwriting.tenant_roster (
  roster_id                     STRING    COMMENT 'PK. One tenant roster.',
  submission_id                 STRING    COMMENT 'FK -> submissions.submission_id.',
  named_insured                 STRING    COMMENT 'Named insured.',
  property_address              STRING    COMMENT 'Property address.',
  as_of_date                    STRING    COMMENT 'Roster date, ISO-8601.',
  total_rentable_area_sq_ft     INT       COMMENT 'Total rentable area.',
  occupied_area_sq_ft           INT       COMMENT 'Occupied area.',
  vacant_area_sq_ft             INT       COMMENT 'Vacant area.',
  vacancy_rate_percentage       DOUBLE    COMMENT 'Vacancy rate as printed, e.g. 0.0.',
  total_units                   INT       COMMENT 'Unit count printed on the summary.',
  certified_by                  STRING    COMMENT 'Certifying party.',
  signature_detected            BOOLEAN   COMMENT 'True when a certification signature is detected.'
)
PARTITIONED BY SPEC (
  submission_id
)
COMMENT 'Tenant roster header and building occupancy summary.'
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'TenantRoster',
  'llm.primary_key' = 'roster_id',
  'llm.foreign_keys' = 'submission_id->submissions.submission_id',
  'llm.grain' = 'one tenant roster'
);


CREATE TABLE IF NOT EXISTS underwriting.tenant_roster_unit (
  unit_id                       STRING    COMMENT 'PK. One roster unit.',
  roster_id                     STRING    COMMENT 'FK -> tenant_roster.roster_id.',
  submission_id                 STRING    COMMENT 'FK -> submissions.submission_id.',
  unit_number                   STRING    COMMENT 'Unit letter or number.',
  tenant_name                   STRING    COMMENT 'Tenant name.',
  area_sq_ft                    INT       COMMENT 'Unit area.',
  percent_of_total_area         DOUBLE    COMMENT 'Share of building area as printed.',
  business_classification       STRING    COMMENT 'Business classification.',
  operations_description        STRING    COMMENT 'Operations description.',
  lease_expiration              STRING    COMMENT 'Lease expiration, ISO-8601.'
)
PARTITIONED BY SPEC (
  submission_id
)
COMMENT 'Units on a tenant roster.'
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'underwriting',
  'llm.ontology_class' = 'TenantRosterUnit',
  'llm.primary_key' = 'unit_id',
  'llm.foreign_keys' = 'roster_id->tenant_roster.roster_id;submission_id->submissions.submission_id',
  'llm.grain' = 'one unit on a tenant roster'
);
