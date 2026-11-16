-- =============================================================================
-- Underwriting submissions — seed (SUB-9100 … SUB-9107)
-- Prerequisite: underwriting_iceberg.sql. Safe after underwriting_governance_alter.sql:
-- the three widened tables name their original columns. Added columns stay null
-- until underwriting_governance_seed.sql.
-- =============================================================================
-- SUB-9100 class 4812                         → DECLINE_UNINSURABLE (P0)
-- SUB-9101 TIV 2000001, inspection open       → TRIGGER_SURVEY (P1)
-- SUB-9102 TIV 4500000, flood, inspection open → TRIGGER_SURVEY (P1);
--   set inspection_completed = TRUE and re-chat → REFER_TO_SENIOR_UW (P2)
-- SUB-9103 TIV 1999999, no flood, 0 claims    → AUTO_RATE_AND_BIND (P3)
-- SUB-9104 inspection done, flood, TIV 1.5M   → REFER_TO_SENIOR_UW (P2)
-- SUB-9105 one prior claim, no flood, TIV 500k → HUMAN_UW_REVIEW
-- SUB-9106 TIV 25000001, inspection open      → DECLINE_UNINSURABLE (P0)
-- SUB-9107 TIV 1800000, inspection done, no owner → AssignUnderwriter (U0);
--   insert UNDERWRITER party 14 and re-chat → AUTO_RATE_AND_BIND (P3)
-- Party 14 (Riley Cho) owns SUB-9100 … SUB-9106.
-- =============================================================================

USE underwriting;

INSERT INTO TABLE underwriting.appetite_class_codes
SELECT * FROM (
  SELECT '4812' AS class_code, 'PROHIBITED' AS appetite_status_code
  UNION ALL
  SELECT '5921', 'PROHIBITED'
  UNION ALL
  SELECT '5411', 'ACCEPT'
) s;


INSERT INTO TABLE underwriting.submissions (
  submission_id, submission_number, producer_id, applicant_tax_id,
  line_of_business, class_code, total_insured_value,
  submission_timestamp, submission_status_code
)
SELECT * FROM (
  SELECT CAST(9100 AS BIGINT) AS submission_id, 'SUB-9100' AS submission_number,
         'PRD-100' AS producer_id,
         '91-0910000' AS applicant_tax_id, 'COMMERCIAL_PROPERTY' AS line_of_business,
         '4812' AS class_code, CAST(800000 AS BIGINT) AS total_insured_value,
         CAST('2026-11-01 09:00:00' AS TIMESTAMP) AS submission_timestamp,
         'OPEN' AS submission_status_code
  UNION ALL
  SELECT CAST(9101 AS BIGINT), 'SUB-9101', 'PRD-100', '91-0910001', 'COMMERCIAL_PROPERTY', '5411',
         CAST(2000001 AS BIGINT), CAST('2026-11-01 09:00:00' AS TIMESTAMP), 'OPEN'
  UNION ALL
  SELECT CAST(9102 AS BIGINT), 'SUB-9102', 'PRD-100', '91-0910002', 'COMMERCIAL_PROPERTY', '5411',
         CAST(4500000 AS BIGINT), CAST('2026-11-01 09:00:00' AS TIMESTAMP), 'OPEN'
  UNION ALL
  SELECT CAST(9103 AS BIGINT), 'SUB-9103', 'PRD-100', '91-0910003', 'COMMERCIAL_PROPERTY', '5411',
         CAST(1999999 AS BIGINT), CAST('2026-11-01 09:00:00' AS TIMESTAMP), 'OPEN'
  UNION ALL
  SELECT CAST(9104 AS BIGINT), 'SUB-9104', 'PRD-100', '91-0910004', 'COMMERCIAL_PROPERTY', '5411',
         CAST(1500000 AS BIGINT), CAST('2026-11-01 09:00:00' AS TIMESTAMP), 'OPEN'
  UNION ALL
  SELECT CAST(9105 AS BIGINT), 'SUB-9105', 'PRD-100', '91-0910005', 'COMMERCIAL_PROPERTY', '5411',
         CAST(500000 AS BIGINT), CAST('2026-11-01 09:00:00' AS TIMESTAMP), 'OPEN'
  UNION ALL
  SELECT CAST(9106 AS BIGINT), 'SUB-9106', 'PRD-100', '91-0910006', 'COMMERCIAL_PROPERTY', '5411',
         CAST(25000001 AS BIGINT), CAST('2026-11-01 09:00:00' AS TIMESTAMP), 'OPEN'
  UNION ALL
  SELECT CAST(9107 AS BIGINT), 'SUB-9107', 'PRD-100', '91-0910007', 'COMMERCIAL_PROPERTY', '5411',
         CAST(1800000 AS BIGINT), CAST('2026-11-01 09:00:00' AS TIMESTAMP), 'OPEN'
) s;


INSERT INTO TABLE underwriting.property_risk_scores (
  risk_score_id, submission_id, is_in_flood_plain, inspection_completed, flood_zone
)
SELECT * FROM (
  SELECT 'RS-9100' AS risk_score_id, CAST(9100 AS BIGINT) AS submission_id,
         FALSE AS is_in_flood_plain, TRUE AS inspection_completed, 'NONE' AS flood_zone
  UNION ALL
  SELECT 'RS-9101', CAST(9101 AS BIGINT), FALSE, FALSE, 'NONE'
  UNION ALL
  SELECT 'RS-9102', CAST(9102 AS BIGINT), TRUE, FALSE, 'AE'
  UNION ALL
  SELECT 'RS-9103', CAST(9103 AS BIGINT), FALSE, FALSE, 'NONE'
  UNION ALL
  SELECT 'RS-9104', CAST(9104 AS BIGINT), TRUE, TRUE, 'AE'
  UNION ALL
  SELECT 'RS-9105', CAST(9105 AS BIGINT), FALSE, TRUE, 'NONE'
  UNION ALL
  SELECT 'RS-9106', CAST(9106 AS BIGINT), FALSE, FALSE, 'NONE'
  UNION ALL
  SELECT 'RS-9107', CAST(9107 AS BIGINT), FALSE, TRUE, 'NONE'
) s;


INSERT INTO TABLE underwriting.loss_history_summary (
  loss_summary_id, submission_id, prior_claims_count,
  has_open_loss_past_36m, financial_stability_tier
)
SELECT * FROM (
  SELECT 'LH-9100' AS loss_summary_id, CAST(9100 AS BIGINT) AS submission_id,
         0 AS prior_claims_count, FALSE AS has_open_loss_past_36m,
         'B' AS financial_stability_tier
  UNION ALL
  SELECT 'LH-9101', CAST(9101 AS BIGINT), 0, FALSE, 'B'
  UNION ALL
  SELECT 'LH-9102', CAST(9102 AS BIGINT), 1, FALSE, 'B'
  UNION ALL
  SELECT 'LH-9103', CAST(9103 AS BIGINT), 0, FALSE, 'B'
  UNION ALL
  SELECT 'LH-9104', CAST(9104 AS BIGINT), 0, FALSE, 'C'
  UNION ALL
  SELECT 'LH-9105', CAST(9105 AS BIGINT), 1, FALSE, 'A'
  UNION ALL
  SELECT 'LH-9106', CAST(9106 AS BIGINT), 0, FALSE, 'B'
  UNION ALL
  SELECT 'LH-9107', CAST(9107 AS BIGINT), 0, FALSE, 'B'
) s;


INSERT INTO TABLE underwriting.mvr_reports
SELECT * FROM (
  SELECT 'MVR-9100' AS mvr_id, CAST(9100 AS BIGINT) AS submission_id,
         0 AS violation_count, FALSE AS major_violation,
         'ON_FILE' AS report_status_code
  UNION ALL
  SELECT 'MVR-9101', CAST(9101 AS BIGINT), 0, FALSE, 'ON_FILE'
  UNION ALL
  SELECT 'MVR-9102', CAST(9102 AS BIGINT), 0, FALSE, 'ON_FILE'
  UNION ALL
  SELECT 'MVR-9103', CAST(9103 AS BIGINT), 0, FALSE, 'ON_FILE'
  UNION ALL
  SELECT 'MVR-9104', CAST(9104 AS BIGINT), 0, FALSE, 'ON_FILE'
  UNION ALL
  SELECT 'MVR-9105', CAST(9105 AS BIGINT), 0, FALSE, 'ON_FILE'
  UNION ALL
  SELECT 'MVR-9106', CAST(9106 AS BIGINT), 0, FALSE, 'ON_FILE'
  UNION ALL
  SELECT 'MVR-9107', CAST(9107 AS BIGINT), 0, FALSE, 'ON_FILE'
) s;


INSERT INTO TABLE underwriting.person
SELECT CAST(14 AS BIGINT) AS party_id, 'Riley' AS first_name, 'Cho' AS last_name;


INSERT INTO TABLE underwriting.submission_party_role
SELECT * FROM (
  SELECT 'SPR-9100' AS submission_party_role_id, CAST(9100 AS BIGINT) AS submission_id,
         CAST(14 AS BIGINT) AS party_id, 'UNDERWRITER' AS role_type_code,
         CAST('2026-11-01 09:05:00' AS TIMESTAMP) AS assigned_at,
         CAST(NULL AS TIMESTAMP) AS unassigned_at,
         TRUE AS is_current_assignment,
         CAST('2026-11-01 09:05:00' AS TIMESTAMP) AS created_at
  UNION ALL
  SELECT 'SPR-9101', CAST(9101 AS BIGINT), CAST(14 AS BIGINT), 'UNDERWRITER',
         CAST('2026-11-01 09:05:00' AS TIMESTAMP), CAST(NULL AS TIMESTAMP), TRUE,
         CAST('2026-11-01 09:05:00' AS TIMESTAMP)
  UNION ALL
  SELECT 'SPR-9102', CAST(9102 AS BIGINT), CAST(14 AS BIGINT), 'UNDERWRITER',
         CAST('2026-11-01 09:05:00' AS TIMESTAMP), CAST(NULL AS TIMESTAMP), TRUE,
         CAST('2026-11-01 09:05:00' AS TIMESTAMP)
  UNION ALL
  SELECT 'SPR-9103', CAST(9103 AS BIGINT), CAST(14 AS BIGINT), 'UNDERWRITER',
         CAST('2026-11-01 09:05:00' AS TIMESTAMP), CAST(NULL AS TIMESTAMP), TRUE,
         CAST('2026-11-01 09:05:00' AS TIMESTAMP)
  UNION ALL
  SELECT 'SPR-9104', CAST(9104 AS BIGINT), CAST(14 AS BIGINT), 'UNDERWRITER',
         CAST('2026-11-01 09:05:00' AS TIMESTAMP), CAST(NULL AS TIMESTAMP), TRUE,
         CAST('2026-11-01 09:05:00' AS TIMESTAMP)
  UNION ALL
  SELECT 'SPR-9105', CAST(9105 AS BIGINT), CAST(14 AS BIGINT), 'UNDERWRITER',
         CAST('2026-11-01 09:05:00' AS TIMESTAMP), CAST(NULL AS TIMESTAMP), TRUE,
         CAST('2026-11-01 09:05:00' AS TIMESTAMP)
  UNION ALL
  SELECT 'SPR-9106', CAST(9106 AS BIGINT), CAST(14 AS BIGINT), 'UNDERWRITER',
         CAST('2026-11-01 09:05:00' AS TIMESTAMP), CAST(NULL AS TIMESTAMP), TRUE,
         CAST('2026-11-01 09:05:00' AS TIMESTAMP)
) s;
