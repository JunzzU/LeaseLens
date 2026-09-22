"""Command line entry point.

    leaselens-pipeline import rentsafe    download + load registration and both evaluation files
    leaselens-pipeline import permits     download + load active and cleared permits (needs rentsafe first)
    leaselens-pipeline import all         both, in that order
    leaselens-pipeline report             data-quality summary of what is loaded (Markdown)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .db import REPO_ROOT, SchemaNotReady, check_schema, connect
from .download.fetch import SOURCES, fetch
from .loading.evaluations import load_evaluations
from .loading.permits import load_permits
from .loading.registration import load_registration
from .report import quality_report

# Registration first: it is the authority for building details. Older evaluations before newer.
RENTSAFE = [("registration", load_registration),
            ("evaluations_pre2023", load_evaluations),
            ("evaluations_v2023", load_evaluations)]
# Active before cleared, so a permit that has moved files ends up recorded as cleared.
PERMITS = [("permits_active", load_permits),
           ("permits_cleared", load_permits)]
GROUPS = {"rentsafe": RENTSAFE, "permits": PERMITS, "all": RENTSAFE + PERMITS}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="leaselens-pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import")
    imp.add_argument("group", choices=sorted(GROUPS))
    imp.add_argument("--raw-dir", type=Path, default=REPO_ROOT / "raw")
    sub.add_parser("report")
    args = parser.parse_args(argv)

    conn = connect()
    try:
        check_schema(conn)
    except SchemaNotReady as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.command == "report":
        print(quality_report(conn))
        return 0

    failed = False
    for key, loader in GROUPS[args.group]:
        result = loader(conn, fetch(SOURCES[key], args.raw_dir))
        print(result.report(), end="\n\n")
        if result.status == "failed":
            failed = True
            break   # later files depend on earlier ones
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
