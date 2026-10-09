"""Build a DCAT-AP 3.0.1 dcat:Catalog for one or more models as an rdflib graph.

Two kinds of input, kept apart: what the model's package carries (nothing invented), and what the catalog's publisher
declares in catalog.yaml because the profile's controlled vocabularies and ranges demand values the package cannot
know (the contact point, the EU data theme, access rights, language, the publisher's ADMS type). Every node the
graph references is typed and named inline, because the range shapes require it and a harvesting portal gets a
complete graph. DCAT-AP has no data-dictionary slot: the schema is cited twice, as dct:conformsTo (a dct:Standard,
the exact pinned bytes) and as foaf:page (a foaf:Document, the schema at its stable URL).
"""
from __future__ import annotations

import re
from datetime import date
from importlib import resources

import yaml
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, PROV, RDF, RDFS, SKOS, XSD

from .model import Model

VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
ADMS = Namespace("http://www.w3.org/ns/adms#")
DCATAP = Namespace("http://data.europa.eu/r5r/")
SDC4 = "https://semanticdatacharter.com/ns/sdc4/"
SDC4_RM = URIRef("https://semanticdatacharter.com/ns/sdc4/sdc4.xsd")
PERMANENCE = "https://semanticdatacharter.com/permanence.html"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PREFIXES = {"dcat": DCAT, "dct": DCTERMS, "foaf": FOAF, "vcard": VCARD, "skos": SKOS, "adms": ADMS, "dcatap": DCATAP, "prov": PROV,
            "rdfs": RDFS, "xsd": XSD}


class DeclaredInputError(Exception):
    pass


def load_declared(path=None, contact_name: str | None = None, contact_email: str | None = None) -> dict:
    """The declared input: the package's default file, or the publisher's own, with command-line overrides."""
    text = open(path, encoding="utf-8").read() if path else resources.files("sdchealthdcatap").joinpath("data/catalog.yaml").read_text(encoding="utf-8")
    d = yaml.safe_load(text) or {}
    contact = dict(d.get("contact") or {})
    if contact_name:
        contact["name"] = contact_name
    if contact_email:
        contact["email"] = contact_email
    d["contact"] = contact
    email = (contact.get("email") or "").strip()
    if not email or not EMAIL_RE.match(email):
        raise DeclaredInputError("a contact e-mail is required for the contact point; set contact.email in the catalog file or pass --contact-email")
    if not (contact.get("name") or "").strip():
        raise DeclaredInputError("a contact name is required (vcard:fn); set contact.name or pass --contact-name")
    for key in ("theme", "access_rights", "language"):
        if not d.get(key):
            raise DeclaredInputError(f"{key} is required: a URI from the EU Named Authority List the profile names")
    return d


def build_catalog(models: list[Model], declared: dict, today: date | None = None) -> Graph:
    today = today or date.today()
    g = Graph()
    for p, ns in PREFIXES.items():
        g.bind(p, ns)
    cat = declared.get("catalog") or {}
    catalog = URIRef(cat.get("id") or "https://semanticdatacharter.com/catalogs/governed-data-records")
    publisher = _agent(g, declared.get("publisher") or {}, declared)
    g.add((catalog, RDF.type, DCAT.Catalog))
    g.add((catalog, DCTERMS.title, Literal(cat.get("title") or "Governed data records", lang="en")))
    g.add((catalog, DCTERMS.description, Literal(cat.get("description") or "Collections of governed data records.", lang="en")))
    g.add((catalog, DCTERMS.publisher, publisher))
    g.add((catalog, DCTERMS.language, _language(g, declared)))
    if cat.get("homepage"):
        g.add((catalog, FOAF.homepage, _document(g, URIRef(cat["homepage"]), cat.get("title") or "Homepage")))
    # the theme taxonomy the datasets' themes come from (the codelist check expects the EU Data Theme vocabulary here)
    scheme = URIRef(declared.get("theme_taxonomy") or "http://publications.europa.eu/resource/authority/data-theme")
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, DCTERMS.title, Literal(declared.get("theme_taxonomy_label") or "EU Vocabularies Data Theme", lang="en")))
    g.add((catalog, DCAT.themeTaxonomy, scheme))
    dates = []
    for m in models:
        ds, d = _dataset(g, m, declared, publisher, today)
        g.add((catalog, DCAT.dataset, ds))
        dates.append(d)
    if dates:
        g.add((catalog, DCTERMS.issued, Literal(min(dates), datatype=XSD.date)))
        g.add((catalog, DCTERMS.modified, Literal(max(dates), datatype=XSD.date)))
    return g


def _dataset(g: Graph, model: Model, declared: dict, default_publisher: URIRef, today: date):
    pkg = model.package
    ds = URIRef(f"{SDC4}dm-{model.ct_id}")
    date_modified = (model.dc("date") or "")[:10] or today.isoformat()
    g.add((ds, RDF.type, DCAT.Dataset))
    g.add((ds, DCTERMS.title, Literal(f"{model.title} governed data records", lang="en")))
    g.add((ds, DCTERMS.description, Literal(_description(model, date_modified), lang="en")))
    g.add((ds, DCTERMS.identifier, Literal(f"dm-{model.ct_id}")))
    ident = BNode()
    g.add((ident, RDF.type, ADMS.Identifier))
    g.add((ident, SKOS.notation, Literal(f"dm-{model.ct_id}")))
    g.add((ident, ADMS.schemaAgency, Literal("Semantic Data Charter")))
    g.add((ds, ADMS.identifier, ident))
    # publisher: the model's dc:publisher when the modeler wrote one, else the declared publisher
    model_publisher = model.dc("publisher")
    pub = _agent(g, {"name": model_publisher}, declared, iri=None) if model_publisher else default_publisher
    g.add((ds, DCTERMS.publisher, pub))
    creator = model.dc("creator")
    if creator:
        g.add((ds, DCTERMS.creator, _agent(g, {"name": creator}, declared, iri=None, typed=False)))
    for c in model.contributors:
        g.add((ds, DCTERMS.contributor, _agent(g, {"name": c}, declared, iri=None, typed=False)))
    # contact point, declared
    contact = declared["contact"]
    kind = BNode()
    g.add((kind, RDF.type, VCARD.Kind))
    g.add((kind, VCARD.fn, Literal(contact["name"])))
    g.add((kind, VCARD.hasEmail, URIRef(f"mailto:{contact['email']}")))
    g.add((ds, DCAT.contactPoint, kind))
    for kw in _keywords(model):
        g.add((ds, DCAT.keyword, Literal(kw, lang="en")))
    theme = URIRef(declared["theme"])
    g.add((theme, RDF.type, SKOS.Concept))
    g.add((theme, SKOS.prefLabel, Literal(declared.get("theme_label") or declared["theme"].rsplit("/", 1)[-1], lang="en")))
    g.add((theme, SKOS.inScheme, URIRef(declared.get("theme_taxonomy") or "http://publications.europa.eu/resource/authority/data-theme")))
    g.add((ds, DCAT.theme, theme))
    g.add((ds, DCTERMS.issued, Literal(date_modified, datatype=XSD.date)))
    g.add((ds, DCTERMS.modified, Literal(date_modified, datatype=XSD.date)))
    g.add((ds, DCTERMS.language, _language(g, declared)))
    rights = URIRef(declared["access_rights"])
    g.add((rights, RDF.type, DCTERMS.RightsStatement))
    g.add((ds, DCTERMS.accessRights, rights))
    if model.rights_url:
        lic = URIRef(model.rights_url)
        g.add((lic, RDF.type, DCTERMS.LicenseDocument))
        g.add((ds, DCTERMS.license, lic))
    if model.rights_statement:
        rs = BNode()
        g.add((rs, RDF.type, DCTERMS.RightsStatement))
        g.add((rs, RDFS.label, Literal(model.rights_statement, lang="en")))
        g.add((ds, DCTERMS.rights, rs))
    g.add((ds, DCAT.landingPage, _document(g, URIRef(pkg.catalog_url), f"{model.title} in the public catalog")))
    # the schema: the standard the records conform to (the exact pinned bytes) and the document that defines their variables
    std = URIRef(pkg.schema_url_pinned)
    g.add((std, RDF.type, DCTERMS.Standard))
    g.add((std, DCTERMS.title, Literal(f"SDC4 schema dm-{model.ct_id} ({model.title})", lang="en")))
    g.add((std, DCTERMS.identifier, Literal(f"sha256:{pkg.sha256}")))
    g.add((std, DCTERMS.issued, Literal(date_modified, datatype=XSD.date)))
    g.add((ds, DCTERMS.conformsTo, std))
    page = _document(g, URIRef(pkg.schema_url), f"SDC4 schema dm-{model.ct_id}: the data dictionary of {model.title}")
    g.add((page, DCTERMS.description, Literal(f"The immutable schema every {model.title} record is validated against: {len(model.leaves)} variables with "
                                              "their definitions, datatypes, units, enumerated values and codes, and the sixteen typed reasons a value may be "
                                              f"missing. Current version SHA-256 {pkg.sha256}.", lang="en")))
    if declared.get("schema_format"):
        fmt = URIRef(declared["schema_format"])
        g.add((fmt, RDF.type, DCTERMS.MediaTypeOrExtent))
        g.add((page, DCTERMS["format"], fmt))
    g.add((page, DCTERMS.conformsTo, SDC4_RM))
    g.add((SDC4_RM, RDF.type, DCTERMS.Standard))
    g.add((SDC4_RM, DCTERMS.title, Literal("SDC4 reference model", lang="en")))
    g.add((ds, FOAF.page, page))
    prov = BNode()
    g.add((prov, RDF.type, DCTERMS.ProvenanceStatement))
    g.add((prov, RDFS.label, Literal("A published Semantic Data Charter model never changes; a revision is a new model naming the one it revised "
                                     f"(prov:wasRevisionOf). See {PERMANENCE}.", lang="en")))
    g.add((ds, DCTERMS.provenance, prov))
    g.add((ds, URIRef(str(DCAT) + "version"), Literal(pkg.sha256)))   # DCAT 3 property, not in rdflib's closed namespace
    coverage = model.dc("coverage")
    if coverage:
        loc = BNode()
        g.add((loc, RDF.type, DCTERMS.Location))
        g.add((loc, SKOS.prefLabel, Literal(coverage, lang="en")))
        g.add((ds, DCTERMS.spatial, loc))
    relation = model.dc("relation")
    if relation and re.match(r"^https?://\S+$", relation):
        g.add((ds, DCTERMS.relation, URIRef(relation)))
    return ds, date_modified


def _agent(g: Graph, p: dict, declared: dict, iri: str | None = "default", typed: bool = True):
    """A foaf:Agent with its name inline (the base shapes require foaf:name on every agent in the graph)."""
    node = URIRef(p["id"]) if (iri == "default" and p.get("id")) else BNode()
    g.add((node, RDF.type, FOAF.Agent))
    g.add((node, FOAF.name, Literal(p.get("name") or "Unknown")))
    if typed and p.get("type"):
        t = URIRef(p["type"])
        g.add((t, RDF.type, SKOS.Concept))
        g.add((t, SKOS.prefLabel, Literal(p.get("type_label") or p["type"].rsplit("/", 1)[-1], lang="en")))   # the skos:Concept shape needs a label
        g.add((node, DCTERMS.type, t))
    if p.get("id") and iri == "default":
        g.add((node, FOAF.homepage, _document(g, URIRef(p["id"]), p.get("name") or "Homepage")))
    return node


def _document(g: Graph, iri: URIRef, title: str) -> URIRef:
    g.add((iri, RDF.type, FOAF.Document))
    if (iri, DCTERMS.title, None) not in g:
        g.add((iri, DCTERMS.title, Literal(title, lang="en")))
    return iri


def _language(g: Graph, declared: dict) -> URIRef:
    lang = URIRef(declared["language"])
    g.add((lang, RDF.type, DCTERMS.LinguisticSystem))
    return lang


def _description(model: Model, date_modified: str) -> str:
    base = model.description.strip().rstrip(".")
    return (f"{base}. Each record is a governed data record conforming to the Semantic Data Charter model {model.title} "
            f"(dm-{model.ct_id}), published {date_modified}. The schema is immutable and defines every variable's name, definition, "
            f"datatype, units and permitted values; it is cited by URL and SHA-256 as the standard the records conform to and as the "
            f"page that documents them.")


def _keywords(model: Model) -> list[str]:
    words = model.subjects + ["Semantic Data Charter", "SDC4", "governed data record"]
    project = model.package.catalog.get("project_name")
    if project:
        words.insert(0, project)
    return words
