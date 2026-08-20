-- =============================================================================
-- Additive seed: claim 404 (deny path), isolated from 401
-- =============================================================================
-- Prerequisite : car_insurance_claims DDL + original seed (401/402/403) already
--                loaded. Skip this file if claim 404 already exists:
--                  SELECT claim_id FROM car_insurance_claims.claim WHERE claim_id = 404;
-- Re-running will duplicate keys.
--
-- Claim 404 uses its own policy PA-1003, vehicle, loss, police report, and
-- loss_driver. PD demo DELETEs on claim 401 do not change this snapshot.
-- Impairment starts FALSE; docs/deny-path-demo.md flips it.
--
-- Table is geo_location (Impala reserved word: location). If this lake was
-- created as location, rename once before the INSERT:
--   ALTER TABLE car_insurance_claims.`location` RENAME TO geo_location;
-- =============================================================================

USE car_insurance_claims;

INSERT INTO TABLE car_insurance_claims.geo_location
SELECT * FROM (
  SELECT CAST(504 AS BIGINT) AS location_id, 'LOSS_SCENE' AS location_type_code, 'Oak St utility pole' AS location_name, 'Oak Street near 2nd' AS street_line_1, CAST(NULL AS STRING) AS street_line_2, 'Springfield' AS city_name, 'IL' AS country_subdivision_code, '62701' AS postal_code, 'US' AS country_code, CAST(39.799400 AS DECIMAL(9,6)) AS latitude, CAST(-89.641800 AS DECIMAL(9,6)) AS longitude, CAST('2025-07-08 08:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.insurance_policy
SELECT * FROM (
  SELECT CAST(1003 AS BIGINT) AS policy_id, 'PA-1003' AS policy_number, CAST(10 AS BIGINT) AS issuing_insurer_party_id, 'PERSONAL_AUTO' AS policy_type_code, 'ACTIVE' AS policy_status_code, CAST('2025-01-01' AS DATE) AS effective_date, CAST('2026-01-01' AS DATE) AS expiration_date, CAST(NULL AS DATE) AS cancellation_date, CAST(980.00 AS DECIMAL(18,2)) AS annual_premium_amount, 'USD' AS premium_currency_code, CAST('2024-12-20 12:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.policy_party_role
SELECT * FROM (
  SELECT CAST(2004 AS BIGINT) AS policy_party_role_id, CAST(1003 AS BIGINT) AS policy_id, CAST(1 AS BIGINT) AS party_id, 'POLICYHOLDER' AS role_type_code, CAST('2025-01-01' AS DATE) AS effective_date, CAST(NULL AS DATE) AS expiration_date, TRUE AS is_primary_role, CAST('2024-12-20 12:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.policy_coverage
SELECT * FROM (
  SELECT CAST(3008 AS BIGINT) AS policy_coverage_id, CAST(1003 AS BIGINT) AS policy_id, CAST(1 AS BIGINT) AS coverage_id, CAST(500.00 AS DECIMAL(18,2)) AS deductible_amount, CAST(NULL AS DECIMAL(18,2)) AS coverage_limit_amount, 'PER_OCCURRENCE' AS limit_basis_code, 'USD' AS currency_code, CAST('2025-01-01' AS DATE) AS effective_date, CAST(NULL AS DATE) AS expiration_date, TRUE AS is_active, CAST('2024-12-20 12:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.insurable_object
SELECT * FROM (
  SELECT CAST(204 AS BIGINT) AS insurable_object_id, 'VEHICLE' AS insurable_object_type_code, CAST('2024-12-20 12:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.vehicle
SELECT * FROM (
  SELECT CAST(204 AS BIGINT) AS insurable_object_id, '1FMCU0G60NUB40404' AS vin, 'Ford' AS make_name, 'Escape' AS model_name, 2022 AS model_year, 'SE' AS trim_name, 'IL-C4040' AS license_plate_number, 'IL' AS registration_country_subdivision_code, 'COMMUTE' AS primary_use_code, 11000 AS annual_mileage_amount, FALSE AS telematics_installed_indicator, CAST(21000.00 AS DECIMAL(18,2)) AS estimated_market_value_amount, 'USD' AS market_value_currency_code, CAST('2024-12-20 12:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.policy_insurable_object
SELECT * FROM (
  SELECT CAST(4004 AS BIGINT) AS policy_insurable_object_id, CAST(1003 AS BIGINT) AS policy_id, CAST(204 AS BIGINT) AS insurable_object_id, CAST('2025-01-01' AS DATE) AS effective_date, CAST(NULL AS DATE) AS expiration_date, CAST(1002 AS BIGINT) AS garaging_address_id, TRUE AS is_primary_vehicle, CAST('2024-12-20 12:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.policy_driver
SELECT * FROM (
  SELECT CAST(5104 AS BIGINT) AS policy_driver_id, CAST(1003 AS BIGINT) AS policy_id, CAST(501 AS BIGINT) AS driver_id, 'NAMED_INSURED' AS driver_relationship_code, TRUE AS is_primary_driver, FALSE AS is_excluded_driver, CAST('2025-01-01' AS DATE) AS effective_date, CAST(NULL AS DATE) AS expiration_date, CAST('2024-12-20 12:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.loss_event
SELECT * FROM (
  SELECT CAST(303 AS BIGINT) AS loss_event_id, CAST('2025-07-08 21:20:00' AS TIMESTAMP) AS loss_datetime, CAST('2025-07-08' AS DATE) AS loss_date, 'COLLISION' AS loss_cause_code, CAST(504 AS BIGINT) AS location_id, '62701' AS loss_location_postal_code, 'IL' AS loss_location_country_subdivision_code, 'Insured Ford struck a utility pole on Oak Street; single-vehicle collision; operator statements pending.' AS loss_description, CAST('2025-07-08 22:05:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.claim
SELECT * FROM (
  SELECT CAST(404 AS BIGINT) AS claim_id, 'CLM-2025-000404' AS claim_number, CAST(303 AS BIGINT) AS loss_event_id, CAST(1003 AS BIGINT) AS policy_id, CAST(204 AS BIGINT) AS insurable_object_id, CAST(3008 AS BIGINT) AS policy_coverage_id, CAST('2025-07-08 22:05:00' AS TIMESTAMP) AS fnol_report_datetime, 'OPEN' AS claim_status_code, FALSE AS fraudulent_claim_indicator, FALSE AS litigation_indicator, FALSE AS subrogation_indicator, FALSE AS total_loss_indicator, CAST('2025-07-08 22:05:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.loss_driver
SELECT * FROM (
  SELECT CAST(5204 AS BIGINT) AS loss_driver_id, CAST(303 AS BIGINT) AS loss_event_id, CAST(501 AS BIGINT) AS driver_id, CAST(404 AS BIGINT) AS claim_id, CAST(204 AS BIGINT) AS insurable_object_id, 'INSURED_OPERATOR' AS driver_role_code, FALSE AS was_cited_indicator, FALSE AS impairment_suspected_indicator, CAST('2025-07-08 22:10:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.claim_party_role
SELECT * FROM (
  SELECT CAST(6010 AS BIGINT) AS claim_party_role_id, CAST(404 AS BIGINT) AS claim_id, CAST(1 AS BIGINT) AS party_id, 'INSURED' AS role_type_code, CAST('2025-07-08 22:05:00' AS TIMESTAMP) AS assigned_at, CAST(NULL AS TIMESTAMP) AS unassigned_at, TRUE AS is_current_assignment, CAST('2025-07-08 22:05:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 6011, 404, 4, 'ADJUSTER', CAST('2025-07-08 22:20:00' AS TIMESTAMP), NULL, TRUE, CAST('2025-07-08 22:20:00' AS TIMESTAMP)
) s;

INSERT INTO TABLE car_insurance_claims.claim_lifecycle
SELECT * FROM (
  SELECT CAST(7004 AS BIGINT) AS claim_lifecycle_id, CAST(404 AS BIGINT) AS claim_id, CAST('2025-07-08 22:05:00' AS TIMESTAMP) AS intake_datetime, CAST('2025-07-08 22:40:00' AS TIMESTAMP) AS triage_datetime, CAST(NULL AS TIMESTAMP) AS inspection_datetime, CAST(NULL AS TIMESTAMP) AS settlement_offer_datetime, CAST(NULL AS TIMESTAMP) AS closed_datetime, CAST(4 AS BIGINT) AS current_adjuster_party_id, CAST('2025-07-08 22:40:00' AS TIMESTAMP) AS last_updated_at
) s;

INSERT INTO TABLE car_insurance_claims.police_report
SELECT * FROM (
  SELECT CAST(5303 AS BIGINT) AS police_report_id, CAST(303 AS BIGINT) AS loss_event_id, CAST(404 AS BIGINT) AS claim_id, 'SPD-25-14044' AS report_number, 'Springfield Police Department' AS agency_name, CAST(12 AS BIGINT) AS agency_party_id, CAST('2025-07-08 21:40:00' AS TIMESTAMP) AS report_datetime, CAST('2025-07-08' AS DATE) AS report_date, CAST(504 AS BIGINT) AS location_id, FALSE AS citation_issued_indicator, 'Single-vehicle collision with a utility pole; no citation issued at scene.' AS narrative_summary, CAST('2025-07-09 08:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.fault_determination
SELECT * FROM (
  SELECT CAST(5403 AS BIGINT) AS fault_determination_id, CAST(404 AS BIGINT) AS claim_id, CAST(303 AS BIGINT) AS loss_event_id, CAST(501 AS BIGINT) AS at_fault_driver_id, CAST(1 AS BIGINT) AS at_fault_party_id, CAST(100.00 AS DECIMAL(5,2)) AS insured_fault_percent, CAST(0.00 AS DECIMAL(5,2)) AS adverse_fault_percent, 'POLICE' AS fault_basis_code, 'FINAL' AS determination_status_code, CAST('2025-07-09 10:00:00' AS TIMESTAMP) AS determination_datetime, 'Insured operator solely at fault; single-vehicle pole strike.' AS notes, CAST('2025-07-09 10:00:00' AS TIMESTAMP) AS created_at
) s;

INSERT INTO TABLE car_insurance_claims.claim_folder
SELECT * FROM (
  SELECT CAST(8104 AS BIGINT) AS claim_folder_id, CAST(404 AS BIGINT) AS claim_id, 'OPEN' AS folder_status_code, CAST('2025-07-08 22:05:00' AS TIMESTAMP) AS created_at, CAST(NULL AS TIMESTAMP) AS closed_at
) s;

INSERT INTO TABLE car_insurance_claims.claim_document
SELECT * FROM (
  SELECT CAST(8208 AS BIGINT) AS claim_document_id, CAST(8104 AS BIGINT) AS claim_folder_id, CAST(404 AS BIGINT) AS claim_id, 'FNOL' AS document_type_code, 'FNOL intake CLM-2025-000404' AS document_title, 'application/pdf' AS mime_type, 's3a://claims-docs/404/fnol.pdf' AS storage_uri, 'FNOL_APP' AS source_system, CAST('2025-07-08 22:06:00' AS TIMESTAMP) AS received_datetime, CAST('2025-07-08' AS DATE) AS received_date, CAST(NULL AS BIGINT) AS related_police_report_id, CAST(NULL AS BIGINT) AS related_damage_assessment_id, TRUE AS pii_indicator, CAST('2025-07-08 22:06:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 8209, 8104, 404, 'POLICE_REPORT', 'SPD-25-14044 scan', 'application/pdf', 's3a://claims-docs/404/police.pdf', 'ECM', CAST('2025-07-09 08:30:00' AS TIMESTAMP), CAST('2025-07-09' AS DATE), 5303, NULL, TRUE, CAST('2025-07-09 08:30:00' AS TIMESTAMP)
) s;

INSERT INTO TABLE car_insurance_claims.claim_lifecycle_event
SELECT * FROM (
  SELECT CAST(7113 AS BIGINT) AS claim_lifecycle_event_id, CAST(404 AS BIGINT) AS claim_id, 'INTAKE' AS event_type_code, CAST('2025-07-08 22:05:00' AS TIMESTAMP) AS event_datetime, CAST('2025-07-08' AS DATE) AS event_date, CAST(4 AS BIGINT) AS actor_party_id, CAST(NULL AS BIGINT) AS related_claim_offer_id, CAST(NULL AS BIGINT) AS related_claim_payment_id, CAST(NULL AS BIGINT) AS related_damage_assessment_id, 'FNOL intake completed' AS event_notes, CAST('2025-07-08 22:05:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 7114, 404, 'TRIAGE', CAST('2025-07-08 22:40:00' AS TIMESTAMP), CAST('2025-07-08' AS DATE), 4, NULL, NULL, NULL, 'Assigned collision; coverage review pending', CAST('2025-07-08 22:40:00' AS TIMESTAMP)
) s;
