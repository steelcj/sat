#!/usr/bin/env python3
#
# source
#   project: sat
#   path: en/bin/collection/collection-mv.py
#
"""collection mv <old> <new> — rename a collection, safely (ADR-024).

The easy path is also the safe path: this renames the collection and its
assets directory as one act and maintains the records that reference
them — sat:name and the instance's children index. Digests never change.
Plain mv remains legal; reconciliation repairs it when used. Dry-run by
default.

    collection mv <old-path> <new-name> [--apply]
    collection mv --version
"""

import argparse
import sys
from pathlib import Path

from satlib import ROLE_SAT, has_identity, move_collection


def sat_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def tool_version() -> str:
    try:
        return (sat_root() / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "unknown"


def find_instance(start: Path):
    current = start.resolve()
    while True:
        if has_identity(current, ROLE_SAT):
            return current
        if current.parent == current:
            return None
        current = current.parent


def main() -> int:
    parser = argparse.ArgumentParser(prog="collection mv", description=__doc__)
    parser.add_argument("old", nargs="?", help="the collection directory")
    parser.add_argument("new", nargs="?", help="the new collection name")
    parser.add_argument("--apply", action="store_true", help="perform the rename")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()

    if args.version:
        print(f"sat-tools {tool_version()}")
        return 0
    if not args.old or not args.new:
        parser.print_usage()
        return 1

    old = Path(args.old).expanduser().resolve()
    instance = find_instance(old.parent)
    if instance is None:
        print(f"[COLLECTION ERROR] {old} is not inside a SAT instance.",
              file=sys.stderr)
        return 1

    plan = move_collection(old, args.new, parent=instance,
                           command="collection mv", version=tool_version(),
                           apply=args.apply)
    verb = "MOVED" if args.apply else "PLAN"
    print(f"{verb}: collection {old.name} -> {args.new}")
    for line in plan:
        print(f"  {line}")
    if not args.apply:
        print("No changes were made (--dry-run). Pass --apply to rename.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
