"""satlib.cascade — metadata resolution down the SAT tier cascade.

Implements the metadata cascade of the SAT Instance Initialisation
Sequence (Step 11) and the three-state field vocabulary:

    <calculated>    unresolved — a hole the cascade or tooling must
                    fill; a deliberate tripwire, never a fallback
    ""              deliberately empty — a real value that wins like
                    any other
    anything else   resolved

Resolution rules:

- Layers are ordered shallow to deep (SAT -> Collection -> Archive ->
  Content). The deepest concrete value for a field wins.
- <calculated> never wins over a concrete value from any layer: it is
  a hole, and the cascade is precisely the mechanism that fills
  holes. A field that is <calculated> at every contributing layer is
  unresolved, and verification must surface it as an error.
- dc:description is the canonical exception. It is never inherited —
  a description describes one entity, not its descendants — and it
  never carries <calculated>, because it is not inferable by tooling.
  An absent description resolves to the deliberate empty string; a
  <calculated> description at any layer is a violation in its own
  right.
- List-valued fields (dc:subject) currently follow the same
  deepest-wins replacement rule as scalars. Merge-versus-replace for
  dc:subject is an open decision; replacement is the provisional MVP
  behaviour and is pinned by a test marked as such.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from .assets import read_yaml_asset
from .roles import (
    NAME_FIELD,
    ROLE_ARCHIVE,
    ROLE_COLLECTION,
    ROLE_CONTENT,
    ROLE_SAT,
    has_role,
    read_role_yaml,
)

__all__ = [
    "CALCULATED",
    "DESCRIPTION_FIELD",
    "is_calculated",
    "cascade",
    "layers_for",
    "resolve_entity",
    "verify",
    "TripwireReport",
]

CALCULATED = "<calculated>"
DESCRIPTION_FIELD = "dc:description"

# Fields contributed by a level's language.yml. An archive's own
# language record overrides any inherited default (Step 11): the
# record is injected as an override layer at the level it belongs to.
_LANGUAGE_FIELDS = ("dc:language", "dc:language_bcp47")


def is_calculated(value: object) -> bool:
    """True for the unresolved placeholder, and only for it."""
    return value == CALCULATED


# ---------------------------------------------------------------------------
# Core resolution (pure)
# ---------------------------------------------------------------------------

def cascade(layers: Sequence[Mapping]) -> dict:
    """Resolve metadata layers, shallow to deep.

    Returns the resolved record. Fields whose only contributions are
    <calculated> remain <calculated> in the result so that verify()
    can trip on them; silently dropping them would hide exactly the
    error the placeholder exists to expose.
    """
    resolved: dict = {}
    holes: set[str] = set()

    for layer in layers:
        for key, value in layer.items():
            if key == DESCRIPTION_FIELD:
                continue  # never inherited; handled from the entity layer only
            if is_calculated(value):
                if key not in resolved:
                    holes.add(key)
                continue  # a hole never wins over a concrete value
            resolved[key] = value
            holes.discard(key)

    for key in holes:
        resolved[key] = CALCULATED  # left visible for the tripwire

    # dc:description: the entity's own layer only, defaulting to the
    # deliberate empty string. A <calculated> description is preserved
    # so verify() can report it as a violation.
    entity_layer = layers[-1] if layers else {}
    resolved[DESCRIPTION_FIELD] = entity_layer.get(DESCRIPTION_FIELD, "")

    return resolved


# ---------------------------------------------------------------------------
# Filesystem layer collection
# ---------------------------------------------------------------------------

def layers_for(root: Path, entity: Path,
               entity_is_dir: Optional[bool] = None) -> list[dict]:
    """Collect metadata layers in the ADR-025 section 7 tier order.

    The walk gathers, shallow to deep: the instance's sat role dc.yml;
    the owning collection's dc.yml (the deepest collection-declaring
    directory on the path, so a dual-role root and a single-role
    collection resolve by the same nearest-wins rule); the archive's
    dc.yml with its language.yml injected on top; each content
    organizing directory's dc.yml below the archive, outermost first;
    and for a file entity, the document's own content dc.yml beside it.

    The stagger is by tier, not by directory depth (ADR-025 section 8):
    the layers come from role directories, not folder boundaries.
    sat:name is a name record (ADR-024), not an inherited setting, so it
    is stripped from every layer before resolution.
    """
    entity = entity.resolve()
    root = root.resolve()
    try:
        relative = entity.relative_to(root)
    except ValueError:
        raise ValueError(f"{entity} is not inside cascade root {root}")

    if entity_is_dir is None:
        entity_is_dir = entity.is_dir()

    dirs = [root] + [root / Path(*relative.parts[: i + 1])
                     for i in range(len(relative.parts))]
    if not entity_is_dir:
        dirs = dirs[:-1]  # a file is not a directory level

    layers: list[dict] = []

    # Tier 1 — instance: the root's sat role.
    if has_role(root, ROLE_SAT, is_dir=True):
        layers.append(_role_dc(root, ROLE_SAT))

    # Tier 2 — collection: the deepest collection-declaring directory on
    # the path owns the document (nearest wins).
    collection_dir = _deepest_with_role(dirs, ROLE_COLLECTION)
    if collection_dir is not None:
        layers.append(_role_dc(collection_dir, ROLE_COLLECTION))

    # Tier 3 — archive: the deepest archive-declaring directory, its
    # language.yml injected over the archive layer.
    archive_dir = _deepest_with_role(dirs, ROLE_ARCHIVE)
    if archive_dir is not None:
        layers.append(_archive_layer(archive_dir))

    # Tier 4 — content organizing directories below the archive,
    # outermost first.
    base = archive_dir or collection_dir or root
    base_index = dirs.index(base) if base in dirs else 0
    for directory in dirs[base_index + 1:]:
        if has_role(directory, ROLE_CONTENT, is_dir=True):
            layers.append(_role_dc(directory, ROLE_CONTENT))

    # Tier 5 — the document's own content dc.yml, beside the file.
    if not entity_is_dir:
        layers.append(_role_dc(entity, ROLE_CONTENT, is_dir=False))

    return layers


def _role_dc(directory: Path, role: str, is_dir: bool = True) -> dict:
    """A role's dc.yml as a cascade layer, sans the sat:name record."""
    layer = read_role_yaml(directory, role, "dc.yml", is_dir=is_dir) or {}
    return {key: value for key, value in layer.items() if key != NAME_FIELD}


def _archive_layer(directory: Path) -> dict:
    """The archive dc.yml with its language.yml fields injected on top."""
    layer = _role_dc(directory, ROLE_ARCHIVE)
    language = read_role_yaml(directory, ROLE_ARCHIVE, "language.yml", is_dir=True)
    if language:
        layer = dict(layer)
        for key in _LANGUAGE_FIELDS:
            if key in language:
                layer[key] = language[key]
    return layer


def _deepest_with_role(dirs: list[Path], role: str) -> Optional[Path]:
    """The deepest directory on the path declaring a given role, or None."""
    for directory in reversed(dirs):
        if has_role(directory, role, is_dir=True):
            return directory
    return None


def resolve_entity(root: Path, entity: Path,
                   entity_is_dir: Optional[bool] = None) -> dict:
    """Resolved metadata record for an entity under a cascade root."""
    return cascade(layers_for(root, entity, entity_is_dir=entity_is_dir))


# ---------------------------------------------------------------------------
# The tripwire (Step 11 verification)
# ---------------------------------------------------------------------------

@dataclass
class TripwireReport:
    """Every offending field, reported together, never partially."""

    unresolved: list[str] = field(default_factory=list)
    description_violation: bool = False

    @property
    def clean(self) -> bool:
        return not self.unresolved and not self.description_violation

    def messages(self) -> list[str]:
        out = [
            f"{name}: still {CALCULATED} after cascade resolution — a "
            f"tooling error, not a fallback"
            for name in self.unresolved
        ]
        if self.description_violation:
            out.append(
                f"{DESCRIPTION_FIELD}: must never carry {CALCULATED}; it is "
                f"not inferable by tooling. An empty string is the "
                f"deliberate value for an absent description."
            )
        return out


def verify(record: Mapping) -> TripwireReport:
    """Trip on any field still <calculated> in a resolved record."""
    report = TripwireReport()
    for key, value in record.items():
        if not is_calculated(value):
            continue
        if key == DESCRIPTION_FIELD:
            report.description_violation = True
        else:
            report.unresolved.append(key)
    report.unresolved.sort()
    return report
