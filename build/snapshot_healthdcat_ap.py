#!/usr/bin/env python3
"""Copy HealthDCAT-AP Release 8's shapes, context, validator configuration and the vocabularies the shapes reference
from the read-only clone in source/ into data/, named by the pinned commit (docs/design/sdc-healthdcat-ap-PRD.md,
section 1). Refuses a clone that is not at the pin.

    python build/snapshot_healthdcat_ap.py [--source DIR] [--check]
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIN = "cd7841f"
RELEASE = "release-8"
REPO = "healthdcat-ap"
CONFIG = "html/shacl/HealthDCAT-AP_validator/config/rdf-validator/ehds"
CONFIG_DIRS = ["shapes", "ranges", "imports", "controlled-vocabularies", "recommended", "deprecated"]
#: the background vocabularies the codelist shapes name (the large NALs for languages, corporate bodies, countries and
#: places, and the ontologies, stay out: the writer states skos:inScheme for every concept it uses)
VOCABULARIES = ["healthcategories.rdf", "health-theme.rdf", "health-activity.rdf", "coding-system.rdf", "standard.rdf",
                "publisher-type.rdf", "data-theme.rdf", "access-right.rdf", "dataset-types.rdf", "planned-availability.rdf",
                "distribution-status.rdf", "frequencies.rdf", "filetypes.rdf", "countries.rdf"]


def main(check_only: bool, source: Path) -> int:
    repo = source / REPO
    if not repo.is_dir():
        print(f"{REPO}: not cloned (git clone --quiet https://code.europa.eu/healthdataeu/healthdcat-ap.git {repo}; git -C {repo} checkout {PIN})")
        return 1
    at = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short=7", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    if at != PIN:
        print(f"{REPO}: at {at}, pinned {PIN}; re-pinning is a deliberate step (PRD section 1)")
        return 1
    print(f"{REPO}: {PIN} ok")
    if check_only:
        return 0
    rel = repo / "public" / "releases" / RELEASE
    out = ROOT / "data" / f"healthdcat-ap-r8-{PIN}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for d in ("shacl", "context"):
        shutil.copytree(rel / d, out / d)
    cfg = rel / CONFIG
    shutil.copy2(cfg / "config.properties", out / "validator" / "config.properties") if (out / "validator").mkdir() is None else None
    for d in CONFIG_DIRS:
        shutil.copytree(cfg / d, out / "validator" / d, ignore=shutil.ignore_patterns("*.pdf"))
    (out / "validator" / "catalogue").mkdir()
    for v in VOCABULARIES:
        shutil.copy2(cfg / "catalogue" / v, out / "validator" / "catalogue" / v)
    ex = out / "examples"
    ex.mkdir()
    for f in (rel / "html" / "examples").glob("*.ttl"):
        shutil.copy2(f, ex / f.name)
    (ex / "EPRDR").mkdir()
    for f in (rel / "html" / "examples" / "EPRDR").glob("*.ttl"):
        shutil.copy2(f, ex / "EPRDR" / f.name)
    shutil.copy2(repo / "LICENSE", out / "LICENSE")
    shutil.copy2(repo / "notice.md", out / "notice.md")
    print(f"snapshot: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    src = Path(args[args.index("--source") + 1]) if "--source" in args else ROOT / "source"
    sys.exit(main("--check" in args, src))
