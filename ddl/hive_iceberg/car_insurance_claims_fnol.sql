-- Additive FNOL tables for an already-loaded car_insurance_claims lake.
-- Notice grain is not a claim. Fresh full seed: tables are also in
-- car_insurance_claims_iceberg.sql. Seed row 88: car_insurance_claims_seed_fnol_88.sql.

USE car_insurance_claims;

CREATE TABLE IF NOT EXISTS car_insurance_claims.fnol (
  fnol_id                   BIGINT    COMMENT 'PK. Surrogate first-notice id (not a claim_id).',
  fnol_number               STRING    COMMENT 'Business key, e.g. FNOL-2026-00088.',
  report_timestamp          TIMESTAMP COMMENT 'When the notice was taken.',
  reported_by_relationship  STRING    COMMENT 'POLICYHOLDER | AGENT | OTHER.',
  intake_channel            STRING    COMMENT 'APP | PHONE | PORTAL.',
  intake_purpose_code       STRING    COMMENT 'RECORD_ONLY_NOTIFICATION | CLAIM_INTAKE.',
  policy_id                 BIGINT    COMMENT 'FK -> insurance_policy.policy_id.',
  insurable_object_id       BIGINT    COMMENT 'FK -> insurable_object / vehicle.',
  loss_event_id             BIGINT    COMMENT 'FK -> loss_event.loss_event_id.',
  estimated_loss_amount     DECIMAL(18,2) COMMENT 'Reporter estimate at notice; not a reserve.',
  triage_status_code        STRING    COMMENT 'OPEN | DENIED | INCIDENT_ONLY | ADJUSTER_REVIEW | CONVERTED.',
  claim_id                  BIGINT    COMMENT 'Nullable FK -> claim.claim_id after convert_fnol_to_claim.',
  run_id                    STRING    COMMENT 'Optional agent run that last wrote triage.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'First notice of loss. One notice file; not a claim until convert_fnol_to_claim.'
PARTITIONED BY SPEC (
  triage_status_code,
  YEAR(report_timestamp)
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'FirstNoticeOfLoss',
  'llm.primary_key' = 'fnol_id',
  'llm.business_key' = 'fnol_number',
  'llm.foreign_keys' = 'policy_id->insurance_policy.policy_id;insurable_object_id->insurable_object.insurable_object_id;loss_event_id->loss_event.loss_event_id;claim_id->claim.claim_id',
  'llm.grain' = 'one first-notice file (not a claim)'
);

CREATE TABLE IF NOT EXISTS car_insurance_claims.fnol_injury (
  fnol_injury_id            BIGINT    COMMENT 'PK. Surrogate injury reported at FNOL.',
  fnol_id                   BIGINT    COMMENT 'FK -> fnol.fnol_id.',
  party_id                  BIGINT    COMMENT 'Optional injured party.',
  injury_severity_code      STRING    COMMENT 'MINOR | MODERATE | SEVERE | UNKNOWN.',
  body_part_code            STRING    COMMENT 'Optional body-part code.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Injury reported on a notice before a claim exists (not claim_injury).'
PARTITIONED BY SPEC (
  YEAR(created_at)
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'FnolInjury',
  'llm.primary_key' = 'fnol_injury_id',
  'llm.foreign_keys' = 'fnol_id->fnol.fnol_id;party_id->party.party_id',
  'llm.grain' = 'one injury reported on a first notice'
);

CREATE TABLE IF NOT EXISTS car_insurance_claims.fnol_third_party_vehicle (
  fnol_third_party_vehicle_id BIGINT COMMENT 'PK. Surrogate third-party vehicle at FNOL.',
  fnol_id                   BIGINT    COMMENT 'FK -> fnol.fnol_id.',
  vin                       STRING    COMMENT 'Optional third-party VIN.',
  make_name                 STRING    COMMENT 'Optional make.',
  model_name                STRING    COMMENT 'Optional model.',
  license_plate_number      STRING    COMMENT 'Optional plate.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Third-party vehicle on a notice before a claim exists.'
PARTITIONED BY SPEC (
  YEAR(created_at)
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'FnolThirdPartyVehicle',
  'llm.primary_key' = 'fnol_third_party_vehicle_id',
  'llm.foreign_keys' = 'fnol_id->fnol.fnol_id',
  'llm.grain' = 'one third-party vehicle reported on a first notice'
);

INVALIDATE METADATA car_insurance_claims.fnol;
INVALIDATE METADATA car_insurance_claims.fnol_injury;
INVALIDATE METADATA car_insurance_claims.fnol_third_party_vehicle;
