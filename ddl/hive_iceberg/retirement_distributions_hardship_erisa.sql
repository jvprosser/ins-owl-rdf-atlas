-- =============================================================================
-- Additive: hardship / ERISA / SECURE 2.0 / QDRO tables + 7011–7017 seeds
-- Prerequisite: retirement_distributions_iceberg.sql already applied
-- For lakes that already have 7001–7003 without requested_amount.
-- Fresh installs: skip this file; use the updated iceberg.sql + seed_data.sql.
-- =============================================================================

USE retirement_distributions;

ALTER TABLE retirement_distributions.distribution_request ADD COLUMNS (
  requested_amount DECIMAL(18,2) COMMENT 'Requested distribution amount.'
);

-- New tables (CREATE IF NOT EXISTS matches iceberg.sql; safe if already created)
-- Copy from retirement_distributions_iceberg.sql if this file is run alone on
-- an old lake that never received the new CREATE TABLE statements.

CREATE TABLE IF NOT EXISTS retirement_distributions.distribution_plan (
  plan_id                       STRING    COMMENT 'PK. Plan identifier (e.g. 401k-alpha).',
  plan_subject_to_qjsa          BOOLEAN   COMMENT 'True when ERISA QJSA / spousal consent applies.',
  plan_mandates_loan_exhaustion BOOLEAN   COMMENT 'True when available loans must be exhausted before hardship.',
  created_at                    TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Plan-level ERISA / hardship loan rules.'
PARTITIONED BY SPEC (plan_id)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES ('format-version' = '2');

CREATE TABLE IF NOT EXISTS retirement_distributions.distribution_participant (
  participant_id                STRING    COMMENT 'PK. Participant business key.',
  participant_marital_status    STRING    COMMENT 'SINGLE | MARRIED | DIVORCED | WIDOWED.',
  spousal_consent_verified      BOOLEAN   COMMENT 'True when signed spousal consent is on file.',
  created_at                    TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Participant marital / QJSA consent facts.'
PARTITIONED BY SPEC (participant_marital_status)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES ('format-version' = '2');

CREATE TABLE IF NOT EXISTS retirement_distributions.distribution_hardship (
  distribution_request_id             BIGINT,
  hardship_category                   STRING,
  documented_financial_need_amount    DECIMAL(18,2),
  estimated_tax_withholding_amount    DECIMAL(18,2),
  has_participant_self_certified      BOOLEAN,
  requires_substantiation_audit       BOOLEAN,
  created_at                          TIMESTAMP
)
COMMENT 'Hardship facts for playbook CEL.'
PARTITIONED BY SPEC (hardship_category)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES ('format-version' = '2');

CREATE TABLE IF NOT EXISTS retirement_distributions.distribution_loan (
  distribution_request_id       BIGINT,
  available_plan_loan_capacity  DECIMAL(18,2),
  outstanding_loan_balance      DECIMAL(18,2),
  max_loan_amount               DECIMAL(18,2),
  created_at                    TIMESTAMP
)
COMMENT 'Plan loan capacity for hardship loan-exhaustion probe.'
PARTITIONED BY SPEC (distribution_request_id)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES ('format-version' = '2');

CREATE TABLE IF NOT EXISTS retirement_distributions.distribution_qdro (
  qdro_id                     BIGINT,
  distribution_request_id     BIGINT,
  is_active                   BOOLEAN,
  order_status_code           STRING,
  alternate_payee_name        STRING,
  hold_reason                 STRING,
  created_at                  TIMESTAMP
)
COMMENT 'QDRO hold on a distribution request.'
PARTITIONED BY SPEC (order_status_code)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES ('format-version' = '2');

CREATE TABLE IF NOT EXISTS retirement_distributions.distribution_court_order (
  court_order_id              BIGINT,
  distribution_request_id     BIGINT,
  docket_number               STRING,
  status_code                 STRING,
  created_at                  TIMESTAMP
)
COMMENT 'Pending court orders on a distribution request.'
PARTITIONED BY SPEC (status_code)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES ('format-version' = '2');

CREATE TABLE IF NOT EXISTS retirement_distributions.distribution_emergency_ytd (
  distribution_request_id     BIGINT,
  tax_year                    INT,
  prior_count                 INT,
  created_at                  TIMESTAMP
)
COMMENT 'Year-to-date emergency distribution count.'
PARTITIONED BY SPEC (tax_year)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES ('format-version' = '2');

CREATE TABLE IF NOT EXISTS retirement_distributions.distribution_outbound_notice (
  notice_id                   BIGINT,
  distribution_request_id     BIGINT,
  purpose_code                STRING,
  channel_code                STRING,
  body_text                   STRING,
  run_id                      STRING,
  created_at                  TIMESTAMP
)
COMMENT 'Outbound client notice written by send_client_notice.'
PARTITIONED BY SPEC (purpose_code)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES ('format-version' = '2');

-- Backfill existing 7001–7003 amounts; insert remaining demo rows.
-- Skip INSERTs that already exist if re-running.

INSERT INTO TABLE retirement_distributions.distribution_plan
SELECT * FROM (
  SELECT '401k-alpha' AS plan_id, FALSE AS plan_subject_to_qjsa,
         FALSE AS plan_mandates_loan_exhaustion,
         CAST('2026-01-01 00:00:00' AS TIMESTAMP) AS created_at
  UNION ALL
  SELECT '401k-qjsa', TRUE, FALSE, CAST('2026-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT '401k-loan-first', FALSE, TRUE, CAST('2026-01-01 00:00:00' AS TIMESTAMP)
) s;

INSERT INTO TABLE retirement_distributions.distribution_participant
SELECT * FROM (
  SELECT 'P-7001' AS participant_id, 'SINGLE' AS participant_marital_status,
         FALSE AS spousal_consent_verified,
         CAST('2026-01-01 00:00:00' AS TIMESTAMP) AS created_at
  UNION ALL
  SELECT 'P-7002', 'SINGLE', FALSE, CAST('2026-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT 'P-7003', 'SINGLE', FALSE, CAST('2026-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT 'P-7011', 'SINGLE', FALSE, CAST('2026-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT 'P-7012', 'SINGLE', FALSE, CAST('2026-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT 'P-7013', 'SINGLE', FALSE, CAST('2026-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT 'P-7014', 'MARRIED', FALSE, CAST('2026-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT 'P-7015', 'SINGLE', FALSE, CAST('2026-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT 'P-7016', 'SINGLE', FALSE, CAST('2026-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT 'P-7017', 'SINGLE', FALSE, CAST('2026-01-01 00:00:00' AS TIMESTAMP)
) s;

INSERT INTO TABLE retirement_distributions.distribution_request
SELECT * FROM (
  SELECT CAST(7011 AS BIGINT) AS distribution_request_id,
         'OPEN' AS request_status_code,
         'HARDSHIP' AS distribution_type_code,
         '401k-alpha' AS plan_id,
         'P-7011' AS participant_id,
         FALSE AS hold_or_aml_flag,
         CAST(5000.00 AS DECIMAL(18,2)) AS requested_amount,
         CAST('2026-04-01 09:00:00' AS TIMESTAMP) AS created_at
  UNION ALL
  SELECT 7012, 'OPEN', 'HARDSHIP', '401k-alpha', 'P-7012', FALSE,
         CAST(20000.00 AS DECIMAL(18,2)), CAST('2026-04-02 09:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT 7013, 'OPEN', 'HARDSHIP', '401k-alpha', 'P-7013', FALSE,
         CAST(3000.00 AS DECIMAL(18,2)), CAST('2026-04-03 09:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT 7014, 'OPEN', 'HARDSHIP', '401k-qjsa', 'P-7014', FALSE,
         CAST(4000.00 AS DECIMAL(18,2)), CAST('2026-04-04 09:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT 7015, 'OPEN', 'HARDSHIP', '401k-loan-first', 'P-7015', FALSE,
         CAST(6000.00 AS DECIMAL(18,2)), CAST('2026-04-05 09:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT 7016, 'OPEN', 'SECURE20_EMERGENCY', '401k-alpha', 'P-7016', FALSE,
         CAST(1500.00 AS DECIMAL(18,2)), CAST('2026-04-06 09:00:00' AS TIMESTAMP)
  UNION ALL
  SELECT 7017, 'OPEN', 'TERMINATION', '401k-alpha', 'P-7017', FALSE,
         CAST(10000.00 AS DECIMAL(18,2)), CAST('2026-04-07 09:00:00' AS TIMESTAMP)
) s;

INSERT INTO TABLE retirement_distributions.distribution_hardship
SELECT * FROM (
  SELECT CAST(7002 AS BIGINT) AS distribution_request_id,
         'MEDICAL' AS hardship_category,
         CAST(8000.00 AS DECIMAL(18,2)) AS documented_financial_need_amount,
         CAST(0.00 AS DECIMAL(18,2)) AS estimated_tax_withholding_amount,
         TRUE AS has_participant_self_certified,
         TRUE AS requires_substantiation_audit,
         CAST('2026-02-01 09:32:00' AS TIMESTAMP) AS created_at
  UNION ALL
  SELECT 7011, 'VACATION', CAST(5000.00 AS DECIMAL(18,2)), CAST(0.00 AS DECIMAL(18,2)),
         TRUE, FALSE, CAST('2026-04-01 09:05:00' AS TIMESTAMP)
  UNION ALL
  SELECT 7012, 'MEDICAL', CAST(5000.00 AS DECIMAL(18,2)), CAST(0.00 AS DECIMAL(18,2)),
         TRUE, FALSE, CAST('2026-04-02 09:05:00' AS TIMESTAMP)
  UNION ALL
  SELECT 7013, 'TUITION', CAST(3000.00 AS DECIMAL(18,2)), CAST(0.00 AS DECIMAL(18,2)),
         FALSE, FALSE, CAST('2026-04-03 09:05:00' AS TIMESTAMP)
  UNION ALL
  SELECT 7014, 'MEDICAL', CAST(4000.00 AS DECIMAL(18,2)), CAST(0.00 AS DECIMAL(18,2)),
         TRUE, FALSE, CAST('2026-04-04 09:05:00' AS TIMESTAMP)
  UNION ALL
  SELECT 7015, 'FUNERAL', CAST(6000.00 AS DECIMAL(18,2)), CAST(0.00 AS DECIMAL(18,2)),
         TRUE, FALSE, CAST('2026-04-05 09:05:00' AS TIMESTAMP)
) s;

INSERT INTO TABLE retirement_distributions.distribution_loan
SELECT * FROM (
  SELECT CAST(7015 AS BIGINT) AS distribution_request_id,
         CAST(5000.00 AS DECIMAL(18,2)) AS available_plan_loan_capacity,
         CAST(0.00 AS DECIMAL(18,2)) AS outstanding_loan_balance,
         CAST(50000.00 AS DECIMAL(18,2)) AS max_loan_amount,
         CAST('2026-04-05 09:06:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE retirement_distributions.distribution_qdro
SELECT * FROM (
  SELECT CAST(7701 AS BIGINT) AS qdro_id,
         CAST(7017 AS BIGINT) AS distribution_request_id,
         TRUE AS is_active,
         'ACTIVE' AS order_status_code,
         'Alternate Payee' AS alternate_payee_name,
         'Domestic relations order hold' AS hold_reason,
         CAST('2026-04-07 09:06:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE retirement_distributions.distribution_court_order
SELECT * FROM (
  SELECT CAST(7801 AS BIGINT) AS court_order_id,
         CAST(7017 AS BIGINT) AS distribution_request_id,
         '2026-DR-4412' AS docket_number,
         'PENDING' AS status_code,
         CAST('2026-04-07 09:07:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE retirement_distributions.distribution_emergency_ytd
SELECT * FROM (
  SELECT CAST(7016 AS BIGINT) AS distribution_request_id,
         CAST(2026 AS INT) AS tax_year,
         CAST(0 AS INT) AS prior_count,
         CAST('2026-04-06 09:06:00' AS TIMESTAMP) AS created_at
) s;
