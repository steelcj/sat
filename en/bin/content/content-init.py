#!/usr/bin/env python3
#
# source
#   project: sat
#   path: en/bin/content/content-init.py
#
"""content init <directory> — mint a content organizing directory's records.

Deliberate setup for a content organizing directory (ADR-025 section 9):
its content role identity (dc:identifier and sat:work), provenance, and
sparse dc.yml, and a refresh of the enclosing archive's children index.
A bare mkdir remains legal forever; this command is the deliberate path.

    content init <directory> [--dry-run]
    content init --version
"""

import argparse
import sys
from pathlib import Path

from satlib import (
    ROLE_ARCHIVE,
    create_content_directory,
    has_identity,
    refresh_children,
)
from satlib.roles import ROLE_CONTENT, has_role


def sat_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def tool_version() -> str:
    try:
        return (sat_root() / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "unknown"


def find_archive(start: Path):
    """Walk up to the enclosing language archive (archive role)."""
    current = start.resolve()
    while True:
        if has_identity(current, ROLE_ARCHIVE):
            return current
        if current.parent == current:
            return None
        current = current.parent


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.directory).expanduser()

    if target.exists() and has_role(target, ROLE_CONTENT, is_dir=True):
        print(f"[CONTENT ERROR] REFUSED: {target} already carries content "
              f"records. Creation is once.", file=sys.stderr)
        return 1

    archive = find_archive(target.parent if not target.exists() else target)
    version = tool_version()

    if args.dry_run:
        print(f"PLAN: mint content records at {target}")
        print(f"  {target}/.{target.name}.assets/{ROLE_CONTENT}/  "
              f"identity (dc:identifier + sat:work), provenance, dc (sparse), fixity")
        if archive is not None:
            print(f"  refresh archive children index at {archive}")
        print("No records were written (--dry-run).")
        return 0

    target.mkdir(parents=True, exist_ok=True)
    record = create_content_directory(target, version=version)
    if archive is not None:
        refresh_children(archive, ROLE_ARCHIVE, command="content init",
                         version=version)

    print(f"CREATED: content directory at {target}")
    print(f"  dc:identifier: {record['dc:identifier']}")
    print(f"  sat:work:      {record['sat:work']}")
    if archive is not None:
        print(f"  archive children index refreshed at {archive}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="content init", description=__doc__)
    parser.add_argument("directory", nargs="?",
                        help="the content organizing directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan without writing")
    parser.add_argument("--version", action="store_true",
                        help="print the tool version and exit")
    args = parser.parse_args()

    if args.version:
        print(f"sat-tools {tool_version()}")
        return 0
    if not args.directory:
        parser.print_usage()
        return 1
    return cmd_init(args)


if __name__ == "__main__":
    sys.exit(main())
