#
# source
#   project: sat
#   path: en/lib/satlib/satlib/migrate.py
#
"""satlib.migrate — the one-time 0.5.0/0.6.0 to role-directory migration.

ADR-025 section 9 amends the flat record placement of ADR-021 and the
sat/ index namespace of ADR-022. This module moves an existing tree
forward, once. Pre-1.0 fix-forward: no compatibility shims, no dual-path
readers remain after it runs.

What the migration does, narrated per file, dry-run by default:

- Flat identity.yml, provenance.yml, dc.yml, and language.yml move into
  their tier's role directory. Position and content decide the tier: a
  directory with a language record is an archive; the migration root is
  the instance; a directory holding archives is a collection.

- The flat records at the instance root are *instance* records by their
  own content — the provenance records an instantiation, an instance-
  tier creation event no collection may claim (ADR-020), and any
  external citation of the root's dc:identifier meant the instance, the
  sovereign unit. They move into sat/. The collection role at a dual-
  role root was implicit in 0.6.0 — it never existed as a record-bearing
  thing — so it is minted fresh here: a new identity, and a provenance
  recording creation by sat migrate, now, with no back-dating to the
  instance's instantiation.

- sat:name lands in both roles' dc.yml at a dual-role root (ADR-024
  decision 2): the same directory name, two records.

- The old .assets/sat/work-index.yml is deleted and the index rebuilt in
  the collection role (it is derived, so it migrates by regeneration).
  Document identity moves from the 0.6.0 sat/identity.yml to
  content/identity.yml.

- Children indexes are built at every parent, and fixity is recorded for
  the migrated write-once records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Optional

from .assets import assets_name_for, entity_name_for, is_assets_name
from .children import refresh_children
from .fixity import record_fixity
from .identity import build_identity_record
from .archive import build_provenance_record
from .roles import (
    DC_RECORD,
    NAME_FIELD,
    ROLE_ARCHIVE,
    ROLE_COLLECTION,
    ROLE_SAT,
    SPARSE_DC_TEMPLATE_COMMENT,
    write_name,
    write_role_yaml,
    write_sparse_dc,
)
from .work import rebuild_index_data, write_work_index

__all__ = [
    "FLAT_RECORDS",
    "MIGRATE_COMMAND",
    "plan_migration",
    "migrate",
]

# The flat records a 0.5.0/0.6.0 tier directory may carry.
FLAT_RECORDS = ("identity.yml", "provenance.yml", "dc.yml", "language.yml")

# The 0.6.0 operational namespace (now superseded by role directories).
_OLD_NAMESPACE = "sat"
_OLD_WORK_INDEX = "work-index.yml"
_OLD_DOCUMENT_IDENTITY = "identity.yml"

MIGRATE_COMMAND = "sat migrate"


def _utc_now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _assets_of(entity: Path) -> Path:
    return entity / assets_name_for(entity.name)


def _file_assets_of(document: Path) -> Path:
    return document.parent / assets_name_for(document.name)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _is_archive(directory: Path) -> bool:
    """A directory with a (flat or migrated) language record is an archive."""
    assets = _assets_of(directory)
    return (assets / "language.yml").is_file() or \
           (assets / ROLE_ARCHIVE / "language.yml").is_file()


def _has_archive_children(directory: Path) -> bool:
    for child in _direct_dirs(directory):
        if _is_archive(child):
            return True
    return False


def _is_collection(directory: Path) -> bool:
    """A directory holding archives, or a 0.6.0 work index, is a collection."""
    assets = _assets_of(directory)
    if (assets / _OLD_NAMESPACE / _OLD_WORK_INDEX).is_file():
        return True
    return _has_archive_children(directory)


def _primary_role(directory: Path, root: Path) -> Optional[str]:
    """The role the directory's flat records belong to."""
    if _is_archive(directory):
        return ROLE_ARCHIVE
    if directory == root:
        return ROLE_SAT
    if _is_collection(directory):
        return ROLE_COLLECTION
    return None


# ---------------------------------------------------------------------------
# Planning and execution (dry-run by default)
# ---------------------------------------------------------------------------

@dataclass
class _Step:
    line: str
    action: Optional[Callable[[], None]] = None


def plan_migration(root: Path) -> list[str]:
    """The narrated PLAN — every file the migration would touch."""
    return [step.line for step in _build(root, version="", now=_utc_now_dt)]


def migrate(root: Path, *, version: str, apply: bool = False,
            now: Callable[[], datetime] = _utc_now_dt) -> list[str]:
    """Migrate a tree, or narrate the plan. Returns the narration lines.

    Dry-run by default: with apply False nothing is written. With apply
    True each step runs in order, and the same narration is returned.
    """
    steps = _build(root, version=version, now=now)
    if apply:
        for step in steps:
            if step.action is not None:
                step.action()
    return [step.line for step in steps]


def _build(root: Path, *, version: str,
           now: Callable[[], datetime]) -> list[_Step]:
    steps: list[_Step] = []
    # One migration is one event: capture the instant once so every record
    # it writes — moved, minted, stamped — agrees on the timestamp.
    created = now()
    now_str = created.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Directory-tier records: move flat records into role directories,
    #    and mint the dual-role root's collection role.
    for directory in _iter_dirs(root):
        assets = _assets_of(directory)
        if not assets.is_dir():
            continue
        role = _primary_role(directory, root)
        if role is not None:
            _plan_flat_move(steps, directory, assets, role, version, now_str)
        if directory == root and _is_collection(directory):
            _plan_mint_collection(steps, directory, version, created)

    # 2. Document identity: 0.6.0 sat/identity.yml -> content/identity.yml.
    for document in _iter_files(root):
        _plan_document(steps, document, version, now_str)

    # 3. Work index per collection — after documents carry content identity,
    #    so the rebuild reads the migrated sidecars.
    for directory in _iter_dirs(root):
        if _is_collection(directory):
            _plan_work_index(steps, directory, _assets_of(directory),
                             version, now_str)

    # 4. Children indexes at every parent that maintains one.
    _plan_children(steps, root, version, now_str)

    return steps


def _plan_flat_move(steps, directory, assets, role, version, now_str):
    moved_any = False
    for record in FLAT_RECORDS:
        src = assets / record
        if not src.is_file():
            continue
        dst = assets / role / record
        steps.append(_Step(
            f"MOVE  {src}  ->  {role}/{record}",
            _mover(src, dst),
        ))
        moved_any = True
    if moved_any:
        steps.append(_Step(
            f"NAME  {directory}: {NAME_FIELD}: {directory.name} (in {role}/dc.yml)",
            _namer(directory, role, directory.name),
        ))
        steps.append(_Step(
            f"FIXITY  record {role}/fixity.yml for {directory}",
            _fixer(directory, role, version, now_str),
        ))


def _plan_mint_collection(steps, directory, version, created):
    """Mint the dual-role root's collection role: fresh identity and a
    provenance that records creation by sat migrate, at the migration
    instant."""
    steps.append(_Step(
        f"MINT  {directory}: collection role (identity, provenance by "
        f"{MIGRATE_COMMAND}, sparse dc)",
        _minter(directory, version, created),
    ))
    steps.append(_Step(
        f"NAME  {directory}: {NAME_FIELD}: {directory.name} (in collection/dc.yml)",
        _namer(directory, ROLE_COLLECTION, directory.name),
    ))


def _plan_work_index(steps, directory, assets, version, now_str):
    old_index = assets / _OLD_NAMESPACE / _OLD_WORK_INDEX
    if old_index.is_file():
        steps.append(_Step(
            f"DELETE  {old_index} (0.6.0 namespace)",
            _deleter(old_index),
        ))
    steps.append(_Step(
        f"REBUILD  work index at {directory}: collection/work-index.yml",
        _index_rebuilder(directory, version, now_str),
    ))


def _plan_document(steps, document, version, now_str):
    assets = _file_assets_of(document)
    old = assets / _OLD_NAMESPACE / _OLD_DOCUMENT_IDENTITY
    new = assets / "content" / _OLD_DOCUMENT_IDENTITY
    if old.is_file() and not new.is_file():
        steps.append(_Step(
            f"MOVE  {old}  ->  content/{_OLD_DOCUMENT_IDENTITY}",
            _move_and_tidy(old, new),
        ))
        steps.append(_Step(
            f"FIXITY  record content/fixity.yml for {document}",
            _content_fixer(document, version, now_str),
        ))


def _plan_children(steps, root, version, now_str):
    # Instance children, then each collection's, then each archive's.
    for directory in _iter_dirs(root):
        if directory == root:
            steps.append(_Step(
                f"CHILDREN  build sat/children.yml at {directory}",
                _children_builder(directory, ROLE_SAT, version, now_str),
            ))
            if _is_collection(directory):
                steps.append(_Step(
                    f"CHILDREN  build collection/children.yml at {directory}",
                    _children_builder(directory, ROLE_COLLECTION, version, now_str),
                ))
        elif _is_archive(directory):
            steps.append(_Step(
                f"CHILDREN  build archive/children.yml at {directory}",
                _children_builder(directory, ROLE_ARCHIVE, version, now_str),
            ))
        elif _is_collection(directory):
            steps.append(_Step(
                f"CHILDREN  build collection/children.yml at {directory}",
                _children_builder(directory, ROLE_COLLECTION, version, now_str),
            ))


# ---------------------------------------------------------------------------
# Deferred actions (closures the executor runs only under --apply)
# ---------------------------------------------------------------------------

def _mover(src: Path, dst: Path) -> Callable[[], None]:
    def run():
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
    return run


def _move_and_tidy(src: Path, dst: Path) -> Callable[[], None]:
    """Move a record, then remove the emptied 0.6.0 namespace directory.

    A document's identity moves out of the sat/ namespace; the emptied
    sat/ directory must go, or declared_roles would read it as a stray
    sat role beside the file.
    """
    def run():
        source_parent = src.parent
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        if source_parent.is_dir() and not any(source_parent.iterdir()):
            source_parent.rmdir()
    return run


def _namer(directory: Path, role: str, name: str) -> Callable[[], None]:
    return lambda: write_name(directory, role, name)


def _fixer(directory: Path, role: str, version: str, now_str: str):
    return lambda: record_fixity(
        directory, role, command=MIGRATE_COMMAND, version=version,
        now=lambda: now_str)


def _content_fixer(document: Path, version: str, now_str: str):
    from .roles import ROLE_CONTENT
    return lambda: record_fixity(
        document, ROLE_CONTENT, content_path=document, is_dir=False,
        command=MIGRATE_COMMAND, version=version, now=lambda: now_str)


def _deleter(path: Path) -> Callable[[], None]:
    def run():
        path.unlink()
        parent = path.parent
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()  # tidy the emptied 0.6.0 namespace directory
    return run


def _minter(directory: Path, version: str,
            created: datetime) -> Callable[[], None]:
    def run():
        write_role_yaml(directory, ROLE_COLLECTION, "identity.yml",
                        build_identity_record(), is_dir=True)
        provenance = build_provenance_record(
            created, MIGRATE_COMMAND, version, None)
        write_role_yaml(directory, ROLE_COLLECTION, "provenance.yml",
                        provenance, is_dir=True)
        write_sparse_dc(directory, ROLE_COLLECTION,
                        {NAME_FIELD: directory.name, "dc:description": ""})
    return run


def _index_rebuilder(directory: Path, version: str, now_str: str):
    def run():
        works = rebuild_index_data(directory)
        write_work_index(directory, works, command=MIGRATE_COMMAND,
                         version=version, now=lambda: now_str)
    return run


def _children_builder(directory: Path, role: str, version: str, now_str: str):
    return lambda: refresh_children(
        directory, role, command=MIGRATE_COMMAND, version=version,
        now=lambda: now_str)


# ---------------------------------------------------------------------------
# Filesystem walks
# ---------------------------------------------------------------------------

def _direct_dirs(directory: Path) -> Iterator[Path]:
    if not directory.is_dir():
        return
    for child in sorted(directory.iterdir()):
        if child.is_dir() and not is_assets_name(child.name) \
                and not child.name.startswith("."):
            yield child


def _iter_dirs(root: Path) -> Iterator[Path]:
    """The root and every non-metadata directory beneath it."""
    yield root
    stack = [root]
    while stack:
        current = stack.pop()
        for child in _direct_dirs(current):
            yield child
            stack.append(child)


def _iter_files(root: Path) -> Iterator[Path]:
    stack = [root]
    while stack:
        current = stack.pop()
        for entry in sorted(current.iterdir()):
            if is_assets_name(entry.name) or entry.name.startswith("."):
                continue
            if entry.is_dir():
                stack.append(entry)
            elif entry.is_file():
                yield entry
