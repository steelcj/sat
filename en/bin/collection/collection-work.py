#!/usr/bin/env python3
#
# source
#   project: sat
#   path: en/bin/collection/collection-work.py
#
"""collection work — work assignment, joining, and the work index (ADR-022).

A thin caller over satlib.work (ADR-019): every mechanism lives in
satlib; this tool discovers the collection root, resolves addresses,
narrates what it did, and delegates. Work and index operations are
collection-tier acts (ADR-022 tier-permissions), invoked here through
bin/collection/.

    collection work join <document> --expression-of <value> [--apply]
    collection work find <term>
    collection work index --rebuild | --check

join is dry-run by default (the house rule): it prints the plan and
writes nothing until --apply. The index is derived and disposable;
--rebuild writes it from the canonical sidecars, --check rebuilds and
reports every divergence as a finding.
"""

import argparse
import sys
from pathlib import Path

from satlib import (
    DuplicateExpressionError,
    RegistryCache,
    UnresolvedAddressError,
    WORK_FIELD,
    WorkError,
    compare_index,
    iana_source,
    join_work,
    read_document_identity,
    read_work_index,
    read_yaml_asset,
    rebuild_index_data,
    resolve_expression_of,
    update_index_for_document,
    write_work_index,
)
from satlib.discovery import is_language_root
from satlib.language import SubtagRegistry
from satlib.registry import CacheUnavailableError

CACHE_PATH = Path.home() / ".config" / "sat" / "cache" / "iana-registry.txt"

JOIN_COMMAND = "collection work join --apply"
REBUILD_COMMAND = "collection work index --rebuild"


# ---------------------------------------------------------------------------
# Version and registry: the same sources the other tiers read
# ---------------------------------------------------------------------------

def sat_root() -> Path:
    """The artifact root from this script's resolved position:
    en/bin/collection/collection-work.py -> four parents above."""
    return Path(__file__).resolve().parent.parent.parent.parent


def tool_version() -> str:
    """Read the artifact's VERSION — never a literal in code (as sat-init)."""
    try:
        return (sat_root() / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "unknown"


def resolve_registry(offline_confirmed: bool) -> SubtagRegistry:
    """Resolve the IANA subtag registry through the shared cache.

    A fresh cache resolves without touching the network. The registry
    is what tells a language archive directory apart from any other
    directory, so collection-root discovery depends on it.
    """
    cache = RegistryCache(iana_source(CACHE_PATH))
    try:
        result = cache.resolve(offline_confirmed=offline_confirmed)
    except CacheUnavailableError as exc:
        print(f"[COLLECTION ERROR] {exc}", file=sys.stderr)
        print("  Restore network access or run sat init to seed the cache.",
              file=sys.stderr)
        sys.exit(1)
    for warning in result.warnings:
        print(f"[COLLECTION WARNING] {warning}", file=sys.stderr)
    if result.content is None:
        print("[COLLECTION ERROR] The subtag registry is unavailable; the "
              "collection root cannot be discovered without it.",
              file=sys.stderr)
        sys.exit(1)
    return SubtagRegistry.parse(result.content)


# ---------------------------------------------------------------------------
# Collection-root discovery (existing registry-backed machinery, not assumption)
# ---------------------------------------------------------------------------

def discover_collection_root(start: Path,
                             registry: SubtagRegistry) -> Path:
    """Walk upward to the collection root: the nearest ancestor holding a
    language archive as a child.

    A collection is the parent of its language archives (ADR-011); a
    language archive is a directory whose name is a registry-valid
    expression (satlib.discovery). Given a document the walk begins at
    its directory; given the working directory it begins there — so a
    join names its document while index and find run from the root.
    Discovered, never assumed.
    """
    resolved = start.resolve()
    node = resolved if resolved.is_dir() else resolved.parent
    while True:
        try:
            children = sorted(node.iterdir())
        except OSError:
            children = []
        for child in children:
            if child.is_dir() and is_language_root(child, registry) is not None:
                return node
        if node.parent == node:
            print(f"[COLLECTION ERROR] No collection root found at or above "
                  f"{start}: no ancestor holds a language archive.",
                  file=sys.stderr)
            sys.exit(1)
        node = node.parent


def _count_expressions(root: Path, work: str,
                       registry: SubtagRegistry) -> int:
    """How many documents in the collection carry this work as sat:work.

    A direct sidecar count, independent of index freshness — the plan's
    'a work of one' must be true when it is printed, not when the index
    was last built.
    """
    count = 0
    for archive in sorted(root.iterdir()):
        if not archive.is_dir() or is_language_root(archive, registry) is None:
            continue
        for path in archive.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if any(part.startswith(".") for part in rel.parts):
                continue
            try:
                record = read_document_identity(path)
            except WorkError:
                continue
            if record.get(WORK_FIELD) == work:
                count += 1
    return count


def _title_for(root: Path, rel_path: str) -> str:
    """Best-effort dc:title from the expression's dc.yml sidecar, or ''.

    'where cheap' (ADR-022): a present dc.yml is read; anything else is
    left to dc.yml's own tooling and the path speaks for the match.
    """
    try:
        dc = read_yaml_asset(root / rel_path, "dc.yml", is_dir=False)
    except OSError:
        return ""
    return (dc or {}).get("dc:title", "") if isinstance(dc, dict) else ""


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_join(args: argparse.Namespace) -> int:
    registry = resolve_registry(args.offline_confirm)
    document = Path(args.document).resolve()
    if not document.is_file():
        print(f"[COLLECTION ERROR] No such document: {args.document}",
              file=sys.stderr)
        return 1
    root = discover_collection_root(document, registry)

    try:
        target = resolve_expression_of(args.expression_of, root)
    except (UnresolvedAddressError, WorkError) as exc:
        print(f"[COLLECTION ERROR] {exc}", file=sys.stderr)
        return 1

    try:
        record = read_document_identity(document)
    except WorkError as exc:
        print(f"[COLLECTION ERROR] {exc}", file=sys.stderr)
        return 1
    previous = record[WORK_FIELD]
    if previous == target:
        print(f"[COLLECTION ERROR] REFUSED: {args.document} already expresses "
              f"work {target}; nothing to join.", file=sys.stderr)
        return 1

    language = document.relative_to(root).parts[0]
    others = _count_expressions(root, previous, registry) - 1
    standing = "currently a work of one" if others <= 0 else \
        f"currently a work of {others + 1}"

    if not args.apply:
        print(f"PLAN: {language} expression joins work {target} ({standing})")
        print(f"  {WORK_FIELD}        {previous} → {target}")
        print(f"  sat:work_retired append: {{uuid: {previous}, "
              f"retired: <now>, by: \"{JOIN_COMMAND}\"}}")
        print("No records were written (--dry-run). Pass --apply to join.")
        return 0

    join_work(document, target, by=JOIN_COMMAND)
    version = tool_version()
    index_path = update_index_for_document(
        root, document, command=JOIN_COMMAND, version=version)
    print(f"JOINED: {language} expression now expresses work {target}")
    print(f"  {WORK_FIELD} moved: {previous} → {target}")
    print(f"  sat:work_retired: appended {previous}")
    print(f"  index updated: {index_path}")
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    registry = resolve_registry(args.offline_confirm)
    root = discover_collection_root(Path.cwd(), registry)

    body = read_work_index(root)
    try:
        works = (body or {}).get("works") if body else None
        if works is None:
            works = rebuild_index_data(root)
    except DuplicateExpressionError as exc:
        print(f"[COLLECTION ERROR] {exc}", file=sys.stderr)
        return 1

    term = args.term.lower()
    matched = 0
    for work, entry in works.items():
        languages = entry.get("languages") or {}
        rows = []
        hit = False
        for language in sorted(languages):
            expression = languages[language]
            path = expression.get("path", "")
            title = _title_for(root, path)
            if term in path.lower() or term in (title or "").lower():
                hit = True
            rows.append((language, path, title))
        if not hit:
            continue
        matched += 1
        print(f"work {work}")
        for language, path, title in rows:
            suffix = f'   "{title}"' if title else ""
            print(f"  {language:<3} {path}{suffix}")
    if matched == 0:
        print(f"No works matched {args.term!r}.")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    registry = resolve_registry(args.offline_confirm)
    root = discover_collection_root(Path.cwd(), registry)

    if args.rebuild:
        try:
            works = rebuild_index_data(root)
        except DuplicateExpressionError as exc:
            print(f"[COLLECTION ERROR] {exc}", file=sys.stderr)
            return 1
        version = tool_version()
        path = write_work_index(root, works, command=REBUILD_COMMAND,
                                version=version)
        print(f"REBUILT: {len(works)} work(s) indexed from the sidecars.")
        print(f"  index: {path}")
        return 0

    # --check
    try:
        findings = compare_index(root)
    except DuplicateExpressionError as exc:
        print(f"[COLLECTION ERROR] {exc}", file=sys.stderr)
        return 1
    if not findings:
        print("CLEAN: the index agrees with the sidecars.")
        return 0
    print(f"{len(findings)} finding(s): the index diverges from the "
          f"canonical sidecars.")
    for finding in findings:
        language = f" {finding.language}" if finding.language else ""
        detail = f" — {finding.detail}" if finding.detail else ""
        print(f"  {finding.kind}  work {finding.work}{language}{detail}")
    print("Remedy: collection work index --rebuild")
    return 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collection work",
        description="Work assignment, expression joining, and the work "
                    "index (ADR-022).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  collection work join fr/produits/guide-rasoir.md "
            "--expression-of en/products/razor-guide.md\n"
            "  collection work find razor\n"
            "  collection work index --rebuild\n"
            "  collection work index --check\n"
        ),
    )
    parser.add_argument(
        "--offline-confirm", action="store_true",
        help="Proceed without a validated subtag registry (explicit consent).")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_join = sub.add_parser(
        "join", help="Join an existing document to a work (dry-run default).")
    p_join.add_argument("document", help="Document to join (path).")
    p_join.add_argument(
        "--expression-of", dest="expression_of", required=True, metavar="VALUE",
        help="The work: a path, a dc:identifier, or a sat:work UUID.")
    p_join.add_argument(
        "--apply", action="store_true",
        help="Perform the join. Without it, print the plan and write nothing.")
    p_join.set_defaults(func=cmd_join)

    p_find = sub.add_parser(
        "find", help="Find works by path or dc:title substring.")
    p_find.add_argument("term", help="Search term.")
    p_find.set_defaults(func=cmd_find)

    p_index = sub.add_parser("index", help="Rebuild or check the work index.")
    mode = p_index.add_mutually_exclusive_group(required=True)
    mode.add_argument("--rebuild", action="store_true",
                      help="Rebuild the index from the sidecars.")
    mode.add_argument("--check", action="store_true",
                      help="Rebuild-and-compare; report divergences as "
                           "findings (nonzero exit when any exist).")
    p_index.set_defaults(func=cmd_index)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except WorkError as exc:
        print(f"[COLLECTION ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
