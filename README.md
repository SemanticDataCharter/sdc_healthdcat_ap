# sdc_healthdcat_ap

One Semantic Data Charter model, described in HealthDCAT-AP.

`sdchealthdcatap` reads a published SDC model's package and writes the `dcat:Catalog` that HealthDCAT-AP, the health
extension of DCAT-AP for the secondary use of health data under the European Health Data Space, asks a data holder to
publish for the HealthData@EU catalogue: one Dataset per model at a declared access level, its variables as a CSVW
table group built from the record's leaves, its coding systems from the model's bindings, and the holder's facts from
declared input. One rdflib graph, serialized as Turtle and as JSON-LD. The output is checked with the HealthData@EU
validator's own shape set for the level, at a pinned commit of the specification's repository.

## 1. What this is, and where it came from

The sample, `samples/nhanes-participant/catalog.ttl` (and `catalog.jsonld`, the same graph), is a Catalog with one
Dataset at the `NON_PUBLIC` access level: the records of **NHANES Participant** (`dm-xy8upneajsb8vdcmnve01g6g`) from
the FAIR Data Demo, a demographic, examination and laboratory record of the National Health and Nutrition
Examination Survey (CDC), 9,254 records, one per participant. The model is public:

- the catalog record: https://sdcstudio.axius-sdc.com/api/v1/catalog/dm/xy8upneajsb8vdcmnve01g6g/
- the schema the records conform to: https://sdcstudio.axius-sdc.com/dmlib/dm-xy8upneajsb8vdcmnve01g6g.xsd
- the Semantic Data Charter: https://semanticdatacharter.com

```
pip install -e ".[fetch]"
sdchealthdcatap write --package samples/nhanes-participant --out catalog.ttl --jsonld catalog.jsonld
sdchealthdcatap write --ct-id xy8upneajsb8vdcmnve01g6g --save-package pkg/ --out catalog.ttl     # any published model, from the public catalog
sdchealthdcatap write --package DIR --catalog my-catalog.yaml --out catalog.ttl                  # a data holder's own declared input
```

**Two kinds of input, kept apart.** From the model's package (its JSON-LD, its schema, the public catalog record and
the published schema versions; no account needed; a model without a package is refused): title, description,
identifier, creator, dates, licence, the schema's URL and SHA-256, **every leaf of the record** for the variables,
**every concept system the model binds to** for the coding systems, and the model's own Dublin Core when the
modeler wrote it. From the data holder, declared in `catalog.yaml` because the profile asks for facts only a holder
has and for values from the DG SANTE and EU vocabularies: the access level, the health data access body, the
applicable legislation, the health category and theme, the dataset type, the distribution that is the access
route, the counts of records and individuals, typical ages, population coverage, personal-data categories, legal
basis, purpose, the publisher's type, the contact point. The package ships the sample's file
(`src/sdchealthdcatap/data/catalog.yaml`); a holder supplies its own.

**The data dictionary is a slot here.** `healthdcatap:hasVariables` takes a `csvw:TableGroup`; the writer builds one
table with one `csvw:Column` per leaf of the record, 153 for NHANES Participant: `csvw:name` the leaf's path in the
record, `csvw:title` its label, `csvw:datatype` its XSD type, `dct:description` its definition, `csvw:propertyUrl`
its library slot (the identifier that says what the variable means wherever it is reused), `dct:identifier` its
element name. `healthdcatap:hasStructuredData` is `true`. `healthdcatap:hasCodingSystem` carries SNOMED CT, LOINC
and NCIT from the Coding System NAL, derived from the model's `skos:exactMatch` bindings by IRI prefix.

What else the Dataset carries:

| | |
|---|---|
| `dct:title`, `dct:description`, `dct:identifier`, `adms:identifier`, `dcat:keyword`, `dcat:landingPage`, `dct:issued`, `dct:modified`, `dct:language`, `dct:license`, `dct:provenance`, `dcat:version` | as the DCAT-AP writer does, from the package |
| `dct:accessRights` | `NON_PUBLIC` from the Access Rights NAL (declared; it selects the validator's shape set) |
| `dcatap:applicableLegislation` | the EHDS Regulation's ELI, `http://data.europa.eu/eli/reg/2025/327/oj`, on the Catalog, the Dataset and the Distribution (declared) |
| `healthdcatap:hdab`, `geodcatap:custodian` | the publisher, a `foaf:Agent` with a `cv:ContactPoint` and a type from the Health Publisher Types NAL (declared; see part 3) |
| `healthdcatap:healthCategory`, `healthdcatap:healthTheme`, `dct:type`, `dcat:theme` | `RQSH` (research cohorts, questionnaires and surveys), noncommunicable diseases, `STATISTICAL`, `HEAL` (declared) |
| `dcat:distribution` | the access route: title, description, `dcat:accessURL`, availability, the legislation, the licence, and `dct:conformsTo` the schema as a `dct:Standard` by its pinned URL |
| `foaf:page` | the schema at its stable URL, described as the data dictionary |
| `healthdcatap:numberOfRecords`, `numberOfUniqueIndividuals`, `minTypicalAge`, `maxTypicalAge`, `populationCoverage` | 9,254; 9,254; 0; 80; the NHANES population (declared) |
| `dpv:hasPersonalData`, `dpv:hasLegalBasis`, `dpv:hasPurpose` | age, gender and health record from the DPV personal-data taxonomy; the basis and purpose as text (declared) |
| `dqv:hasQualityAnnotation` | a `dqv:QualityCertificate` whose body is the schema: every record is validated against it before it exists |

Every NAL concept the graph uses states its scheme (`skos:inScheme`), and every scheme is typed and titled, because
the validator's codelist shapes check membership that way. Every agent is typed and named, with a contact point.

## 2. How to verify it

The tests run the HealthData@EU validator's own configuration from `data/healthdcat-ap-r8-cd7841f/validator/`
(`build/snapshot_healthdcat_ap.py` verifies the pin first): `config.properties` names the shape files per access
level, and the tests load exactly those for the declared level, plus SEMIC's DCAT-AP 3.0.1 shapes as the release
ships them, plus the thirteen vocabularies the codelist shapes name, which the validator preloads as background:

```
pip install -e ".[dev]"
python -m pytest tests -q
```

Result at the pin, `NON_PUBLIC`, in Turtle and in JSON-LD: **0 violations, 12 warnings**. The warnings are the
recommended properties the package does not carry (analytics, retention period, frequency, `dct:conformsTo` on the
Dataset, references, relations, source, temporal coverage and resolution, a sample) and, twice, the Catalog's
publisher outside the EU Corporate Bodies NAL (a company). The committed samples are asserted isomorphic to a fresh
run. The release's own ARCA example, run the same way at `PUBLIC`, passes except where the background we carry
stops (part 4).

Second witness, the hosted HealthData@EU validator at https://data.health.europa.eu/validator/ (upload the Turtle,
choose "HealthDCAT-AP NON_PUBLIC Data"): **to be run by hand and recorded here with the date.** It sits behind a
single-page interface with no public REST path we found, so it is not in the tests.

## 3. What the projection could not say

Declared rather than read from the package, and said so here:
- **The health data access body is the publisher.** The field is mandatory at every level and no EU body holds
  this dataset. The sample names Axius SDC, Inc., with its contact point, as the body that grants access, which is
  true of the FAIR Data Demo and would be replaced by the real body for a dataset inside the EHDS.
- **The applicable legislation is the EHDS Regulation**, as the profile's usage note recommends, for a dataset the
  Regulation does not govern. It is the profile's required way of saying "described for the EHDS framework."
- **The counts, ages, population, personal-data categories, legal basis and purpose** are the holder's statements
  about the FAIR Data Demo's generation run and the NHANES source, not facts the package carries.
- **The distribution is a route, not a file.** The records are not published; the access route is the contact
  page. A holder with a download or a data service replaces it.

Left out: retention period, analytics distribution, sample distribution, frequency, temporal coverage, relations.
The package does not carry them, and the profile recommends rather than requires them.

In the other direction, what the record carries that the catalog entry only points at:
- **The governance envelope is data in every record**, an audit event, a PROV activity and a PROV agent, validated
  with the rest. The columns for them are in the table group, so a reader can see they exist; the values are in the
  records.
- **The schema is bound to each record**, and cited here on the distribution and the page by URL and SHA-256.
- **The reason a value is missing is typed in the record.** The table group's description says every column may
  carry one of sixteen exceptional values; which one applies, and where, is in the record.

## 4. What we learned about HealthDCAT-AP Release 8 and its validator

Implementer's notes from building this against `healthdataeu/healthdcat-ap` at cd7841f on 9 October 2026. They
describe how the artifacts behave, so the next implementer spends the day on their own catalog rather than on these.

- **The validator ships with the release, configured.** `html/shacl/HealthDCAT-AP_validator/config/rdf-validator/ehds/`
  holds `config.properties`, which names the shape files per access level, and the vocabularies and ontologies the
  validator preloads. Running that file set with pySHACL is running the validator's logic; the hosted instance adds
  background knowledge and a web interface.
- **Membership in a vocabulary is checked through `skos:inScheme`.** Every codelist restriction asks the concept for
  `skos:inScheme <the scheme>`, several also ask the scheme to be a typed `skos:ConceptScheme`, and SEMIC's base
  shapes then ask every scheme in the graph for a `dct:title`. The hosted validator preloads the vocabularies, which
  supply the `inScheme`; offline, either load them or state them. The writer states them for every concept it uses,
  and the tests load the thirteen vocabularies anyway, which is why the release's ARCA example passes offline
  except for its language (the Languages NAL is 14 MB and stays out) and its licence type (the ADMS scheme is not
  among the preloads).
- **`dct:conformsTo` on a Dataset is closed to the Technical Standard NAL** (FHIR, OMOP-CDM, openEHR, DICOM, CDISC
  SDTM and about twenty more), at violation level. A schema of one's own cannot go there; the writer cites it on
  the distribution, which has no such restriction, and on `foaf:page`.
- **A health publisher is an agent with exactly one `cv:ContactPoint`** (Core Public Service vocabulary, not vCard)
  and a type from the Health Publisher Types NAL; the Dataset's contact point is a `vcard:Kind` with an e-mail or a
  URL. Two contact-point vocabularies in one document, each where its shape asks.
- **Coding systems must be `dct:Standard`s as well as concepts.** The range shapes ask `healthdcatap:hasCodingSystem`
  for `dct:Standard`; the codelist shapes ask for `skos:inScheme` the Coding System NAL. Both at once.
- **Three path-less property shapes** (a `vcard:Kind`'s "e-mail or URL", a `cv:ContactPoint`'s "e-mail or page",
  written as `sh:or` without `sh:path`) stop pySHACL; the tests drop them and assert both by hand. The range file
  references property shapes it does not define, as DCAT-AP's does.
- **pySHACL reports nested results.** A failed `sh:node` yields the outer result at the property's severity and the
  inner results under `sh:detail` at their own; a Jena-based validator reports the outer one. The tests fold the
  nested ones into their parent, so a warning on the Catalog's publisher stays a warning.
- **The Catalog's publisher is checked twice, against two vocabularies.** DCAT-AP's codelist shape wants the
  Catalog's publisher type from the ADMS publisher-type scheme (a warning); HealthDCAT-AP's wants the Dataset's
  publisher type from the Health Publisher Types NAL (a violation). One agent in both roles satisfies the second and
  warns on the first.
- **`csvw:column` is used as a plain repeated property** in the release's examples and shapes, not as the
  `rdf:List` the CSVW specification defines; column names need to be unique in the table, so a component composed
  three times (the blood pressure readings) gets three columns named by path.
- **Release 8's `CHANGELOG.md` and root `shacl/` are DCAT-AP 3.0.1's**, unchanged; the HealthDCAT-AP shapes live
  only under the validator configuration path.

## Layout

- `src/sdchealthdcatap/`: `package.py`, `model.py` and `dcatap.py` (reused from `sdc_cdif` and `sdc_dcat3_ap`),
  `healthdcatap.py` (the health layer and the table group), `validate.py` (the validator's shape set with pySHACL),
  `cli.py`, `data/catalog.yaml` (the declared input for the sample).
- `data/healthdcat-ap-r8-cd7841f/`: the release's shapes, context, validator configuration with the vocabularies the
  shapes name, and examples, at the pin.
- `samples/nhanes-participant/`: the model's package as fetched and the catalog written from it, in Turtle and JSON-LD.
- `build/snapshot_healthdcat_ap.py`: re-creates `data/` from a read-only clone at the pinned commit.

## Licences

Apache-2.0 (see `LICENSE`, `NOTICE`). The HealthDCAT-AP artifacts in `data/` are CC BY 4.0 and keep that licence here.
