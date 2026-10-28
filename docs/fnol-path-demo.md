# FNOL path demo (notice 88)

Repeatable Agent Studio demo of first-notice triage. A notice is **not** a claim. Seed **88** is Marcus Vance / `PA-9018442-01` / RAV4 garage scrape: active policy, listed vehicle, collision covered, no injury or third party, estimated 450 vs 1000 deductible, `RECORD_ONLY_NOTIFICATION`. First match is **F6** `ConvertFnolToIncidentOnly`.

Leave **401** / **402** / **403** / **404** rows alone.

Chat the **Orchestrator** as a handler: one sentence and an FNOL id. Do not mention tools, catalog labels, `run_id`, or probe ids.

| Snapshot | Lake | User says | Expect |
|---|---|---|---|
| Seed | FNOL 88 OPEN, 450 vs 1000 | Please process FNOL 88. | `ConvertFnolToIncidentOnly` / F6; `close_fnol_incident_only` |
| Alias | same | Please process FNOL-2026-00088. | same |
| Grey band | estimated_loss 800 | Please process FNOL 88. | `FnolAdjusterReview` / F4b; `review_fnol` |
| Over deductible | estimated_loss 1500 | Please process FNOL 88. | `ConvertFnolToClaim` / F5; claim **80088** |
| Injury | one `fnol_injury` row | Please process FNOL 88. | `ConvertFnolToClaim` / F2 |
| Lapsed | policy LAPSED | Please process FNOL 88. | `DenyFnolNoCoverage` / F1; `deny_fnol` (no claim row) |
| Already converted | `fnol.claim_id` set | Please process FNOL 88. | `FnolAlreadyTriaged` / F0; then process claim N |

Coworker Roles must be exactly `FNOL Agent`, `Deny Agent`, or `Human Review Agent`.

---

## 0. One-time setup

1. Claims MCP on **0.6.0** (`INS_CLAIMS_MCP_V12`). Restart `iceberg-mcp-server-claims`.
2. Operator chat: `Call get_server_info once and stop.` Expect `INS_CLAIMS_MCP_V12` / **`0.6.0`**.
3. Operator chat: `Call list_named_queries once and stop.` Must include `get_fnol_spine`, `get_fnol_routing_signals`, `deny_fnol`, `close_fnol_incident_only`, `convert_fnol_to_claim`, `review_fnol`.
4. Workflow Data includes the playbook with **F0–F7** before R0.1.
5. Same Crew, Roles **exactly**: `Intake Agent`, `FNOL Agent`, `Deny Agent`, `Human Review Agent`. Re-paste Orchestrator, Deny, Human Review, and FNOL Goals from `agent_studio/studio_tools/agents/`.
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

If a convert created claim 80088, delete that claim (and its reserve) before a second convert, or leave it and expect F0 / idempotent convert.

---

## 3. After convert, process the claim

`convert_fnol_to_claim` inserts `claim_id = 80000 + fnol_id` (80088). A later handler chat is a **claim** intake:

```text
Please process claim 80088.
```

Existing claim probes (PD, R6.*, …) apply. Do not re-run FNOL F* probes on that chat.
