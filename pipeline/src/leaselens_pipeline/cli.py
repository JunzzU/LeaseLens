"""Command line entry point.

    leaselens-pipeline migrate            apply database/migrations
    leaselens-pipeline import rentsafe    download + load registration and both evaluation files
    leaselens-pipeline report             data-quality summary of what is loaded (Markdown)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .db import REPO_ROOT, connect, migrate
from .download.fetch import SOURCES, fetch
from .loading.evaluations import load_evaluations
from .loading.registration import load_registration
from .report import quality_report

# Registration first: it is the authority for building details. Older evaluations before newer.
RENTSAFE = [("registration", load_registration),
            ("evaluations_pre2023", load_evaluations),
            ("evaluations_v2023", load_evaluations)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="leaselens-pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate")
    imp = sub.add_parser("import")
    imp.add_argument("group", choices=["rentsafe"])
    imp.add_argument("--raw-dir", type=Path, default=REPO_ROOT / "raw")
    sub.add_parser("report")
    args = parser.parse_args(argv)

    conn = connect()
    if args.command == "migrate":
        applied = migrate(conn)
        print("applied: " + (", ".join(applied) if applied else "nothing (up to date)"))
        return 0
    if args.command == "report":
        print(quality_report(conn))
        return 0

    migrate(conn)
    failed = False
    for key, loader in RENTSAFE:
        result = loader(conn, fetch(SOURCES[key], args.raw_dir))
        print(result.report(), end="\n\n")
        if result.status == "failed":
            failed = True
            break   # later files depend on earlier ones
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
