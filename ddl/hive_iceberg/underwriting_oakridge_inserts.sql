-- =============================================================================
-- Oakridge Plaza document inserts — submission_id 9200 (submission_number SUB-9200)
-- =============================================================================
-- Source files: packs/underwriting/additional_data/
-- Prerequisite : underwriting_iceberg.sql, underwriting_governance_alter.sql,
--                underwriting_ocr.sql, underwriting_sov.sql,
--                underwriting_rental_value.sql, underwriting_four_point.sql,
--                underwriting_loss_run.sql, underwriting_large_loss.sql,
--                underwriting_tenant_roster.sql, and underwriting_seed_data.sql
--                (party 14).
--
-- 9100 through 9107 are left unchanged.
-- Building 4250000 + business income 480000 + signs 35000 = 4765000.
-- Equipment breakdown is stored and excluded from that total.
-- The lowest word on these scans is below 0.8, so the first probe is
-- P0C_LOW_OCR_CONFIDENCE. The loss run signature is absent.
-- Run once. A second run inserts the same keys again.
-- =============================================================================

USE underwriting;

-- Submission spine for the Oakridge scans. OFAC, SIU, flood, and wind are not on these files.
INSERT INTO TABLE underwriting.submissions
(submission_id, submission_number, producer_id, applicant_tax_id, line_of_business, class_code, total_insured_value, submission_timestamp, submission_status_code, naics_code, has_ofac_match, siu_score, tax_lien_unresolved)
SELECT * FROM (
  SELECT CAST(9200 AS BIGINT) AS submission_id, 'SUB-9200' AS submission_number, 'OAKR-00942' AS producer_id, '84-3920184' AS applicant_tax_id, 'COMMERCIAL_PROPERTY' AS line_of_business, '67635' AS class_code, CAST(4765000 AS BIGINT) AS total_insured_value, CAST('2026-11-15 09:00:00' AS TIMESTAMP) AS submission_timestamp, 'OPEN' AS submission_status_code, '531120' AS naics_code, FALSE AS has_ofac_match, 0 AS siu_score, FALSE AS tax_lien_unresolved
) s;
INSERT INTO TABLE underwriting.property_risk_scores
(risk_score_id, submission_id, is_in_flood_plain, inspection_completed, flood_zone, has_survey_on_file, survey_age_months, wind_tier, has_recent_cat_run, construction_type, year_built, wiring_updated, protection_class, has_sprinklers, square_footage)
SELECT * FROM (
  SELECT 'RS-9200' AS risk_score_id, CAST(9200 AS BIGINT) AS submission_id, FALSE AS is_in_flood_plain, TRUE AS inspection_completed, 'NONE' AS flood_zone, FALSE AS has_survey_on_file, 0 AS survey_age_months, 0 AS wind_tier, FALSE AS has_recent_cat_run, 'MASONRY' AS construction_type, 2004 AS year_built, FALSE AS wiring_updated, '2' AS protection_class, TRUE AS has_sprinklers, 18500 AS square_footage
) s;
INSERT INTO TABLE underwriting.loss_history_summary
(loss_summary_id, submission_id, prior_claims_count, has_open_loss_past_36m, financial_stability_tier, claims_count_36m, total_incurred_36m, financial_score)
SELECT * FROM (
  SELECT 'LH-9200' AS loss_summary_id, CAST(9200 AS BIGINT) AS submission_id, 1 AS prior_claims_count, FALSE AS has_open_loss_past_36m, 'B' AS financial_stability_tier, 1 AS claims_count_36m, CAST(14250 AS BIGINT) AS total_incurred_36m, CAST(NULL AS INT) AS financial_score
) s;
INSERT INTO TABLE underwriting.submission_party_role
(submission_party_role_id, submission_id, party_id, role_type_code, assigned_at, unassigned_at, is_current_assignment, created_at)
SELECT * FROM (
  SELECT 'SPR-9200' AS submission_party_role_id, CAST(9200 AS BIGINT) AS submission_id, CAST(14 AS BIGINT) AS party_id, 'UNDERWRITER' AS role_type_code, CAST('2026-11-15 09:05:00' AS TIMESTAMP) AS assigned_at, CAST(NULL AS TIMESTAMP) AS unassigned_at, TRUE AS is_current_assignment, CAST('2026-11-15 09:05:00' AS TIMESTAMP) AS created_at
) s;

-- acord-125-126-140-confidence.json, businessincome-rentalvalue-scanned.json, 4-point-inspection-scanned.json, loss-run-report.json, large-loss-narrative-scanned.json, tenant-roster-scanned.json
INSERT INTO TABLE underwriting.ocr_document
(document_id, submission_id, ocr_model, pages_processed, doc_size_bytes, application_date, status_of_transaction)
SELECT * FROM (
  SELECT 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'mistral-ocr-2505' AS ocr_model, 9 AS pages_processed, CAST(3241920 AS BIGINT) AS doc_size_bytes, '2026-11-15' AS application_date, 'Quote' AS status_of_transaction
  UNION ALL
  SELECT 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'mistral-ocr-2505' AS ocr_model, 1 AS pages_processed, CAST(412550 AS BIGINT) AS doc_size_bytes, '2026-11-15' AS application_date, CAST(NULL AS STRING) AS status_of_transaction
  UNION ALL
  SELECT 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'mistral-ocr-2505' AS ocr_model, 1 AS pages_processed, CAST(182410 AS BIGINT) AS doc_size_bytes, '2026-11-10' AS application_date, CAST(NULL AS STRING) AS status_of_transaction
  UNION ALL
  SELECT 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'mistral-ocr-2505' AS ocr_model, 3 AS pages_processed, CAST(1024840 AS BIGINT) AS doc_size_bytes, '2026-10-15' AS application_date, CAST(NULL AS STRING) AS status_of_transaction
  UNION ALL
  SELECT 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'mistral-ocr-2505' AS ocr_model, 2 AS pages_processed, CAST(624190 AS BIGINT) AS doc_size_bytes, '2026-11-15' AS application_date, CAST(NULL AS STRING) AS status_of_transaction
  UNION ALL
  SELECT 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'mistral-ocr-2505' AS ocr_model, 1 AS pages_processed, CAST(215440 AS BIGINT) AS doc_size_bytes, '2026-11-15' AS application_date, CAST(NULL AS STRING) AS status_of_transaction
) s;
INSERT INTO TABLE underwriting.ocr_form
(form_id, document_id, submission_id, form_label)
SELECT * FROM (
  SELECT 'OCR-ACORD-F1' AS form_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'ACORD 125 (2016/03)' AS form_label
  UNION ALL
  SELECT 'OCR-ACORD-F2' AS form_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'ACORD 140 (2016/03)' AS form_label
  UNION ALL
  SELECT 'OCR-ACORD-F3' AS form_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'ACORD 126 (2016/03)' AS form_label
  UNION ALL
  SELECT 'OCR-810-F1' AS form_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'ACORD 810 (2015/12)' AS form_label
  UNION ALL
  SELECT 'OCR-4PT-F1' AS form_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, '4-POINT SYSTEM UPDATE VERIFICATION' AS form_label
  UNION ALL
  SELECT 'OCR-LOSS-F1' AS form_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'Carrier Loss Run' AS form_label
  UNION ALL
  SELECT 'OCR-NARR-F1' AS form_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'Large Loss Narrative & Remediation Proof' AS form_label
  UNION ALL
  SELECT 'OCR-ROSTER-F1' AS form_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'Tenant Roster & Business Classifications' AS form_label
) s;
INSERT INTO TABLE underwriting.ocr_field
(field_id, document_id, submission_id, field_path, field_value)
SELECT * FROM (
  SELECT 'OCR-ACORD-V0001' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'submission_metadata.application_date' AS field_path, '2026-11-15' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0002' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'submission_metadata.forms_detected.1' AS field_path, 'ACORD 125 (2016/03)' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0003' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'submission_metadata.forms_detected.2' AS field_path, 'ACORD 140 (2016/03)' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0004' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'submission_metadata.forms_detected.3' AS field_path, 'ACORD 126 (2016/03)' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0005' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'submission_metadata.status_of_transaction' AS field_path, 'Quote' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0006' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.agency.name' AS field_path, 'Beacon Commercial Risk Partners, LLC' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0007' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.agency.contact_name' AS field_path, 'Marcus Vance, CIC' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0008' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.agency.phone' AS field_path, '(212) 555-0194' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0009' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.agency.email' AS field_path, 'mvance@beaconrisk.example.com' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0010' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.agency.agency_customer_id' AS field_path, 'OAKR-00942' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0011' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.carrier.name' AS field_path, 'Travelers Indemnity Company' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0012' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.carrier.naic_code' AS field_path, '25658' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0013' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.carrier.program_name' AS field_path, 'Commercial Package Policy' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0014' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.policy_information.proposed_effective_date' AS field_path, '2026-12-01' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0015' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.policy_information.proposed_expiration_date' AS field_path, '2027-12-01' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0016' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.policy_information.billing_plan' AS field_path, 'Direct' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0017' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.policy_information.payment_plan' AS field_path, 'Annual' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0018' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.policy_information.total_estimated_premium' AS field_path, '18450' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0019' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.first_named_insured.name' AS field_path, 'Oakridge Plaza Holdings, LLC' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0020' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.first_named_insured.mailing_address' AS field_path, '1200 Harbor View Drive, Suite 400, Stamford, CT 06902' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0021' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.first_named_insured.fein' AS field_path, '84-3920184' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0022' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.first_named_insured.sic_code' AS field_path, '6512' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0023' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.first_named_insured.naics_code' AS field_path, '531120' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0024' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.first_named_insured.legal_entity' AS field_path, 'LLC' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0025' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.first_named_insured.date_business_started' AS field_path, '2018-04-15' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0026' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.prior_carrier_and_loss_summary.current_carrier' AS field_path, 'Hartford Fire Insurance Company' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0027' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.prior_carrier_and_loss_summary.current_policy_number' AS field_path, '42-UEN-88412' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0028' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.prior_carrier_and_loss_summary.five_year_total_incurred' AS field_path, '14250' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0029' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_125_applicant_information.prior_carrier_and_loss_summary.claims_count' AS field_path, '1' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0030' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.form_metadata.form_number' AS field_path, 'ACORD 140' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0031' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.form_metadata.form_edition' AS field_path, '2016/03' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0032' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.form_metadata.effective_date' AS field_path, '2026-12-01' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0033' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.form_metadata.named_insured' AS field_path, 'Oakridge Plaza Holdings, LLC' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0034' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.premises_number' AS field_path, '001' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0035' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.building_number' AS field_path, '001' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0036' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.street_address' AS field_path, '840 Boston Post Road, Milford, CT 06460' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0037' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.building_description' AS field_path, 'Oakridge Plaza Retail Strip Center' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0038' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.1.subject_of_insurance' AS field_path, 'Building' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0039' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.1.amount' AS field_path, '4250000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0040' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.1.valuation' AS field_path, 'RC' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0041' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.1.coinsurance_percent' AS field_path, '90' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0042' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.1.cause_of_loss' AS field_path, 'Special' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0043' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.1.deductible' AS field_path, '5000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0044' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.2.subject_of_insurance' AS field_path, 'Business Income & Extra Expense' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0045' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.2.amount' AS field_path, '480000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0046' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.2.valuation' AS field_path, 'ALS (12 Months)' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0047' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.2.monthly_limitation' AS field_path, '1/3' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0048' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.2.cause_of_loss' AS field_path, 'Special' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0049' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.2.deductible' AS field_path, '72' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0050' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.2.deductible_type' AS field_path, 'Hours Waiting Period' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0051' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.3.subject_of_insurance' AS field_path, 'Ordinance or Law (Cov. B & C Combined)' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0052' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.3.amount' AS field_path, '500000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0053' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.3.valuation' AS field_path, 'RC' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0054' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.3.cause_of_loss' AS field_path, 'Special' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0055' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.3.deductible' AS field_path, '5000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0056' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.4.subject_of_insurance' AS field_path, 'Equipment Breakdown' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0057' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.4.amount' AS field_path, '4250000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0058' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.4.valuation' AS field_path, 'RC' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0059' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.4.cause_of_loss' AS field_path, 'Comprehensive' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0060' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.4.deductible' AS field_path, '5000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0061' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.5.subject_of_insurance' AS field_path, 'Outdoor Signs (Pylon & Facade)' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0062' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.5.amount' AS field_path, '35000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0063' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.5.valuation' AS field_path, 'RC' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0064' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.5.coinsurance_percent' AS field_path, '80' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0065' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.5.cause_of_loss' AS field_path, 'Special' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0066' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.coverages.5.deductible' AS field_path, '1000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0067' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.construction_and_cope.construction_type' AS field_path, 'Masonry Non-Combustible' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0068' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.construction_and_cope.iso_construction_code' AS field_path, '4' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0069' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.construction_and_cope.year_built' AS field_path, '2004' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0070' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.construction_and_cope.total_area_sq_ft' AS field_path, '18500' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0071' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.construction_and_cope.number_of_stories' AS field_path, '1' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0072' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.construction_and_cope.roof_type' AS field_path, 'TPO Membrane' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0073' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.construction_and_cope.roof_year_replaced' AS field_path, '2021' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0074' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.protection_and_security.public_protection_class' AS field_path, '02' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0075' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.protection_and_security.sprinklered' AS field_path, 'true' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0076' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.protection_and_security.percent_sprinklered' AS field_path, '100' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0077' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.protection_and_security.sprinkler_central_station_monitored' AS field_path, 'true' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0078' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.additional_interests.1.interest_type' AS field_path, 'Mortgagee / Loss Payee' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0079' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.additional_interests.1.name' AS field_path, 'First Coastal Commercial Bank' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0080' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_140_property_section.premises_schedules.1.additional_interests.1.loan_number' AS field_path, 'CRE-2018-44910' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0081' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.form_metadata.form_number' AS field_path, 'ACORD 126' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0082' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.form_metadata.form_edition' AS field_path, '2016/03' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0083' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.form_metadata.form_title' AS field_path, 'COMMERCIAL GENERAL LIABILITY SECTION' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0084' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.form_metadata.effective_date' AS field_path, '2026-12-01' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0085' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.form_metadata.named_insured' AS field_path, 'Oakridge Plaza Holdings, LLC' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0086' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.coverage_form' AS field_path, 'Commercial General Liability' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0087' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.trigger_type' AS field_path, 'Occurrence' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0088' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.claims_made_retroactive_date' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0089' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.limits.general_aggregate' AS field_path, '2000000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0090' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.limits.general_aggregate_applies_per' AS field_path, 'Location' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0091' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.limits.products_completed_operations_aggregate' AS field_path, '2000000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0092' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.limits.personal_and_advertising_injury' AS field_path, '1000000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0093' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.limits.each_occurrence' AS field_path, '1000000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0094' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.limits.damage_to_rented_premises_each_occurrence' AS field_path, '300000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0095' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.limits.medical_expense_any_one_person' AS field_path, '10000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0096' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.deductible.bodily_injury_deductible' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0097' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.deductible.property_damage_deductible' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0098' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.deductible.deductible_basis' AS field_path, 'Per Occurrence' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0099' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.other_coverages_or_endorsements.1' AS field_path, 'CG 20 11 - Additional Insured - Managers or Lessors of Premises' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0100' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.other_coverages_or_endorsements.2' AS field_path, 'CG 24 04 - Waiver of Transfer of Rights of Recovery Against Others' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0101' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.coverages_and_limits.other_coverages_or_endorsements.3' AS field_path, 'Hired & Non-Owned Auto Liability ($1,000,000 CSL)' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0102' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.1.location_number' AS field_path, '001' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0103' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.1.hazard_number' AS field_path, '001' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0104' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.1.classification_description' AS field_path, 'Shopping Centers - Buildings or Premises - Not Occupied by the Insured (Lessor\'s Risk Only)' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0105' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.1.class_code' AS field_path, '67635' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0106' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.1.premium_basis' AS field_path, 'Area' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0107' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.1.exposure' AS field_path, '18500' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0108' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.1.territory' AS field_path, '005' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0109' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.1.premises_ops_rate' AS field_path, '295.4' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0110' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.1.products_rate' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0111' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.1.premises_ops_premium' AS field_path, '5465' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0112' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.1.products_premium' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0113' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.2.location_number' AS field_path, '001' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0114' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.2.hazard_number' AS field_path, '002' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0115' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.2.classification_description' AS field_path, 'Parking - Public - Shopping Centers - Open Air (42 paved spaces)' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0116' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.2.class_code' AS field_path, '46604' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0117' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.2.premium_basis' AS field_path, 'Area' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0118' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.2.exposure' AS field_path, '14200' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0119' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.2.territory' AS field_path, '005' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0120' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.2.premises_ops_rate' AS field_path, '55.28' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0121' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.2.products_rate' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0122' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.2.premises_ops_premium' AS field_path, '785' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0123' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.schedule_of_hazards.2.products_premium' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0124' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.claims_made_section.applicable' AS field_path, 'false' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0125' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.employee_benefits_liability.applicable' AS field_path, 'false' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0126' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.contractors_subcontractors_info.draws_plans_designs_specifications' AS field_path, 'false' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0127' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.contractors_subcontractors_info.blasting_or_explosives' AS field_path, 'false' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0128' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.contractors_subcontractors_info.excavation_tunneling_underground' AS field_path, 'false' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0129' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.contractors_subcontractors_info.subcontractors_used' AS field_path, 'true' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0130' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.contractors_subcontractors_info.subcontractor_work_description' AS field_path, 'Third-party snow/ice removal, landscaping, HVAC maintenance, and parking lot sweeping' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0131' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.contractors_subcontractors_info.percent_work_subcontracted' AS field_path, '100' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0132' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.contractors_subcontractors_info.certificates_of_insurance_collected' AS field_path, 'true' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0133' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.contractors_subcontractors_info.minimum_gl_limit_required_from_subs' AS field_path, '1000000' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0134' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.products_completed_operations.applicable' AS field_path, 'false' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0135' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.products_completed_operations.notes' AS field_path, 'Real estate lessor\'s risk only; no manufacturing, distribution, or installation.' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0136' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.additional_interests_gl.1.interest_type' AS field_path, 'Additional Insured - Managing Agent' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0137' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.additional_interests_gl.1.name' AS field_path, 'Harbor View Property Management, Inc.' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0138' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.additional_interests_gl.1.address' AS field_path, '1200 Harbor View Drive, Suite 410, Stamford, CT 06902' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0139' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.additional_interests_gl.1.location_number' AS field_path, '001' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0140' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.additional_interests_gl.1.certificate_required' AS field_path, 'true' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0141' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.additional_interests_gl.2.interest_type' AS field_path, 'Mortgagee / Additional Insured' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0142' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.additional_interests_gl.2.name' AS field_path, 'First Coastal Commercial Bank' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0143' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.additional_interests_gl.2.address' AS field_path, 'Attn: Commercial Loan Servicing, P.O. Box 90210, Hartford, CT 06103' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0144' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.additional_interests_gl.2.loan_number' AS field_path, 'CRE-2018-44910' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0145' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.additional_interests_gl.2.location_number' AS field_path, '001' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0146' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.additional_interests_gl.2.certificate_required' AS field_path, 'true' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0147' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.1.question_code' AS field_path, '1' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0148' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.1.question_text' AS field_path, 'Any medical facilities provided or medical professionals employed or contracted?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0149' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.1.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0150' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.1.explanation' AS field_path, 'Tenants in Units B & C are independent medical/dental practices carrying their own liability policies.' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0151' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.2.question_code' AS field_path, '2' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0152' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.2.question_text' AS field_path, 'Any exposure to radioactive/nuclear materials?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0153' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.2.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0154' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.2.explanation' AS field_path, 'Dental X-ray equipment in Unit B is owned, operated, and insured solely by tenant Harborview Dental.' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0155' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.3.question_code' AS field_path, '3' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0156' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.3.question_text' AS field_path, 'Do/have past, present or discontinued operations involve(d) storing, treating, discharging, applying, disposing, or transporting of hazardous material?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0157' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.3.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0158' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.3.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0159' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.4.question_code' AS field_path, '4' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0160' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.4.question_text' AS field_path, 'Any operations sold, acquired, or discontinued in last five (5) years?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0161' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.4.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0162' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.4.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0163' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.5.question_code' AS field_path, '5' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0164' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.5.question_text' AS field_path, 'Do you rent or loan equipment to others?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0165' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.5.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0166' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.5.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0167' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.6.question_code' AS field_path, '6' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0168' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.6.question_text' AS field_path, 'Any watercraft, docks, floats owned, hired or leased?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0169' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.6.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0170' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.6.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0171' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.7.question_code' AS field_path, '7' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0172' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.7.question_text' AS field_path, 'Any parking facilities owned/rented?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0173' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.7.answer' AS field_path, 'Y' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0174' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.7.explanation' AS field_path, 'Asphalt surface lot with 42 spaces; dedicated snow/ice removal contract with hold-harmless and AI status.' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0175' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.8.question_code' AS field_path, '8' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0176' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.8.question_text' AS field_path, 'Is a fee charged for parking?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0177' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.8.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0178' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.8.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0179' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.9.question_code' AS field_path, '9' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0180' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.9.question_text' AS field_path, 'Recreation facilities provided?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0181' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.9.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0182' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.9.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0183' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.10.question_code' AS field_path, '10' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0184' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.10.question_text' AS field_path, 'Are there any lodging operations including apartments?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0185' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.10.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0186' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.10.explanation' AS field_path, '100% commercial retail/office occupancy; zero residential units.' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0187' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.11.question_code' AS field_path, '11' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0188' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.11.question_text' AS field_path, 'Is there a swimming pool on the premises?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0189' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.11.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0190' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.11.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0191' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.12.question_code' AS field_path, '12' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0192' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.12.question_text' AS field_path, 'Social events sponsored?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0193' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.12.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0194' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.12.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0195' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.13.question_code' AS field_path, '13' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0196' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.13.question_text' AS field_path, 'Are athletic teams sponsored?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0197' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.13.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0198' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.13.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0199' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.14.question_code' AS field_path, '14' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0200' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.14.question_text' AS field_path, 'Any structural alterations contemplated?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0201' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.14.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0202' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.14.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0203' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.15.question_code' AS field_path, '15' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0204' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.15.question_text' AS field_path, 'Any demolition exposure contemplated?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0205' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.15.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0206' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.15.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0207' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.16.question_code' AS field_path, '16' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0208' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.16.question_text' AS field_path, 'Has applicant been active in or is currently active in joint ventures?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0209' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.16.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0210' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.16.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0211' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.17.question_code' AS field_path, '17' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0212' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.17.question_text' AS field_path, 'Do you lease employees to or from other employers?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0213' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.17.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0214' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.17.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0215' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.18.question_code' AS field_path, '18' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0216' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.18.question_text' AS field_path, 'Is there a labor interchange with any other business or subsidiaries?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0217' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.18.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0218' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.18.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0219' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.19.question_code' AS field_path, '19' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0220' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.19.question_text' AS field_path, 'Are day care facilities operated or controlled?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0221' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.19.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0222' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.19.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0223' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.20.question_code' AS field_path, '20' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0224' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.20.question_text' AS field_path, 'Have any crimes occurred or been attempted on your premises within the last three (3) years?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0225' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.20.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0226' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.20.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0227' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.21.question_code' AS field_path, '21' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0228' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.21.question_text' AS field_path, 'Is there a formal, written safety and security policy in effect?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0229' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.21.answer' AS field_path, 'Y' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0230' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.21.explanation' AS field_path, 'Written slip-and-fall prevention log, winter weather salting protocol, and semi-annual tenant COI audit.' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0231' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.22.question_code' AS field_path, '22' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0232' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.22.question_text' AS field_path, 'Does the businesses\' promotional literature make any representations about the safety or security of the premises?' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0233' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.22.answer' AS field_path, 'N' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0234' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.general_liability_underwriting_questions.22.explanation' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0235' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.signatures.applicant_signature_detected' AS field_path, 'true' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0236' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.signatures.applicant_signed_by' AS field_path, 'Elena Rostova' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0237' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.signatures.applicant_signature_date' AS field_path, '2026-11-15' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0238' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.signatures.producer_signature_detected' AS field_path, 'true' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0239' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.signatures.producer_signed_by' AS field_path, 'Marcus Vance' AS field_value
  UNION ALL
  SELECT 'OCR-ACORD-V0240' AS field_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'acord_126_commercial_general_liability.signatures.producer_signature_date' AS field_path, '2026-11-15' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0001' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'form_metadata.form_number' AS field_path, 'ACORD 810' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0002' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'form_metadata.form_edition' AS field_path, '2015/12' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0003' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'form_metadata.form_title' AS field_path, 'BUSINESS INCOME / EXTRA EXPENSE / RENTAL VALUE WORKSHEET' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0004' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'form_metadata.worksheet_date' AS field_path, '2026-11-15' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0005' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'form_metadata.named_insured' AS field_path, 'Oakridge Plaza Holdings, LLC' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0006' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'form_metadata.applicable_location.premises_number' AS field_path, '001' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0007' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'form_metadata.applicable_location.building_number' AS field_path, '001' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0008' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'form_metadata.applicable_location.address' AS field_path, '840 Boston Post Road, Milford, CT 06460' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0009' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.coverage_type_selected' AS field_path, 'Rental Value Only' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0010' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.financial_period' AS field_path, '12-Month Projection (12/01/2026 to 12/01/2027)' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0011' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.gross_income.annual_gross_rent' AS field_path, '435000' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0012' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.gross_income.tenant_contributions_taxes_cam' AS field_path, '105000' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0013' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.gross_income.fair_rental_value_vacant_space' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0014' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.gross_income.total_gross_rental_income' AS field_path, '540000' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0015' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.deductions_non_continuing_expenses.janitorial_services' AS field_path, '12500' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0016' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.deductions_non_continuing_expenses.landscaping_and_snow_removal' AS field_path, '18500' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0017' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.deductions_non_continuing_expenses.utilities_water_sewer_electric' AS field_path, '25000' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0018' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.deductions_non_continuing_expenses.ordinary_payroll_maintenance' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0019' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.deductions_non_continuing_expenses.property_management_fees' AS field_path, '4000' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0020' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.deductions_non_continuing_expenses.total_deductions' AS field_path, '60000' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0021' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.net_estimated_exposure.net_rental_value' AS field_path, '480000' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0022' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.net_estimated_exposure.selected_limit_of_insurance' AS field_path, '480000' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0023' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.net_estimated_exposure.monthly_limitation_fraction' AS field_path, '1/3' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0024' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'rental_value_calculation.net_estimated_exposure.coinsurance_percentage' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-810-V0025' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.1.unit' AS field_path, 'A' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0026' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.1.tenant_name' AS field_path, 'Gourmet Corner Market' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0027' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.1.square_footage' AS field_path, '6500' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0028' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.1.annual_base_rent' AS field_path, '156000' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0029' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.2.unit' AS field_path, 'B' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0030' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.2.tenant_name' AS field_path, 'Harborview Dental & Orthodontics' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0031' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.2.square_footage' AS field_path, '4500' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0032' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.2.annual_base_rent' AS field_path, '117000' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0033' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.3.unit' AS field_path, 'C' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0034' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.3.tenant_name' AS field_path, 'Coastal Physical Therapy & Wellness' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0035' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.3.square_footage' AS field_path, '4000' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0036' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.3.annual_base_rent' AS field_path, '92000' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0037' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.4.unit' AS field_path, 'D' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0038' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.4.tenant_name' AS field_path, 'Edward Jones Financial Advisory' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0039' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.4.square_footage' AS field_path, '3500' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0040' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_rent_roll_summary.4.annual_base_rent' AS field_path, '70000' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0041' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'signatures.prepared_by' AS field_path, 'Elena Rostova' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0042' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'signatures.title' AS field_path, 'Managing Member' AS field_value
  UNION ALL
  SELECT 'OCR-810-V0043' AS field_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'signatures.date_signed' AS field_path, '2026-11-15' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0001' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'form_metadata.form_title' AS field_path, '4-POINT SYSTEM UPDATE VERIFICATION' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0002' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'form_metadata.inspection_date' AS field_path, '2026-11-10' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0003' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'form_metadata.property_address' AS field_path, '840 Boston Post Road, Milford, CT 06460' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0004' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'form_metadata.named_insured' AS field_path, 'Oakridge Plaza Holdings, LLC' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0005' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'form_metadata.year_built' AS field_path, '2004' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0006' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.roof.system_type' AS field_path, 'TPO Membrane over rigid insulation' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0007' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.roof.year_last_updated' AS field_path, '2021' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0008' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.roof.update_type' AS field_path, 'Full Replacement' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0009' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.roof.notes' AS field_path, '15-year manufacturer warranty on file. No active leaks detected.' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0010' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.plumbing.system_type' AS field_path, 'Copper supply / PVC drain lines' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0011' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.plumbing.year_last_updated' AS field_path, '2004' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0012' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.plumbing.update_type' AS field_path, 'Original' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0013' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.plumbing.notes' AS field_path, 'No polybutylene piping present. Backflow preventers inspected annually (last passed 08/2026).' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0014' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.electrical.system_type' AS field_path, '100% Copper, 800-amp main service, individual tenant sub-panels' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0015' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.electrical.year_last_updated' AS field_path, '2004' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0016' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.electrical.update_type' AS field_path, 'Original' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0017' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.electrical.notes' AS field_path, 'No aluminum branch wiring. Thermal infrared scan passed in 2025 with no hotspots.' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0018' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.hvac.system_type' AS field_path, 'Four (4) rooftop packaged gas/electric units (5 to 7.5 ton)' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0019' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.hvac.year_last_updated' AS field_path, '2023' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0020' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.hvac.update_type' AS field_path, 'Partial Replacement' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0021' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'system_updates.hvac.notes' AS field_path, '2 RTUs replaced in 2021; remaining 2 RTUs replaced in 2023. Quarterly preventative maintenance contract in place.' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0022' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'inspector_certification.inspector_name' AS field_path, 'James OConnor' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0023' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'inspector_certification.license_number' AS field_path, 'HOI.0004921' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0024' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'inspector_certification.company_name' AS field_path, 'OConnor Commercial Inspections, LLC' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0025' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'inspector_certification.signature_detected' AS field_path, 'true' AS field_value
  UNION ALL
  SELECT 'OCR-4PT-V0026' AS field_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'inspector_certification.date_signed' AS field_path, '2026-11-10' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0001' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'report_metadata.document_type' AS field_path, 'Carrier Loss Run' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0002' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'report_metadata.carrier' AS field_path, 'Hartford Fire Insurance Company' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0003' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'report_metadata.named_insured' AS field_path, 'Oakridge Plaza Holdings, LLC' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0004' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'report_metadata.valuation_date' AS field_path, '2026-10-15' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0005' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'report_metadata.report_run_date' AS field_path, '2026-10-16' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0006' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.1.policy_number' AS field_path, '42-UEN-88412' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0007' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.1.policy_term' AS field_path, '12/01/2025 to 12/01/2026' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0008' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.1.line_of_business' AS field_path, 'Commercial Package (Property & GL)' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0009' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.1.total_claims' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0010' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.1.total_incurred' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0011' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.1.total_paid' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0012' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.1.total_reserved' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0013' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.1.total_recovered' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0014' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.2.policy_number' AS field_path, '42-UEN-88412' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0015' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.2.policy_term' AS field_path, '12/01/2024 to 12/01/2025' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0016' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.2.line_of_business' AS field_path, 'Commercial Package (Property & GL)' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0017' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.2.total_claims' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0018' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.2.total_incurred' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0019' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.2.total_paid' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0020' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.2.total_reserved' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0021' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'policy_summary.2.total_recovered' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0022' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'claims_detail' AS field_path, CAST(NULL AS STRING) AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0023' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'aggregate_totals.total_claims_count' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0024' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'aggregate_totals.total_paid_indemnity' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0025' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'aggregate_totals.total_paid_expense' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0026' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'aggregate_totals.total_outstanding_reserve' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0027' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'aggregate_totals.total_gross_incurred' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0028' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'certification.statement' AS field_path, 'This report is a true and accurate summary of claims reported to Hartford Fire Insurance Company as of the valuation date.' AS field_value
  UNION ALL
  SELECT 'OCR-LOSS-V0029' AS field_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'certification.authorized_signature_detected' AS field_path, 'false' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0001' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'document_metadata.document_type' AS field_path, 'Large Loss Narrative & Remediation Proof' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0002' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'document_metadata.named_insured' AS field_path, 'Oakridge Plaza Holdings, LLC' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0003' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'document_metadata.date_prepared' AS field_path, '2026-11-15' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0004' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'document_metadata.related_claim_date' AS field_path, '2024-02-18' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0005' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'document_metadata.related_claim_amount' AS field_path, '14250' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0006' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'loss_narrative.author' AS field_path, 'Elena Rostova' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0007' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'loss_narrative.title' AS field_path, 'Managing Member' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0008' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'loss_narrative.claim_description' AS field_path, 'On February 18, 2024, a severe winter wind and hail storm passed through Milford, CT. High winds detached the protective metal shroud/casing on the rooftop HVAC condenser unit serving Unit B (Harborview Dental). The detached shroud damaged the immediate surrounding TPO membrane and shorted the condenser motor.' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0009' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'loss_narrative.remediation_actions.1' AS field_path, 'Immediate emergency tarping by Coastal Roofing to prevent water intrusion.' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0010' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'loss_narrative.remediation_actions.2' AS field_path, 'Full replacement of the 5-ton HVAC condenser unit and shroud by Apex Mechanical.' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0011' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'loss_narrative.remediation_actions.3' AS field_path, 'Patching and heat-welding of the affected 10x10 sq. ft. TPO membrane section by Coastal Roofing.' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0012' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'loss_narrative.remediation_actions.4' AS field_path, 'Passed municipal mechanical inspection.' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0013' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'loss_narrative.future_mitigation' AS field_path, 'All remaining RTU shrouds were proactively inspected and retrofitted with reinforced hurricane strapping to prevent future detachment.' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0014' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'loss_narrative.signature_detected' AS field_path, 'true' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0015' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.contractor_name' AS field_path, 'Apex Mechanical & Roofing Contractors' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0016' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.invoice_number' AS field_path, 'INV-2402-991A' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0017' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.invoice_date' AS field_path, '2024-03-05' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0018' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.total_amount' AS field_path, '14250' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0019' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.status' AS field_path, 'Paid in Full' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0020' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.line_items.1.description' AS field_path, 'Emergency service call and roof tarping' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0021' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.line_items.1.amount' AS field_path, '850' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0022' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.line_items.2.description' AS field_path, 'Trane 5-Ton Rooftop Packaged Unit (Condenser only) & Shroud' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0023' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.line_items.2.amount' AS field_path, '9200' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0024' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.line_items.3.description' AS field_path, 'Crane fee for RTU hoist' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0025' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.line_items.3.amount' AS field_path, '1500' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0026' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.line_items.4.description' AS field_path, 'TPO Membrane repair (10x10 heat weld)' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0027' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.line_items.4.amount' AS field_path, '1200' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0028' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.line_items.5.description' AS field_path, 'Labor and municipal permit fees' AS field_value
  UNION ALL
  SELECT 'OCR-NARR-V0029' AS field_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'remediation_proof_invoice.line_items.5.amount' AS field_path, '1500' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0001' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'document_metadata.document_type' AS field_path, 'Tenant Roster & Business Classifications' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0002' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'document_metadata.named_insured' AS field_path, 'Oakridge Plaza Holdings, LLC' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0003' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'document_metadata.property_address' AS field_path, '840 Boston Post Road, Milford, CT 06460' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0004' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'document_metadata.as_of_date' AS field_path, '2026-11-15' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0005' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'building_summary.total_rentable_area_sq_ft' AS field_path, '18500' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0006' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'building_summary.occupied_area_sq_ft' AS field_path, '18500' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0007' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'building_summary.vacant_area_sq_ft' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0008' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'building_summary.vacancy_rate_percentage' AS field_path, '0' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0009' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'building_summary.total_units' AS field_path, '4' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0010' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.1.unit_number' AS field_path, 'A' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0011' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.1.tenant_name' AS field_path, 'Gourmet Corner Market' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0012' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.1.area_sq_ft' AS field_path, '6500' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0013' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.1.percent_of_total_area' AS field_path, '35.1' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0014' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.1.business_classification' AS field_path, 'Retail - Specialty Grocery' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0015' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.1.operations_description' AS field_path, 'Neighborhood market selling fresh produce, pre-packaged foods, and cold deli items. No commercial cooking, deep-fat frying, or grease-laden vapors (electric convection ovens for baking only).' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0016' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.1.lease_expiration' AS field_path, '2028-10-31' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0017' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.2.unit_number' AS field_path, 'B' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0018' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.2.tenant_name' AS field_path, 'Harborview Dental & Orthodontics' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0019' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.2.area_sq_ft' AS field_path, '4500' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0020' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.2.percent_of_total_area' AS field_path, '24.3' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0021' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.2.business_classification' AS field_path, 'Medical Office - Dental Clinic' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0022' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.2.operations_description' AS field_path, 'Outpatient dental clinic. Operates independent dental X-ray equipment. No general anesthesia or overnight patient stays.' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0023' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.2.lease_expiration' AS field_path, '2031-03-31' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0024' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.3.unit_number' AS field_path, 'C' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0025' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.3.tenant_name' AS field_path, 'Coastal Physical Therapy & Wellness' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0026' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.3.area_sq_ft' AS field_path, '4000' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0027' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.3.percent_of_total_area' AS field_path, '21.6' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0028' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.3.business_classification' AS field_path, 'Medical Office - Physical Therapy' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0029' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.3.operations_description' AS field_path, 'Outpatient physical therapy and rehabilitation clinic. Includes standard exercise equipment and treatment tables. No aquatic therapy/pools.' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0030' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.3.lease_expiration' AS field_path, '2029-06-30' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0031' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.4.unit_number' AS field_path, 'D' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0032' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.4.tenant_name' AS field_path, 'Edward Jones Financial Advisory' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0033' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.4.area_sq_ft' AS field_path, '3500' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0034' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.4.percent_of_total_area' AS field_path, '18.9' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0035' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.4.business_classification' AS field_path, 'Professional Office - Financial Services' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0036' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.4.operations_description' AS field_path, 'Standard professional office space for financial planning and wealth management. Low foot traffic, standard office exposures.' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0037' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'tenant_roster.4.lease_expiration' AS field_path, '2027-12-31' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0038' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'certification.certified_by' AS field_path, 'Harbor View Property Management, Inc.' AS field_value
  UNION ALL
  SELECT 'OCR-ROSTER-V0039' AS field_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 'certification.signature_detected' AS field_path, 'true' AS field_value
) s;
INSERT INTO TABLE underwriting.ocr_page
(page_id, document_id, submission_id, page_index, average_page_confidence, minimum_page_confidence)
SELECT * FROM (
  SELECT 'OCR-ACORD-P6' AS page_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 6 AS page_index, CAST(0.952 AS DOUBLE) AS average_page_confidence, CAST(0.768 AS DOUBLE) AS minimum_page_confidence
  UNION ALL
  SELECT 'OCR-ACORD-P7' AS page_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 7 AS page_index, CAST(0.967 AS DOUBLE) AS average_page_confidence, CAST(0.842 AS DOUBLE) AS minimum_page_confidence
  UNION ALL
  SELECT 'OCR-ACORD-P8' AS page_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 8 AS page_index, CAST(0.939 AS DOUBLE) AS average_page_confidence, CAST(0.691 AS DOUBLE) AS minimum_page_confidence
  UNION ALL
  SELECT 'OCR-810-P0' AS page_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, CAST(0.942 AS DOUBLE) AS average_page_confidence, CAST(0.658 AS DOUBLE) AS minimum_page_confidence
  UNION ALL
  SELECT 'OCR-4PT-P0' AS page_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, CAST(0.961 AS DOUBLE) AS average_page_confidence, CAST(0.718 AS DOUBLE) AS minimum_page_confidence
  UNION ALL
  SELECT 'OCR-LOSS-P0' AS page_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, CAST(0.985 AS DOUBLE) AS average_page_confidence, CAST(0.942 AS DOUBLE) AS minimum_page_confidence
  UNION ALL
  SELECT 'OCR-NARR-P0' AS page_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, CAST(0.978 AS DOUBLE) AS average_page_confidence, CAST(0.741 AS DOUBLE) AS minimum_page_confidence
  UNION ALL
  SELECT 'OCR-NARR-P1' AS page_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 1 AS page_index, CAST(0.962 AS DOUBLE) AS average_page_confidence, CAST(0.814 AS DOUBLE) AS minimum_page_confidence
  UNION ALL
  SELECT 'OCR-ROSTER-P0' AS page_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, CAST(0.971 AS DOUBLE) AS average_page_confidence, CAST(0.812 AS DOUBLE) AS minimum_page_confidence
) s;
INSERT INTO TABLE underwriting.ocr_word
(word_id, document_id, submission_id, page_index, word_text, confidence)
SELECT * FROM (
  SELECT 'OCR-ACORD-W6-01' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 6 AS page_index, '$2,000,000' AS word_text, CAST(0.989 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W6-02' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 6 AS page_index, '$1,000,000' AS word_text, CAST(0.991 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W6-03' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 6 AS page_index, '$300,000' AS word_text, CAST(0.984 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W6-04' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 6 AS page_index, '$10,000' AS word_text, CAST(0.987 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W6-05' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 6 AS page_index, '67635' AS word_text, CAST(0.962 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W6-06' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 6 AS page_index, '18,500' AS word_text, CAST(0.985 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W6-07' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 6 AS page_index, '295.40' AS word_text, CAST(0.814 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W6-08' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 6 AS page_index, '$5,465' AS word_text, CAST(0.973 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W6-09' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 6 AS page_index, '46604' AS word_text, CAST(0.958 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W6-10' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 6 AS page_index, '14,200' AS word_text, CAST(0.979 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W6-11' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 6 AS page_index, '55.28' AS word_text, CAST(0.768 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W6-12' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 6 AS page_index, '$785' AS word_text, CAST(0.969 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W7-01' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 7 AS page_index, '100%' AS word_text, CAST(0.993 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W7-02' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 7 AS page_index, '$1,000,000' AS word_text, CAST(0.988 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W7-03' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 7 AS page_index, '[N]' AS word_text, CAST(0.912 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W7-04' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 7 AS page_index, '[Y]' AS word_text, CAST(0.895 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W7-05' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 7 AS page_index, '42' AS word_text, CAST(0.974 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W7-06' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 7 AS page_index, 'hold-harmless.' AS word_text, CAST(0.842 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W8-01' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 8 AS page_index, 'COI' AS word_text, CAST(0.941 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W8-02' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 8 AS page_index, 'Harbor' AS word_text, CAST(0.988 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W8-03' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 8 AS page_index, 'View' AS word_text, CAST(0.985 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W8-04' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 8 AS page_index, 'CRE-2018-44910' AS word_text, CAST(0.904 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W8-05' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 8 AS page_index, 'Elena' AS word_text, CAST(0.738 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W8-06' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 8 AS page_index, 'Rostova' AS word_text, CAST(0.691 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W8-07' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 8 AS page_index, 'Marcus' AS word_text, CAST(0.812 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ACORD-W8-08' AS word_id, 'OCR-ACORD' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 8 AS page_index, 'Vance' AS word_text, CAST(0.795 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-01' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Rental' AS word_text, CAST(0.995 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-02' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Value' AS word_text, CAST(0.991 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-03' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '$435,000' AS word_text, CAST(0.978 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-04' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '$105,000' AS word_text, CAST(0.982 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-05' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '$540,000' AS word_text, CAST(0.985 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-06' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '$12,500' AS word_text, CAST(0.961 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-07' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '$18,500' AS word_text, CAST(0.954 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-08' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '$25,000' AS word_text, CAST(0.966 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-09' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '$4,000' AS word_text, CAST(0.971 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-10' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '$60,000' AS word_text, CAST(0.959 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-11' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '$480,000' AS word_text, CAST(0.989 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-12' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '1/3' AS word_text, CAST(0.742 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-13' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Gourmet' AS word_text, CAST(0.993 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-14' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Corner' AS word_text, CAST(0.994 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-15' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '$156,000' AS word_text, CAST(0.968 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-16' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Elena' AS word_text, CAST(0.712 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-810-W0-17' AS word_id, 'OCR-810' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Rostova' AS word_text, CAST(0.658 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-4PT-W0-01' AS word_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '2021' AS word_text, CAST(0.985 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-4PT-W0-02' AS word_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Full' AS word_text, CAST(0.991 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-4PT-W0-03' AS word_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '2004' AS word_text, CAST(0.988 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-4PT-W0-04' AS word_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Original' AS word_text, CAST(0.952 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-4PT-W0-05' AS word_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '2004' AS word_text, CAST(0.982 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-4PT-W0-06' AS word_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Original' AS word_text, CAST(0.941 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-4PT-W0-07' AS word_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '2023' AS word_text, CAST(0.976 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-4PT-W0-08' AS word_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Partial' AS word_text, CAST(0.965 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-4PT-W0-09' AS word_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'HOI.0004921' AS word_text, CAST(0.892 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-4PT-W0-10' AS word_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'James' AS word_text, CAST(0.742 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-4PT-W0-11' AS word_id, 'OCR-4PT' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'OConnor' AS word_text, CAST(0.718 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-LOSS-W0-01' AS word_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'HARTFORD' AS word_text, CAST(0.998 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-LOSS-W0-02' AS word_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'LOSS' AS word_text, CAST(0.995 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-LOSS-W0-03' AS word_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'EXPERIENCE' AS word_text, CAST(0.992 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-LOSS-W0-04' AS word_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '10/15/2026' AS word_text, CAST(0.988 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-LOSS-W0-05' AS word_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '10/16/2026' AS word_text, CAST(0.987 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-LOSS-W0-06' AS word_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '42-UEN-88412' AS word_text, CAST(0.976 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-LOSS-W0-07' AS word_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '12/01/2025' AS word_text, CAST(0.981 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-LOSS-W0-08' AS word_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '$0.00' AS word_text, CAST(0.99 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-LOSS-W0-09' AS word_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'No' AS word_text, CAST(0.965 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-LOSS-W0-10' AS word_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'claims' AS word_text, CAST(0.958 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-LOSS-W0-11' AS word_id, 'OCR-LOSS' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'reported' AS word_text, CAST(0.942 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W0-01' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'OAKRIDGE' AS word_text, CAST(0.998 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W0-02' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'PLAZA' AS word_text, CAST(0.997 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W0-03' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '02/18/2024' AS word_text, CAST(0.985 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W0-04' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'shroud' AS word_text, CAST(0.942 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W0-05' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'tarping' AS word_text, CAST(0.951 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W0-06' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'retrofitted' AS word_text, CAST(0.932 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W0-07' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Elena' AS word_text, CAST(0.768 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W0-08' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Rostova' AS word_text, CAST(0.741 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W1-01' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 1 AS page_index, 'APEX' AS word_text, CAST(0.995 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W1-02' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 1 AS page_index, 'MECHANICAL' AS word_text, CAST(0.992 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W1-03' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 1 AS page_index, 'INV-2402-991A' AS word_text, CAST(0.976 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W1-04' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 1 AS page_index, '03/05/2024' AS word_text, CAST(0.985 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W1-05' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 1 AS page_index, '$9,200.00' AS word_text, CAST(0.988 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W1-06' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 1 AS page_index, 'Crane' AS word_text, CAST(0.971 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W1-07' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 1 AS page_index, 'hoist' AS word_text, CAST(0.924 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W1-08' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 1 AS page_index, 'weld)' AS word_text, CAST(0.814 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W1-09' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 1 AS page_index, '$14,250.00' AS word_text, CAST(0.991 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-NARR-W1-10' AS word_id, 'OCR-NARR' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 1 AS page_index, 'PAID' AS word_text, CAST(0.994 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ROSTER-W0-01' AS word_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '18,500' AS word_text, CAST(0.988 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ROSTER-W0-02' AS word_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '0.0%' AS word_text, CAST(0.995 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ROSTER-W0-03' AS word_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '6,500' AS word_text, CAST(0.981 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ROSTER-W0-04' AS word_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '35.1%' AS word_text, CAST(0.964 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ROSTER-W0-05' AS word_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '24.3%' AS word_text, CAST(0.957 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ROSTER-W0-06' AS word_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '21.6%' AS word_text, CAST(0.962 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ROSTER-W0-07' AS word_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, '18.9%' AS word_text, CAST(0.955 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ROSTER-W0-08' AS word_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'grease-laden' AS word_text, CAST(0.941 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ROSTER-W0-09' AS word_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'X-ray' AS word_text, CAST(0.938 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ROSTER-W0-10' AS word_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'aquatic' AS word_text, CAST(0.947 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ROSTER-W0-11' AS word_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Chen,' AS word_text, CAST(0.842 AS DOUBLE) AS confidence
  UNION ALL
  SELECT 'OCR-ROSTER-W0-12' AS word_id, 'OCR-ROSTER' AS document_id, CAST(9200 AS BIGINT) AS submission_id, 0 AS page_index, 'Manager' AS word_text, CAST(0.812 AS DOUBLE) AS confidence
) s;

-- Oakridge_Plaza_Statement_of_Values.csv
INSERT INTO TABLE underwriting.statement_of_values
(sov_id, submission_id, loc_number, bldg_number, named_insured, street_address, city, state, zip, subject_of_insurance, occupancy, construction_type, year_built, area_sq_ft, sprinklered, protection_class, limit_amount, valuation, coinsurance, deductible)
SELECT * FROM (
  SELECT 'SOV-9200-1' AS sov_id, CAST(9200 AS BIGINT) AS submission_id, '001' AS loc_number, '001' AS bldg_number, 'Oakridge Plaza Holdings, LLC' AS named_insured, '840 Boston Post Road' AS street_address, 'Milford' AS city, 'CT' AS state, '06460' AS zip, 'Building' AS subject_of_insurance, 'Retail Strip Center' AS occupancy, 'Masonry Non-Combustible (ISO 4)' AS construction_type, 2004 AS year_built, 18500 AS area_sq_ft, TRUE AS sprinklered, '02' AS protection_class, CAST(4250000 AS BIGINT) AS limit_amount, 'RC' AS valuation, '90%' AS coinsurance, 5000 AS deductible
  UNION ALL
  SELECT 'SOV-9200-2' AS sov_id, CAST(9200 AS BIGINT) AS submission_id, '001' AS loc_number, '001' AS bldg_number, 'Oakridge Plaza Holdings, LLC' AS named_insured, '840 Boston Post Road' AS street_address, 'Milford' AS city, 'CT' AS state, '06460' AS zip, 'Business Income & Extra Expense' AS subject_of_insurance, 'Retail Strip Center' AS occupancy, 'Masonry Non-Combustible (ISO 4)' AS construction_type, 2004 AS year_built, 18500 AS area_sq_ft, TRUE AS sprinklered, '02' AS protection_class, CAST(480000 AS BIGINT) AS limit_amount, 'ALS (12 Mos)' AS valuation, '1/3 Monthly' AS coinsurance, 72 AS deductible
  UNION ALL
  SELECT 'SOV-9200-3' AS sov_id, CAST(9200 AS BIGINT) AS submission_id, '001' AS loc_number, '001' AS bldg_number, 'Oakridge Plaza Holdings, LLC' AS named_insured, '840 Boston Post Road' AS street_address, 'Milford' AS city, 'CT' AS state, '06460' AS zip, 'Equipment Breakdown' AS subject_of_insurance, 'Retail Strip Center' AS occupancy, 'Masonry Non-Combustible (ISO 4)' AS construction_type, 2004 AS year_built, 18500 AS area_sq_ft, TRUE AS sprinklered, '02' AS protection_class, CAST(4250000 AS BIGINT) AS limit_amount, 'RC' AS valuation, 'N/A' AS coinsurance, 5000 AS deductible
  UNION ALL
  SELECT 'SOV-9200-4' AS sov_id, CAST(9200 AS BIGINT) AS submission_id, '001' AS loc_number, '001' AS bldg_number, 'Oakridge Plaza Holdings, LLC' AS named_insured, '840 Boston Post Road' AS street_address, 'Milford' AS city, 'CT' AS state, '06460' AS zip, 'Outdoor Signs' AS subject_of_insurance, 'Retail Strip Center' AS occupancy, 'Masonry Non-Combustible (ISO 4)' AS construction_type, 2004 AS year_built, 18500 AS area_sq_ft, TRUE AS sprinklered, '02' AS protection_class, CAST(35000 AS BIGINT) AS limit_amount, 'RC' AS valuation, '80%' AS coinsurance, 1000 AS deductible
) s;

-- businessincome-rentalvalue-scanned.json
INSERT INTO TABLE underwriting.rental_value_worksheet
(worksheet_id, submission_id, form_number, form_edition, worksheet_date, named_insured, premises_number, building_number, premises_address, coverage_type, financial_period, annual_gross_rent, tenant_contributions, fair_rental_value_vacant, total_gross_rental_income, janitorial_services, landscaping_and_snow_removal, utilities, ordinary_payroll, property_management_fees, total_deductions, net_rental_value, selected_limit, monthly_limitation, coinsurance_percentage)
SELECT * FROM (
  SELECT 'WS-810' AS worksheet_id, CAST(9200 AS BIGINT) AS submission_id, 'ACORD 810' AS form_number, '2015/12' AS form_edition, '2026-11-15' AS worksheet_date, 'Oakridge Plaza Holdings, LLC' AS named_insured, '001' AS premises_number, '001' AS building_number, '840 Boston Post Road, Milford, CT 06460' AS premises_address, 'Rental Value Only' AS coverage_type, '12-Month Projection (12/01/2026 to 12/01/2027)' AS financial_period, CAST(435000 AS BIGINT) AS annual_gross_rent, CAST(105000 AS BIGINT) AS tenant_contributions, CAST(0 AS BIGINT) AS fair_rental_value_vacant, CAST(540000 AS BIGINT) AS total_gross_rental_income, CAST(12500 AS BIGINT) AS janitorial_services, CAST(18500 AS BIGINT) AS landscaping_and_snow_removal, CAST(25000 AS BIGINT) AS utilities, CAST(0 AS BIGINT) AS ordinary_payroll, CAST(4000 AS BIGINT) AS property_management_fees, CAST(60000 AS BIGINT) AS total_deductions, CAST(480000 AS BIGINT) AS net_rental_value, CAST(480000 AS BIGINT) AS selected_limit, '1/3' AS monthly_limitation, CAST(NULL AS STRING) AS coinsurance_percentage
) s;
INSERT INTO TABLE underwriting.rental_value_tenant
(tenant_id, worksheet_id, submission_id, unit, tenant_name, square_footage, annual_base_rent)
SELECT * FROM (
  SELECT 'T-810-A' AS tenant_id, 'WS-810' AS worksheet_id, CAST(9200 AS BIGINT) AS submission_id, 'A' AS unit, 'Gourmet Corner Market' AS tenant_name, 6500 AS square_footage, CAST(156000 AS BIGINT) AS annual_base_rent
  UNION ALL
  SELECT 'T-810-B' AS tenant_id, 'WS-810' AS worksheet_id, CAST(9200 AS BIGINT) AS submission_id, 'B' AS unit, 'Harborview Dental & Orthodontics' AS tenant_name, 4500 AS square_footage, CAST(117000 AS BIGINT) AS annual_base_rent
  UNION ALL
  SELECT 'T-810-C' AS tenant_id, 'WS-810' AS worksheet_id, CAST(9200 AS BIGINT) AS submission_id, 'C' AS unit, 'Coastal Physical Therapy & Wellness' AS tenant_name, 4000 AS square_footage, CAST(92000 AS BIGINT) AS annual_base_rent
  UNION ALL
  SELECT 'T-810-D' AS tenant_id, 'WS-810' AS worksheet_id, CAST(9200 AS BIGINT) AS submission_id, 'D' AS unit, 'Edward Jones Financial Advisory' AS tenant_name, 3500 AS square_footage, CAST(70000 AS BIGINT) AS annual_base_rent
) s;

-- 4-point-inspection-scanned.json
INSERT INTO TABLE underwriting.four_point_inspection
(inspection_id, submission_id, form_title, inspection_date, property_address, named_insured, year_built, inspector_name, license_number, company_name, signature_detected, date_signed)
SELECT * FROM (
  SELECT 'FP-9200' AS inspection_id, CAST(9200 AS BIGINT) AS submission_id, '4-POINT SYSTEM UPDATE VERIFICATION' AS form_title, '2026-11-10' AS inspection_date, '840 Boston Post Road, Milford, CT 06460' AS property_address, 'Oakridge Plaza Holdings, LLC' AS named_insured, 2004 AS year_built, 'James OConnor' AS inspector_name, 'HOI.0004921' AS license_number, 'OConnor Commercial Inspections, LLC' AS company_name, TRUE AS signature_detected, '2026-11-10' AS date_signed
) s;
INSERT INTO TABLE underwriting.four_point_system
(system_id, inspection_id, submission_id, system_name, system_type, year_last_updated, update_type, notes)
SELECT * FROM (
  SELECT 'FP-9200-ROOF' AS system_id, 'FP-9200' AS inspection_id, CAST(9200 AS BIGINT) AS submission_id, 'roof' AS system_name, 'TPO Membrane over rigid insulation' AS system_type, 2021 AS year_last_updated, 'Full Replacement' AS update_type, '15-year manufacturer warranty on file. No active leaks detected.' AS notes
  UNION ALL
  SELECT 'FP-9200-PLUMBING' AS system_id, 'FP-9200' AS inspection_id, CAST(9200 AS BIGINT) AS submission_id, 'plumbing' AS system_name, 'Copper supply / PVC drain lines' AS system_type, 2004 AS year_last_updated, 'Original' AS update_type, 'No polybutylene piping present. Backflow preventers inspected annually (last passed 08/2026).' AS notes
  UNION ALL
  SELECT 'FP-9200-ELECTRICAL' AS system_id, 'FP-9200' AS inspection_id, CAST(9200 AS BIGINT) AS submission_id, 'electrical' AS system_name, '100% Copper, 800-amp main service, individual tenant sub-panels' AS system_type, 2004 AS year_last_updated, 'Original' AS update_type, 'No aluminum branch wiring. Thermal infrared scan passed in 2025 with no hotspots.' AS notes
  UNION ALL
  SELECT 'FP-9200-HVAC' AS system_id, 'FP-9200' AS inspection_id, CAST(9200 AS BIGINT) AS submission_id, 'hvac' AS system_name, 'Four (4) rooftop packaged gas/electric units (5 to 7.5 ton)' AS system_type, 2023 AS year_last_updated, 'Partial Replacement' AS update_type, '2 RTUs replaced in 2021; remaining 2 RTUs replaced in 2023. Quarterly preventative maintenance contract in place.' AS notes
) s;

-- loss-run-report.json
INSERT INTO TABLE underwriting.loss_run_report
(report_id, submission_id, carrier, named_insured, valuation_date, report_run_date, total_claims_count, detail_claim_count, total_paid_indemnity, total_paid_expense, total_outstanding_reserve, total_gross_incurred, signature_detected, certification_statement)
SELECT * FROM (
  SELECT 'LR-9200' AS report_id, CAST(9200 AS BIGINT) AS submission_id, 'Hartford Fire Insurance Company' AS carrier, 'Oakridge Plaza Holdings, LLC' AS named_insured, '2026-10-15' AS valuation_date, '2026-10-16' AS report_run_date, 0 AS total_claims_count, 0 AS detail_claim_count, CAST(0 AS BIGINT) AS total_paid_indemnity, CAST(0 AS BIGINT) AS total_paid_expense, CAST(0 AS BIGINT) AS total_outstanding_reserve, CAST(0 AS BIGINT) AS total_gross_incurred, FALSE AS signature_detected, 'This report is a true and accurate summary of claims reported to Hartford Fire Insurance Company as of the valuation date.' AS certification_statement
) s;
INSERT INTO TABLE underwriting.loss_run_policy
(policy_row_id, report_id, submission_id, policy_number, policy_term, line_of_business, total_claims, total_incurred, total_paid, total_reserved, total_recovered)
SELECT * FROM (
  SELECT 'LR-9200-1' AS policy_row_id, 'LR-9200' AS report_id, CAST(9200 AS BIGINT) AS submission_id, '42-UEN-88412' AS policy_number, '12/01/2025 to 12/01/2026' AS policy_term, 'Commercial Package (Property & GL)' AS line_of_business, 0 AS total_claims, CAST(0 AS BIGINT) AS total_incurred, CAST(0 AS BIGINT) AS total_paid, CAST(0 AS BIGINT) AS total_reserved, CAST(0 AS BIGINT) AS total_recovered
  UNION ALL
  SELECT 'LR-9200-2' AS policy_row_id, 'LR-9200' AS report_id, CAST(9200 AS BIGINT) AS submission_id, '42-UEN-88412' AS policy_number, '12/01/2024 to 12/01/2025' AS policy_term, 'Commercial Package (Property & GL)' AS line_of_business, 0 AS total_claims, CAST(0 AS BIGINT) AS total_incurred, CAST(0 AS BIGINT) AS total_paid, CAST(0 AS BIGINT) AS total_reserved, CAST(0 AS BIGINT) AS total_recovered
) s;

-- large-loss-narrative-scanned.json
INSERT INTO TABLE underwriting.large_loss_narrative
(narrative_id, submission_id, named_insured, date_prepared, related_claim_date, related_claim_amount, author, author_title, claim_description, future_mitigation, signature_detected, contractor_name, invoice_number, invoice_date, invoice_total, invoice_status)
SELECT * FROM (
  SELECT 'LL-9200' AS narrative_id, CAST(9200 AS BIGINT) AS submission_id, 'Oakridge Plaza Holdings, LLC' AS named_insured, '2026-11-15' AS date_prepared, '2024-02-18' AS related_claim_date, CAST(14250 AS BIGINT) AS related_claim_amount, 'Elena Rostova' AS author, 'Managing Member' AS author_title, 'On February 18, 2024, a severe winter wind and hail storm passed through Milford, CT. High winds detached the protective metal shroud/casing on the rooftop HVAC condenser unit serving Unit B (Harborview Dental). The detached shroud damaged the immediate surrounding TPO membrane and shorted the condenser motor.' AS claim_description, 'All remaining RTU shrouds were proactively inspected and retrofitted with reinforced hurricane strapping to prevent future detachment.' AS future_mitigation, TRUE AS signature_detected, 'Apex Mechanical & Roofing Contractors' AS contractor_name, 'INV-2402-991A' AS invoice_number, '2024-03-05' AS invoice_date, CAST(14250 AS BIGINT) AS invoice_total, 'Paid in Full' AS invoice_status
) s;
INSERT INTO TABLE underwriting.large_loss_invoice_line
(line_id, narrative_id, submission_id, description, amount)
SELECT * FROM (
  SELECT 'LL-9200-L1' AS line_id, 'LL-9200' AS narrative_id, CAST(9200 AS BIGINT) AS submission_id, 'Emergency service call and roof tarping' AS description, CAST(850 AS BIGINT) AS amount
  UNION ALL
  SELECT 'LL-9200-L2' AS line_id, 'LL-9200' AS narrative_id, CAST(9200 AS BIGINT) AS submission_id, 'Trane 5-Ton Rooftop Packaged Unit (Condenser only) & Shroud' AS description, CAST(9200 AS BIGINT) AS amount
  UNION ALL
  SELECT 'LL-9200-L3' AS line_id, 'LL-9200' AS narrative_id, CAST(9200 AS BIGINT) AS submission_id, 'Crane fee for RTU hoist' AS description, CAST(1500 AS BIGINT) AS amount
  UNION ALL
  SELECT 'LL-9200-L4' AS line_id, 'LL-9200' AS narrative_id, CAST(9200 AS BIGINT) AS submission_id, 'TPO Membrane repair (10x10 heat weld)' AS description, CAST(1200 AS BIGINT) AS amount
  UNION ALL
  SELECT 'LL-9200-L5' AS line_id, 'LL-9200' AS narrative_id, CAST(9200 AS BIGINT) AS submission_id, 'Labor and municipal permit fees' AS description, CAST(1500 AS BIGINT) AS amount
) s;
INSERT INTO TABLE underwriting.large_loss_remediation
(action_id, narrative_id, submission_id, action_text)
SELECT * FROM (
  SELECT 'LL-9200-A1' AS action_id, 'LL-9200' AS narrative_id, CAST(9200 AS BIGINT) AS submission_id, 'Immediate emergency tarping by Coastal Roofing to prevent water intrusion.' AS action_text
  UNION ALL
  SELECT 'LL-9200-A2' AS action_id, 'LL-9200' AS narrative_id, CAST(9200 AS BIGINT) AS submission_id, 'Full replacement of the 5-ton HVAC condenser unit and shroud by Apex Mechanical.' AS action_text
  UNION ALL
  SELECT 'LL-9200-A3' AS action_id, 'LL-9200' AS narrative_id, CAST(9200 AS BIGINT) AS submission_id, 'Patching and heat-welding of the affected 10x10 sq. ft. TPO membrane section by Coastal Roofing.' AS action_text
  UNION ALL
  SELECT 'LL-9200-A4' AS action_id, 'LL-9200' AS narrative_id, CAST(9200 AS BIGINT) AS submission_id, 'Passed municipal mechanical inspection.' AS action_text
) s;

-- tenant-roster-scanned.json
INSERT INTO TABLE underwriting.tenant_roster
(roster_id, submission_id, named_insured, property_address, as_of_date, total_rentable_area_sq_ft, occupied_area_sq_ft, vacant_area_sq_ft, vacancy_rate_percentage, total_units, certified_by, signature_detected)
SELECT * FROM (
  SELECT 'TR-9200' AS roster_id, CAST(9200 AS BIGINT) AS submission_id, 'Oakridge Plaza Holdings, LLC' AS named_insured, '840 Boston Post Road, Milford, CT 06460' AS property_address, '2026-11-15' AS as_of_date, 18500 AS total_rentable_area_sq_ft, 18500 AS occupied_area_sq_ft, 0 AS vacant_area_sq_ft, CAST(0 AS DOUBLE) AS vacancy_rate_percentage, 4 AS total_units, 'Harbor View Property Management, Inc.' AS certified_by, TRUE AS signature_detected
) s;
INSERT INTO TABLE underwriting.tenant_roster_unit
(unit_id, roster_id, submission_id, unit_number, tenant_name, area_sq_ft, percent_of_total_area, business_classification, operations_description, lease_expiration)
SELECT * FROM (
  SELECT 'TR-9200-A' AS unit_id, 'TR-9200' AS roster_id, CAST(9200 AS BIGINT) AS submission_id, 'A' AS unit_number, 'Gourmet Corner Market' AS tenant_name, 6500 AS area_sq_ft, CAST(35.1 AS DOUBLE) AS percent_of_total_area, 'Retail - Specialty Grocery' AS business_classification, 'Neighborhood market selling fresh produce, pre-packaged foods, and cold deli items. No commercial cooking, deep-fat frying, or grease-laden vapors (electric convection ovens for baking only).' AS operations_description, '2028-10-31' AS lease_expiration
  UNION ALL
  SELECT 'TR-9200-B' AS unit_id, 'TR-9200' AS roster_id, CAST(9200 AS BIGINT) AS submission_id, 'B' AS unit_number, 'Harborview Dental & Orthodontics' AS tenant_name, 4500 AS area_sq_ft, CAST(24.3 AS DOUBLE) AS percent_of_total_area, 'Medical Office - Dental Clinic' AS business_classification, 'Outpatient dental clinic. Operates independent dental X-ray equipment. No general anesthesia or overnight patient stays.' AS operations_description, '2031-03-31' AS lease_expiration
  UNION ALL
  SELECT 'TR-9200-C' AS unit_id, 'TR-9200' AS roster_id, CAST(9200 AS BIGINT) AS submission_id, 'C' AS unit_number, 'Coastal Physical Therapy & Wellness' AS tenant_name, 4000 AS area_sq_ft, CAST(21.6 AS DOUBLE) AS percent_of_total_area, 'Medical Office - Physical Therapy' AS business_classification, 'Outpatient physical therapy and rehabilitation clinic. Includes standard exercise equipment and treatment tables. No aquatic therapy/pools.' AS operations_description, '2029-06-30' AS lease_expiration
  UNION ALL
  SELECT 'TR-9200-D' AS unit_id, 'TR-9200' AS roster_id, CAST(9200 AS BIGINT) AS submission_id, 'D' AS unit_number, 'Edward Jones Financial Advisory' AS tenant_name, 3500 AS area_sq_ft, CAST(18.9 AS DOUBLE) AS percent_of_total_area, 'Professional Office - Financial Services' AS business_classification, 'Standard professional office space for financial planning and wealth management. Low foot traffic, standard office exposures.' AS operations_description, '2027-12-31' AS lease_expiration
) s;
