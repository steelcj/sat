#!/usr/bin/env python3
#
# source
#   project: sat
#   path: en/bin/collection/collection-reconcile.py
#
"""collection reconcile — repair a pairing a plain mv broke (ADR-024).

Secondary discovery: when an entity was renamed with plain mv and its
assets kept the old name, reconciliation gathers evidence, proposes the
repair, and — only with --apply — performs it. Dry-run by default; the
loop closes through the operator.

    collection reconcile [path]            # gather evidence, propose
    collection reconcile [path] --apply    # perform the proposed repairs
    collection reconcile --version
"""

import argparse
import sys
from pathlib import Path

from satlib import apply_reconciliation, find_reconcilable


def sat_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def tool_version() -> str:
    try:
        return (sat_root() / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "unknown"


def cmd_reconcile(root: Path, apply: bool) -> int:
    version = tool_version()
    findings = find_reconcilable(root)
    if not findings:
        print("reconcile: clean — every assets directory is paired.")
        return 0

    applied = 0
    for finding in findings:
        print(f"FINDING {finding.kind}: {finding.what}")
        for key, value in finding.evidence.items():
            if value:
                print(f"  {key}: {value}")
        print(f"  means: {finding.means}")
        if finding.proposal is not None:
            print(f"  PROPOSE: {finding.do}")
            if apply:
                apply_reconciliation(finding.proposal, command="collection reconcile",
                                     version=version)
                applied += 1
                print("  APPLIED.")
        else:
            print("  (no confident proposal — reported for the operator)")

    if not apply:
        print("\nNo changes were made (--dry-run). Pass --apply to reconcile.")
        return 1
    print(f"\nReconciled {applied} pairing(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="collection reconcile", description=__doc__)
    parser.add_argument("path", nargs="?", default=".",
                        help="the tree to reconcile (default: .)")
    parser.add_argument("--apply", action="store_true",
                        help="perform the proposed repairs")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()

    if args.version:
        print(f"sat-tools {tool_version()}")
        return 0
    return cmd_reconcile(Path(args.path).expanduser().resolve(), args.apply)


if __name__ == "__main__":
    sys.exit(main())
