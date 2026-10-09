"""The NHANES Participant catalog, at the NON_PUBLIC access level, passes the HealthData@EU validator's own shape set
for that level at the pinned commit (with the vocabularies the validator preloads as background), in Turtle and in
JSON-LD; the release's own ARCA example behaves at the pin as recorded; the variables are the record's leaves; the
coding systems are the model's bindings; and the holder's facts are declared input."""
import hashlib
from collections import Counter
from datetime import date
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, RDF, SKOS

from sdchealthdcatap import DeclaredInputError, build_health_catalog, load_declared, load_package, read_model
from sdchealthdcatap.healthdcatap import CSVW, CV, DPV, HEALTH
from sdchealthdcatap.validate import background, run, shapes_graph

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "samples" / "nhanes-participant"
SNAPSHOT = ROOT / "data" / "healthdcat-ap-r8-cd7841f"
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
CT = "xy8upneajsb8vdcmnve01g6g"
DAY = date(2026, 10, 9)
DS = URIRef(f"https://semanticdatacharter.com/ns/sdc4/dm-{CT}")


@pytest.fixture(scope="module")
def bg():
    return background(SNAPSHOT)


@pytest.fixture(scope="module")
def model():
    return read_model(load_package(PACKAGE))


@pytest.fixture(scope="module")
def graph(model):
    return build_health_catalog([model], load_declared(), today=DAY)


def test_the_catalog_passes_the_validators_non_public_shape_set_in_turtle_and_json_ld(graph, bg):
    sg = shapes_graph(SNAPSHOT, "NON_PUBLIC")
    for fmt in ("turtle", "json-ld"):
        data = Graph().parse(data=graph.serialize(format=fmt), format=fmt)
        ok, res = run(data, sg, bg)
        violations = [r for r in res if r[0] == "Violation"]
        assert ok and not violations, (fmt, violations[:5])
        # the warnings are the recommended properties the package does not carry, and the publisher outside the Corporate Bodies NAL
        paths = Counter(r[2].rsplit("/", 1)[-1].rsplit("#", 1)[-1] for r in res)
        assert set(paths) <= {"publisher", "analytics", "retentionPeriod", "accrualPeriodicity", "conformsTo", "isReferencedBy", "relation",
                              "source", "temporal", "sample", "temporalResolution"}, paths


def test_the_committed_samples_equal_a_fresh_run(graph):
    for name, fmt in (("catalog.ttl", "turtle"), ("catalog.jsonld", "json-ld")):
        assert Graph().parse(PACKAGE / name, format=fmt).isomorphic(graph), name


def test_the_releases_own_example_behaves_at_the_pin_as_recorded(bg):
    """ARCA (an EPRDR registry, PUBLIC) passes the public set except where the background we carry stops: the Languages
    NAL (14 MB) and the ADMS licence-type scheme are not in the snapshot, so its language and licence type report."""
    ex = Graph().parse(SNAPSHOT / "examples" / "EPRDR" / "ARCA.ttl", format="turtle")
    ok, res = run(ex, shapes_graph(SNAPSHOT, "PUBLIC"), bg)
    violations = {r[2].rsplit("/", 1)[-1].rsplit("#", 1)[-1] for r in res if r[0] == "Violation"}
    assert violations <= {"language", "type"}, violations


def test_the_variables_are_the_records_leaves_and_the_coding_systems_are_the_models_bindings(graph, model):
    assert (DS, HEALTH.hasStructuredData, Literal(True)) in graph
    tg = graph.value(DS, HEALTH.hasVariables)
    table = graph.value(tg, CSVW.table)
    columns = list(graph.objects(table, CSVW.column))
    assert len(columns) == len(model.leaves) == 153
    names = [str(graph.value(c, CSVW.name)) for c in columns]
    assert len(set(names)) == len(names)                     # the path, unique; the element name repeats where a component is composed thrice
    assert all(str(graph.value(c, DCTERMS.identifier)).startswith("ms-") for c in columns)
    for c in columns:
        assert graph.value(c, CSVW.title) is not None and graph.value(c, CSVW.datatype) is not None
        assert len(str(graph.value(c, DCTERMS.description))) >= 10 and graph.value(c, CSVW.propertyUrl) is not None
    assert str(graph.value(table, CSVW.url)).endswith(f"?sha256={model.package.sha256}")
    systems = {str(s).rsplit("/", 1)[-1] for s in graph.objects(DS, HEALTH.hasCodingSystem)}
    assert systems == {"SNOMED-CT", "LOINC", "NCIT"}
    for s in graph.objects(DS, HEALTH.hasCodingSystem):
        assert (s, RDF.type, DCTERMS.Standard) in graph and (s, SKOS.inScheme, None) in graph


def test_the_schema_is_cited_on_the_distribution_and_the_page_by_url_and_sha256(graph, model):
    sha = hashlib.sha256((PACKAGE / f"dm-{CT}.xsd").read_bytes()).hexdigest()
    assert model.package.sha256 == sha == model.package.versions["current_sha256"]
    pinned = URIRef(f"https://sdcstudio.axius-sdc.com/dmlib/dm-{CT}.xsd?sha256={sha}")
    dist = graph.value(DS, DCAT.distribution)
    assert (dist, DCTERMS.conformsTo, pinned) in graph and (pinned, RDF.type, DCTERMS.Standard) in graph
    assert (DS, DCTERMS.conformsTo, None) not in graph   # HealthDCAT-AP closes it on the Dataset to the Technical Standard NAL
    assert (DS, FOAF.page, URIRef(f"https://sdcstudio.axius-sdc.com/dmlib/dm-{CT}.xsd")) in graph
    assert str(graph.value(dist, DCAT.accessURL)) == "https://axius-sdc.com"


def test_the_holders_facts_are_declared_and_the_access_body_is_the_publisher(graph):
    publisher = graph.value(DS, DCTERMS.publisher)
    assert graph.value(DS, HEALTH.hdab) == publisher
    cp = graph.value(publisher, CV.contactPoint)
    assert (cp, RDF.type, CV.ContactPoint) in graph and str(graph.value(cp, CV.email)) == "contact@axius-sdc.com"
    kind = graph.value(DS, DCAT.contactPoint)
    assert str(graph.value(kind, VCARD.fn)) == "Axius SDC, Inc. HealthDCAT-AP contact"
    assert int(graph.value(DS, HEALTH.numberOfRecords)) == 9254 and int(graph.value(DS, HEALTH.numberOfUniqueIndividuals)) == 9254
    assert str(graph.value(DS, HEALTH.healthCategory)).endswith("/healthcategories/RQSH")
    assert str(graph.value(DS, DCTERMS.accessRights)).endswith("/access-right/NON_PUBLIC")
    assert len(list(graph.objects(DS, DPV.hasPersonalData))) == 3
    with pytest.raises(DeclaredInputError, match="contact e-mail"):
        load_declared(None, None, "not-an-address")


def test_the_writer_refuses_a_declared_file_without_the_mandatory_health_facts(tmp_path):
    f = tmp_path / "catalog.yaml"
    f.write_text("contact: {name: X, email: x@example.org}\npublisher: {name: X}\ntheme: http://x\naccess_rights: http://x\nlanguage: http://x\naccess_level: NON_PUBLIC\n")
    with pytest.raises(DeclaredInputError, match="applicable_legislation"):
        load_declared(f)
