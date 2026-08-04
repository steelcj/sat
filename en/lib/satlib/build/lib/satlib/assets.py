"""satlib.assets — the universal assets directory convention (ADR-018).

Every file and directory <name> has exactly one hidden assets
directory named .<name>.assets. Everything regarding the entity lives
there. The rules made executable here:

Transform (ADR-018 decision 2)
    The assets name is the literal on-disk entity name with "."
    prepended and ".assets" appended. No slugging, casing, or
    character substitution occurs at mapping time: slug conformance
    is a precondition enforced at ingress (ADR-015), not a runtime
    operation. The transform is injective and reversible.

Placement (ADR-018 decision 3)
    A directory's assets directory lives inside the directory it
    describes. A file's assets directory lives beside the file.

Renames and orphans (ADR-018 decision 5)
    Renaming an entity is a two-name operation belonging to tooling.
    An assets directory whose embedded name has no matching entity in
    the expected location is an orphan: reported, never repaired.

Exclusion (ADR-018 decision 6)
    Anything matching .*.assets is metadata space, excluded from
    content enumeration and ingress.

Known edge, documented: a file whose name equals its parent
directory's name (some/b/b) would map its assets beside itself to
some/b/.b.assets — the same path as the directory's own assets. The
inside-placement interpretation takes precedence everywhere in this
module, and validation reports the file's assets as colliding rather
than guessing. Slug-governed trees make this collision unlikely;
deterministic behaviour makes it harmless.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

import yaml

__all__ = [
    "ASSETS_SUFFIX",
    "assets_dir_for",
    "assets_name_for",
    "entity_name_for",
    "is_assets_name",
    "entity_for",
    "asset_path",
    "write_yaml_asset",
    "read_yaml_asset",
    "Orphan",
    "find_orphans",
    "iter_entities",
]

ASSETS_SUFFIX = ".assets"

_ASSETS_NAME_RE = re.compile(r"^\.(?P<entity>.+)\.assets$")


# ---------------------------------------------------------------------------
# The transform (literal, injective, reversible)
# ---------------------------------------------------------------------------

def assets_name_for(entity_name: str) -> str:
    """The assets directory name for an entity name: .<name>.assets"""
    if not entity_name or entity_name in (".", ".."):
        raise ValueError(f"not a valid entity name: {entity_name!r}")
    if "/" in entity_name or "\x00" in entity_name:
        raise ValueError(f"entity name must be a single path component: {entity_name!r}")
    return f".{entity_name}{ASSETS_SUFFIX}"


def entity_name_for(assets_name: str) -> Optional[str]:
    """Reverse transform: .<name>.assets -> <name>, else None.

    Strip the leading dot and the trailing .assets and the entity
    name is recovered exactly (ADR-018 decision 2).
    """
    match = _ASSETS_NAME_RE.match(assets_name)
    return match.group("entity") if match else None


def is_assets_name(name: str) -> bool:
    """True for any name in metadata space (ADR-018 decision 6)."""
    return _ASSETS_NAME_RE.match(name) is not None


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------

def assets_dir_for(entity: Path, is_dir: Optional[bool] = None) -> Path:
    """The assets directory path for an entity.

    is_dir may be supplied explicitly so paths can be computed for
    entities that do not exist yet (dry-run planning). When None, the
    filesystem is consulted.
    """
    if is_dir is None:
        if not entity.exists():
            raise FileNotFoundError(
                f"{entity}: entity does not exist; pass is_dir explicitly "
                f"to compute assets placement for a planned entity"
            )
        is_dir = entity.is_dir()

    name = assets_name_for(entity.name)
    if is_dir:
        return entity / name          # inside the directory it describes
    return entity.parent / name      # beside the file


def entity_for(assets_dir: Path) -> Path:
    """Reverse placement: the entity an assets directory describes.

    Inside placement (parent's name equals the embedded name) takes
    precedence over the file interpretation; see the module docstring
    for the collision edge this resolves deterministically.
    """
    embedded = entity_name_for(assets_dir.name)
    if embedded is None:
        raise ValueError(f"{assets_dir}: not an assets directory name")
    parent = assets_dir.parent
    if parent.name == embedded:
        return parent                # directory assets, inside placement
    return parent / embedded         # file assets, sibling placement


# ---------------------------------------------------------------------------
# Reading and writing assets
# ---------------------------------------------------------------------------

def asset_path(entity: Path, filename: str,
               is_dir: Optional[bool] = None) -> Path:
    """Path of one asset file belonging to an entity."""
    return assets_dir_for(entity, is_dir=is_dir) / filename


def write_yaml_asset(entity: Path, filename: str, data: dict,
                     is_dir: Optional[bool] = None) -> Path:
    """Write a YAML asset, creating the assets directory if needed.

    Keys are emitted in insertion order: SAT records are authored
    documents with deliberate field ordering, not sorted maps.
    """
    path = asset_path(entity, filename, is_dir=is_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True), "utf-8"
    )
    return path


def read_yaml_asset(entity: Path, filename: str,
                    is_dir: Optional[bool] = None) -> Optional[dict]:
    """Read a YAML asset, or None if it does not exist."""
    path = asset_path(entity, filename, is_dir=is_dir)
    try:
        loaded = yaml.safe_load(path.read_text("utf-8"))
    except FileNotFoundError:
        return None
    return loaded if isinstance(loaded, dict) else {}


# ---------------------------------------------------------------------------
# Orphan detection (ADR-018 decision 5)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Orphan:
    """An assets directory whose pairing with an entity is broken.

    reason is one of:
        "no-entity"   no file or directory with the embedded name
                      exists in the expected location
        "misplaced"   the embedded name matches a sibling directory;
                      directory assets belong inside their directory,
                      not beside it
        "collision"   the embedded name matches both the parent
                      directory (inside placement) and a child file;
                      the file's assets collide with the directory's
    """

    assets_path: Path
    embedded_name: str
    reason: str


def find_orphans(root: Path) -> list[Orphan]:
    """Scan a tree for assets directories with broken pairings.

    Reported, never repaired: manual renames become detectable rather
    than silent divergence. Assets directories are not descended into.
    """
    orphans: list[Orphan] = []
    for parent, assets_dir_name in _walk_assets_dirs(root):
        embedded = entity_name_for(assets_dir_name)
        assets_path = parent / assets_dir_name

        if parent.name == embedded:
            # Inside placement: these are the parent directory's own
            # assets. Valid — unless a child file also claims them.
            if (parent / embedded).is_file():
                orphans.append(Orphan(assets_path, embedded, "collision"))
            continue

        sibling = parent / embedded
        if sibling.is_file():
            continue                 # valid file assets, beside the file
        if sibling.is_dir():
            orphans.append(Orphan(assets_path, embedded, "misplaced"))
            continue
        orphans.append(Orphan(assets_path, embedded, "no-entity"))
    return orphans


# ---------------------------------------------------------------------------
# Content enumeration with the exclusion rule (ADR-018 decision 6)
# ---------------------------------------------------------------------------

def iter_entities(root: Path) -> Iterator[Path]:
    """Depth-first content walk, pruning metadata space.

    Yields every file and directory under root except assets
    directories and their contents. Built on os.scandir so entry
    types arrive from the kernel without per-file stat calls; assets
    subtrees are pruned before descent, never after.
    """
    stack = [root]
    while stack:
        current = stack.pop()
        with os.scandir(current) as entries:
            for entry in sorted(entries, key=lambda e: e.name):
                if is_assets_name(entry.name):
                    continue         # metadata space: pruned entirely
                path = Path(entry.path)
                yield path
                if entry.is_dir(follow_symlinks=False):
                    stack.append(path)


def _walk_assets_dirs(root: Path) -> Iterator[tuple[Path, str]]:
    """Yield (parent, assets_dir_name) for every assets directory."""
    stack = [root]
    while stack:
        current = stack.pop()
        with os.scandir(current) as entries:
            for entry in sorted(entries, key=lambda e: e.name):
                if not entry.is_dir(follow_symlinks=False):
                    continue
                if is_assets_name(entry.name):
                    yield current, entry.name
                    continue         # never descend into assets
                stack.append(Path(entry.path))
