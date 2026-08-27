# Probe / action test prompts

One chat per playbook **probe → action** pair. Chat the **Orchestrator** as a claims handler: one sentence and a claim id. Do not mention tools, catalog labels, `run_id`, or probe ids. Orchestrator Delegates Observation `coworker` (playbook YAML); the specialist Goal owns the write. Pass = `route_claim` returns the expected `next_step`, `agent_role`, `coworker`, `write`, `routing_reason`, and `checks`. Probe ids remain in the JSON for audit.

First-match-wins: a later probe only fires if every earlier action’s `when` failed. You cannot test `R1.4` on claim **402**; litigation (`R1.2b` discovery aging) wins first.

Specialist work runs only if that playbook `coworker` has been configured in Agent Studio. Otherwise Orchestrator Final Answers the route JSON (`SiuAgent`, `SettlementAgent`, `DataQualityAgent`, and `HumanReviewOrWait` have no `coworker`). `HumanCitationReview` maps to Human Review Agent; deny steps map to Deny Agent.

Citation is **not** auto-deny. Narrative is **not** a YAML probe. `R6.1` is the coded unlawful-operation exclusion (impairment or license `SUSPENDED`/`REVOKED`/`UNLICENSED`).

## Handler chats

| Intent | Say |
|---|---|
| Status only | `What's the status of claim <ID>?` |
| Do the next work | `Please process claim <ID>.` |
| Draft the recommended letter | `Please write the recommended letter for claim <ID>.` |

Offline (no Studio): `cd agent_studio && pytest tests/test_route_claim.py tests/test_packs.py`.

---

## Claims (`playbook/playbook.yaml`)

Studio project: live Impala catalog, Workflow Data = repo `ontology/` + `playbook/`. Proven e2e: **402** (Litigation), **403** (Closeout). Seed **401** is PD / subro. Seed **404** is deny (`PA-1003`). Repeatable PD demo: [pd-path-demo.md](pd-path-demo.md). Repeatable DENIED demo: [deny-path-demo.md](deny-path-demo.md). Snapshot-by-snapshot PD path (case JSON → `next_step`): [architecture.md — typical PD path](architecture.md#typical-pd-path-separate-calls).

| Probe | When | `next_step` / `agent_role` / lane | How to fire | Studio id |
|---|---|---|---|---|
| R0.1 | ASK_FALSE | `FixDataQuality` / `DataQualityAgent` / DATA_QUALITY | Graph has no `AutoClaim` at the claim IRI (builder usually prevents this) | none |
| R0.4 | ASK_FALSE | `FixDataQuality` / `DataQualityAgent` / DATA_QUALITY | Claim exists but triangle broken (no policy↔vehicle) | none |
| R1.1 | ASK_TRUE `claim_status_code == "CLOSED"` | `CloseoutAudit` / `CloseoutAgent` / CLOSEOUT | Status CLOSED | **403** |
| R1.1d | ASK_TRUE `claim_status_code == "DENIED"` | `DenyAudit` / `DenyAgent` / DENY | Status DENIED; letter on request; no `deny_claim` | pytest `test_route_denied_terminal`; live **404** after a deny write |
| R5.2 | ASK_TRUE | `HumanCitationReview` / `HumanReviewAgent` / GENERAL | Insured operator `was_cited_indicator`; do not use police `citation_issued_indicator` | pytest `test_route_insured_cited_human_review`; live **401** flip only |
| R6.1 | ASK_TRUE | `DenyUnlawfulOperation` / `DenyAgent` / DENY | Insured impairment or license SUSPENDED/REVOKED/UNLICENSED | pytest `test_route_unlawful_operation_deny`; live **404** flip only |
| R6.2 | ASK_TRUE | `DenyExcludedDriver` / `DenyAgent` / DENY | Insured operator excluded or unlisted (skip PERMISSIVE_USER) | pytest `test_route_excluded_operator_deny`; live **404** / `PA-1003` flip only |
| R6.3 | ASK_TRUE | `DenyLapsedPolicy` / `DenyAgent` / DENY | Policy LAPSED/CANCELLED/EXPIRED, loss outside term, or cancellation ≤ loss | pytest `test_route_lapsed_policy_deny`; live **404** / `PA-1003` flip only |
| R1.2a | ASK_TRUE | `CompleteLitigationFile` / `LitigationAgent` / LITIGATION | Litigated claim missing docket or both counsel ids | pytest `test_route_litigation` |
| R1.2b | ASK_TRUE | `EscalateDiscovery` / `LitigationAgent` / LITIGATION | IN_DISCOVERY, closed_date null, filed_date > 90 days | **402** |
| R1.2 | ASK_TRUE | `LitigationSupport` / `LitigationAgent` / LITIGATION | Remaining litigation (file complete, not aging); `letter_on_request`; draft via `save_claim_letter` only when the user asks | pytest `test_route_litigation_support_letter`; email smoke **402** (skip intake, ask to write) |
| R5.1 | ASK_TRUE | `SiuInvestigation` / `SiuAgent` / SIU | SIU / fraud suspected | pytest `test_route_siu_suspected` |
| R2.3 | ASK_TRUE | `AssignAdjuster` / `DataQualityAgent` / DATA_QUALITY | No ADJUSTER party role | none |
| R2.1 | ASK_TRUE | `RequestPoliceReport` / `PdClaimsAgent` / PD | No police report; earlier probes miss | pytest `test_route_missing_police_report` |
| R2.2 | ASK_TRUE | `DetermineFault` / `PdClaimsAgent` / PD | Police present, no fault determination | pytest `test_route_determine_fault` |
| R2.5 | ASK_TRUE | `CaptureInjuryDetails` / `BiClaimsAgent` / BI | BI_LIABILITY coverage, no injury | none |
| R3.2 | ASK_TRUE | `FollowUpOffer` / `SettlementAgent` / GENERAL | Unresolved (EXTENDED) offer | pytest `test_route_unresolved_offer` |
| R3.4 | ASK_TRUE | `IssuePayment` / `SettlementAgent` / GENERAL | ACCEPTED offer, no payment | none |
| R4.1 | ASK_TRUE | `OpenSubrogationCase` / `SubrogationAgent` / PD | Subro indicator, no subrogation case; gaps filled | pytest `test_route_subrogation_gap` (injected 401) |
| R4.3 | ASK_TRUE | `PursueSubrogationRecovery` / `SubrogationAgent` / PD | Open/negotiating/demanded subro case, no recovery | none |
| R1.3 | ASK_TRUE | `BiClaimsReview` / `BiClaimsAgent` / BI | Injury or BI_LIABILITY; no earlier hit | none |
| R1.4 | ASK_TRUE | `PdClaimsReview` / `PdClaimsAgent` / PD | COLLISION/COMPREHENSIVE; no earlier hit | pytest `test_route_pd_lane`; live **401** may hit this or R4.1 |
| default | no match | `HumanReviewOrWait` / `HumanReviewAgent` / GENERAL | Survives all probes (no PD/BI coverage, no gaps/flags) | none |

### R0.1 ASK_FALSE — FixDataQuality

```text
What's the status of claim 999001?
```

Expect `FixDataQuality` / `DataQualityAgent` (R0.1). Only passes if the session graph has no `ex:AutoClaim` at that IRI. A successful `build_claim_graph` usually makes R0.1 true.

### R0.4 ASK_FALSE — FixDataQuality (triangle)

```text
What's the status of claim 999004?
```

Expect `FixDataQuality` / `DataQualityAgent` (R0.4). Needs a claim row whose spine omits policy or vehicle (or `policy_covers_vehicle` false) so the triangle ASK is false while R0.1 is true.

### R1.1 ASK_TRUE CLOSED — CloseoutAudit (403)

```text
Please process claim 403.
```

Expect `CloseoutAudit` / `CloseoutAgent` (R1.1), then audit write + promote.

### R1.1d ASK_TRUE DENIED — DenyAudit

Offline: `pytest tests/test_route_claim.py::test_route_denied_terminal`.

Live: after an R6.* deny write on **404**, chat again. Expect `DenyAudit` / `DenyAgent` (no second status UPDATE). Full runbook: [deny-path-demo.md](deny-path-demo.md). Restore **404** to OPEN afterward.

```text
Please process claim 404.
```

### R5.2 ASK_TRUE — HumanCitationReview (401 smoke)

Insured `loss_driver.was_cited_indicator` only. Do **not** set police `citation_issued_indicator` (seed 401 is already true for adverse speeding).

```sql
-- 401 only. Restore after.
UPDATE car_insurance_claims.loss_driver
SET was_cited_indicator = TRUE
WHERE claim_id = 401 AND driver_role_code = 'INSURED_OPERATOR';
```

```text
Please process claim 401.
```

Expect `HumanCitationReview` / `HumanReviewAgent` (R5.2). Status stays OPEN. Do not deny. Restore: `was_cited_indicator = FALSE` for that 401 insured operator row.

### R6.1 ASK_TRUE — DenyUnlawfulOperation (404 smoke)

```sql
-- 404 only. Rewrite the row (do not UPDATE). Restore after. Do not flip 401/402/403.
DELETE FROM car_insurance_claims.loss_driver
WHERE claim_id = 404 AND driver_role_code = 'INSURED_OPERATOR';
INSERT INTO TABLE car_insurance_claims.loss_driver
SELECT CAST(5204 AS BIGINT), CAST(303 AS BIGINT), CAST(501 AS BIGINT),
       CAST(404 AS BIGINT), CAST(204 AS BIGINT), 'INSURED_OPERATOR',
       FALSE, TRUE, CAST('2025-07-08 22:10:00' AS TIMESTAMP);
INVALIDATE METADATA car_insurance_claims.loss_driver;
```

```text
Please process claim 404.
```

Expect `DenyUnlawfulOperation` / `DenyAgent` (R6.1) and `claim_status_code=DENIED`. Full runbook: [deny-path-demo.md](deny-path-demo.md).

Optional letter:

```text
Please write the recommended letter for claim 404.
```

Restore 404: `impairment_suspected_indicator = FALSE` and `claim_status_code = 'OPEN'`.

### R6.2 ASK_TRUE — DenyExcludedDriver

Offline: `pytest tests/test_route_claim.py::test_route_excluded_operator_deny`.

Live **404**: set `policy_driver.is_excluded_driver = TRUE` for policy **1003** / driver 501 (or expire that listing). Do **not** flip PA-1001. Same chat as R6.1. Expect `DenyExcludedDriver`. Restore listing and OPEN.

### R6.3 ASK_TRUE — DenyLapsedPolicy

Offline: `pytest tests/test_route_claim.py::test_route_lapsed_policy_deny`.

Live **404**: set policy **1003** `policy_status_code = 'LAPSED'` (or `cancellation_date` ≤ loss date). Do **not** lapse PA-1001. Same chat as R6.1. Expect `DenyLapsedPolicy`. Restore `ACTIVE` and OPEN.

### R1.2a ASK_TRUE — CompleteLitigationFile

```text
Please process claim 99912a.
```

Expect `CompleteLitigationFile` / `LitigationAgent` (R1.2a). Offline: `pytest tests/test_route_claim.py::test_route_litigation` (litigation indicator, empty signals).

### R1.2b ASK_TRUE — EscalateDiscovery (402)

```text
Please process claim 402.
```

Expect `EscalateDiscovery` / `LitigationAgent` (R1.2b). Offline: `pytest tests/test_route_claim.py::test_route_litigation_discovery_aging`.

### R1.2 ASK_TRUE — LitigationSupport (letter on request)

No live seed today. Seed **402** is R1.2b (`EscalateDiscovery`), not this probe. To fire R1.2 you need a litigated claim with docket + counsel and discovery **not** aging (not `IN_DISCOVERY` with `filed_date` older than 90 days and `closed_date` null). Intake reports that a letter is recommended. It does **not** draft the letter unless you ask.

```text
Please process claim <ID>.
```

Expect `LitigationSupport` / `LitigationAgent` (R1.2), `letter_on_request` true. Then, to draft:

```text
Please write the recommended letter for claim <ID>.
```

Offline: `pytest tests/test_route_claim.py::test_route_litigation_support_letter` (route only).

### Generate litigation hold/status email (letter artifact)

Use this when you want the `.txt` email, including on seed **402** (402 would otherwise route to R1.2b and would not recommend a letter). `save_claim_letter` writes the file; it does not send mail.

```text
Please write a litigation hold letter for claim 402.
```

Pass = `save_claim_letter` returns `status=success` and `claim_402_letter.txt` is in the session folder. Offline file write (canned body, no LLM): `pytest tests/test_studio_io.py::test_save_claim_letter_writes_txt`.

### R5.1 ASK_TRUE — SiuInvestigation

```text
What's the status of claim 999501?
```

Expect `SiuInvestigation` / `SiuAgent` / SIU (R5.1). SiuAgent is not configured in Agent Studio — route JSON is enough. Studio needs a database record with SIU/fraud suspected and no litigation/CLOSED. Offline: `pytest tests/test_route_claim.py::test_route_siu_suspected`.

### R2.3 ASK_TRUE — AssignAdjuster

```text
What's the status of claim 999203?
```

Expect `AssignAdjuster` / `DataQualityAgent` (R2.3). Needs OPEN, not litigation/SIU, and no ADJUSTER role on the claim.

### R2.0 ASK_TRUE — CollectIncidentReportNumber

```text
Please process claim 401.
```

Expect `CollectIncidentReportNumber` / `PdClaimsAgent` (R2.0). An SMS is written to `claim_outbound_message` (no carrier) and a session copy is always saved to `claim_{id}_sms.txt`. Offline: `pytest tests/test_route_claim.py::test_route_collect_incident_report_number`. Needs no `police_report` and no `claim_police_intake` row. Live PD path: [pd-path-demo.md](pd-path-demo.md).

### R2.1 ASK_TRUE — RequestPoliceReport

```text
Please process claim 401.
```

Expect `RequestPoliceReport` / `PdClaimsAgent` (R2.1). A police-report request letter for the **incident report number** (not claim id) is recommended and will not be drafted unless you ask. Offline: `pytest tests/test_route_claim.py::test_route_missing_police_report`. Apply `pd_task` + intake DDL before the live write. Needs `claim_police_intake` present and no `police_report` row. Live PD path: [pd-path-demo.md](pd-path-demo.md).

### R2.2 ASK_TRUE — DetermineFault

```text
Please process claim 999202.
```

Expect `DetermineFault` / `PdClaimsAgent` (R2.2). Needs police report present, no fault determination, and no earlier hit. Offline: `pytest tests/test_route_claim.py::test_route_determine_fault`.

### R2.5 ASK_TRUE — CaptureInjuryDetails

```text
Please process claim 999205.
```

Expect `CaptureInjuryDetails` / `BiClaimsAgent` (R2.5). Needs BI_LIABILITY coverage and no `hasInjury`.

### R3.2 ASK_TRUE — FollowUpOffer

```text
What's the status of claim 999302?
```

Expect `FollowUpOffer` / `SettlementAgent` (R3.2). SettlementAgent is not configured in Agent Studio — route JSON is enough. Offline: `pytest tests/test_route_claim.py::test_route_unresolved_offer`.

### R3.4 ASK_TRUE — IssuePayment

```text
What's the status of claim 999304?
```

Expect `IssuePayment` / `SettlementAgent` (R3.4). Needs an ACCEPTED offer and no loss payment; gaps and SIU/litigation must miss.

### R4.1 ASK_TRUE — OpenSubrogationCase

```text
Please process claim 401.
```

If `OpenSubrogationCase`: expect `SubrogationAgent` (R4.1). If `PdClaimsAgent`, that is also a valid live 401 outcome. Injected pytest (police+fault, subro indicator, no case): `test_route_subrogation_gap`. Live **401** may already have a subro case and skip R4.1.

### R4.3 ASK_TRUE — PursueSubrogationRecovery

```text
Please process claim 999403.
```

Expect `PursueSubrogationRecovery` / `SubrogationAgent` (R4.3). Needs an OPEN/NEGOTIATING/DEMANDED subrogation case and no recovery. R4.1 must not fire (case already exists).

### R1.3 ASK_TRUE — BiClaimsReview

```text
Please process claim 999103.
```

Expect `BiClaimsReview` / `BiClaimsAgent` (R1.3). Needs injury or BI_LIABILITY, and no R2.5 (injury already present) or earlier hits.

### R1.4 ASK_TRUE — PdClaimsReview

```text
Please process claim 401.
```

Expect `PdClaimsReview` / `PdClaimsAgent` (R1.4) when police, fault, and subro gaps are already filled. Offline: `pytest tests/test_route_claim.py::test_route_pd_lane`.

### default_action — HumanReviewOrWait

```text
What's the status of claim 999000?
```

Expect `HumanReviewOrWait` / `HumanReviewAgent`, terminal. Needs a valid triangle claim that matches **no** action `when` (no CLOSED/litigation/SIU/gaps/offers/subro/BI/PD coverage). No seed today.

---

## Distributions (`packs/retirement_distributions/playbook/playbook.yaml`)

Separate Studio project. Fixture cases: **7001**, **7002**, **7003**. MCP must serve those labels (`PACK_ID` resume; see [finserv-pattern-pack-status.md](finserv-pattern-pack-status.md)).

| Probe | When | `next_step` / `agent_role` / `coworker` | Studio id |
|---|---|---|---|
| R0.1 | ASK_FALSE | `FixDataQuality` / `DataQualityAgent` / omit | none (unknown id) |
| R1.1 | ASK_TRUE CLOSED | `CloseoutAudit` / `CloseoutAgent` / `Closeout Agent` | none (add CLOSED fixture) |
| R2.1 | ASK_TRUE | `HoldReview` / `ExceptionQueueAgent` / `Exception Queue Agent` | none (add `hold_or_aml_flag`) |
| R2.2 | ASK_TRUE | `RequestSubstantiation` / `ExceptionQueueAgent` / `Exception Queue Agent` | **7002** |
| R2.3 | ASK_TRUE | `RmdReview` / `RmdOpsAgent` / `RMD Ops Agent` | **7003** |
| default | no match | `ProcessDistribution` / `DistributionOpsAgent` / `Distribution Ops Agent` | **7001** |

### R0.1 ASK_FALSE

```text
What's the status of claim 7009?
```

Expect `FixDataQuality` / `DataQualityAgent` (R0.1).

### R1.1 ASK_TRUE CLOSED

```text
Please process claim 7004.
```

Expect `CloseoutAudit` / `CloseoutAgent` (R1.1). Needs a fixture spine with `request_status_code: CLOSED` before this chat is valid.

### R2.1 ASK_TRUE — HoldReview

```text
Please process claim 7005.
```

Expect `HoldReview` / `ExceptionQueueAgent` (R2.1). Needs `hold_or_aml_flag: true` and not CLOSED.

### R2.2 ASK_TRUE — RequestSubstantiation (7002)

```text
Please process claim 7002.
```

Expect `RequestSubstantiation` / `ExceptionQueueAgent` (R2.2). Offline: `pytest tests/test_packs.py::test_distribution_7002_exception`.

### R2.3 ASK_TRUE — RmdReview (7003)

```text
Please process claim 7003.
```

Expect `RmdReview` / `RmdOpsAgent` (R2.3). Offline: `pytest tests/test_packs.py::test_distribution_7003_rmd`.

### default — ProcessDistribution (7001)

```text
Please process claim 7001.
```

Expect `ProcessDistribution` / `DistributionOpsAgent`. Offline: `pytest tests/test_packs.py::test_distribution_7001_ops`.

---

## Rollovers (`packs/retirement_rollovers/playbook/playbook.yaml`)

Separate Studio project. Fixture cases: **8001**, **8002**.

| Probe | When | `next_step` / `agent_role` / `coworker` | Studio id |
|---|---|---|---|
| R0.1 | ASK_FALSE | `FixDataQuality` / `DataQualityAgent` / omit | none |
| R1.1 | ASK_TRUE CLOSED | `CloseoutAudit` / `CloseoutAgent` / `Closeout Agent` | none (add CLOSED fixture) |
| R2.1 | ASK_TRUE | `ErisaReview` / `ErisaReviewAgent` / `ERISA Review Agent` | **8001** |
| R2.2 | ASK_TRUE | `RequestDocuments` / `ExceptionQueueAgent` / `Exception Queue Agent` | none (add `missing_required_docs`) |
| default | no match | `ProcessRollover` / `RolloverOpsAgent` / `Rollover Ops Agent` | **8002** |

### R0.1 ASK_FALSE

```text
What's the status of claim 8009?
```

Expect `FixDataQuality` / `DataQualityAgent` (R0.1).

### R1.1 ASK_TRUE CLOSED

```text
Please process claim 8004.
```

Expect `CloseoutAudit` / `CloseoutAgent` (R1.1). Needs a CLOSED rollover fixture.

### R2.1 ASK_TRUE — ErisaReview (8001)

```text
Please process claim 8001.
```

Expect `ErisaReview` / `ErisaReviewAgent` (R2.1). Offline: `pytest tests/test_packs.py::test_rollover_8001_erisa`.

### R2.2 ASK_TRUE — RequestDocuments

```text
Please process claim 8003.
```

Expect `RequestDocuments` / `ExceptionQueueAgent` (R2.2). Needs `missing_required_docs: true` and `missing_spousal_consent: false` (else R2.1 wins).

### default — ProcessRollover (8002)

```text
Please process claim 8002.
```

Expect `ProcessRollover` / `RolloverOpsAgent`. Offline: `pytest tests/test_packs.py::test_rollover_8002_ops`.
