-- =============================================================================
-- Retirement distributions — seed (demo 7001 / 7002 / 7003)
-- Prerequisite: retirement_distributions_iceberg.sql
-- =============================================================================
-- 7001 TERMINATION, no exceptions → ProcessDistribution
-- 7002 HARDSHIP missing substantiation → RequestSubstantiation (R2.2)
-- 7003 RMD underpaid → RmdReview (R2.3)
-- =============================================================================

USE retirement_distributions;

-- Optional cleanup (uncomment for re-seed)
-- TRUNCATE TABLE distribution_rmd;
-- TRUNCATE TABLE distribution_exception;
-- TRUNCATE TABLE distribution_request;


INSERT INTO TABLE retirement_distributions.distribution_request
SELECT * FROM (
  SELECT CAST(7001 AS BIGINT) AS distribution_request_id,
         'OPEN' AS request_status_code,
         'TERMINATION' AS distribution_type_code,
         '401k-alpha' AS plan_id,
         'P-7001' AS participant_id,
         FALSE AS hold_or_aml_flag,
         CAST('2026-01-15 10:00:00' AS TIMESTAMP) AS created_at
  UNION ALL
  SELECT 7002, 'OPEN', 'HARDSHIP', '401k-alpha', 'P-7002', FALSE,
         CAST('2026-02-01 09:30:00' AS TIMESTAMP)
  UNION ALL
  SELECT 7003, 'OPEN', 'RMD', '401k-alpha', 'P-7003', FALSE,
         CAST('2026-03-01 11:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE retirement_distributions.distribution_exception
SELECT * FROM (
  SELECT 'EX-7002' AS exception_id,
         CAST(7002 AS BIGINT) AS distribution_request_id,
         'HARDSHIP_SUBSTANTIATION_MISSING' AS reason_code,
         'ExceptionQueue' AS queue,
         '["medical_bills","hardship_attestation"]' AS required_docs,
         CAST('2026-02-01 09:35:00' AS TIMESTAMP) AS created_at
) s;


INSERT INTO TABLE retirement_distributions.distribution_rmd
SELECT * FROM (
  SELECT CAST(7301 AS BIGINT) AS rmd_id,
         CAST(7003 AS BIGINT) AS distribution_request_id,
         CAST(2026 AS INT) AS tax_year,
         CAST(12500.00 AS DECIMAL(18,2)) AS required_amount,
         CAST(8000.00 AS DECIMAL(18,2)) AS paid_amount,
         CAST(4500.00 AS DECIMAL(18,2)) AS shortfall_amount,
         CAST('2026-12-31' AS DATE) AS deadline,
         CAST('2026-03-01 11:05:00' AS TIMESTAMP) AS created_at
) s;
