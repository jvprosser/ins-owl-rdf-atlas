SELECT
  f.fnol_id,
  f.fnol_number,
  f.report_timestamp,
  f.reported_by_relationship,
  f.intake_channel,
  f.intake_purpose_code,
  f.triage_status_code,
  f.estimated_loss_amount,
  f.claim_id,
  f.policy_id,
  f.insurable_object_id,
  f.loss_event_id,
  p.policy_number,
  p.policy_status_code,
  p.effective_date,
  p.expiration_date,
  p.cancellation_date,
  le.loss_cause_code,
  le.loss_date,
  v.vin,
  CASE WHEN pio.policy_id IS NOT NULL THEN TRUE ELSE FALSE END AS vehicle_listed_on_policy,
  pc.policy_coverage_id,
  cov.coverage_type_code,
  pc.deductible_amount,
  CASE WHEN pc.policy_coverage_id IS NOT NULL THEN TRUE ELSE FALSE END AS peril_covered
FROM ${database}.fnol f
LEFT JOIN ${database}.loss_event le ON f.loss_event_id = le.loss_event_id
LEFT JOIN ${database}.insurance_policy p ON f.policy_id = p.policy_id
LEFT JOIN ${database}.vehicle v ON f.insurable_object_id = v.insurable_object_id
LEFT JOIN ${database}.policy_insurable_object pio
  ON pio.policy_id = f.policy_id
 AND pio.insurable_object_id = f.insurable_object_id
 AND pio.expiration_date IS NULL
LEFT JOIN ${database}.coverage cov
  ON (
    (UPPER(COALESCE(le.loss_cause_code, '')) = 'COLLISION'
     AND cov.coverage_type_code = 'COLLISION')
    OR (UPPER(COALESCE(le.loss_cause_code, '')) <> 'COLLISION'
     AND cov.coverage_type_code = 'COMPREHENSIVE')
  )
LEFT JOIN ${database}.policy_coverage pc
  ON pc.policy_id = f.policy_id
 AND pc.coverage_id = cov.coverage_id
 AND pc.is_active = TRUE
 AND pc.expiration_date IS NULL
WHERE f.fnol_id = ${fnol_id}
LIMIT 1
