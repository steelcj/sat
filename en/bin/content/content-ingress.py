#!/usr/bin/env python3
#
# source
#   project: sat
#   path: en/bin/content/content-ingress.py
#
"""content ingress — bring an arriving document under SAT management.

The operator-invoked tool of content-ingress-specification-v0.3.1. It reads a
document's frontmatter, catalogs its metadata against the resolved cascade
(ADR-023, via satlib.cataloging), mints identity (ADR-021/022), writes the
descriptive sidecar, provenance, and fixity, records the ingress event, and
updates the work index. It is a thin caller: the cataloging policy lives in
satlib.cataloging, and every write-once primitive lives in its own satlib
module.

Increments 1 and 2 are implemented: the ADR-023 cataloging core and the
ADR-029 staging promotion path (`--to`, pipeline step 0). Markdown
normalization (ADR-030, pipeline step 9.5) is deliberately not implemented
here; it is increment 3.

    content ingress <document.md> [--expression-of <address>] [--date <value>]
    content ingress --tree <path> | --archive <lang> | --collection
    content ingress ... --dry-run
    content ingress --version

Decisions from the content-ingress implementation plan applied here: dc:date
falls back transcribed -> --date -> st_birthtime (where the platform exposes
it) -> UTC-now recorded as a noted line (Decision 1); the tool applies by
default and previews under --dry-run (Decision 2).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from satlib import (
    ROLE_ARCHIVE,
    ROLE_COLLECTION,
    ROLE_CONTENT,
    ROLE_SAT,
    FrontmatterError,
    MarkdownError,
    StagingError,
    UnresolvedAddressError,
    apply_cataloging_policy,
    assign_document_identity,
    build_provenance_record,
    check_house_rules,
    create_content_directory,
    ensure_mdformat_available,
    has_document_identity,
    has_role,
    is_assets_name,
    load_markdown_rules,
    normalize_markdown,
    promote,
    read_frontmatter,
    record_fixity,
    resolve_entity,
    resolve_expression_of,
    update_index_for_document,
    verify,
    write_role_yaml,
)

TOOL = "content ingress"
INGRESS_RECORD_VERSION = "0.1"


class IngressError(RuntimeError):
    """A per-document failure narrated to the operator."""


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def sat_root() -> Path:
    return Path(__file__).resolve().parents[3]


def tool_version() -> str:
    try:
        return (sat_root() / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "unknown"


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Discovery (ADR-005: walk upward to the role-declaring directory)
# ---------------------------------------------------------------------------

def _find_role_root(start: Path, role: str) -> Optional[Path]:
    current = start.resolve()
    while True:
        # Guard the filesystem root: it has an empty name, which the assets
        # transform rejects. A SAT role never lives there anyway.
        if current.name and current.is_dir() \
                and has_role(current, role, is_dir=True):
            return current
        if current.parent == current:
            return None
        current = current.parent


def _iter_markdown(base: Path):
    """Every .md document under base, excluding the .*.assets metadata space."""
    base = base.resolve()
    for path in sorted(base.rglob("*.md")):
        rel = path.relative_to(base)
        if any(is_assets_name(part) for part in rel.parts):
            continue
        if path.is_file():
            yield path


# ---------------------------------------------------------------------------
# dc:date fallback (plan Decision 1)
# ---------------------------------------------------------------------------

def _compute_supplied_date(document: Path,
                           operator_date: Optional[str]) -> tuple[str, str]:
    """Return (value, source). source is operator | birthtime | utc-now.

    Transcribed dates are handled inside satlib.cataloging and outrank this;
    the tool only computes the supplied fallback.
    """
    if operator_date:
        return operator_date, "operator"
    birthtime = getattr(document.stat(), "st_birthtime", None)
    if birthtime is not None:
        return (datetime.fromtimestamp(birthtime, tz=timezone.utc)
                .date().isoformat(), "birthtime")
    return _now_dt().date().isoformat(), "utc-now"


# ---------------------------------------------------------------------------
# Content-directory chain minting (pipeline step 2, ADR-025 section 9)
# ---------------------------------------------------------------------------

def _mint_chain(archive_root: Optional[Path], document: Path, *,
                version: str) -> list[Path]:
    """Mint the content role on every organizing directory between the
    archive and the document's parent that lacks it, outermost first."""
    minted: list[Path] = []
    if archive_root is None:
        return minted
    archive_root = archive_root.resolve()
    chain: list[Path] = []
    current = document.parent.resolve()
    while current != archive_root and archive_root in current.parents:
        chain.append(current)
        current = current.parent
    for directory in reversed(chain):
        if not has_role(directory, ROLE_CONTENT, is_dir=True):
            create_content_directory(directory, version=version, command=TOOL)
            minted.append(directory)
    return minted


# ---------------------------------------------------------------------------
# The ingress record (pipeline step 11, spec section 10)
# ---------------------------------------------------------------------------

def _write_ingress_record(document: Path, collection_root: Optional[Path],
                          result, raw: str, frontmatter_present: bool,
                          version: str) -> Path:
    stamp = _now_dt()
    filename_ts = stamp.strftime("%Y-%m-%dT%H-%M-%SZ")
    source = str(document.resolve())
    if collection_root is not None:
        try:
            source = str(document.resolve().relative_to(collection_root.resolve()))
        except ValueError:
            pass
    record = {
        "sat_version": INGRESS_RECORD_VERSION,
        "recorded": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "recorded_by": {"command": TOOL, "version": version},
        "source": source,
        "frontmatter_present": bool(frontmatter_present),
        "origins": result.origins,
        "noted": result.noted,
        "findings": [asdict(f) for f in result.findings],
        "original_frontmatter": raw,
    }
    return write_role_yaml(document, ROLE_CONTENT,
                           f"ingress/ingress-{filename_ts}.yml", record,
                           is_dir=False)


# ---------------------------------------------------------------------------
# The pipeline for one document
# ---------------------------------------------------------------------------

def ingress_document(document: Path, *, to: Optional[str] = None,
                     expression_of: Optional[str] = None,
                     operator_date: Optional[str] = None,
                     dry_run: bool = False, version: str,
                     on_identified: str = "raise") -> str:
    """Run the section-4 pipeline (step 9.5 omitted) for one document.

    Returns one of: "processed", "skipped", "planned". Raises IngressError,
    FrontmatterError, UnresolvedAddressError, or StagingError on a
    per-document failure.
    """
    document = Path(document).resolve()
    if not document.is_file():
        raise IngressError(f"not a file: {document}")

    # Step 0 — staging promotion (ADR-029). Validate the destination is a
    # real archive location before any move, then relocate and continue the
    # pipeline against the document at its new path. The destination is
    # operator-supplied, never inferred from frontmatter.
    if to is not None:
        destination_dir = Path(to)
        if _find_role_root(destination_dir, ROLE_ARCHIVE) is None:
            raise IngressError(
                "--to destination does not resolve to a valid archive "
                f"location: {destination_dir}"
            )
        new_path = destination_dir / document.name
        if new_path.exists():
            raise IngressError(
                f"--to destination already holds {document.name}: {new_path}"
            )
        if dry_run:
            print(f"PLAN: promote {document} -> {new_path}, then catalog")
            print("No changes were made (--dry-run).")
            return "planned"
        document = promote(document, destination_dir)

    # Step 1 — refuse if already identified.
    if has_document_identity(document):
        if on_identified == "skip":
            return "skipped"
        raise IngressError(
            f"REFUSED: {document} already carries content/identity.yml "
            f"(DocumentIdentityExistsError). Identity is write-once."
        )

    instance_root = _find_role_root(document.parent, ROLE_SAT)
    collection_root = _find_role_root(document.parent, ROLE_COLLECTION)
    archive_root = _find_role_root(document.parent, ROLE_ARCHIVE)
    if instance_root is None:
        raise IngressError(
            f"no instance (sat role) found above {document}; not inside a SAT tree"
        )

    # Resolve --expression-of before any write, so an unresolvable address
    # is fatal and leaves nothing behind (spec section 12).
    work = None
    if expression_of is not None:
        if collection_root is None:
            raise IngressError(
                "cannot resolve --expression-of without an enclosing collection"
            )
        work = resolve_expression_of(expression_of, collection_root)

    # Step 3 — read and parse frontmatter (malformed is fatal).
    text = document.read_text("utf-8")
    frontmatter, body, raw = read_frontmatter(text)

    # Step 4 — resolve the cascade preseed and run the <calculated> tripwire.
    preseed = resolve_entity(instance_root, document, entity_is_dir=False)
    tripwire = verify(preseed)
    if not tripwire.clean:
        raise IngressError("cascade tripwire: " + "; ".join(tripwire.messages()))

    # Step 5 — apply the cataloging policy.
    supplied_date, date_source = _compute_supplied_date(document, operator_date)
    result = apply_cataloging_policy(
        frontmatter, preseed,
        archive_language=preseed.get("dc:language_bcp47"),
        supplied_date=supplied_date,
    )
    # Narrate the UTC-now date fallback as a noted line (Decision 1).
    if result.origins.get("dc:date") == "supplied" and date_source == "utc-now":
        noted = dict(result.noted)
        noted["date_fallback"] = {
            "value": supplied_date,
            "source": "ingress-time-utc",
            "reason": "no transcribed dc:date, no --date, st_birthtime unavailable",
        }
        result.noted = noted

    # Markdown normalization is a cascaded setting (ADR-030, ADR-025 section 7),
    # default true; no CLI flag. The house-rule toggles will ride ADR-032's
    # markdown.yml once that is wired; until then the defaults apply.
    normalize_on = bool(preseed.get("sat:normalize_markdown", True))

    if dry_run:
        _print_plan(document, result, frontmatter is not None)
        return "planned"

    # mdformat absence is fatal, and it must fail before any write (ADR-030).
    if normalize_on:
        ensure_mdformat_available()

    # ----- writes -----
    _mint_chain(archive_root, document, version=version)          # step 2
    assign_document_identity(document, work=work)                 # step 6
    write_role_yaml(document, ROLE_CONTENT, "dc.yml",             # step 7
                    result.sidecar, is_dir=False)
    write_role_yaml(document, ROLE_CONTENT, "provenance.yml",     # step 8
                    build_provenance_record(_now_dt(), TOOL, version, None),
                    is_dir=False)
    final_body = body                                            # step 9
    if normalize_on:                                            # step 9.5
        final_body = normalize_markdown(final_body)
    document.write_text(final_body, "utf-8")
    if normalize_on:
        # House-rule toggles come from the shipped-floor markdown.yml
        # (ADR-032); a missing floor falls back to the built-in defaults.
        rules = load_markdown_rules(
            sat_root() / "en" / "bin" / "sat" / "defaults"
            / "content" / "markdown.yml"
        )
        result.findings.extend(check_house_rules(final_body, rules))
    record_fixity(document, ROLE_CONTENT, content_path=document,  # step 10
                  is_dir=False, command=TOOL, version=version)
    _write_ingress_record(document, collection_root, result, raw,  # step 11
                          frontmatter is not None, version)
    if collection_root is not None:                              # step 12
        update_index_for_document(collection_root, document,
                                  command=TOOL, version=version)
    # Single-scope confirmation reports the document's final path, which
    # differs from the argument when the file was promoted from staging.
    if on_identified == "raise":
        print(f"CATALOGED: {document}")
    return "processed"


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _print_plan(document: Path, result, frontmatter_present: bool) -> None:
    print(f"PLAN: content ingress {document}")
    print(f"  frontmatter present: {frontmatter_present}")
    print(f"  descriptive fields:  {', '.join(result.sidecar) or '(none)'}")
    for finding in result.findings:
        print(f"  FINDING [{finding.kind}]: {finding.what}")
    print("  would write: content/identity.yml, dc.yml, provenance.yml, "
          "fixity.yml, an ingress record, and the work index")
    print("No changes were made (--dry-run).")


# ---------------------------------------------------------------------------
# Scope runners
# ---------------------------------------------------------------------------

def _run_single(document: Path, args, version: str) -> int:
    try:
        status = ingress_document(
            document, to=args.to, expression_of=args.expression_of,
            operator_date=args.date, dry_run=args.dry_run,
            version=version, on_identified="raise",
        )
    except (IngressError, FrontmatterError, UnresolvedAddressError,
            StagingError, MarkdownError) as exc:
        print(f"[CONTENT ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


def _discover_batch(args) -> list[Path]:
    if args.tree:
        base = Path(args.tree)
    elif args.archive:
        base = Path(args.archive)
        if not base.exists():
            collection_root = _find_role_root(Path.cwd(), ROLE_COLLECTION)
            if collection_root is not None:
                base = collection_root / args.archive
    else:  # --collection
        base = _find_role_root(Path.cwd(), ROLE_COLLECTION) or Path.cwd()
    if not base.exists():
        raise IngressError(f"scope path not found: {base}")
    return list(_iter_markdown(base))


def _run_batch(args, version: str) -> int:
    try:
        documents = _discover_batch(args)
    except IngressError as exc:
        print(f"[CONTENT ERROR] {exc}", file=sys.stderr)
        return 1

    processed = skipped = findings = errors = 0
    for document in documents:
        try:
            status = ingress_document(
                document, expression_of=args.expression_of,
                operator_date=args.date, dry_run=args.dry_run,
                version=version, on_identified="skip",
            )
        except (IngressError, FrontmatterError, UnresolvedAddressError,
                StagingError, MarkdownError) as exc:
            print(f"[CONTENT ERROR] {document}: {exc}", file=sys.stderr)
            errors += 1
            continue
        if status in ("processed", "planned"):
            processed += 1
        elif status == "skipped":
            skipped += 1

    print(f"{processed} documents processed")
    print(f"{skipped} documents skipped (already identified)")
    if errors:
        print(f"{errors} documents failed")
    return 1 if errors else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="content ingress", description=__doc__)
    parser.add_argument("document", nargs="?",
                        help="a single document to catalog")
    parser.add_argument("--expression-of", dest="expression_of",
                        help="declare the work this document expresses "
                             "(file path, dc:identifier, or sat:work UUID)")
    parser.add_argument("--to", dest="to",
                        help="promote a staged file into an archive location, "
                             "then catalog it there (ADR-029)")
    parser.add_argument("--tree", help="batch: every document under a path")
    parser.add_argument("--archive", help="batch: an entire language archive")
    parser.add_argument("--collection", action="store_true",
                        help="batch: every archive in the collection")
    parser.add_argument("--date", dest="date",
                        help="operator-supplied dc:date fallback")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan and write nothing")
    parser.add_argument("--version", action="store_true",
                        help="print the tool version and exit")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    version = tool_version()

    if args.version:
        print(f"sat-tools {version}")
        return 0

    is_batch = bool(args.tree or args.archive or args.collection)
    if is_batch:
        if args.document:
            print("[CONTENT ERROR] give a single document or a batch scope, "
                  "not both.", file=sys.stderr)
            return 1
        if args.to is not None:
            print("[CONTENT ERROR] --to promotes a single staged file; it "
                  "cannot be combined with a batch scope.", file=sys.stderr)
            return 1
        return _run_batch(args, version)

    if args.document:
        return _run_single(Path(args.document), args, version)

    parser.print_usage()
    return 1


if __name__ == "__main__":
    sys.exit(main())
