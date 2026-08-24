# Named-query catalog (claims MCP)

Allow-listed Impala behind `iceberg-mcp-server-claims`. Agents call `run_named_query` or `run_named_write` with a **label**. Labels are not MCP tools. Free SQL is not registered.

Source of truth: `mcp_forks/iceberg-mcp-server-claims/src/iceberg_mcp_server_claims/catalog.py` and the handlers it points at. This file is a snapshot of that SQL.

## Session variables

Initialize `database` and `claim_id` **once** at the top of the Hue / Impala editor (or impala-shell). Every statement below uses Impala `${var:database}` and `${var:claim_id}`. Change the values here only.

**Impala-shell** (and Hue if parameterized queries are off):

```sql
SET VAR:database=car_insurance_claims;
SET VAR:claim_id=404;
```

**Hue** (editor form with defaults). Hue fills the `SET VAR` values; Impala then substitutes `${var:…}` in the SQL:

```sql
SET VAR:database=${database=car_insurance_claims};
SET VAR:claim_id=${claim_id=404};
```

If Hue prompts for `var:database` on the SELECTs, turn off parameterized / “replace variables” for that snippet so Impala does the substitution.

Other write fields (`{run_id}`, `{event_type}`, …) are still markdown placeholders. Fill those per statement.

Boolean columns from Hive-written Iceberg are matched with:

```sql
UPPER(TRIM(CAST(<expr> AS STRING))) IN ('TRUE', '1', 'T')
```

That predicate is written out in full below wherever the Python helper `sql_bool_truthy` is used.

Distributions live on a separate MCP (`iceberg-mcp-server-finserv`). They are not listed here.

---

## Index

### Reads (`run_named_query`)

| Label | Params | SQL |
|---|---|---|
| [`get_claim_spine`](#get_claim_spine) | `claim_id` | two SELECTs (spine + roles) |
| [`get_claim_routing_signals`](#get_claim_routing_signals) | `claim_id` | REFRESH + signals SELECT + four id lists |
| [`get_litigation_view`](#get_litigation_view) | `claim_id` | one SELECT |
| [`get_bi_view`](#get_bi_view) | `claim_id` | one SELECT |
| [`get_subrogation_view`](#get_subrogation_view) | `claim_id` | one SELECT |
| [`get_pd_view`](#get_pd_view) | `claim_id` | police, fault, intake, last SMS |
| [`get_deny_view`](#get_deny_view) | `claim_id` | three SELECTs |
| [`get_schema`](#get_schema) | optional `database` | `SHOW TABLES` |

### Writes (`run_named_write`)

| Label | Params | SQL |
|---|---|---|
| [`write_audit_event`](#write_audit_event) | `run_id`, `event_json` | INSERT `agent_run_audit` |
| [`append_agent_audit_event`](#write_audit_event) | same | alias of `write_audit_event` |
| [`append_agent_audit_evidence`](#append_agent_audit_evidence) | `run_id`, `evidence_json` | INSERT `agent_run_evidence` |
| [`begin_agent_audit_run`](#begin_agent_audit_run) | `run_id` | none (JSON only) |
| [`promote_audit_run`](#promote_audit_run) | `run_id` | none (JSON only) |
| [`promote_agent_audit_run`](#promote_audit_run) | same | alias of `promote_audit_run` |
| [`abandon_agent_audit_run`](#abandon_agent_audit_run) | `run_id` | two DELETEs |
| [`create_litigation_task`](#create_litigation_task) | `run_id`, `event_json` | INSERT `litigation_task` |
| [`create_pd_task`](#create_pd_task) | `run_id`, `event_json` | INSERT `pd_task` + INSERT `agent_run_audit` |
| [`deny_claim`](#deny_claim) | `run_id`, `event_json` | SELECT status, UPDATE `claim`, INSERT audit |

---

## get_claim_spine

Claim + loss + policy + vehicle + coverage triangle + current party roles.

### Spine

```sql
SELECT
  c.claim_id,
  c.claim_number,
  c.claim_status_code,
  c.litigation_indicator,
  c.subrogation_indicator,
  c.fraudulent_claim_indicator,
  c.total_loss_indicator,
  c.loss_event_id,
  le.loss_cause_code,
  c.policy_id,
  p.policy_number,
  c.insurable_object_id,
  v.vin,
  CASE WHEN pio.policy_id IS NOT NULL THEN TRUE ELSE FALSE END AS policy_covers_vehicle,
  c.policy_coverage_id,
  cov.coverage_type_code,
  cl.claim_lifecycle_id
FROM ${var:database}.claim c
LEFT JOIN ${var:database}.loss_event le ON c.loss_event_id = le.loss_event_id
LEFT JOIN ${var:database}.insurance_policy p ON c.policy_id = p.policy_id
LEFT JOIN ${var:database}.vehicle v ON c.insurable_object_id = v.insurable_object_id
LEFT JOIN ${var:database}.policy_insurable_object pio
  ON pio.policy_id = c.policy_id
 AND pio.insurable_object_id = c.insurable_object_id
 AND pio.expiration_date IS NULL
LEFT JOIN ${var:database}.policy_coverage pc ON c.policy_coverage_id = pc.policy_coverage_id
LEFT JOIN ${var:database}.coverage cov ON pc.coverage_id = cov.coverage_id
LEFT JOIN ${var:database}.claim_lifecycle cl ON cl.claim_id = c.claim_id
WHERE c.claim_id = ${var:claim_id}
LIMIT 1
```

### Roles

```sql
SELECT claim_party_role_id, party_id, role_type_code, is_current_assignment
FROM ${var:database}.claim_party_role
WHERE claim_id = ${var:claim_id}
  AND is_current_assignment = TRUE
```

---

## get_claim_routing_signals

Existence flags for YAML probes. Before the SELECTs, the handler best-effort `REFRESH`es `loss_driver`, `claim`, `police_report`, and `fault_determination` so Hue writes are visible on this Impala coordinator.

### Signals (one row)

```sql
WITH
sub AS (
  SELECT COUNT(*) AS cnt,
         MIN(subrogation_case_id) AS subrogation_case_id,
         MIN(subrogation_status_code) AS subrogation_status_code
  FROM ${var:database}.subrogation_case WHERE claim_id = ${var:claim_id}
),
lit AS (
  SELECT COUNT(*) AS cnt,
         MIN(litigation_case_id) AS litigation_case_id,
         MIN(docket_number) AS docket_number,
         MIN(defense_counsel_party_id) AS defense_counsel_party_id,
         MIN(plaintiff_counsel_party_id) AS plaintiff_counsel_party_id,
         MIN(served_date) AS served_date,
         MIN(filed_date) AS filed_date,
         MIN(closed_date) AS closed_date,
         MIN(litigation_status_code) AS litigation_status_code
  FROM ${var:database}.litigation_case WHERE claim_id = ${var:claim_id}
),
inj AS (
  SELECT COUNT(*) AS cnt FROM ${var:database}.claim_injury WHERE claim_id = ${var:claim_id}
),
pr AS (
  SELECT COUNT(*) AS cnt, MIN(police_report_id) AS police_report_id
  FROM ${var:database}.police_report WHERE claim_id = ${var:claim_id}
),
intake AS (
  SELECT COUNT(*) AS cnt,
         MIN(incident_report_number) AS incident_report_number
  FROM ${var:database}.claim_police_intake
  WHERE claim_id = ${var:claim_id}
    AND incident_report_number IS NOT NULL
    AND TRIM(incident_report_number) <> ''
),
fd AS (
  SELECT COUNT(*) AS cnt, MIN(fault_determination_id) AS fault_determination_id
  FROM ${var:database}.fault_determination WHERE claim_id = ${var:claim_id}
),
ofr AS (
  SELECT COUNT(*) AS cnt,
         SUM(CASE WHEN offer_status_code = 'EXTENDED' THEN 1 ELSE 0 END) AS extended_cnt,
         SUM(CASE WHEN offer_status_code = 'ACCEPTED' THEN 1 ELSE 0 END) AS accepted_cnt
  FROM ${var:database}.claim_offer WHERE claim_id = ${var:claim_id}
),
pay AS (
  SELECT COUNT(*) AS cnt FROM ${var:database}.claim_payment WHERE claim_id = ${var:claim_id}
),
rec AS (
  SELECT COUNT(*) AS cnt FROM ${var:database}.claim_recovery WHERE claim_id = ${var:claim_id}
),
res AS (
  SELECT COUNT(*) AS cnt FROM ${var:database}.claim_reserve
  WHERE claim_id = ${var:claim_id} AND is_current = TRUE
),
fa AS (
  SELECT COUNT(*) AS cnt,
         MIN(fraud_assessment_id) AS fraud_assessment_id,
         MIN(outcome_code) AS fraud_outcome_code
  FROM ${var:database}.fraud_assessment
  WHERE claim_id = ${var:claim_id} AND outcome_code IN ('SUSPECTED', 'PENDING')
),
doc AS (
  SELECT COUNT(*) AS cnt FROM ${var:database}.claim_document WHERE claim_id = ${var:claim_id}
),
cited AS (
  SELECT COUNT(*) AS cnt
  FROM ${var:database}.loss_driver
  WHERE claim_id = ${var:claim_id}
    AND driver_role_code = 'INSURED_OPERATOR'
    AND UPPER(TRIM(CAST(was_cited_indicator AS STRING))) IN ('TRUE', '1', 'T')
),
unlawful AS (
  SELECT COUNT(*) AS cnt
  FROM ${var:database}.loss_driver ld
  LEFT JOIN ${var:database}.driver d ON d.driver_id = ld.driver_id
  WHERE ld.claim_id = ${var:claim_id}
    AND ld.driver_role_code = 'INSURED_OPERATOR'
    AND (
      UPPER(TRIM(CAST(ld.impairment_suspected_indicator AS STRING))) IN ('TRUE', '1', 'T')
      OR UPPER(COALESCE(d.license_status_code, '')) IN (
        'SUSPENDED', 'REVOKED', 'UNLICENSED'
      )
    )
),
excl AS (
  SELECT COUNT(*) AS cnt
  FROM ${var:database}.loss_driver ld
  INNER JOIN ${var:database}.claim c ON c.claim_id = ld.claim_id
  LEFT JOIN ${var:database}.policy_driver pd
    ON pd.policy_id = c.policy_id
   AND pd.driver_id = ld.driver_id
   AND pd.expiration_date IS NULL
  WHERE ld.claim_id = ${var:claim_id}
    AND ld.driver_role_code = 'INSURED_OPERATOR'
    AND (
      pd.driver_id IS NULL
      OR UPPER(TRIM(CAST(pd.is_excluded_driver AS STRING))) IN ('TRUE', '1', 'T')
    )
),
lapse AS (
  SELECT COUNT(*) AS cnt
  FROM ${var:database}.claim c
  INNER JOIN ${var:database}.loss_event le ON le.loss_event_id = c.loss_event_id
  INNER JOIN ${var:database}.insurance_policy p ON p.policy_id = c.policy_id
  WHERE c.claim_id = ${var:claim_id}
    AND (
      UPPER(COALESCE(p.policy_status_code, '')) IN (
        'LAPSED', 'CANCELLED', 'EXPIRED'
      )
      OR (p.effective_date IS NOT NULL AND le.loss_date < p.effective_date)
      OR (p.expiration_date IS NOT NULL AND le.loss_date > p.expiration_date)
      OR (
        p.cancellation_date IS NOT NULL
        AND p.cancellation_date <= le.loss_date
      )
    )
)
SELECT
  (sub.cnt > 0) AS has_subrogation_case,
  sub.subrogation_case_id,
  sub.subrogation_status_code,
  (lit.cnt > 0) AS has_litigation_case,
  lit.litigation_case_id,
  lit.docket_number,
  lit.defense_counsel_party_id,
  lit.plaintiff_counsel_party_id,
  lit.served_date,
  lit.filed_date,
  lit.closed_date,
  lit.litigation_status_code,
  (
    lit.cnt > 0
    AND (
      lit.docket_number IS NULL OR TRIM(lit.docket_number) = ''
      OR (
        lit.defense_counsel_party_id IS NULL
        AND lit.plaintiff_counsel_party_id IS NULL
      )
    )
  ) AS missing_docket_or_counsel,
  (
    lit.cnt > 0
    AND lit.litigation_status_code = 'IN_DISCOVERY'
    AND lit.closed_date IS NULL
    AND lit.filed_date IS NOT NULL
    AND DATEDIFF(CURRENT_DATE(), lit.filed_date) > 90
  ) AS discovery_aging,
  (inj.cnt > 0) AS has_injury,
  (pr.cnt > 0) AS has_police_report,
  pr.police_report_id,
  (fd.cnt > 0) AS has_fault_determination,
  fd.fault_determination_id,
  (intake.cnt > 0) AS has_incident_report_number,
  intake.incident_report_number,
  (ofr.cnt > 0) AS has_offer,
  (COALESCE(ofr.extended_cnt, 0) > 0) AS has_unresolved_offer,
  (COALESCE(ofr.accepted_cnt, 0) > 0) AS has_accepted_offer,
  (pay.cnt > 0) AS has_loss_payment,
  (rec.cnt > 0) AS has_recovery,
  (res.cnt > 0) AS has_current_reserve,
  (fa.cnt > 0) AS has_siu_suspected,
  fa.fraud_assessment_id,
  fa.fraud_outcome_code,
  (doc.cnt > 0) AS has_document,
  (cited.cnt > 0) AS insured_operator_cited,
  (unlawful.cnt > 0) AS unlawful_operation_exclusion,
  (excl.cnt > 0) AS excluded_operator_exclusion,
  (lapse.cnt > 0) AS policy_not_in_force_on_loss
FROM sub
CROSS JOIN lit
CROSS JOIN inj
CROSS JOIN pr
CROSS JOIN fd
CROSS JOIN intake
CROSS JOIN ofr
CROSS JOIN pay
CROSS JOIN rec
CROSS JOIN res
CROSS JOIN fa
CROSS JOIN doc
CROSS JOIN cited
CROSS JOIN unlawful
CROSS JOIN excl
CROSS JOIN lapse
```

### Injury ids

```sql
SELECT claim_injury_id FROM ${var:database}.claim_injury WHERE claim_id = ${var:claim_id}
```

### Offers

```sql
SELECT claim_offer_id, offer_status_code
FROM ${var:database}.claim_offer
WHERE claim_id = ${var:claim_id}
```

### Payment ids

```sql
SELECT claim_payment_id FROM ${var:database}.claim_payment WHERE claim_id = ${var:claim_id}
```

### Recovery ids

```sql
SELECT claim_recovery_id FROM ${var:database}.claim_recovery WHERE claim_id = ${var:claim_id}
```

---

## get_litigation_view

Business columns only (no PK/FK). Envelope still has `claim_id`.

```sql
SELECT litigation_status_code, docket_number, venue_name,
       venue_country_subdivision_code, filed_date, served_date, closed_date,
       demand_amount, currency_code, created_at
FROM ${var:database}.litigation_case
WHERE claim_id = ${var:claim_id}
```

---

## get_bi_view

```sql
SELECT injury_severity_code, body_region_code, injury_description,
       treatment_start_date, treatment_end_date, ambulance_used_indicator,
       hospitalization_indicator, created_at
FROM ${var:database}.claim_injury
WHERE claim_id = ${var:claim_id}
```

---

## get_subrogation_view

```sql
SELECT subrogation_status_code, demand_amount, recovered_amount, currency_code,
       opened_date, closed_date, statute_limitations_date, created_at
FROM ${var:database}.subrogation_case
WHERE claim_id = ${var:claim_id}
```

---

## get_pd_view

### Police reports

```sql
SELECT report_number, agency_name, report_datetime, report_date,
       citation_issued_indicator, narrative_summary, created_at
FROM ${var:database}.police_report
WHERE claim_id = ${var:claim_id}
```

### Fault determinations

```sql
SELECT insured_fault_percent, adverse_fault_percent, fault_basis_code,
       determination_status_code, determination_datetime, notes, created_at
FROM ${var:database}.fault_determination
WHERE claim_id = ${var:claim_id}
```

### Incident number (policyholder intake)

```sql
SELECT incident_report_number
FROM ${var:database}.claim_police_intake
WHERE claim_id = ${var:claim_id}
  AND incident_report_number IS NOT NULL
  AND TRIM(incident_report_number) <> ''
ORDER BY collected_at DESC
LIMIT 1
```

### Last SMS

```sql
SELECT to_phone, body_text, created_at
FROM ${var:database}.claim_outbound_message
WHERE claim_id = ${var:claim_id}
  AND purpose_code = 'COLLECT_INCIDENT_REPORT_NUMBER'
ORDER BY created_at DESC
LIMIT 1
```

---

## get_deny_view

Operator, policy, and police facts for Deny Agent / Human Review.

### Operators

```sql
SELECT ld.driver_role_code, ld.was_cited_indicator,
       ld.impairment_suspected_indicator, d.license_status_code,
       (pd.is_excluded_driver IS NOT NULL) AS listed_on_policy,
       COALESCE(pd.is_excluded_driver, FALSE) AS is_excluded_driver
FROM ${var:database}.loss_driver ld
LEFT JOIN ${var:database}.driver d ON d.driver_id = ld.driver_id
INNER JOIN ${var:database}.claim c ON c.claim_id = ld.claim_id
LEFT JOIN ${var:database}.policy_driver pd
  ON pd.policy_id = c.policy_id
 AND pd.driver_id = ld.driver_id
 AND pd.expiration_date IS NULL
WHERE ld.claim_id = ${var:claim_id}
```

### Policy

```sql
SELECT c.claim_status_code, c.claim_number, p.policy_number,
       p.policy_status_code, p.effective_date, p.expiration_date,
       p.cancellation_date, le.loss_date
FROM ${var:database}.claim c
INNER JOIN ${var:database}.insurance_policy p ON p.policy_id = c.policy_id
INNER JOIN ${var:database}.loss_event le ON le.loss_event_id = c.loss_event_id
WHERE c.claim_id = ${var:claim_id}
```

### Police (short)

```sql
SELECT report_number, agency_name, narrative_summary
FROM ${var:database}.police_report
WHERE claim_id = ${var:claim_id}
```

---

## get_schema

If `database` is set:

```sql
SHOW TABLES IN ${var:database}
```

Otherwise:

```sql
SHOW TABLES
```

---

## write_audit_event

Playbook name. Same SQL as `append_agent_audit_event`.

`event_ts` uses `CURRENT_TIMESTAMP()` when omitted. JSON fields are string-quoted.

```sql
INSERT INTO ${var:database}.agent_run_audit (
  run_id, event_ts, claim_id, event_type, next_step, agent_role, lane,
  needs_llm, terminal, reason_probe_ids, payload_json
) VALUES (
  '{run_id}',
  CURRENT_TIMESTAMP(),   -- or CAST('{event_ts}' AS TIMESTAMP)
  '${var:claim_id}',
  '{event_type}',
  '{next_step}',
  '{agent_role}',
  '{lane}',
  '{needs_llm}',
  '{terminal}',
  '{reason_probe_ids}',
  '{payload_json}'
)
```

---

## append_agent_audit_evidence

```sql
INSERT INTO ${var:database}.agent_run_evidence (
  run_id, evidence_ts, claim_id, evidence_type, probe_id,
  content_format, content_text, content_uri
) VALUES (
  '{run_id}',
  CURRENT_TIMESTAMP(),   -- or CAST('{evidence_ts}' AS TIMESTAMP)
  '${var:claim_id}',
  '{evidence_type}',
  '{probe_id}',
  '{content_format}',    -- default 'json'
  '{content_text}',
  '{content_uri}'
)
```

---

## begin_agent_audit_run

No SQL. Returns `mode=table_append`. Impala has no Iceberg WAP branch on this path.

---

## promote_audit_run

No SQL. Same handler as `promote_agent_audit_run`. Rows are already on main; response is `mode=table_append`.

---

## abandon_agent_audit_run

```sql
DELETE FROM ${var:database}.agent_run_audit WHERE run_id = '{run_id}'
```

```sql
DELETE FROM ${var:database}.agent_run_evidence WHERE run_id = '{run_id}'
```

---

## create_litigation_task

`event_json.task_type_code` must be `COMPLETE_FILE`, `ESCALATE_DISCOVERY`, or `DRAFT_HOLD`. `litigation_task_id` is a hash of `run_id:claim_id:task_type`.

```sql
INSERT INTO ${var:database}.litigation_task (
  litigation_task_id, litigation_case_id, claim_id, task_type_code,
  task_status_code, due_date, run_id, created_at
) VALUES (
  {litigation_task_id},
  {litigation_case_id},   -- or NULL
  ${var:claim_id},
  '{task_type_code}',
  'OPEN',
  CAST('{due_date}' AS DATE),   -- or NULL
  '{run_id}',
  CURRENT_TIMESTAMP()
)
```

---

## create_pd_task

`event_json.task_type_code` must be `COLLECT_INCIDENT_NUMBER`, `REQUEST_POLICE_REPORT`, `DETERMINE_FAULT`, or `PD_REVIEW`. Then one audit receipt. `REQUEST_POLICE_REPORT` requires `claim_police_intake.incident_report_number`, stores it on the task, and refuses if a `police_report` row already exists. `COLLECT_INCIDENT_NUMBER` also inserts `claim_outbound_message`.

```sql
INSERT INTO ${var:database}.pd_task (
  pd_task_id, claim_id, loss_event_id, task_type_code,
  task_status_code, due_date, incident_report_number, run_id, created_at
) VALUES (
  {pd_task_id},
  ${var:claim_id},
  {loss_event_id},   -- or NULL
  '{task_type_code}',
  'OPEN',
  CAST('{due_date}' AS DATE),   -- or NULL
  '{incident_report_number}',   -- or NULL
  '{run_id}',
  CURRENT_TIMESTAMP()
)
```

`COLLECT_INCIDENT_NUMBER` also:

```sql
INSERT INTO ${var:database}.claim_outbound_message (
  message_id, claim_id, channel_code, to_phone, body_text,
  purpose_code, run_id, created_at
) VALUES (
  {message_id},
  ${var:claim_id},
  'SMS',
  '{to_phone}',
  '{body_text}',
  'COLLECT_INCIDENT_REPORT_NUMBER',
  '{run_id}',
  CURRENT_TIMESTAMP()
)
```

Plus the same `INSERT INTO ${var:database}.agent_run_audit …` as `write_audit_event`.

---

## deny_claim

`event_json.next_step` must be `DenyUnlawfulOperation`, `DenyExcludedDriver`, or `DenyLapsedPolicy`. Refuses `CLOSED` and already-`DENIED`.

### Status check

```sql
SELECT claim_status_code FROM ${var:database}.claim WHERE claim_id = ${var:claim_id}
```

### Status write

```sql
UPDATE ${var:database}.claim SET claim_status_code = 'DENIED'
WHERE claim_id = ${var:claim_id}
  AND UPPER(COALESCE(claim_status_code, '')) NOT IN ('CLOSED', 'DENIED')
```

### Audit receipt

Same `INSERT INTO ${var:database}.agent_run_audit …` as `write_audit_event`.
