#
# source
#   project: sat
#   path: en/lib/satlib/satlib/create.py
#
"""satlib.create — role-set creation for instance, collection, content.

The tier creators the full-chain (ADR-026) stands on. Each writes one
role's complete record set — identity, provenance, its dc.yml, any
role-specific records, and its fixity baseline — into the role directory
(ADR-025), stamped by the invoking command. Archive creation keeps its
own home in satlib.archive (it needs a validated language expression);
these three cover the tiers that do not.

The instance role owns its settings: its dc.yml carries concrete
creator/publisher/rights when the preseed or the operator supplied them,
and the <calculated> tripwire otherwise (ADR-026 keeps absent-preseed
behaviour byte-for-byte with today's — the holes arm at the owning
tier). It also records sat:collections_home, the resolved name of the
instance's collections directory, which tooling reads and never assumes.

The collection role ships sparse: its dc.yml inherits from the instance,
carrying only sat:name and its own description, and it declares itself in
collection.yml (ADR-011, ADR-022). A dual-role root and a single-role
collection are created the same way — the only difference is the
directory they are written into.

A content organizing directory (ADR-025 section 9) carries the content
role: an identity of dc:identifier and sat:work (every content entity is
a work, lone by default and joinable), provenance, and a sparse dc.yml.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from .archive import PROVENANCE_RECORD, build_provenance_record
from .cascade import CALCULATED
from .fixity import record_fixity
from .identity import (
    IDENTIFIER_FIELD,
    IdentityExistsError,
    has_identity,
    new_identifier,
    write_identity,
)
from .roles import (
    ROLE_COLLECTION,
    ROLE_CONTENT,
    ROLE_SAT,
    write_role_yaml,
    write_sparse_dc,
)
from .work import WORK_FIELD

__all__ = [
    "COLLECTION_RECORD",
    "COLLECTIONS_HOME_FIELD",
    "DEFAULT_COLLECTIONS_HOME",
    "create_instance_role",
    "create_collection_role",
    "create_content_directory",
]

COLLECTION_RECORD = "collection.yml"
COLLECTIONS_HOME_FIELD = "sat:collections_home"
DEFAULT_COLLECTIONS_HOME = "collections"


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(created: datetime) -> str:
    return created.strftime("%Y-%m-%dT%H:%M:%SZ")


def create_instance_role(root: Path, *, version: str,
                         command: str = "sat init",
                         creator: Optional[str] = None,
                         publisher: Optional[str] = None,
                         rights: Optional[str] = None,
                         collections_home: str = DEFAULT_COLLECTIONS_HOME,
                         registry_file_date: Optional[str] = None,
                         identifier: Optional[str] = None,
                         now: Callable[[], datetime] = _now_dt) -> str:
    """Write the instance sat role set. Returns the identifier.

    The instance owns creator/publisher/rights: a supplied value is
    stated, an absent one arms the <calculated> tripwire at this tier.
    sat:collections_home is written here for tooling to resolve.
    """
    if has_identity(root, ROLE_SAT):
        raise IdentityExistsError(root, ROLE_SAT)
    created = now()
    identity = write_identity(root, ROLE_SAT, identifier)
    write_role_yaml(root, ROLE_SAT, PROVENANCE_RECORD,
                    build_provenance_record(created, command, version,
                                            registry_file_date), is_dir=True)
    write_role_yaml(root, ROLE_SAT, "dc.yml", {
        "sat:name": root.name,
        COLLECTIONS_HOME_FIELD: collections_home,
        "dc:creator": creator if creator is not None else CALCULATED,
        "dc:publisher": publisher if publisher is not None else CALCULATED,
        "dc:rights": rights if rights is not None else CALCULATED,
        "dc:description": "",
    }, is_dir=True)
    stamp = _stamp(created)
    record_fixity(root, ROLE_SAT, command=command, version=version,
                  now=lambda: stamp)
    return identity


def create_collection_role(directory: Path, *, version: str,
                           command: str = "collection init",
                           relationships: Optional[dict] = None,
                           registry_file_date: Optional[str] = None,
                           identifier: Optional[str] = None,
                           now: Callable[[], datetime] = _now_dt) -> str:
    """Write a collection role set — sparse dc, collection.yml, fixity.

    Used for both the dual-role root (directory is the instance) and a
    single-role collection (directory is under the collections home).
    The children index is written by the caller once archives exist.
    """
    if has_identity(directory, ROLE_COLLECTION):
        raise IdentityExistsError(directory, ROLE_COLLECTION)
    created = now()
    identity = write_identity(directory, ROLE_COLLECTION, identifier)
    write_role_yaml(directory, ROLE_COLLECTION, PROVENANCE_RECORD,
                    build_provenance_record(created, command, version,
                                            registry_file_date), is_dir=True)
    write_sparse_dc(directory, ROLE_COLLECTION,
                    {"sat:name": directory.name, "dc:description": "",
                     "dc:type": "Collection"})
    write_role_yaml(directory, ROLE_COLLECTION, COLLECTION_RECORD, {
        "sat:name": directory.name,
        "sat:relationships": relationships or {},
    }, is_dir=True)
    stamp = _stamp(created)
    record_fixity(directory, ROLE_COLLECTION, command=command, version=version,
                  now=lambda: stamp)
    return identity


def create_content_directory(directory: Path, *, version: str,
                             command: str = "content init",
                             work: Optional[str] = None,
                             registry_file_date: Optional[str] = None,
                             identifier: Optional[str] = None,
                             now: Callable[[], datetime] = _now_dt) -> dict:
    """Mint a content organizing directory's records (ADR-025 section 9).

    Returns the identity record. The identity carries dc:identifier and
    sat:work: a content directory is a work, lone by default and
    joinable across languages (products/ and produits/ are two
    expressions of one work).
    """
    if has_identity(directory, ROLE_CONTENT):
        raise IdentityExistsError(directory, ROLE_CONTENT)
    created = now()
    id_record = {
        IDENTIFIER_FIELD: identifier or new_identifier(),
        WORK_FIELD: work or new_identifier(),
    }
    write_role_yaml(directory, ROLE_CONTENT, "identity.yml", id_record,
                    is_dir=True)
    write_role_yaml(directory, ROLE_CONTENT, PROVENANCE_RECORD,
                    build_provenance_record(created, command, version,
                                            registry_file_date), is_dir=True)
    write_sparse_dc(directory, ROLE_CONTENT,
                    {"sat:name": directory.name, "dc:description": ""})
    stamp = _stamp(created)
    record_fixity(directory, ROLE_CONTENT, command=command, version=version,
                  now=lambda: stamp)
    return id_record
