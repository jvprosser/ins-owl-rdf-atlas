-- =============================================================================
-- Seed governance columns on SUB-9100 … SUB-9107
-- Prerequisite: underwriting_governance_alter.sql
-- =============================================================================
-- SUB-9100 NAICS 325120                         → DECLINE_UNINSURABLE_CLASS (P00)
-- SUB-9101 OFAC match                           → HOLD_COMPLIANCE_FREEZE (P01)
-- SUB-9102 3 property losses in 36 months       → DECLINE_ADVERSE_LOSS_HISTORY (P02)
-- SUB-9103 SIU score 90                         → REFER_TO_SPECIAL_INVESTIGATIONS (P10)
-- SUB-9104 TIV 6000000, no survey               → ORDER_RISK_ENGINEERING_SURVEY (P20)
-- SUB-9105 protection class 9                   → REFER_PROPERTY_FACULTATIVE_DESK (P31)
-- SUB-9106 TIV 25000001, survey on file         → REFER_SENIOR_PROPERTY_UW (P30)
-- SUB-9107 clean, no underwriter                → AssignUnderwriter (U0);
--   after party 14 is assigned                  → EXECUTE_AUTOMATED_BIND_AND_QUOTE (P40)
-- Wind tier stays 0, so P21 does not fire on the seed.
-- =============================================================================

USE underwriting;

UPDATE underwriting.submissions
SET naics_code = CASE submission_id
      WHEN 9100 THEN '325120'
      ELSE '541110'
    END,
    has_ofac_match = CASE submission_id
      WHEN 9101 THEN TRUE
      ELSE FALSE
    END,
    siu_score = CASE submission_id
      WHEN 9103 THEN 90
      ELSE 0
    END,
    tax_lien_unresolved = FALSE,
    total_insured_value = CASE submission_id
      WHEN 9104 THEN CAST(6000000 AS BIGINT)
      ELSE total_insured_value
    END
WHERE submission_id IN (
  9100, 9101, 9102, 9103,
  9104, 9105, 9106, 9107
);

UPDATE underwriting.property_risk_scores
SET has_survey_on_file = CASE submission_id
      WHEN 9104 THEN FALSE
      ELSE TRUE
    END,
    survey_age_months = 12,
    wind_tier = 0,
    has_recent_cat_run = TRUE,
    construction_type = CASE submission_id
      WHEN 9104 THEN 'FRAME'
      ELSE 'MASONRY'
    END,
    year_built = 1990,
    wiring_updated = TRUE,
    protection_class = CASE submission_id
      WHEN 9105 THEN '9'
      ELSE '3'
    END,
    has_sprinklers = TRUE,
    square_footage = 10000
WHERE submission_id IN (
  9100, 9101, 9102, 9103,
  9104, 9105, 9106, 9107
);

UPDATE underwriting.loss_history_summary
SET claims_count_36m = CASE submission_id
      WHEN 9102 THEN 3
      ELSE 0
    END,
    total_incurred_36m = CAST(0 AS BIGINT),
    financial_score = 700
WHERE submission_id IN (
  9100, 9101, 9102, 9103,
  9104, 9105, 9106, 9107
);
