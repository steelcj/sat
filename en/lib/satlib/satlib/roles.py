#
# source
#   project: sat
#   path: en/lib/satlib/satlib/roles.py
#
"""satlib.roles — role-named assets directories (ADR-025 sections 1-2).

A directory's roles are exactly the role-named directories inside its
assets directory (ADR-018). The four role names are the cascade's four
tiers:

    sat          the instance role
    collection   the collection role
    archive      the archive role (a language archive's assets)
    content      the content role (a content organizing directory's
                 assets, or a document's assets beside the file)

The pattern is uniform. Inside a directory's assets, or beside a
content file's, each role owns a subdirectory that holds that role's
records:

    .<directory_name>.assets/sat/          instance role
    .<directory_name>.assets/collection/   collection role
    .<directory_name>.assets/archive/      archive role
    .<directory_name>.assets/content/      content role (directory)
    .<file_name>.assets/content/           content role (document,
                                           ADR-018 file placement)

A directory carrying two role directories in one assets directory is a
**dual-role directory** — SAT's own repository, an instance and a
collection at once, is the founding example. A directory wearing one
role is a **single-role directory**. Discovery reads the declared roles
straight off the filesystem (ADR-024): the set of role subdirectories
present is the set of roles the entity declares.

Each role's ``dc.yml`` records the entity's directory name in
``sat:name`` (ADR-024 section 2). The name is mutable filesystem
metadata — renames are legitimate operator acts — so it lives in the
mutable, operator-owned settings file, never in the write-once
``identity.yml``. The self-recorded name is what proves an orphan's
past pairing when reconciliation runs.

This module locates role directories, reports which roles an entity
declares, and reads and writes ``sat:name``. What each role directory
holds at creation is ADR-026's subject (satlib.archive, satlib.identity);
what the cascade does with the ``dc.yml`` files is satlib.cascade's.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from .assets import assets_dir_for, read_yaml_asset, write_yaml_asset

__all__ = [
    "ROLE_SAT",
    "ROLE_COLLECTION",
    "ROLE_ARCHIVE",
    "ROLE_CONTENT",
    "ROLES",
    "NAME_FIELD",
    "DC_RECORD",
    "SPARSE_DC_TEMPLATE_COMMENT",
    "RoleError",
    "role_dir",
    "role_path",
    "has_role",
    "declared_roles",
    "read_role_yaml",
    "write_role_yaml",
    "write_sparse_dc",
    "read_name",
    "write_name",
]

ROLE_SAT = "sat"
ROLE_COLLECTION = "collection"
ROLE_ARCHIVE = "archive"
ROLE_CONTENT = "content"

# Canonical order: the cascade's tier order (ADR-025 section 7). Every
# listing this module produces follows it, so a dual-role directory
# always reports sat before collection.
ROLES = (ROLE_SAT, ROLE_COLLECTION, ROLE_ARCHIVE, ROLE_CONTENT)

NAME_FIELD = "sat:name"
DC_RECORD = "dc.yml"

# The sparse-inheritance template comment (ADR-025 section 4). A lower
# tier's dc.yml ships nearly empty carrying this comment: an empty file
# means inherit, a stated value means this tier decided differently.
SPARSE_DC_TEMPLATE_COMMENT = (
    "# Settings flow down from the instance automatically.\n"
    "# Only write something here if THIS tier needs a different answer.\n"
    "#\n"
)


class RoleError(ValueError):
    """An unknown role name was supplied."""


def _check_role(role: str) -> None:
    if role not in ROLES:
        raise RoleError(
            f"unknown role {role!r}; the roles are {', '.join(ROLES)}"
        )


# ---------------------------------------------------------------------------
# Role directory location
# ---------------------------------------------------------------------------

def role_dir(entity: Path, role: str,
             is_dir: Optional[bool] = None) -> Path:
    """The role directory for an entity: .<name>.assets/<role>/.

    is_dir may be supplied explicitly so the path can be computed for a
    planned entity that does not exist yet (dry-run), exactly as
    assets_dir_for allows.
    """
    _check_role(role)
    return assets_dir_for(entity, is_dir=is_dir) / role


def role_path(entity: Path, role: str, filename: str,
              is_dir: Optional[bool] = None) -> Path:
    """Path of one record inside a role directory."""
    return role_dir(entity, role, is_dir=is_dir) / filename


def has_role(entity: Path, role: str,
             is_dir: Optional[bool] = None) -> bool:
    """True if the entity declares the given role."""
    _check_role(role)
    return role_dir(entity, role, is_dir=is_dir).is_dir()


def declared_roles(entity: Path,
                   is_dir: Optional[bool] = None) -> list[str]:
    """The roles an entity declares, in canonical tier order.

    A pure read of the filesystem (ADR-024 primary discovery): the role
    subdirectories present inside the entity's assets directory are the
    roles it declares. An entity with no assets directory declares
    nothing and returns the empty list.
    """
    assets = assets_dir_for(entity, is_dir=is_dir)
    if not assets.is_dir():
        return []
    return [role for role in ROLES if (assets / role).is_dir()]


# ---------------------------------------------------------------------------
# Role records
# ---------------------------------------------------------------------------

def read_role_yaml(entity: Path, role: str, filename: str,
                   is_dir: Optional[bool] = None) -> Optional[dict]:
    """Read a record from a role directory, or None if absent."""
    _check_role(role)
    return read_yaml_asset(entity, f"{role}/{filename}", is_dir=is_dir)


def write_role_yaml(entity: Path, role: str, filename: str, data: dict,
                    is_dir: Optional[bool] = None) -> Path:
    """Write a record into a role directory, creating it if needed."""
    _check_role(role)
    return write_yaml_asset(entity, f"{role}/{filename}", data, is_dir=is_dir)


def write_sparse_dc(entity: Path, role: str, record: dict,
                    is_dir: Optional[bool] = None) -> Path:
    """Write a lower tier's dc.yml, led by the template comment.

    The sparse-inheritance header (ADR-025 section 4) opens the file so
    an operator reading it sees at once that an empty file inherits and
    a stated value overrides on purpose. The record itself is whatever
    this tier owns (its sat:name, its per-entity fields); everything
    absent inherits from above through the cascade.
    """
    _check_role(role)
    path = role_path(entity, role, DC_RECORD, is_dir=is_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        SPARSE_DC_TEMPLATE_COMMENT
        + yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
        "utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# The self-recorded name (ADR-024 section 2)
# ---------------------------------------------------------------------------

def read_name(entity: Path, role: str,
              is_dir: Optional[bool] = None) -> Optional[str]:
    """Return the entity's self-recorded sat:name for a role, or None."""
    record = read_role_yaml(entity, role, DC_RECORD, is_dir=is_dir)
    return (record or {}).get(NAME_FIELD)


def write_name(entity: Path, role: str, name: str,
               is_dir: Optional[bool] = None) -> Path:
    """Set sat:name in a role's dc.yml, preserving the rest of the file.

    A read-modify-write that keeps any leading comment block — the
    sparse-inheritance template comment (ADR-025 section 4) or a
    generated-record header — and the file's existing field order. An
    absent sat:name is prepended; an existing one is updated in place.
    The safe mv verb (ADR-024) and migration (ADR-025 section 9) both
    reach for this: a rename maintains the name record without
    disturbing the settings beside it.
    """
    _check_role(role)
    path = role_path(entity, role, DC_RECORD, is_dir=is_dir)

    header, body_text = "", ""
    if path.is_file():
        header, body_text = _split_leading_comment(path.read_text("utf-8"))

    data = yaml.safe_load(body_text) if body_text.strip() else None
    if not isinstance(data, dict):
        data = {}

    if NAME_FIELD in data:
        data[NAME_FIELD] = name
        body = data
    else:
        body = {NAME_FIELD: name, **data}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        header + yaml.safe_dump(body, sort_keys=False, allow_unicode=True),
        "utf-8",
    )
    return path


def _split_leading_comment(text: str) -> tuple[str, str]:
    """Split a leading comment/blank block from the YAML body beneath it."""
    lines = text.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped and not stripped.startswith("#"):
            break
        index += 1
    return "".join(lines[:index]), "".join(lines[index:])
