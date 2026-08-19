# PD path demo (claim 401)

Repeatable Agent Studio demo of the property-damage probes on seed **401**. Three Orchestrator chats, with Impala between them. The crew does **not** walk FNOL → payout in one run. Each chat classifies the current lake snapshot.

Chat the **Orchestrator**. Pass `claim_id` (and `run_id` on the specialist task). Do **not** pass `next_step` in the user message. Leave **402** / **403** rows alone.

Probe order (first match wins): R2.1 `RequestPoliceReport` → R2.2 `DetermineFault` → … → R1.4 `PdClaimsReview`. Snapshot-to-`next_step` table: [architecture.md — typical PD path](architecture.md#typical-pd-path-separate-calls). Per-probe chat prompts: [probe-action-tests.md](probe-action-tests.md).

| Snapshot | Lake | Expect |
|---|---|---|
| A | no police, no fault | `RequestPoliceReport` / R2.1 |
| B | police present, no fault | `DetermineFault` / R2.2 |
| C | police + fault (seed) | `PdClaimsReview` / R1.4 |

Coworker Role must be exactly `PD Claims Agent`. Playbook `agent_role` is `PdClaimsAgent`.

---

## 0. One-time setup

Skip if already done this session.

1. Claims MCP on **0.3.6** or later (`INS_CLAIMS_MCP_V7`). Studio `uvx` from GitHub `main` only sees `get_pd_view` / `create_pd_task` after that commit is on the remote.
2. Restart `iceberg-mcp-server-claims`.
3. Chat Orchestrator: `Call get_server_info once and stop.` Expect `INS_CLAIMS_MCP_V7` / **`0.3.6`** or newer.
4. `Call list_named_queries once and stop.` Must include `get_pd_view` and `create_pd_task`.
5. Workflow Data includes the playbook whose PD actions list `get_pd_view` / `create_pd_task` (and `save_claim_letter` on `RequestPoliceReport`, drafted only when the user asks).
6. Same Crew, Roles **exactly**: `Manager agent`, `PD Claims Agent`. Re-paste Orchestrator Goal from [`agent_studio/studio_tools/agents/orchestrator_agent.md`](../agent_studio/studio_tools/agents/orchestrator_agent.md) so the PD handoff is in it. Paste [`pd_claims_agent.md`](../agent_studio/studio_tools/agents/pd_claims_agent.md). Attach MCP + Studio `save_claim_letter` on the PD agent (used only when the user asks to write the letter).
7. In Impala, create `pd_task` if it does not exist. Source of truth: `ddl/hive_iceberg/car_insurance_claims_iceberg.sql`. Impala accepted `litigation_task` with COMMENT **after** `PARTITIONED BY SPEC` and no `STORED AS PARQUET`. If the file’s `pd_task` block fails, use this shape:

```sql
USE car_insurance_claims;

CREATE TABLE IF NOT EXISTS car_insurance_claims.pd_task (
  pd_task_id        BIGINT    COMMENT 'PK.',
  claim_id          BIGINT    COMMENT 'FK -> claim.claim_id.',
  loss_event_id     BIGINT    COMMENT 'Optional FK -> loss_event.',
  task_type_code    STRING    COMMENT 'REQUEST_POLICE_REPORT | DETERMINE_FAULT | PD_REVIEW.',
  task_status_code  STRING    COMMENT 'OPEN | DONE | CANCELLED.',
  due_date          DATE      COMMENT 'Optional due date.',
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

## 1. Reset 401 to “no police, no fault”

Run in Impala (Hue / impala-shell). This is the start of every full PD demo.

```sql
USE car_insurance_claims;

DELETE FROM car_insurance_claims.pd_task
WHERE claim_id = 401;

DELETE FROM car_insurance_claims.police_report
WHERE claim_id = 401;

DELETE FROM car_insurance_claims.fault_determination
WHERE claim_id = 401;

-- expect 0, 0, 0
SELECT COUNT(*) FROM car_insurance_claims.police_report WHERE claim_id = 401;
SELECT COUNT(*) FROM car_insurance_claims.fault_determination WHERE claim_id = 401;
SELECT COUNT(*) FROM car_insurance_claims.pd_task WHERE claim_id = 401;
```

If `DELETE` is rejected, use `TRUNCATE TABLE` only on `pd_task`. Do **not** truncate `police_report` / `fault_determination` (that also wipes 403 / 402).

---

## 2. Snapshot A — `RequestPoliceReport`

New Orchestrator chat. Paste:

```text
Intake and route claim_id 401, then complete the post-route specialist work.

You have no MCP tools. Do not skip the Orchestrator.

1) Delegate ONCE to Manager.
   Task: structured claim intake for 401 —
   run_named_query label get_claim_spine, then get_claim_routing_signals,
   then build, validate, route. STOP after route_claim.
   Return next_step, lane, agent_role, routing_reason, and the checks
   (Why this routing). Do not lead with probe ids.
   Do not call specialist views or write audit.

2) Map agent_role to coworker Role. Delegate ONCE to PD Claims Agent.
   Task: claim_id=401 run_id=demo-401-r21 next_step=<next_step from route>.
   run_named_query {"label":"get_pd_view","claim_id":"401"}
   then run_named_write create_pd_task
   event_json task_type_code REQUEST_POLICE_REPORT.
   Do not save_claim_letter unless asked to write the letter.

3) Final Answer: route + specialist summary + exact write JSON.
   STOP. Do not Delegate a third time.
```

**Pass:** `next_step=RequestPoliceReport`, `agent_role=PdClaimsAgent`, probe **R2.1**, `police_reports` empty, `create_pd_task` `REQUEST_POLICE_REPORT`. `routing_summary` says a police-report request letter is recommended and will not be drafted unless you ask. No `claim_*_letter.txt` unless you asked to write it.

Optional, same or new Orchestrator chat — only if you want the `.txt` draft:

```text
Write the recommended police-report request letter for claim_id 401.
Delegate ONCE to PD Claims Agent. View get_pd_view, then save_claim_letter.
Do not send mail.
```

```sql
SELECT pd_task_id, task_type_code, run_id, task_status_code
FROM car_insurance_claims.pd_task
WHERE claim_id = 401 AND run_id = 'demo-401-r21';

SELECT run_id, claim_id, event_type, next_step, agent_role
FROM car_insurance_claims.agent_run_audit
WHERE claim_id = '401' AND run_id = 'demo-401-r21';
```

The agent does **not** insert a `police_report` row. You do that next.

---

## 3. Advance lake — police present, still no fault

```sql
INSERT INTO TABLE car_insurance_claims.police_report
SELECT CAST(5301 AS BIGINT), CAST(301 AS BIGINT), CAST(401 AS BIGINT),
       'SPD-25-11887', 'Springfield Police Department', CAST(12 AS BIGINT),
       CAST('2025-06-15 18:10:00' AS TIMESTAMP), CAST('2025-06-15' AS DATE),
       CAST(501 AS BIGINT), TRUE,
       'Unit 2 cited for failure to reduce speed; rear-end collision.',
       CAST('2025-06-16 08:00:00' AS TIMESTAMP);

SELECT COUNT(*) FROM car_insurance_claims.police_report WHERE claim_id = 401;
-- expect 1
SELECT COUNT(*) FROM car_insurance_claims.fault_determination WHERE claim_id = 401;
-- expect 0
```

If that `INSERT` duplicates (row 5301 already restored), skip it.

---

## 4. Snapshot B — `DetermineFault`

New Orchestrator chat:

```text
Intake and route claim_id 401, then complete the post-route specialist work.

You have no MCP tools. Do not skip the Orchestrator.

1) Delegate ONCE to Manager.
   Task: structured claim intake for 401 —
   run_named_query label get_claim_spine, then get_claim_routing_signals,
   then build, validate, route. STOP after route_claim.
   Return next_step, lane, agent_role, routing_reason, and the checks
   (Why this routing). Do not lead with probe ids.

2) Delegate ONCE to PD Claims Agent.
   Task: claim_id=401 run_id=demo-401-r22 next_step=<next_step from route>.
   run_named_query {"label":"get_pd_view","claim_id":"401"}
   then run_named_write create_pd_task
   event_json task_type_code DETERMINE_FAULT.
   Do not call save_claim_letter.

3) Final Answer: route + specialist summary + exact write JSON. STOP.
```

**Pass:** `next_step=DetermineFault`, probe **R2.2**, view shows a police row and empty `fault_determinations`, task `DETERMINE_FAULT`.

---

## 5. Advance lake — restore fault (full PD facts)

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

## 6. Snapshot C — `PdClaimsReview`

New Orchestrator chat:

```text
Intake and route claim_id 401, then complete the post-route specialist work.

You have no MCP tools. Do not skip the Orchestrator.

1) Delegate ONCE to Manager.
   Task: structured claim intake for 401 —
   run_named_query label get_claim_spine, then get_claim_routing_signals,
   then build, validate, route. STOP after route_claim.
   Return next_step, lane, agent_role, routing_reason, and the checks
   (Why this routing). Do not lead with probe ids.

2) Delegate ONCE to PD Claims Agent.
   Task: claim_id=401 run_id=demo-401-r14 next_step=<next_step from route>.
   run_named_query {"label":"get_pd_view","claim_id":"401"}
   then run_named_write create_pd_task
   event_json task_type_code PD_REVIEW.
   Do not call save_claim_letter.

3) Final Answer: route + specialist summary + exact write JSON. STOP.
```

**Pass:** `next_step=PdClaimsReview`, probe **R1.4**, view has report `SPD-25-11887` and fault 20/80, task `PD_REVIEW`.

If you get `OpenSubrogationCase` / `PursueSubrogationRecovery` instead, the lake is missing the subro case or recovery from seed — re-run those INSERTs from `ddl/hive_iceberg/car_insurance_claims_seed_data.sql` (rows 8801 / 8901) and chat again. Do not invent those rows in the crew.

---

## 7. Confirm the three work items

```sql
SELECT run_id, task_type_code, task_status_code, pd_task_id
FROM car_insurance_claims.pd_task
WHERE claim_id = 401
ORDER BY created_at;
```

Expect three OPEN rows: `demo-401-r21` / `REQUEST_POLICE_REPORT`, `demo-401-r22` / `DETERMINE_FAULT`, `demo-401-r14` / `PD_REVIEW`.

---

## 8. Repeat from a clean slate

Run **step 1**, then 2 → 6 again. Use new `run_id`s if you skip the `pd_task` delete (`create_pd_task` hashes `run_id + claim_id + task_type`; the same triple will collide).

To put 401 back to the original seed (police 5301 + fault 5401) without re-seeding the whole database, run steps **3** and **5** if those counts are 0.

---

## Short path (one chat)

Skip steps 1–5. On an already-seeded 401 (police + fault present), start at step 6 with `run_id=demo-401-pd`. That only demos `PdClaimsReview`, not the police/fault gaps.

Direct specialist (skip intake): paste the task from [`pd_claims_agent.md`](../agent_studio/studio_tools/agents/pd_claims_agent.md) (`coworker: PD Claims Agent`, `next_step=PdClaimsReview`).
