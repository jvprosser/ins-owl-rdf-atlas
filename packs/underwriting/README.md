# Underwriting (submission routing)

Same control plane as claims and retirement distributions. The playbook decides whether to decline, order an inspection, refer to a senior underwriter, issue an indicative quote, or wait for a human. The LLM does not invent appetite or price.

Studio tools stay `build_claim_graph`, `validate_claim_graph`, and `route_claim`. `claim_id` is the submission id (`SUB-9102`).

Live lake + MCP: `ddl/hive_iceberg/underwriting_iceberg.sql`, `ddl/hive_iceberg/underwriting_seed_data.sql`, and [`mcp_forks/iceberg-mcp-server-underwriting`](../../mcp_forks/iceberg-mcp-server-underwriting/README.md). Fixture JSON stays golden for `agent_studio/tests/test_underwriting_pack.py`.

| Case | Story | Route |
|---|---|---|
| **SUB-9100** | Class `4812` | `DECLINE_UNINSURABLE` / `UnderwritingIntakeSpecialist` (P0) |
| **SUB-9101** | TIV `2000001`, inspection open | `TRIGGER_SURVEY` / `RiskEngineeringSpecialist` (P1) |
| **SUB-9102** | TIV `4500000`, flood, inspection open | `TRIGGER_SURVEY` first. After inspection is on file, the same prompt hits P2 |
| **SUB-9103** | TIV `1999999`, no flood, no prior claims | `AUTO_RATE_AND_BIND` / `RatingSpecialist` (P3) |
| **SUB-9104** | Inspection done, flood plain, TIV under $2M | `REFER_TO_SENIOR_UW` / `SeniorUnderwriter` (P2) |
| **SUB-9105** | One prior claim, no flood, TIV `$500,000` | `HUMAN_UW_REVIEW` / `UnderwritingReviewAgent` |
| **SUB-9106** | TIV `25000001`, inspection open | `DECLINE_UNINSURABLE` (P0 beats P1) |
| **SUB-9107** | TIV `1800000`, inspection done, no owner | `AssignUnderwriter`. After party 14 is assigned, the same prompt binds |

Quote premium is computed in the catalog (cents per $100 of TIV): tier A `15`, B `25`, C `40`, anything else `STANDARD` at `30`. `premium_cents = total_insured_value * rate // 100`. **SUB-9103** (tier B) is `499999` cents. The agent does not pass a premium.

## Upload workflow data (Studio)

Upload the **contents** of `packs/underwriting/` so `/workflow_data/pack.yaml` exists. Do not nest an `underwriting/` folder. Do not upload `agents/`, `fixtures/`, or `catalog_fixtures.json`.

```text
/workflow_data/
  pack.yaml
  exemplars.yaml
  ontology/submissions.json
  playbook/playbook.yaml
```

Use a separate Agent Studio project from claims **402** and from distributions.

## MCP registration

Register **`iceberg-mcp-server-underwriting`** only. Identity `INS_UW_MCP_V1`. Do **not** set `PACK_ROOT`.

```json
{
  "mcpServers": {
    "iceberg-mcp-server-underwriting": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/jvprosser/ins-owl-rdf-atlas.git@main#subdirectory=mcp_forks/iceberg-mcp-server-underwriting",
        "run-server"
      ],
      "env": {
        "IMPALA_HOST": "<coordinator-host>",
        "IMPALA_PORT": "443",
        "IMPALA_USER": "<user>",
        "IMPALA_PASSWORD": "<password>",
        "IMPALA_DATABASE": "underwriting"
      }
    }
  }
}
```

Check: Delegate Intake Agent `get_server_info` → `content_id=INS_UW_MCP_V1`. Then `list_named_queries` must include `get_submission_spine` and must **not** include `get_claim_spine`.

## Studio prompt

Paste agents from `agents/`. Roles must be exactly `Intake Agent`, `Underwriting Intake Specialist`, `Risk Engineering Specialist`, `Senior Underwriter`, `Rating Specialist`, and `Underwriting Review Agent`. Decline letters need Studio `save_claim_letter` on the intake specialist only.

```text
Please evaluate submission SUB-9102.
```

Expect `TRIGGER_SURVEY`, `Risk Engineering Specialist`, `write_data_enrichment_request`.

After the inspection lands, flip the lake row and send the same sentence again:

```sql
UPDATE underwriting.property_risk_scores
SET inspection_completed = TRUE
WHERE submission_id = 'SUB-9102';
```

Expect `REFER_TO_SENIOR_UW` / `Senior Underwriter` / `write_referral_queue`. Flood is already true on the seed, so P2 wins once P1 no longer matches.

## Assignment

Party **14** (Riley Cho) is the current `UNDERWRITER` on **SUB-9100** through **SUB-9106**. **SUB-9107** has no role, so evaluation stops at `AssignUnderwriter` (no coworker; the agent does not pick a person). Insert the role, then send the same sentence again:

```sql
INSERT INTO TABLE underwriting.submission_party_role
SELECT 'SPR-9107' AS submission_party_role_id,
       'SUB-9107' AS submission_id,
       CAST(14 AS BIGINT) AS party_id,
       'UNDERWRITER' AS role_type_code,
       CAST('2026-11-04 11:00:00' AS TIMESTAMP) AS assigned_at,
       CAST(NULL AS TIMESTAMP) AS unassigned_at,
       TRUE AS is_current_assignment,
       CAST('2026-11-04 11:00:00' AS TIMESTAMP) AS created_at;
```

Expect `AUTO_RATE_AND_BIND`. A prohibited class still declines with no owner (P0 before U0).

Open queue (DECLINED and QUOTED omitted):

```text
What are my current open submissions?
```

Expect **SUB-9100** through **SUB-9106** for party 14.
