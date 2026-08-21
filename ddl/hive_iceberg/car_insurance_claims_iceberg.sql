-- =============================================================================
-- Car Insurance Claims — Cloudera Hive + Apache Iceberg DDL
-- =============================================================================
-- Engine target : Cloudera Data Platform (CDP) Hive with STORED BY ICEBERG
-- Format        : Iceberg v2, Parquet data files (default write format)
-- Database      : car_insurance_claims
--
-- PURPOSE
--   Physical schema for a personal auto Property and Casualty (P&C) claims
--   warehouse, aligned to Association for Cooperative Operations Research and
--   Development (ACORD) / Object Management Group (OMG) P&C concepts and ready
--   for mapping into a Web Ontology Language (OWL) Terminological Box (TBox)
--   and Resource Description Framework (RDF) Assertion Box (ABox).
--
-- PLANNING DECISIONS (accepted)
--   D1  Lifecycle          : wide-row claim_lifecycle + claim_lifecycle_event (high-value add)
--   D2  Reserves           : claim_reserve + claim_reserve_component (+ txn)
--   D3  Parties            : party + person/organization + party roles
--   D4  Vehicle–Policy     : policy_insurable_object (=1 active link pattern)
--   D5  Reserve history    : claim_reserve_transaction allowed; is_current flag
--   D6  Identity           : surrogate keys; business keys documented for OWL
--   D7  Post-MVT axis      : light standards alignment in properties; then dict
--   D8  Coverage           : first-class coverage + policy_coverage
--   D9  Loss vs claim      : loss_event + claim
--   D10 Money              : DECIMAL(18,2) + ISO 4217 currency_code
--   D11 Codes              : ref_code_list / ref_code (SKOS-ready)
--   D12 PII                : person holds PII; organization for vendors/firms
--
-- HIGH-VALUE EXTENSION (accepted): drivers, geo_location, police report, fault,
--   injuries, damage assessment, claim folder/documents, settlement offers,
--   subrogation, recoveries, litigation, fraud/SIU assessment, other insurance,
--   lifecycle events.
--
-- ACRONYMS (defined once for agent / Large Language Model (LLM) context)
--   ACORD  Association for Cooperative Operations Research and Development
--   ABox   Assertion Box (OWL instance data)
--   BI     Bodily Injury
--   CDP    Cloudera Data Platform
--   DDL    Data Definition Language
--   FIBO   Financial Industry Business Ontology
--   FK     Foreign Key
--   FNOL   First Notice of Loss
--   IBNR   Incurred But Not Reported (reserve concept; not modeled as table yet)
--   IRI    Internationalized Resource Identifier
--   ISO    International Organization for Standardization
--   LLM    Large Language Model
--   MVT    Minimal Viable TBox
--   OEM    Original Equipment Manufacturer
--   OMG    Object Management Group
--   OWL    Web Ontology Language
--   P&C    Property and Casualty
--   PD     Property Damage
--   PII    Personally Identifiable Information
--   PK     Primary Key
--   RDF    Resource Description Framework
--   SHACL  Shapes Constraint Language
--   SIU    Special Investigations Unit (fraud investigation function)
--   SKOS   Simple Knowledge Organization System
--   SWRL   Semantic Web Rule Language
--   TBox   Terminological Box (OWL schema: classes, properties, axioms)
--   VIN    Vehicle Identification Number
--
-- ENTITY RELATIONSHIP SPINE (logical FK graph; not Hive-enforced)
--   party 1──1 person | organization
--   party 1──* party_postal_address
--   party 1──* policy_party_role *──1 insurance_policy
--   party 1──1 driver (driver is a person party specialization)
--   geo_location (first-class) <- loss_event, police_report
--   insurance_policy 1──* policy_coverage *──1 coverage
--   insurance_policy 1──* policy_insurable_object *──1 insurable_object
--   insurance_policy 1──* policy_driver *──1 driver
--   insurable_object 1──1 vehicle
--   loss_event 1──* claim
--   loss_event 1──* loss_driver *──1 driver
--   loss_event 0──1 geo_location
--   loss_event 0──* police_report
--   insurance_policy 1──* claim
--   claim 0──1 insurable_object (vehicle)
--   claim 0──1 policy_coverage
--   claim 1──* claim_party_role *──1 party
--   claim 1──* claim_lifecycle
--   claim 1──* claim_lifecycle_event
--   claim 1──* claim_reserve 1──* claim_reserve_component
--   claim_reserve 1──* claim_reserve_transaction
--   claim 1──* claim_payment
--   claim 1──* claim_recovery
--   claim 1──* repair_engagement *──1 party (vendor organization)
--   claim 1──* claim_injury *──1 party (injured person)
--   claim 1──* damage_assessment
--   claim 1──* fault_determination
--   claim 1──* claim_offer
--   claim 1──* subrogation_case
--   claim 1──* litigation_case
--   claim 1──* fraud_assessment
--   claim 1──* other_insurance
--   claim 1──1 claim_folder 1──* claim_document
--   subrogation_case / salvage / deductible -> claim_recovery
--
-- OWL / RDF MAPPING HINTS (see TBLPROPERTIES llm.* on each table)
--   Tables map to owl:Class; columns to owl:DatatypeProperty or coded concepts;
--   FK columns map to owl:ObjectProperty. Preferred IRI pattern (D6):
--     https://example.org/ins/id/{TableCamel}/{surrogate_id}
--   Business keys (claim_number, policy_number, vin) are owl:hasKey candidates.
--
-- AGENT / LLM PROPERTY CONVENTION (custom TBLPROPERTIES)
--   llm.domain                  Business domain tag
--   llm.ontology_class          Primary OWL class name for this table
--   llm.acord_concept           Closest ACORD information-model concept
--   llm.omg_pc_entity           Closest OMG P&C entity
--   llm.fibo_alignment          FIBO alignment note (often "extend")
--   llm.primary_key             Surrogate PK column(s)
--   llm.business_key            Natural / business key column(s)
--   llm.foreign_keys            Semicolon-separated child->parent.col refs
--   llm.object_properties       Suggested RDF object property names
--   llm.pii                     true|false|mixed — Personally Identifiable Info
--   llm.sensitivity             public|internal|confidential|restricted
--   llm.grain                   What one row represents
--   llm.partitioning_rationale  Why the Iceberg partition spec was chosen
--   llm.competency_questions    Questions this table helps answer
--   llm.related_tables          Neighbor tables for join discovery
--   llm.decision_refs           Planning decision ids that shaped this table
--   llm.notes                   Extra context for retrieval-augmented agents
--
-- NOTES
--   * Hive/Iceberg does not enforce PK/FK; relationships are documented for
--     humans, LLMs, and SHACL/OWL layers.
--   * Prefer CREATE EXTERNAL TABLE for Iceberg on Cloudera Hive.
--   * Adjust LOCATION via database managed location or cluster defaults.
-- =============================================================================

CREATE DATABASE IF NOT EXISTS car_insurance_claims
COMMENT 'Personal auto P&C insurance warehouse: parties, policies, coverages, vehicles, loss events, claims, reserves, payments, repairs, plus high-value FNOL/claims entities (drivers, geo_location, police reports, fault, injuries, assessments, documents, offers, subrogation, recoveries, litigation, fraud/SIU, other insurance, lifecycle events). Iceberg analytics and OWL/RDF semantic mapping (ACORD/OMG/FIBO-aligned).';

USE car_insurance_claims;


-- =============================================================================
-- REFERENCE / CODE LISTS (SKOS-ready controlled vocabularies)
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.ref_code_list (
  code_list_id        STRING  COMMENT 'PK. Stable list identifier, e.g. CLAIM_STATUS, COVERAGE_TYPE, PARTY_ROLE_TYPE. Maps to skos:ConceptScheme.',
  code_list_name      STRING  COMMENT 'Human-readable name of the code list for UI and agent display.',
  description         STRING  COMMENT 'Long-form definition of the vocabulary purpose and ownership.',
  owning_steward      STRING  COMMENT 'Data steward team (e.g. Claims, Actuarial, Underwriting).',
  is_acord_aligned    BOOLEAN COMMENT 'True when values are intended to align with ACORD codelist semantics.',
  created_at          TIMESTAMP COMMENT 'Row creation timestamp (UTC recommended).'
)
COMMENT 'SKOS-ready registry of controlled vocabularies (code lists) used across the car insurance claims domain. Each list groups allowable code_value rows in ref_code. Agents should resolve free-text status fields to these lists before reasoning.'
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'CodeList',
  'llm.acord_concept' = 'Codelist',
  'llm.omg_pc_entity' = 'Code / Domain',
  'llm.fibo_alignment' = 'extend: controlled vocabulary; align codes via SKOS',
  'llm.primary_key' = 'code_list_id',
  'llm.business_key' = 'code_list_id',
  'llm.foreign_keys' = '',
  'llm.object_properties' = 'hasCode',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'internal',
  'llm.grain' = 'one controlled vocabulary / concept scheme',
  'llm.partitioning_rationale' = 'unpartitioned; small reference dimension',
  'llm.competency_questions' = 'Which code lists exist? Which steward owns CLAIM_STATUS?',
  'llm.related_tables' = 'ref_code',
  'llm.decision_refs' = 'D11',
  'llm.notes' = 'Seed lists: PARTY_TYPE, PARTY_ROLE_TYPE, POLICY_STATUS, POLICY_TYPE, COVERAGE_TYPE, CLAIM_STATUS, LOSS_CAUSE, RESERVE_TYPE, PAYMENT_CATEGORY, PAYMENT_STATUS, PAYEE_TYPE, PRIMARY_USE, GENDER, MARITAL_STATUS, ADDRESS_TYPE, ORGANIZATION_TYPE, LIMIT_BASIS, ESTIMATE_STATUS, RESERVE_STATUS, DRIVER_RELATIONSHIP, LICENSE_STATUS, INJURY_SEVERITY, BODY_REGION, ASSESSMENT_TYPE, OFFER_STATUS, SUBROGATION_STATUS, RECOVERY_TYPE, LITIGATION_STATUS, FRAUD_ASSESSMENT_OUTCOME, DOCUMENT_TYPE, FAULT_BASIS, LIFECYCLE_EVENT_TYPE, LOCATION_TYPE, OTHER_INSURANCE_TYPE.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.ref_code (
  code_list_id        STRING  COMMENT 'FK -> ref_code_list.code_list_id. Concept scheme membership.',
  code_value          STRING  COMMENT 'PK part. Machine code, e.g. OPEN, COLLISION, ADJUSTER. Maps to skos:Concept notation.',
  code_label          STRING  COMMENT 'Display label (skos:prefLabel).',
  description         STRING  COMMENT 'Definition (skos:definition). Critical for LLM disambiguation.',
  is_active           BOOLEAN COMMENT 'Soft-deprecate codes without breaking historical facts.',
  sort_order          INT     COMMENT 'Optional UI / report ordering.',
  parent_code_value   STRING  COMMENT 'Optional hierarchy within the same list (skos:broader).',
  external_acord_code STRING  COMMENT 'Optional ACORD codelist value for interoperability.',
  created_at          TIMESTAMP COMMENT 'Row creation timestamp (UTC recommended).'
)
COMMENT 'Allowable coded values for a ref_code_list. Use these codes in transactional tables (*_code columns) instead of free text so OWL enumerations and SHACL in-value constraints stay stable.'
PARTITIONED BY SPEC (
  code_list_id
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'CodeValue',
  'llm.acord_concept' = 'Codelist value',
  'llm.omg_pc_entity' = 'Code',
  'llm.fibo_alignment' = 'extend: SKOS concept; optional exactMatch to ACORD',
  'llm.primary_key' = 'code_list_id+code_value',
  'llm.business_key' = 'code_list_id+code_value',
  'llm.foreign_keys' = 'code_list_id->ref_code_list.code_list_id',
  'llm.object_properties' = 'inCodeList;broaderCode',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'internal',
  'llm.grain' = 'one code value within a list',
  'llm.partitioning_rationale' = 'identity partition on code_list_id for list-scoped scans',
  'llm.competency_questions' = 'What does claim_status_code=REOPENED mean? Valid payee_type_code values?',
  'llm.related_tables' = 'ref_code_list',
  'llm.decision_refs' = 'D11',
  'llm.notes' = 'Composite PK is logical only. Prefer joining on (code_list_id, code_value).'
);


-- =============================================================================
-- PARTY MODEL (ACORD / OMG Party + Person / Organization)
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.party (
  party_id            BIGINT  COMMENT 'PK. Surrogate party identifier. OWL IRI local name candidate.',
  party_type_code     STRING  COMMENT 'FK-code -> ref_code(PARTY_TYPE): PERSON | ORGANIZATION. Discriminator for person vs organization subtype tables.',
  created_at          TIMESTAMP COMMENT 'Party record creation timestamp.',
  source_system       STRING  COMMENT 'System of record that minted party_id (lineage for agents).'
)
COMMENT 'Canonical Party hub (ACORD/OMG). Every person or organization that can play roles on policies or claims has exactly one party_id. Do not store PII here; see person and party_postal_address.'
PARTITIONED BY SPEC (
  party_type_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'Party',
  'llm.acord_concept' = 'Party',
  'llm.omg_pc_entity' = 'Party',
  'llm.fibo_alignment' = 'subClassOf FIBO independent party / legal person patterns where applicable',
  'llm.primary_key' = 'party_id',
  'llm.business_key' = '',
  'llm.foreign_keys' = '',
  'llm.object_properties' = 'hasPersonDetail;hasOrganizationDetail;hasPostalAddress;playsPolicyRole;playsClaimRole',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'internal',
  'llm.grain' = 'one party (person or organization)',
  'llm.partitioning_rationale' = 'identity partition on party_type_code for subtype-oriented scans',
  'llm.competency_questions' = 'Is party X a person or organization? What roles does party X play?',
  'llm.related_tables' = 'person;organization;party_postal_address;policy_party_role;claim_party_role;repair_engagement',
  'llm.decision_refs' = 'D3,D12',
  'llm.notes' = 'Subtype exclusivity: PERSON rows must exist in person; ORGANIZATION rows in organization.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.person (
  party_id                 BIGINT  COMMENT 'PK/FK -> party.party_id where party_type_code=PERSON.',
  first_name               STRING  COMMENT 'PII. Given name.',
  last_name                STRING  COMMENT 'PII. Family name.',
  birth_date               DATE    COMMENT 'PII. Date of birth (canonical name; was date_of_birth).',
  gender_code              STRING  COMMENT 'Code -> ref_code(GENDER).',
  marital_status_code      STRING  COMMENT 'Code -> ref_code(MARITAL_STATUS).',
  email_address            STRING  COMMENT 'PII. Primary email (was email).',
  phone_number             STRING  COMMENT 'PII. Primary phone in E.164 when possible.',
  customer_tenure_years    INT     COMMENT 'Years as customer; underwriting/risk feature.',
  prior_claims_count       INT     COMMENT 'Count of prior claims known at underwriting/servicing time.',
  prior_fraud_indicator    BOOLEAN COMMENT 'Prior fraud history indicator (was prior_fraud_flag).',
  created_at               TIMESTAMP COMMENT 'Person detail creation timestamp.'
)
COMMENT 'Person subtype of Party. Holds demographic and contact PII for individual policyholders, claimants, adjusters (if persons), attorneys, etc. Migrated from legacy policyholders table plus other person roles.'
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'Person',
  'llm.acord_concept' = 'Person',
  'llm.omg_pc_entity' = 'Person',
  'llm.fibo_alignment' = 'subClassOf FIBO Person / human being concepts',
  'llm.primary_key' = 'party_id',
  'llm.business_key' = '',
  'llm.foreign_keys' = 'party_id->party.party_id',
  'llm.object_properties' = 'detailOfParty',
  'llm.pii' = 'true',
  'llm.sensitivity' = 'restricted',
  'llm.grain' = 'one natural person party',
  'llm.partitioning_rationale' = 'unpartitioned or cluster-default; PII table — restrict access',
  'llm.competency_questions' = 'Who is the person behind party_id? Prior fraud or claims history?',
  'llm.related_tables' = 'party;party_postal_address;policy_party_role;claim_party_role',
  'llm.decision_refs' = 'D3,D12',
  'llm.notes' = 'Legacy policyholders maps here when party plays POLICYHOLDER role. Mask PII in LLM prompts unless authorized.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.organization (
  party_id                 BIGINT  COMMENT 'PK/FK -> party.party_id where party_type_code=ORGANIZATION.',
  legal_name               STRING  COMMENT 'Registered legal name (e.g. body shop corporation).',
  trade_name               STRING  COMMENT 'Doing-business-as / brand name shown on estimates.',
  organization_type_code   STRING  COMMENT 'Code -> ref_code(ORGANIZATION_TYPE): REPAIR_VENDOR | LAW_FIRM | INSURER | LIENHOLDER | OTHER.',
  tax_identifier           STRING  COMMENT 'Sensitive. Tax id when required for payments; protect like PII.',
  created_at               TIMESTAMP COMMENT 'Organization detail creation timestamp.'
)
COMMENT 'Organization subtype of Party for repair vendors, law firms, lienholders, carriers, etc. Replaces denormalized body_shop_name / vendor_id strings on repair tables.'
PARTITIONED BY SPEC (
  organization_type_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'Organization',
  'llm.acord_concept' = 'Organization',
  'llm.omg_pc_entity' = 'Organization',
  'llm.fibo_alignment' = 'subClassOf FIBO FormalOrganization / LegalEntity patterns',
  'llm.primary_key' = 'party_id',
  'llm.business_key' = 'legal_name',
  'llm.foreign_keys' = 'party_id->party.party_id',
  'llm.object_properties' = 'detailOfParty;performsRepair',
  'llm.pii' = 'mixed',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one organization party',
  'llm.partitioning_rationale' = 'identity partition on organization_type_code for vendor vs law-firm scans',
  'llm.competency_questions' = 'Which repair vendors exist? Legal name for vendor_party_id on a repair?',
  'llm.related_tables' = 'party;repair_engagement;claim_payment;claim_party_role',
  'llm.decision_refs' = 'D3,D12',
  'llm.notes' = 'tax_identifier is sensitive even though not always classified as consumer PII.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.party_postal_address (
  address_id                        BIGINT  COMMENT 'PK. Surrogate address identifier.',
  party_id                          BIGINT  COMMENT 'FK -> party.party_id. Address owner.',
  address_type_code                 STRING  COMMENT 'Code -> ref_code(ADDRESS_TYPE): MAILING | GARAGING | BILLING | PHYSICAL.',
  street_line_1                     STRING  COMMENT 'PII. Address line 1 (was street_address).',
  street_line_2                     STRING  COMMENT 'PII. Address line 2 optional.',
  city_name                         STRING  COMMENT 'PII. City / locality.',
  country_subdivision_code          STRING  COMMENT 'State/province code (was state). Prefer ISO 3166-2 subdivision where applicable.',
  postal_code                       STRING  COMMENT 'PII. Postal/ZIP code (was zip_code).',
  country_code                      STRING  COMMENT 'ISO 3166-1 alpha-2 country code.',
  valid_from_date                   DATE    COMMENT 'Address effective from (inclusive).',
  valid_to_date                     DATE    COMMENT 'Address effective to (inclusive); NULL = current.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Postal addresses for parties with type and validity window. Supports mailing vs garaging distinctions common in auto underwriting and claims.'
PARTITIONED BY SPEC (
  country_subdivision_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'PostalAddress',
  'llm.acord_concept' = 'Address',
  'llm.omg_pc_entity' = 'Geographic Location / Address',
  'llm.fibo_alignment' = 'align to FIBO address / contact constructs',
  'llm.primary_key' = 'address_id',
  'llm.business_key' = '',
  'llm.foreign_keys' = 'party_id->party.party_id',
  'llm.object_properties' = 'addressForParty',
  'llm.pii' = 'true',
  'llm.sensitivity' = 'restricted',
  'llm.grain' = 'one address version for a party',
  'llm.partitioning_rationale' = 'identity partition on country_subdivision_code for regional analytics (legacy policyholders.state)',
  'llm.competency_questions' = 'What is the mailing address for a policyholder? Garaging state for a vehicle owner?',
  'llm.related_tables' = 'party;person;policy_insurable_object',
  'llm.decision_refs' = 'D3,D12',
  'llm.notes' = 'Legacy policyholders address columns land here with address_type_code=MAILING.'
);


-- =============================================================================
-- POLICY AND COVERAGE
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.insurance_policy (
  policy_id                 BIGINT  COMMENT 'PK. Surrogate policy identifier.',
  policy_number             STRING  COMMENT 'Business key. Human-facing policy number. owl:hasKey candidate.',
  issuing_insurer_party_id  BIGINT  COMMENT 'FK -> party/organization. Issuing carrier when multi-carrier warehouse.',
  policy_type_code          STRING  COMMENT 'Code -> ref_code(POLICY_TYPE): PERSONAL_AUTO | ...',
  policy_status_code        STRING  COMMENT 'Code -> ref_code(POLICY_STATUS): ACTIVE | LAPSED | CANCELLED | EXPIRED | PENDING.',
  effective_date            DATE    COMMENT 'Policy term start (inclusive).',
  expiration_date           DATE    COMMENT 'Policy term end (inclusive/exclusive per carrier rule — document in ETL).',
  cancellation_date         DATE    COMMENT 'Mid-term cancellation date if applicable.',
  annual_premium_amount     DECIMAL(18,2) COMMENT 'Annualized premium amount.',
  premium_currency_code     STRING  COMMENT 'ISO 4217 currency code for premium (e.g. USD). CHAR(3) semantic; stored as STRING for Hive portability.',
  created_at                TIMESTAMP COMMENT 'Policy record creation timestamp.'
)
COMMENT 'Insurance policy contract header (ACORD Policy / OMG Agreement subtype / FIBO Insurance Policy extension point). Coverage limits and deductibles live in policy_coverage, not as single booleans on this row.'
PARTITIONED BY SPEC (
  policy_status_code,
  YEAR(effective_date)
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'AutoInsurancePolicy',
  'llm.acord_concept' = 'Policy',
  'llm.omg_pc_entity' = 'Agreement / Policy',
  'llm.fibo_alignment' = 'subClassOf FIBO InsurancePolicy (extend for PersonalAuto)',
  'llm.primary_key' = 'policy_id',
  'llm.business_key' = 'policy_number',
  'llm.foreign_keys' = 'issuing_insurer_party_id->party.party_id',
  'llm.object_properties' = 'hasPolicyholder;hasPolicyPartyRole;hasPolicyCoverage;coversInsurableObject;hasClaim;issuedBy',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one insurance policy contract header',
  'llm.partitioning_rationale' = 'status + year(effective_date) for term and in-force analytics (legacy policies partitioning)',
  'llm.competency_questions' = 'Is policy P in force on loss date? What is annual premium? Who is primary policyholder?',
  'llm.related_tables' = 'policy_party_role;policy_coverage;policy_insurable_object;claim',
  'llm.decision_refs' = 'D4,D8,D10',
  'llm.notes' = 'Legacy policies.deductible_amount and coverage_limit and collision/comprehensive flags migrate to policy_coverage rows.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.policy_party_role (
  policy_party_role_id  BIGINT  COMMENT 'PK. Surrogate for a party playing a role on a policy.',
  policy_id             BIGINT  COMMENT 'FK -> insurance_policy.policy_id.',
  party_id              BIGINT  COMMENT 'FK -> party.party_id.',
  role_type_code        STRING  COMMENT 'Code -> ref_code(PARTY_ROLE_TYPE): POLICYHOLDER | NAMED_INSURED | LIENHOLDER | AGENT | UNDERWRITER.',
  effective_date        DATE    COMMENT 'Role effective from.',
  expiration_date       DATE    COMMENT 'Role effective to; NULL = current.',
  is_primary_role       BOOLEAN COMMENT 'True for primary policyholder / primary named insured.',
  created_at            TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'ACORD/OMG Party Role on a Policy. Replaces a single policyholder_id FK on the policy header and supports lienholders and named insureds.'
PARTITIONED BY SPEC (
  role_type_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'PolicyPartyRole',
  'llm.acord_concept' = 'Party Role (Policy)',
  'llm.omg_pc_entity' = 'Party Role',
  'llm.fibo_alignment' = 'extend: role/relator pattern between party and contract',
  'llm.primary_key' = 'policy_party_role_id',
  'llm.business_key' = 'policy_id+party_id+role_type_code+effective_date',
  'llm.foreign_keys' = 'policy_id->insurance_policy.policy_id;party_id->party.party_id',
  'llm.object_properties' = 'roleOnPolicy;rolePlayedByParty;hasPolicyholder(shortcut)',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one party-role assignment on a policy for a time range',
  'llm.partitioning_rationale' = 'identity partition on role_type_code (policyholder vs lienholder scans)',
  'llm.competency_questions' = 'Who is the primary policyholder on policy P? Which parties are named insureds?',
  'llm.related_tables' = 'insurance_policy;party;person',
  'llm.decision_refs' = 'D3',
  'llm.notes' = 'OWL shortcut property hasPolicyholder can be a property chain: policy -> PolicyPartyRole(POLICYHOLDER) -> party.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.coverage (
  coverage_id           BIGINT  COMMENT 'PK. Surrogate coverage product identifier.',
  coverage_type_code    STRING  COMMENT 'Code -> ref_code(COVERAGE_TYPE): COLLISION | COMPREHENSIVE | BI_LIABILITY | PD_LIABILITY | RENTAL | MED_PAY | UMBI | UMPD | ...',
  coverage_name         STRING  COMMENT 'Display name for the coverage product.',
  description           STRING  COMMENT 'Business definition of what the coverage indemnifies.',
  is_active             BOOLEAN COMMENT 'Whether coverage may be newly bound.'
)
COMMENT 'Catalog of coverage types (ACORD coverage / OMG Coverage). Instantiated on policies via policy_coverage. Replaces has_collision_coverage / has_comprehensive_coverage booleans.'
PARTITIONED BY SPEC (
  coverage_type_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'Coverage',
  'llm.acord_concept' = 'Coverage',
  'llm.omg_pc_entity' = 'Coverage',
  'llm.fibo_alignment' = 'extend: FIBO hasCoverageArea / insurance product features',
  'llm.primary_key' = 'coverage_id',
  'llm.business_key' = 'coverage_type_code',
  'llm.foreign_keys' = '',
  'llm.object_properties' = 'instantiatedAsPolicyCoverage',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'internal',
  'llm.grain' = 'one coverage type in the product catalog',
  'llm.partitioning_rationale' = 'identity partition on coverage_type_code',
  'llm.competency_questions' = 'What coverages exist? Difference between COLLISION and COMPREHENSIVE?',
  'llm.related_tables' = 'policy_coverage;claim',
  'llm.decision_refs' = 'D8',
  'llm.notes' = 'Keep catalog small and code-driven; prefer ref_code labels for LLM glossaries.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.policy_coverage (
  policy_coverage_id      BIGINT  COMMENT 'PK. Surrogate for coverage bound on a policy (OMG Policy Coverage Detail).',
  policy_id               BIGINT  COMMENT 'FK -> insurance_policy.policy_id.',
  coverage_id             BIGINT  COMMENT 'FK -> coverage.coverage_id.',
  deductible_amount       DECIMAL(18,2) COMMENT 'Deductible for this coverage.',
  coverage_limit_amount   DECIMAL(18,2) COMMENT 'Limit amount for this coverage.',
  limit_basis_code        STRING  COMMENT 'Code -> ref_code(LIMIT_BASIS): PER_OCCURRENCE | PER_PERSON | COMBINED_SINGLE_LIMIT | AGGREGATE.',
  currency_code           STRING  COMMENT 'ISO 4217 currency for deductible and limit amounts.',
  effective_date          DATE    COMMENT 'Coverage endorsement effective from.',
  expiration_date         DATE    COMMENT 'Coverage endorsement effective to; NULL = through policy term.',
  is_active               BOOLEAN COMMENT 'Whether this binding is currently active.',
  created_at              TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'OMG Policy Coverage Detail: link among Policy, Coverage, and (via claim.policy_coverage_id) Claim. Stores per-coverage deductible and limit instead of policy-level single limit/deductible.'
PARTITIONED BY SPEC (
  is_active
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'PolicyCoverage',
  'llm.acord_concept' = 'Policy Coverage',
  'llm.omg_pc_entity' = 'Policy Coverage Detail',
  'llm.fibo_alignment' = 'extend: coverage detail under InsurancePolicy',
  'llm.primary_key' = 'policy_coverage_id',
  'llm.business_key' = 'policy_id+coverage_id+effective_date',
  'llm.foreign_keys' = 'policy_id->insurance_policy.policy_id;coverage_id->coverage.coverage_id',
  'llm.object_properties' = 'coverageOnPolicy;ofCoverageType;claimedUnder',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one coverage binding on a policy for a time range',
  'llm.partitioning_rationale' = 'identity partition on is_active for in-force coverage scans',
  'llm.competency_questions' = 'Does policy P have COLLISION? What is the BI limit? Deductible for comprehensive?',
  'llm.related_tables' = 'insurance_policy;coverage;claim;claim_payment',
  'llm.decision_refs' = 'D8,D10',
  'llm.notes' = 'SHACL later: claim.date_of_loss within policy and policy_coverage effective windows.'
);


-- =============================================================================
-- INSURABLE OBJECT / VEHICLE
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.insurable_object (
  insurable_object_id         BIGINT  COMMENT 'PK. Surrogate for any insurable object (vehicle, etc.).',
  insurable_object_type_code  STRING  COMMENT 'Code -> ref_code(INSURABLE_OBJECT_TYPE): VEHICLE | ... OMG Insurable Object discriminator.',
  created_at                  TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'OMG Insurable Object hub. Vehicles and future object types (e.g. equipment) specialize this identifier. Claims and policy links should prefer insurable_object_id for polymorphism.'
PARTITIONED BY SPEC (
  insurable_object_type_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'InsurableObject',
  'llm.acord_concept' = 'Risk / Insured Object',
  'llm.omg_pc_entity' = 'Insurable Object',
  'llm.fibo_alignment' = 'extend: asset/collateral-like insured thing',
  'llm.primary_key' = 'insurable_object_id',
  'llm.business_key' = '',
  'llm.foreign_keys' = '',
  'llm.object_properties' = 'hasVehicleDetail;coveredUnderPolicy;involvedInClaim',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'internal',
  'llm.grain' = 'one insurable object identity',
  'llm.partitioning_rationale' = 'identity partition on type for polymorphic scans',
  'llm.competency_questions' = 'What type of object is insured under id X?',
  'llm.related_tables' = 'vehicle;policy_insurable_object;claim',
  'llm.decision_refs' = 'D4',
  'llm.notes' = 'For this auto domain, most rows are VEHICLE with a matching vehicle subtype row.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.vehicle (
  insurable_object_id                     BIGINT  COMMENT 'PK/FK -> insurable_object.insurable_object_id where type=VEHICLE. Legacy vehicle_id maps here.',
  vin                                     STRING  COMMENT 'Vehicle Identification Number. owl:hasKey / inverse-functional candidate.',
  make_name                               STRING  COMMENT 'Manufacturer make (was make).',
  model_name                              STRING  COMMENT 'Model name (was model).',
  model_year                              INT     COMMENT 'Model year (was year).',
  trim_name                               STRING  COMMENT 'Trim level (was trim).',
  license_plate_number                    STRING  COMMENT 'Plate number (was license_plate). Semi-sensitive.',
  registration_country_subdivision_code   STRING  COMMENT 'Registration state/province (was registration_state).',
  primary_use_code                        STRING  COMMENT 'Code -> ref_code(PRIMARY_USE): COMMUTE | PLEASURE | BUSINESS | FARM.',
  annual_mileage_amount                   INT     COMMENT 'Stated annual mileage (was annual_mileage).',
  telematics_installed_indicator          BOOLEAN COMMENT 'Telematics device installed (was has_telematics_installed).',
  estimated_market_value_amount           DECIMAL(18,2) COMMENT 'Estimated market value (was INT estimated_market_value).',
  market_value_currency_code              STRING  COMMENT 'ISO 4217 currency for market value.',
  created_at                              TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Vehicle specialization of Insurable Object (OMG Vehicle). Asset inventory for covered automobiles including VIN, specs, telematics, and usage.'
PARTITIONED BY SPEC (
  make_name,
  model_year
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'Vehicle',
  'llm.acord_concept' = 'Vehicle',
  'llm.omg_pc_entity' = 'Vehicle',
  'llm.fibo_alignment' = 'extend: tangible asset / vehicle under insurance',
  'llm.primary_key' = 'insurable_object_id',
  'llm.business_key' = 'vin',
  'llm.foreign_keys' = 'insurable_object_id->insurable_object.insurable_object_id',
  'llm.object_properties' = 'detailOfInsurableObject;coveredByPolicy;involvedInClaim',
  'llm.pii' = 'mixed',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one vehicle asset',
  'llm.partitioning_rationale' = 'make_name + model_year for actuarial/vehicle-risk analytics (legacy vehicles partitioning)',
  'llm.competency_questions' = 'Which vehicle VIN is on claim C? Market value and telematics for vehicle V?',
  'llm.related_tables' = 'insurable_object;policy_insurable_object;claim;repair_engagement',
  'llm.decision_refs' = 'D4,D6,D10',
  'llm.notes' = 'Legacy vehicles.policy_id removed; use policy_insurable_object for policy links and history.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.policy_insurable_object (
  policy_insurable_object_id  BIGINT  COMMENT 'PK. Surrogate for policy–object coverage link.',
  policy_id                   BIGINT  COMMENT 'FK -> insurance_policy.policy_id.',
  insurable_object_id         BIGINT  COMMENT 'FK -> insurable_object.insurable_object_id (vehicle).',
  effective_date              DATE    COMMENT 'Object added to policy effective from. Supports endorsements (D4).',
  expiration_date             DATE    COMMENT 'Removed/replaced effective to; NULL = current.',
  garaging_address_id         BIGINT  COMMENT 'Optional FK -> party_postal_address.address_id for garaging location.',
  is_primary_vehicle          BOOLEAN COMMENT 'Primary vehicle on the policy when multiple.',
  created_at                  TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Associative entity linking policies to insured vehicles/objects with effective dating. Enforces the industry pattern that coverage of an object under a policy can change over time without rewriting vehicle rows.'
PARTITIONED BY SPEC (
  YEAR(effective_date)
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'PolicyInsurableObject',
  'llm.acord_concept' = 'Policy risk / insured item link',
  'llm.omg_pc_entity' = 'Insurable Object is covered as defined in Policy Coverage Detail (related)',
  'llm.fibo_alignment' = 'extend: contract covers asset relationship',
  'llm.primary_key' = 'policy_insurable_object_id',
  'llm.business_key' = 'policy_id+insurable_object_id+effective_date',
  'llm.foreign_keys' = 'policy_id->insurance_policy.policy_id;insurable_object_id->insurable_object.insurable_object_id;garaging_address_id->party_postal_address.address_id',
  'llm.object_properties' = 'coversInsurableObject;coveredByPolicy',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one policy–object association for a time range',
  'llm.partitioning_rationale' = 'year(effective_date) for endorsement-era pruning',
  'llm.competency_questions' = 'Which vehicles were on policy P on date D? Which policy covers VIN V on loss date?',
  'llm.related_tables' = 'insurance_policy;insurable_object;vehicle;claim',
  'llm.decision_refs' = 'D4',
  'llm.notes' = 'SHACL triangle: claim.policy_id and claim.insurable_object_id should match an active policy_insurable_object row on loss_date.'
);


-- =============================================================================
-- LOSS EVENT AND CLAIM (FNOL)
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.loss_event (
  loss_event_id               BIGINT  COMMENT 'PK. Surrogate loss occurrence identifier.',
  loss_datetime               TIMESTAMP COMMENT 'Best-known date/time of loss (may be date-only in source with 00:00).',
  loss_date                   DATE    COMMENT 'Loss calendar date; preferred partition/analytics field.',
  loss_cause_code             STRING  COMMENT 'Code -> ref_code(LOSS_CAUSE): COLLISION | THEFT | WEATHER | VANDALISM | GLASS | OTHER.',
  location_id                 BIGINT  COMMENT 'FK -> geo_location.location_id. First-class loss scene (prefer over fragmented postal fields).',
  loss_location_postal_code   STRING  COMMENT 'Optional postal/region code where loss occurred (legacy/denormalized).',
  loss_location_country_subdivision_code STRING COMMENT 'State/province of loss location (denormalized convenience).',
  loss_description            STRING  COMMENT 'Free-text FNOL narrative; useful for NLP agents; may contain PII.',
  created_at                  TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Real-world loss occurrence (peril event). Separated from claim (D9) so one loss can relate to multiple claims/coverages over time. Claim.fnol_report_datetime remains the notice timestamp.'
PARTITIONED BY SPEC (
  YEAR(loss_date),
  loss_cause_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'LossEvent',
  'llm.acord_concept' = 'Loss / Accident',
  'llm.omg_pc_entity' = 'Loss occurrence (related to Claim)',
  'llm.fibo_alignment' = 'extend: event/occurrence underpinning Claim',
  'llm.primary_key' = 'loss_event_id',
  'llm.business_key' = '',
  'llm.foreign_keys' = 'location_id->geo_location.location_id',
  'llm.object_properties' = 'givesRiseToClaim;occurredAtLocation;hasPoliceReport;hasLossDriver',
  'llm.pii' = 'mixed',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one loss occurrence',
  'llm.partitioning_rationale' = 'year(loss_date)+loss_cause_code for actuarial accident-year and cause analytics',
  'llm.competency_questions' = 'What caused the loss? How many claims stem from loss_event L? Where did it occur?',
  'llm.related_tables' = 'claim;geo_location;police_report;loss_driver;fault_determination;other_insurance',
  'llm.decision_refs' = 'D9,high_value_location',
  'llm.notes' = 'Legacy claims.date_of_loss migrates to loss_date/loss_datetime.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.claim (
  claim_id                    BIGINT  COMMENT 'PK. Surrogate claim identifier.',
  claim_number                STRING  COMMENT 'Business key. FNOL/case number. owl:hasKey candidate.',
  loss_event_id               BIGINT  COMMENT 'FK -> loss_event.loss_event_id. Occurrence underlying this claim.',
  policy_id                   BIGINT  COMMENT 'FK -> insurance_policy.policy_id. Policy against which claim is filed.',
  insurable_object_id         BIGINT  COMMENT 'FK -> insurable_object.insurable_object_id. Usually the damaged/involved vehicle.',
  policy_coverage_id          BIGINT  COMMENT 'FK -> policy_coverage.policy_coverage_id. Coverage path for the claim when known.',
  fnol_report_datetime        TIMESTAMP COMMENT 'First Notice of Loss report timestamp (expanded from report_date).',
  claim_status_code           STRING  COMMENT 'Code -> ref_code(CLAIM_STATUS): OPEN | CLOSED | REOPENED | DENIED | IN_LITIGATION.',
  fraudulent_claim_indicator  BOOLEAN COMMENT 'Fraud indicator (was is_fraudulent_flag). Prefer workflow classes in OWL for suspected vs confirmed.',
  litigation_indicator        BOOLEAN COMMENT 'True when claim is in litigation (broader than attorney_retained_flag).',
  subrogation_indicator       BOOLEAN COMMENT 'True when subrogation/recovery is pursued (was subrogation_flag).',
  total_loss_indicator        BOOLEAN COMMENT 'True when vehicle is total loss.',
  created_at                  TIMESTAMP COMMENT 'Claim case creation timestamp.'
)
COMMENT 'Master claim / FNOL case (ACORD Claim / OMG Claim). Tracks status and risk indicators (fraud, litigation, subrogation, total loss). Financials, lifecycle, payments, and repairs are child tables. Attorney retention also represented via claim_party_role ATTORNEY.'
PARTITIONED BY SPEC (
  YEAR(fnol_report_datetime),
  claim_status_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'AutoClaim',
  'llm.acord_concept' = 'Claim',
  'llm.omg_pc_entity' = 'Claim',
  'llm.fibo_alignment' = 'subClassOf / extend FIBO Claim',
  'llm.primary_key' = 'claim_id',
  'llm.business_key' = 'claim_number',
  'llm.foreign_keys' = 'loss_event_id->loss_event.loss_event_id;policy_id->insurance_policy.policy_id;insurable_object_id->insurable_object.insurable_object_id;policy_coverage_id->policy_coverage.policy_coverage_id',
  'llm.object_properties' = 'arisesFromPolicy;involvesVehicle;underPolicyCoverage;fromLossEvent;hasLifecycle;hasReserve;hasPayout;hasRepairEngagement;hasClaimPartyRole',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one claim case / FNOL file',
  'llm.partitioning_rationale' = 'year(fnol_report_datetime)+claim_status_code for operational queues and accident-year style pruning (legacy used YEAR(date_of_loss); loss_date remains on loss_event)',
  'llm.competency_questions' = 'Which policy and vehicle are on claim C? Is C in subrogation or litigation? Fraud flag?',
  'llm.related_tables' = 'loss_event;insurance_policy;vehicle;policy_coverage;claim_party_role;claim_lifecycle;claim_reserve;claim_payment;repair_engagement',
  'llm.decision_refs' = 'D6,D9',
  'llm.notes' = 'OWL MVT: AutoClaim exactly 1 arisesFromPolicy and exactly 1 involvesVehicle (when insurable_object_id present). Triangle consistency via SHACL against policy_insurable_object.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.claim_party_role (
  claim_party_role_id     BIGINT  COMMENT 'PK. Surrogate for a party playing a role on a claim.',
  claim_id                BIGINT  COMMENT 'FK -> claim.claim_id.',
  party_id                BIGINT  COMMENT 'FK -> party.party_id.',
  role_type_code          STRING  COMMENT 'Code -> ref_code(PARTY_ROLE_TYPE): CLAIMANT | INSURED | ADJUSTER | ATTORNEY | ADVERSE_PARTY | WITNESS | MEDICAL_PROVIDER.',
  assigned_at             TIMESTAMP COMMENT 'When the role assignment started (critical for adjuster cycle time).',
  unassigned_at           TIMESTAMP COMMENT 'When the role assignment ended; NULL if current.',
  is_current_assignment   BOOLEAN COMMENT 'True for the active assignment of this role type (e.g. current adjuster).',
  created_at              TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'ACORD/OMG Party Role on a Claim. Replaces assigned_adjuster_id string and attorney_retained_flag-only modeling. Supports adjuster history, attorneys, claimants, and adverse parties.'
PARTITIONED BY SPEC (
  role_type_code,
  is_current_assignment
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimPartyRole',
  'llm.acord_concept' = 'Party Role (Claim)',
  'llm.omg_pc_entity' = 'Party Role',
  'llm.fibo_alignment' = 'extend: party role / relator on Claim',
  'llm.primary_key' = 'claim_party_role_id',
  'llm.business_key' = 'claim_id+party_id+role_type_code+assigned_at',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;party_id->party.party_id',
  'llm.object_properties' = 'roleOnClaim;rolePlayedByParty;assignedToAdjuster(shortcut)',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one party-role assignment on a claim for a time range',
  'llm.partitioning_rationale' = 'role_type_code + current flag for adjuster workload and attorney involvement scans',
  'llm.competency_questions' = 'Who is the current adjuster on claim C? Is an attorney retained? Who is the claimant?',
  'llm.related_tables' = 'claim;party;person;organization;claim_lifecycle',
  'llm.decision_refs' = 'D3',
  'llm.notes' = 'D1 keeps claim_lifecycle.current_adjuster_party_id as optional denormalized convenience for marts; this table is authoritative for role history.'
);


-- =============================================================================
-- OPERATIONAL LIFECYCLE (D1 wide-row)
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.claim_lifecycle (
  claim_lifecycle_id          BIGINT  COMMENT 'PK. Surrogate lifecycle record id (was milestone_id).',
  claim_id                    BIGINT  COMMENT 'FK -> claim.claim_id.',
  intake_datetime             TIMESTAMP COMMENT 'Intake phase timestamp (was intake_timestamp).',
  triage_datetime             TIMESTAMP COMMENT 'Triage phase timestamp.',
  inspection_datetime         TIMESTAMP COMMENT 'Inspection phase timestamp.',
  settlement_offer_datetime   TIMESTAMP COMMENT 'Settlement offer timestamp.',
  closed_datetime             TIMESTAMP COMMENT 'Claim closed timestamp.',
  current_adjuster_party_id   BIGINT  COMMENT 'Denormalized FK -> party.party_id for current adjuster (optional convenience; authoritative history in claim_party_role).',
  last_updated_at             TIMESTAMP COMMENT 'Last update to this lifecycle row.'
)
COMMENT 'Operational cycle-time wide row (D1): intake, triage, inspection, settlement offer, closed. Prefer claim_party_role for adjuster history. Future claim_lifecycle_event table may reify phases as events without replacing this mart-friendly row.'
PARTITIONED BY SPEC (
  BUCKET(16, current_adjuster_party_id)
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimLifecycle',
  'llm.acord_concept' = 'Claim process / status timestamps',
  'llm.omg_pc_entity' = 'Claim Folder process milestones (related)',
  'llm.fibo_alignment' = 'extend: process schedule / event dates on Claim',
  'llm.primary_key' = 'claim_lifecycle_id',
  'llm.business_key' = 'claim_id',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;current_adjuster_party_id->party.party_id',
  'llm.object_properties' = 'lifecycleOf;assignedToAdjuster',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'internal',
  'llm.grain' = 'one wide lifecycle record per claim (or versioned row if ETL keeps history)',
  'llm.partitioning_rationale' = 'bucket adjuster for workload distribution queries (legacy partitioned by assigned_adjuster_id)',
  'llm.competency_questions' = 'Cycle time intake-to-close for claim C? When was inspection completed?',
  'llm.related_tables' = 'claim;claim_party_role',
  'llm.decision_refs' = 'D1,D3',
  'llm.notes' = 'Temporal order constraints (intake<=triage<=...) belong in SHACL/SPARQL, not Iceberg DDL.'
);


-- =============================================================================
-- RESERVES (D2 / D5)
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.claim_reserve (
  claim_reserve_id              BIGINT  COMMENT 'PK. Surrogate reserve header id (was reserve_id).',
  claim_id                      BIGINT  COMMENT 'FK -> claim.claim_id.',
  reserve_status_code           STRING  COMMENT 'Code -> ref_code(RESERVE_STATUS): OPEN | CLOSED.',
  currency_code                 STRING  COMMENT 'ISO 4217 currency for all amounts on this reserve header/components.',
  initial_loss_reserve_amount   DECIMAL(18,2) COMMENT 'Initial loss reserve set at setup (was initial_loss_reserve).',
  revised_reserve_total_amount  DECIMAL(18,2) COMMENT 'Current revised total reserve (was revised_reserve_total).',
  is_current                    BOOLEAN COMMENT 'D5: true for the current reserve header version used in reporting.',
  last_updated_at               TIMESTAMP COMMENT 'Last actuarial/claims update (was last_updated).',
  created_at                    TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Claim reserve header (OMG Claim Amount / reserve patterns; ACME-style LossReserve). PD/BI/expense breakdowns are in claim_reserve_component. History of changes in claim_reserve_transaction.'
PARTITIONED BY SPEC (
  is_current,
  reserve_status_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimReserve',
  'llm.acord_concept' = 'Claim reserve / financials',
  'llm.omg_pc_entity' = 'Claim Amount (reserve)',
  'llm.fibo_alignment' = 'extend: claim financial obligation / reserve',
  'llm.primary_key' = 'claim_reserve_id',
  'llm.business_key' = 'claim_id+is_current',
  'llm.foreign_keys' = 'claim_id->claim.claim_id',
  'llm.object_properties' = 'reserveForClaim;hasReserveComponent;hasReserveTransaction',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one reserve header version for a claim',
  'llm.partitioning_rationale' = 'is_current + status for actuarial current-vs-history scans',
  'llm.competency_questions' = 'What is the current total reserve on claim C? Initial vs revised reserve?',
  'llm.related_tables' = 'claim;claim_reserve_component;claim_reserve_transaction;claim_payment',
  'llm.decision_refs' = 'D2,D5,D10',
  'llm.notes' = 'Do not mark hasReserve functional in OWL unless business confirms single current header; use is_current=true filter in queries.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.claim_reserve_component (
  claim_reserve_component_id  BIGINT  COMMENT 'PK. Surrogate component id.',
  claim_reserve_id            BIGINT  COMMENT 'FK -> claim_reserve.claim_reserve_id.',
  reserve_type_code           STRING  COMMENT 'Code -> ref_code(RESERVE_TYPE): LOSS_PD | LOSS_BI | EXPENSE_ALE | EXPENSE_LEGAL | EXPENSE_ADJUSTING | RENTAL | OTHER.',
  reserve_amount              DECIMAL(18,2) COMMENT 'Component reserve amount in header currency.',
  created_at                  TIMESTAMP COMMENT 'Row creation timestamp.',
  last_updated_at             TIMESTAMP COMMENT 'Last update timestamp.'
)
COMMENT 'Typed reserve components. Migrates legacy property_damage_reserve and bodily_injury_reserve columns into LOSS_PD and LOSS_BI codes; supports expense reserves aligned to industry Loss vs Expense patterns.'
PARTITIONED BY SPEC (
  reserve_type_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimReserveComponent',
  'llm.acord_concept' = 'Reserve category amount',
  'llm.omg_pc_entity' = 'Claim Amount classification',
  'llm.fibo_alignment' = 'extend: typed monetary component',
  'llm.primary_key' = 'claim_reserve_component_id',
  'llm.business_key' = 'claim_reserve_id+reserve_type_code',
  'llm.foreign_keys' = 'claim_reserve_id->claim_reserve.claim_reserve_id',
  'llm.object_properties' = 'componentOfReserve',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one typed reserve amount under a reserve header',
  'llm.partitioning_rationale' = 'identity partition on reserve_type_code for PD vs BI vs expense analytics',
  'llm.competency_questions' = 'What is the BI reserve on claim C? Expense vs loss reserve split?',
  'llm.related_tables' = 'claim_reserve;claim',
  'llm.decision_refs' = 'D2,D10',
  'llm.notes' = 'Legacy: property_damage_reserve -> LOSS_PD; bodily_injury_reserve -> LOSS_BI.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.claim_reserve_transaction (
  claim_reserve_txn_id    BIGINT  COMMENT 'PK. Surrogate reserve ledger transaction id.',
  claim_reserve_id        BIGINT  COMMENT 'FK -> claim_reserve.claim_reserve_id.',
  transaction_datetime    TIMESTAMP COMMENT 'When the reserve change was booked.',
  reserve_type_code       STRING  COMMENT 'Code -> ref_code(RESERVE_TYPE). Component affected by the delta.',
  change_amount           DECIMAL(18,2) COMMENT 'Signed delta to the component reserve (positive increase / negative decrease).',
  reason_code             STRING  COMMENT 'Code or short reason for the change (e.g. NEW_INFO, SETTLEMENT, REOPEN).',
  created_by_party_id     BIGINT  COMMENT 'Optional FK -> party.party_id of adjuster/actuarial user.',
  created_at              TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Reserve change history (D5). Enables audit of how case reserves evolved; current balances remain on claim_reserve / claim_reserve_component.'
PARTITIONED BY SPEC (
  YEAR(transaction_datetime),
  reserve_type_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimReserveTransaction',
  'llm.acord_concept' = 'Reserve transaction',
  'llm.omg_pc_entity' = 'Claim Amount transaction (related)',
  'llm.fibo_alignment' = 'extend: financial transaction against reserve',
  'llm.primary_key' = 'claim_reserve_txn_id',
  'llm.business_key' = '',
  'llm.foreign_keys' = 'claim_reserve_id->claim_reserve.claim_reserve_id;created_by_party_id->party.party_id',
  'llm.object_properties' = 'transactionForReserve;createdByParty',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one reserve adjustment event',
  'llm.partitioning_rationale' = 'year(transaction_datetime)+reserve_type_code for time-series reserve analytics',
  'llm.competency_questions' = 'How did PD reserve change over time for claim C?',
  'llm.related_tables' = 'claim_reserve;claim_reserve_component;claim',
  'llm.decision_refs' = 'D2,D5,D10',
  'llm.notes' = 'Optional table for warehouses that only store current balances; keep for actuarial auditability.'
);


-- =============================================================================
-- PAYMENTS / CLAIM AMOUNTS (ledger)
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.claim_payment (
  claim_payment_id            BIGINT  COMMENT 'PK. Surrogate payment id (was transaction_id).',
  claim_id                    BIGINT  COMMENT 'FK -> claim.claim_id.',
  payment_datetime            TIMESTAMP COMMENT 'Best-known payment timestamp.',
  payment_date                DATE    COMMENT 'Payment calendar date; partition-friendly (was transaction_date).',
  payment_category_code       STRING  COMMENT 'Code -> ref_code(PAYMENT_CATEGORY): LOSS | EXPENSE | RENTAL | SALVAGE | MEDICAL | OTHER (was payment_category).',
  payment_amount              DECIMAL(18,2) COMMENT 'Gross amount paid for this transaction (was amount_paid).',
  deductible_applied_amount   DECIMAL(18,2) COMMENT 'Deductible applied on this payment (was deductible_applied).',
  currency_code               STRING  COMMENT 'ISO 4217 currency code.',
  payee_party_id              BIGINT  COMMENT 'FK -> party.party_id. Payee as first-class party when known.',
  payee_type_code             STRING  COMMENT 'Code -> ref_code(PAYEE_TYPE): INSURED | BODY_SHOP | CLAIMANT | ATTORNEY | LIENHOLDER | OTHER (was payee_type).',
  payment_status_code         STRING  COMMENT 'Code -> ref_code(PAYMENT_STATUS): PENDING | ISSUED | CLEARED | VOID | STOPPED (was payment_status).',
  policy_coverage_id          BIGINT  COMMENT 'Optional FK -> policy_coverage.policy_coverage_id for coverage-level payment attribution.',
  created_at                  TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Financial ledger of claim disbursements (OMG Claim Amount payments / ACORD payment concepts). Categorized by payment type, payee party/type, deductible, and settlement status.'
PARTITIONED BY SPEC (
  YEAR(payment_date),
  payment_category_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimPayment',
  'llm.acord_concept' = 'Claim payment',
  'llm.omg_pc_entity' = 'Claim Amount (payment)',
  'llm.fibo_alignment' = 'align/extend FIBO Payment patterns under Claim',
  'llm.primary_key' = 'claim_payment_id',
  'llm.business_key' = '',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;payee_party_id->party.party_id;policy_coverage_id->policy_coverage.policy_coverage_id',
  'llm.object_properties' = 'payoutForClaim;payoutUnderPolicy(chain);paidToParty;underPolicyCoverage',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one disbursement / payment transaction',
  'llm.partitioning_rationale' = 'year(payment_date)+payment_category_code matches legacy claim_payout_transactions partitioning',
  'llm.competency_questions' = 'Total paid on claim C? Payments to body shops vs insureds? Payments under collision coverage?',
  'llm.related_tables' = 'claim;party;policy_coverage;claim_reserve',
  'llm.decision_refs' = 'D10,D11',
  'llm.notes' = 'OWL property chain candidate: payoutForClaim o arisesFromPolicy => payoutUnderPolicy.'
);


-- =============================================================================
-- REPAIR / VENDOR ENGAGEMENT
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.repair_engagement (
  repair_engagement_id              BIGINT  COMMENT 'PK. Surrogate repair engagement id (was repair_id).',
  claim_id                          BIGINT  COMMENT 'FK -> claim.claim_id.',
  vendor_party_id                   BIGINT  COMMENT 'FK -> party.party_id (organization repair vendor). Replaces vendor_id + body_shop_name.',
  estimate_status_code              STRING  COMMENT 'Code -> ref_code(ESTIMATE_STATUS): ESTIMATED | APPROVED | IN_REPAIR | COMPLETED | SUPPLEMENTED.',
  estimated_repair_hours            DECIMAL(8,2) COMMENT 'Estimated labor hours (precision widened from DECIMAL(5,2)).',
  parts_cost_oem_amount             DECIMAL(18,2) COMMENT 'OEM parts cost (was parts_cost_oem).',
  parts_cost_aftermarket_amount     DECIMAL(18,2) COMMENT 'Aftermarket parts cost (was parts_cost_aftermarket).',
  labor_cost_amount                 DECIMAL(18,2) COMMENT 'Labor cost (was labor_cost).',
  rental_car_days_count             INT     COMMENT 'Rental days (was rental_car_days).',
  rental_car_total_amount           DECIMAL(18,2) COMMENT 'Rental total cost (was rental_car_total_cost).',
  currency_code                     STRING  COMMENT 'ISO 4217 currency for money columns.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.',
  last_updated_at                   TIMESTAMP COMMENT 'Last update timestamp.'
)
COMMENT 'Repair shop / vendor performance and estimate facts for a claim: hours, OEM vs aftermarket parts, labor, and rental car spend. Vendor identity is a Party/Organization.'
PARTITIONED BY SPEC (
  BUCKET(32, vendor_party_id)
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'RepairEngagement',
  'llm.acord_concept' = 'Repair / vendor service',
  'llm.omg_pc_entity' = 'Assessment / service provider engagement (related)',
  'llm.fibo_alignment' = 'extend: service engagement + monetary amounts',
  'llm.primary_key' = 'repair_engagement_id',
  'llm.business_key' = '',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;vendor_party_id->party.party_id',
  'llm.object_properties' = 'repairOfClaim;performedByVendor;repairForVehicle(chain)',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'internal',
  'llm.grain' = 'one repair estimate/engagement for a claim and vendor',
  'llm.partitioning_rationale' = 'bucket(vendor_party_id) for vendor performance queries (legacy partitioned by vendor_id)',
  'llm.competency_questions' = 'OEM vs aftermarket parts cost for claim C? Which vendor repaired the vehicle? Rental days?',
  'llm.related_tables' = 'claim;organization;party;vehicle;claim_payment',
  'llm.decision_refs' = 'D3,D10',
  'llm.notes' = 'Join organization for legal_name/trade_name. Property chain: repairOfClaim o involvesVehicle => repairForVehicle.'
);


-- =============================================================================
-- HIGH-VALUE EXTENSION: GEO_LOCATION
-- Table is geo_location (not location): LOCATION is reserved in Impala.
-- PK/FK column stays location_id.
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.geo_location (
  location_id                       BIGINT  COMMENT 'PK. Surrogate location identifier.',
  location_type_code                STRING  COMMENT 'Code -> ref_code(LOCATION_TYPE): LOSS_SCENE | GARAGING | INTERSECTION | PARKING_LOT | HIGHWAY | OTHER.',
  location_name                     STRING  COMMENT 'Optional place name (intersection name, landmark, facility).',
  street_line_1                     STRING  COMMENT 'Street address line 1 when known.',
  street_line_2                     STRING  COMMENT 'Street address line 2 optional.',
  city_name                         STRING  COMMENT 'City / locality.',
  country_subdivision_code          STRING  COMMENT 'State/province code.',
  postal_code                       STRING  COMMENT 'Postal/ZIP code.',
  country_code                      STRING  COMMENT 'ISO 3166-1 alpha-2.',
  latitude                          DECIMAL(9,6) COMMENT 'Optional geocode latitude (WGS84).',
  longitude                         DECIMAL(9,6) COMMENT 'Optional geocode longitude (WGS84).',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'First-class geographic location for loss scenes, garaging, and related claim geography. Prefer referencing location_id from loss_event and police_report instead of duplicating address fragments.'
PARTITIONED BY SPEC (
  country_subdivision_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'Location',
  'llm.acord_concept' = 'Location / Place',
  'llm.omg_pc_entity' = 'Geographic Location',
  'llm.fibo_alignment' = 'align to FIBO location / address constructs',
  'llm.primary_key' = 'location_id',
  'llm.business_key' = '',
  'llm.foreign_keys' = '',
  'llm.object_properties' = 'locationOfLoss;locationOfReport',
  'llm.pii' = 'mixed',
  'llm.sensitivity' = 'internal',
  'llm.grain' = 'one geographic place',
  'llm.partitioning_rationale' = 'subdivision code for regional loss analytics',
  'llm.competency_questions' = 'Where did the loss occur? Which losses are in state S?',
  'llm.related_tables' = 'loss_event;police_report;claim',
  'llm.decision_refs' = 'high_value_location',
  'llm.notes' = 'Distinct from party_postal_address (party contact). Loss geography belongs here.'
);


-- =============================================================================
-- HIGH-VALUE EXTENSION: DRIVERS
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.driver (
  driver_id                         BIGINT  COMMENT 'PK. Surrogate driver identifier.',
  party_id                          BIGINT  COMMENT 'FK -> party.party_id (PERSON). Driver is a person party.',
  license_number                    STRING  COMMENT 'PII/sensitive. Driver license number (mask in LLM contexts).',
  license_country_subdivision_code  STRING  COMMENT 'Licensing state/province.',
  license_country_code              STRING  COMMENT 'ISO 3166-1 alpha-2 of licensing authority country.',
  license_status_code               STRING  COMMENT 'Code -> ref_code(LICENSE_STATUS): VALID | SUSPENDED | EXPIRED | REVOKED | UNKNOWN.',
  license_class_code                STRING  COMMENT 'License class if captured (e.g. passenger auto).',
  date_first_licensed               DATE    COMMENT 'Optional first-licensed date for experience calculations.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Driver identity separate from policyholder. Links to person via party_id. Used by policy_driver (rated/declared drivers) and loss_driver (operators in the loss).'
PARTITIONED BY SPEC (
  license_country_subdivision_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'Driver',
  'llm.acord_concept' = 'Driver',
  'llm.omg_pc_entity' = 'Person in driver role / operator',
  'llm.fibo_alignment' = 'extend: person role; not a FIBO core class',
  'llm.primary_key' = 'driver_id',
  'llm.business_key' = 'license_country_code+license_country_subdivision_code+license_number',
  'llm.foreign_keys' = 'party_id->party.party_id',
  'llm.object_properties' = 'driverIsParty;listedOnPolicy;operatedInLoss',
  'llm.pii' = 'true',
  'llm.sensitivity' = 'restricted',
  'llm.grain' = 'one licensed (or unlicensed-known) driver person',
  'llm.partitioning_rationale' = 'licensing subdivision for DMV-oriented joins and regional driver analytics',
  'llm.competency_questions' = 'Who was the driver on the loss? Is the driver a listed policy driver?',
  'llm.related_tables' = 'party;person;policy_driver;loss_driver;fault_determination',
  'llm.decision_refs' = 'high_value_driver',
  'llm.notes' = 'Unlicensed operators: allow NULL license_number with license_status_code=UNKNOWN or UNLICENSED if seeded.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.policy_driver (
  policy_driver_id                  BIGINT  COMMENT 'PK. Surrogate for driver listed/rated on a policy.',
  policy_id                         BIGINT  COMMENT 'FK -> insurance_policy.policy_id.',
  driver_id                         BIGINT  COMMENT 'FK -> driver.driver_id.',
  driver_relationship_code          STRING  COMMENT 'Code -> ref_code(DRIVER_RELATIONSHIP): NAMED_INSURED | SPOUSE | CHILD | OTHER_RESIDENT | EXCLUDED | PERMISSIVE.',
  is_primary_driver                 BOOLEAN COMMENT 'True if primary rated driver.',
  is_excluded_driver                BOOLEAN COMMENT 'True if explicitly excluded from coverage.',
  effective_date                    DATE    COMMENT 'Driver added to policy effective from.',
  expiration_date                   DATE    COMMENT 'Driver removed/excluded effective to; NULL = current.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Drivers declared or rated on an auto policy (including excluded drivers). Distinct from the operator involved in a specific loss (see loss_driver).'
PARTITIONED BY SPEC (
  is_excluded_driver
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'PolicyDriver',
  'llm.acord_concept' = 'Driver on Policy',
  'llm.omg_pc_entity' = 'Party Role / rated driver on Agreement',
  'llm.fibo_alignment' = 'extend: role linking person to InsurancePolicy',
  'llm.primary_key' = 'policy_driver_id',
  'llm.business_key' = 'policy_id+driver_id+effective_date',
  'llm.foreign_keys' = 'policy_id->insurance_policy.policy_id;driver_id->driver.driver_id',
  'llm.object_properties' = 'listedOnPolicy;listsDriver',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one driver listing on a policy for a time range',
  'llm.partitioning_rationale' = 'excluded vs included driver scans for coverage disputes',
  'llm.competency_questions' = 'Was loss operator a listed driver on policy P? Who is excluded?',
  'llm.related_tables' = 'insurance_policy;driver;loss_driver;claim',
  'llm.decision_refs' = 'high_value_driver',
  'llm.notes' = 'Coverage dispute SHACL: loss_driver not in policy_driver and not permissive may imply denial review.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.loss_driver (
  loss_driver_id                    BIGINT  COMMENT 'PK. Surrogate for a driver involvement in a loss.',
  loss_event_id                     BIGINT  COMMENT 'FK -> loss_event.loss_event_id.',
  driver_id                         BIGINT  COMMENT 'FK -> driver.driver_id. Operator involved in the loss.',
  claim_id                          BIGINT  COMMENT 'Optional FK -> claim.claim_id when involvement is claim-scoped.',
  insurable_object_id               BIGINT  COMMENT 'Optional FK -> vehicle being operated at time of loss.',
  driver_role_code                  STRING  COMMENT 'Code: INSURED_OPERATOR | ADVERSE_OPERATOR | PERMISSIVE_USER | UNKNOWN_OPERATOR.',
  was_cited_indicator               BOOLEAN COMMENT 'True if traffic citation issued to this driver.',
  impairment_suspected_indicator    BOOLEAN COMMENT 'Suspected impairment/alcohol/drugs if captured at FNOL.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Operators involved in a loss event (insured and adverse). Bridges driver identity to loss_event and optionally to claim and vehicle operated.'
PARTITIONED BY SPEC (
  driver_role_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'LossDriver',
  'llm.acord_concept' = 'Driver involved in loss',
  'llm.omg_pc_entity' = 'Person involvement in Claim/Loss',
  'llm.fibo_alignment' = 'extend: participation in loss event',
  'llm.primary_key' = 'loss_driver_id',
  'llm.business_key' = 'loss_event_id+driver_id+driver_role_code',
  'llm.foreign_keys' = 'loss_event_id->loss_event.loss_event_id;driver_id->driver.driver_id;claim_id->claim.claim_id;insurable_object_id->insurable_object.insurable_object_id',
  'llm.object_properties' = 'operatedInLoss;operatedVehicle;involvedInClaim',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one driver participation in one loss',
  'llm.partitioning_rationale' = 'role code for insured vs adverse operator analytics',
  'llm.competency_questions' = 'Who drove the insured vehicle? Was the adverse driver cited?',
  'llm.related_tables' = 'loss_event;driver;claim;vehicle;fault_determination;police_report',
  'llm.decision_refs' = 'high_value_driver,D9',
  'llm.notes' = 'Prefer linking fault_determination.at_fault_driver_id to driver_id used here.'
);


-- =============================================================================
-- HIGH-VALUE EXTENSION: POLICE REPORT, FAULT, INJURY, DAMAGE
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.police_report (
  police_report_id                  BIGINT  COMMENT 'PK. Surrogate police report identifier.',
  loss_event_id                     BIGINT  COMMENT 'FK -> loss_event.loss_event_id.',
  claim_id                          BIGINT  COMMENT 'Optional FK -> claim.claim_id when report is claim-filed.',
  report_number                     STRING  COMMENT 'Business key from agency (report/case number).',
  agency_name                       STRING  COMMENT 'Reporting law-enforcement agency name.',
  agency_party_id                   BIGINT  COMMENT 'Optional FK -> party/organization for the agency.',
  report_datetime                   TIMESTAMP COMMENT 'When the report was taken / filed.',
  report_date                       DATE    COMMENT 'Report calendar date for partitioning.',
  location_id                       BIGINT  COMMENT 'Optional FK -> geo_location.location_id of incident as recorded by police.',
  citation_issued_indicator         BOOLEAN COMMENT 'True if any citation issued (detail may be on loss_driver).',
  narrative_summary                 STRING  COMMENT 'Short police narrative if stored; may contain PII.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Law-enforcement incident/police report associated with a loss (common FNOL artifact). Supports report number lookup and linkage to geo_location and claims.'
PARTITIONED BY SPEC (
  YEAR(report_date)
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'PoliceReport',
  'llm.acord_concept' = 'Police Report / Accident Report',
  'llm.omg_pc_entity' = 'Claim Document subtype (related)',
  'llm.fibo_alignment' = 'extend: evidence document for Claim',
  'llm.primary_key' = 'police_report_id',
  'llm.business_key' = 'agency_name+report_number',
  'llm.foreign_keys' = 'loss_event_id->loss_event.loss_event_id;claim_id->claim.claim_id;location_id->geo_location.location_id;agency_party_id->party.party_id',
  'llm.object_properties' = 'documentsLoss;documentsClaim;reportedAtLocation',
  'llm.pii' = 'mixed',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one police/accident report',
  'llm.partitioning_rationale' = 'year(report_date) for FNOL document-era pruning',
  'llm.competency_questions' = 'Is there a police report for loss L? What is the report number?',
  'llm.related_tables' = 'loss_event;claim;geo_location;claim_document;loss_driver',
  'llm.decision_refs' = 'high_value_police_report',
  'llm.notes' = 'Binary/PDF payload should live in claim_document with document_type_code=POLICE_REPORT; this table holds structured metadata.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.fault_determination (
  fault_determination_id            BIGINT  COMMENT 'PK. Surrogate fault determination identifier.',
  claim_id                          BIGINT  COMMENT 'FK -> claim.claim_id.',
  loss_event_id                     BIGINT  COMMENT 'FK -> loss_event.loss_event_id.',
  at_fault_driver_id                BIGINT  COMMENT 'Optional FK -> driver.driver_id determined at fault (or primary at-fault).',
  at_fault_party_id                 BIGINT  COMMENT 'Optional FK -> party.party_id when fault is organizational/other.',
  insured_fault_percent             DECIMAL(5,2) COMMENT 'Insured comparative negligence percent (0-100).',
  adverse_fault_percent             DECIMAL(5,2) COMMENT 'Adverse party fault percent (0-100).',
  fault_basis_code                  STRING  COMMENT 'Code -> ref_code(FAULT_BASIS): POLICE | ADJUSTER | LEGAL | SHARED | UNKNOWN.',
  determination_status_code         STRING  COMMENT 'PRELIMINARY | FINAL | DISPUTED.',
  determination_datetime            TIMESTAMP COMMENT 'When determination was recorded.',
  notes                             STRING  COMMENT 'Free-text rationale; may be used by agents with care.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Liability / comparative negligence determination for a claim/loss. Supports subrogation and BI/PD allocation decisions.'
PARTITIONED BY SPEC (
  determination_status_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'FaultDetermination',
  'llm.acord_concept' = 'Liability / Fault',
  'llm.omg_pc_entity' = 'Assessment Result (liability)',
  'llm.fibo_alignment' = 'extend: assessment outcome on Claim',
  'llm.primary_key' = 'fault_determination_id',
  'llm.business_key' = 'claim_id+determination_status_code+determination_datetime',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;loss_event_id->loss_event.loss_event_id;at_fault_driver_id->driver.driver_id;at_fault_party_id->party.party_id',
  'llm.object_properties' = 'faultForClaim;atFaultDriver;atFaultParty',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one fault/liability determination version for a claim',
  'llm.partitioning_rationale' = 'status for final vs disputed liability queues',
  'llm.competency_questions' = 'What is insured fault percent on claim C? Who is at fault?',
  'llm.related_tables' = 'claim;loss_event;driver;subrogation_case;litigation_case',
  'llm.decision_refs' = 'high_value_fault',
  'llm.notes' = 'SHACL soft rule: insured_fault_percent + adverse_fault_percent ~= 100 when both present.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.claim_injury (
  claim_injury_id                   BIGINT  COMMENT 'PK. Surrogate injury record id.',
  claim_id                          BIGINT  COMMENT 'FK -> claim.claim_id.',
  injured_party_id                  BIGINT  COMMENT 'FK -> party.party_id (PERSON) who was injured.',
  injury_severity_code             STRING  COMMENT 'Code -> ref_code(INJURY_SEVERITY): MINOR | MODERATE | SEVERE | FATAL | UNKNOWN.',
  body_region_code                  STRING  COMMENT 'Code -> ref_code(BODY_REGION): HEAD | NECK | BACK | UPPER_EXT | LOWER_EXT | CHEST | OTHER | MULTIPLE.',
  injury_description                STRING  COMMENT 'Clinical/FNOL injury description; may contain sensitive health info.',
  medical_provider_party_id         BIGINT  COMMENT 'Optional FK -> party/organization treating provider.',
  treatment_start_date              DATE    COMMENT 'First treatment date if known.',
  treatment_end_date                DATE    COMMENT 'Treatment end / MMI date if known.',
  ambulance_used_indicator          BOOLEAN COMMENT 'Ambulance/EMS used.',
  hospitalization_indicator         BOOLEAN COMMENT 'Hospital admission occurred.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Bodily injury details for a claim beyond BI reserve amounts. Captures injured person, severity, body region, and care indicators for BI claims handling and litigation risk.'
PARTITIONED BY SPEC (
  injury_severity_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimInjury',
  'llm.acord_concept' = 'Injury / Bodily Injury',
  'llm.omg_pc_entity' = 'Injury / Assessment related to Claim',
  'llm.fibo_alignment' = 'extend: claim impact on person (sensitive)',
  'llm.primary_key' = 'claim_injury_id',
  'llm.business_key' = 'claim_id+injured_party_id+body_region_code',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;injured_party_id->party.party_id;medical_provider_party_id->party.party_id',
  'llm.object_properties' = 'injuryOnClaim;injuredParty;treatedByProvider',
  'llm.pii' = 'true',
  'llm.sensitivity' = 'restricted',
  'llm.grain' = 'one injury record for an injured party on a claim',
  'llm.partitioning_rationale' = 'severity for BI triage and severity analytics',
  'llm.competency_questions' = 'Were there injuries on claim C? Severity and body region? Treating provider?',
  'llm.related_tables' = 'claim;party;person;claim_reserve_component;litigation_case;claim_payment',
  'llm.decision_refs' = 'high_value_injury',
  'llm.notes' = 'Health-sensitive: restrict LLM access. Multiple injuries per claim/person allowed.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.damage_assessment (
  damage_assessment_id              BIGINT  COMMENT 'PK. Surrogate assessment identifier.',
  claim_id                          BIGINT  COMMENT 'FK -> claim.claim_id.',
  insurable_object_id               BIGINT  COMMENT 'FK -> insurable_object/vehicle assessed.',
  assessor_party_id                 BIGINT  COMMENT 'FK -> party (appraiser, adjuster, or vendor) performing assessment.',
  assessment_type_code              STRING  COMMENT 'Code -> ref_code(ASSESSMENT_TYPE): STAFF_APPRAISAL | INDEPENDENT_APPRAISAL | DESK_REVIEW | DRONE | PHOTO.',
  assessment_datetime               TIMESTAMP COMMENT 'When assessment was performed.',
  assessment_date                   DATE    COMMENT 'Assessment calendar date.',
  estimated_repair_amount           DECIMAL(18,2) COMMENT 'Estimated repair cost from this assessment.',
  actual_cash_value_amount          DECIMAL(18,2) COMMENT 'Actual cash value (ACV) if evaluated.',
  total_loss_indicator              BOOLEAN COMMENT 'Assessor opinion that unit is total loss.',
  currency_code                     STRING  COMMENT 'ISO 4217 currency.',
  assessment_notes                  STRING  COMMENT 'Free-text assessment summary.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Formal property-damage appraisal/assessment distinct from repair_engagement (shop estimate/work). Supports independent appraisals, ACV, and total-loss opinions.'
PARTITIONED BY SPEC (
  YEAR(assessment_date),
  assessment_type_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'DamageAssessment',
  'llm.acord_concept' = 'Appraisal / Damage Estimate',
  'llm.omg_pc_entity' = 'Assessment',
  'llm.fibo_alignment' = 'extend: appraisal/assessment on insured asset',
  'llm.primary_key' = 'damage_assessment_id',
  'llm.business_key' = '',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;insurable_object_id->insurable_object.insurable_object_id;assessor_party_id->party.party_id',
  'llm.object_properties' = 'assessmentForClaim;assessesObject;performedByAssessor',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one damage appraisal/assessment event',
  'llm.partitioning_rationale' = 'year + assessment type for appraisal workload and ACV studies',
  'llm.competency_questions' = 'What was ACV on claim C? Staff vs independent appraisal amounts?',
  'llm.related_tables' = 'claim;vehicle;repair_engagement;claim_offer;party',
  'llm.decision_refs' = 'high_value_damage_assessment,D10',
  'llm.notes' = 'repair_engagement = shop path; damage_assessment = formal appraisal path. Both may exist.'
);


-- =============================================================================
-- HIGH-VALUE EXTENSION: CLAIM FOLDER / DOCUMENTS
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.claim_folder (
  claim_folder_id                   BIGINT  COMMENT 'PK. Surrogate claim folder id.',
  claim_id                          BIGINT  COMMENT 'FK -> claim.claim_id. Typically 1:1 with claim.',
  folder_status_code                STRING  COMMENT 'OPEN | CLOSED | ARCHIVED.',
  created_at                        TIMESTAMP COMMENT 'Folder creation timestamp.',
  closed_at                         TIMESTAMP COMMENT 'Folder closed/archived timestamp.'
)
COMMENT 'OMG Claim Folder: logical container for claim documents and artifacts. One folder per claim in most implementations.'
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimFolder',
  'llm.acord_concept' = 'Claim file / folder',
  'llm.omg_pc_entity' = 'Claim Folder',
  'llm.fibo_alignment' = 'extend: document collection for Claim',
  'llm.primary_key' = 'claim_folder_id',
  'llm.business_key' = 'claim_id',
  'llm.foreign_keys' = 'claim_id->claim.claim_id',
  'llm.object_properties' = 'folderForClaim;containsDocument',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one document folder for a claim',
  'llm.partitioning_rationale' = 'unpartitioned small hub; documents carry volume partitions',
  'llm.competency_questions' = 'What folder holds documents for claim C?',
  'llm.related_tables' = 'claim;claim_document',
  'llm.decision_refs' = 'high_value_documents',
  'llm.notes' = 'OWL: Claim documentedIn ClaimFolder; folder contains ClaimDocument.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.claim_document (
  claim_document_id                 BIGINT  COMMENT 'PK. Surrogate document id.',
  claim_folder_id                   BIGINT  COMMENT 'FK -> claim_folder.claim_folder_id.',
  claim_id                          BIGINT  COMMENT 'FK -> claim.claim_id (denormalized for partition/prune).',
  document_type_code                STRING  COMMENT 'Code -> ref_code(DOCUMENT_TYPE): FNOL | POLICE_REPORT | PHOTO | ESTIMATE | MEDICAL | RELEASE | CORRESPONDENCE | OTHER.',
  document_title                    STRING  COMMENT 'Display title.',
  mime_type                         STRING  COMMENT 'MIME type (application/pdf, image/jpeg, ...).',
  storage_uri                       STRING  COMMENT 'Object-store URI / path to binary (not stored in Iceberg row payload).',
  source_system                     STRING  COMMENT 'ECM/FNOL system that holds the binary.',
  received_datetime                 TIMESTAMP COMMENT 'When document was received.',
  received_date                     DATE    COMMENT 'Received calendar date.',
  related_police_report_id          BIGINT  COMMENT 'Optional FK -> police_report when document is that report scan.',
  related_damage_assessment_id      BIGINT  COMMENT 'Optional FK -> damage_assessment supporting docs.',
  pii_indicator                     BOOLEAN COMMENT 'True if document likely contains PII/PHI.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'OMG Claim Document metadata for files in a claim folder. Binary content remains in object storage referenced by storage_uri; this table is the catalog for agents and analytics.'
PARTITIONED BY SPEC (
  YEAR(received_date),
  document_type_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimDocument',
  'llm.acord_concept' = 'Attachment / Document',
  'llm.omg_pc_entity' = 'Claim Document',
  'llm.fibo_alignment' = 'extend: evidence/document resource',
  'llm.primary_key' = 'claim_document_id',
  'llm.business_key' = 'storage_uri',
  'llm.foreign_keys' = 'claim_folder_id->claim_folder.claim_folder_id;claim_id->claim.claim_id;related_police_report_id->police_report.police_report_id;related_damage_assessment_id->damage_assessment.damage_assessment_id',
  'llm.object_properties' = 'documentInFolder;documentForClaim;supportsAssessment;supportsPoliceReport',
  'llm.pii' = 'mixed',
  'llm.sensitivity' = 'restricted',
  'llm.grain' = 'one document metadata record',
  'llm.partitioning_rationale' = 'year(received_date)+document_type for retrieval and retention workflows',
  'llm.competency_questions' = 'Which photos exist for claim C? Is the police report PDF attached?',
  'llm.related_tables' = 'claim_folder;claim;police_report;damage_assessment',
  'llm.decision_refs' = 'high_value_documents',
  'llm.notes' = 'Do not embed document bytes in the table; agents should fetch via storage_uri with authz.'
);


-- =============================================================================
-- HIGH-VALUE EXTENSION: OFFERS, SUBROGATION, RECOVERIES, LITIGATION, FRAUD
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.claim_offer (
  claim_offer_id                    BIGINT  COMMENT 'PK. Surrogate settlement offer id.',
  claim_id                          BIGINT  COMMENT 'FK -> claim.claim_id.',
  offer_datetime                    TIMESTAMP COMMENT 'When offer was extended.',
  offer_date                        DATE    COMMENT 'Offer calendar date.',
  offer_amount                      DECIMAL(18,2) COMMENT 'Amount offered to settle.',
  currency_code                     STRING  COMMENT 'ISO 4217 currency.',
  offer_status_code                 STRING  COMMENT 'Code -> ref_code(OFFER_STATUS): EXTENDED | ACCEPTED | REJECTED | COUNTERED | WITHDRAWN | EXPIRED.',
  offer_type_code                   STRING  COMMENT 'FULL_SETTLEMENT | PARTIAL | POLICY_LIMITS | WALKAWAY.',
  payee_party_id                    BIGINT  COMMENT 'FK -> party.party_id receiving the offer.',
  policy_coverage_id                BIGINT  COMMENT 'Optional FK -> policy_coverage under which offer is made.',
  accepted_datetime                 TIMESTAMP COMMENT 'Acceptance timestamp if accepted.',
  notes                             STRING  COMMENT 'Offer rationale / conditions summary.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'OMG Claim Offer: settlement proposals to claimant/third party, with accept/reject/counter status. Distinct from claim_payment (money movement after agreement).'
PARTITIONED BY SPEC (
  YEAR(offer_date),
  offer_status_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimOffer',
  'llm.acord_concept' = 'Settlement Offer',
  'llm.omg_pc_entity' = 'Claim Offer',
  'llm.fibo_alignment' = 'extend: offer/commitment related to Claim',
  'llm.primary_key' = 'claim_offer_id',
  'llm.business_key' = '',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;payee_party_id->party.party_id;policy_coverage_id->policy_coverage.policy_coverage_id',
  'llm.object_properties' = 'offerOnClaim;offeredToParty;underPolicyCoverage;resultsInPayment',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one settlement offer instance',
  'llm.partitioning_rationale' = 'year + status for negotiation analytics and open-offer queues',
  'llm.competency_questions' = 'Was a settlement offer accepted on claim C? Offer vs paid amounts?',
  'llm.related_tables' = 'claim;claim_payment;party;policy_coverage;claim_lifecycle',
  'llm.decision_refs' = 'high_value_offer,D10',
  'llm.notes' = 'OMG: Claim Offer results in Claim Amount/payment when accepted.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.subrogation_case (
  subrogation_case_id               BIGINT  COMMENT 'PK. Surrogate subrogation case id.',
  claim_id                          BIGINT  COMMENT 'FK -> claim.claim_id.',
  adverse_party_id                  BIGINT  COMMENT 'FK -> party.party_id adverse responsible party when known.',
  adverse_carrier_party_id          BIGINT  COMMENT 'FK -> party/organization adverse insurer when known.',
  other_insurance_id                BIGINT  COMMENT 'Optional FK -> other_insurance.other_insurance_id.',
  subrogation_status_code           STRING  COMMENT 'Code -> ref_code(SUBROGATION_STATUS): OPEN | DEMANDED | NEGOTIATING | RECOVERED | CLOSED_UNRECOVERABLE | WAIVED.',
  demand_amount                     DECIMAL(18,2) COMMENT 'Amount demanded from adverse party/carrier.',
  recovered_amount                  DECIMAL(18,2) COMMENT 'Amount recovered to date (also detailed in claim_recovery).',
  currency_code                     STRING  COMMENT 'ISO 4217 currency.',
  opened_date                       DATE    COMMENT 'Subrogation case opened.',
  closed_date                       DATE    COMMENT 'Subrogation case closed.',
  statute_limitations_date          DATE    COMMENT 'Optional SOL / filing deadline.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Subrogation recovery case for a claim (expands claim.subrogation_indicator). Tracks adverse party/carrier, demand, status, and recovered totals.'
PARTITIONED BY SPEC (
  subrogation_status_code,
  YEAR(opened_date)
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'SubrogationCase',
  'llm.acord_concept' = 'Subrogation',
  'llm.omg_pc_entity' = 'Recovery / Claim Amount related',
  'llm.fibo_alignment' = 'extend: recovery claim against third party',
  'llm.primary_key' = 'subrogation_case_id',
  'llm.business_key' = 'claim_id',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;adverse_party_id->party.party_id;adverse_carrier_party_id->party.party_id;other_insurance_id->other_insurance.other_insurance_id',
  'llm.object_properties' = 'subrogationForClaim;seeksRecoveryFrom;adverseCarrier;hasRecovery',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one subrogation case for a claim (or split case if multiple adverses)',
  'llm.partitioning_rationale' = 'status + year opened for recovery inventory management',
  'llm.competency_questions' = 'Is claim C in subrogation? Demand vs recovered? Adverse carrier?',
  'llm.related_tables' = 'claim;claim_recovery;other_insurance;fault_determination;party',
  'llm.decision_refs' = 'high_value_subrogation,D10',
  'llm.notes' = 'When subrogation_case exists, claim.subrogation_indicator should be true (SHACL warning if not).'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.claim_recovery (
  claim_recovery_id                 BIGINT  COMMENT 'PK. Surrogate recovery (inflow) transaction id.',
  claim_id                          BIGINT  COMMENT 'FK -> claim.claim_id.',
  subrogation_case_id               BIGINT  COMMENT 'Optional FK -> subrogation_case.subrogation_case_id.',
  recovery_type_code                STRING  COMMENT 'Code -> ref_code(RECOVERY_TYPE): SUBROGATION | SALVAGE | DEDUCTIBLE_RECOVERY | CONTRIBUTION | OTHER.',
  recovery_datetime                 TIMESTAMP COMMENT 'When recovery was received/booked.',
  recovery_date                     DATE    COMMENT 'Recovery calendar date.',
  recovery_amount                   DECIMAL(18,2) COMMENT 'Amount recovered (inflow). Not a claim_payment.',
  currency_code                     STRING  COMMENT 'ISO 4217 currency.',
  payer_party_id                    BIGINT  COMMENT 'FK -> party.party_id who paid the recovery (carrier, salvager, insured).',
  salvage_vendor_party_id           BIGINT  COMMENT 'Optional FK -> party for salvage buyer/yard.',
  payment_status_code               STRING  COMMENT 'PENDING | RECEIVED | VOID.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Inbound recoveries (subrogation receipts, salvage proceeds, deductible recovery). Distinct from claim_payment outflows. Completes the financial picture with reserves and payments.'
PARTITIONED BY SPEC (
  YEAR(recovery_date),
  recovery_type_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimRecovery',
  'llm.acord_concept' = 'Recovery / Salvage',
  'llm.omg_pc_entity' = 'Claim Amount (recovery/collection)',
  'llm.fibo_alignment' = 'extend: incoming payment/recovery vs disbursement',
  'llm.primary_key' = 'claim_recovery_id',
  'llm.business_key' = '',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;subrogation_case_id->subrogation_case.subrogation_case_id;payer_party_id->party.party_id;salvage_vendor_party_id->party.party_id',
  'llm.object_properties' = 'recoveryForClaim;recoveryForSubrogation;paidByParty',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one recovery inflow transaction',
  'llm.partitioning_rationale' = 'year + recovery type for salvage vs subrogation cash analytics',
  'llm.competency_questions' = 'Total salvage and subrogation recovered on claim C? Net paid = payments - recoveries?',
  'llm.related_tables' = 'claim;subrogation_case;claim_payment;claim_reserve',
  'llm.decision_refs' = 'high_value_recovery,D10',
  'llm.notes' = 'Never model recoveries as negative claim_payment; keep ledger direction explicit for agents.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.litigation_case (
  litigation_case_id                BIGINT  COMMENT 'PK. Surrogate litigation case id.',
  claim_id                          BIGINT  COMMENT 'FK -> claim.claim_id.',
  litigation_status_code            STRING  COMMENT 'Code -> ref_code(LITIGATION_STATUS): PRE_SUIT | FILED | IN_DISCOVERY | SETTLED | DISMISSED | JUDGMENT | CLOSED.',
  docket_number                     STRING  COMMENT 'Court docket / case number.',
  venue_name                        STRING  COMMENT 'Court / venue name.',
  venue_country_subdivision_code    STRING  COMMENT 'State/province of venue.',
  plaintiff_party_id                BIGINT  COMMENT 'FK -> party.party_id plaintiff.',
  defendant_party_id                BIGINT  COMMENT 'FK -> party.party_id defendant (often insured or carrier).',
  plaintiff_counsel_party_id        BIGINT  COMMENT 'FK -> party/organization plaintiff counsel.',
  defense_counsel_party_id          BIGINT  COMMENT 'FK -> party/organization defense counsel.',
  filed_date                        DATE    COMMENT 'Suit filed date.',
  served_date                       DATE    COMMENT 'Service date if tracked.',
  closed_date                       DATE    COMMENT 'Litigation closed date.',
  demand_amount                     DECIMAL(18,2) COMMENT 'Litigation demand amount if known.',
  currency_code                     STRING  COMMENT 'ISO 4217 currency.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Litigation / suit case expanding claim.litigation_indicator. Captures docket, venue, parties, counsel, and key dates for legal ops and BI severity analytics.'
PARTITIONED BY SPEC (
  litigation_status_code,
  YEAR(filed_date)
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'LitigationCase',
  'llm.acord_concept' = 'Suit / Litigation',
  'llm.omg_pc_entity' = 'Legal action related to Claim',
  'llm.fibo_alignment' = 'extend: legal proceeding linked to Claim',
  'llm.primary_key' = 'litigation_case_id',
  'llm.business_key' = 'docket_number+venue_name',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;plaintiff_party_id->party.party_id;defendant_party_id->party.party_id;plaintiff_counsel_party_id->party.party_id;defense_counsel_party_id->party.party_id',
  'llm.object_properties' = 'litigationForClaim;hasPlaintiff;hasDefendant;hasCounsel',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one suit/litigation matter on a claim',
  'llm.partitioning_rationale' = 'status + year filed for legal inventory',
  'llm.competency_questions' = 'Is claim C in suit? Docket number? Counsel?',
  'llm.related_tables' = 'claim;claim_party_role;claim_injury;claim_offer;party',
  'llm.decision_refs' = 'high_value_litigation',
  'llm.notes' = 'ATTORNEY rows in claim_party_role remain; this table holds case-level structure. Indicator on claim should align.'
);


CREATE TABLE IF NOT EXISTS car_insurance_claims.litigation_task (
  litigation_task_id        BIGINT    COMMENT 'PK. Surrogate litigation task id.',
  litigation_case_id        BIGINT    COMMENT 'FK -> litigation_case.litigation_case_id (nullable if suit row missing).',
  claim_id                  BIGINT    COMMENT 'FK -> claim.claim_id.',
  task_type_code            STRING    COMMENT 'COMPLETE_FILE | ESCALATE_DISCOVERY | DRAFT_HOLD.',
  task_status_code          STRING    COMMENT 'OPEN | DONE | CANCELLED.',
  due_date                  DATE      COMMENT 'Optional due date.',
  run_id                    STRING    COMMENT 'Agent run that created the task.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
PARTITIONED BY SPEC (
  task_status_code,
  YEAR(created_at)
)
COMMENT 'Work item opened by LitigationAgent from playbook next_step (file completeness or discovery aging).'
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'LitigationTask',
  'llm.primary_key' = 'litigation_task_id',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;litigation_case_id->litigation_case.litigation_case_id',
  'llm.grain' = 'one work item on a litigated claim'
);


CREATE TABLE IF NOT EXISTS car_insurance_claims.claim_police_intake (
  claim_id                  BIGINT    COMMENT 'FK -> claim.claim_id.',
  incident_report_number    STRING    COMMENT 'Agency incident / exchange-slip number from the policyholder.',
  source_code               STRING    COMMENT 'POLICYHOLDER_APP.',
  collected_at              TIMESTAMP COMMENT 'When the policyholder submitted the number.',
  run_id                    STRING    COMMENT 'Optional agent run that prompted collection.'
)
COMMENT 'Policyholder-supplied police incident report number before a police_report row exists.'
PARTITIONED BY SPEC (
  YEAR(collected_at)
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimPoliceIntake',
  'llm.primary_key' = 'claim_id+collected_at',
  'llm.foreign_keys' = 'claim_id->claim.claim_id',
  'llm.grain' = 'one policyholder submission of an incident report number'
);


CREATE TABLE IF NOT EXISTS car_insurance_claims.claim_outbound_message (
  message_id                BIGINT    COMMENT 'PK. Surrogate outbound message id.',
  claim_id                  BIGINT    COMMENT 'FK -> claim.claim_id.',
  channel_code              STRING    COMMENT 'SMS.',
  to_phone                  STRING    COMMENT 'PII. Destination phone (E.164 when possible).',
  body_text                 STRING    COMMENT 'Curated message body. No carrier send.',
  purpose_code              STRING    COMMENT 'COLLECT_INCIDENT_REPORT_NUMBER.',
  run_id                    STRING    COMMENT 'Agent run that created the message.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Demo evidence for outbound SMS (no carrier). Policyholder is asked to enter the incident report number in the app.'
PARTITIONED BY SPEC (
  purpose_code,
  YEAR(created_at)
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimOutboundMessage',
  'llm.primary_key' = 'message_id',
  'llm.foreign_keys' = 'claim_id->claim.claim_id',
  'llm.grain' = 'one outbound SMS (or other channel) tied to a claim'
);


CREATE TABLE IF NOT EXISTS car_insurance_claims.pd_task (
  pd_task_id                BIGINT    COMMENT 'PK. Surrogate PD work-item id.',
  claim_id                  BIGINT    COMMENT 'FK -> claim.claim_id.',
  loss_event_id             BIGINT    COMMENT 'Optional FK -> loss_event.loss_event_id.',
  task_type_code            STRING    COMMENT 'COLLECT_INCIDENT_NUMBER | REQUEST_POLICE_REPORT | DETERMINE_FAULT | PD_REVIEW.',
  task_status_code          STRING    COMMENT 'OPEN | DONE | CANCELLED.',
  due_date                  DATE      COMMENT 'Optional due date.',
  incident_report_number    STRING    COMMENT 'Agency incident number for REQUEST_POLICE_REPORT (from claim_police_intake).',
  run_id                    STRING    COMMENT 'Agent run that created the task.',
  created_at                TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Work item opened by PdClaimsAgent from playbook next_step (collect incident number, police report request, fault, or PD review).'
PARTITIONED BY SPEC (
  task_status_code,
  YEAR(created_at)
)
STORED BY ICEBERG
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'PdTask',
  'llm.primary_key' = 'pd_task_id',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;loss_event_id->loss_event.loss_event_id',
  'llm.grain' = 'one work item on a property-damage claim'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.fraud_assessment (
  fraud_assessment_id               BIGINT  COMMENT 'PK. Surrogate fraud/SIU assessment id.',
  claim_id                          BIGINT  COMMENT 'FK -> claim.claim_id.',
  assessment_datetime               TIMESTAMP COMMENT 'When assessment result was recorded.',
  assessment_date                   DATE    COMMENT 'Assessment calendar date.',
  siu_referral_indicator            BOOLEAN COMMENT 'True if referred to Special Investigations Unit (SIU).',
  outcome_code                      STRING  COMMENT 'Code -> ref_code(FRAUD_ASSESSMENT_OUTCOME): SUSPECTED | CONFIRMED | CLEARED | INCONCLUSIVE | PENDING.',
  risk_score                        DECIMAL(7,4) COMMENT 'Optional model/investigative risk score.',
  assessor_party_id                 BIGINT  COMMENT 'FK -> party.party_id investigator/adjuster/SIU.',
  rationale_summary                 STRING  COMMENT 'Short rationale; avoid dumping raw investigative PII into LLM prompts.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'OMG-style Fraud Assessment / SIU outcome for a claim. Expands claim.fraudulent_claim_indicator into suspected vs confirmed vs cleared with investigative metadata.'
PARTITIONED BY SPEC (
  outcome_code,
  YEAR(assessment_date)
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'FraudAssessment',
  'llm.acord_concept' = 'SIU / Fraud Investigation',
  'llm.omg_pc_entity' = 'Fraud Assessment (Assessment Result)',
  'llm.fibo_alignment' = 'extend: assessment result on Claim',
  'llm.primary_key' = 'fraud_assessment_id',
  'llm.business_key' = '',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;assessor_party_id->party.party_id',
  'llm.object_properties' = 'fraudAssessmentForClaim;assessedByParty',
  'llm.pii' = 'mixed',
  'llm.sensitivity' = 'restricted',
  'llm.grain' = 'one fraud/SIU assessment result (history allowed)',
  'llm.partitioning_rationale' = 'outcome + year for SIU caseload and confirmed-fraud analytics',
  'llm.competency_questions' = 'Was claim C referred to SIU? Confirmed fraud or cleared?',
  'llm.related_tables' = 'claim;party;claim_document',
  'llm.decision_refs' = 'high_value_fraud',
  'llm.notes' = 'OWL class hints: SuspectedFraudulentClaim vs ConfirmedFraudulentClaim from outcome_code. Keep investigative detail access-controlled.'
);


CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.other_insurance (
  other_insurance_id                BIGINT  COMMENT 'PK. Surrogate other-insurance record id.',
  claim_id                          BIGINT  COMMENT 'FK -> claim.claim_id.',
  loss_event_id                     BIGINT  COMMENT 'Optional FK -> loss_event.loss_event_id.',
  other_insurance_type_code         STRING  COMMENT 'Code -> ref_code(OTHER_INSURANCE_TYPE): ADVERSE_AUTO | INSURED_OTHER_AUTO | HEALTH | WORKERS_COMP | UMBRELLA | UNKNOWN.',
  carrier_party_id                  BIGINT  COMMENT 'FK -> party/organization of the other carrier.',
  carrier_name_raw                  STRING  COMMENT 'Raw carrier name when party not yet mastered.',
  policy_number                     STRING  COMMENT 'Other carrier policy number if known.',
  claim_number                      STRING  COMMENT 'Other carrier claim number if known.',
  coverage_type_code                STRING  COMMENT 'Optional coverage type on the other policy.',
  contact_phone                     STRING  COMMENT 'PII/business contact phone for other carrier adjuster unit.',
  is_primary_on_loss                BOOLEAN COMMENT 'Whether other insurance is deemed primary.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Other / adverse insurance discovered on a loss or claim. Supports coordination of benefits, subrogation targeting, and adverse carrier linkage.'
PARTITIONED BY SPEC (
  other_insurance_type_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'OtherInsurance',
  'llm.acord_concept' = 'Other Insurance',
  'llm.omg_pc_entity' = 'Related Agreement / other policy on Claim',
  'llm.fibo_alignment' = 'extend: related InsurancePolicy reference (external)',
  'llm.primary_key' = 'other_insurance_id',
  'llm.business_key' = 'carrier_party_id+policy_number',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;loss_event_id->loss_event.loss_event_id;carrier_party_id->party.party_id',
  'llm.object_properties' = 'otherInsuranceOnClaim;issuedByCarrier;usedInSubrogation',
  'llm.pii' = 'mixed',
  'llm.sensitivity' = 'confidential',
  'llm.grain' = 'one other-insurance policy/claim reference on a loss/claim',
  'llm.partitioning_rationale' = 'type for adverse-auto vs health/comp coordination paths',
  'llm.competency_questions' = 'What adverse carrier covers the other vehicle? Other insurance claim number?',
  'llm.related_tables' = 'claim;loss_event;subrogation_case;party;organization',
  'llm.decision_refs' = 'high_value_other_insurance',
  'llm.notes' = 'External policies are references, not rows in insurance_policy (unless brought in-house).'
);


-- =============================================================================
-- HIGH-VALUE EXTENSION: LIFECYCLE EVENTS (complements D1 wide-row)
-- =============================================================================

CREATE EXTERNAL TABLE IF NOT EXISTS car_insurance_claims.claim_lifecycle_event (
  claim_lifecycle_event_id          BIGINT  COMMENT 'PK. Surrogate lifecycle event id.',
  claim_id                          BIGINT  COMMENT 'FK -> claim.claim_id.',
  event_type_code                   STRING  COMMENT 'Code -> ref_code(LIFECYCLE_EVENT_TYPE): INTAKE | TRIAGE | INSPECTION | APPRAISAL | OFFER | ACCEPTANCE | PAYMENT | REOPEN | CLOSE | SIU_REFERRAL | SUIT_FILED | OTHER.',
  event_datetime                    TIMESTAMP COMMENT 'When the event occurred.',
  event_date                        DATE    COMMENT 'Event calendar date.',
  actor_party_id                    BIGINT  COMMENT 'FK -> party.party_id who performed/recorded the event (adjuster, system user, vendor).',
  related_claim_offer_id            BIGINT  COMMENT 'Optional FK -> claim_offer.claim_offer_id.',
  related_claim_payment_id          BIGINT  COMMENT 'Optional FK -> claim_payment.claim_payment_id.',
  related_damage_assessment_id      BIGINT  COMMENT 'Optional FK -> damage_assessment.damage_assessment_id.',
  event_notes                       STRING  COMMENT 'Short event note.',
  created_at                        TIMESTAMP COMMENT 'Row creation timestamp.'
)
COMMENT 'Event-stream complement to wide-row claim_lifecycle (D1 amended). Each phase/action is a row for sequencing, SLA analytics, and OWL process modeling. Wide-row remains useful for cycle-time marts.'
PARTITIONED BY SPEC (
  YEAR(event_date),
  event_type_code
)
STORED BY ICEBERG
STORED AS PARQUET
TBLPROPERTIES (
  'format-version' = '2',
  'llm.domain' = 'personal_auto_pc_claims',
  'llm.ontology_class' = 'ClaimLifecycleEvent',
  'llm.acord_concept' = 'Claim activity / status event',
  'llm.omg_pc_entity' = 'Claim process event (related to Claim Folder activities)',
  'llm.fibo_alignment' = 'extend: dated occurrence in claim process',
  'llm.primary_key' = 'claim_lifecycle_event_id',
  'llm.business_key' = 'claim_id+event_type_code+event_datetime',
  'llm.foreign_keys' = 'claim_id->claim.claim_id;actor_party_id->party.party_id;related_claim_offer_id->claim_offer.claim_offer_id;related_claim_payment_id->claim_payment.claim_payment_id;related_damage_assessment_id->damage_assessment.damage_assessment_id',
  'llm.object_properties' = 'eventOnClaim;performedByActor;precedesEvent',
  'llm.pii' = 'false',
  'llm.sensitivity' = 'internal',
  'llm.grain' = 'one claim process event',
  'llm.partitioning_rationale' = 'year + event type for SLA and funnel analytics',
  'llm.competency_questions' = 'Event sequence for claim C? Time from intake to offer? Who closed the claim?',
  'llm.related_tables' = 'claim;claim_lifecycle;claim_offer;claim_payment;damage_assessment;party',
  'llm.decision_refs' = 'D1,high_value_lifecycle_event',
  'llm.notes' = 'ETL may sync milestone timestamps into claim_lifecycle for convenience while this table remains authoritative for history.'
);


-- =============================================================================
-- END OF DDL
-- =============================================================================
-- Suggested follow-ons (not in this file):
--   1) Seed DML for ref_code_list / ref_code (including high-value code lists)
--   2) Iceberg tags/branches for medallion layers if used
--   3) SHACL shapes for triangle + temporal + fault percent rules
--   4) OWL MVT Turtle from llm.ontology_class / llm.object_properties
-- =============================================================================
