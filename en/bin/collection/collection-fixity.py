#!/usr/bin/env python3
#
# source
#   project: sat
#   path: en/bin/collection/collection-fixity.py
#
"""collection fixity — check recorded digests, or export the manifest (ADR-027).

Checking is deliberate and never writes; findings are classified. Export
derives a SHA256SUMS manifest from the content sidecars for coreutils and
rclone.

    collection fixity --check [path]     # compare digests, report findings
    collection fixity --export [path]    # print SHA256SUMS to stdout
    collection fixity --version
"""

import argparse
import os
import sys
from pathlib import Path

from satlib.assets import entity_for, entity_name_for, is_assets_name
from satlib.fixity import FIXITY_RECORD, check_fixity, format_sha256sums, read_fixity
from satlib.roles import ROLE_CONTENT, ROLES


def sat_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def tool_version() -> str:
    try:
        return (sat_root() / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "unknown"


def _iter_fixity_targets(root: Path):
    """Yield (entity, role, is_dir, content_path) for every fixity record.

    Walks content space and stops at each assets directory rather than
    recursing into it: role directories and records are never descended.
    """
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda e: e.name)
        except (FileNotFoundError, NotADirectoryError):
            continue
        for entry in entries:
            if not entry.is_dir(follow_symlinks=False):
                continue
            if not is_assets_name(entry.name):
                if not entry.name.startswith("."):
                    stack.append(Path(entry.path))
                continue
            assets_dir = Path(entry.path)          # an assets dir: do not descend
            if entity_name_for(assets_dir.name) is None:
                continue
            try:
                entity = entity_for(assets_dir)
            except ValueError:
                continue
            is_dir = entity.is_dir()
            for role in ROLES:
                if (assets_dir / role / FIXITY_RECORD).is_file():
                    content_path = entity if (role == ROLE_CONTENT and not is_dir) else None
                    yield entity, role, is_dir, content_path


def cmd_check(root: Path) -> int:
    findings = []
    for entity, role, is_dir, content_path in _iter_fixity_targets(root):
        findings.extend(check_fixity(entity, role, content_path=content_path,
                                     is_dir=is_dir))
    if not findings:
        print("fixity: clean — every recorded digest matches.")
        return 0
    hard = 0
    for f in findings:
        marker = "HARD" if f.hard else "soft"
        print(f"[{marker}] {f.kind}: {f.target}")
        print(f"    means: {f.means}")
        if f.remedy:
            print(f"    do:    {f.remedy}")
        hard += 1 if f.hard else 0
    print(f"\n{len(findings)} finding(s); {hard} hard. No changes were made.")
    return 1


def cmd_export(root: Path) -> int:
    entries = []
    for entity, role, is_dir, content_path in _iter_fixity_targets(root):
        if content_path is None:
            continue
        body = read_fixity(entity, role, is_dir=is_dir) or {}
        content = body.get("content")
        if content and content.get("digest"):
            rel = content_path.relative_to(root)
            entries.append((content["digest"], str(rel)))
    sys.stdout.write(format_sha256sums(sorted(entries, key=lambda e: e[1])))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="collection fixity", description=__doc__)
    parser.add_argument("path", nargs="?", default=".",
                        help="the tree to check or export (default: .)")
    parser.add_argument("--check", action="store_true", help="compare digests")
    parser.add_argument("--export", action="store_true", help="print SHA256SUMS")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()

    if args.version:
        print(f"sat-tools {tool_version()}")
        return 0
    root = Path(args.path).expanduser().resolve()
    if args.export:
        return cmd_export(root)
    if args.check:
        return cmd_check(root)
    parser.print_usage()
    return 1


if __name__ == "__main__":
    sys.exit(main())
