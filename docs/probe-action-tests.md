# Probe / action test prompts

One chat prompt per playbook **probe → action** pair. Chat the **Orchestrator** (not Manager). The LLM must not choose the lane. Pass = `route_claim` returns the expected `next_step`, `agent_role`, `routing_reason`, and `checks`. Probe ids remain in the JSON for audit (`reason_probe_ids`); do not lead the chat with them.

First-match-wins: a later probe only fires if every earlier action’s `when` failed. You cannot test `R1.4` on claim **402**; litigation (`R1.2b` discovery aging) wins first.

Specialist Delegate after route only if that `agent_role` has a Studio paste. Otherwise Orchestrator Final Answers the route JSON (`SiuAgent`, `SettlementAgent`, `DataQualityAgent`, `HumanReviewAgent`).

`R6.1` (`context_probe`) is CONSTRUCT only. It has no action pair.

## Shared intake prompt

Replace `<ID>` and the expect line. Keep the rest.

```text
Intake and route claim_id <ID>. Do not skip the Orchestrator.

1) Delegate ONCE to Manager. Task: structured intake for <ID> —
   run_named_query spine, then routing signals, then build, validate, route.
   STOP after route_claim. Return next_step, lane, agent_role, routing_reason,
   and the checks (Why this routing). Do not lead with probe ids.
   Do not call specialist views or write_audit_event.

2) Map agent_role to coworker Role from your Goal. If that Role is in the Crew,
   Delegate ONCE. If not, Final Answer the route JSON. Do not invent a Role.

Expect: next_step=<STEP>, agent_role=<AGENT>, routing_reason names the assigned check.
```

Offline (no Studio): `cd agent_studio && pytest tests/test_route_claim.py tests/test_packs.py`.

---

## Claims (`playbook/playbook.yaml`)

Studio project: live Impala catalog, Workflow Data = repo `ontology/` + `playbook/`. Proven e2e: **402** (Litigation), **403** (Closeout). Seed **401** is lake-dependent (often PD or subro). Repeatable PD demo (Impala reset + three chats): [pd-path-demo.md](pd-path-demo.md). Snapshot-by-snapshot PD path (case JSON → `next_step`): [architecture.md — typical PD path](architecture.md#typical-pd-path-separate-calls).

| Probe | When | `next_step` / `agent_role` / lane | How to fire | Studio id |
|---|---|---|---|---|
| R0.1 | ASK_FALSE | `FixDataQuality` / `DataQualityAgent` / DATA_QUALITY | Graph has no `AutoClaim` at the claim IRI (builder usually prevents this) | none |
| R0.4 | ASK_FALSE | `FixDataQuality` / `DataQualityAgent` / DATA_QUALITY | Claim exists but triangle broken (no policy↔vehicle) | none |
| R1.1 | SELECT_EQUALS CLOSED | `CloseoutAudit` / `CloseoutAgent` / CLOSEOUT | Status CLOSED | **403** |
| R1.2a | ASK_TRUE | `CompleteLitigationFile` / `LitigationAgent` / LITIGATION | Litigated claim missing docket or both counsel ids | pytest `test_route_litigation` |
| R1.2b | ASK_TRUE | `EscalateDiscovery` / `LitigationAgent` / LITIGATION | IN_DISCOVERY, closed_date null, filed_date > 90 days | **402** |
| R1.2 | ASK_TRUE | `LitigationSupport` / `LitigationAgent` / LITIGATION | Remaining litigation (file complete, not aging); `needs_llm`; letter via `save_claim_letter` | pytest `test_route_litigation_support_letter`; email smoke **402** (skip intake) |
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
Intake and route claim_id 999001. Do not skip the Orchestrator.
Delegate ONCE to Manager: spine, signals, build, validate, route. STOP after route.
Expect next_step=FixDataQuality, agent_role=DataQualityAgent, reason_probe_ids includes R0.1.
If agent_role has no coworker, Final Answer the route JSON.
```

Only passes if the session graph has no `ex:AutoClaim` at that IRI. A successful `build_claim_graph` usually makes R0.1 true.

### R0.4 ASK_FALSE — FixDataQuality (triangle)

```text
Intake and route claim_id 999004. Do not skip the Orchestrator.
Delegate ONCE to Manager: spine, signals, build, validate, route. STOP after route.
Expect next_step=FixDataQuality, agent_role=DataQualityAgent, reason_probe_ids includes R0.4.
```

Needs a claim row whose spine omits policy or vehicle (or `policy_covers_vehicle` false) so the triangle ASK is false while R0.1 is true.

### R1.1 SELECT_EQUALS CLOSED — CloseoutAudit (403)

```text
Intake and route claim_id 403, then complete the post-route specialist work.
Do not skip the Orchestrator.

1) Delegate ONCE to Manager: structured intake for 403. STOP after route_claim.
   Expect next_step=CloseoutAudit, agent_role=CloseoutAgent, reason_probe_ids includes R1.1.

2) Delegate ONCE to Closeout Agent.
   Task: claim_id=403 run_id=demo-403-close.
   run_named_write write_audit_event then run_named_write promote_audit_run.

3) Final Answer: route + exact write JSON + exact promote JSON. STOP.
```

### R1.2a ASK_TRUE — CompleteLitigationFile

```text
Intake and route claim_id 99912a. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=CompleteLitigationFile, agent_role=LitigationAgent,
reason_probe_ids includes R1.2a.
If Litigation Agent is in the Crew: Delegate ONCE — get_litigation_view
then create_litigation_task task_type_code COMPLETE_FILE.
```

Offline: `pytest tests/test_route_claim.py::test_route_litigation` (litigation indicator, empty signals).

### R1.2b ASK_TRUE — EscalateDiscovery (402)

```text
Intake and route claim_id 402, then complete the post-route specialist work.
Do not skip the Orchestrator.

1) Delegate ONCE to Manager: structured intake for 402. STOP after route_claim.
   Expect next_step=EscalateDiscovery, agent_role=LitigationAgent,
   reason_probe_ids includes R1.2b.

2) Delegate ONCE to Litigation Agent.
   Task: claim_id=402 run_id=demo-402-e2e next_step=EscalateDiscovery.
   run_named_query {"label":"get_litigation_view","claim_id":"402"}
   then run_named_write create_litigation_task
   event_json task_type_code ESCALATE_DISCOVERY.

3) Final Answer: route + specialist summary + exact write JSON. STOP.
```

Offline: `pytest tests/test_route_claim.py::test_route_litigation_discovery_aging`.

### R1.2 ASK_TRUE — LitigationSupport (letter)

No live seed today. Seed **402** is R1.2b (`EscalateDiscovery`), not this probe. To fire R1.2 you need a litigated claim with docket + counsel and discovery **not** aging (not `IN_DISCOVERY` with `filed_date` older than 90 days and `closed_date` null).

```text
Intake and route claim_id <ID>, then complete the post-route specialist work.
Do not skip the Orchestrator.

1) Delegate ONCE to Manager: structured intake for <ID>. STOP after route_claim.
   Expect next_step=LitigationSupport, agent_role=LitigationAgent, needs_llm true,
   reason_probe_ids includes R1.2.

2) Delegate ONCE to Litigation Agent.
   Task: claim_id=<ID> run_id=demo-<ID>-letter next_step=LitigationSupport.
   run_named_query {"label":"get_litigation_view","claim_id":"<ID>"}
   then run_named_write write_audit_event.
   Draft a short hold/status email from the view only (Subject + body).
   Do not invent docket, counsel, dates, or amounts.
   Then save_claim_letter once with that body.
   Do not create a litigation_task.

3) Final Answer: route + email summary + exact write JSON + letter file_path.
   Expect SESSION_DIRECTORY/claim_<ID>_letter.txt. STOP.
```

Offline: `pytest tests/test_route_claim.py::test_route_litigation_support_letter`
(route only).

### Generate litigation hold/status email (letter artifact)

Use this when you want the `.txt` email, including on seed **402** (skip intake — 402 would otherwise route to R1.2b and would not draft a letter). Chat the **Orchestrator**. `save_claim_letter` writes the file; it does not send mail.

```text
Generate a litigation hold/status email for claim_id 402.
Do not skip the Orchestrator. Do not run structured claim intake.

1) Delegate ONCE to Litigation Agent (Role exactly "Litigation Agent").
   Task: claim_id=402 run_id=demo-402-letter next_step=LitigationSupport.
   Call run_named_query once:
   {"label":"get_litigation_view","claim_id":"402"}
   Then run_named_write once label write_audit_event.
   Draft a short hold/status email from the view Observation only.
   Include a Subject line and 1–2 short paragraphs (status, docket, venue,
   counsel, dates, demand). Do not invent ids or amounts.
   Then call save_claim_letter once:
   {"claim_id":"402","run_id":"demo-402-letter","next_step":"LitigationSupport",
    "body":"<the drafted email>"}
   Do not create_litigation_task. Do not send mail.

2) Final Answer: the email text, exact write JSON, and letter file_path.
   Expect claim_402_letter.txt in SESSION_DIRECTORY. Then STOP.
   Do not Delegate a second time.
```

Pass = `save_claim_letter` returns `status=success` and `claim_402_letter.txt` is in the session folder. Offline file write (canned body, no LLM): `pytest tests/test_studio_io.py::test_save_claim_letter_writes_txt`.

### R5.1 ASK_TRUE — SiuInvestigation

```text
Intake and route claim_id 999501. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=SiuInvestigation, agent_role=SiuAgent, lane=SIU,
reason_probe_ids includes R5.1.
Final Answer the route JSON (no SiuAgent paste). Do not invent a Role.
```

Studio needs a lake row with SIU/fraud suspected and no litigation/CLOSED. Offline: `pytest tests/test_route_claim.py::test_route_siu_suspected`.

### R2.3 ASK_TRUE — AssignAdjuster

```text
Intake and route claim_id 999203. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=AssignAdjuster, agent_role=DataQualityAgent,
reason_probe_ids includes R2.3.
Final Answer the route JSON (no DataQualityAgent paste).
```

Needs OPEN, not litigation/SIU, and no ADJUSTER role on the claim.

### R2.1 ASK_TRUE — RequestPoliceReport

```text
Intake and route claim_id 999201. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=RequestPoliceReport, agent_role=PdClaimsAgent,
reason_probe_ids includes R2.1.
If PD Claims Agent is in the Crew, Delegate ONCE (get_pd_view then
create_pd_task REQUEST_POLICE_REPORT then save_claim_letter).
```

Offline: `pytest tests/test_route_claim.py::test_route_missing_police_report`. Apply `pd_task` DDL before the live write. Needs a claim with no `police_report` row (seed **401** already has one).

### R2.2 ASK_TRUE — DetermineFault

```text
Intake and route claim_id 999202. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=DetermineFault, agent_role=PdClaimsAgent,
reason_probe_ids includes R2.2.
If PD Claims Agent is in the Crew, Delegate ONCE (get_pd_view then
create_pd_task DETERMINE_FAULT). Do not call save_claim_letter.
```

Needs police report present, no fault determination, and no earlier hit. Offline: `pytest tests/test_route_claim.py::test_route_determine_fault`.

### R2.5 ASK_TRUE — CaptureInjuryDetails

```text
Intake and route claim_id 999205. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=CaptureInjuryDetails, agent_role=BiClaimsAgent,
reason_probe_ids includes R2.5.
If BI Claims Agent is in the Crew, Delegate ONCE (view get_bi_view then write).
```

Needs BI_LIABILITY coverage and no `hasInjury`.

### R3.2 ASK_TRUE — FollowUpOffer

```text
Intake and route claim_id 999302. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=FollowUpOffer, agent_role=SettlementAgent,
reason_probe_ids includes R3.2.
Final Answer the route JSON (no SettlementAgent paste).
```

Offline: `pytest tests/test_route_claim.py::test_route_unresolved_offer`.

### R3.4 ASK_TRUE — IssuePayment

```text
Intake and route claim_id 999304. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=IssuePayment, agent_role=SettlementAgent,
reason_probe_ids includes R3.4.
Final Answer the route JSON.
```

Needs an ACCEPTED offer and no loss payment; gaps and SIU/litigation must miss.

### R4.1 ASK_TRUE — OpenSubrogationCase

```text
Intake and route claim_id 401. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake for 401. STOP after route.
If next_step=OpenSubrogationCase: expect agent_role=SubrogationAgent,
reason_probe_ids includes R4.1. Delegate ONCE to Subrogation Agent
(view get_subrogation_view then write), run_id=demo-401-sub.
If agent_role is PdClaimsAgent: Delegate ONCE to PD Claims Agent
(view get_pd_view then create_pd_task PD_REVIEW), run_id=demo-401-pd.
```

Injected pytest (police+fault, subro indicator, no case): `test_route_subrogation_gap`. Live **401** may already have a subro case and skip R4.1.

### R4.3 ASK_TRUE — PursueSubrogationRecovery

```text
Intake and route claim_id 999403. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=PursueSubrogationRecovery, agent_role=SubrogationAgent,
reason_probe_ids includes R4.3.
If Subrogation Agent is in the Crew, Delegate ONCE (get_subrogation_view then write).
```

Needs an OPEN/NEGOTIATING/DEMANDED subrogation case and no recovery. R4.1 must not fire (case already exists).

### R1.3 ASK_TRUE — BiClaimsReview

```text
Intake and route claim_id 999103. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=BiClaimsReview, agent_role=BiClaimsAgent,
reason_probe_ids includes R1.3.
Delegate ONCE to BI Claims Agent (get_bi_view then write) if in the Crew.
```

Needs injury or BI_LIABILITY, and no R2.5 (injury already present) or earlier hits.

### R1.4 ASK_TRUE — PdClaimsReview

```text
Intake and route claim_id 401. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake for 401. STOP after route.
If next_step=PdClaimsReview: expect agent_role=PdClaimsAgent,
reason_probe_ids includes R1.4. Delegate ONCE to PD Claims Agent
(get_pd_view then create_pd_task PD_REVIEW) if in the Crew.
```

Offline: `pytest tests/test_route_claim.py::test_route_pd_lane`.

### default_action — HumanReviewOrWait

```text
Intake and route claim_id 999000. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=HumanReviewOrWait, agent_role=HumanReviewAgent, terminal=true.
Final Answer the route JSON.
```

Needs a valid triangle claim that matches **no** action `when` (no CLOSED/litigation/SIU/gaps/offers/subro/BI/PD coverage). No seed today.

---

## Distributions (`packs/retirement_distributions/playbook/playbook.yaml`)

Separate Studio project. Fixture cases: **7001**, **7002**, **7003**. MCP must serve those labels (`PACK_ID` resume; see [finserv-pattern-pack-status.md](finserv-pattern-pack-status.md)).

| Probe | When | `next_step` / `agent_role` | Studio id |
|---|---|---|---|
| R0.1 | ASK_FALSE | `FixDataQuality` / `DataQualityAgent` | none (unknown id) |
| R1.1 | SELECT_EQUALS CLOSED | `CloseoutAudit` / `CloseoutAgent` | none (add CLOSED fixture) |
| R2.1 | ASK_TRUE | `HoldReview` / `ExceptionQueueAgent` | none (add `hold_or_aml_flag`) |
| R2.2 | ASK_TRUE | `RequestSubstantiation` / `ExceptionQueueAgent` | **7002** |
| R2.3 | ASK_TRUE | `RmdReview` / `RmdOpsAgent` | **7003** |
| default | no match | `ProcessDistribution` / `DistributionOpsAgent` | **7001** |

### R0.1 ASK_FALSE

```text
Intake and route claim_id 7009. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=FixDataQuality, agent_role=DataQualityAgent,
reason_probe_ids includes R0.1.
Final Answer the route JSON.
```

### R1.1 SELECT_EQUALS CLOSED

```text
Intake and route claim_id 7004. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=CloseoutAudit, agent_role=CloseoutAgent,
reason_probe_ids includes R1.1.
```

Needs a fixture spine with `request_status_code: CLOSED` before this prompt is valid.

### R2.1 ASK_TRUE — HoldReview

```text
Intake and route claim_id 7005. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=HoldReview, agent_role=ExceptionQueueAgent,
reason_probe_ids includes R2.1.
Delegate ONCE to Exception Queue Agent (get_distribution_exception_view then write).
```

Needs `hold_or_aml_flag: true` and not CLOSED.

### R2.2 ASK_TRUE — RequestSubstantiation (7002)

```text
Intake and route claim_id 7002, then complete the post-route specialist work.
Do not skip the Orchestrator.

1) Delegate ONCE to Manager: structured intake for 7002. STOP after route.
   Expect next_step=RequestSubstantiation, agent_role=ExceptionQueueAgent,
   reason_probe_ids includes R2.2.

2) Delegate ONCE to Exception Queue Agent.
   Task: claim_id=7002 run_id=demo-7002-exc.
   run_named_query {"label":"get_distribution_exception_view","claim_id":"7002"}
   then run_named_write write_audit_event.

3) Final Answer: route + summary + exact write JSON. STOP.
```

Offline: `pytest tests/test_packs.py::test_distribution_7002_exception`.

### R2.3 ASK_TRUE — RmdReview (7003)

```text
Intake and route claim_id 7003, then complete the post-route specialist work.
Do not skip the Orchestrator.

1) Delegate ONCE to Manager: structured intake for 7003. STOP after route.
   Expect next_step=RmdReview, agent_role=RmdOpsAgent,
   reason_probe_ids includes R2.3.

2) Delegate ONCE to RMD Ops Agent.
   Task: claim_id=7003 run_id=demo-7003-rmd.
   run_named_query {"label":"get_rmd_view","claim_id":"7003"}
   then run_named_write write_audit_event.

3) Final Answer: route + summary + exact write JSON. STOP.
```

Offline: `pytest tests/test_packs.py::test_distribution_7003_rmd`.

### default — ProcessDistribution (7001)

```text
Intake and route claim_id 7001, then complete the post-route specialist work.
Do not skip the Orchestrator.

1) Delegate ONCE to Manager: structured intake for 7001. STOP after route.
   Expect next_step=ProcessDistribution, agent_role=DistributionOpsAgent.
   reason_probe_ids should not include R2.1, R2.2, or R2.3 as the matching action.

2) Delegate ONCE to Distribution Ops Agent.
   Task: claim_id=7001 run_id=demo-7001-ops.
   run_named_write write_audit_event only.

3) Final Answer: route + exact write JSON. STOP.
```

Offline: `pytest tests/test_packs.py::test_distribution_7001_ops`.

---

## Rollovers (`packs/retirement_rollovers/playbook/playbook.yaml`)

Separate Studio project. Fixture cases: **8001**, **8002**.

| Probe | When | `next_step` / `agent_role` | Studio id |
|---|---|---|---|
| R0.1 | ASK_FALSE | `FixDataQuality` / `DataQualityAgent` | none |
| R1.1 | SELECT_EQUALS CLOSED | `CloseoutAudit` / `CloseoutAgent` | none (add CLOSED fixture) |
| R2.1 | ASK_TRUE | `ErisaReview` / `ErisaReviewAgent` | **8001** |
| R2.2 | ASK_TRUE | `RequestDocuments` / `ExceptionQueueAgent` | none (add `missing_required_docs`) |
| default | no match | `ProcessRollover` / `RolloverOpsAgent` | **8002** |

### R0.1 ASK_FALSE

```text
Intake and route claim_id 8009. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=FixDataQuality, agent_role=DataQualityAgent,
reason_probe_ids includes R0.1.
Final Answer the route JSON.
```

### R1.1 SELECT_EQUALS CLOSED

```text
Intake and route claim_id 8004. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=CloseoutAudit, agent_role=CloseoutAgent,
reason_probe_ids includes R1.1.
```

Needs a CLOSED rollover fixture.

### R2.1 ASK_TRUE — ErisaReview (8001)

```text
Intake and route claim_id 8001, then complete the post-route specialist work.
Do not skip the Orchestrator.

1) Delegate ONCE to Manager: structured intake for 8001. STOP after route.
   Expect next_step=ErisaReview, agent_role=ErisaReviewAgent,
   reason_probe_ids includes R2.1.

2) Delegate ONCE to ERISA Review Agent.
   Task: claim_id=8001 run_id=demo-8001-erisa.
   run_named_query {"label":"get_erisa_review_view","claim_id":"8001"}
   then run_named_write write_audit_event.

3) Final Answer: route + summary + exact write JSON. STOP.
```

Offline: `pytest tests/test_packs.py::test_rollover_8001_erisa`.

### R2.2 ASK_TRUE — RequestDocuments

```text
Intake and route claim_id 8003. Do not skip the Orchestrator.
Delegate ONCE to Manager: structured intake. STOP after route.
Expect next_step=RequestDocuments, agent_role=ExceptionQueueAgent,
reason_probe_ids includes R2.2.
Delegate ONCE to Exception Queue Agent (write_audit_event only) if in the Crew.
```

Needs `missing_required_docs: true` and `missing_spousal_consent: false` (else R2.1 wins).

### default — ProcessRollover (8002)

```text
Intake and route claim_id 8002, then complete the post-route specialist work.
Do not skip the Orchestrator.

1) Delegate ONCE to Manager: structured intake for 8002. STOP after route.
   Expect next_step=ProcessRollover, agent_role=RolloverOpsAgent.

2) Delegate ONCE to Rollover Ops Agent.
   Task: claim_id=8002 run_id=demo-8002-ops.
   run_named_write write_audit_event only.

3) Final Answer: route + exact write JSON. STOP.
```

Offline: `pytest tests/test_packs.py::test_rollover_8002_ops`.
