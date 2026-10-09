"""sdchealthdcatap: describe published SDC models' governed data records in a HealthDCAT-AP (Release 8) catalog.

    sdchealthdcatap write --package DIR [--package DIR ...] [--catalog catalog.yaml] --out catalog.ttl [--jsonld catalog.jsonld]
    sdchealthdcatap write --ct-id ID [--ct-id ID ...] [--save-package DIR] [--host URL] --out catalog.ttl
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .healthdcatap import DeclaredInputError, build_health_catalog, load_declared
from sdcreader import read_model
from sdcreader import DEFAULT_HOST, PackageError, fetch_package, load_package


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="sdchealthdcatap", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write", help="write a HealthDCAT-AP catalog for one or more models")
    w.add_argument("--package", action="append", default=[], help="directory holding dm-<ct>.jsonld and dm-<ct>.xsd (repeatable)")
    w.add_argument("--ct-id", action="append", default=[], help="published model identifier to fetch from the public catalog (repeatable)")
    w.add_argument("--save-package", help="with --ct-id: save each fetched package under this directory")
    w.add_argument("--host", default=DEFAULT_HOST)
    w.add_argument("--catalog", help="declared input (default: the package's catalog.yaml for the sample)")
    w.add_argument("--contact-name")
    w.add_argument("--contact-email")
    w.add_argument("--out", help="Turtle output file (default stdout)")
    w.add_argument("--jsonld", help="also write JSON-LD here")
    w.add_argument("--date", help="the catalog's date when no model date exists, YYYY-MM-DD (default today)")
    a = p.parse_args(argv)
    if not a.package and not a.ct_id:
        p.error("give at least one --package or --ct-id")
    try:
        declared = load_declared(a.catalog, a.contact_name, a.contact_email)
        pkgs = [load_package(d, host=a.host) for d in a.package]
        for ct in a.ct_id:
            pkgs.append(fetch_package(ct, save_to=Path(a.save_package) / ct if a.save_package else None, host=a.host))
    except (PackageError, DeclaredInputError) as e:
        print(f"sdchealthdcatap: {e}", file=sys.stderr)
        return 2
    g = build_health_catalog([read_model(pkg) for pkg in pkgs], declared, today=date.fromisoformat(a.date) if a.date else None)
    ttl = g.serialize(format="turtle")
    if a.out:
        Path(a.out).write_text(ttl, encoding="utf-8")
        print(f"wrote {a.out}: {len(pkgs)} dataset(s) at {declared['access_level']}, {len(g)} triples", file=sys.stderr)
    else:
        print(ttl)
    if a.jsonld:
        Path(a.jsonld).write_text(g.serialize(format="json-ld", indent=1), encoding="utf-8")
        print(f"wrote {a.jsonld}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
