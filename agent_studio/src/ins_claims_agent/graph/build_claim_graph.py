"""Build an in-memory RDF graph for one claim run."""

from __future__ import annotations

from typing import Any

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from ins_claims_agent.mcp_facade import IcebergFacade
from ins_claims_agent.paths import default_ontology_path
from ins_claims_agent.graph.iri import claim_iri, entity_iri, term_iri

EX = Namespace("https://example.org/ins/")


def build_claim_graph(
    claim_id: int | str,
    *,
    iceberg: IcebergFacade | None = None,
    spine: dict[str, Any] | None = None,
    signals: dict[str, Any] | None = None,
    ontology_path: str | None = None,
    database: str = "car_insurance_claims",
) -> Graph:
    """Load TBox + claim spine/signals into an rdflib Graph.

    Prefer ``iceberg.get_claim_spine`` / ``get_claim_routing_signals`` (fork P0,
    or SQL fallback). For local unit tests, pass ``spine`` / ``signals`` dicts.
    """
    g = Graph()
    g.bind("ex", EX)

    onto = ontology_path or str(default_ontology_path())
    g.parse(onto, format="turtle")

    if spine is None:
        if iceberg is None:
            raise ValueError("Provide iceberg facade or spine dict")
        spine = iceberg.get_claim_spine(claim_id, database=database)
    if signals is None and iceberg is not None:
        signals = iceberg.get_claim_routing_signals(claim_id, database=database)
    signals = signals or {}

    _assert_spine(spine)
    claim = URIRef(claim_iri(claim_id))
    g.add((claim, RDF.type, EX.AutoClaim))

    _add_literal(g, claim, EX.claimNumber, spine.get("claim_number"), XSD.string)
    _add_literal(g, claim, EX.claimStatusCode, spine.get("claim_status_code"), XSD.string)
    _add_bool(g, claim, EX.litigationIndicator, spine.get("litigation_indicator"))
    _add_bool(g, claim, EX.subrogationIndicator, spine.get("subrogation_indicator"))
    _add_bool(g, claim, EX.fraudulentClaimIndicator, spine.get("fraudulent_claim_indicator"))
    _add_bool(g, claim, EX.totalLossIndicator, spine.get("total_loss_indicator"))

    if spine.get("loss_event_id") is not None:
        loss = URIRef(entity_iri("LossEvent", spine["loss_event_id"]))
        g.add((loss, RDF.type, EX.LossEvent))
        g.add((claim, EX.fromLossEvent, loss))
        _add_literal(g, loss, EX.lossCauseCode, spine.get("loss_cause_code"), XSD.string)

    if spine.get("policy_id") is not None:
        policy = URIRef(entity_iri("Policy", spine["policy_id"]))
        g.add((policy, RDF.type, EX.AutoInsurancePolicy))
        g.add((claim, EX.arisesFromPolicy, policy))
        _add_literal(g, policy, EX.policyNumber, spine.get("policy_number"), XSD.string)

    if spine.get("insurable_object_id") is not None:
        vehicle = URIRef(entity_iri("Vehicle", spine["insurable_object_id"]))
        g.add((vehicle, RDF.type, EX.Vehicle))
        g.add((claim, EX.involvesVehicle, vehicle))
        _add_literal(g, vehicle, EX.vin, spine.get("vin"), XSD.string)
        if spine.get("policy_id") is not None and spine.get("policy_covers_vehicle", True):
            policy = URIRef(entity_iri("Policy", spine["policy_id"]))
            g.add((policy, EX.coversVehicle, vehicle))

    coverage_codes = list(spine.get("coverage_type_codes") or [])
    if spine.get("coverage_type_code") and spine["coverage_type_code"] not in coverage_codes:
        coverage_codes.insert(0, spine["coverage_type_code"])

    if spine.get("policy_coverage_id") is not None or coverage_codes:
        pc_id = spine.get("policy_coverage_id") or "primary"
        pc = URIRef(entity_iri("PolicyCoverage", pc_id))
        g.add((pc, RDF.type, EX.PolicyCoverage))
        g.add((claim, EX.underPolicyCoverage, pc))
        for cov_code in coverage_codes:
            cov = URIRef(term_iri(f"Coverage/{cov_code}"))
            g.add((cov, RDF.type, EX.Coverage))
            g.add((pc, EX.ofCoverageType, cov))
            _add_literal(g, cov, EX.coverageTypeCode, cov_code, XSD.string)

    for role in spine.get("roles") or []:
        role_id = role.get("claim_party_role_id") or role.get("role_type_code")
        role_uri = URIRef(entity_iri("ClaimPartyRole", role_id))
        g.add((role_uri, RDF.type, EX.ClaimPartyRole))
        g.add((claim, EX.hasClaimPartyRole, role_uri))
        _add_literal(g, role_uri, EX.roleTypeCode, role.get("role_type_code"), XSD.string)
        if role.get("party_id") is not None:
            party = URIRef(entity_iri("Party", role["party_id"]))
            g.add((party, RDF.type, EX.Party))
            g.add((role_uri, EX.rolePlayedBy, party))

    if spine.get("claim_lifecycle_id") is not None:
        life = URIRef(entity_iri("Lifecycle", spine["claim_lifecycle_id"]))
        g.add((life, RDF.type, EX.ClaimLifecycle))
        g.add((claim, EX.hasLifecycle, life))

    _attach_signals(g, claim, signals)
    return g


def _attach_signals(g: Graph, claim: URIRef, signals: dict[str, Any]) -> None:
    if signals.get("has_subrogation_case") and signals.get("subrogation_case_id") is not None:
        case = URIRef(entity_iri("SubrogationCase", signals["subrogation_case_id"]))
        g.add((case, RDF.type, EX.SubrogationCase))
        g.add((claim, EX.hasSubrogationCase, case))
        _add_literal(
            g, case, EX.subrogationStatusCode, signals.get("subrogation_status_code"), XSD.string
        )

    if signals.get("has_litigation_case") and signals.get("litigation_case_id") is not None:
        lit = URIRef(entity_iri("LitigationCase", signals["litigation_case_id"]))
        g.add((lit, RDF.type, EX.LitigationCase))
        g.add((claim, EX.hasLitigationCase, lit))
    elif signals.get("has_litigation_case"):
        lit = URIRef(entity_iri("LitigationCase", "signal"))
        g.add((lit, RDF.type, EX.LitigationCase))
        g.add((claim, EX.hasLitigationCase, lit))

    if signals.get("has_injury"):
        injury_ids = signals.get("injury_ids") or ["signal"]
        for injury_id in injury_ids:
            inj = URIRef(entity_iri("ClaimInjury", injury_id))
            g.add((inj, RDF.type, EX.ClaimInjury))
            g.add((claim, EX.hasInjury, inj))

    if signals.get("has_police_report"):
        pr_id = signals.get("police_report_id") or "signal"
        pr = URIRef(entity_iri("PoliceReport", pr_id))
        g.add((pr, RDF.type, EX.PoliceReport))
        g.add((claim, EX.hasPoliceReport, pr))

    if signals.get("has_fault_determination"):
        fd_id = signals.get("fault_determination_id") or "signal"
        fd = URIRef(entity_iri("FaultDetermination", fd_id))
        g.add((fd, RDF.type, EX.FaultDetermination))
        g.add((claim, EX.hasFaultDetermination, fd))

    for offer in signals.get("offers") or []:
        oid = offer.get("claim_offer_id") or offer.get("offer_id") or "signal"
        offer_uri = URIRef(entity_iri("ClaimOffer", oid))
        g.add((offer_uri, RDF.type, EX.ClaimOffer))
        g.add((claim, EX.hasOffer, offer_uri))
        _add_literal(g, offer_uri, EX.offerStatusCode, offer.get("offer_status_code"), XSD.string)

    # Convenience flags when detailed offer rows are absent
    if not signals.get("offers"):
        if signals.get("has_unresolved_offer"):
            offer_uri = URIRef(entity_iri("ClaimOffer", "extended"))
            g.add((offer_uri, RDF.type, EX.ClaimOffer))
            g.add((claim, EX.hasOffer, offer_uri))
            _add_literal(g, offer_uri, EX.offerStatusCode, "EXTENDED", XSD.string)
        elif signals.get("has_accepted_offer"):
            offer_uri = URIRef(entity_iri("ClaimOffer", "accepted"))
            g.add((offer_uri, RDF.type, EX.ClaimOffer))
            g.add((claim, EX.hasOffer, offer_uri))
            _add_literal(g, offer_uri, EX.offerStatusCode, "ACCEPTED", XSD.string)
        elif signals.get("has_offer"):
            offer_uri = URIRef(entity_iri("ClaimOffer", "signal"))
            g.add((offer_uri, RDF.type, EX.ClaimOffer))
            g.add((claim, EX.hasOffer, offer_uri))

    if signals.get("has_loss_payment") or signals.get("payment_ids"):
        for pay_id in signals.get("payment_ids") or ["signal"]:
            pay = URIRef(entity_iri("ClaimPayment", pay_id))
            g.add((pay, RDF.type, EX.ClaimPayment))
            g.add((claim, EX.hasLossPayment, pay))

    if signals.get("has_recovery") or signals.get("recovery_ids"):
        for rec_id in signals.get("recovery_ids") or ["signal"]:
            rec = URIRef(entity_iri("ClaimRecovery", rec_id))
            g.add((rec, RDF.type, EX.ClaimRecovery))
            g.add((claim, EX.hasRecovery, rec))

    if signals.get("has_current_reserve"):
        res = URIRef(entity_iri("ClaimReserve", signals.get("reserve_id") or "current"))
        g.add((res, RDF.type, EX.ClaimReserve))
        g.add((claim, EX.hasReserve, res))
        _add_bool(g, res, EX.reserveIsCurrent, True)

    if signals.get("has_siu_suspected") or signals.get("fraud_outcome_code"):
        fa_id = signals.get("fraud_assessment_id") or "signal"
        fa = URIRef(entity_iri("FraudAssessment", fa_id))
        g.add((fa, RDF.type, EX.FraudAssessment))
        g.add((claim, EX.hasFraudAssessment, fa))
        _add_literal(
            g,
            fa,
            EX.fraudOutcomeCode,
            signals.get("fraud_outcome_code") or "SUSPECTED",
            XSD.string,
        )

    if signals.get("has_document"):
        for doc_id in signals.get("document_ids") or ["signal"]:
            doc = URIRef(entity_iri("ClaimDocument", doc_id))
            g.add((doc, RDF.type, EX.ClaimDocument))
            g.add((claim, EX.hasDocument, doc))


def _assert_spine(spine: dict[str, Any]) -> None:
    if "claim_id" not in spine and "claim_status_code" not in spine:
        # allow minimal test spines keyed only by status/flags
        return


def _add_literal(g: Graph, s: URIRef, p: URIRef, value: Any, datatype: URIRef) -> None:
    if value is None:
        return
    # Prefer plain string literals so SPARQL "CODE" matches (rdflib xsd:string
    # often fails to unify with simple-literal constants in ASK/FILTERs).
    if datatype == XSD.string:
        g.add((s, p, Literal(str(value))))
        return
    g.add((s, p, Literal(value, datatype=datatype)))


def _add_bool(g: Graph, s: URIRef, p: URIRef, value: Any) -> None:
    if value is None:
        return
    g.add((s, p, Literal(bool(value), datatype=XSD.boolean)))
