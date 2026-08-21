# Deny path demo (claim 404)

Repeatable Agent Studio demo of **DENIED** as the other terminal status for a claim. Claims that are not denied are just **CLOSED** (Closeout on seed **403**). YAML chooses the lane; the LLM does not.

Seed **404** is the deny file. It has its own policy (`PA-1003`), loss, police report, and `loss_driver` row. Do **not** use **401** here — 401 is the PD / subro seed; deleting or restoring its police row does not change 404.

Two Orchestrator chats, with Impala before the first. The crew does **not** invent the exclusion. You flip a coded fact on seed **404**; `deny_claim` then sets `claim_status_code = DENIED`. A later chat hits `DenyAudit` and must **not** UPDATE status again.

Chat the **Orchestrator** as a claims handler would: one sentence and a claim id. Do not mention tools, catalog labels, `run_id`, or `next_step`. Leave **401** / **402** / **403** rows alone.

This path is **R6.1** (insured operator impairment). Citation is **not** auto-deny — that is Human Review on **401** ([probe-action-tests.md](probe-action-tests.md) R5.2). Per-probe chats: same file.

| Snapshot | Claim State | User says | Expect |
|---|---|---|---|
| A | 404 OPEN, insured `impairment_suspected_indicator` true | Please process claim 404. | `DenyUnlawfulOperation` / Deny Agent / `deny_claim` → `DENIED` |
| B | 404 already `DENIED` | Please process claim 404. | `DenyAudit` / Deny Agent / audit + promote; **no** second UPDATE |

Coworker Role must be exactly `Deny Agent`. Playbook `agent_role` is `DenyAgent`.

---

## 0. One-time setup

Skip if already done this session. These checks are for the operator, not the handler chats below.

1. Claims MCP on **0.3.8** or later (`INS_CLAIMS_MCP_V8`). Studio `uvx` from GitHub `main` only sees `get_deny_view` / `deny_claim` after that commit is on the remote.
2. Restart `iceberg-mcp-server-claims`.
3. Operator chat: `Call get_server_info once and stop.` Expect `INS_CLAIMS_MCP_V8` / **`0.3.8`** or newer.
4. Operator chat: `Call list_named_queries once and stop.` Must include `get_deny_view` and `deny_claim`.
5. Workflow Data includes the playbook whose R6.* actions list `get_deny_view` / `deny_claim` (and `save_claim_letter`, drafted only if the handler asks).
6. Same Crew, Roles **exactly**: `Manager agent`, `Deny Agent`. Re-paste Orchestrator Goal from [`agent_studio/studio_tools/agents/orchestrator_agent.md`](../agent_studio/studio_tools/agents/orchestrator_agent.md) so the Deny handoff is in it. Paste [`deny_agent.md`](../agent_studio/studio_tools/agents/deny_agent.md). Attach MCP + Studio `save_claim_letter` on the Deny agent (used only if the handler asks to write the letter).
7. Studio custom tools must **not** pin `ins-claims-agent` to `8f60419`. Re-upload `build_claim_graph` and `route_claim` `tool.py` + `requirements.txt` from this repo (`PACKAGE_PIN: main`). That pin never copied deny flags onto the case JSON, so MCP `unlawful_operation_exclusion: true` still routed `PdClaimsReview`.
8. Claim **404** must exist. Fresh full seed: [`ddl/hive_iceberg/car_insurance_claims_seed_data.sql`](../ddl/hive_iceberg/car_insurance_claims_seed_data.sql). Already-loaded 401/402/403 lake: run [`ddl/hive_iceberg/car_insurance_claims_seed_404.sql`](../ddl/hive_iceberg/car_insurance_claims_seed_404.sql) once.

Do **not** paste Closeout for this demo. CLOSED **403** is a different story.

---

## 1. Confirm 404 is still the seed (OPEN, not cited, not impaired)

Run in Impala (Hue / impala-shell). Do this at the start of every full deny demo.

```sql
USE car_insurance_claims;

SELECT claim_id, claim_status_code, policy_id
FROM car_insurance_claims.claim
WHERE claim_id = 404;
-- expect OPEN, policy 1003

SELECT COUNT(*) AS police_rows
FROM car_insurance_claims.police_report
WHERE claim_id = 404;
-- expect 1 (404's own report; 401's police row is irrelevant)

SELECT driver_role_code, was_cited_indicator, impairment_suspected_indicator
FROM car_insurance_claims.loss_driver
WHERE claim_id = 404 AND driver_role_code = 'INSURED_OPERATOR';
-- expect cited FALSE, impairment FALSE
```

If `was_cited_indicator` is TRUE, Human Review (R5.2) wins **before** R6.1. Set it back to FALSE before you continue. If status is already `DENIED` from a prior run, go to **step 6** restore first, then start here. If the claim row is missing, run the additive seed in step 0.

---

## 2. Flip the coded exclusion (404 only)

Insured-operator impairment on **404**'s `loss_driver` row. Not narrative. Not police `citation_issued_indicator`. Do **not** flip 401. Do **not** change `driver.license_status_code` on driver 501 (that person is also 401's operator).

Do **not** `UPDATE` this Iceberg table. Impala often keeps serving the old snapshot to the Studio MCP, so R6.1 still sees `unlawful_operation_exclusion=false` and you get `PdClaimsReview`. Rewrite the row the same way the PD demo writes police/fault:

```sql
DELETE FROM car_insurance_claims.loss_driver
WHERE claim_id = 404 AND driver_role_code = 'INSURED_OPERATOR';

INSERT INTO TABLE car_insurance_claims.loss_driver
SELECT CAST(5204 AS BIGINT) AS loss_driver_id,
       CAST(303 AS BIGINT) AS loss_event_id,
       CAST(501 AS BIGINT) AS driver_id,
       CAST(404 AS BIGINT) AS claim_id,
       CAST(204 AS BIGINT) AS insurable_object_id,
       'INSURED_OPERATOR' AS driver_role_code,
       FALSE AS was_cited_indicator,
       TRUE AS impairment_suspected_indicator,
       CAST('2025-07-08 22:10:00' AS TIMESTAMP) AS created_at;

INVALIDATE METADATA car_insurance_claims.loss_driver;

SELECT loss_driver_id, impairment_suspected_indicator, was_cited_indicator
FROM car_insurance_claims.loss_driver
WHERE claim_id = 404 AND driver_role_code = 'INSURED_OPERATOR';
-- expect 1 row, 5204, TRUE, FALSE
```

If `DELETE` is rejected and `INSERT` 5204 conflicts, insert **5205** with the same columns (impairment TRUE). R6.1 counts any impaired insured operator.

If that SELECT is empty, 404's `loss_driver` row was never loaded — re-run the additive seed. Do not chat Studio until impairment is TRUE.

Hue `true` with Studio `PdClaimsReview` means the **MCP Impala coordinator** still has old Iceberg metadata, or `= TRUE` did not match the stored boolean. Restart `iceberg-mcp-server-claims`, then a **new** Orchestrator chat. Operator check (not a handler chat):

```text
Call run_named_query once with label get_claim_routing_signals and claim_id 404 and stop.
```

Expect `unlawful_operation_exclusion: true`. If that JSON is still false, MCP is not reading 5204. If it is true but `route_claim` still says **No unlawful-operation exclusion** / `PdClaimsReview`, Studio `build_claim_graph` is pinned to `8f60419`. That pin nested the MCP `signals` object but never copied `unlawful_operation_exclusion` onto the case JSON root, so R6.1 reads false. Re-upload `studio_tools/build_claim_graph/requirements.txt` **and** `route_claim/requirements.txt` (`PACKAGE_PIN: main`, not `8f60419`). Confirm `build_claim_graph` Observation includes `unlawful_operation_exclusion: true`. Then a **new** Orchestrator chat.

---

## 3. Snapshot A — `DenyUnlawfulOperation`

New Orchestrator chat:

```text
Please process claim 404.
```

**Pass:** `next_step=DenyUnlawfulOperation`, `agent_role=DenyAgent`, probe **R6.1**, `deny_claim` `ok=true`, `claim_status_code=DENIED`. `routing_summary` says a denial letter is recommended and will not be drafted unless you ask. No `claim_*_letter.txt` unless you asked to write it. Orchestrator Goal supplies `run_id` (`demo-404-e2e`).

```sql
SELECT claim_id, claim_status_code
FROM car_insurance_claims.claim
WHERE claim_id = 404;
-- expect DENIED

SELECT run_id, event_type, next_step, agent_role, lane, terminal
FROM car_insurance_claims.agent_run_audit
WHERE claim_id = '404' AND next_step = 'DenyUnlawfulOperation'
ORDER BY event_ts DESC
LIMIT 5;
```

`deny_claim` refuses CLOSED (approved) and already-DENIED. This snapshot must be the first deny write on 404.

If you see `RequestPoliceReport`, you processed **401** (or 404 has no police row). If you see `PdClaimsReview` while MCP already showed `unlawful_operation_exclusion: true`, the case JSON was built by pin `8f60419` (or a stale session file) — re-upload the Studio tool pins in step 0, then a **new** Orchestrator chat. If MCP itself is still false, repeat step 2 SELECT / `INVALIDATE METADATA`.

---

## 4. Snapshot B — `DenyAudit`

New Orchestrator chat (status is already `DENIED`):

```text
Please process claim 404.
```

**Pass:** `next_step=DenyAudit`, `agent_role=DenyAgent`, probe **R1.1d**. View `get_deny_view`, then `write_audit_event` + `promote_audit_run`. **Do not** call `deny_claim` again. Impala promote may return `mode=table_append`.

```sql
SELECT claim_id, claim_status_code
FROM car_insurance_claims.claim
WHERE claim_id = 404;
-- still DENIED (one UPDATE only)

SELECT run_id, event_type, next_step, agent_role
FROM car_insurance_claims.agent_run_audit
WHERE claim_id = '404' AND next_step = 'DenyAudit'
ORDER BY event_ts DESC
LIMIT 5;
```

---

## 5. Optional letter

Same or new chat — only if you want the `.txt` draft:

```text
Please write the recommended letter for claim 404.
```

**Pass:** Deny Agent drafts from `get_deny_view` (operators, policy dates, narrative). `save_claim_letter` writes `claim_404_letter.txt`. Does not send mail.

---

## 6. Restore 404

Required before you leave the data, and before R6.2 / R6.3 smokes on this id.

```sql
DELETE FROM car_insurance_claims.loss_driver
WHERE claim_id = 404 AND driver_role_code = 'INSURED_OPERATOR';

INSERT INTO TABLE car_insurance_claims.loss_driver
SELECT CAST(5204 AS BIGINT), CAST(303 AS BIGINT), CAST(501 AS BIGINT),
       CAST(404 AS BIGINT), CAST(204 AS BIGINT), 'INSURED_OPERATOR',
       FALSE, FALSE, CAST('2025-07-08 22:10:00' AS TIMESTAMP);

UPDATE car_insurance_claims.claim
SET claim_status_code = 'OPEN'
WHERE claim_id = 404;

INVALIDATE METADATA car_insurance_claims.loss_driver;
INVALIDATE METADATA car_insurance_claims.claim;

SELECT claim_id, claim_status_code
FROM car_insurance_claims.claim
WHERE claim_id = 404;
-- expect OPEN

SELECT impairment_suspected_indicator, was_cited_indicator
FROM car_insurance_claims.loss_driver
WHERE claim_id = 404 AND driver_role_code = 'INSURED_OPERATOR';
-- expect FALSE, FALSE
```

---

## 7. Repeat from a clean slate

Run **step 1**, then 2 → 4 again. If `deny_claim` says already DENIED, you skipped restore.

---

## Not this demo

| What | Why | Where |
|---|---|---|
| Seed **401** PD / subro | Different file; police DELETE/INSERT is the PD runbook | [pd-path-demo.md](pd-path-demo.md) |
| Insured cited, status stays OPEN | Citation is a reason to look, not a coded exclusion | R5.2 Human Review on **401**; do not flip `was_cited_indicator` on 404 for this demo |
| Seed **403** CLOSED | That is approved closeout | `Please process claim 403.` → Closeout Agent |
| Lapsed policy / excluded driver | Same Deny Agent, different `next_step`; flip **404** / `PA-1003` only | R6.3 / R6.2 in [probe-action-tests.md](probe-action-tests.md). Do **not** lapse policy `1001` |

---

## Short path (one chat)

If 404 is already OPEN and you only need the deny write: run **step 2**, then **step 3**. Always finish with **step 6**.
