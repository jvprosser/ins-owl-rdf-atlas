-- =============================================================================
-- Underwriting governance columns for playbook 2.2.0
-- Prerequisite: underwriting_iceberg.sql already applied
-- =============================================================================
-- Adds the facts P00–P40 read. Existing rows stay null until
-- underwriting_governance_seed.sql runs.
-- =============================================================================

USE underwriting;

ALTER TABLE underwriting.submissions ADD COLUMNS (
  naics_code            STRING,
  has_ofac_match        BOOLEAN,
  siu_score             INT,
  tax_lien_unresolved   BOOLEAN
);

ALTER TABLE underwriting.property_risk_scores ADD COLUMNS (
  has_survey_on_file    BOOLEAN,
  survey_age_months     INT,
  wind_tier             INT,
  has_recent_cat_run    BOOLEAN,
  construction_type     STRING,
  year_built            INT,
  wiring_updated        BOOLEAN,
  protection_class      STRING,
  has_sprinklers        BOOLEAN,
  square_footage        INT
);

ALTER TABLE underwriting.loss_history_summary ADD COLUMNS (
  claims_count_36m      INT,
  total_incurred_36m    BIGINT,
  financial_score       INT
);
