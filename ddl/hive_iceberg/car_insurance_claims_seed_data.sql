-- =============================================================================
-- Car Insurance Claims — Seed INSERT data (Cloudera Hive / Iceberg)
-- =============================================================================
-- Prerequisite : ddl/hive_iceberg/car_insurance_claims_iceberg.sql applied
-- Database     : car_insurance_claims
--
-- PURPOSE
--   Populate every table with referentially consistent sample rows that exercise
--   1:1, 1:N, and association cardinalities used by the schema / OWL spine.
--
-- SCENARIO SUMMARY
--   Policy PA-1001 (ACTIVE): Policyholder John Smith (party 1), named insured /
--     spouse Jane Smith (party 2). Two listed drivers, two vehicles, five
--     coverages. Issuing carrier Acme Auto (party 10).
--   Loss 301 COLLISION (2025-06-15): John operating Honda; Jane injured passenger;
--     adverse driver Bob Reyes (party 3) at fault ~80%. Spawns two claims:
--       Claim 401 CLM-2025-000401 — PD / collision path (OPEN, subrogation)
--       Claim 402 CLM-2025-000402 — BI path (IN_LITIGATION)
--   Loss 302 THEFT (2024-11-02): Toyota stolen; single CLOSED claim 403.
--   Policy PA-1002 (EXPIRED): Prior policy for John (shows 1 party : N policies).
--
-- CARDINALITIES DEMONSTRATED
--   party 1──1 person|organization
--   party 1──* party_postal_address
--   party 1──* policy (via roles) ; insurance_policy 1──* policy_party_role
--   insurance_policy 1──* policy_coverage ; coverage 1──* policy_coverage
--   insurance_policy 1──* policy_insurable_object 1──1 vehicle
--   insurance_policy 1──* policy_driver ; driver 1──* policy_driver
--   loss_event 1──* claim ; loss_event 1──* loss_driver ; loss_event 0──1 location
--   claim 1──* (roles, lifecycle events, reserves, payments, docs, etc.)
--   claim_reserve 1──* components / transactions ; claim_folder 1──* documents
--   subrogation_case 1──* claim_recovery
--
-- LOAD NOTES
--   * Uses INSERT INTO ... SELECT ... UNION ALL for Hive portability.
--   * Re-running without truncate will duplicate keys — truncate or use a fresh DB.
--   * Timestamps are naive (no TZ); treat as UTC in analytics.
-- =============================================================================

USE car_insurance_claims;

-- Optional cleanup (uncomment for idempotent re-seed on empty-or-replace workflows)
-- TRUNCATE TABLE litigation_task;
-- TRUNCATE TABLE claim_lifecycle_event;
-- TRUNCATE TABLE fraud_assessment;
-- TRUNCATE TABLE litigation_case;
-- TRUNCATE TABLE claim_recovery;
-- TRUNCATE TABLE subrogation_case;
-- TRUNCATE TABLE other_insurance;
-- TRUNCATE TABLE claim_offer;
-- TRUNCATE TABLE claim_document;
-- TRUNCATE TABLE claim_folder;
-- TRUNCATE TABLE damage_assessment;
-- TRUNCATE TABLE claim_injury;
-- TRUNCATE TABLE fault_determination;
-- TRUNCATE TABLE police_report;
-- TRUNCATE TABLE loss_driver;
-- TRUNCATE TABLE repair_engagement;
-- TRUNCATE TABLE claim_payment;
-- TRUNCATE TABLE claim_reserve_transaction;
-- TRUNCATE TABLE claim_reserve_component;
-- TRUNCATE TABLE claim_reserve;
-- TRUNCATE TABLE claim_lifecycle;
-- TRUNCATE TABLE claim_party_role;
-- TRUNCATE TABLE claim;
-- TRUNCATE TABLE policy_driver;
-- TRUNCATE TABLE driver;
-- TRUNCATE TABLE policy_insurable_object;
-- TRUNCATE TABLE vehicle;
-- TRUNCATE TABLE insurable_object;
-- TRUNCATE TABLE policy_coverage;
-- TRUNCATE TABLE coverage;
-- TRUNCATE TABLE policy_party_role;
-- TRUNCATE TABLE insurance_policy;
-- TRUNCATE TABLE party_postal_address;
-- TRUNCATE TABLE organization;
-- TRUNCATE TABLE person;
-- TRUNCATE TABLE party;
-- TRUNCATE TABLE location;
-- TRUNCATE TABLE ref_code;
-- TRUNCATE TABLE ref_code_list;


-- =============================================================================
-- 1) REFERENCE DATA
-- =============================================================================

INSERT INTO TABLE car_insurance_claims.ref_code_list
SELECT * FROM (
  SELECT 'PARTY_TYPE'            AS code_list_id, 'Party type' AS code_list_name, 'Person vs organization discriminator' AS description, 'Master Data' AS owning_steward, TRUE AS is_acord_aligned, CAST('2024-01-01 00:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 'PARTY_ROLE_TYPE', 'Party role type', 'Roles on policies and claims', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'POLICY_STATUS', 'Policy status', 'Policy lifecycle status', 'Policy Admin', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'POLICY_TYPE', 'Policy type', 'Line of business / product type', 'Product', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'COVERAGE_TYPE', 'Coverage type', 'Auto coverage catalog codes', 'Product', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'CLAIM_STATUS', 'Claim status', 'Claim case status', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LOSS_CAUSE', 'Loss cause', 'Peril / cause of loss', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'RESERVE_TYPE', 'Reserve type', 'Loss and expense reserve components', 'Actuarial', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'RESERVE_STATUS', 'Reserve status', 'Reserve header status', 'Actuarial', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PAYMENT_CATEGORY', 'Payment category', 'Claim disbursement categories', 'Claims Finance', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PAYMENT_STATUS', 'Payment status', 'Disbursement status', 'Claims Finance', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PAYEE_TYPE', 'Payee type', 'Payment recipient classification', 'Claims Finance', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PRIMARY_USE', 'Vehicle primary use', 'Stated vehicle use', 'Underwriting', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'GENDER', 'Gender', 'Demographic gender code', 'Master Data', FALSE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'MARITAL_STATUS', 'Marital status', 'Demographic marital status', 'Master Data', FALSE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ADDRESS_TYPE', 'Address type', 'Postal address purpose', 'Master Data', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ORGANIZATION_TYPE', 'Organization type', 'Organization classification', 'Master Data', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LIMIT_BASIS', 'Limit basis', 'Coverage limit basis', 'Product', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ESTIMATE_STATUS', 'Estimate status', 'Repair estimate status', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'INSURABLE_OBJECT_TYPE', 'Insurable object type', 'OMG insurable object discriminator', 'Underwriting', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LOCATION_TYPE', 'Location type', 'Geographic location purpose', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LICENSE_STATUS', 'License status', 'Driver license status', 'Underwriting', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'DRIVER_RELATIONSHIP', 'Driver relationship', 'Driver relationship to insured', 'Underwriting', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'INJURY_SEVERITY', 'Injury severity', 'BI severity class', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'BODY_REGION', 'Body region', 'Injured body region', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ASSESSMENT_TYPE', 'Assessment type', 'Damage appraisal type', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'OFFER_STATUS', 'Offer status', 'Settlement offer status', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'SUBROGATION_STATUS', 'Subrogation status', 'Subrogation case status', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'RECOVERY_TYPE', 'Recovery type', 'Inbound recovery classification', 'Claims Finance', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LITIGATION_STATUS', 'Litigation status', 'Suit status', 'Legal', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'FRAUD_ASSESSMENT_OUTCOME', 'Fraud assessment outcome', 'SIU / fraud outcome', 'SIU', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'DOCUMENT_TYPE', 'Document type', 'Claim document classification', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'FAULT_BASIS', 'Fault basis', 'Basis for fault determination', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LIFECYCLE_EVENT_TYPE', 'Lifecycle event type', 'Claim process event types', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'OTHER_INSURANCE_TYPE', 'Other insurance type', 'Other/adverse insurance classification', 'Claims', TRUE, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.ref_code
SELECT * FROM (
  SELECT 'PARTY_TYPE' AS code_list_id, 'PERSON' AS code_value, 'Person' AS code_label, 'Natural person' AS description, TRUE AS is_active, 1 AS sort_order, CAST(NULL AS STRING) AS parent_code_value, CAST(NULL AS STRING) AS external_acord_code, CAST('2024-01-01 00:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 'PARTY_TYPE', 'ORGANIZATION', 'Organization', 'Legal organization', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PARTY_ROLE_TYPE', 'POLICYHOLDER', 'Policyholder', 'Primary policyholder', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PARTY_ROLE_TYPE', 'NAMED_INSURED', 'Named insured', 'Additional named insured', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PARTY_ROLE_TYPE', 'CLAIMANT', 'Claimant', 'Claim claimant', TRUE, 3, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PARTY_ROLE_TYPE', 'INSURED', 'Insured', 'Insured on claim', TRUE, 4, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PARTY_ROLE_TYPE', 'ADJUSTER', 'Adjuster', 'Claim adjuster', TRUE, 5, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PARTY_ROLE_TYPE', 'ATTORNEY', 'Attorney', 'Counsel on claim', TRUE, 6, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PARTY_ROLE_TYPE', 'ADVERSE_PARTY', 'Adverse party', 'Adverse party on loss', TRUE, 7, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'POLICY_STATUS', 'ACTIVE', 'Active', 'In-force policy', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'POLICY_STATUS', 'EXPIRED', 'Expired', 'Term ended', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'POLICY_TYPE', 'PERSONAL_AUTO', 'Personal auto', 'Personal auto line', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'COVERAGE_TYPE', 'COLLISION', 'Collision', 'Collision coverage', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'COVERAGE_TYPE', 'COMPREHENSIVE', 'Comprehensive', 'Other than collision', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'COVERAGE_TYPE', 'BI_LIABILITY', 'Bodily injury liability', 'BI liability', TRUE, 3, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'COVERAGE_TYPE', 'PD_LIABILITY', 'Property damage liability', 'PD liability', TRUE, 4, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'COVERAGE_TYPE', 'RENTAL', 'Rental reimbursement', 'Rental coverage', TRUE, 5, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'CLAIM_STATUS', 'OPEN', 'Open', 'Open claim', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'CLAIM_STATUS', 'CLOSED', 'Closed', 'Closed claim', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'CLAIM_STATUS', 'IN_LITIGATION', 'In litigation', 'Claim in suit', TRUE, 3, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LOSS_CAUSE', 'COLLISION', 'Collision', 'Vehicle collision', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LOSS_CAUSE', 'THEFT', 'Theft', 'Theft of vehicle', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'RESERVE_TYPE', 'LOSS_PD', 'Loss PD', 'Property damage loss reserve', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'RESERVE_TYPE', 'LOSS_BI', 'Loss BI', 'Bodily injury loss reserve', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'RESERVE_TYPE', 'EXPENSE_ADJUSTING', 'Adjusting expense', 'LAE adjusting expense reserve', TRUE, 3, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'RESERVE_TYPE', 'EXPENSE_LEGAL', 'Legal expense', 'Legal expense reserve', TRUE, 4, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'RESERVE_STATUS', 'OPEN', 'Open', 'Open reserve', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'RESERVE_STATUS', 'CLOSED', 'Closed', 'Closed reserve', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PAYMENT_CATEGORY', 'LOSS', 'Loss', 'Loss payment', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PAYMENT_CATEGORY', 'EXPENSE', 'Expense', 'Expense payment', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PAYMENT_CATEGORY', 'RENTAL', 'Rental', 'Rental payment', TRUE, 3, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PAYMENT_STATUS', 'ISSUED', 'Issued', 'Payment issued', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PAYMENT_STATUS', 'CLEARED', 'Cleared', 'Payment cleared', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PAYMENT_STATUS', 'PENDING', 'Pending', 'Payment pending', TRUE, 3, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PAYEE_TYPE', 'INSURED', 'Insured', 'Paid to insured', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PAYEE_TYPE', 'BODY_SHOP', 'Body shop', 'Paid to repair vendor', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PAYEE_TYPE', 'CLAIMANT', 'Claimant', 'Paid to claimant', TRUE, 3, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PAYEE_TYPE', 'ATTORNEY', 'Attorney', 'Paid to attorney', TRUE, 4, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PRIMARY_USE', 'COMMUTE', 'Commute', 'Commute use', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'PRIMARY_USE', 'PLEASURE', 'Pleasure', 'Pleasure use', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'GENDER', 'M', 'Male', 'Male', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'GENDER', 'F', 'Female', 'Female', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'MARITAL_STATUS', 'MARRIED', 'Married', 'Married', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'MARITAL_STATUS', 'SINGLE', 'Single', 'Single', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ADDRESS_TYPE', 'MAILING', 'Mailing', 'Mailing address', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ADDRESS_TYPE', 'GARAGING', 'Garaging', 'Garaging address', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ORGANIZATION_TYPE', 'REPAIR_VENDOR', 'Repair vendor', 'Body shop / repair', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ORGANIZATION_TYPE', 'INSURER', 'Insurer', 'Insurance carrier', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ORGANIZATION_TYPE', 'LAW_FIRM', 'Law firm', 'Law firm', TRUE, 3, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ORGANIZATION_TYPE', 'MEDICAL_PROVIDER', 'Medical provider', 'Medical provider', TRUE, 4, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ORGANIZATION_TYPE', 'GOVERNMENT', 'Government', 'Government agency', TRUE, 5, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LIMIT_BASIS', 'PER_OCCURRENCE', 'Per occurrence', 'Per occurrence limit', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LIMIT_BASIS', 'PER_PERSON', 'Per person', 'Per person limit', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LIMIT_BASIS', 'COMBINED_SINGLE_LIMIT', 'Combined single limit', 'CSL', TRUE, 3, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ESTIMATE_STATUS', 'APPROVED', 'Approved', 'Estimate approved', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ESTIMATE_STATUS', 'COMPLETED', 'Completed', 'Repair completed', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'INSURABLE_OBJECT_TYPE', 'VEHICLE', 'Vehicle', 'Motor vehicle', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LOCATION_TYPE', 'LOSS_SCENE', 'Loss scene', 'Scene of loss', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LOCATION_TYPE', 'GARAGING', 'Garaging', 'Garaging location', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LICENSE_STATUS', 'VALID', 'Valid', 'Valid license', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'DRIVER_RELATIONSHIP', 'NAMED_INSURED', 'Named insured', 'Named insured driver', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'DRIVER_RELATIONSHIP', 'SPOUSE', 'Spouse', 'Spouse driver', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'INJURY_SEVERITY', 'MODERATE', 'Moderate', 'Moderate injury', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'INJURY_SEVERITY', 'MINOR', 'Minor', 'Minor injury', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'BODY_REGION', 'NECK', 'Neck', 'Neck', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'BODY_REGION', 'BACK', 'Back', 'Back', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ASSESSMENT_TYPE', 'STAFF_APPRAISAL', 'Staff appraisal', 'Staff appraiser', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'ASSESSMENT_TYPE', 'INDEPENDENT_APPRAISAL', 'Independent appraisal', 'Independent appraiser', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'OFFER_STATUS', 'EXTENDED', 'Extended', 'Offer extended', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'OFFER_STATUS', 'ACCEPTED', 'Accepted', 'Offer accepted', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'OFFER_STATUS', 'REJECTED', 'Rejected', 'Offer rejected', TRUE, 3, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'SUBROGATION_STATUS', 'NEGOTIATING', 'Negotiating', 'In negotiation', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'SUBROGATION_STATUS', 'RECOVERED', 'Recovered', 'Fully/partially recovered', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'RECOVERY_TYPE', 'SUBROGATION', 'Subrogation', 'Subrogation recovery', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'RECOVERY_TYPE', 'SALVAGE', 'Salvage', 'Salvage proceeds', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LITIGATION_STATUS', 'IN_DISCOVERY', 'In discovery', 'Discovery phase', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'FRAUD_ASSESSMENT_OUTCOME', 'CLEARED', 'Cleared', 'No fraud substantiated', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'FRAUD_ASSESSMENT_OUTCOME', 'SUSPECTED', 'Suspected', 'Suspected fraud', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'DOCUMENT_TYPE', 'FNOL', 'FNOL', 'First notice of loss', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'DOCUMENT_TYPE', 'POLICE_REPORT', 'Police report', 'Police report scan', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'DOCUMENT_TYPE', 'PHOTO', 'Photo', 'Loss photo', TRUE, 3, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'DOCUMENT_TYPE', 'ESTIMATE', 'Estimate', 'Repair estimate', TRUE, 4, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'DOCUMENT_TYPE', 'MEDICAL', 'Medical', 'Medical record', TRUE, 5, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'FAULT_BASIS', 'POLICE', 'Police', 'Based on police report', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'FAULT_BASIS', 'ADJUSTER', 'Adjuster', 'Adjuster determination', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LIFECYCLE_EVENT_TYPE', 'INTAKE', 'Intake', 'Claim intake', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LIFECYCLE_EVENT_TYPE', 'TRIAGE', 'Triage', 'Claim triage', TRUE, 2, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LIFECYCLE_EVENT_TYPE', 'INSPECTION', 'Inspection', 'Vehicle inspection', TRUE, 3, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LIFECYCLE_EVENT_TYPE', 'OFFER', 'Offer', 'Settlement offer event', TRUE, 4, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LIFECYCLE_EVENT_TYPE', 'PAYMENT', 'Payment', 'Payment event', TRUE, 5, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LIFECYCLE_EVENT_TYPE', 'CLOSE', 'Close', 'Claim closed', TRUE, 6, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LIFECYCLE_EVENT_TYPE', 'SIU_REFERRAL', 'SIU referral', 'Referred to SIU', TRUE, 7, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'LIFECYCLE_EVENT_TYPE', 'SUIT_FILED', 'Suit filed', 'Litigation filed', TRUE, 8, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
  UNION ALL SELECT 'OTHER_INSURANCE_TYPE', 'ADVERSE_AUTO', 'Adverse auto', 'Adverse auto policy', TRUE, 1, NULL, NULL, CAST('2024-01-01 00:00:00' AS TIMESTAMP)
) s;


-- =============================================================================
-- 2) PARTIES (persons + organizations) AND ADDRESSES
-- =============================================================================
-- party_id: 1 John, 2 Jane, 3 Bob (adverse), 4 Alice Adjuster, 5 (unused spare),
--           6 Attorney Dana, 7 Metro Body Shop, 8 Peak Mutual (adverse carrier),
--           9 Rivers & Reed LLP, 10 Acme Auto (issuer), 11 CareFirst Clinic,
--           12 City PD, 13 SIU Sam, 14 Appraiser Eve

INSERT INTO TABLE car_insurance_claims.party
SELECT * FROM (
  SELECT CAST(1 AS BIGINT) AS party_id, 'PERSON' AS party_type_code, CAST('2020-03-15 10:00:00' AS TIMESTAMP) AS created_at, 'POLICY_ADMIN' AS source_system
  UNION ALL SELECT 2, 'PERSON', CAST('2020-03-15 10:00:00' AS TIMESTAMP), 'POLICY_ADMIN'
  UNION ALL SELECT 3, 'PERSON', CAST('2025-06-16 09:00:00' AS TIMESTAMP), 'CLAIMS'
  UNION ALL SELECT 4, 'PERSON', CAST('2019-01-01 08:00:00' AS TIMESTAMP), 'HR'
  UNION ALL SELECT 6, 'PERSON', CAST('2025-07-01 11:00:00' AS TIMESTAMP), 'CLAIMS'
  UNION ALL SELECT 7, 'ORGANIZATION', CAST('2018-06-01 08:00:00' AS TIMESTAMP), 'VENDOR_MASTER'
  UNION ALL SELECT 8, 'ORGANIZATION', CAST('2017-01-01 08:00:00' AS TIMESTAMP), 'CLAIMS'
  UNION ALL SELECT 9, 'ORGANIZATION', CAST('2016-01-01 08:00:00' AS TIMESTAMP), 'LEGAL'
  UNION ALL SELECT 10, 'ORGANIZATION', CAST('2010-01-01 08:00:00' AS TIMESTAMP), 'ORG_MASTER'
  UNION ALL SELECT 11, 'ORGANIZATION', CAST('2015-01-01 08:00:00' AS TIMESTAMP), 'CLAIMS'
  UNION ALL SELECT 12, 'ORGANIZATION', CAST('2010-01-01 08:00:00' AS TIMESTAMP), 'CLAIMS'
  UNION ALL SELECT 13, 'PERSON', CAST('2018-01-01 08:00:00' AS TIMESTAMP), 'HR'
  UNION ALL SELECT 14, 'PERSON', CAST('2019-06-01 08:00:00' AS TIMESTAMP), 'VENDOR_MASTER'
) s;


INSERT INTO TABLE car_insurance_claims.person
SELECT * FROM (
  SELECT CAST(1 AS BIGINT) AS party_id, 'John' AS first_name, 'Smith' AS last_name, CAST('1985-04-12' AS DATE) AS birth_date, 'M' AS gender_code, 'MARRIED' AS marital_status_code, 'john.smith@example.com' AS email_address, '+1-555-0101' AS phone_number, 5 AS customer_tenure_years, 1 AS prior_claims_count, FALSE AS prior_fraud_indicator, CAST('2020-03-15 10:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 2, 'Jane', 'Smith', CAST('1987-09-03' AS DATE), 'F', 'MARRIED', 'jane.smith@example.com', '+1-555-0102', 5, 0, FALSE, CAST('2020-03-15 10:00:00' AS TIMESTAMP)
  UNION ALL SELECT 3, 'Bob', 'Reyes', CAST('1990-01-22' AS DATE), 'M', 'SINGLE', 'bob.reyes@example.com', '+1-555-0144', CAST(NULL AS INT), CAST(NULL AS INT), FALSE, CAST('2025-06-16 09:00:00' AS TIMESTAMP)
  UNION ALL SELECT 4, 'Alice', 'Ng', CAST('1982-11-30' AS DATE), 'F', 'SINGLE', 'alice.ng@acmeauto.example', '+1-555-0200', CAST(NULL AS INT), CAST(NULL AS INT), FALSE, CAST('2019-01-01 08:00:00' AS TIMESTAMP)
  UNION ALL SELECT 6, 'Dana', 'Keller', CAST('1978-05-18' AS DATE), 'F', 'SINGLE', 'dkeller@riversreed.example', '+1-555-0300', CAST(NULL AS INT), CAST(NULL AS INT), FALSE, CAST('2025-07-01 11:00:00' AS TIMESTAMP)
  UNION ALL SELECT 13, 'Sam', 'Ortiz', CAST('1975-07-09' AS DATE), 'M', 'MARRIED', 'sam.ortiz@acmeauto.example', '+1-555-0201', CAST(NULL AS INT), CAST(NULL AS INT), FALSE, CAST('2018-01-01 08:00:00' AS TIMESTAMP)
  UNION ALL SELECT 14, 'Eve', 'Patel', CAST('1980-02-14' AS DATE), 'F', 'MARRIED', 'eve.patel@appraisepro.example', '+1-555-0400', CAST(NULL AS INT), CAST(NULL AS INT), FALSE, CAST('2019-06-01 08:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.organization
SELECT * FROM (
  SELECT CAST(7 AS BIGINT) AS party_id, 'Metro Collision Center LLC' AS legal_name, 'Metro Body Shop' AS trade_name, 'REPAIR_VENDOR' AS organization_type_code, '81-1111111' AS tax_identifier, CAST('2018-06-01 08:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 8, 'Peak Mutual Insurance Company', 'Peak Mutual', 'INSURER', '82-2222222', CAST('2017-01-01 08:00:00' AS TIMESTAMP)
  UNION ALL SELECT 9, 'Rivers & Reed LLP', 'Rivers & Reed', 'LAW_FIRM', '83-3333333', CAST('2016-01-01 08:00:00' AS TIMESTAMP)
  UNION ALL SELECT 10, 'Acme Auto Insurance Company', 'Acme Auto', 'INSURER', '84-4444444', CAST('2010-01-01 08:00:00' AS TIMESTAMP)
  UNION ALL SELECT 11, 'CareFirst Orthopedic Clinic PC', 'CareFirst Clinic', 'MEDICAL_PROVIDER', '85-5555555', CAST('2015-01-01 08:00:00' AS TIMESTAMP)
  UNION ALL SELECT 12, 'Springfield Police Department', 'Springfield PD', 'GOVERNMENT', CAST(NULL AS STRING), CAST('2010-01-01 08:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.party_postal_address
SELECT * FROM (
  SELECT CAST(1001 AS BIGINT) AS address_id, CAST(1 AS BIGINT) AS party_id, 'MAILING' AS address_type_code, '100 Oak Street' AS street_line_1, CAST(NULL AS STRING) AS street_line_2, 'Springfield' AS city_name, 'IL' AS country_subdivision_code, '62701' AS postal_code, 'US' AS country_code, CAST('2020-03-15' AS DATE) AS valid_from_date, CAST(NULL AS DATE) AS valid_to_date, CAST('2020-03-15 10:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 1002, 1, 'GARAGING', '100 Oak Street', NULL, 'Springfield', 'IL', '62701', 'US', CAST('2020-03-15' AS DATE), NULL, CAST('2020-03-15 10:00:00' AS TIMESTAMP)
  UNION ALL SELECT 1003, 2, 'MAILING', '100 Oak Street', NULL, 'Springfield', 'IL', '62701', 'US', CAST('2020-03-15' AS DATE), NULL, CAST('2020-03-15 10:00:00' AS TIMESTAMP)
  UNION ALL SELECT 1004, 7, 'MAILING', '500 Industrial Pkwy', 'Suite 2', 'Springfield', 'IL', '62703', 'US', CAST('2018-06-01' AS DATE), NULL, CAST('2018-06-01 08:00:00' AS TIMESTAMP)
  UNION ALL SELECT 1005, 3, 'MAILING', '88 Pine Ave', NULL, 'Springfield', 'IL', '62704', 'US', CAST('2025-06-16' AS DATE), NULL, CAST('2025-06-16 09:00:00' AS TIMESTAMP)
) s;


-- =============================================================================
-- 3) LOCATION, COVERAGE CATALOG, POLICIES, ROLES, POLICY COVERAGES
-- =============================================================================

INSERT INTO TABLE car_insurance_claims.location
SELECT * FROM (
  SELECT CAST(501 AS BIGINT) AS location_id, 'LOSS_SCENE' AS location_type_code, 'Main St & 5th Ave' AS location_name, 'Main St & 5th Ave' AS street_line_1, CAST(NULL AS STRING) AS street_line_2, 'Springfield' AS city_name, 'IL' AS country_subdivision_code, '62701' AS postal_code, 'US' AS country_code, CAST(39.781700 AS DECIMAL(9,6)) AS latitude, CAST(-89.650100 AS DECIMAL(9,6)) AS longitude, CAST('2025-06-15 08:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 502, 'LOSS_SCENE', 'Home driveway', '100 Oak Street', NULL, 'Springfield', 'IL', '62701', 'US', CAST(39.800100 AS DECIMAL(9,6)), CAST(-89.640200 AS DECIMAL(9,6)), CAST('2024-11-02 08:00:00' AS TIMESTAMP)
  UNION ALL SELECT 503, 'GARAGING', 'Smith garaging', '100 Oak Street', NULL, 'Springfield', 'IL', '62701', 'US', CAST(39.800100 AS DECIMAL(9,6)), CAST(-89.640200 AS DECIMAL(9,6)), CAST('2020-03-15 10:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.coverage
SELECT * FROM (
  SELECT CAST(1 AS BIGINT) AS coverage_id, 'COLLISION' AS coverage_type_code, 'Collision' AS coverage_name, 'Pays to repair/replace insured vehicle after collision' AS description, TRUE AS is_active
  UNION ALL SELECT 2, 'COMPREHENSIVE', 'Comprehensive', 'Other-than-collision physical damage', TRUE
  UNION ALL SELECT 3, 'BI_LIABILITY', 'Bodily injury liability', 'Liability for bodily injury to others', TRUE
  UNION ALL SELECT 4, 'PD_LIABILITY', 'Property damage liability', 'Liability for property damage to others', TRUE
  UNION ALL SELECT 5, 'RENTAL', 'Rental reimbursement', 'Rental car reimbursement', TRUE
) s;


INSERT INTO TABLE car_insurance_claims.insurance_policy
SELECT * FROM (
  SELECT CAST(1001 AS BIGINT) AS policy_id, 'PA-1001' AS policy_number, CAST(10 AS BIGINT) AS issuing_insurer_party_id, 'PERSONAL_AUTO' AS policy_type_code, 'ACTIVE' AS policy_status_code, CAST('2025-01-01' AS DATE) AS effective_date, CAST('2026-01-01' AS DATE) AS expiration_date, CAST(NULL AS DATE) AS cancellation_date, CAST(1480.00 AS DECIMAL(18,2)) AS annual_premium_amount, 'USD' AS premium_currency_code, CAST('2024-12-15 12:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 1002, 'PA-1002', 10, 'PERSONAL_AUTO', 'EXPIRED', CAST('2024-01-01' AS DATE), CAST('2025-01-01' AS DATE), NULL, CAST(1390.00 AS DECIMAL(18,2)), 'USD', CAST('2023-12-10 12:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.policy_party_role
SELECT * FROM (
  SELECT CAST(2001 AS BIGINT) AS policy_party_role_id, CAST(1001 AS BIGINT) AS policy_id, CAST(1 AS BIGINT) AS party_id, 'POLICYHOLDER' AS role_type_code, CAST('2025-01-01' AS DATE) AS effective_date, CAST(NULL AS DATE) AS expiration_date, TRUE AS is_primary_role, CAST('2024-12-15 12:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 2002, 1001, 2, 'NAMED_INSURED', CAST('2025-01-01' AS DATE), NULL, FALSE, CAST('2024-12-15 12:00:00' AS TIMESTAMP)
  UNION ALL SELECT 2003, 1002, 1, 'POLICYHOLDER', CAST('2024-01-01' AS DATE), CAST('2025-01-01' AS DATE), TRUE, CAST('2023-12-10 12:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.policy_coverage
SELECT * FROM (
  SELECT CAST(3001 AS BIGINT) AS policy_coverage_id, CAST(1001 AS BIGINT) AS policy_id, CAST(1 AS BIGINT) AS coverage_id, CAST(500.00 AS DECIMAL(18,2)) AS deductible_amount, CAST(NULL AS DECIMAL(18,2)) AS coverage_limit_amount, 'PER_OCCURRENCE' AS limit_basis_code, 'USD' AS currency_code, CAST('2025-01-01' AS DATE) AS effective_date, CAST(NULL AS DATE) AS expiration_date, TRUE AS is_active, CAST('2024-12-15 12:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 3002, 1001, 2, CAST(250.00 AS DECIMAL(18,2)), NULL, 'PER_OCCURRENCE', 'USD', CAST('2025-01-01' AS DATE), NULL, TRUE, CAST('2024-12-15 12:00:00' AS TIMESTAMP)
  UNION ALL SELECT 3003, 1001, 3, CAST(0.00 AS DECIMAL(18,2)), CAST(100000.00 AS DECIMAL(18,2)), 'PER_PERSON', 'USD', CAST('2025-01-01' AS DATE), NULL, TRUE, CAST('2024-12-15 12:00:00' AS TIMESTAMP)
  UNION ALL SELECT 3004, 1001, 4, CAST(0.00 AS DECIMAL(18,2)), CAST(50000.00 AS DECIMAL(18,2)), 'PER_OCCURRENCE', 'USD', CAST('2025-01-01' AS DATE), NULL, TRUE, CAST('2024-12-15 12:00:00' AS TIMESTAMP)
  UNION ALL SELECT 3005, 1001, 5, CAST(0.00 AS DECIMAL(18,2)), CAST(40.00 AS DECIMAL(18,2)), 'PER_OCCURRENCE', 'USD', CAST('2025-01-01' AS DATE), NULL, TRUE, CAST('2024-12-15 12:00:00' AS TIMESTAMP)
  UNION ALL SELECT 3006, 1002, 1, CAST(500.00 AS DECIMAL(18,2)), NULL, 'PER_OCCURRENCE', 'USD', CAST('2024-01-01' AS DATE), CAST('2025-01-01' AS DATE), FALSE, CAST('2023-12-10 12:00:00' AS TIMESTAMP)
  UNION ALL SELECT 3007, 1002, 2, CAST(250.00 AS DECIMAL(18,2)), NULL, 'PER_OCCURRENCE', 'USD', CAST('2024-01-01' AS DATE), CAST('2025-01-01' AS DATE), FALSE, CAST('2023-12-10 12:00:00' AS TIMESTAMP)
) s;


-- =============================================================================
-- 4) VEHICLES / INSURABLE OBJECTS / POLICY LINKS / DRIVERS
-- =============================================================================
-- 201 Honda (PA-1001 primary), 202 Toyota (PA-1001 + theft loss), 203 adverse Chevy (not on policy)

INSERT INTO TABLE car_insurance_claims.insurable_object
SELECT * FROM (
  SELECT CAST(201 AS BIGINT) AS insurable_object_id, 'VEHICLE' AS insurable_object_type_code, CAST('2020-03-15 10:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 202, 'VEHICLE', CAST('2021-05-01 10:00:00' AS TIMESTAMP)
  UNION ALL SELECT 203, 'VEHICLE', CAST('2025-06-16 09:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.vehicle
SELECT * FROM (
  SELECT CAST(201 AS BIGINT) AS insurable_object_id, '1HGBH41JXMN109186' AS vin, 'Honda' AS make_name, 'Accord' AS model_name, 2021 AS model_year, 'EX' AS trim_name, 'IL-A1001' AS license_plate_number, 'IL' AS registration_country_subdivision_code, 'COMMUTE' AS primary_use_code, 12000 AS annual_mileage_amount, TRUE AS telematics_installed_indicator, CAST(22000.00 AS DECIMAL(18,2)) AS estimated_market_value_amount, 'USD' AS market_value_currency_code, CAST('2020-03-15 10:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 202, '4T1BF1FK5CU123456', 'Toyota', 'Camry', 2020, 'LE', 'IL-B2002', 'IL', 'PLEASURE', 9000, FALSE, CAST(18000.00 AS DECIMAL(18,2)), 'USD', CAST('2021-05-01 10:00:00' AS TIMESTAMP)
  UNION ALL SELECT 203, '1G1ZD5ST1MF012345', 'Chevrolet', 'Malibu', 2022, 'LT', 'IL-Z9999', 'IL', 'COMMUTE', CAST(NULL AS INT), FALSE, CAST(19500.00 AS DECIMAL(18,2)), 'USD', CAST('2025-06-16 09:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.policy_insurable_object
SELECT * FROM (
  SELECT CAST(4001 AS BIGINT) AS policy_insurable_object_id, CAST(1001 AS BIGINT) AS policy_id, CAST(201 AS BIGINT) AS insurable_object_id, CAST('2025-01-01' AS DATE) AS effective_date, CAST(NULL AS DATE) AS expiration_date, CAST(1002 AS BIGINT) AS garaging_address_id, TRUE AS is_primary_vehicle, CAST('2024-12-15 12:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 4002, 1001, 202, CAST('2025-01-01' AS DATE), NULL, 1002, FALSE, CAST('2024-12-15 12:00:00' AS TIMESTAMP)
  UNION ALL SELECT 4003, 1002, 201, CAST('2024-01-01' AS DATE), CAST('2025-01-01' AS DATE), 1002, TRUE, CAST('2023-12-10 12:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.driver
SELECT * FROM (
  SELECT CAST(501 AS BIGINT) AS driver_id, CAST(1 AS BIGINT) AS party_id, 'S1234567' AS license_number, 'IL' AS license_country_subdivision_code, 'US' AS license_country_code, 'VALID' AS license_status_code, 'D' AS license_class_code, CAST('2003-06-01' AS DATE) AS date_first_licensed, CAST('2020-03-15 10:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 502, 2, 'S7654321', 'IL', 'US', 'VALID', 'D', CAST('2005-08-15' AS DATE), CAST('2020-03-15 10:00:00' AS TIMESTAMP)
  UNION ALL SELECT 503, 3, 'S9988776', 'IL', 'US', 'VALID', 'D', CAST('2008-01-10' AS DATE), CAST('2025-06-16 09:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.policy_driver
SELECT * FROM (
  SELECT CAST(5101 AS BIGINT) AS policy_driver_id, CAST(1001 AS BIGINT) AS policy_id, CAST(501 AS BIGINT) AS driver_id, 'NAMED_INSURED' AS driver_relationship_code, TRUE AS is_primary_driver, FALSE AS is_excluded_driver, CAST('2025-01-01' AS DATE) AS effective_date, CAST(NULL AS DATE) AS expiration_date, CAST('2024-12-15 12:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 5102, 1001, 502, 'SPOUSE', FALSE, FALSE, CAST('2025-01-01' AS DATE), NULL, CAST('2024-12-15 12:00:00' AS TIMESTAMP)
  UNION ALL SELECT 5103, 1002, 501, 'NAMED_INSURED', TRUE, FALSE, CAST('2024-01-01' AS DATE), CAST('2025-01-01' AS DATE), CAST('2023-12-10 12:00:00' AS TIMESTAMP)
) s;


-- =============================================================================
-- 5) LOSS EVENTS, LOSS DRIVERS, CLAIMS
-- =============================================================================

INSERT INTO TABLE car_insurance_claims.loss_event
SELECT * FROM (
  SELECT CAST(301 AS BIGINT) AS loss_event_id, CAST('2025-06-15 17:42:00' AS TIMESTAMP) AS loss_datetime, CAST('2025-06-15' AS DATE) AS loss_date, 'COLLISION' AS loss_cause_code, CAST(501 AS BIGINT) AS location_id, '62701' AS loss_location_postal_code, 'IL' AS loss_location_country_subdivision_code, 'Insured Honda struck in rear by adverse Chevy at Main & 5th; passenger Jane reports neck/back pain.' AS loss_description, CAST('2025-06-15 19:05:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 302, CAST('2024-11-02 22:15:00' AS TIMESTAMP), CAST('2024-11-02' AS DATE), 'THEFT', 502, '62701', 'IL', 'Toyota Camry stolen from driveway overnight; recovered burned total loss later.', CAST('2024-11-03 08:30:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.claim
SELECT * FROM (
  SELECT CAST(401 AS BIGINT) AS claim_id, 'CLM-2025-000401' AS claim_number, CAST(301 AS BIGINT) AS loss_event_id, CAST(1001 AS BIGINT) AS policy_id, CAST(201 AS BIGINT) AS insurable_object_id, CAST(3001 AS BIGINT) AS policy_coverage_id, CAST('2025-06-15 19:05:00' AS TIMESTAMP) AS fnol_report_datetime, 'OPEN' AS claim_status_code, FALSE AS fraudulent_claim_indicator, FALSE AS litigation_indicator, TRUE AS subrogation_indicator, FALSE AS total_loss_indicator, CAST('2025-06-15 19:05:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 402, 'CLM-2025-000402', 301, 1001, 201, 3003, CAST('2025-06-15 19:20:00' AS TIMESTAMP), 'IN_LITIGATION', FALSE, TRUE, FALSE, FALSE, CAST('2025-06-15 19:20:00' AS TIMESTAMP)
  UNION ALL SELECT 403, 'CLM-2024-000403', 302, 1001, 202, 3002, CAST('2024-11-03 08:30:00' AS TIMESTAMP), 'CLOSED', FALSE, FALSE, FALSE, TRUE, CAST('2024-11-03 08:30:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.loss_driver
SELECT * FROM (
  SELECT CAST(5201 AS BIGINT) AS loss_driver_id, CAST(301 AS BIGINT) AS loss_event_id, CAST(501 AS BIGINT) AS driver_id, CAST(401 AS BIGINT) AS claim_id, CAST(201 AS BIGINT) AS insurable_object_id, 'INSURED_OPERATOR' AS driver_role_code, FALSE AS was_cited_indicator, FALSE AS impairment_suspected_indicator, CAST('2025-06-15 19:10:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 5202, 301, 503, 401, 203, 'ADVERSE_OPERATOR', TRUE, FALSE, CAST('2025-06-16 09:15:00' AS TIMESTAMP)
  UNION ALL SELECT 5203, 302, 501, 403, 202, 'INSURED_OPERATOR', FALSE, FALSE, CAST('2024-11-03 08:35:00' AS TIMESTAMP)
) s;


-- =============================================================================
-- 6) CLAIM ROLES, LIFECYCLE (wide + events)
-- =============================================================================

INSERT INTO TABLE car_insurance_claims.claim_party_role
SELECT * FROM (
  SELECT CAST(6001 AS BIGINT) AS claim_party_role_id, CAST(401 AS BIGINT) AS claim_id, CAST(1 AS BIGINT) AS party_id, 'INSURED' AS role_type_code, CAST('2025-06-15 19:05:00' AS TIMESTAMP) AS assigned_at, CAST(NULL AS TIMESTAMP) AS unassigned_at, TRUE AS is_current_assignment, CAST('2025-06-15 19:05:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 6002, 401, 4, 'ADJUSTER', CAST('2025-06-15 19:30:00' AS TIMESTAMP), NULL, TRUE, CAST('2025-06-15 19:30:00' AS TIMESTAMP)
  UNION ALL SELECT 6003, 401, 3, 'ADVERSE_PARTY', CAST('2025-06-16 09:00:00' AS TIMESTAMP), NULL, TRUE, CAST('2025-06-16 09:00:00' AS TIMESTAMP)
  UNION ALL SELECT 6004, 402, 2, 'CLAIMANT', CAST('2025-06-15 19:20:00' AS TIMESTAMP), NULL, TRUE, CAST('2025-06-15 19:20:00' AS TIMESTAMP)
  UNION ALL SELECT 6005, 402, 4, 'ADJUSTER', CAST('2025-06-15 19:35:00' AS TIMESTAMP), NULL, TRUE, CAST('2025-06-15 19:35:00' AS TIMESTAMP)
  UNION ALL SELECT 6006, 402, 6, 'ATTORNEY', CAST('2025-07-01 11:00:00' AS TIMESTAMP), NULL, TRUE, CAST('2025-07-01 11:00:00' AS TIMESTAMP)
  UNION ALL SELECT 6007, 403, 1, 'INSURED', CAST('2024-11-03 08:30:00' AS TIMESTAMP), NULL, TRUE, CAST('2024-11-03 08:30:00' AS TIMESTAMP)
  UNION ALL SELECT 6008, 403, 4, 'ADJUSTER', CAST('2024-11-03 09:00:00' AS TIMESTAMP), CAST('2024-12-01 17:00:00' AS TIMESTAMP), FALSE, CAST('2024-11-03 09:00:00' AS TIMESTAMP)
  UNION ALL SELECT 6009, 403, 4, 'ADJUSTER', CAST('2024-11-03 09:00:00' AS TIMESTAMP), NULL, TRUE, CAST('2024-11-03 09:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.claim_lifecycle
SELECT * FROM (
  SELECT CAST(7001 AS BIGINT) AS claim_lifecycle_id, CAST(401 AS BIGINT) AS claim_id, CAST('2025-06-15 19:05:00' AS TIMESTAMP) AS intake_datetime, CAST('2025-06-15 20:00:00' AS TIMESTAMP) AS triage_datetime, CAST('2025-06-17 14:00:00' AS TIMESTAMP) AS inspection_datetime, CAST('2025-07-10 16:00:00' AS TIMESTAMP) AS settlement_offer_datetime, CAST(NULL AS TIMESTAMP) AS closed_datetime, CAST(4 AS BIGINT) AS current_adjuster_party_id, CAST('2025-07-10 16:00:00' AS TIMESTAMP) AS last_updated_at
  UNION ALL SELECT 7002, 402, CAST('2025-06-15 19:20:00' AS TIMESTAMP), CAST('2025-06-15 20:15:00' AS TIMESTAMP), CAST(NULL AS TIMESTAMP), CAST('2025-07-20 10:00:00' AS TIMESTAMP), NULL, 4, CAST('2025-08-01 09:00:00' AS TIMESTAMP)
  UNION ALL SELECT 7003, 403, CAST('2024-11-03 08:30:00' AS TIMESTAMP), CAST('2024-11-03 09:15:00' AS TIMESTAMP), CAST('2024-11-05 11:00:00' AS TIMESTAMP), CAST('2024-11-20 15:00:00' AS TIMESTAMP), CAST('2024-12-01 17:00:00' AS TIMESTAMP), 4, CAST('2024-12-01 17:00:00' AS TIMESTAMP)
) s;


-- =============================================================================
-- 7) POLICE, FAULT, INJURY, DAMAGE ASSESSMENT
-- =============================================================================

INSERT INTO TABLE car_insurance_claims.police_report
SELECT * FROM (
  SELECT CAST(5301 AS BIGINT) AS police_report_id, CAST(301 AS BIGINT) AS loss_event_id, CAST(401 AS BIGINT) AS claim_id, 'SPD-25-11887' AS report_number, 'Springfield Police Department' AS agency_name, CAST(12 AS BIGINT) AS agency_party_id, CAST('2025-06-15 18:10:00' AS TIMESTAMP) AS report_datetime, CAST('2025-06-15' AS DATE) AS report_date, CAST(501 AS BIGINT) AS location_id, TRUE AS citation_issued_indicator, 'Unit 2 cited for failure to reduce speed; rear-end collision.' AS narrative_summary, CAST('2025-06-16 08:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 5302, 302, 403, 'SPD-24-99012', 'Springfield Police Department', 12, CAST('2024-11-03 07:45:00' AS TIMESTAMP), CAST('2024-11-03' AS DATE), 502, FALSE, 'Theft report taken; vehicle entered NCIC.', CAST('2024-11-03 09:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.fault_determination
SELECT * FROM (
  SELECT CAST(5401 AS BIGINT) AS fault_determination_id, CAST(401 AS BIGINT) AS claim_id, CAST(301 AS BIGINT) AS loss_event_id, CAST(503 AS BIGINT) AS at_fault_driver_id, CAST(3 AS BIGINT) AS at_fault_party_id, CAST(20.00 AS DECIMAL(5,2)) AS insured_fault_percent, CAST(80.00 AS DECIMAL(5,2)) AS adverse_fault_percent, 'POLICE' AS fault_basis_code, 'FINAL' AS determination_status_code, CAST('2025-06-18 10:00:00' AS TIMESTAMP) AS determination_datetime, 'Final liability: adverse primarily at fault based on police report and photos.' AS notes, CAST('2025-06-18 10:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 5402, 402, 301, 503, 3, CAST(20.00 AS DECIMAL(5,2)), CAST(80.00 AS DECIMAL(5,2)), 'ADJUSTER', 'FINAL', CAST('2025-06-18 10:05:00' AS TIMESTAMP), 'Same loss liability adopted for BI claim.', CAST('2025-06-18 10:05:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.claim_injury
SELECT * FROM (
  SELECT CAST(5501 AS BIGINT) AS claim_injury_id, CAST(402 AS BIGINT) AS claim_id, CAST(2 AS BIGINT) AS injured_party_id, 'MODERATE' AS injury_severity_code, 'NECK' AS body_region_code, 'Cervical strain; physical therapy prescribed.' AS injury_description, CAST(11 AS BIGINT) AS medical_provider_party_id, CAST('2025-06-16' AS DATE) AS treatment_start_date, CAST(NULL AS DATE) AS treatment_end_date, FALSE AS ambulance_used_indicator, FALSE AS hospitalization_indicator, CAST('2025-06-16 12:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 5502, 402, 2, 'MINOR', 'BACK', 'Lumbar soreness secondary to collision.', 11, CAST('2025-06-16' AS DATE), NULL, FALSE, FALSE, CAST('2025-06-16 12:05:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.damage_assessment
SELECT * FROM (
  SELECT CAST(8001 AS BIGINT) AS damage_assessment_id, CAST(401 AS BIGINT) AS claim_id, CAST(201 AS BIGINT) AS insurable_object_id, CAST(14 AS BIGINT) AS assessor_party_id, 'STAFF_APPRAISAL' AS assessment_type_code, CAST('2025-06-17 14:00:00' AS TIMESTAMP) AS assessment_datetime, CAST('2025-06-17' AS DATE) AS assessment_date, CAST(4850.00 AS DECIMAL(18,2)) AS estimated_repair_amount, CAST(22000.00 AS DECIMAL(18,2)) AS actual_cash_value_amount, FALSE AS total_loss_indicator, 'USD' AS currency_code, 'Rear bumper, trunk lid, sensors.' AS assessment_notes, CAST('2025-06-17 15:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 8002, 401, 201, 14, 'INDEPENDENT_APPRAISAL', CAST('2025-06-25 11:00:00' AS TIMESTAMP), CAST('2025-06-25' AS DATE), CAST(5100.00 AS DECIMAL(18,2)), CAST(22000.00 AS DECIMAL(18,2)), FALSE, 'USD', 'Supplement for ADAS calibration.', CAST('2025-06-25 12:00:00' AS TIMESTAMP)
  UNION ALL SELECT 8003, 403, 202, 14, 'STAFF_APPRAISAL', CAST('2024-11-05 11:00:00' AS TIMESTAMP), CAST('2024-11-05' AS DATE), CAST(0.00 AS DECIMAL(18,2)), CAST(17500.00 AS DECIMAL(18,2)), TRUE, 'USD', 'Recovered burned; total loss ACV 17500.', CAST('2024-11-05 12:00:00' AS TIMESTAMP)
) s;


-- =============================================================================
-- 8) FOLDER / DOCUMENTS
-- =============================================================================

INSERT INTO TABLE car_insurance_claims.claim_folder
SELECT * FROM (
  SELECT CAST(8101 AS BIGINT) AS claim_folder_id, CAST(401 AS BIGINT) AS claim_id, 'OPEN' AS folder_status_code, CAST('2025-06-15 19:05:00' AS TIMESTAMP) AS created_at, CAST(NULL AS TIMESTAMP) AS closed_at
  UNION ALL SELECT 8102, 402, 'OPEN', CAST('2025-06-15 19:20:00' AS TIMESTAMP), NULL
  UNION ALL SELECT 8103, 403, 'ARCHIVED', CAST('2024-11-03 08:30:00' AS TIMESTAMP), CAST('2024-12-01 17:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.claim_document
SELECT * FROM (
  SELECT CAST(8201 AS BIGINT) AS claim_document_id, CAST(8101 AS BIGINT) AS claim_folder_id, CAST(401 AS BIGINT) AS claim_id, 'FNOL' AS document_type_code, 'FNOL intake CLM-2025-000401' AS document_title, 'application/pdf' AS mime_type, 's3a://claims-docs/401/fnol.pdf' AS storage_uri, 'FNOL_APP' AS source_system, CAST('2025-06-15 19:06:00' AS TIMESTAMP) AS received_datetime, CAST('2025-06-15' AS DATE) AS received_date, CAST(NULL AS BIGINT) AS related_police_report_id, CAST(NULL AS BIGINT) AS related_damage_assessment_id, TRUE AS pii_indicator, CAST('2025-06-15 19:06:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 8202, 8101, 401, 'POLICE_REPORT', 'SPD-25-11887 scan', 'application/pdf', 's3a://claims-docs/401/police.pdf', 'ECM', CAST('2025-06-16 08:30:00' AS TIMESTAMP), CAST('2025-06-16' AS DATE), 5301, NULL, TRUE, CAST('2025-06-16 08:30:00' AS TIMESTAMP)
  UNION ALL SELECT 8203, 8101, 401, 'PHOTO', 'Rear damage photo 1', 'image/jpeg', 's3a://claims-docs/401/photo1.jpg', 'MOBILE_APP', CAST('2025-06-15 19:40:00' AS TIMESTAMP), CAST('2025-06-15' AS DATE), NULL, NULL, FALSE, CAST('2025-06-15 19:40:00' AS TIMESTAMP)
  UNION ALL SELECT 8204, 8101, 401, 'ESTIMATE', 'Metro estimate', 'application/pdf', 's3a://claims-docs/401/estimate.pdf', 'ECM', CAST('2025-06-18 10:00:00' AS TIMESTAMP), CAST('2025-06-18' AS DATE), NULL, 8001, FALSE, CAST('2025-06-18 10:00:00' AS TIMESTAMP)
  UNION ALL SELECT 8205, 8102, 402, 'MEDICAL', 'CareFirst initial eval', 'application/pdf', 's3a://claims-docs/402/medical1.pdf', 'ECM', CAST('2025-06-20 09:00:00' AS TIMESTAMP), CAST('2025-06-20' AS DATE), NULL, NULL, TRUE, CAST('2025-06-20 09:00:00' AS TIMESTAMP)
  UNION ALL SELECT 8206, 8103, 403, 'FNOL', 'FNOL theft CLM-2024-000403', 'application/pdf', 's3a://claims-docs/403/fnol.pdf', 'FNOL_APP', CAST('2024-11-03 08:31:00' AS TIMESTAMP), CAST('2024-11-03' AS DATE), NULL, NULL, TRUE, CAST('2024-11-03 08:31:00' AS TIMESTAMP)
  UNION ALL SELECT 8207, 8103, 403, 'POLICE_REPORT', 'SPD-24-99012 scan', 'application/pdf', 's3a://claims-docs/403/police.pdf', 'ECM', CAST('2024-11-03 10:00:00' AS TIMESTAMP), CAST('2024-11-03' AS DATE), 5302, NULL, TRUE, CAST('2024-11-03 10:00:00' AS TIMESTAMP)
) s;


-- =============================================================================
-- 9) RESERVES, PAYMENTS, REPAIR
-- =============================================================================

INSERT INTO TABLE car_insurance_claims.claim_reserve
SELECT * FROM (
  SELECT CAST(8301 AS BIGINT) AS claim_reserve_id, CAST(401 AS BIGINT) AS claim_id, 'OPEN' AS reserve_status_code, 'USD' AS currency_code, CAST(4500.00 AS DECIMAL(18,2)) AS initial_loss_reserve_amount, CAST(5600.00 AS DECIMAL(18,2)) AS revised_reserve_total_amount, TRUE AS is_current, CAST('2025-07-01 09:00:00' AS TIMESTAMP) AS last_updated_at, CAST('2025-06-16 08:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 8302, 402, 'OPEN', 'USD', CAST(15000.00 AS DECIMAL(18,2)), CAST(35000.00 AS DECIMAL(18,2)), TRUE, CAST('2025-08-01 09:00:00' AS TIMESTAMP), CAST('2025-06-16 08:10:00' AS TIMESTAMP)
  UNION ALL SELECT 8303, 403, 'CLOSED', 'USD', CAST(18000.00 AS DECIMAL(18,2)), CAST(17500.00 AS DECIMAL(18,2)), TRUE, CAST('2024-12-01 17:00:00' AS TIMESTAMP), CAST('2024-11-03 10:00:00' AS TIMESTAMP)
  UNION ALL SELECT 8304, 401, 'OPEN', 'USD', CAST(4500.00 AS DECIMAL(18,2)), CAST(5000.00 AS DECIMAL(18,2)), FALSE, CAST('2025-06-20 09:00:00' AS TIMESTAMP), CAST('2025-06-16 08:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.claim_reserve_component
SELECT * FROM (
  SELECT CAST(8401 AS BIGINT) AS claim_reserve_component_id, CAST(8301 AS BIGINT) AS claim_reserve_id, 'LOSS_PD' AS reserve_type_code, CAST(5100.00 AS DECIMAL(18,2)) AS reserve_amount, CAST('2025-06-16 08:00:00' AS TIMESTAMP) AS created_at, CAST('2025-07-01 09:00:00' AS TIMESTAMP) AS last_updated_at
  UNION ALL SELECT 8402, 8301, 'EXPENSE_ADJUSTING', CAST(500.00 AS DECIMAL(18,2)), CAST('2025-06-16 08:00:00' AS TIMESTAMP), CAST('2025-07-01 09:00:00' AS TIMESTAMP)
  UNION ALL SELECT 8403, 8302, 'LOSS_BI', CAST(30000.00 AS DECIMAL(18,2)), CAST('2025-06-16 08:10:00' AS TIMESTAMP), CAST('2025-08-01 09:00:00' AS TIMESTAMP)
  UNION ALL SELECT 8404, 8302, 'EXPENSE_LEGAL', CAST(5000.00 AS DECIMAL(18,2)), CAST('2025-07-02 08:00:00' AS TIMESTAMP), CAST('2025-08-01 09:00:00' AS TIMESTAMP)
  UNION ALL SELECT 8405, 8303, 'LOSS_PD', CAST(17500.00 AS DECIMAL(18,2)), CAST('2024-11-03 10:00:00' AS TIMESTAMP), CAST('2024-12-01 17:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.claim_reserve_transaction
SELECT * FROM (
  SELECT CAST(8501 AS BIGINT) AS claim_reserve_txn_id, CAST(8301 AS BIGINT) AS claim_reserve_id, CAST('2025-06-16 08:00:00' AS TIMESTAMP) AS transaction_datetime, 'LOSS_PD' AS reserve_type_code, CAST(4500.00 AS DECIMAL(18,2)) AS change_amount, 'INITIAL' AS reason_code, CAST(4 AS BIGINT) AS created_by_party_id, CAST('2025-06-16 08:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 8502, 8301, CAST('2025-06-25 12:30:00' AS TIMESTAMP), 'LOSS_PD', CAST(600.00 AS DECIMAL(18,2)), 'SUPPLEMENT', 4, CAST('2025-06-25 12:30:00' AS TIMESTAMP)
  UNION ALL SELECT 8503, 8302, CAST('2025-06-16 08:10:00' AS TIMESTAMP), 'LOSS_BI', CAST(15000.00 AS DECIMAL(18,2)), 'INITIAL', 4, CAST('2025-06-16 08:10:00' AS TIMESTAMP)
  UNION ALL SELECT 8504, 8302, CAST('2025-07-02 08:00:00' AS TIMESTAMP), 'LOSS_BI', CAST(15000.00 AS DECIMAL(18,2)), 'NEW_INFO', 4, CAST('2025-07-02 08:00:00' AS TIMESTAMP)
  UNION ALL SELECT 8505, 8302, CAST('2025-07-02 08:05:00' AS TIMESTAMP), 'EXPENSE_LEGAL', CAST(5000.00 AS DECIMAL(18,2)), 'SUIT', 4, CAST('2025-07-02 08:05:00' AS TIMESTAMP)
  UNION ALL SELECT 8506, 8303, CAST('2024-11-03 10:00:00' AS TIMESTAMP), 'LOSS_PD', CAST(18000.00 AS DECIMAL(18,2)), 'INITIAL', 4, CAST('2024-11-03 10:00:00' AS TIMESTAMP)
  UNION ALL SELECT 8507, 8303, CAST('2024-11-05 12:00:00' AS TIMESTAMP), 'LOSS_PD', CAST(-500.00 AS DECIMAL(18,2)), 'ACV_ADJUST', 4, CAST('2024-11-05 12:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.claim_payment
SELECT * FROM (
  SELECT CAST(9201 AS BIGINT) AS claim_payment_id, CAST(401 AS BIGINT) AS claim_id, CAST('2025-07-12 11:00:00' AS TIMESTAMP) AS payment_datetime, CAST('2025-07-12' AS DATE) AS payment_date, 'LOSS' AS payment_category_code, CAST(4600.00 AS DECIMAL(18,2)) AS payment_amount, CAST(500.00 AS DECIMAL(18,2)) AS deductible_applied_amount, 'USD' AS currency_code, CAST(7 AS BIGINT) AS payee_party_id, 'BODY_SHOP' AS payee_type_code, 'CLEARED' AS payment_status_code, CAST(3001 AS BIGINT) AS policy_coverage_id, CAST('2025-07-12 11:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 9202, 401, CAST('2025-07-13 09:00:00' AS TIMESTAMP), CAST('2025-07-13' AS DATE), 'RENTAL', CAST(240.00 AS DECIMAL(18,2)), CAST(0.00 AS DECIMAL(18,2)), 'USD', 1, 'INSURED', 'CLEARED', 3005, CAST('2025-07-13 09:00:00' AS TIMESTAMP)
  UNION ALL SELECT 9203, 402, CAST('2025-07-25 14:00:00' AS TIMESTAMP), CAST('2025-07-25' AS DATE), 'EXPENSE', CAST(1500.00 AS DECIMAL(18,2)), CAST(0.00 AS DECIMAL(18,2)), 'USD', 9, 'ATTORNEY', 'ISSUED', 3003, CAST('2025-07-25 14:00:00' AS TIMESTAMP)
  UNION ALL SELECT 9204, 403, CAST('2024-11-22 10:00:00' AS TIMESTAMP), CAST('2024-11-22' AS DATE), 'LOSS', CAST(17250.00 AS DECIMAL(18,2)), CAST(250.00 AS DECIMAL(18,2)), 'USD', 1, 'INSURED', 'CLEARED', 3002, CAST('2024-11-22 10:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.repair_engagement
SELECT * FROM (
  SELECT CAST(8601 AS BIGINT) AS repair_engagement_id, CAST(401 AS BIGINT) AS claim_id, CAST(7 AS BIGINT) AS vendor_party_id, 'APPROVED' AS estimate_status_code, CAST(28.50 AS DECIMAL(8,2)) AS estimated_repair_hours, CAST(2100.00 AS DECIMAL(18,2)) AS parts_cost_oem_amount, CAST(350.00 AS DECIMAL(18,2)) AS parts_cost_aftermarket_amount, CAST(2400.00 AS DECIMAL(18,2)) AS labor_cost_amount, 6 AS rental_car_days_count, CAST(240.00 AS DECIMAL(18,2)) AS rental_car_total_amount, 'USD' AS currency_code, CAST('2025-06-18 10:00:00' AS TIMESTAMP) AS created_at, CAST('2025-07-12 16:00:00' AS TIMESTAMP) AS last_updated_at
  UNION ALL SELECT 8602, 401, 7, 'COMPLETED', CAST(30.00 AS DECIMAL(8,2)), CAST(2250.00 AS DECIMAL(18,2)), CAST(350.00 AS DECIMAL(18,2)), CAST(2500.00 AS DECIMAL(18,2)), 6, CAST(240.00 AS DECIMAL(18,2)), 'USD', CAST('2025-07-01 09:00:00' AS TIMESTAMP), CAST('2025-07-12 16:00:00' AS TIMESTAMP)
) s;


-- =============================================================================
-- 10) OFFERS, OTHER INSURANCE, SUBROGATION, RECOVERIES, LITIGATION, FRAUD
-- =============================================================================

INSERT INTO TABLE car_insurance_claims.claim_offer
SELECT * FROM (
  SELECT CAST(9001 AS BIGINT) AS claim_offer_id, CAST(401 AS BIGINT) AS claim_id, CAST('2025-07-10 16:00:00' AS TIMESTAMP) AS offer_datetime, CAST('2025-07-10' AS DATE) AS offer_date, CAST(5100.00 AS DECIMAL(18,2)) AS offer_amount, 'USD' AS currency_code, 'ACCEPTED' AS offer_status_code, 'FULL_SETTLEMENT' AS offer_type_code, CAST(1 AS BIGINT) AS payee_party_id, CAST(3001 AS BIGINT) AS policy_coverage_id, CAST('2025-07-11 09:30:00' AS TIMESTAMP) AS accepted_datetime, 'Repair at Metro; deductible applies.' AS notes, CAST('2025-07-10 16:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 9002, 402, CAST('2025-07-20 10:00:00' AS TIMESTAMP), CAST('2025-07-20' AS DATE), CAST(12000.00 AS DECIMAL(18,2)), 'USD', 'REJECTED', 'PARTIAL', 2, 3003, CAST(NULL AS TIMESTAMP), 'Initial BI offer rejected by counsel.', CAST('2025-07-20 10:00:00' AS TIMESTAMP)
  UNION ALL SELECT 9003, 403, CAST('2024-11-20 15:00:00' AS TIMESTAMP), CAST('2024-11-20' AS DATE), CAST(17500.00 AS DECIMAL(18,2)), 'USD', 'ACCEPTED', 'FULL_SETTLEMENT', 1, 3002, CAST('2024-11-21 11:00:00' AS TIMESTAMP), 'ACV total loss settlement.', CAST('2024-11-20 15:00:00' AS TIMESTAMP)
) s;


-- Lifecycle events after assessments / payments / offers so related_* keys resolve
INSERT INTO TABLE car_insurance_claims.claim_lifecycle_event
SELECT * FROM (
  SELECT CAST(7101 AS BIGINT) AS claim_lifecycle_event_id, CAST(401 AS BIGINT) AS claim_id, 'INTAKE' AS event_type_code, CAST('2025-06-15 19:05:00' AS TIMESTAMP) AS event_datetime, CAST('2025-06-15' AS DATE) AS event_date, CAST(4 AS BIGINT) AS actor_party_id, CAST(NULL AS BIGINT) AS related_claim_offer_id, CAST(NULL AS BIGINT) AS related_claim_payment_id, CAST(NULL AS BIGINT) AS related_damage_assessment_id, 'FNOL intake completed' AS event_notes, CAST('2025-06-15 19:05:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 7102, 401, 'TRIAGE', CAST('2025-06-15 20:00:00' AS TIMESTAMP), CAST('2025-06-15' AS DATE), 4, NULL, NULL, NULL, 'Assigned severity medium PD', CAST('2025-06-15 20:00:00' AS TIMESTAMP)
  UNION ALL SELECT 7103, 401, 'INSPECTION', CAST('2025-06-17 14:00:00' AS TIMESTAMP), CAST('2025-06-17' AS DATE), 14, NULL, NULL, 8001, 'Staff appraisal scheduled/completed', CAST('2025-06-17 14:00:00' AS TIMESTAMP)
  UNION ALL SELECT 7104, 401, 'OFFER', CAST('2025-07-10 16:00:00' AS TIMESTAMP), CAST('2025-07-10' AS DATE), 4, 9001, NULL, NULL, 'Collision repair settlement offer', CAST('2025-07-10 16:00:00' AS TIMESTAMP)
  UNION ALL SELECT 7105, 401, 'PAYMENT', CAST('2025-07-12 11:00:00' AS TIMESTAMP), CAST('2025-07-12' AS DATE), 4, NULL, 9201, NULL, 'Body shop payment issued', CAST('2025-07-12 11:00:00' AS TIMESTAMP)
  UNION ALL SELECT 7106, 402, 'INTAKE', CAST('2025-06-15 19:20:00' AS TIMESTAMP), CAST('2025-06-15' AS DATE), 4, NULL, NULL, NULL, 'BI claim opened for passenger', CAST('2025-06-15 19:20:00' AS TIMESTAMP)
  UNION ALL SELECT 7107, 402, 'SIU_REFERRAL', CAST('2025-06-18 13:00:00' AS TIMESTAMP), CAST('2025-06-18' AS DATE), 13, NULL, NULL, NULL, 'Routine BI screening referral', CAST('2025-06-18 13:00:00' AS TIMESTAMP)
  UNION ALL SELECT 7108, 402, 'SUIT_FILED', CAST('2025-08-01 09:00:00' AS TIMESTAMP), CAST('2025-08-01' AS DATE), 6, NULL, NULL, NULL, 'Plaintiff counsel filed suit', CAST('2025-08-01 09:00:00' AS TIMESTAMP)
  UNION ALL SELECT 7109, 403, 'INTAKE', CAST('2024-11-03 08:30:00' AS TIMESTAMP), CAST('2024-11-03' AS DATE), 4, NULL, NULL, NULL, 'Theft FNOL', CAST('2024-11-03 08:30:00' AS TIMESTAMP)
  UNION ALL SELECT 7110, 403, 'OFFER', CAST('2024-11-20 15:00:00' AS TIMESTAMP), CAST('2024-11-20' AS DATE), 4, 9003, NULL, NULL, 'ACV total loss offer', CAST('2024-11-20 15:00:00' AS TIMESTAMP)
  UNION ALL SELECT 7111, 403, 'PAYMENT', CAST('2024-11-22 10:00:00' AS TIMESTAMP), CAST('2024-11-22' AS DATE), 4, NULL, 9204, NULL, 'Insured ACV payment', CAST('2024-11-22 10:00:00' AS TIMESTAMP)
  UNION ALL SELECT 7112, 403, 'CLOSE', CAST('2024-12-01 17:00:00' AS TIMESTAMP), CAST('2024-12-01' AS DATE), 4, NULL, NULL, NULL, 'Claim closed after salvage', CAST('2024-12-01 17:00:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.other_insurance
SELECT * FROM (
  SELECT CAST(8701 AS BIGINT) AS other_insurance_id, CAST(401 AS BIGINT) AS claim_id, CAST(301 AS BIGINT) AS loss_event_id, 'ADVERSE_AUTO' AS other_insurance_type_code, CAST(8 AS BIGINT) AS carrier_party_id, 'Peak Mutual Insurance Company' AS carrier_name_raw, 'PM-778812' AS policy_number, 'PM-CLM-554421' AS claim_number, 'BI_LIABILITY' AS coverage_type_code, '+1-555-0888' AS contact_phone, TRUE AS is_primary_on_loss, CAST('2025-06-16 11:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 8702, 402, 301, 'ADVERSE_AUTO', 8, 'Peak Mutual Insurance Company', 'PM-778812', 'PM-CLM-554422', 'BI_LIABILITY', '+1-555-0888', TRUE, CAST('2025-06-16 11:05:00' AS TIMESTAMP)
) s;


INSERT INTO TABLE car_insurance_claims.subrogation_case
SELECT * FROM (
  SELECT CAST(8801 AS BIGINT) AS subrogation_case_id, CAST(401 AS BIGINT) AS claim_id, CAST(3 AS BIGINT) AS adverse_party_id, CAST(8 AS BIGINT) AS adverse_carrier_party_id, CAST(8701 AS BIGINT) AS other_insurance_id, 'NEGOTIATING' AS subrogation_status_code, CAST(5100.00 AS DECIMAL(18,2)) AS demand_amount, CAST(2500.00 AS DECIMAL(18,2)) AS recovered_amount, 'USD' AS currency_code, CAST('2025-07-15' AS DATE) AS opened_date, CAST(NULL AS DATE) AS closed_date, CAST('2027-06-15' AS DATE) AS statute_limitations_date, CAST('2025-07-15 10:00:00' AS TIMESTAMP) AS created_at
) s;


INSERT INTO TABLE car_insurance_claims.claim_recovery
SELECT * FROM (
  SELECT CAST(8901 AS BIGINT) AS claim_recovery_id, CAST(401 AS BIGINT) AS claim_id, CAST(8801 AS BIGINT) AS subrogation_case_id, 'SUBROGATION' AS recovery_type_code, CAST('2025-08-01 15:00:00' AS TIMESTAMP) AS recovery_datetime, CAST('2025-08-01' AS DATE) AS recovery_date, CAST(2500.00 AS DECIMAL(18,2)) AS recovery_amount, 'USD' AS currency_code, CAST(8 AS BIGINT) AS payer_party_id, CAST(NULL AS BIGINT) AS salvage_vendor_party_id, 'RECEIVED' AS payment_status_code, CAST('2025-08-01 15:00:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 8902, 403, CAST(NULL AS BIGINT), 'SALVAGE', CAST('2024-11-28 13:00:00' AS TIMESTAMP), CAST('2024-11-28' AS DATE), CAST(900.00 AS DECIMAL(18,2)), 'USD', 7, 7, 'RECEIVED', CAST('2024-11-28 13:00:00' AS TIMESTAMP)
) s;


-- 9101 / claim 402: docket + counsel present; IN_DISCOVERY filed 2025-08-01
-- (R1.2b EscalateDiscovery once filed_date is older than 90 days).
INSERT INTO TABLE car_insurance_claims.litigation_case
SELECT * FROM (
  SELECT CAST(9101 AS BIGINT) AS litigation_case_id, CAST(402 AS BIGINT) AS claim_id, 'IN_DISCOVERY' AS litigation_status_code, '2025-CV-4412' AS docket_number, 'Sangamon County Circuit Court' AS venue_name, 'IL' AS venue_country_subdivision_code, CAST(2 AS BIGINT) AS plaintiff_party_id, CAST(10 AS BIGINT) AS defendant_party_id, CAST(9 AS BIGINT) AS plaintiff_counsel_party_id, CAST(9 AS BIGINT) AS defense_counsel_party_id, CAST('2025-08-01' AS DATE) AS filed_date, CAST('2025-08-05' AS DATE) AS served_date, CAST(NULL AS DATE) AS closed_date, CAST(75000.00 AS DECIMAL(18,2)) AS demand_amount, 'USD' AS currency_code, CAST('2025-08-01 09:00:00' AS TIMESTAMP) AS created_at
) s;


INSERT INTO TABLE car_insurance_claims.fraud_assessment
SELECT * FROM (
  SELECT CAST(9301 AS BIGINT) AS fraud_assessment_id, CAST(402 AS BIGINT) AS claim_id, CAST('2025-06-18 13:30:00' AS TIMESTAMP) AS assessment_datetime, CAST('2025-06-18' AS DATE) AS assessment_date, TRUE AS siu_referral_indicator, 'CLEARED' AS outcome_code, CAST(0.1800 AS DECIMAL(7,4)) AS risk_score, CAST(13 AS BIGINT) AS assessor_party_id, 'Soft-tissue BI after rear-end; cleared after records review.' AS rationale_summary, CAST('2025-06-18 13:30:00' AS TIMESTAMP) AS created_at
  UNION ALL SELECT 9302, 403, CAST('2024-11-04 16:00:00' AS TIMESTAMP), CAST('2024-11-04' AS DATE), TRUE, 'SUSPECTED', CAST(0.6200 AS DECIMAL(7,4)), 13, 'Theft timing reviewed; later cleared operationally but first SIU screen flagged.', CAST('2024-11-04 16:00:00' AS TIMESTAMP)
  UNION ALL SELECT 9303, 403, CAST('2024-11-10 11:00:00' AS TIMESTAMP), CAST('2024-11-10' AS DATE), TRUE, 'CLEARED', CAST(0.2100 AS DECIMAL(7,4)), 13, 'Police recovery confirmed; fraud suspicion cleared.', CAST('2024-11-10 11:00:00' AS TIMESTAMP)
) s;


-- =============================================================================
-- END OF SEED DATA
-- =============================================================================
-- Quick row-count sanity check (optional):
-- SELECT 'ref_code_list' AS tbl, COUNT(*) AS cnt FROM car_insurance_claims.ref_code_list
-- UNION ALL SELECT 'party', COUNT(*) FROM car_insurance_claims.party
-- UNION ALL SELECT 'insurance_policy', COUNT(*) FROM car_insurance_claims.insurance_policy
-- UNION ALL SELECT 'claim', COUNT(*) FROM car_insurance_claims.claim
-- UNION ALL SELECT 'claim_payment', COUNT(*) FROM car_insurance_claims.claim_payment
-- UNION ALL SELECT 'claim_recovery', COUNT(*) FROM car_insurance_claims.claim_recovery;
-- =============================================================================
