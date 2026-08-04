#
# source
#   project: sat
#   path: en/lib/satlib/satlib/children.py
#
"""satlib.children — the parent's children index (ADR-024 section 3).

Reconciliation needs three witnesses to recognize a moved thing as the
same thing (ADR-024 section 4): the orphan's identity, its self-recorded
name, and the parent's expectation. The children index is that third
witness. Each parent role directory carries a derived children.yml
mapping a child key to the child's identifier:

    instance sat role       -> its collections, keyed by relative path
    collection role         -> its archives, keyed by name
    archive role            -> its content organizing directories,
                               keyed by relative path from the archive

Collections and content directories are keyed by relative path because
bare names can collide across containers (ADR-026: collections/test-
collection); archives are immediate children of a collection, so their
names are unique and the key is the name.

The index follows the work index's exact contract (ADR-022, ADR-024):
derived and disposable, written by a single satlib writer that stamps
the generated-record header (source header convention), sidecars
canonical, staleness the detection signal, rebuild the remedy. The
index attests existence, never integrity — that is fixity's job
(ADR-027). Comparison speaks the ADR-024 findings grammar: a child on
disk but absent from the index is missing-child, one in the index but
gone from disk is extra-child, and a key whose recorded identifier no
longer matches the child is stale-child.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Optional

import yaml

from .assets import is_assets_name
from .identity import read_identity
from .roles import (
    ROLE_ARCHIVE,
    ROLE_COLLECTION,
    ROLE_CONTENT,
    ROLE_SAT,
    has_role,
    read_role_yaml,
    role_path,
)

__all__ = [
    "CHILDREN_RECORD",
    "CHILDREN_SAT_VERSION",
    "ChildFinding",
    "child_role_for",
    "discover_children",
    "rebuild_children_data",
    "write_children",
    "read_children",
    "refresh_children",
    "compare_children",
]

CHILDREN_RECORD = "children.yml"
CHILDREN_SAT_VERSION = "0.1"

# Each parent role indexes the tier directly below it.
_CHILD_ROLE = {
    ROLE_SAT: ROLE_COLLECTION,
    ROLE_COLLECTION: ROLE_ARCHIVE,
    ROLE_ARCHIVE: ROLE_CONTENT,
}

# The rebuild remedy printed in each index's header, per parent tier.
_REBUILD_COMMAND = {
    ROLE_SAT: "sat children --rebuild",
    ROLE_COLLECTION: "collection children --rebuild",
    ROLE_ARCHIVE: "archive children --rebuild",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ChildrenError(RuntimeError):
    """The parent role does not maintain a children index."""


def child_role_for(parent_role: str) -> str:
    """The role of the children a parent role indexes."""
    try:
        return _CHILD_ROLE[parent_role]
    except KeyError:
        raise ChildrenError(
            f"{parent_role!r} maintains no children index; only "
            f"{', '.join(_CHILD_ROLE)} do."
        )


@dataclass(frozen=True)
class ChildFinding:
    """One divergence between the children index and the filesystem."""
    kind: str      # missing-child | extra-child | stale-child
    key: str
    detail: str = ""


# ---------------------------------------------------------------------------
# Discovery: the canonical children, read from the filesystem
# ---------------------------------------------------------------------------

def discover_children(parent: Path, parent_role: str) -> dict[str, str]:
    """The parent's children as {key: identifier}, read from disk.

    The canonical source. Collections and content directories are keyed
    by relative path from the parent; archives, being immediate
    children, are keyed by name.
    """
    child_role = child_role_for(parent_role)
    children: dict[str, str] = {}

    if parent_role == ROLE_COLLECTION:
        # Archives are the collection's immediate child directories.
        for directory in sorted(parent.iterdir()):
            if not directory.is_dir() or is_assets_name(directory.name):
                continue
            if directory.name.startswith("."):
                continue
            if has_role(directory, child_role, is_dir=True):
                children[directory.name] = read_identity(directory, child_role)
        return children

    if parent_role == ROLE_SAT:
        # Collections live at the root (dual-role) and under the collections
        # home. A collection never sits inside another collection or an
        # archive in the MVP — the collections home is a flat organizational
        # directory (ADR-026 section 2) — so the walk prunes at collection
        # and archive boundaries rather than descending the whole content
        # tree. If collections-within-collections are ever allowed, this
        # prune is where that opens.
        if has_role(parent, ROLE_COLLECTION, is_dir=True):
            children[_relkey(parent, parent)] = read_identity(parent, ROLE_COLLECTION)
        for directory in _iter_collection_candidates(parent):
            children[_relkey(parent, directory)] = read_identity(directory, ROLE_COLLECTION)
        return children

    # ROLE_ARCHIVE: content organizing directories may sit at any depth, so
    # the archive subtree is walked in full and keyed by relative path.
    for directory in _iter_dirs(parent, include_self=False):
        if has_role(directory, child_role, is_dir=True):
            children[_relkey(parent, directory)] = read_identity(directory, child_role)
    return children


def rebuild_children_data(parent: Path, parent_role: str) -> dict[str, str]:
    """Alias for discover_children: the index is rebuilt from the tree."""
    return discover_children(parent, parent_role)


# ---------------------------------------------------------------------------
# Write, read, refresh
# ---------------------------------------------------------------------------

def _children_header(parent: Path, parent_role: str) -> str:
    """The generated record header (source header convention)."""
    name = parent.name
    remedy = _REBUILD_COMMAND[parent_role]
    return (
        f"# {name}/.{name}.assets/{parent_role}/{CHILDREN_RECORD}\n"
        f"#\n"
        f"#   To update, delete and rebuild using:\n"
        f"#     {remedy}\n"
        f"#\n"
    )


def write_children(parent: Path, parent_role: str, children: dict[str, str], *,
                   command: str, version: str,
                   now: Callable[[], str] = _utc_now) -> Path:
    """Write the children index with its generated record header.

    The single writer every command calls: creation, mv, and rebuild
    stamp the same header shape, only the command differs.
    """
    child_role_for(parent_role)  # validates the parent role
    body = {
        "sat_version": CHILDREN_SAT_VERSION,
        "generated": now(),
        "generated_by": {"command": command, "version": version},
        "children": children,
    }
    path = role_path(parent, parent_role, CHILDREN_RECORD, is_dir=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _children_header(parent, parent_role)
        + yaml.safe_dump(body, sort_keys=False, allow_unicode=True),
        "utf-8",
    )
    return path


def read_children(parent: Path, parent_role: str) -> Optional[dict]:
    """Read the children index body, or None if absent."""
    child_role_for(parent_role)
    return read_role_yaml(parent, parent_role, CHILDREN_RECORD, is_dir=True)


def refresh_children(parent: Path, parent_role: str, *,
                     command: str, version: str,
                     now: Callable[[], str] = _utc_now) -> Path:
    """Rebuild and write the index — what creation and mv call."""
    return write_children(
        parent, parent_role, rebuild_children_data(parent, parent_role),
        command=command, version=version, now=now,
    )


# ---------------------------------------------------------------------------
# Comparison: the ADR-024 findings grammar
# ---------------------------------------------------------------------------

def compare_children(parent: Path, parent_role: str) -> list[ChildFinding]:
    """Diff the stored index against the filesystem.

    Sidecars are canonical, so every finding reads as a correction the
    index needs. A missing index is treated as empty — every child then
    reads as missing-child, which is the correct rebuild signal.
    """
    canonical = discover_children(parent, parent_role)
    stored_body = read_children(parent, parent_role)
    stored = (stored_body or {}).get("children") or {}

    findings: list[ChildFinding] = []
    for key, identifier in canonical.items():
        if key not in stored:
            findings.append(ChildFinding(
                "missing-child", key, f"{key} on disk, absent from index"))
        elif stored[key] != identifier:
            findings.append(ChildFinding(
                "stale-child", key,
                f"index has {stored[key]!r}, disk has {identifier!r}"))
    for key in stored:
        if key not in canonical:
            findings.append(ChildFinding(
                "extra-child", key, f"{key} in index, absent from disk"))
    return findings


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def _iter_collection_candidates(root: Path) -> Iterator[Path]:
    """Collection directories under the instance, walked with pruning.

    Descends only through organizational directories (the collections
    home). A directory declaring the collection role is yielded and not
    descended into; a directory declaring the archive role is skipped
    entirely — neither holds a collection in the MVP. This bounds the
    walk to the shallow collection layer instead of the whole content
    tree.
    """
    stack = [root]
    while stack:
        current = stack.pop()
        with os.scandir(current) as entries:
            for entry in sorted(entries, key=lambda e: e.name):
                if not entry.is_dir(follow_symlinks=False):
                    continue
                if is_assets_name(entry.name) or entry.name.startswith("."):
                    continue
                path = Path(entry.path)
                if has_role(path, ROLE_COLLECTION, is_dir=True):
                    yield path                     # a collection; do not descend
                elif has_role(path, ROLE_ARCHIVE, is_dir=True):
                    continue                       # an archive; holds no collections
                else:
                    stack.append(path)             # organizational; keep looking


def _iter_dirs(root: Path, *, include_self: bool) -> Iterator[Path]:
    """Directories under root, metadata space pruned, self optional."""
    if include_self:
        yield root
    stack = [root]
    while stack:
        current = stack.pop()
        with os.scandir(current) as entries:
            for entry in sorted(entries, key=lambda e: e.name):
                if not entry.is_dir(follow_symlinks=False):
                    continue
                if is_assets_name(entry.name) or entry.name.startswith("."):
                    continue
                path = Path(entry.path)
                yield path
                stack.append(path)


def _relkey(parent: Path, directory: Path) -> str:
    """The child's key: its POSIX relative path from the parent."""
    return directory.relative_to(parent).as_posix()
