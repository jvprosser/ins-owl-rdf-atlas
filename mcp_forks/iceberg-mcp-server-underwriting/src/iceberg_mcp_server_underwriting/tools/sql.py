"""Curated Impala SQL for submission spine, signals, and governed writes."""

from __future__ import annotations

import re
from typing import Any

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_ident(name: str, kind: str = "identifier") -> str:
    if not _IDENT_RE.match(name):
        raise ValueError(f"Invalid {kind}: {name!r}")
    return name


def validate_min_confidence(value: Any, default: float = 0.8) -> float:
    """Review line for low-confidence words. Omitted uses 0.8."""
    if value in (None, ""):
        score = default
    else:
        try:
            score = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "min_confidence_score must be a number from 0 to 1"
            ) from exc
    if score != score or score < 0 or score > 1:
        raise ValueError("min_confidence_score must be a number from 0 to 1")
    return score


def validate_submission_id(value: Any) -> int:
    """Surrogate submission id. SUB-9200 is the business key, not this value."""
    text = str(value if value is not None else "").strip()
    if not text.isdigit():
        raise ValueError("submission id must be an integer (9200)")
    return int(text)


def sql_quote(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "t", "1", "yes"}:
        return True
    if text in {"false", "f", "0", "no"}:
        return False
    return bool(value)


def submission_spine_sql(submission_id: str, database: str) -> str:
    db = validate_ident(database, "database")
    sid = sql_quote(validate_submission_id(submission_id))
    return f"""
SELECT
  s.submission_id,
  s.submission_number,
  s.producer_id,
  s.applicant_tax_id,
  s.line_of_business,
  s.class_code,
  s.naics_code,
  s.total_insured_value,
  s.submission_timestamp,
  s.submission_status_code
FROM {db}.submissions s
WHERE s.submission_id = {sid}
LIMIT 1
""".strip()


def submission_snapshot_sql(submission_id: str, database: str) -> str:
    """Spine plus the signal columns the playbook and rate table read."""
    db = validate_ident(database, "database")
    sid = sql_quote(validate_submission_id(submission_id))
    return f"""
SELECT
  s.submission_id,
  s.submission_number,
  s.line_of_business,
  s.class_code,
  s.naics_code,
  CASE
    WHEN sov.submission_id IS NOT NULL THEN sov.sov_tiv
    ELSE s.total_insured_value
  END AS total_insured_value,
  s.submission_status_code,
  COALESCE(s.has_ofac_match, FALSE) AS has_ofac_match,
  COALESCE(s.siu_score, 0) AS siu_score,
  COALESCE(s.tax_lien_unresolved, FALSE) AS tax_lien_unresolved,
  COALESCE(p.is_in_flood_plain, FALSE) AS is_in_flood_plain,
  COALESCE(p.inspection_completed, FALSE) AS inspection_completed,
  p.flood_zone,
  COALESCE(p.has_survey_on_file, FALSE) AS has_survey_on_file,
  COALESCE(p.survey_age_months, 0) AS survey_age_months,
  COALESCE(p.wind_tier, 0) AS wind_tier,
  COALESCE(p.has_recent_cat_run, FALSE) AS has_recent_cat_run,
  CASE
    WHEN sov.submission_id IS NULL THEN p.construction_type
    WHEN INSTR(LOWER(sov.construction_type), 'iso 1') > 0
      OR (
        INSTR(LOWER(sov.construction_type), 'frame') > 0
        AND INSTR(LOWER(sov.construction_type), 'masonry') = 0
      )
      THEN 'FRAME'
    WHEN INSTR(LOWER(sov.construction_type), 'iso 4') > 0
      OR INSTR(LOWER(sov.construction_type), 'masonry') > 0
      THEN 'MASONRY'
    ELSE p.construction_type
  END AS construction_type,
  COALESCE(
    CASE WHEN sov.submission_id IS NOT NULL THEN sov.year_built ELSE p.year_built END,
    0
  ) AS year_built,
  CASE
    WHEN fp.submission_id IS NOT NULL THEN COALESCE(fp.electrical_updated, 0) = 1
    ELSE COALESCE(p.wiring_updated, FALSE)
  END AS wiring_updated,
  CASE
    WHEN sov.submission_id IS NULL THEN p.protection_class
    WHEN regexp_extract(sov.protection_class, '^0*([0-9]+)$', 1) != ''
      THEN regexp_extract(sov.protection_class, '^0*([0-9]+)$', 1)
    ELSE sov.protection_class
  END AS protection_class,
  CASE
    WHEN sov.submission_id IS NOT NULL THEN sov.sprinklered_flag = 1
    ELSE COALESCE(p.has_sprinklers, FALSE)
  END AS has_sprinklers,
  COALESCE(
    CASE WHEN sov.submission_id IS NOT NULL THEN sov.area_sq_ft ELSE p.square_footage END,
    0
  ) AS square_footage,
  COALESCE(l.prior_claims_count, 0) AS prior_claims_count,
  COALESCE(l.claims_count_36m, 0) AS claims_count_36m,
  COALESCE(l.total_incurred_36m, 0) AS total_incurred_36m,
  COALESCE(l.has_open_loss_past_36m, FALSE) AS has_open_loss_past_36m,
  l.financial_stability_tier,
  COALESCE(l.financial_score, 0) AS financial_score,
  CASE WHEN r.party_id IS NOT NULL THEN TRUE ELSE FALSE END AS has_underwriter,
  CASE WHEN ocr.submission_id IS NOT NULL THEN TRUE ELSE FALSE END AS ocr_document_present,
  COALESCE(ocr.min_ocr_confidence, 1.0) AS min_ocr_confidence,
  COALESCE(low.low_ocr_spans, '') AS low_ocr_spans,
  CASE WHEN sov.submission_id IS NOT NULL THEN TRUE ELSE FALSE END AS sov_present,
  COALESCE(sov.min_coinsurance_pct, 100) AS sov_min_coinsurance_pct,
  CASE
    WHEN sov.submission_id IS NULL THEN FALSE
    WHEN sov.building_rows = 0 OR sov.blank_limits > 0 OR sov.blank_coinsurance > 0 THEN TRUE
    ELSE FALSE
  END AS sov_schedule_incomplete,
  CASE WHEN rv.submission_id IS NOT NULL THEN TRUE ELSE FALSE END AS rental_worksheet_present,
  CASE
    WHEN rv.submission_id IS NULL THEN FALSE
    WHEN COALESCE(rv.annual_gross_rent, 0) + COALESCE(rv.tenant_contributions, 0) + COALESCE(rv.fair_rental_value_vacant, 0) != COALESCE(rv.total_gross, 0) THEN TRUE
    WHEN COALESCE(rv.janitorial_services, 0) + COALESCE(rv.landscaping, 0) + COALESCE(rv.utilities, 0) + COALESCE(rv.ordinary_payroll, 0) + COALESCE(rv.management_fees, 0) != COALESCE(rv.total_deductions, 0) THEN TRUE
    WHEN COALESCE(rv.total_gross, 0) - COALESCE(rv.total_deductions, 0) != COALESCE(rv.net_rental_value, 0) THEN TRUE
    WHEN COALESCE(rv.net_rental_value, 0) != COALESCE(rv.selected_limit, 0) THEN TRUE
    WHEN COALESCE(rv.rent_sum, 0) != COALESCE(rv.annual_gross_rent, 0) THEN TRUE
    WHEN sov.submission_id IS NOT NULL AND COALESCE(sov.bi_limit, 0) > 0 AND COALESCE(rv.selected_limit, 0) != sov.bi_limit THEN TRUE
    WHEN sov.submission_id IS NOT NULL AND COALESCE(sov.bi_limit, 0) > 0 AND TRIM(COALESCE(rv.monthly_limitation, '')) != '' AND INSTR(COALESCE(sov.bi_coinsurance, ''), rv.monthly_limitation) = 0 THEN TRUE
    WHEN sov.submission_id IS NOT NULL AND COALESCE(sov.area_sq_ft, 0) > 0 AND COALESCE(rv.sq_ft_sum, 0) != sov.area_sq_ft THEN TRUE
    ELSE FALSE
  END AS rental_needs_review,
  CASE
    WHEN rv.submission_id IS NULL THEN ''
    WHEN COALESCE(rv.annual_gross_rent, 0) + COALESCE(rv.tenant_contributions, 0) + COALESCE(rv.fair_rental_value_vacant, 0) != COALESCE(rv.total_gross, 0) THEN 'gross rental income does not foot'
    WHEN COALESCE(rv.janitorial_services, 0) + COALESCE(rv.landscaping, 0) + COALESCE(rv.utilities, 0) + COALESCE(rv.ordinary_payroll, 0) + COALESCE(rv.management_fees, 0) != COALESCE(rv.total_deductions, 0) THEN 'deductions do not foot'
    WHEN COALESCE(rv.total_gross, 0) - COALESCE(rv.total_deductions, 0) != COALESCE(rv.net_rental_value, 0) THEN 'net rental value does not foot'
    WHEN COALESCE(rv.net_rental_value, 0) != COALESCE(rv.selected_limit, 0) THEN 'selected limit does not match net rental value'
    WHEN COALESCE(rv.rent_sum, 0) != COALESCE(rv.annual_gross_rent, 0) THEN 'rent roll does not match annual gross rent'
    WHEN sov.submission_id IS NOT NULL AND COALESCE(sov.bi_limit, 0) > 0 AND COALESCE(rv.selected_limit, 0) != sov.bi_limit THEN 'selected limit does not match the business income schedule'
    WHEN sov.submission_id IS NOT NULL AND COALESCE(sov.bi_limit, 0) > 0 AND TRIM(COALESCE(rv.monthly_limitation, '')) != '' AND INSTR(COALESCE(sov.bi_coinsurance, ''), rv.monthly_limitation) = 0 THEN 'monthly limitation is not on the business income coinsurance'
    WHEN sov.submission_id IS NOT NULL AND COALESCE(sov.area_sq_ft, 0) > 0 AND COALESCE(rv.sq_ft_sum, 0) != sov.area_sq_ft THEN 'rent roll area does not match the building area'
    ELSE ''
  END AS rental_review_detail,
  CASE WHEN fp.submission_id IS NOT NULL THEN TRUE ELSE FALSE END AS four_point_present,
  CASE
    WHEN fp.submission_id IS NULL THEN FALSE
    WHEN COALESCE(fp.roof_rows, 0) = 0 OR COALESCE(fp.plumbing_rows, 0) = 0 OR COALESCE(fp.electrical_rows, 0) = 0 OR COALESCE(fp.hvac_rows, 0) = 0 THEN TRUE
    WHEN COALESCE(fp.year_built, 0) > 0 AND COALESCE(CASE WHEN sov.submission_id IS NOT NULL THEN sov.year_built ELSE p.year_built END, 0) > 0 AND fp.year_built != CASE WHEN sov.submission_id IS NOT NULL THEN sov.year_built ELSE p.year_built END THEN TRUE
    WHEN INSTR(COALESCE(fp.electrical_text, ''), 'aluminum') > 0 AND INSTR(COALESCE(fp.electrical_text, ''), 'no aluminum') = 0 THEN TRUE
    WHEN INSTR(COALESCE(fp.plumbing_text, ''), 'polybutylene') > 0 AND INSTR(COALESCE(fp.plumbing_text, ''), 'no polybutylene') = 0 THEN TRUE
    ELSE FALSE
  END AS four_point_needs_review,
  CASE
    WHEN fp.submission_id IS NULL THEN ''
    WHEN COALESCE(fp.roof_rows, 0) = 0 OR COALESCE(fp.plumbing_rows, 0) = 0 OR COALESCE(fp.electrical_rows, 0) = 0 OR COALESCE(fp.hvac_rows, 0) = 0 THEN 'a roof, plumbing, electrical, or hvac row is missing'
    WHEN COALESCE(fp.year_built, 0) > 0 AND COALESCE(CASE WHEN sov.submission_id IS NOT NULL THEN sov.year_built ELSE p.year_built END, 0) > 0 AND fp.year_built != CASE WHEN sov.submission_id IS NOT NULL THEN sov.year_built ELSE p.year_built END THEN 'inspection year built does not match the schedule'
    WHEN INSTR(COALESCE(fp.electrical_text, ''), 'aluminum') > 0 AND INSTR(COALESCE(fp.electrical_text, ''), 'no aluminum') = 0 THEN 'electrical notes report aluminum wiring'
    WHEN INSTR(COALESCE(fp.plumbing_text, ''), 'polybutylene') > 0 AND INSTR(COALESCE(fp.plumbing_text, ''), 'no polybutylene') = 0 THEN 'plumbing notes report polybutylene'
    ELSE ''
  END AS four_point_review_detail,
  CASE WHEN lr.submission_id IS NOT NULL THEN TRUE ELSE FALSE END AS loss_run_present,
  CASE
    WHEN lr.submission_id IS NULL THEN FALSE
    WHEN COALESCE(lr.signature_flag, 0) = 0 THEN TRUE
    WHEN COALESCE(lr.policy_claims, 0) != COALESCE(lr.total_claims_count, 0) THEN TRUE
    WHEN COALESCE(lr.policy_incurred, 0) != COALESCE(lr.total_gross_incurred, 0) THEN TRUE
    WHEN COALESCE(lr.policy_paid, 0) != COALESCE(lr.total_paid_indemnity, 0) + COALESCE(lr.total_paid_expense, 0) THEN TRUE
    WHEN COALESCE(lr.policy_reserved, 0) != COALESCE(lr.total_outstanding_reserve, 0) THEN TRUE
    WHEN COALESCE(lr.detail_claim_count, 0) != COALESCE(lr.total_claims_count, 0) THEN TRUE
    ELSE FALSE
  END AS loss_run_needs_review,
  CASE
    WHEN lr.submission_id IS NULL THEN ''
    WHEN COALESCE(lr.signature_flag, 0) = 0 THEN 'loss run has no authorized signature'
    WHEN COALESCE(lr.policy_claims, 0) != COALESCE(lr.total_claims_count, 0) THEN 'policy claim counts do not match the loss run total'
    WHEN COALESCE(lr.policy_incurred, 0) != COALESCE(lr.total_gross_incurred, 0) THEN 'policy incurred does not match the loss run total'
    WHEN COALESCE(lr.policy_paid, 0) != COALESCE(lr.total_paid_indemnity, 0) + COALESCE(lr.total_paid_expense, 0) THEN 'policy paid does not match the loss run total'
    WHEN COALESCE(lr.policy_reserved, 0) != COALESCE(lr.total_outstanding_reserve, 0) THEN 'policy reserves do not match the loss run total'
    WHEN COALESCE(lr.detail_claim_count, 0) != COALESCE(lr.total_claims_count, 0) THEN 'claim detail count does not match the loss run total'
    ELSE ''
  END AS loss_run_review_detail,
  CASE WHEN ll.submission_id IS NOT NULL THEN TRUE ELSE FALSE END AS large_loss_present,
  CASE
    WHEN ll.submission_id IS NULL THEN FALSE
    WHEN COALESCE(ll.signature_flag, 0) = 0 THEN TRUE
    WHEN COALESCE(ll.line_sum, 0) != COALESCE(ll.invoice_total, 0) THEN TRUE
    WHEN COALESCE(ll.claim_amount, 0) != COALESCE(ll.invoice_total, 0) THEN TRUE
    WHEN COALESCE(ll.invoice_status, '') != 'paid in full' THEN TRUE
    WHEN COALESCE(ll.blank_description, 0) = 1 THEN TRUE
    WHEN COALESCE(span.claim_in_term, 0) = 1 AND COALESCE(lr.total_claims_count, 0) = 0 AND COALESCE(lr.total_gross_incurred, 0) = 0 AND COALESCE(ll.claim_amount, 0) > 0 THEN TRUE
    ELSE FALSE
  END AS large_loss_needs_review,
  CASE
    WHEN ll.submission_id IS NULL THEN ''
    WHEN COALESCE(ll.signature_flag, 0) = 0 THEN 'large loss narrative has no signature'
    WHEN COALESCE(ll.line_sum, 0) != COALESCE(ll.invoice_total, 0) THEN 'invoice lines do not match the invoice total'
    WHEN COALESCE(ll.claim_amount, 0) != COALESCE(ll.invoice_total, 0) THEN 'claim amount does not match the invoice total'
    WHEN COALESCE(ll.invoice_status, '') != 'paid in full' THEN 'remediation invoice is not paid in full'
    WHEN COALESCE(ll.blank_description, 0) = 1 THEN 'claim description is blank'
    WHEN COALESCE(span.claim_in_term, 0) = 1 AND COALESCE(lr.total_claims_count, 0) = 0 AND COALESCE(lr.total_gross_incurred, 0) = 0 AND COALESCE(ll.claim_amount, 0) > 0 THEN 'loss date falls in a loss run period that shows no losses'
    ELSE ''
  END AS large_loss_review_detail,
  CASE WHEN tr.submission_id IS NOT NULL THEN TRUE ELSE FALSE END AS tenant_roster_present,
  CASE
    WHEN tr.submission_id IS NULL THEN FALSE
    WHEN COALESCE(tr.signature_flag, 0) = 0 THEN TRUE
    WHEN COALESCE(tr.unit_area_sum, 0) != COALESCE(tr.total_area, 0) THEN TRUE
    WHEN COALESCE(tr.occupied_area, 0) + COALESCE(tr.vacant_area, 0) != COALESCE(tr.total_area, 0) THEN TRUE
    WHEN COALESCE(tr.unit_count, 0) != COALESCE(tr.total_units, 0) THEN TRUE
    WHEN COALESCE(tr.vacant_area, 0) = 0 AND COALESCE(tr.vacancy_rate, 0) > 0 THEN TRUE
    WHEN COALESCE(tr.vacant_area, 0) > 0 AND COALESCE(tr.vacancy_rate, 0) = 0 THEN TRUE
    WHEN COALESCE(tr.percent_off, 0) = 1 THEN TRUE
    WHEN COALESCE(tr.cooking_flag, 0) = 1 THEN TRUE
    WHEN sov.submission_id IS NOT NULL AND COALESCE(sov.area_sq_ft, 0) > 0 AND COALESCE(tr.total_area, 0) != sov.area_sq_ft THEN TRUE
    WHEN COALESCE(rc.rental_count, 0) > 0 AND (rc.rental_count != COALESCE(tr.unit_count, 0) OR COALESCE(tm.unit_mismatch, 0) = 1) THEN TRUE
    ELSE FALSE
  END AS tenant_roster_needs_review,
  CASE
    WHEN tr.submission_id IS NULL THEN ''
    WHEN COALESCE(tr.signature_flag, 0) = 0 THEN 'tenant roster has no signature'
    WHEN COALESCE(tr.unit_area_sum, 0) != COALESCE(tr.total_area, 0) THEN 'unit areas do not match the rentable area'
    WHEN COALESCE(tr.occupied_area, 0) + COALESCE(tr.vacant_area, 0) != COALESCE(tr.total_area, 0) THEN 'occupied and vacant area do not match the rentable area'
    WHEN COALESCE(tr.unit_count, 0) != COALESCE(tr.total_units, 0) THEN 'unit count does not match the roster summary'
    WHEN COALESCE(tr.vacant_area, 0) = 0 AND COALESCE(tr.vacancy_rate, 0) > 0 THEN 'vacancy rate does not match the vacant area'
    WHEN COALESCE(tr.vacant_area, 0) > 0 AND COALESCE(tr.vacancy_rate, 0) = 0 THEN 'vacancy rate does not match the vacant area'
    WHEN COALESCE(tr.percent_off, 0) = 1 THEN 'a unit share of area does not match its square footage'
    WHEN COALESCE(tr.cooking_flag, 0) = 1 THEN 'a tenant describes commercial cooking'
    WHEN sov.submission_id IS NOT NULL AND COALESCE(sov.area_sq_ft, 0) > 0 AND COALESCE(tr.total_area, 0) != sov.area_sq_ft THEN 'roster area does not match the statement of values'
    WHEN COALESCE(rc.rental_count, 0) > 0 AND (rc.rental_count != COALESCE(tr.unit_count, 0) OR COALESCE(tm.unit_mismatch, 0) = 1) THEN 'roster does not match the rental value rent roll'
    ELSE ''
  END AS tenant_roster_review_detail
FROM {db}.submissions s
LEFT JOIN {db}.property_risk_scores p
  ON p.submission_id = s.submission_id
LEFT JOIN {db}.loss_history_summary l
  ON l.submission_id = s.submission_id
LEFT JOIN {db}.submission_party_role r
  ON r.submission_id = s.submission_id
 AND r.role_type_code = 'UNDERWRITER'
 AND r.is_current_assignment = TRUE
LEFT JOIN (
  SELECT
    d.submission_id,
    MIN(w.confidence) AS min_ocr_confidence
  FROM {db}.ocr_document d
  LEFT JOIN {db}.ocr_word w
    ON w.document_id = d.document_id
  GROUP BY d.submission_id
) ocr
  ON ocr.submission_id = s.submission_id
LEFT JOIN (
  SELECT
    submission_id,
    GROUP_CONCAT(
      CONCAT(
        'page ', CAST(page_index AS STRING), ' ',
        word_text, ' ',
        CAST(confidence AS STRING)
      ),
      '; '
    ) AS low_ocr_spans
  FROM {db}.ocr_word
  WHERE confidence < 0.8
  GROUP BY submission_id
) low
  ON low.submission_id = s.submission_id
LEFT JOIN (
  SELECT
    submission_id,
    SUM(
      CASE
        WHEN subject_of_insurance != 'Equipment Breakdown' THEN COALESCE(limit_amount, 0)
        ELSE 0
      END
    ) AS sov_tiv,
    MIN(
      CASE
        WHEN regexp_extract(coinsurance, '^([0-9]+)%$', 1) != ''
        THEN CAST(regexp_extract(coinsurance, '^([0-9]+)%$', 1) AS INT)
      END
    ) AS min_coinsurance_pct,
    SUM(CASE WHEN subject_of_insurance = 'Building' THEN 1 ELSE 0 END) AS building_rows,
    SUM(CASE WHEN limit_amount IS NULL OR limit_amount <= 0 THEN 1 ELSE 0 END) AS blank_limits,
    SUM(CASE WHEN coinsurance IS NULL OR TRIM(coinsurance) = '' THEN 1 ELSE 0 END) AS blank_coinsurance,
    MAX(construction_type) AS construction_type,
    MAX(year_built) AS year_built,
    MAX(area_sq_ft) AS area_sq_ft,
    SUM(
      CASE
        WHEN subject_of_insurance = 'Business Income & Extra Expense' THEN COALESCE(limit_amount, 0)
        ELSE 0
      END
    ) AS bi_limit,
    MAX(
      CASE
        WHEN subject_of_insurance = 'Business Income & Extra Expense' THEN coinsurance
      END
    ) AS bi_coinsurance,
    MAX(protection_class) AS protection_class,
    MAX(CASE WHEN sprinklered THEN 1 ELSE 0 END) AS sprinklered_flag
  FROM {db}.statement_of_values
  GROUP BY submission_id
) sov
  ON sov.submission_id = s.submission_id
LEFT JOIN (
  SELECT
    w.submission_id,
    MAX(w.selected_limit) AS selected_limit,
    MAX(w.monthly_limitation) AS monthly_limitation,
    MAX(w.net_rental_value) AS net_rental_value,
    MAX(w.annual_gross_rent) AS annual_gross_rent,
    MAX(w.total_gross_rental_income) AS total_gross,
    MAX(w.total_deductions) AS total_deductions,
    MAX(w.tenant_contributions) AS tenant_contributions,
    MAX(w.fair_rental_value_vacant) AS fair_rental_value_vacant,
    MAX(w.janitorial_services) AS janitorial_services,
    MAX(w.landscaping_and_snow_removal) AS landscaping,
    MAX(w.utilities) AS utilities,
    MAX(w.ordinary_payroll) AS ordinary_payroll,
    MAX(w.property_management_fees) AS management_fees,
    COALESCE(SUM(t.annual_base_rent), 0) AS rent_sum,
    COALESCE(SUM(t.square_footage), 0) AS sq_ft_sum
  FROM {db}.rental_value_worksheet w
  LEFT JOIN {db}.rental_value_tenant t
    ON t.worksheet_id = w.worksheet_id
  GROUP BY w.submission_id
) rv
  ON rv.submission_id = s.submission_id
LEFT JOIN (
  SELECT
    i.submission_id,
    MAX(i.year_built) AS year_built,
    MAX(
      CASE
        WHEN s.system_name = 'electrical' AND LOWER(COALESCE(s.update_type, '')) != 'original' THEN 1
        ELSE 0
      END
    ) AS electrical_updated,
    SUM(CASE WHEN s.system_name = 'roof' THEN 1 ELSE 0 END) AS roof_rows,
    SUM(CASE WHEN s.system_name = 'plumbing' THEN 1 ELSE 0 END) AS plumbing_rows,
    SUM(CASE WHEN s.system_name = 'electrical' THEN 1 ELSE 0 END) AS electrical_rows,
    SUM(CASE WHEN s.system_name = 'hvac' THEN 1 ELSE 0 END) AS hvac_rows,
    MAX(
      CASE
        WHEN s.system_name = 'electrical'
        THEN LOWER(CONCAT(COALESCE(s.system_type, ''), ' ', COALESCE(s.notes, '')))
      END
    ) AS electrical_text,
    MAX(
      CASE
        WHEN s.system_name = 'plumbing'
        THEN LOWER(CONCAT(COALESCE(s.system_type, ''), ' ', COALESCE(s.notes, '')))
      END
    ) AS plumbing_text
  FROM {db}.four_point_inspection i
  LEFT JOIN {db}.four_point_system s
    ON s.inspection_id = i.inspection_id
  GROUP BY i.submission_id
) fp
  ON fp.submission_id = s.submission_id
LEFT JOIN (
  SELECT
    r.submission_id,
    MAX(CASE WHEN r.signature_detected THEN 1 ELSE 0 END) AS signature_flag,
    MAX(r.total_claims_count) AS total_claims_count,
    MAX(r.detail_claim_count) AS detail_claim_count,
    MAX(r.total_gross_incurred) AS total_gross_incurred,
    MAX(r.total_paid_indemnity) AS total_paid_indemnity,
    MAX(r.total_paid_expense) AS total_paid_expense,
    MAX(r.total_outstanding_reserve) AS total_outstanding_reserve,
    COALESCE(SUM(p.total_claims), 0) AS policy_claims,
    COALESCE(SUM(p.total_incurred), 0) AS policy_incurred,
    COALESCE(SUM(p.total_paid), 0) AS policy_paid,
    COALESCE(SUM(p.total_reserved), 0) AS policy_reserved
  FROM {db}.loss_run_report r
  LEFT JOIN {db}.loss_run_policy p
    ON p.report_id = r.report_id
  GROUP BY r.submission_id
) lr
  ON lr.submission_id = s.submission_id
LEFT JOIN (
  SELECT
    n.submission_id,
    MAX(n.related_claim_amount) AS claim_amount,
    MAX(CASE WHEN n.signature_detected THEN 1 ELSE 0 END) AS signature_flag,
    MAX(n.invoice_total) AS invoice_total,
    MAX(LOWER(COALESCE(n.invoice_status, ''))) AS invoice_status,
    MAX(CASE WHEN TRIM(COALESCE(n.claim_description, '')) = '' THEN 1 ELSE 0 END) AS blank_description,
    COALESCE(SUM(li.amount), 0) AS line_sum
  FROM {db}.large_loss_narrative n
  LEFT JOIN {db}.large_loss_invoice_line li
    ON li.narrative_id = n.narrative_id
  GROUP BY n.submission_id
) ll
  ON ll.submission_id = s.submission_id
LEFT JOIN (
  SELECT
    p.submission_id,
    MAX(
      CASE
        WHEN unix_timestamp(n.related_claim_date, 'yyyy-MM-dd') >= unix_timestamp(regexp_extract(p.policy_term, '^([0-9]{2}/[0-9]{2}/[0-9]{4})', 1), 'MM/dd/yyyy')
         AND unix_timestamp(n.related_claim_date, 'yyyy-MM-dd') < unix_timestamp(regexp_extract(p.policy_term, 'to ([0-9]{2}/[0-9]{2}/[0-9]{4})$', 1), 'MM/dd/yyyy')
        THEN 1
        ELSE 0
      END
    ) AS claim_in_term
  FROM {db}.loss_run_policy p
  INNER JOIN {db}.large_loss_narrative n
    ON n.submission_id = p.submission_id
  GROUP BY p.submission_id
) span
  ON span.submission_id = s.submission_id
LEFT JOIN (
  SELECT
    d.submission_id,
    MAX(d.total_rentable_area_sq_ft) AS total_area,
    MAX(d.occupied_area_sq_ft) AS occupied_area,
    MAX(d.vacant_area_sq_ft) AS vacant_area,
    MAX(d.vacancy_rate_percentage) AS vacancy_rate,
    MAX(d.total_units) AS total_units,
    MAX(CASE WHEN d.signature_detected THEN 1 ELSE 0 END) AS signature_flag,
    COALESCE(SUM(u.area_sq_ft), 0) AS unit_area_sum,
    COUNT(u.unit_id) AS unit_count,
    MAX(
      CASE
        WHEN COALESCE(d.total_rentable_area_sq_ft, 0) > 0
         AND ABS(u.percent_of_total_area - (u.area_sq_ft * 100.0 / d.total_rentable_area_sq_ft)) > 0.2
        THEN 1
        ELSE 0
      END
    ) AS percent_off,
    MAX(
      CASE
        WHEN INSTR(LOWER(COALESCE(u.operations_description, '')), 'commercial cooking') > 0
         AND INSTR(LOWER(COALESCE(u.operations_description, '')), 'no commercial cooking') = 0
        THEN 1
        WHEN INSTR(LOWER(COALESCE(u.operations_description, '')), 'deep-fat') > 0
         AND INSTR(LOWER(COALESCE(u.operations_description, '')), 'no commercial cooking') = 0
        THEN 1
        ELSE 0
      END
    ) AS cooking_flag
  FROM {db}.tenant_roster d
  LEFT JOIN {db}.tenant_roster_unit u
    ON u.roster_id = d.roster_id
  GROUP BY d.submission_id
) tr
  ON tr.submission_id = s.submission_id
LEFT JOIN (
  SELECT submission_id, COUNT(*) AS rental_count
  FROM {db}.rental_value_tenant
  GROUP BY submission_id
) rc
  ON rc.submission_id = s.submission_id
LEFT JOIN (
  SELECT
    u.submission_id,
    MAX(
      CASE
        WHEN rv.unit IS NULL
          OR rv.square_footage != u.area_sq_ft
          OR LOWER(COALESCE(rv.tenant_name, '')) != LOWER(COALESCE(u.tenant_name, ''))
        THEN 1
        ELSE 0
      END
    ) AS unit_mismatch
  FROM {db}.tenant_roster_unit u
  INNER JOIN (
    SELECT submission_id
    FROM {db}.rental_value_tenant
    GROUP BY submission_id
  ) has_rv
    ON has_rv.submission_id = u.submission_id
  LEFT JOIN {db}.rental_value_tenant rv
    ON rv.submission_id = u.submission_id
   AND rv.unit = u.unit_number
  GROUP BY u.submission_id
) tm
  ON tm.submission_id = s.submission_id
WHERE s.submission_id = {sid}
LIMIT 1
""".strip()


def list_low_confidence_fields_sql(
    submission_id: str,
    database: str,
    min_confidence_score: Any = None,
) -> str:
    """Words below the score, joined to the field value that contains each word."""
    db = validate_ident(database, "database")
    sid = sql_quote(validate_submission_id(submission_id))
    score = validate_min_confidence(min_confidence_score)
    cutoff = format(score, "f").rstrip("0").rstrip(".") or "0"
    return f"""
SELECT
  w.document_id,
  w.page_index,
  w.word_text,
  w.confidence,
  f.field_path,
  f.field_value
FROM {db}.ocr_word w
JOIN {db}.ocr_field f
  ON f.submission_id = w.submission_id
 AND f.document_id = w.document_id
 AND instr(f.field_value, w.word_text) > 0
WHERE w.submission_id = {sid}
  AND w.word_text IS NOT NULL
  AND TRIM(w.word_text) != ''
  AND w.confidence < {cutoff}
ORDER BY w.confidence, f.field_path
""".strip()


def list_underwriter_open_submissions_sql(party_id: int | str, database: str) -> str:
    """Open submissions currently assigned to an underwriter.

    DECLINED and QUOTED are terminal and stay off the list.
    """
    db = validate_ident(database, "database")
    pid = int(party_id)
    return f"""
SELECT
  s.submission_id,
  s.line_of_business,
  s.submission_status_code,
  pe.first_name,
  pe.last_name
FROM {db}.submissions s
INNER JOIN {db}.submission_party_role r
  ON r.submission_id = s.submission_id
 AND r.role_type_code = 'UNDERWRITER'
 AND r.is_current_assignment = TRUE
 AND r.party_id = {pid}
LEFT JOIN {db}.person pe ON pe.party_id = r.party_id
WHERE UPPER(COALESCE(s.submission_status_code, '')) NOT IN ('DECLINED', 'QUOTED')
ORDER BY s.submission_id
""".strip()


def insert_decline_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    return (
        f"INSERT INTO {db}.submission_decline ("
        "decline_id, submission_id, reason_code, run_id, created_at"
        ") VALUES ("
        f"{sql_quote(row['decline_id'])}, {sql_quote(row['submission_id'])}, "
        f"{sql_quote(row['reason_code'])}, {sql_quote(row['run_id'])}, "
        "CURRENT_TIMESTAMP())"
    )


def insert_quote_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    return (
        f"INSERT INTO {db}.quote_issuance ("
        "quote_id, submission_id, rating_tier, premium_cents, run_id, created_at"
        ") VALUES ("
        f"{sql_quote(row['quote_id'])}, {sql_quote(row['submission_id'])}, "
        f"{sql_quote(row['rating_tier'])}, {int(row['premium_cents'])}, "
        f"{sql_quote(row['run_id'])}, CURRENT_TIMESTAMP())"
    )


def insert_enrichment_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    return (
        f"INSERT INTO {db}.data_enrichment_request ("
        "enrichment_id, submission_id, provider_type, run_id, created_at"
        ") VALUES ("
        f"{sql_quote(row['enrichment_id'])}, {sql_quote(row['submission_id'])}, "
        f"{sql_quote(row['provider_type'])}, {sql_quote(row['run_id'])}, "
        "CURRENT_TIMESTAMP())"
    )


def insert_referral_sql(database: str, row: dict[str, Any]) -> str:
    db = validate_ident(database, "database")
    return (
        f"INSERT INTO {db}.referral_queue ("
        "referral_id, submission_id, queue_code, run_id, created_at"
        ") VALUES ("
        f"{sql_quote(row['referral_id'])}, {sql_quote(row['submission_id'])}, "
        f"{sql_quote(row['queue_code'])}, {sql_quote(row['run_id'])}, "
        "CURRENT_TIMESTAMP())"
    )
