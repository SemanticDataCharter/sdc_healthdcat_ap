"""Run the HealthData@EU validator's own shape set for an access level with pySHACL, from the pinned snapshot.

`config.properties` names the shape files per level; this loads exactly those (plus SEMIC's DCAT-AP base and range
shapes, which the release ships) and returns the report's results by severity. The range file references property
shapes it does not define, which pySHACL refuses; those references are dropped first, as in the DCAT-AP writer.
"""
from __future__ import annotations

from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace, RDF

SH = Namespace("http://www.w3.org/ns/shacl#")


def level_files(snapshot: Path, level: str) -> list[Path]:
    key = {"PUBLIC": "public", "NON_PUBLIC": "non-public", "RESTRICTED": "restricted"}[level.upper()]
    for line in (snapshot / "validator" / "config.properties").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"validator.shaclFile.{key} ="):
            return [snapshot / "validator" / f.strip() for f in line.split("=", 1)[1].split(",")]
    raise ValueError(f"no shape files configured for {level}")


def shapes_graph(snapshot: Path, level: str, with_dcat_ap: bool = True) -> Graph:
    sg = Graph()
    for f in level_files(snapshot, level):
        sg.parse(f, format="turtle")
    if with_dcat_ap:
        sg.parse(snapshot / "shacl" / "dcat-ap-SHACL.ttl", format="turtle")
        sg.parse(snapshot / "shacl" / "ranges.ttl", format="turtle")
    # pySHACL requires sh:path on every property shape: drop the references to shapes the files do not define, and the
    # path-less property shapes written as an sh:or of alternatives (a vcard:Kind's "e-mail or URL", a cv:ContactPoint's
    # "e-mail or page"); the tests assert those two by hand
    for t in [t for t in sg.triples((None, SH.property, None)) if (t[2], SH.path, None) not in sg]:
        sg.remove(t)
    return sg


def background(snapshot: Path) -> Graph:
    """The vocabularies the hosted validator preloads (validator.preloadOwlImports): the codelist shapes check a
    concept's skos:inScheme, which the NAL files supply for concepts the document does not describe itself."""
    g = Graph()
    for f in sorted((snapshot / "validator" / "catalogue").glob("*.rdf")):
        g.parse(f)
    return g


def run(data: Graph, sg: Graph, bg: Graph | None = None):
    """(conforms, results): results as (severity, focus, path, message), sorted. Nested results that pySHACL reports
    under sh:detail of an sh:node failure are folded into their parent, as a Jena-based validator reports them."""
    merged = Graph()
    for t in data:
        merged.add(t)
    if bg is not None:
        for t in bg:
            merged.add(t)
    ok, rg, _ = validate(merged, shacl_graph=sg, inference="none", advanced=True, allow_warnings=True)
    nested = set(rg.objects(None, SH.detail))
    described = set(data.subjects())   # results on background-only nodes (a NAL scheme without a title) are not about the document
    out = []
    for r in rg.subjects(RDF.type, SH.ValidationResult):
        if r in nested:
            continue
        focus = rg.value(r, SH.focusNode)
        if bg is not None and focus not in described:
            continue
        sev = str(rg.value(r, SH.resultSeverity)).split("#")[-1]
        out.append((sev, str(rg.value(r, SH.focusNode)), str(rg.value(r, SH.resultPath) or ""), str(rg.value(r, SH.resultMessage) or "")[:140]))
    conforms = not any(r[0] == "Violation" for r in out)   # about the document: warnings do not fail, background nodes are not ours
    return conforms, sorted(out)
