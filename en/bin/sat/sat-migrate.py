#!/usr/bin/env python3
#
# source
#   project: sat
#   path: en/bin/sat/sat-migrate.py
#
"""sat migrate — move a 0.5.0/0.6.0 tree into role directories (ADR-025).

One-time, dry-run by default. Flat identity/provenance/dc/language
records move into their tier's role directory; the dual-role root's
collection role is minted fresh; the old sat/ work index is rebuilt in
the collection role; children indexes are built and fixity recorded.

    sat migrate <path>            # print the PLAN, write nothing
    sat migrate <path> --apply    # perform the migration
    sat migrate --version
"""

import argparse
import sys
from pathlib import Path

from satlib import migrate, plan_migration


def sat_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def tool_version() -> str:
    try:
        return (sat_root() / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "unknown"


def cmd_migrate(args: argparse.Namespace) -> int:
    target = Path(args.path).expanduser()
    if not target.is_dir():
        print(f"[SAT ERROR] {target} is not a directory.", file=sys.stderr)
        return 1

    version = tool_version()
    if args.apply:
        lines = migrate(target, version=version, apply=True)
        header = f"MIGRATED: {target} into role directories"
    else:
        lines = plan_migration(target)
        header = f"PLAN: migrate {target} into role directories"

    print(header)
    for line in lines:
        print(f"  {line}")
    if not args.apply:
        print("No records were written (--dry-run). Pass --apply to migrate.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="sat migrate", description=__doc__)
    parser.add_argument("path", nargs="?", help="the instance tree to migrate")
    parser.add_argument("--apply", action="store_true",
                        help="perform the migration (default is dry-run)")
    parser.add_argument("--version", action="store_true",
                        help="print the tool version and exit")
    args = parser.parse_args()

    if args.version:
        print(f"sat-tools {tool_version()}")
        return 0
    if not args.path:
        parser.print_usage()
        return 1
    return cmd_migrate(args)


if __name__ == "__main__":
    sys.exit(main())
