#!/usr/bin/env python3
#
# source
#   project: sat
#   path: en/bin/sat/sat-init.py
#
"""sat init — instantiate a SAT instance, whole chain (ADR-026).

One command produces a working whole: the instance sat role, the dual-
role collection role (with collection.yml), the language archives, the
children indexes at every parent, and — because a fresh install is a
standing integration test — seeded documentation, the example
collection, and staged samples.

The instantiation preseed (~/.config/sat/instantiate-preseed.yml) is
read once if present; command-line arguments override it; absent, sat
init behaves exactly as today, tripwires armed. Below the instance
there is no preseed: the cascade is the preseed.

    sat init --version
    sat init <path> [--language TAG]... [--dry-run] [--offline-confirm]
"""

import argparse
import sys
from pathlib import Path

from satlib import (
    CacheUnavailableError,
    DEFAULT_COLLECTIONS_HOME,
    ROLE_COLLECTION,
    ROLE_SAT,
    RegistryCache,
    create_archive,
    create_collection_role,
    create_instance_role,
    discover,
    has_identity,
    has_provenance,
    iana_source,
    plan_archive,
    refresh_children,
    resolve_entity,
    seed_documentation,
    seed_example_collection,
    validate_expression,
    verify,
)
from satlib.language import SubtagRegistry

CONFIG_DIR = Path.home() / ".config" / "sat"
CACHE_PATH = CONFIG_DIR / "cache" / "iana-registry.txt"
PRESEED_PATH = CONFIG_DIR / "instantiate-preseed.yml"


def sat_root() -> Path:
    """en/bin/sat/sat-init.py -> three parents above en/."""
    return Path(__file__).resolve().parent.parent.parent.parent


def tool_version() -> str:
    try:
        return (sat_root() / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "unknown"


def read_preseed() -> dict:
    """The instantiation preseed, or {} when absent (ADR-026 section 4).

    Absent is not an error: sat init behaves exactly as today, tripwires
    armed. Present, its answers arrive already resolved in the instance
    role's dc.yml.
    """
    if not PRESEED_PATH.is_file():
        return {}
    import yaml
    try:
        return yaml.safe_load(PRESEED_PATH.read_text("utf-8")) or {}
    except Exception as exc:  # a malformed preseed must not corrupt creation
        print(f"[SAT WARNING] could not read {PRESEED_PATH}: {exc}; "
              f"proceeding as if absent.", file=sys.stderr)
        return {}


def resolve_registry(offline_confirmed: bool):
    cache = RegistryCache(iana_source(CACHE_PATH))
    try:
        result = cache.resolve(offline_confirmed=offline_confirmed)
    except CacheUnavailableError as exc:
        print(f"[SAT ERROR] {exc}", file=sys.stderr)
        print("  Pass --offline-confirm to proceed without validation, or abort.",
              file=sys.stderr)
        sys.exit(1)
    for warning in result.warnings:
        print(f"[SAT WARNING] {warning}", file=sys.stderr)
    if result.content is None:
        return None
    print(f"registry:  {result.status.value} (File-Date: {result.file_date})")
    return SubtagRegistry.parse(result.content)


def default_language(registry: SubtagRegistry):
    found = discover(Path(__file__), registry)
    return found.context.dc_language_bcp47 if found.found else None


def _resolve_languages(args, preseed, registry):
    """Command-line overrides preseed overrides self-discovery."""
    if args.language:
        return args.language
    if preseed.get("languages"):
        return list(preseed["languages"])
    discovered = default_language(registry)
    if discovered is None:
        print("[SAT ERROR] No language declared and self-discovery found no "
              "language context. Pass --language TAG.", file=sys.stderr)
        return None
    print(f"language:  {discovered} (tool self-discovery)")
    return [discovered]


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.path).expanduser()

    if has_identity(target, ROLE_SAT):
        print(f"[SAT ERROR] REFUSED: {target}/.{target.name}.assets/{ROLE_SAT}/"
              f"identity.yml exists. An instance is instantiated once "
              f"(ADR-021). No records were written.", file=sys.stderr)
        return 1
    if has_provenance(target, ROLE_SAT):
        print(f"[SAT ERROR] REFUSED: {target}/.{target.name}.assets/{ROLE_SAT}/"
              f"provenance.yml exists. Re-initialisation is an error, not a "
              f"merge. No records were written.", file=sys.stderr)
        return 1

    registry = resolve_registry(args.offline_confirm)
    if registry is None:
        print("[SAT ERROR] Unvalidated operation is not yet supported by this "
              "CLI. Restore network access or provide a registry cache.",
              file=sys.stderr)
        return 1

    preseed = read_preseed()
    if PRESEED_PATH.is_file():
        print(f"preseed:   {PRESEED_PATH}")

    languages = _resolve_languages(args, preseed, registry)
    if languages is None:
        return 1

    validations = []
    for expression in languages:
        validation = validate_expression(expression, registry)
        if not validation.valid:
            problems = validation.errors + [
                e for c in validation.components for e in c.errors]
            print(f"[SAT ERROR] {expression}: " + "; ".join(problems),
                  file=sys.stderr)
            return 1
        validations.append(validation)

    creator = preseed.get("dc:creator")
    publisher = preseed.get("dc:publisher")
    rights = preseed.get("dc:rights")
    collections_home = preseed.get("collections_home", DEFAULT_COLLECTIONS_HOME)
    seed = preseed.get("seed") or {}
    want_docs = seed.get("documentation", True)
    want_samples = seed.get("sample_content", True)
    version = tool_version()

    if args.dry_run:
        return _plan(target, validations, collections_home, want_docs,
                     want_samples, registry.file_date)

    # --- The chain (ADR-026 section 1) ---
    target.mkdir(parents=True, exist_ok=True)
    create_instance_role(
        target, version=version, creator=creator, publisher=publisher,
        rights=rights, collections_home=collections_home,
        registry_file_date=registry.file_date)
    create_collection_role(target, version=version, command="sat init",
                           registry_file_date=registry.file_date)

    archives = []
    for validation in validations:
        archive = create_archive(
            plan_archive(target, validation, tool="sat init",
                         tool_version=version,
                         registry_file_date=registry.file_date,
                         title=f"SAT Documentation ({validation.dc_language_bcp47})"),
            command="sat init", version=version)
        archives.append(archive)
    refresh_children(target, ROLE_COLLECTION, command="sat init", version=version)

    if want_docs and archives:
        seed_documentation(archives[0], version=version,
                           registry_file_date=registry.file_date)

    seed_example_collection(
        target, validations, collections_home=collections_home,
        version=version, sample_content=want_samples,
        registry_file_date=registry.file_date)

    # The instance indexes its collections last: the dual-role collection
    # and the seeded test-collection now both exist.
    refresh_children(target, ROLE_SAT, command="sat init", version=version)

    _report(target, archives, collections_home, registry.file_date)
    return 0


def _plan(target, validations, collections_home, want_docs, want_samples,
          file_date):
    name = target.name
    print(f"PLAN: instantiate SAT instance at {target}")
    print(f"  {target}/.{name}.assets/{ROLE_SAT}/          "
          f"identity, provenance, dc, children, fixity (instance role)")
    print(f"  {target}/.{name}.assets/{ROLE_COLLECTION}/   "
          f"identity, provenance, dc (sparse), collection.yml, children, fixity")
    for validation in validations:
        print(f"  {target}/{validation.dc_language_bcp47}/  archive: "
              f"{validation.dc_language} / {validation.dc_language_bcp47}")
    if want_docs:
        print(f"  {target}/{validations[0].dc_language_bcp47}/docs/  "
              f"seeded documentation")
    print(f"  {target}/{collections_home}/test-collection/  "
          f"example collection (always)"
          + (", staged samples" if want_samples else ""))
    print(f"registry File-Date: {file_date}")
    print("No records were written (--dry-run).")
    return 0


def _report(target, archives, collections_home, file_date):
    print(f"INSTANTIATED: SAT instance at {target}")
    unresolved = False
    for archive in archives:
        record = resolve_entity(target, archive)
        report = verify(record)
        state = "clean" if report.clean else (
            "unresolved: " + ", ".join(report.unresolved))
        print(f"  {archive.name}: [{state}]")
        unresolved = unresolved or not report.clean
    print(f"  {collections_home}/test-collection/  seeded")
    print(f"registry File-Date: {file_date}")
    if unresolved:
        print("NOTE: <calculated> fields remain; set instance defaults in "
              f"{target}/.{target.name}.assets/{ROLE_SAT}/dc.yml")


def main() -> int:
    parser = argparse.ArgumentParser(prog="sat init", description=__doc__)
    parser.add_argument("path", nargs="?", help="target directory for the instance")
    parser.add_argument("--language", action="append",
                        help="language tag for an archive (repeatable)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan without writing")
    parser.add_argument("--offline-confirm", action="store_true",
                        help="explicit consent to proceed without registry validation")
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
