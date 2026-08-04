#!/usr/bin/env python3
#
# source
#   project: sat
#   path: en/bin/collection/collection-init.py
#
"""collection init <path> — create a single-role collection (ADR-026).

Creates an additional collection inside an existing instance: its
collection role records, its declared archives, its children index, and
its sparse dc.yml inheriting through the cascade. It refreshes the
instance role's children index to record the new collection. There is no
~/.config preseed below the instance — the cascade is the preseed.

    collection init <path> [--language TAG]... [--dry-run] [--offline-confirm]
    collection init --version
"""

import argparse
import sys
from pathlib import Path

from satlib import (
    CacheUnavailableError,
    ROLE_COLLECTION,
    ROLE_SAT,
    RegistryCache,
    create_archive,
    create_collection_role,
    has_identity,
    iana_source,
    plan_archive,
    refresh_children,
    resolve_entity,
    validate_expression,
    verify,
)
from satlib.language import SubtagRegistry

CACHE_PATH = Path.home() / ".config" / "sat" / "cache" / "iana-registry.txt"


def sat_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def tool_version() -> str:
    try:
        return (sat_root() / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "unknown"


def find_instance(start: Path):
    """Walk up from a path to the enclosing SAT instance (sat role)."""
    current = start.resolve()
    while True:
        if has_identity(current, ROLE_SAT):
            return current
        if current.parent == current:
            return None
        current = current.parent


def resolve_registry(offline_confirmed: bool):
    cache = RegistryCache(iana_source(CACHE_PATH))
    try:
        result = cache.resolve(offline_confirmed=offline_confirmed)
    except CacheUnavailableError as exc:
        print(f"[COLLECTION ERROR] {exc}", file=sys.stderr)
        return None
    if result.content is None:
        return None
    return SubtagRegistry.parse(result.content)


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.path).expanduser()

    if has_identity(target, ROLE_COLLECTION):
        print(f"[COLLECTION ERROR] REFUSED: {target} already carries a "
              f"collection identity. Creation is once. No records were "
              f"written.", file=sys.stderr)
        return 1

    instance = find_instance(target.parent if not target.exists() else target)
    if instance is None:
        print(f"[COLLECTION ERROR] {target} is not inside a SAT instance. "
              f"Run sat init first, or point at a path within an instance.",
              file=sys.stderr)
        return 1

    registry = resolve_registry(args.offline_confirm)
    if registry is None:
        print("[COLLECTION ERROR] Language registry unavailable; cannot "
              "validate archives.", file=sys.stderr)
        return 1

    validations = []
    for expression in (args.language or []):
        validation = validate_expression(expression, registry)
        if not validation.valid:
            print(f"[COLLECTION ERROR] {expression}: invalid language "
                  f"expression.", file=sys.stderr)
            return 1
        validations.append(validation)

    version = tool_version()

    if args.dry_run:
        print(f"PLAN: create collection at {target} (instance: {instance})")
        print(f"  {target}/.{target.name}.assets/{ROLE_COLLECTION}/  "
              f"identity, provenance, dc (sparse), collection.yml, children, fixity")
        for v in validations:
            print(f"  {target}/{v.dc_language_bcp47}/  archive")
        print(f"  refresh instance children index at {instance}")
        print("No records were written (--dry-run).")
        return 0

    target.mkdir(parents=True, exist_ok=True)
    create_collection_role(target, version=version,
                           registry_file_date=registry.file_date)
    archives = []
    for validation in validations:
        archive = create_archive(
            plan_archive(target, validation, tool="collection init",
                         tool_version=version,
                         registry_file_date=registry.file_date,
                         title=f"{target.name} ({validation.dc_language_bcp47})"),
            command="collection init", version=version)
        archives.append(archive)
    refresh_children(target, ROLE_COLLECTION, command="collection init",
                     version=version)
    # The instance now has one more collection.
    refresh_children(instance, ROLE_SAT, command="collection init",
                     version=version)

    print(f"CREATED: collection at {target}")
    for archive in archives:
        report = verify(resolve_entity(instance, archive))
        state = "clean" if report.clean else (
            "unresolved: " + ", ".join(report.unresolved))
        print(f"  {archive.name}: [{state}]")
    print(f"  instance children index refreshed at {instance}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="collection init", description=__doc__)
    parser.add_argument("path", nargs="?", help="target directory for the collection")
    parser.add_argument("--language", action="append",
                        help="language tag for an archive (repeatable)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan without writing")
    parser.add_argument("--offline-confirm", action="store_true",
                        help="proceed without registry validation")
    parser.add_argument("--version", action="store_true",
                        help="print the tool version and exit")
    args = parser.parse_args()

    if args.version:
        print(f"sat-tools {tool_version()}")
        return 0
    if not args.path:
        parser.print_usage()
        return 1
    return cmd_init(args)


if __name__ == "__main__":
    sys.exit(main())
