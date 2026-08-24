# PD path demo (claim 401)

Repeatable Agent Studio demo of the property-damage probes on seed **401**. Orchestrator chats, with Impala between them. The crew does **not** walk FNOL → payout in one run. Each chat classifies the current lake snapshot.

Chat the **Orchestrator** as a claims handler would: one sentence and a claim id. Do not mention tools, catalog labels, `run_id`, or `next_step`. Orchestrator supplies `run_id` and the specialist Role; the PD agent Goal owns the catalog write. Leave **402** / **403** / **404** rows alone.

Probe order (first match wins): R2.0 `CollectIncidentReportNumber` → R2.1 `RequestPoliceReport` → R2.2 `DetermineFault` → … → R1.4 `PdClaimsReview`. Snapshot-to-`next_step` table: [architecture.md — typical PD path](architecture.md#typical-pd-path-separate-calls). Per-probe chats: [probe-action-tests.md](probe-action-tests.md).

| Snapshot | Lake | User says | Expect |
|---|---|---|---|
| A0 | no police, no intake number | Please process claim 401. | `CollectIncidentReportNumber` / R2.0; SMS to `+1-555-0101` |
| A1 | intake `SPD-25-11887`, no police | Please process claim 401. | `RequestPoliceReport` / R2.1; letter/task cite **SPD-25-11887** not 401 |
| B | police present, no fault | Please process claim 401. | `DetermineFault` / R2.2 |
| C | police + fault (seed) | Please process claim 401. | `PdClaimsReview` / R1.4 |

Coworker Role must be exactly `PD Claims Agent`. Playbook `agent_role` is `PdClaimsAgent`.

---

## 0. One-time setup

Skip if already done this session. These checks are for the operator, not the handler chats below.

1. Claims MCP on **0.3.9** or later (`INS_CLAIMS_MCP_V9`). Studio `uvx` from GitHub `main` only sees SMS / intake after that commit is on the remote.
2. Restart `iceberg-mcp-server-claims`.
3. Operator chat: `Call get_server_info once and stop.` Expect `INS_CLAIMS_MCP_V9` / **`0.3.9`** or newer.
4. Operator chat: `Call list_named_queries once and stop.` Must include `get_pd_view` and `create_pd_task`.
5. Workflow Data includes the playbook with **R2.0** `CollectIncidentReportNumber` before R2.1.
6. Same Crew, Roles **exactly**: `Manager agent`, `PD Claims Agent`. Re-paste Orchestrator Goal from [`agent_studio/studio_tools/agents/orchestrator_agent.md`](../agent_studio/studio_tools/agents/orchestrator_agent.md). Paste [`pd_claims_agent.md`](../agent_studio/studio_tools/agents/pd_claims_agent.md). Attach MCP + Studio `save_claim_letter` on the PD agent (always SMS copy on CollectIncidentReportNumber; police letter only if the handler asks).
7. In Impala, create intake / SMS tables and add `pd_task.incident_report_number` if they do not exist. Fresh full seed: [`ddl/hive_iceberg/car_insurance_claims_iceberg.sql`](../ddl/hive_iceberg/car_insurance_claims_iceberg.sql). Already-loaded lake: run [`ddl/hive_iceberg/car_insurance_claims_pd_intake.sql`](../ddl/hive_iceberg/car_insurance_claims_pd_intake.sql). If `pd_task` itself is missing, use this shape (then re-run the additive file for the extra column):

```sql
USE car_insurance_claims;

CREATE TABLE IF NOT EXISTS car_insurance_claims.pd_task (
  pd_task_id        BIGINT    COMMENT 'PK.',
  claim_id          BIGINT    COMMENT 'FK -> claim.claim_id.',
  loss_event_id     BIGINT    COMMENT 'Optional FK -> loss_event.',
  task_type_code    STRING    COMMENT 'COLLECT_INCIDENT_NUMBER | REQUEST_POLICE_REPORT | DETERMINE_FAULT | PD_REVIEW.',
  task_status_code  STRING    COMMENT 'OPEN | DONE | CANCELLED.',
  due_date          DATE      COMMENT 'Optional due date.',
  incident_report_number STRING COMMENT 'Agency incident number for REQUEST_POLICE_REPORT.',
  run_id            STRING    COMMENT 'Agent run that created the task.',
  created_at        TIMESTAMP COMMENT 'Row creation timestamp.'
)
PARTITIONED BY SPEC (
  task_status_code,
  YEAR(created_at)
)
COMMENT 'PD work item from playbook next_step.'
STORED BY ICEBERG
TBLPROPERTIES ('format-version' = '2');

INVALIDATE METADATA car_insurance_claims.pd_task;
```

---

## 1. Reset 401 to “no police, no intake, no fault”

Run in Impala (Hue / impala-shell). This is the start of every full PD demo.

```sql
USE car_insurance_claims;

DELETE FROM car_insurance_claims.pd_task
WHERE claim_id = 401;

DELETE FROM car_insurance_claims.claim_outbound_message
WHERE claim_id = 401;

DELETE FROM car_insurance_claims.claim_police_intake
WHERE claim_id = 401;

DELETE FROM car_insurance_claims.police_report
WHERE claim_id = 401;

DELETE FROM car_insurance_claims.fault_determination
WHERE claim_id = 401;

-- expect 0, 0, 0, 0, 0
SELECT COUNT(*) FROM car_insurance_claims.police_report WHERE claim_id = 401;
SELECT COUNT(*) FROM car_insurance_claims.claim_police_intake WHERE claim_id = 401;
SELECT COUNT(*) FROM car_insurance_claims.claim_outbound_message WHERE claim_id = 401;
SELECT COUNT(*) FROM car_insurance_claims.fault_determination WHERE claim_id = 401;
SELECT COUNT(*) FROM car_insurance_claims.pd_task WHERE claim_id = 401;
```

If `DELETE` is rejected, use `TRUNCATE TABLE` only on `pd_task`. Do **not** truncate `police_report` / `fault_determination` (that also wipes 403 / 402).

---

## 2. Snapshot A0 — `CollectIncidentReportNumber`

New Orchestrator chat:

```text
Please process claim 401.
```

**Pass:** `next_step=CollectIncidentReportNumber`, `agent_role=PdClaimsAgent`, probe **R2.0**, `create_pd_task` `COLLECT_INCIDENT_NUMBER`. Observation / Hue shows an SMS row to **`+1-555-0101`**. A session copy is always written to `claim_401_sms.txt`. Orchestrator Goal supplies `run_id` (`demo-401-e2e`).

```sql
SELECT to_phone, purpose_code, body_text, run_id
FROM car_insurance_claims.claim_outbound_message
WHERE claim_id = 401
ORDER BY created_at DESC
LIMIT 1;
-- expect +1-555-0101, COLLECT_INCIDENT_REPORT_NUMBER

SELECT pd_task_id, task_type_code, run_id, task_status_code
FROM car_insurance_claims.pd_task
WHERE claim_id = 401 AND task_type_code = 'COLLECT_INCIDENT_NUMBER';
```

The agent does **not** insert `claim_police_intake`. The policyholder (you, in Hue) does that next.

---

## 3. Policyholder reply — incident number on file

This is the app update. Do **not** `UPDATE` if the table is empty — `INSERT` the intake row.

```sql
INSERT INTO TABLE car_insurance_claims.claim_police_intake
SELECT CAST(401 AS BIGINT) AS claim_id,
       'SPD-25-11887' AS incident_report_number,
       'POLICYHOLDER_APP' AS source_code,
       CAST('2025-06-16 09:00:00' AS TIMESTAMP) AS collected_at,
       CAST(NULL AS STRING) AS run_id;

INVALIDATE METADATA car_insurance_claims.claim_police_intake;

SELECT incident_report_number, source_code
FROM car_insurance_claims.claim_police_intake
WHERE claim_id = 401;
-- expect SPD-25-11887
```

---

## 4. Snapshot A1 — `RequestPoliceReport`

New Orchestrator chat:

```text
Please process claim 401.
```

**Pass:** `next_step=RequestPoliceReport`, probe **R2.1**, view `incident_report_number=SPD-25-11887`, `police_reports` empty, task `REQUEST_POLICE_REPORT` with **`incident_report_number=SPD-25-11887`**. A police-report request letter is recommended and will not be drafted unless you ask. The letter (if asked) must request **SPD-25-11887**, not claim 401 / `CLM-2025-000401`.

Optional letter:

```text
Please write the recommended letter for claim 401.
```

```sql
SELECT pd_task_id, task_type_code, incident_report_number, run_id
FROM car_insurance_claims.pd_task
WHERE claim_id = 401 AND task_type_code = 'REQUEST_POLICE_REPORT';
-- expect SPD-25-11887

SELECT run_id, claim_id, event_type, next_step, agent_role
FROM car_insurance_claims.agent_run_audit
WHERE claim_id = '401' AND next_step = 'RequestPoliceReport';
```

The agent does **not** insert a `police_report` row. You do that next.

---

## 5. Advance lake — police present, still no fault

```sql
INSERT INTO TABLE car_insurance_claims.police_report
SELECT CAST(5301 AS BIGINT), CAST(301 AS BIGINT), CAST(401 AS BIGINT),
       'SPD-25-11887', 'Springfield Police Department', CAST(12 AS BIGINT),
       CAST('2025-06-15 18:10:00' AS TIMESTAMP), CAST('2025-06-15' AS DATE),
       CAST(501 AS BIGINT), TRUE,
       'Unit 2 cited for failure to reduce speed; rear-end collision.',
       CAST('2025-06-16 08:00:00' AS TIMESTAMP);

INVALIDATE METADATA car_insurance_claims.police_report;

SELECT COUNT(*) FROM car_insurance_claims.police_report WHERE claim_id = 401;
-- expect 1
SELECT COUNT(*) FROM car_insurance_claims.fault_determination WHERE claim_id = 401;
-- expect 0
```

If that `INSERT` duplicates (row 5301 already restored), skip it.

---

## 6. Snapshot B — `DetermineFault`

New Orchestrator chat:

```text
Please process claim 401.
```

**Pass:** `next_step=DetermineFault`, probe **R2.2**, view shows a police row and empty `fault_determinations`, task `DETERMINE_FAULT`.

---

## 7. Advance lake — restore fault (full PD facts)

```sql
INSERT INTO TABLE car_insurance_claims.fault_determination
SELECT CAST(5401 AS BIGINT), CAST(401 AS BIGINT), CAST(301 AS BIGINT),
       CAST(503 AS BIGINT), CAST(3 AS BIGINT),
       CAST(20.00 AS DECIMAL(5,2)), CAST(80.00 AS DECIMAL(5,2)),
       'POLICE', 'FINAL',
       CAST('2025-06-18 10:00:00' AS TIMESTAMP),
       'Final liability: adverse primarily at fault based on police report and photos.',
       CAST('2025-06-18 10:00:00' AS TIMESTAMP);

SELECT COUNT(*) FROM car_insurance_claims.police_report WHERE claim_id = 401;
-- expect 1
SELECT COUNT(*) FROM car_insurance_claims.fault_determination WHERE claim_id = 401;
-- expect 1
```

---

## 8. Snapshot C — `PdClaimsReview`

New Orchestrator chat:

```text
Please process claim 401.
```

**Pass:** `next_step=PdClaimsReview`, probe **R1.4**, view has report `SPD-25-11887` and fault 20/80, task `PD_REVIEW`.

If you get `OpenSubrogationCase` / `PursueSubrogationRecovery` instead, the data is missing the subro case or recovery from seed — re-run those INSERTs from `ddl/hive_iceberg/car_insurance_claims_seed_data.sql` (rows 8801 / 8901) and chat again. Do not invent those rows in the crew.

---

## 9. Confirm the work items

```sql
SELECT run_id, task_type_code, incident_report_number, task_status_code, pd_task_id
FROM car_insurance_claims.pd_task
WHERE claim_id = 401
ORDER BY created_at;
```

Expect OPEN rows: `COLLECT_INCIDENT_NUMBER`, `REQUEST_POLICE_REPORT` (incident **SPD-25-11887**), `DETERMINE_FAULT`, `PD_REVIEW`. `run_id` is whatever Orchestrator Goal used (typically `demo-401-e2e`).

---

## 10. Repeat from a clean slate

Run **step 1**, then 2 → 8 again. If you skip the `pd_task` delete, `create_pd_task` hashes `run_id + claim_id + task_type` and the same triple will collide.

To put 401 back to the original seed (police 5301 + fault 5401) without re-seeding the whole database, run steps **5** and **7** if those counts are 0.

---

## Short path (one chat)

Skip steps 1–7. On an already-seeded 401 (police + fault present):

```text
Please process claim 401.
```

That only demos `PdClaimsReview` (or subrogation), not the intake / police / fault gaps.
