# FNOL path demo (notice 88)

Repeatable Agent Studio demo of first-notice triage. A notice is **not** a claim. Seed **88** is Marcus Vance / `PA-9018442-01` / RAV4 garage scrape: active policy, listed vehicle, collision covered, no injury or third party, estimated 450 vs 1000 deductible, `RECORD_ONLY_NOTIFICATION`. First match is **F6** `ConvertFnolToIncidentOnly`.

Leave **401** / **402** / **403** / **404** rows alone.

Chat the **Orchestrator** as a handler: one sentence and an FNOL id. Do not mention tools, catalog labels, `run_id`, or probe ids.

| Snapshot | Lake | User says | Expect |
|---|---|---|---|
| Seed | FNOL 88 OPEN, 450 vs 1000 | Please process FNOL 88. | `ConvertFnolToIncidentOnly` / F6; `close_fnol_incident_only` |
| Alias | same | Please process FNOL-2026-00088. | same |
| Grey band | estimated_loss 800 | Please process FNOL 88. | `FnolAdjusterReview` / F4b; `review_fnol` |
| Over deductible | estimated_loss 1500 | Please process FNOL 88. | `ConvertFnolToClaim` / F5; claim **80088**; then PD on 80088 |
| Injury | one `fnol_injury` row | Please process FNOL 88. | `ConvertFnolToClaim` / F2 |
| Lapsed | policy LAPSED | Please process FNOL 88. | `DenyFnolNoCoverage` / F1; `deny_fnol` (no claim row) |
| Already converted | `fnol.claim_id` set | Please process FNOL 88. | `FnolAlreadyTriaged` / F0; then process claim N |

Coworker Roles must be exactly `FNOL Agent`, `Deny Agent`, or `Human Review Agent`. Convert-then-PD also needs `PD Claims Agent`.

---

## 0. One-time setup

1. Claims MCP on **0.8.0** (`INS_CLAIMS_MCP_V14`). Restart `iceberg-mcp-server-claims`.
2. Operator chat: `Call get_server_info once and stop.` Expect `INS_CLAIMS_MCP_V14` / **`0.8.0`**.
3. Operator chat: `Call list_named_queries once and stop.` Must include `get_fnol_spine`, `get_fnol_routing_signals`, `deny_fnol`, `close_fnol_incident_only`, `convert_fnol_to_claim`, `review_fnol`.
4. Workflow Data includes the playbook with **F0–F7** before R0.1.
5. Same Crew, Roles **exactly**: `Intake Agent`, `FNOL Agent`, `Deny Agent`, `Human Review Agent`, and `PD Claims Agent` for convert-then-PD. Re-paste Orchestrator, Deny, Human Review, FNOL, and PD Goals from `agent_studio/studio_tools/agents/`.
6. In Impala, create FNOL tables if they do not exist, then seed 88. Fresh full seed: [`ddl/hive_iceberg/car_insurance_claims_iceberg.sql`](../ddl/hive_iceberg/car_insurance_claims_iceberg.sql) then [`car_insurance_claims_seed_data.sql`](../ddl/hive_iceberg/car_insurance_claims_seed_data.sql). Already-loaded lake:

```sql
-- tables
-- ddl/hive_iceberg/car_insurance_claims_fnol.sql
-- seed (skip if fnol_id 88 exists)
-- ddl/hive_iceberg/car_insurance_claims_seed_fnol_88.sql
```

Hue check after seed:

```sql
SELECT fnol_id, fnol_number, intake_purpose_code, triage_status_code,
       estimated_loss_amount, claim_id
FROM car_insurance_claims.fnol
WHERE fnol_id = 88;
```

Expect `OPEN`, `RECORD_ONLY_NOTIFICATION`, 450, `claim_id` NULL.

---

## 1. Process FNOL 88 (STP)

```text
Please process FNOL 88.
```

Expect `ConvertFnolToIncidentOnly` / `FNOL Agent` / `close_fnol_incident_only`. Hue:

```sql
SELECT triage_status_code, claim_id
FROM car_insurance_claims.fnol WHERE fnol_id = 88;
```

Expect `INCIDENT_ONLY` and still no claim row.

---

## 2. Reset 88 for another snapshot

```sql
UPDATE car_insurance_claims.fnol
SET triage_status_code = 'OPEN', claim_id = NULL, run_id = NULL
WHERE fnol_id = 88;
```

If a convert created claim 80088, delete that claim (and its children) before a second convert, or leave it and expect F0 / idempotent convert. Restore `estimated_loss_amount = 450` for the STP snapshot.

---

## 3. Convert then PD (claim 80088)

Do **not** use claim **401**. Convert inserts `claim_id = 80000 + fnol_id` (**80088**), plus current `INSURED` (Marcus Vance, party 15) and `ADJUSTER` (Alice Ng, party 4). Then run the PD snapshots on **80088**. Leave 401 / 402 / 403 / 404 alone.

Use F5 (estimated 1500 vs collision deductible **1000**), not F2 injury — a `claim_injury` row would steal BI later. `get_fnol_spine` must show deductible **1000** (collision), not 500 (comprehensive). If you still see 500, MCP is pre-V14; restart after pull.

### 3a. Lake: over-deductible convert snapshot

```sql
USE car_insurance_claims;

-- children of a prior 80088 convert
DELETE FROM car_insurance_claims.pd_task WHERE claim_id = 80088;
DELETE FROM car_insurance_claims.claim_outbound_message WHERE claim_id = 80088;
DELETE FROM car_insurance_claims.claim_police_intake WHERE claim_id = 80088;
DELETE FROM car_insurance_claims.police_report WHERE claim_id = 80088;
DELETE FROM car_insurance_claims.fault_determination WHERE claim_id = 80088;
DELETE FROM car_insurance_claims.claim_reserve WHERE claim_id = 80088;
DELETE FROM car_insurance_claims.claim_party_role WHERE claim_id = 80088;
DELETE FROM car_insurance_claims.claim WHERE claim_id = 80088;

UPDATE car_insurance_claims.fnol
SET estimated_loss_amount = 1500,
    triage_status_code = 'OPEN',
    claim_id = NULL,
    run_id = NULL
WHERE fnol_id = 88;
```

### 3b. Convert the notice

```text
Please process FNOL 88.
```

Expect `ConvertFnolToClaim` / `FNOL Agent` / `convert_fnol_to_claim` / claim **80088**. Hue:

```sql
SELECT triage_status_code, claim_id, estimated_loss_amount
FROM car_insurance_claims.fnol WHERE fnol_id = 88;
-- CONVERTED, 80088, 1500

SELECT claim_id, claim_status_code, policy_id, insurable_object_id
FROM car_insurance_claims.claim WHERE claim_id = 80088;
-- OPEN, 1088, 288

SELECT party_id, role_type_code
FROM car_insurance_claims.claim_party_role
WHERE claim_id = 80088 AND is_current_assignment = TRUE;
-- 15 INSURED, 4 ADJUSTER
```

### 3c. PD on 80088 (same probes as 401)

New user message (same Orchestrator chat is fine). Do not re-run FNOL F* probes.

```text
Please process claim 80088.
```

**A0** `CollectIncidentReportNumber` / R2.0 / SMS to **`+1-555-0188`**. Then leave the SMS; chat again → **A0b** `WaitForIncidentNumber`. Insert intake, chat → **A1** `RequestPoliceReport` citing **SPD-26-88088**. Insert police, chat → **B** `DetermineFault`. Insert fault, chat → **C** `PdClaimsReview`. Pattern: [pd-path-demo.md](pd-path-demo.md) with `401` → `80088`, phone `+1-555-0101` → `+1-555-0188`, incident `SPD-25-11887` → `SPD-26-88088`, `run_id` `demo-80088-e2e`.

Intake (after A0b):

```sql
INSERT INTO TABLE car_insurance_claims.claim_police_intake
SELECT CAST(80088 AS BIGINT) AS claim_id,
       'SPD-26-88088' AS incident_report_number,
       'POLICYHOLDER_APP' AS source_code,
       CAST('2026-10-21 09:00:00' AS TIMESTAMP) AS collected_at,
       CAST(NULL AS STRING) AS run_id;
```

Police (after A1). `loss_event_id` **388**, location **588**:

```sql
INSERT INTO TABLE car_insurance_claims.police_report
SELECT CAST(5388 AS BIGINT), CAST(388 AS BIGINT), CAST(80088 AS BIGINT),
       'SPD-26-88088', 'Springfield Police Department', CAST(12 AS BIGINT),
       CAST('2026-10-20 18:40:00' AS TIMESTAMP), CAST('2026-10-20' AS DATE),
       CAST(588 AS BIGINT), FALSE,
       'Garage-frame scrape; no other vehicle; incident number taken.',
       CAST('2026-10-21 08:00:00' AS TIMESTAMP);
```

Fault (after B). Insured operator **588** / party **15**:

```sql
INSERT INTO TABLE car_insurance_claims.fault_determination
SELECT CAST(5488 AS BIGINT), CAST(80088 AS BIGINT), CAST(388 AS BIGINT),
       CAST(588 AS BIGINT), CAST(15 AS BIGINT),
       CAST(100.00 AS DECIMAL(5,2)), CAST(0.00 AS DECIMAL(5,2)),
       'POLICE', 'FINAL',
       CAST('2026-10-21 10:00:00' AS TIMESTAMP),
       'Insured solely at fault; single-vehicle garage scrape.',
       CAST('2026-10-21 10:00:00' AS TIMESTAMP);
```

Converted `subrogation_indicator` is false, so C is `PdClaimsReview`, not subrogation. If you get `AssignAdjuster`, the ADJUSTER role is missing (pre-V14 convert); insert party 4 on 80088 and chat again.
