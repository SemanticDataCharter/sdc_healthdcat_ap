"""The health layer on the DCAT-AP graph: HealthDCAT-AP Release 8 at a declared access level.

What the package carries goes in from the package: every leaf of the record becomes a csvw:Column of the dataset's
table group (healthdcatap:hasVariables), the model's skos:exactMatch bindings become coding systems from the Coding
System NAL. What only a data holder knows comes from the declared input: the access level, the access body, the
legislation, the health category and theme, the counts, ages, personal-data categories, legal basis and purpose.
Every NAL concept the graph uses states its scheme (skos:inScheme), and every scheme is typed and titled, because the
validator's codelist shapes check membership that way.
"""
from __future__ import annotations

from datetime import date

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, RDF, SKOS, XSD

from .dcatap import DCATAP, DeclaredInputError, build_catalog, load_declared as _load_declared
from sdcreader import EXACT, CLOSE, IDENTIFIER, Model

HEALTH = Namespace("http://healthdataportal.eu/ns/health#")
CV = Namespace("http://data.europa.eu/m8g/")
DPV = Namespace("https://w3id.org/dpv#")
DQV = Namespace("http://www.w3.org/ns/dqv#")
OA = Namespace("http://www.w3.org/ns/oa#")
GEODCATAP = Namespace("http://data.europa.eu/930/")
CSVW = Namespace("http://www.w3.org/ns/csvw#")
ELI = Namespace("http://data.europa.eu/eli/ontology#")
EU_AUTH = "http://publications.europa.eu/resource/authority/"
HDEU = "https://hdeu-dcat.data.health.europa.eu/resource/authority/"
SCHEME_TITLES = {
    EU_AUTH + "access-right": "Access Rights Named Authority List", EU_AUTH + "language": "Languages Named Authority List",
    EU_AUTH + "data-theme": "Data Theme Named Authority List", EU_AUTH + "dataset-type": "Dataset Type Named Authority List",
    EU_AUTH + "file-type": "File Type Named Authority List", EU_AUTH + "planned-availability": "Planned Availability Named Authority List",
    HDEU + "publisher-type": "Health Publisher Types NAL", HDEU + "healthcategories": "Health Categories (EHDS Art. 51) NAL",
    HDEU + "health-theme": "Health Theme NAL", HDEU + "coding-system": "Coding System NAL",
}
#: the model's concept systems by IRI prefix, as the Coding System NAL names them
CODING_SYSTEMS = [
    ("http://snomed.info/sct", "SNOMED-CT", "SNOMED CT"), ("https://loinc.org/", "LOINC", "LOINC"), ("http://loinc.org/", "LOINC", "LOINC"),
    ("http://purl.obolibrary.org/obo/NCIT_", "NCIT", "NCI Thesaurus"), ("http://purl.bioontology.org/ontology/ICD10", "ICD-10", "ICD-10"),
    ("http://www.whocc.no/atc", "ATC", "ATC"), ("http://unitsofmeasure.org", "UCUM", "UCUM"), ("http://id.nlm.nih.gov/mesh", "MESH", "MeSH"),
    ("http://purl.obolibrary.org/obo/HP_", "HPO", "HPO"), ("http://www.orpha.net/ORDO", "ORPHACODE", "Orphanet"),
    ("https://www.nlm.nih.gov/research/umls/rxnorm", "RXNORM", "RxNorm"),
]
LEVELS = {"PUBLIC", "NON_PUBLIC", "RESTRICTED"}


def load_declared(path=None, contact_name: str | None = None, contact_email: str | None = None) -> dict:
    d = _load_declared(path, contact_name, contact_email)
    level = (d.get("access_level") or "").upper()
    if level not in LEVELS:
        raise DeclaredInputError("access_level must be PUBLIC, NON_PUBLIC or RESTRICTED (the validator's shape set is chosen by it)")
    d["access_level"] = level
    for key in ("applicable_legislation", "health_category", "hdab", "distribution"):
        if not d.get(key):
            raise DeclaredInputError(f"{key} is required: HealthDCAT-AP makes it mandatory at every access level")
    if not (d["distribution"].get("access_url") or "").strip():
        raise DeclaredInputError("distribution.access_url is required: a distribution needs dcat:accessURL")
    return d


def build_health_catalog(models: list[Model], declared: dict, today: date | None = None) -> Graph:
    g = build_catalog(models, declared, today)
    g.bind("healthdcatap", HEALTH); g.bind("cv", CV); g.bind("dpv", DPV); g.bind("dqv", DQV); g.bind("oa", OA)
    g.bind("geodcatap", GEODCATAP); g.bind("csvw", CSVW); g.bind("eli", ELI)
    catalog = next(g.subjects(RDF.type, DCAT.Catalog))
    legislation = URIRef(declared["applicable_legislation"])
    g.add((legislation, RDF.type, ELI.LegalResource))
    g.add((catalog, DCATAP.applicableLegislation, legislation))
    publisher = g.value(catalog, DCTERMS.publisher)
    _health_agent(g, publisher, declared)
    for scheme_of in ((declared["language"], EU_AUTH + "language"), (declared["theme"], EU_AUTH + "data-theme"),
                      (declared.get("schema_format"), EU_AUTH + "file-type"), (declared["publisher"].get("type"), HDEU + "publisher-type")):
        if scheme_of[0]:
            _in_scheme(g, URIRef(scheme_of[0]), scheme_of[1])
    datasets = {str(g.value(ds, DCTERMS.identifier)): ds for ds in g.objects(catalog, DCAT.dataset)}
    for m in models:
        _health_layer(g, datasets[f"dm-{m.ct_id}"], m, declared, publisher, legislation)
    # A HealthDCAT-AP document is the Dataset, as the release's own examples are. With DCAT loaded (dcat:Catalog is a
    # subclass of dcat:Dataset), the validator reads a Catalog node as a Dataset and holds it to the Dataset's mandatory
    # list, so the Catalog wrapper stays out; the HealthData@EU catalogue is the catalogue.
    homepage = g.value(catalog, FOAF.homepage)
    for t in list(g.triples((catalog, None, None))):
        g.remove(t)
    if homepage is not None and (None, None, homepage) not in g:
        for t in list(g.triples((homepage, None, None))):
            g.remove(t)
    return g


def _health_layer(g: Graph, ds: URIRef, model: Model, declared: dict, publisher: URIRef, legislation: URIRef) -> None:
    pkg = model.package
    g.add((ds, DCATAP.applicableLegislation, legislation))
    # access rights at the declared level (the writer's DCAT-AP layer already stated the declared access right; make them agree)
    for old in list(g.objects(ds, DCTERMS.accessRights)):
        g.remove((ds, DCTERMS.accessRights, old))
    rights = URIRef(declared["access_rights"])
    g.add((rights, RDF.type, DCTERMS.RightsStatement))
    g.add((rights, RDF.type, SKOS.Concept))
    g.add((rights, SKOS.prefLabel, Literal(declared["access_level"].replace("_", " ").title(), lang="en")))
    _in_scheme(g, rights, EU_AUTH + "access-right")
    g.add((ds, DCTERMS.accessRights, rights))
    # the dataset's publisher is a health publisher (contact point, health publisher type); the access body and custodian are declared
    ds_publisher = g.value(ds, DCTERMS.publisher)
    if ds_publisher != publisher:
        _health_agent(g, ds_publisher, declared)
    hdab = publisher if declared.get("hdab") == "publisher" else _declared_agent(g, declared["hdab"], declared)
    g.add((ds, HEALTH.hdab, hdab))
    custodian = publisher if declared.get("custodian", "publisher") == "publisher" else _declared_agent(g, declared["custodian"], declared)
    g.add((ds, GEODCATAP.custodian, custodian))
    # type, category, theme from the NALs
    _concept(g, ds, DCTERMS.type, declared.get("dataset_type"), declared.get("dataset_type_label"), EU_AUTH + "dataset-type")
    _concept(g, ds, HEALTH.healthCategory, declared["health_category"], declared.get("health_category_label"), HDEU + "healthcategories")
    _concept(g, ds, HEALTH.healthTheme, declared.get("health_theme"), declared.get("health_theme_label"), HDEU + "health-theme")
    # the distribution that is the access route
    dist = declared["distribution"]
    d = URIRef(f"{ds}#distribution")
    g.add((d, RDF.type, DCAT.Distribution))
    g.add((d, DCTERMS.title, Literal(dist.get("title") or "Access to the records", lang="en")))
    g.add((d, DCTERMS.description, Literal(dist.get("description") or "Access by request.", lang="en")))
    g.add((d, DCAT.accessURL, URIRef(dist["access_url"])))
    g.add((d, DCATAP.applicableLegislation, legislation))
    if dist.get("availability"):
        _concept(g, d, DCATAP.availability, dist["availability"], dist.get("availability_label"), EU_AUTH + "planned-availability")
    if model.rights_url:
        g.add((d, DCTERMS.license, URIRef(model.rights_url)))
    # the schema: HealthDCAT-AP closes dct:conformsTo on the Dataset to the Technical Standard NAL, so the citation of
    # the standard the records conform to moves to the distribution; the Dataset keeps foaf:page and the table group
    for std in list(g.objects(ds, DCTERMS.conformsTo)):
        g.remove((ds, DCTERMS.conformsTo, std))
        g.add((d, DCTERMS.conformsTo, std))
    g.add((ds, DCAT.distribution, d))
    # the variables: the data dictionary as a CSVW table group, one column per leaf of the record
    g.add((ds, HEALTH.hasStructuredData, Literal(True)))
    tg = URIRef(f"{ds}#variables")
    g.add((tg, RDF.type, CSVW.TableGroup))
    g.add((tg, DCTERMS.title, Literal(f"Variables of {model.title}", lang="en")))
    g.add((tg, DCTERMS.description, Literal(f"The {len(model.leaves)} variables of a {model.title} governed data record, in document order, as the "
                                            f"immutable schema defines them (SHA-256 {pkg.sha256}). Every variable may carry one of the sixteen "
                                            "exceptional values of the SDC4 reference model in place of a value, the typed reason it is missing.", lang="en")))
    table = URIRef(f"{ds}#table")
    g.add((table, RDF.type, CSVW.Table))
    g.add((table, DCTERMS.title, Literal(f"{model.title} record", lang="en")))
    g.add((table, CSVW.url, URIRef(pkg.schema_url_pinned)))
    g.add((tg, CSVW.table, table))
    seen: dict[str, int] = {}
    for leaf in model.leaves:
        c = leaf.component
        slug = leaf.slug
        n = seen.get(slug, 0); seen[slug] = n + 1
        if n:
            slug = f"{slug}-{n + 1}"
        col = URIRef(f"{ds}#column/{slug}")
        g.add((col, RDF.type, CSVW.Column))
        g.add((col, CSVW.name, Literal(slug)))                 # unique in the table: the path; a component composed three times is three columns
        g.add((col, DCTERMS.identifier, Literal(f"ms-{c.ct_id}")))   # the element name in the record
        g.add((col, CSVW.title, Literal(c.label, lang="en")))
        g.add((col, CSVW.datatype, Literal((c.data_type or "xsd:string").split(":")[-1])))
        g.add((col, DCTERMS.description, Literal(c.description if len(c.description) >= 10 else f"{c.label}: an {c.sdc_type} of the {model.title} record.", lang="en")))
        g.add((col, CSVW.propertyUrl, URIRef(c.link(IDENTIFIER) or c.iri)))
        g.add((table, CSVW.column, col))
    g.add((ds, HEALTH.hasVariables, tg))
    # the coding systems the model's bindings use
    systems, named = _coding_systems(model)
    for code, label in sorted(systems.items()):
        _concept(g, ds, HEALTH.hasCodingSystem, HDEU + "coding-system/" + code, label, HDEU + "coding-system")
        g.add((URIRef(HDEU + "coding-system/" + code), RDF.type, DCTERMS.Standard))   # the range shapes ask for dct:Standard as well
    if named:
        g.add((ds, HEALTH.hasCodeValues, Literal("Enumerated values and concepts carry codes from " + ", ".join(sorted(named)) +
                                                  " as skos:exactMatch bindings in the schema.", lang="en")))
    # the data holder's facts
    for key, prop in (("number_of_records", HEALTH.numberOfRecords), ("number_of_unique_individuals", HEALTH.numberOfUniqueIndividuals),
                      ("min_typical_age", HEALTH.minTypicalAge), ("max_typical_age", HEALTH.maxTypicalAge)):
        if declared.get(key) is not None:
            g.add((ds, prop, Literal(int(declared[key]), datatype=XSD.nonNegativeInteger)))
    if declared.get("population_coverage"):
        g.add((ds, HEALTH.populationCoverage, Literal(declared["population_coverage"], lang="en")))
    for pd in declared.get("personal_data") or []:
        g.add((URIRef(pd), RDF.type, DPV.PersonalData))
        g.add((ds, DPV.hasPersonalData, URIRef(pd)))
    for key, cls, prop in (("legal_basis", DPV.LegalBasis, DPV.hasLegalBasis), ("purpose", DPV.Purpose, DPV.hasPurpose)):
        if declared.get(key):
            b = BNode()
            g.add((b, RDF.type, cls))
            g.add((b, DCTERMS.description, Literal(declared[key], lang="en")))
            g.add((ds, prop, b))
    # the quality annotation: every record is validated against the schema before it exists
    q = BNode()
    g.add((q, RDF.type, DQV.QualityCertificate))
    g.add((q, OA.motivatedBy, DQV.qualityAssessment))
    g.add((q, OA.hasBody, URIRef(pkg.schema_url_pinned)))
    g.add((ds, DQV.hasQualityAnnotation, q))


def _health_agent(g: Graph, agent, declared: dict) -> None:
    """A health publisher: a cv:ContactPoint (exactly one) and a type from the Health Publisher Types NAL."""
    if (agent, CV.contactPoint, None) in g:
        return
    contact = declared["contact"]
    cp = BNode()
    g.add((cp, RDF.type, CV.ContactPoint))
    g.add((cp, CV.email, Literal(contact["email"])))
    if contact.get("page"):
        g.add((cp, CV.contactPage, URIRef(contact["page"])))
    g.add((agent, CV.contactPoint, cp))


def _declared_agent(g: Graph, spec: dict, declared: dict) -> URIRef:
    node = URIRef(spec["id"]) if spec.get("id") else BNode()
    g.add((node, RDF.type, FOAF.Agent))
    g.add((node, FOAF.name, Literal(spec.get("name") or "Unknown", lang="en")))
    if spec.get("type"):
        t = URIRef(spec["type"])
        g.add((t, RDF.type, SKOS.Concept))
        g.add((t, SKOS.prefLabel, Literal(spec.get("type_label") or spec["type"].rsplit("/", 1)[-1], lang="en")))
        _in_scheme(g, t, HDEU + "publisher-type")
        g.add((node, DCTERMS.type, t))
    cp = BNode()
    g.add((cp, RDF.type, CV.ContactPoint))
    if spec.get("email"):
        g.add((cp, CV.email, Literal(spec["email"])))
    if spec.get("page"):
        g.add((cp, CV.contactPage, URIRef(spec["page"])))
    g.add((node, CV.contactPoint, cp))
    return node


def _concept(g: Graph, subject, prop, iri: str | None, label: str | None, scheme: str) -> None:
    if not iri:
        return
    c = URIRef(iri)
    g.add((c, RDF.type, SKOS.Concept))
    g.add((c, SKOS.prefLabel, Literal(label or iri.rsplit("/", 1)[-1], lang="en")))
    _in_scheme(g, c, scheme)
    g.add((subject, prop, c))


def _in_scheme(g: Graph, concept: URIRef, scheme: str) -> None:
    s = URIRef(scheme)
    g.add((concept, SKOS.inScheme, s))
    g.add((s, RDF.type, SKOS.ConceptScheme))
    g.add((s, DCTERMS.title, Literal(SCHEME_TITLES.get(scheme, scheme.rsplit("/", 1)[-1]), lang="en")))


def _coding_systems(model: Model):
    systems: dict[str, str] = {}
    named: set[str] = set()
    for c in model.components.values():
        for p in (EXACT, CLOSE):
            for o in c.links.get(p, []):
                for prefix, code, label in CODING_SYSTEMS:
                    if o.startswith(prefix):
                        systems[code] = label
                        named.add(label)
    for key, codes in model.codes.items():
        for code in codes:
            for prefix, nal, label in CODING_SYSTEMS:
                if code.defined_by.startswith(prefix):
                    systems[nal] = label
                    named.add(label)
    return systems, named
