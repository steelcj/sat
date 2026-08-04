#
# source
#   project: sat
#   path: en/lib/satlib/satlib/identity.py
#
"""satlib.identity — stable identity at creation (ADR-021, ADR-025).

Every tier above the document — the SAT instance root, collections,
and archives — carries a permanent identifier minted at creation. The
identifier is a UUID version 4 in URN form, held in dc:identifier
inside an identity.yml in the entity's role directory (ADR-025), beside
that role's provenance record. Each function takes the role whose
identity it reads or writes, so a dual-role directory carries two
identities — one per role — and extraction stays a pure move.
Document-tier identity is governed by ADR-010 v0.1.3 (satlib.work) and
is out of scope here; the format, however, is the same, so this module
is the single home for UUID generation and validation across all tiers
(ADR-019).

identity.yml follows the provenance-record contract: written once at
creation, never modified. It is not regenerated on copy, move, or
rename, and creation tooling refuses a target that already carries
one. The record holds the identifier and nothing else.

Backfill exists because entities created before ADR-021 carry no
identity record. The pre-1.0 fix-forward rule applies: validation
flags them, and backfill_identity mints an identifier for an existing
entity exactly once — it refuses an entity that already has one, like
every other creation-record writer.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Optional

from .roles import role_path, read_role_yaml, write_role_yaml

__all__ = [
    "IdentityError",
    "IdentityExistsError",
    "MalformedIdentityError",
    "IDENTITY_RECORD",
    "IDENTIFIER_FIELD",
    "URN_UUID_PATTERN",
    "new_identifier",
    "is_valid_identifier",
    "build_identity_record",
    "has_identity",
    "read_identity",
    "write_identity",
    "backfill_identity",
]

IDENTITY_RECORD = "identity.yml"
IDENTIFIER_FIELD = "dc:identifier"

# ADR-010's validation pattern, extended with the urn:uuid: prefix
# this record uses. Version nibble 4 and variant bits [89ab] are
# enforced; only lowercase hex is canonical.
URN_UUID_PATTERN = re.compile(
    r"^urn:uuid:"
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class IdentityError(RuntimeError):
    """Base class for identity refusals."""


class IdentityExistsError(IdentityError):
    """The target already carries an identity record.

    Identity is written once at creation and never modified
    (ADR-021). Re-minting is an error, not an update.
    """

    def __init__(self, directory: Path, role: str):
        self.directory = directory
        self.role = role
        super().__init__(
            f"REFUSED: {role_path(directory, role, IDENTITY_RECORD, is_dir=True)} "
            f"already exists. Identity is written once at creation and is "
            f"immutable (ADR-021)."
        )


class MalformedIdentityError(IdentityError):
    """An identity record exists but does not conform to ADR-021."""

    def __init__(self, directory: Path, role: str, problem: str):
        self.directory = directory
        self.role = role
        super().__init__(
            f"{role_path(directory, role, IDENTITY_RECORD, is_dir=True)}: {problem}"
        )


def new_identifier() -> str:
    """Mint a new URN-form UUID v4 identifier.

    Any RFC 9562 compliant v4 generator is acceptable per ADR-010;
    this is the standard library's.
    """
    return f"urn:uuid:{uuid.uuid4()}"


def is_valid_identifier(value: object) -> bool:
    """True if value is a conformant urn:uuid: v4 identifier.

    Uppercase hex is rejected: the canonical form is lowercase
    (ADR-010). Non-strings are never valid.
    """
    return isinstance(value, str) and bool(URN_UUID_PATTERN.match(value))


def build_identity_record(identifier: Optional[str] = None) -> dict:
    """The identity record shape shared by every tier (ADR-021).

    The record holds the identifier and nothing else. When identifier
    is None a fresh one is minted; when supplied it must already be
    conformant — this function refuses to write a malformed value
    rather than normalising it.
    """
    if identifier is None:
        identifier = new_identifier()
    elif not is_valid_identifier(identifier):
        raise ValueError(
            f"not a conformant urn:uuid: v4 identifier: {identifier!r}"
        )
    return {IDENTIFIER_FIELD: identifier}


def has_identity(directory: Path, role: str) -> bool:
    """True if the directory's role directory carries an identity record."""
    return role_path(directory, role, IDENTITY_RECORD, is_dir=True).is_file()


def read_identity(directory: Path, role: str) -> str:
    """Return the role's identifier, validating the record.

    Raises MalformedIdentityError when the record is missing, is not
    a mapping, lacks the identifier field, or carries a value that
    does not conform. Validation tooling reports these; nothing
    repairs them silently.
    """
    path = role_path(directory, role, IDENTITY_RECORD, is_dir=True)
    if not path.is_file():
        raise MalformedIdentityError(directory, role, "identity record is absent")
    record = read_role_yaml(directory, role, IDENTITY_RECORD, is_dir=True)
    if not isinstance(record, dict):
        raise MalformedIdentityError(
            directory, role, "identity record is not a mapping"
        )
    value = record.get(IDENTIFIER_FIELD)
    if value is None:
        raise MalformedIdentityError(
            directory, role, f"identity record lacks {IDENTIFIER_FIELD}"
        )
    if not is_valid_identifier(value):
        raise MalformedIdentityError(
            directory, role,
            f"{IDENTIFIER_FIELD} is not a conformant urn:uuid: v4 "
            f"identifier: {value!r}",
        )
    return value


def write_identity(directory: Path, role: str,
                   identifier: Optional[str] = None) -> str:
    """Write a role's identity record at creation. Returns the identifier.

    Refuses a role directory that already carries an identity record:
    the record is written once and never modified. Callers that need
    the written value (to report it, or to include it in a plan)
    receive it back.
    """
    if has_identity(directory, role):
        raise IdentityExistsError(directory, role)
    record = build_identity_record(identifier)
    write_role_yaml(directory, role, IDENTITY_RECORD, record, is_dir=True)
    return record[IDENTIFIER_FIELD]


def backfill_identity(directory: Path, role: str) -> str:
    """Mint an identifier for a role created before ADR-021.

    One-time by construction: a role directory that already has an
    identity record is refused exactly as at creation. Backfill is the
    same write with a different occasion — the record it produces is
    indistinguishable from one written at creation, which is the
    point: after backfill, tooling has one code path, not two.
    """
    return write_identity(directory, role)
