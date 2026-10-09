# sdc_healthdcat_ap PRD: one SDC model, described in HealthDCAT-AP (Release 8)

**Status:** v0.1, 9 October 2026, DRAFT for Tim. The fourth projection demo of the projections track (ContentStrategy
lane 5.6), its own repository rather than a phase of `sdc_dcat3_ap` (Tim, 9 October: the health market is large
enough to want its own door). No issues are filed on the target's repositories (Tim, 9 October). Order of the track:
CDIF, DCAT-US 3.0, DCAT-AP 3.0.1, now HealthDCAT-AP; schema.org Dataset and Croissant follow.

## 1. Facts

**What HealthDCAT-AP is.** "A domain-specific metadata model designed to support the implementation of the secondary
use framework under the European Health Data Space (EHDS)": the health extension of DCAT-AP 3.0 that the
HealthData@EU central platform's dataset catalogue harvests from member states, EU institutions, third countries and
research infrastructures. Developed under the EHDS2 pilot, then moved from GitHub to the Commission's own
infrastructure: specification at https://data.health.europa.eu/healthdcat-ap/releases/latest/ (**Release 8**,
September 2026, `specStatus` base), repository https://code.europa.eu/healthdataeu/healthdcat-ap (CC BY 4.0), a
hosted validator at https://data.health.europa.eu/validator/. Its distinctive feature is **three access levels**,
`PUBLIC`, `NON_PUBLIC` and `RESTRICTED` (the Access Rights NAL), each with its own mandatory list and its own shape
set; the validator is chosen by level.

**Its shape.** DCAT-AP 3.0.1 (the release ships SEMIC's two shape files unchanged) plus the health extension in
`http://healthdataportal.eu/ns/health#` (`healthdcatap:`), with the Core Public Service vocabulary's contact point
(`cv:`), the Data Privacy Vocabulary (`dpv:`), the Data Quality Vocabulary (`dqv:`), GeoDCAT-AP's custodian and
CSVW. RDF, SHACL-validated, Turtle or RDF/XML at the hosted validator.

**What is mandatory, per access level** (from the release's `context/healthdcat-cardinality-rules.json` and the
validator's shape files):
| Level | Mandatory on the Dataset |
|---|---|
| `PUBLIC`, `RESTRICTED` | title, description, identifier, theme, access rights, applicable legislation, **health category**, **health data access body**, **structured data** (a boolean), **distribution** |
| `NON_PUBLIC` | the same, plus contact point, keyword, provenance, type |

Recommended at every level: analytics, code values, coding system, custodian, **variables**, health theme, legal basis,
number of records, number of unique individuals, personal data, population coverage, publisher, purpose, quality
annotation, retention period, sample, minimum and maximum typical age; non-public adds documentation, frequency,
language, landing page, temporal coverage and relations. A Catalog, a Distribution and a Dataset Series each carry
`dcatap:applicableLegislation` as mandatory. Every `vcard:Kind` needs an e-mail or a URL; `healthdcatap:hdab` is one
`foaf:Agent` with a `cv:ContactPoint`.

**The slots this profile has that the first three did not.**
- **`healthdcatap:hasVariables`**, a `csvw:TableGroup` with `csvw:Table`s and `csvw:Column`s, each column with
  `csvw:name`, `csvw:title`, `csvw:datatype`, `dct:description` and an optional `csvw:propertyUrl`, "a
  machine-readable description of the data variables," expected when `healthdcatap:hasStructuredData` is `true`.
  One column per SDC leaf: this is the data dictionary, inline.
- **`healthdcatap:hasCodingSystem`** from the Coding System NAL (SNOMED-CT, LOINC, NCIT, ICD-10, ATC, UCUM, MeSH,
  HPO, ORPHACODE and 23 more) and **`healthdcatap:hasCodeValues`** as text: where the model's `skos:exactMatch`
  bindings to SNOMED CT, LOINC and NCIT go.
- **`healthdcatap:numberOfRecords`**, **`numberOfUniqueIndividuals`**, **`minTypicalAge`**, **`maxTypicalAge`**,
  **`populationCoverage`**, **`retentionPeriod`**: facts about the collection, which the publisher knows.
- **`dpv:hasPersonalData`** (from the DPV personal-data taxonomy), **`dpv:hasLegalBasis`**, **`dpv:hasPurpose`**:
  what the EHDS secondary-use framework asks a data holder to state.

**Controlled vocabularies** (DG SANTE's, migrated in Release 8 to `https://hdeu-dcat.data.health.europa.eu/resource/authority/`):
health categories (EHDS Article 51: `RQSH` "data from research cohorts, questionnaires and surveys related to
health", `EHRS`, `MRMR`, `HRAD`, `HGPD` and twelve more), health themes (`NONCOMMUNICABLE_DISEASES`, `LIFECOURSE_HEALTH`,
`MENTAL_HEALTH` and seventeen more), health publisher types (`private-company`, `research-academic-org`,
`public-health-institute` and nine more), coding systems, health activities, technical standards; plus the EU NALs
DCAT-AP already requires (data theme `HEAL`, access right, language, file type, dataset type, frequency, corporate
bodies for the publisher).

**Validation.** The release ships the hosted validator's configuration verbatim
(`html/shacl/HealthDCAT-AP_validator/config/rdf-validator/ehds/`): `config.properties` names the shape files per
level. For `non-public`: `shapes/graph-guard.ttl`, `deprecated/deprecateduris.ttl`, `imports/mdr_imports.ttl`,
`imports/imports.ttl`, `ranges/range.ttl`, `shapes/non-public-shapes.ttl`,
`controlled-vocabularies/mdr-vocabularies.shape.ttl`, `recommended/non-public-shapes_recommended.ttl`; the
`catalogue/` directory holds the vocabularies and ontologies the validator preloads as background (the DG SANTE
NALs, the EU NALs, DCAT, Dublin Core, FOAF, vCard, PROV, SPDX, CSVW, DQV, ELI, schema.org). Two judges:
1. **Local, offline, at the pin:** pySHACL over exactly the file set `config.properties` names for the declared
   level, with the `catalogue/` vocabularies loaded as background, plus SEMIC's DCAT-AP 3.0.1 base and range shapes.
   This is the hosted validator's own logic, run here.
2. **The hosted HealthData@EU validator** (https://data.health.europa.eu/validator/, an Interoperability Test Bed
   instance behind a single-page interface with no public REST path found): the sample uploaded by hand at the
   declared level, the report recorded in the README with the date and the validator's version.

**Sources, pinned 9 October 2026.** `code.europa.eu/healthdataeu/healthdcat-ap` at **cd7841f** (2026-09-18,
"Release 8"; CC BY 4.0), `public/releases/release-8/`: `shacl/` (SEMIC's two files), `context/dcat-ap.jsonld` and
`context/healthdcat-cardinality-rules.json`, `html/shacl/HealthDCAT-AP_validator/config/rdf-validator/ehds/` (the
validator configuration, shapes and `catalogue/` background, about 7 MB), `html/examples/` (the per-property
examples and the EPRDR registry examples, Release 8 compliant). Cloned read-only into `source/` (gitignored);
`build/snapshot_healthdcat_ap.py` verifies the pin and copies those into `data/healthdcat-ap-r8-cd7841f/`.

**How HealthDCAT-AP relates to SDC: compose, with the best fit so far.** The profile asks a data holder for exactly
what a governed model already carries: the variables with their definitions and datatypes, the coding systems the
values are bound to, and a per-dataset statement of what is personal data. The writer fills `hasVariables` from the
record's leaves, `hasCodingSystem` from the model's bindings, and leaves the holder's facts (counts, ages, legal
basis, purpose) to declared input.

## 2. Rules

**One deliverable: the writer.** From a published SDC model's package, a HealthDCAT-AP Release 8 Catalog in Turtle and
JSON-LD, one Dataset per model at a declared access level, passing the validator's own shape set for that level
offline and the hosted validator by hand.

**Two kinds of input, kept apart,** as in the three earlier writers. From the package: title, description,
identifier, creator, dates, licence, the schema's URL and SHA-256, every leaf (name, label, datatype, description,
slot) for the variables, the concept systems bound by `skos:exactMatch` for the coding systems, the model's Dublin
Core when written. Declared by the catalog's publisher in `catalog.yaml`, because the profile demands facts only a
data holder has: the access level; the **health data access body** (an agent with a contact point: for a dataset
outside the EU there is none, and the sample names the publisher as the body that grants access and says so); the
applicable legislation (the EHDS regulation's ELI, `http://data.europa.eu/eli/reg/2025/327/oj`, as the profile's
usage note recommends); the health category and theme; the dataset type; the distribution that is the access route
(for non-public data, "a distribution for the Health Data Access Body responsible for providing access"); the
numbers of records and unique individuals, typical ages, population coverage, retention period; personal-data
categories, legal basis and purpose; the publisher's health publisher type; the contact point ("Axius SDC, Inc.
HealthDCAT-AP contact", `contact@axius-sdc.com`); language, data theme (`HEAL`).

**Mapping (the writer's rulebook), beyond what the DCAT-AP writer already does:**
| SDC (package) | HealthDCAT-AP |
|---|---|
| Every leaf of the record, in document order | `healthdcatap:hasVariables` a `csvw:TableGroup` (`dct:title`) with one `csvw:Table` (`dct:title` the model, `csvw:url` the schema's pinned URL) and one `csvw:Column` per leaf: `csvw:name` the element name, `csvw:title` the label, `csvw:datatype` the XSD type's local name, `dct:description`, `csvw:propertyUrl` the library slot or the component IRI; `healthdcatap:hasStructuredData true` |
| `skos:exactMatch` bindings by IRI prefix | `healthdcatap:hasCodingSystem` from the Coding System NAL (`snomed.info/sct` to `SNOMED-CT`, `loinc.org` to `LOINC`, `purl.obolibrary.org/obo/NCIT_` to `NCIT`, and so on; unmapped systems named in `hasCodeValues` as text) |
| The published schema | `dct:conformsTo` a `dct:Standard` and `foaf:page` a `foaf:Document`, as in DCAT-AP; `csvw:url` on the table |
| Immutability | `dct:provenance` (mandatory for non-public) with the permanence statement; `dcat:version` the SHA-256 |
| The sixteen exceptional values | named in the table group's description: every column may carry a typed reason for a missing value |
| Declared input | everything in the paragraph above, each as the shapes require: agents typed with `cv:ContactPoint`, concepts from the NALs, `dpv:` nodes typed, counts as `xsd:nonNegativeInteger`, the retention period a `dct:PeriodOfTime` |

**The sample's access level is `NON_PUBLIC`.** The FAIR Data Demo's records are not published; non-public is the
EHDS case for health data reached through a permit, and the stricter of the three lists. The distribution is the
access route (the contact page), with `dcatap:applicableLegislation` on it as the shapes require.

**Not here.** Dataset series, data services, `RESTRICTED` and `PUBLIC` samples (the writer takes the level as input;
one sample is enough for the proof), the hosted validator through automation (no public API found), the DCAT-AP HVD
annex.

**Attribution.** CC BY 4.0: a NOTICE naming DG SANTE, the HealthData@EU platform and the EHDS2 pilot; the pinned
commit in `data/`.

**No issues filed** on the target's repository (Tim, 9 October). Held privately: the release's `CHANGELOG.md` is
DCAT-AP 3.0.1's changelog verbatim, and `shacl/` at the release root is SEMIC's two files unchanged, so the
HealthDCAT-AP shapes are only under the validator configuration path.

## 3. Scope

### 3.1 First: one model, the same record as the other three
NHANES Participant (`xy8upneajsb8vdcmnve01g6g`) at `NON_PUBLIC`: a Catalog with one Dataset, 153 columns in its
table group, coding systems from the model's bindings, the validator's non-public shape set conforming offline, the
hosted validator's report recorded. The README in the four parts.

### 3.2 Then
- The seven FAIR Data Demo models as one Catalog (declared facts per model).
- `PUBLIC` and `RESTRICTED` on request; any published model.

## 4. Decisions (proposed; open for Tim)
1. **Package name `sdchealthdcatap`**, repository `sdc_healthdcat_ap`, the `sdc_cdif` layout; dev to main by pull
   request with merge commits; CI offline.
2. **Loader, model reader and the DCAT-AP graph builder copied from `sdcdcatap`** (the fourth copy; the shared
   package is its own piece of work after this one is green).
3. **The table group is the data dictionary**, one column per leaf, built from the package; nothing declared.
4. **Coding systems are derived from the bindings** by IRI prefix, with a small fixed table in the writer; a system
   the NAL does not list is named in `hasCodeValues` and not invented into the NAL.
5. **The health data access body for the sample is the publisher**, declared and said so in the README's part 3:
   the field is mandatory and no EU body holds this dataset.
6. **Judge: the validator's own non-public file set, offline, conforming**, warnings listed; the hosted validator
   by hand as the second witness.
7. **Sample declared facts** (open for Tim's numbers): health category `RQSH`, health theme
   `NONCOMMUNICABLE_DISEASES`, dataset type `STATISTICAL`, publisher type `private-company`, personal data
   `dpv-pd:Age`, `dpv-pd:Gender`, `dpv-pd:HealthRecord`, legal basis and purpose as text, number of records and
   unique individuals from the FAIR Data Demo's generation counts, typical ages 0 to 80 (NHANES), retention period
   open.

## 5. Pipeline
`source/` (healthdataeu/healthdcat-ap at cd7841f, read-only), then `build/snapshot_healthdcat_ap.py` (verify the
pin; copy Release 8's shapes, context, validator configuration with its `catalogue/` background, and examples to
`data/healthdcat-ap-r8-cd7841f/`), then `src/sdchealthdcatap/` (`package.py`, `model.py`, `dcatap.py` from
`sdcdcatap`; `healthdcatap.py` adds the health layer and the table group; `cli.py`: `sdchealthdcatap write --package
DIR [--catalog catalog.yaml] --out catalog.ttl [--jsonld catalog.jsonld]`), then `tests/` (pySHACL over the
level's file set with the background loaded; the examples of the release as a sanity check), then the README.
