# Atlas + Ranger integration (deferred)

**Status:** Parked — not on the claim-routing critical path  
**Date:** 2026-08-13  
**Depends on:** Iceberg claims MCP V7 (catalog-only), structured claim intake, `agent_run_audit`

Atlas and Ranger attach **meaning** and **enforcement** to the same Iceberg tables. They do not replace SPARQL routing or the session RDF graph (`SESSION_DIRECTORY/claim_{id}_graph.ttl`).

Related: [`mcp-fork-charter.md`](mcp-fork-charter.md), ADR 0001 D1.

## What stays locked

- Orchestrator has no tools. Manager (or a small governance agent) calls MCP.
- Custom tools do not call MCP in-process.
- SPARQL + playbook own `next_step`. Session Turtle owns the instance graph.
- Iceberg MCP stays catalog-only (`run_named_query` / `run_named_write`).
- One Atlas MCP: data-contract fork. Do **not** also register `ecole5/atlas-mcp`.
- Do **not** fork Ranger; use upstream `ranger-mcp-server`.

## Two jobs

| | Atlas | Ranger |
|---|---|---|
| Question | What *is* this table/column in the ontology? | Who may *see or change* it, and is PII masked? |
| Object | Catalog entities (table/column GUIDs) | Policies on those same objects (and tags) |
| Agent use | Bind/read `ontology.iri` as business metadata; contracts/classifications | Explain or check access; do not let the LLM invent policies |
| Owner | Platform / MCP + data stewards | Security / Ranger admins |

Atlas does not grant access. Ranger does not define Claim vs LitigationCase.

## Sequence

### Phase 0 (done)

Named Iceberg catalog, structured intake, specialists, `car_insurance_claims.agent_run_audit`. No Atlas/Ranger required.

### Phase A — Atlas bind (governance, not runtime routing)

1. Fork/register `data-contract-mcp-server-claims` with a **small** tool surface (same lesson as V7): e.g. `ensure_business_metadata_typedef`, `bind_ontology_iri_to_entity`, `get_entity_business_metadata`.
2. Steward smoke: bind `car_insurance_claims.claim` → `https://example.org/ins/Claim` (and a few columns).
3. Manager one-shot: read BM back; Final Answer the IRI. Do not fold this into every 402 intake.
4. Optional: ODCS contract on the claims database; classification on PII columns.

**Success:** a steward (or Manager) can show “this Iceberg table *is* ontology Claim” in Atlas without label hacks.

Facade stubs already exist in `agent_studio/src/ins_claims_agent/mcp_facade/atlas_client.py`.

### Phase B — Ranger (enforcement)

1. Register upstream Ranger MCP.
2. Policies for `car_insurance_claims` (and later `agent_run_audit`): who can SELECT/INSERT; column mask on PII if present.
3. Prefer **tag-based** policies that consume Atlas classifications from Phase A so meaning is not duplicated in Ranger resource names.
4. Agent use is narrow: “what can this run’s identity do?” — never “create a policy from NL.”

**Success:** Impala MCP calls fail closed for unauthorized users; audit table writes are an explicit allow.

### Phase C — optional join-up

Intake unchanged. After route, a governance step may *record* that the run used tables bound to those IRIs (evidence JSON or Atlas note). Audit writes remain Iceberg; Atlas/Ranger do not store the claim graph.

## Out of scope for this plan

- Atlas as a triple store or SPARQL endpoint
- Putting `claim_{id}_graph.ttl` into Atlas
- Agent-authored Ranger policies
- Dual Atlas servers
- Blocking closeout / PD pastes on Atlas

## Crew / Studio

- Iceberg MCP stays on Manager + specialists (facts + audit).
- Atlas MCP: Manager only, or a Governance Agent with a tiny Goal (bind/read, then STOP). Do not add an Atlas `agent_role` to the playbook in Phase A.
- Ranger MCP: Manager or security helper; keep it off Litigation/BI.

## Risks

- **Tool sprawl** — Atlas upstream has many tools; wrap in a catalog or Goal-forbid extras.
- **Identity** — Impala MCP user vs Ranger policy subject must match Studio’s runtime identity.
- **PII in session Turtle and `payload_json`** — Ranger on Impala does not mask `/workspace` artifacts.
- **Steward vs agent** — first IRI binds are human-approved, not every claim run.

## Business value (reminder)

Shared catalog meaning of lake tables (`ontology.iri` on real assets), contracts/classifications, and (with Ranger) enforced access/masking. Not faster routing for claim 402.
