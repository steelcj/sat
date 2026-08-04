"""satlib.archive — archive creation (the guide's Step 9, ADR-025).

Composes the scaffold: a validated language expression (satlib.language)
becomes an archive directory whose archive role directory (satlib.roles,
ADR-025) carries its identity, its language record, its provenance
record, and a sparse dc.yml. The role set lives at
.<archive>.assets/archive/.

Creation is split into plan and create so that --dry-run resolves the
exact records a real run would write — nothing is approximated
(Step 7). The plan is pure; only create_archive touches disk.

Records written at creation are immutable from that point (Step 9).
An archive with a provenance record refuses re-creation:
re-initialisation is an error, not a merge (Step 6). A non-empty
directory without a provenance record is a colliding structure and
is likewise refused — nothing is silently absorbed.

The archive dc.yml is sparse (ADR-025 section 4): it carries the
archive's self-recorded sat:name (ADR-024), the fields the archive tier
owns — dc:title, dc:date, and dc:type — and its own dc:description, and it
inherits creator, publisher, and rights from the instance through the
cascade unless an override is supplied. dc:title is not inferable by
tooling; absent, it is written as <calculated>, so an archive whose
title is never set trips verification rather than shipping a silent
blank. The language fields live in language.yml, injected over the
archive layer by the cascade; they are not duplicated into dc.yml.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .cascade import CALCULATED
from .fixity import record_fixity
from .identity import IDENTITY_RECORD, build_identity_record, has_identity
from .language import TagValidation
from .roles import (
    NAME_FIELD,
    ROLE_ARCHIVE,
    has_role,
    role_path,
    write_role_yaml,
    write_sparse_dc,
)

__all__ = [
    "ArchiveError",
    "ArchiveExistsError",
    "ArchiveCollisionError",
    "ArchivePlan",
    "plan_archive",
    "create_archive",
    "has_provenance",
    "build_provenance_record",
    "IDENTITY_RECORD",
    "PROVENANCE_RECORD",
    "LANGUAGE_RECORD",
    "DC_RECORD",
]

PROVENANCE_RECORD = "provenance.yml"
LANGUAGE_RECORD = "language.yml"
DC_RECORD = "dc.yml"


class ArchiveError(RuntimeError):
    """Base class for archive creation refusals."""


class ArchiveExistsError(ArchiveError):
    """The target carries a provenance record.

    Archive records are immutable. Re-initialisation is an error, not
    a merge. No records were written.
    """

    def __init__(self, directory: Path):
        self.directory = directory
        super().__init__(
            f"REFUSED: {role_path(directory, ROLE_ARCHIVE, PROVENANCE_RECORD, is_dir=True)} "
            f"exists. Archive records are immutable. Re-initialisation is "
            f"an error, not a merge. No records were written."
        )


class ArchiveCollisionError(ArchiveError):
    """The target exists with content the creation would absorb."""

    def __init__(self, directory: Path):
        self.directory = directory
        super().__init__(
            f"REFUSED: {directory} exists and is not empty. Creation does "
            f"not silently absorb existing structure. No records were "
            f"written."
        )


def has_provenance(directory: Path, role: str = ROLE_ARCHIVE) -> bool:
    """True if the given role directory carries a provenance record."""
    return role_path(directory, role, PROVENANCE_RECORD, is_dir=True).is_file()


def build_provenance_record(
    created: _dt.datetime,
    tool: str,
    tool_version: str,
    registry_file_date: Optional[str],
) -> dict:
    """The provenance record shape shared by every tier (ADR-020 section 4).

    What distinguishes an instance provenance record from an archive
    one is its content, not its shape: both carry created, tool,
    tool_version, and registry_file_date.
    """
    if created.tzinfo is None:
        raise ValueError("provenance requires a timezone-aware timestamp")
    return {
        "created": created.isoformat(timespec="seconds"),
        "tool": tool,
        "tool_version": tool_version,
        "registry_file_date": registry_file_date,
    }


@dataclass(frozen=True)
class ArchivePlan:
    """Everything a creation will write, resolved before any write.

    records maps asset filename to the exact mapping that will be
    written into the archive's assets directory.
    """

    parent: Path
    directory: Path
    language: TagValidation
    records: dict[str, dict]

    @property
    def assets_dir(self) -> Path:
        return self.directory / f".{self.directory.name}.assets"


def _directory_name(validation: TagValidation) -> str:
    """The archive root directory name for a validated expression.

    Registered expressions use the canonical form (single tag) or the
    canonical underscore-joined form (mixed) — both are what
    dc_language_bcp47 carries. A generated non-authority expression
    keeps its original directory name (spec section 4): the community
    named the directory; SAT generated only the x- tag.
    """
    generated = (
        validation.sat_authority == "none"
        and validation.dc_language_bcp47.startswith("x-")
        and validation.expression != validation.dc_language_bcp47
    )
    return validation.expression if generated else validation.dc_language_bcp47


def plan_archive(
    parent: Path,
    validation: TagValidation,
    *,
    tool: str,
    tool_version: str,
    registry_file_date: Optional[str],
    title: Optional[str] = None,
    creator: Optional[str] = None,
    publisher: Optional[str] = None,
    rights: Optional[str] = None,
    now: Callable[[], _dt.datetime] = lambda: _dt.datetime.now().astimezone(),
) -> ArchivePlan:
    """Resolve an archive creation without writing anything.

    creator, publisher, and rights default to <calculated>: they are
    the cascade's to fill (Step 11). Supplying them here writes
    concrete values instead, which the cascade then has no hole to
    fill — either path verifies clean.
    """
    if not validation.valid:
        problems = validation.errors + [
            e for c in validation.components for e in c.errors
        ]
        raise ValueError(
            f"{validation.expression}: cannot plan an archive from an "
            f"invalid expression: " + "; ".join(problems)
        )

    created = now()
    provenance_record = build_provenance_record(
        created, tool, tool_version, registry_file_date
    )

    language_record: dict = {
        "dc:language": validation.dc_language,
        "dc:language_bcp47": validation.dc_language_bcp47,
        "sat:authority": validation.sat_authority,
    }
    if validation.sat_authority_note:
        language_record["sat:authority_note"] = validation.sat_authority_note

    name = _directory_name(validation)
    directory = parent / name

    # The archive dc.yml is sparse (ADR-025 section 4): sat:name and the
    # fields the archive tier owns. creator, publisher, and rights
    # inherit from the instance; a supplied value states an override
    # here, absence inherits. dc:language lives in language.yml (injected
    # by the cascade), never duplicated into dc.yml.
    dc_record: dict = {
        NAME_FIELD: name,
        "dc:title": title if title is not None else CALCULATED,
        "dc:date": created.date().isoformat(),
    }
    if creator is not None:
        dc_record["dc:creator"] = creator
    if publisher is not None:
        dc_record["dc:publisher"] = publisher
    if rights is not None:
        dc_record["dc:rights"] = rights
    dc_record["dc:description"] = ""  # never <calculated>; not inferable
    dc_record["dc:type"] = "Collection"  # DCMI Type Vocabulary; closest
                                          # available match — no "Archive"
                                          # type exists (radar-1b item 2.4)

    return ArchivePlan(
        parent=parent,
        directory=directory,
        language=validation,
        records={
            IDENTITY_RECORD: build_identity_record(),
            LANGUAGE_RECORD: language_record,
            PROVENANCE_RECORD: provenance_record,
            DC_RECORD: dc_record,
        },
    )


def create_archive(plan: ArchivePlan, *,
                   command: Optional[str] = None,
                   version: Optional[str] = None) -> Path:
    """Execute a plan: create the archive directory and its records.

    Refuses targets that carry a provenance or identity record
    (both immutable) or hold any other content (never silently
    absorbed). When command and version are supplied, the archive
    role's write-once records are digested into fixity.yml at creation
    (ADR-027); omitting them writes the records without a baseline.
    Returns the archive directory.
    """
    directory = plan.directory

    if directory.exists():
        if has_provenance(directory, ROLE_ARCHIVE) or \
                has_identity(directory, ROLE_ARCHIVE):
            raise ArchiveExistsError(directory)
        if any(directory.iterdir()):
            raise ArchiveCollisionError(directory)
    else:
        directory.mkdir(parents=True)

    for filename, record in plan.records.items():
        if filename == DC_RECORD:
            write_sparse_dc(directory, ROLE_ARCHIVE, record)
        else:
            write_role_yaml(directory, ROLE_ARCHIVE, filename, record)

    if command is not None and version is not None:
        record_fixity(directory, ROLE_ARCHIVE, command=command, version=version)

    return directory
