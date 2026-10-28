-- =============================================================================
-- Additive seed: FNOL 88 (RECORD_ONLY garage scrape). Isolated from 401-404.
-- =============================================================================
-- Prerequisite: car_insurance_claims DDL + original seed already loaded, and
--               car_insurance_claims_fnol.sql (or iceberg.sql with FNOL tables).
-- Skip if already present:
--   SELECT fnol_id FROM car_insurance_claims.fnol WHERE fnol_id = 88;
-- Re-running will duplicate keys. Do not touch claim 401-404 rows.
--
-- Marcus Vance / PA-9018442-01 / RAV4 VIN 4T1B11HK5NU123456 /
-- collision deductible 1000 / estimated 450 / empty injuries and third parties.
-- =============================================================================

USE car_insurance_claims;

INSERT INTO TABLE car_insurance_claims.party
SELECT * FROM (
  SELECT CAST(15 AS BIGINT) AS party_id, 'PERSON' AS party_type_code, CAST('2026-01-10 10:00:00' AS TIMESTAMP) AS created_at, 'POLICY_ADMIN' AS source_system
) s;

INSERT INTO TABLE car_insurance_claims.person
SELECT * FROM (
  SELECT CAST(15 AS BIGINT) AS party_id, 'Marcus' AS first_name, 'Vance' AS last_name, CAST('1984-08-21' AS DATE) AS birth_date, 'M' AS gender_code, 'MARRIED' AS marital_status_code, 'marcus.vance@example.com' AS email_address, '+1-555-0188' AS phone_number, 2 AS customer_tenure_years, 0 AS prior_claims_count, FALSE AS prior_fraud_indicator, CAST('2026-01-10 10:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.party_postal_address
SELECT * FROM (
  SELECT CAST(1088 AS BIGINT) AS address_id, CAST(15 AS BIGINT) AS party_id, 'MAILING' AS address_type_code, '88 Willow Lane' AS street_line_1, CAST(NULL AS STRING) AS street_line_2, 'Springfield' AS city_name, 'IL' AS country_subdivision_code, '62704' AS postal_code, 'US' AS country_code, CAST('2026-01-10' AS DATE) AS valid_from_date, CAST(NULL AS DATE) AS valid_to_date, CAST('2026-01-10 10:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 1089, 15, 'GARAGING', '88 Willow Lane', NULL, 'Springfield', 'IL', '62704', 'US', CAST('2026-01-10' AS DATE), NULL, CAST('2026-01-10 10:00:00' AS TIMESTAMP)
) s;

INSERT INTO TABLE car_insurance_claims.geo_location
SELECT * FROM (
  SELECT CAST(588 AS BIGINT) AS location_id, 'LOSS_SCENE' AS location_type_code, 'Vance driveway garage scrape' AS location_name, '88 Willow Lane' AS street_line_1, CAST(NULL AS STRING) AS street_line_2, 'Springfield' AS city_name, 'IL' AS country_subdivision_code, '62704' AS postal_code, 'US' AS country_code, CAST(39.801200 AS DECIMAL(9,6)) AS latitude, CAST(-89.639400 AS DECIMAL(9,6)) AS longitude, CAST('2026-10-20 08:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.insurance_policy
SELECT * FROM (
  SELECT CAST(1088 AS BIGINT) AS policy_id, 'PA-9018442-01' AS policy_number, CAST(10 AS BIGINT) AS issuing_insurer_party_id, 'PERSONAL_AUTO' AS policy_type_code, 'ACTIVE' AS policy_status_code, CAST('2026-01-01' AS DATE) AS effective_date, CAST('2027-01-01' AS DATE) AS expiration_date, CAST(NULL AS DATE) AS cancellation_date, CAST(1260.00 AS DECIMAL(18,2)) AS annual_premium_amount, 'USD' AS premium_currency_code, CAST('2025-12-15 12:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.policy_party_role
SELECT * FROM (
  SELECT CAST(2088 AS BIGINT) AS policy_party_role_id, CAST(1088 AS BIGINT) AS policy_id, CAST(15 AS BIGINT) AS party_id, 'POLICYHOLDER' AS role_type_code, CAST('2026-01-01' AS DATE) AS effective_date, CAST(NULL AS DATE) AS expiration_date, TRUE AS is_primary_role, CAST('2025-12-15 12:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.policy_coverage
SELECT * FROM (
  SELECT CAST(3088 AS BIGINT) AS policy_coverage_id, CAST(1088 AS BIGINT) AS policy_id, CAST(1 AS BIGINT) AS coverage_id, CAST(1000.00 AS DECIMAL(18,2)) AS deductible_amount, CAST(NULL AS DECIMAL(18,2)) AS coverage_limit_amount, 'PER_OCCURRENCE' AS limit_basis_code, 'USD' AS currency_code, CAST('2026-01-01' AS DATE) AS effective_date, CAST(NULL AS DATE) AS expiration_date, TRUE AS is_active, CAST('2025-12-15 12:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 3089, 1088, 2, CAST(500.00 AS DECIMAL(18,2)), NULL, 'PER_OCCURRENCE', 'USD', CAST('2026-01-01' AS DATE), NULL, TRUE, CAST('2025-12-15 12:00:00' AS TIMESTAMP)
) s;

INSERT INTO TABLE car_insurance_claims.insurable_object
SELECT * FROM (
  SELECT CAST(288 AS BIGINT) AS insurable_object_id, 'VEHICLE' AS insurable_object_type_code, CAST('2026-01-10 10:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.vehicle
SELECT * FROM (
  SELECT CAST(288 AS BIGINT) AS insurable_object_id, '4T1B11HK5NU123456' AS vin, 'Toyota' AS make_name, 'RAV4' AS model_name, 2022 AS model_year, 'XLE' AS trim_name, 'IL-V0088' AS license_plate_number, 'IL' AS registration_country_subdivision_code, 'COMMUTE' AS primary_use_code, 9500 AS annual_mileage_amount, FALSE AS telematics_installed_indicator, CAST(24500.00 AS DECIMAL(18,2)) AS estimated_market_value_amount, 'USD' AS market_value_currency_code, CAST('2026-01-10 10:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.policy_insurable_object
SELECT * FROM (
  SELECT CAST(4088 AS BIGINT) AS policy_insurable_object_id, CAST(1088 AS BIGINT) AS policy_id, CAST(288 AS BIGINT) AS insurable_object_id, CAST('2026-01-01' AS DATE) AS effective_date, CAST(NULL AS DATE) AS expiration_date, CAST(1089 AS BIGINT) AS garaging_address_id, TRUE AS is_primary_vehicle, CAST('2025-12-15 12:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.driver
SELECT * FROM (
  SELECT CAST(588 AS BIGINT) AS driver_id, CAST(15 AS BIGINT) AS party_id, 'S8800888' AS license_number, 'IL' AS license_country_subdivision_code, 'US' AS license_country_code, 'VALID' AS license_status_code, 'D' AS license_class_code, CAST('2002-04-01' AS DATE) AS date_first_licensed, CAST('2026-01-10 10:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.policy_driver
SELECT * FROM (
  SELECT CAST(5188 AS BIGINT) AS policy_driver_id, CAST(1088 AS BIGINT) AS policy_id, CAST(588 AS BIGINT) AS driver_id, 'NAMED_INSURED' AS driver_relationship_code, TRUE AS is_primary_driver, FALSE AS is_excluded_driver, CAST('2026-01-01' AS DATE) AS effective_date, CAST(NULL AS DATE) AS expiration_date, CAST('2025-12-15 12:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.loss_event
SELECT * FROM (
  SELECT CAST(388 AS BIGINT) AS loss_event_id, CAST('2026-10-20 18:10:00' AS TIMESTAMP) AS loss_datetime, CAST('2026-10-20' AS DATE) AS loss_date, 'COLLISION' AS loss_cause_code, CAST(588 AS BIGINT) AS location_id, '62704' AS loss_location_postal_code, 'IL' AS loss_location_country_subdivision_code, 'Insured RAV4 scraped the garage door frame while backing in; cosmetic bumper scratch; no other vehicles or injuries.' AS loss_description, CAST('2026-10-20 19:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.loss_driver
SELECT * FROM (
  SELECT CAST(5288 AS BIGINT) AS loss_driver_id, CAST(388 AS BIGINT) AS loss_event_id, CAST(588 AS BIGINT) AS driver_id, CAST(NULL AS BIGINT) AS claim_id, CAST(288 AS BIGINT) AS insurable_object_id, 'INSURED_OPERATOR' AS driver_role_code, FALSE AS was_cited_indicator, FALSE AS impairment_suspected_indicator, CAST('2026-10-20 19:05:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.fnol
SELECT * FROM (
  SELECT CAST(88 AS BIGINT) AS fnol_id, 'FNOL-2026-00088' AS fnol_number, CAST('2026-10-20 19:00:00' AS TIMESTAMP) AS report_timestamp, 'POLICYHOLDER' AS reported_by_relationship, 'APP' AS intake_channel, 'RECORD_ONLY_NOTIFICATION' AS intake_purpose_code, CAST(1088 AS BIGINT) AS policy_id, CAST(288 AS BIGINT) AS insurable_object_id, CAST(388 AS BIGINT) AS loss_event_id, CAST(450.00 AS DECIMAL(18,2)) AS estimated_loss_amount, 'OPEN' AS triage_status_code, CAST(NULL AS BIGINT) AS claim_id, CAST(NULL AS STRING) AS run_id, CAST('2026-10-20 19:00:00' AS TIMESTAMP) AS created_at
) s;
