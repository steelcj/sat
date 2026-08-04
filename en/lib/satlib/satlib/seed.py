#
# source
#   project: sat
#   path: en/lib/satlib/satlib/seed.py
#
"""satlib.seed — a fresh instance as a standing integration test (ADR-026).

A new instance ships with documentation, an example collection, and
sample content staged for ingress. That is not decoration: an install
that completes is a chain that works, on every machine, and a seeded
element that fails is a release finding (ADR-026 section 7).

Three seeding acts, each idempotent per its switch:

- Documentation seeds a content organizing directory in the dual-role
  collection's first archive, with a getting-started document carrying
  full content identity — SAT documents itself in SAT, and the docs
  participate in identity and the work index like any content.

- The example collection at <collections_home>/test-collection/ ships
  with every instance, unswitched (ADR-026 section 6): a single-role
  collection with one identified sample per language, joined as one
  work, so a newcomer's first `collection work find` and first
  `collection work join` land on content that cannot matter.

- Staged samples (the sample_content switch) fill the example
  collection's staging/ with raw markdown awaiting ingress — an en/fr
  pair plus one deliberately misfiled French document, so the language
  finding (ADR-023) fires somewhere safe when cataloging arrives.

These functions take validated language expressions and create real
archives, so the whole chain is exercised, not mocked.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Sequence

from .archive import create_archive, plan_archive
from .children import refresh_children
from .create import create_collection_role, create_content_directory
from .language import TagValidation
from .roles import ROLE_ARCHIVE, ROLE_COLLECTION
from .work import (
    WORK_FIELD,
    assign_document_identity,
    join_work,
    read_document_identity,
    rebuild_index_data,
    write_work_index,
)

__all__ = [
    "seed_documentation",
    "seed_example_collection",
    "MISFILED_SAMPLE",
]

MISFILED_SAMPLE = "note-de-service.md"


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(created: datetime) -> str:
    return created.strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_archive(parent: Path, validation: TagValidation, *, title: str,
                  registry_file_date: Optional[str], version: str,
                  command: str, now: Callable[[], datetime]) -> Path:
    plan = plan_archive(parent, validation, tool=command, tool_version=version,
                        registry_file_date=registry_file_date, title=title,
                        now=now)
    return create_archive(plan, command=command, version=version)


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------

def seed_documentation(archive: Path, *, version: str,
                       command: str = "sat init",
                       registry_file_date: Optional[str] = None,
                       now: Callable[[], datetime] = _now_dt) -> Path:
    """Seed a docs/ content directory and a getting-started document.

    The document doubles as the seeded manual's first page — written for
    the newcomer who just ran their first sat init.
    """
    docs = archive / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    create_content_directory(docs, version=version, command=command,
                             registry_file_date=registry_file_date, now=now)

    guide = docs / "getting-started.md"
    guide.write_text(
        "---\n"
        "dc:title: \"Getting Started with SAT\"\n"
        "dc:description: \"The first page of your instance's documentation.\"\n"
        "dc:language: eng\n"
        "dc:language_bcp47: en\n"
        "---\n\n"
        "# Getting Started with SAT\n\n"
        "You just created a SAT instance. This page is seeded documentation:\n"
        "it lives in your instance like any other content, and you can edit,\n"
        "translate, or remove it.\n",
        "utf-8",
    )
    assign_document_identity(guide)
    return guide


# ---------------------------------------------------------------------------
# The example collection and its staging samples
# ---------------------------------------------------------------------------

def seed_example_collection(instance_root: Path,
                            validations: Sequence[TagValidation], *,
                            collections_home: str, version: str,
                            command: str = "sat init",
                            sample_content: bool = True,
                            registry_file_date: Optional[str] = None,
                            now: Callable[[], datetime] = _now_dt) -> Path:
    """Seed <collections_home>/test-collection/ and return its path.

    One identified sample per language, joined as one work; and, per the
    sample_content switch, staged raw samples including the misfiled
    French document.
    """
    collection = instance_root / collections_home / "test-collection"
    collection.mkdir(parents=True, exist_ok=True)
    create_collection_role(collection, version=version, command=command,
                           registry_file_date=registry_file_date, now=now)

    samples: list[Path] = []
    for validation in validations:
        lang = validation.dc_language_bcp47
        archive = _make_archive(
            collection, validation, title=f"Test Collection ({lang})",
            registry_file_date=registry_file_date, version=version,
            command=command, now=now)
        name = "sample.md" if lang == "en" else f"sample-{lang}.md"
        document = archive / name
        document.write_text(
            f"---\n"
            f"dc:title: \"Sample document ({lang})\"\n"
            f"dc:description: \"A seeded sample. Safe to join, edit, or remove.\"\n"
            f"---\n\n"
            f"# Sample document ({lang})\n\n"
            f"This is a seeded sample in the test collection.\n",
            "utf-8",
        )
        assign_document_identity(document)
        samples.append(document)

    # Join every sample to the first sample's work: one work, N expressions.
    if len(samples) > 1:
        base_work = read_document_identity(samples[0])[WORK_FIELD]
        for document in samples[1:]:
            join_work(document, base_work, by=f"{command} (seed)",
                      now=lambda c=now: _stamp(c()))

    if samples:
        stamp = _stamp(now())
        write_work_index(collection, rebuild_index_data(collection),
                         command=command, version=version, now=lambda: stamp)

    stamp = _stamp(now())
    refresh_children(collection, ROLE_COLLECTION, command=command,
                     version=version, now=lambda: stamp)

    if sample_content:
        _seed_staging(collection, validations)

    return collection


def _seed_staging(collection: Path,
                  validations: Sequence[TagValidation]) -> Path:
    """Raw markdown awaiting ingress: an en/fr pair, plus the misfiled one.

    Staging is not language-structured (it is pre-ingress), so nothing
    here carries SAT records. The misfiled sample is French content whose
    frontmatter claims English — exactly the mismatch the language
    finding (ADR-023) will catch at ingress. It is load-bearing for that
    lesson; it is meant to be wrong.
    """
    staging = collection / "staging"
    staging.mkdir(parents=True, exist_ok=True)

    (staging / "welcome.md").write_text(
        "---\n"
        "dc:title: \"Welcome (sample for ingress)\"\n"
        "dc:language_bcp47: en\n"
        "---\n\n"
        "# Welcome\n\nIngress this file to practice cataloging.\n",
        "utf-8",
    )
    (staging / "bienvenue.md").write_text(
        "---\n"
        "dc:title: \"Bienvenue (échantillon pour l'ingestion)\"\n"
        "dc:language_bcp47: fr\n"
        "---\n\n"
        "# Bienvenue\n\nCe fichier est un échantillon en français.\n",
        "utf-8",
    )
    # Deliberately misfiled: French content, frontmatter claims English.
    (staging / MISFILED_SAMPLE).write_text(
        "---\n"
        "dc:title: \"Note de service\"\n"
        "dc:language_bcp47: en\n"          # WRONG on purpose: the body is French
        "sat:sample_note: \"deliberately misfiled — French content declared en; \"\n"
        "  \"the language finding should fire here at ingress\"\n"
        "---\n\n"
        "# Note de service\n\n"
        "Ceci est un document en français, mais son en-tête déclare l'anglais.\n",
        "utf-8",
    )
    return staging
