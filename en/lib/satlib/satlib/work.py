#
# source
#   project: sat
#   path: en/lib/satlib/satlib/work.py
#
"""satlib.work — work assignment, expression joining, the work index (ADR-022).

Document-tier identity (ADR-010 v0.1.3, ADR-012): every document carries
two UUIDs in content/identity.yml inside its assets directory, in the
content role directory (ADR-025). dc:identifier
is the expression's own identity and is immutable without exception.
sat:work names the work the document expresses; a fresh work is minted by
default at assignment, and sat:work changes afterward only through the
join operation — a deliberate, recorded act. The previous lone work UUID
is appended to sat:work_retired with the timestamp and acting operation:
a provenance trail, because that is what retirement is.

The work index (ADR-022 section 5) is the derived, disposable lookup
mapping each sat:work UUID to its expressions by language, identifier,
and current path. Sidecars are canonical; if index and sidecars disagree,
the index is wrong by definition, and rebuild_index_data() is the remedy.
The index lives in the collection role directory (ADR-025), at
collection/work-index.yml, and its file carries the generated record
header (source header convention):
one satlib writer stamps every write, so the shape cannot vary by
command.

A work has at most one expression per language (the MVP model). The
languages key in the index names the axis on purpose: a future variant
axis arrives as a sibling key without moving anything that exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import yaml

from .assets import asset_path, is_assets_name, read_yaml_asset, write_yaml_asset
from .identity import is_valid_identifier, new_identifier

__all__ = [
    "WorkError",
    "DocumentIdentityExistsError",
    "MalformedDocumentIdentityError",
    "DuplicateExpressionError",
    "UnresolvedAddressError",
    "DOCUMENT_IDENTITY_RECORD",
    "IDENTIFIER_FIELD",
    "WORK_FIELD",
    "WORK_RETIRED_FIELD",
    "WORK_INDEX_RECORD",
    "INDEX_SAT_VERSION",
    "Finding",
    "read_document_identity",
    "has_document_identity",
    "assign_document_identity",
    "join_work",
    "resolve_expression_of",
    "rebuild_index_data",
    "write_work_index",
    "read_work_index",
    "update_index_for_document",
    "compare_index",
]

DOCUMENT_IDENTITY_RECORD = "content/identity.yml"
IDENTIFIER_FIELD = "dc:identifier"
WORK_FIELD = "sat:work"
WORK_RETIRED_FIELD = "sat:work_retired"

WORK_INDEX_RECORD = "collection/work-index.yml"
INDEX_SAT_VERSION = "0.1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class WorkError(RuntimeError):
    """Base class for work and index refusals."""


class DocumentIdentityExistsError(WorkError):
    """The document already carries identity; minting again is an error."""

    def __init__(self, document: Path):
        self.document = document
        super().__init__(
            f"REFUSED: {document} already carries {DOCUMENT_IDENTITY_RECORD}. "
            f"Document identity is written once at assignment (ADR-010, ADR-022)."
        )


class MalformedDocumentIdentityError(WorkError):
    """A document identity record exists but does not conform."""

    def __init__(self, document: Path, problem: str):
        self.document = document
        super().__init__(f"{document}: {problem}")


class DuplicateExpressionError(WorkError):
    """Two same-language expressions claim one work (validation finding)."""

    def __init__(self, work: str, language: str, paths: list[str]):
        self.work = work
        self.language = language
        self.paths = paths
        super().__init__(
            f"work {work} has {len(paths)} '{language}' expressions "
            f"({', '.join(paths)}); a work has at most one expression per "
            f"language (ADR-022)."
        )


class UnresolvedAddressError(WorkError):
    """An --expression-of value matched no file path, identifier, or work."""

    def __init__(self, value: str):
        self.value = value
        super().__init__(
            f"could not resolve {value!r} as a file path, a dc:identifier, "
            f"or a sat:work UUID."
        )


# ---------------------------------------------------------------------------
# Document identity: assignment and join
# ---------------------------------------------------------------------------

def has_document_identity(document: Path) -> bool:
    """True if the document's assets carry content/identity.yml."""
    return asset_path(document, DOCUMENT_IDENTITY_RECORD, is_dir=False).is_file()


def read_document_identity(document: Path) -> dict:
    """Return the document's identity record, validating both UUIDs.

    Raises MalformedDocumentIdentityError when the record is missing, a
    field is absent, or a value does not conform. Validation reports
    these; nothing repairs them silently.
    """
    record = read_yaml_asset(document, DOCUMENT_IDENTITY_RECORD, is_dir=False)
    if record is None:
        raise MalformedDocumentIdentityError(document, "identity record is absent")
    for fieldname in (IDENTIFIER_FIELD, WORK_FIELD):
        value = record.get(fieldname)
        if value is None:
            raise MalformedDocumentIdentityError(
                document, f"identity record lacks {fieldname}"
            )
        if not is_valid_identifier(value):
            raise MalformedDocumentIdentityError(
                document,
                f"{fieldname} is not a conformant urn:uuid: v4 identifier: "
                f"{value!r}",
            )
    return record


def assign_document_identity(document: Path,
                             work: Optional[str] = None) -> dict:
    """Mint document identity at assignment. Returns the written record.

    dc:identifier is always fresh. sat:work is fresh by default — a new
    document is a new work — or the declared work when the operator knows
    it (resolved beforehand via resolve_expression_of). Refuses a document
    that already carries identity.
    """
    if has_document_identity(document):
        raise DocumentIdentityExistsError(document)
    if work is not None and not is_valid_identifier(work):
        raise ValueError(f"not a conformant sat:work UUID: {work!r}")
    record = {
        IDENTIFIER_FIELD: new_identifier(),
        WORK_FIELD: work if work is not None else new_identifier(),
    }
    write_yaml_asset(document, DOCUMENT_IDENTITY_RECORD, record, is_dir=False)
    return record


def join_work(document: Path, work: str, *,
              by: str = "collection work join --apply",
              now: Callable[[], str] = _utc_now) -> dict:
    """Join an existing document to a work. Returns the updated record.

    dc:identifier is untouched. The previous sat:work is appended to
    sat:work_retired with the retirement timestamp and the acting
    operation. Joining a document to the work it already expresses is
    refused rather than silently recorded as a no-op retirement.
    """
    if not is_valid_identifier(work):
        raise ValueError(f"not a conformant sat:work UUID: {work!r}")
    record = read_document_identity(document)
    previous = record[WORK_FIELD]
    if previous == work:
        raise WorkError(
            f"REFUSED: {document} already expresses work {work}; "
            f"nothing to join."
        )
    retired = list(record.get(WORK_RETIRED_FIELD) or [])
    retired.append({"uuid": previous, "retired": now(), "by": by})
    record[WORK_FIELD] = work
    record[WORK_RETIRED_FIELD] = retired
    write_yaml_asset(document, DOCUMENT_IDENTITY_RECORD, record, is_dir=False)
    return record


# ---------------------------------------------------------------------------
# Address resolution: file path, dc:identifier, or sat:work UUID
# ---------------------------------------------------------------------------

def resolve_expression_of(value: str, collection_root: Path) -> str:
    """Resolve an --expression-of value to a sat:work UUID.

    Three address forms, resolved in this order (ADR-022): a file path
    (through the document's own sidecar), a dc:identifier (through the
    sidecars), or a sat:work UUID (used directly). Humans remember
    filenames and titles, not UUIDs; the path form is the expected
    common case.
    """
    candidate = (collection_root / value) if not Path(value).is_absolute() \
        else Path(value)
    if candidate.is_file():
        return read_document_identity(candidate)[WORK_FIELD]
    if is_valid_identifier(value):
        for document in _iter_documents(collection_root):
            record = read_document_identity(document)
            if record[IDENTIFIER_FIELD] == value:
                return record[WORK_FIELD]
        # Not any expression's identifier: treat as a work UUID directly.
        return value
    raise UnresolvedAddressError(value)


# ---------------------------------------------------------------------------
# The work index: rebuild, write, read, incremental update, compare
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Finding:
    """One divergence between the index and the canonical sidecars."""
    kind: str      # missing-work | missing-expression | stale-path |
                   # stale-identifier | extra-work | extra-expression
    work: str
    language: str = ""
    detail: str = ""


def _iter_documents(collection_root: Path):
    """Yield the documents this collection owns, by identity.

    The walk prunes at any collection below the root: a document inside a
    single-role collection under the collections home belongs to that
    collection, not to the dual-role collection above it (ADR-025). Its
    language is the top-level archive directory it lives under (ADR-001),
    so mixing collections would key one collection's document under
    another's container name — exactly the divergence the index exists to
    avoid.
    """
    from .roles import ROLE_COLLECTION, has_role

    stack = [collection_root]
    while stack:
        current = stack.pop()
        for entry in sorted(current.iterdir()):
            if entry.name.startswith(".") or is_assets_name(entry.name):
                continue
            if entry.is_dir():
                if entry != collection_root and \
                        has_role(entry, ROLE_COLLECTION, is_dir=True):
                    continue  # a single-role collection owns its documents
                stack.append(entry)
            elif entry.is_file() and has_document_identity(entry):
                yield entry


def rebuild_index_data(collection_root: Path) -> dict:
    """Build the works mapping from the sidecars — the canonical source.

    The language of an expression is the top-level archive directory it
    lives under (ADR-001: language as filesystem structure). Raises
    DuplicateExpressionError when two same-language expressions claim one
    work.
    """
    works: dict = {}
    for document in _iter_documents(collection_root):
        record = read_document_identity(document)
        relative = document.relative_to(collection_root)
        language = relative.parts[0]
        entry = works.setdefault(record[WORK_FIELD], {"languages": {}})
        existing = entry["languages"].get(language)
        if existing is not None:
            raise DuplicateExpressionError(
                record[WORK_FIELD], language,
                [existing["path"], str(relative)],
            )
        entry["languages"][language] = {
            "identifier": record[IDENTIFIER_FIELD],
            "path": str(relative),
        }
    return works


def _index_header(collection_root: Path) -> str:
    """The generated record header (source header convention)."""
    name = collection_root.name
    return (
        f"# {name}/.{name}.assets/{WORK_INDEX_RECORD}\n"
        f"#\n"
        f"#   To update, delete and rebuild using:\n"
        f"#     collection work index --rebuild\n"
        f"#\n"
    )


def write_work_index(collection_root: Path, works: dict, *,
                     command: str, version: str,
                     now: Callable[[], str] = _utc_now) -> Path:
    """Write the index with its generated record header.

    The single writer every command calls (ADR-019): the header shape
    cannot vary between content ingress, collection work join, and
    collection work index --rebuild — only the stamped command differs.
    """
    body = {
        "sat_version": INDEX_SAT_VERSION,
        "generated": now(),
        "generated_by": {"command": command, "version": version},
        "works": works,
    }
    path = asset_path(collection_root, WORK_INDEX_RECORD, is_dir=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _index_header(collection_root)
        + yaml.safe_dump(body, sort_keys=False, allow_unicode=True),
        "utf-8",
    )
    return path


def read_work_index(collection_root: Path) -> Optional[dict]:
    """Read the index body, or None if absent. Comments parse away."""
    return read_yaml_asset(collection_root, WORK_INDEX_RECORD, is_dir=True)


def update_index_for_document(collection_root: Path, document: Path, *,
                              command: str, version: str,
                              now: Callable[[], str] = _utc_now) -> Path:
    """Incrementally reflect one document's sidecar into the index.

    Missing index falls back to a full rebuild — any tool that finds the
    index missing rebuilds it from the sidecars. The incremental result
    is, by construction, what a full rebuild would produce for this
    document: same sidecar, same entry. Retired works lose this
    expression before the current work gains it.
    """
    existing = read_work_index(collection_root)
    if existing is None:
        works = rebuild_index_data(collection_root)
        return write_work_index(collection_root, works,
                                command=command, version=version, now=now)
    works = existing.get("works") or {}
    record = read_document_identity(document)
    relative = str(document.relative_to(collection_root))
    language = Path(relative).parts[0]
    # Remove this expression wherever it previously appeared.
    for work_uuid in list(works):
        languages = works[work_uuid].get("languages") or {}
        if languages.get(language, {}).get("identifier") == record[IDENTIFIER_FIELD]:
            del languages[language]
            if not languages:
                del works[work_uuid]
    entry = works.setdefault(record[WORK_FIELD], {"languages": {}})
    if language in entry["languages"] and \
            entry["languages"][language]["identifier"] != record[IDENTIFIER_FIELD]:
        raise DuplicateExpressionError(
            record[WORK_FIELD], language,
            [entry["languages"][language]["path"], relative],
        )
    entry["languages"][language] = {
        "identifier": record[IDENTIFIER_FIELD],
        "path": relative,
    }
    return write_work_index(collection_root, works,
                            command=command, version=version, now=now)


def compare_index(collection_root: Path) -> list[Finding]:
    """Rebuild from sidecars and diff against the stored index.

    The conformance check validation runs: every divergence is a Finding.
    Sidecars are canonical, so every finding reads as a correction the
    index needs, never the reverse.
    """
    canonical = rebuild_index_data(collection_root)
    stored_body = read_work_index(collection_root)
    stored = (stored_body or {}).get("works") or {}
    findings: list[Finding] = []
    for work, entry in canonical.items():
        stored_langs = (stored.get(work) or {}).get("languages") or {}
        if work not in stored:
            findings.append(Finding("missing-work", work))
        for language, expression in entry["languages"].items():
            held = stored_langs.get(language)
            if held is None:
                if work in stored:
                    findings.append(Finding("missing-expression", work, language))
                continue
            if held.get("path") != expression["path"]:
                findings.append(Finding(
                    "stale-path", work, language,
                    f"index has {held.get('path')!r}, sidecars say "
                    f"{expression['path']!r}",
                ))
            if held.get("identifier") != expression["identifier"]:
                findings.append(Finding(
                    "stale-identifier", work, language,
                    f"index has {held.get('identifier')!r}, sidecars say "
                    f"{expression['identifier']!r}",
                ))
    for work, entry in stored.items():
        if work not in canonical:
            findings.append(Finding("extra-work", work))
            continue
        for language in (entry.get("languages") or {}):
            if language not in canonical[work]["languages"]:
                findings.append(Finding("extra-expression", work, language))
    return findings
