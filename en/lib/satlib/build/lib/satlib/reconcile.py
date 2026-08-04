#
# source
#   project: sat
#   path: en/lib/satlib/satlib/reconcile.py
#
"""satlib.reconcile — secondary discovery and the safe move (ADR-024).

Primary discovery is a pure read of declared roles (satlib.roles). When
a plain ``mv`` breaks the pairing between an entity and its assets
directory — ADR-018 names the assets directory after the entity, and
names are mutable filesystem metadata — tooling enters reconciliation:
it gathers evidence, proposes the repair, and never acts on its own.

Evidence is weighed in the ADR-024 section 4 hierarchy, strongest
first: the orphan's identity (the one value that survives every move),
its self-recorded ``sat:name`` (proving its past pairing), the parent's
children index (proving what the parent last knew), the fixity digest
(content sameness, corroboration), and filesystem metadata
(corroboration only, never a sole basis). Proposals speak the ADR-024
findings grammar and are dry-run by default; ``apply_reconciliation``
performs the re-pair and refreshes the parent index.

The safe move is the forward path: ``move_collection`` and
``move_archive`` rename the entity and its assets directory as one act
and maintain the records that reference them — the four effects of
ADR-024 section 6, and nothing more. Digests never change (paths move,
content does not). A move between language archives is never a rename
(ADR-001). Reconciliation enforces that half of the rule now: a
candidate found in a different language archive is excluded as a re-pair
and reported as a language question, never proposed as a rename. The
mv-side refusal — a verb that declines a cross-archive destination —
awaits the deferred document and content ``mv`` verbs; the current
collection and archive verbs rename within one parent, so no move they
can express crosses an archive boundary. ``CrossArchiveMoveError`` is
provided for those deferred verbs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .assets import (
    assets_name_for,
    entity_name_for,
    find_orphans,
    is_assets_name,
)
from .children import child_role_for, read_children, refresh_children
from .roles import (
    DC_RECORD,
    NAME_FIELD,
    ROLE_ARCHIVE,
    ROLE_COLLECTION,
    ROLE_SAT,
    ROLES,
    read_name,
    write_name,
)
from .work import rebuild_index_data, write_work_index

__all__ = [
    "ReconcileError",
    "CrossArchiveMoveError",
    "Evidence",
    "Proposal",
    "ReconcileFinding",
    "gather_evidence",
    "find_reconcilable",
    "apply_reconciliation",
    "move_collection",
    "move_archive",
]


class ReconcileError(RuntimeError):
    """Base class for reconciliation and safe-move refusals."""


class CrossArchiveMoveError(ReconcileError):
    """A move would cross a language-archive boundary.

    Language is filesystem structure (ADR-001), so moving content into a
    different language archive changes its expression's language, not
    its path — a semantic act with one-expression-per-language
    consequences (ADR-022), never a rename.
    """

    def __init__(self, source: Path, destination: Path):
        self.source = source
        self.destination = destination
        super().__init__(
            f"REFUSED: moving {source} to {destination} crosses a language "
            f"archive boundary. A move between language archives is never a "
            f"rename — it would change the expression's language (ADR-001, "
            f"ADR-022). Assign the target language deliberately instead."
        )


# ---------------------------------------------------------------------------
# Evidence gathering (ADR-024 section 4)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Evidence:
    """What reconciliation knows about an orphaned assets directory."""
    orphan_assets: Path
    role: Optional[str]
    old_name: str
    identity: Optional[str]
    self_name: Optional[str]
    candidate: Optional[Path]
    parent_confirms: bool
    cross_archive: bool = False


@dataclass(frozen=True)
class Proposal:
    """A confident re-pair: rename the assets, fix the name, reindex."""
    orphan_assets: Path
    candidate: Path
    role: str
    old_name: str
    new_name: str
    identity: Optional[str]


@dataclass(frozen=True)
class ReconcileFinding:
    """One reconciliation finding in the ADR-024 grammar."""
    kind: str          # orphaned-assets | staging-unmatched | ambiguous
    what: str
    means: str
    evidence: dict = field(default_factory=dict)
    do: str = ""
    severity: str = "soft"
    proposal: Optional[Proposal] = None


def _declared_roles_of_assets(assets_dir: Path) -> list[str]:
    """The roles an orphaned assets directory declares, read directly."""
    return [role for role in ROLES if (assets_dir / role).is_dir()]


def _read_yaml(path: Path) -> Optional[dict]:
    import yaml
    try:
        loaded = yaml.safe_load(path.read_text("utf-8"))
    except FileNotFoundError:
        return None
    return loaded if isinstance(loaded, dict) else {}


def gather_evidence(root: Path, orphan_assets: Path) -> Evidence:
    """Weigh the evidence for one orphaned assets directory.

    The directory-rename case (the ADR-024 worked example): a directory
    renamed with plain mv carries its inside assets along but leaves the
    assets name pointing at the old entity. The candidate is the
    containing directory whose name no longer matches the assets, when
    that directory has no assets of its own.
    """
    old_name = entity_name_for(orphan_assets.name) or orphan_assets.name
    roles = _declared_roles_of_assets(orphan_assets)
    role = roles[0] if roles else None

    identity = self_name = None
    if role is not None:
        identity_record = _read_yaml(orphan_assets / role / "identity.yml")
        identity = (identity_record or {}).get("dc:identifier")
        dc_record = _read_yaml(orphan_assets / role / DC_RECORD)
        self_name = (dc_record or {}).get(NAME_FIELD)

    candidate = None
    container = orphan_assets.parent
    if container != orphan_assets and container.name != old_name:
        # The orphan sits inside a directory whose name it no longer
        # matches: the renamed directory is the candidate, provided it
        # carries no proper assets of its own.
        proper = container / assets_name_for(container.name)
        if not proper.exists():
            candidate = container
    if candidate is None:
        # No directory-rename candidate: look for an unadorned entity
        # elsewhere bearing the orphan's name (the file-rename or the
        # moved-expression case).
        candidate = _find_named_candidate(root, self_name or old_name)

    # A candidate in a different language archive is a language question,
    # not a rename (ADR-001, ADR-024 section 6): keep it for narration but
    # never propose the re-pair.
    cross_archive = bool(
        candidate is not None and crosses_archive(orphan_assets, candidate, root))

    parent_confirms = _parent_confirms(root, candidate, role, identity)
    return Evidence(orphan_assets, role, old_name, identity, self_name,
                    candidate, parent_confirms, cross_archive)


def _find_named_candidate(root: Path, name: Optional[str]) -> Optional[Path]:
    """An unadorned entity elsewhere in the tree bearing a given name.

    Returns the match only when exactly one exists: ambiguity is reported
    as a finding, never resolved by guess (ADR-024).
    """
    if not name:
        return None
    matches = [
        path for path in root.rglob(name)
        if not any(is_assets_name(part)
                   for part in path.relative_to(root).parts)
    ]
    return matches[0] if len(matches) == 1 else None


def _parent_confirms(root: Path, candidate: Optional[Path],
                     role: Optional[str], identity: Optional[str]) -> bool:
    """True if the candidate's parent children index knows this identity."""
    if candidate is None or role is None or identity is None:
        return False
    parent = candidate.parent
    for parent_role in (ROLE_COLLECTION, ROLE_ARCHIVE):
        try:
            child_role_for(parent_role)
        except Exception:
            continue
        body = read_children(parent, parent_role)
        if body and identity in (body.get("children") or {}).values():
            return True
    return False


def find_reconcilable(root: Path) -> list[ReconcileFinding]:
    """Every orphaned assets directory under root, with its proposal.

    Dry-run by construction: this function only reads and proposes.
    Confident proposals carry a Proposal; ambiguous or identity-less
    orphans are reported without one, never resolved by guess.
    """
    findings: list[ReconcileFinding] = []
    for orphan in find_orphans(root):
        if orphan.reason != "no-entity":
            continue  # misplaced/collision are validation findings, not moves
        evidence = gather_evidence(root, orphan.assets_path)
        findings.append(_finding_from(evidence))
    return findings


def _finding_from(evidence: Evidence) -> ReconcileFinding:
    ev = {
        "identity": evidence.identity,
        "self-record": f"{NAME_FIELD}: {evidence.self_name}"
        if evidence.self_name else None,
        "parent index": "confirms" if evidence.parent_confirms else "silent",
        "candidate": str(evidence.candidate) if evidence.candidate else None,
    }
    if evidence.cross_archive and evidence.candidate is not None:
        # A move between language archives changes the expression's
        # language, not its path — for the operator, never a rename.
        return ReconcileFinding(
            kind="orphaned-assets",
            what=f"{evidence.orphan_assets.name} matches {evidence.candidate} "
                 f"in a different language archive",
            means="a move between language archives is a language question, "
                  "not a rename (ADR-001): the expression's language would "
                  "change. Reported for the operator, never re-paired.",
            evidence=ev,
            severity="soft",
        )
    if (evidence.candidate is not None and evidence.role is not None
            and evidence.identity is not None):
        new_name = evidence.candidate.name
        proposal = Proposal(
            orphan_assets=evidence.orphan_assets,
            candidate=evidence.candidate,
            role=evidence.role,
            old_name=evidence.old_name,
            new_name=new_name,
            identity=evidence.identity,
        )
        do = (f"rename {assets_name_for(evidence.old_name)} to "
              f"{assets_name_for(new_name)}; update {NAME_FIELD} to "
              f"{new_name}; rebuild the parent children index")
        if evidence.role == ROLE_ARCHIVE:
            do += "; refresh the work index where expression paths changed"
        return ReconcileFinding(
            kind="orphaned-assets",
            what=f"{evidence.orphan_assets.name} has no entity "
                 f"'{evidence.old_name}'",
            means=f"the entity was renamed to '{new_name}' with plain mv; "
                  f"its assets kept the old name",
            evidence=ev,
            do=do,
            severity="soft",
            proposal=proposal,
        )
    return ReconcileFinding(
        kind="orphaned-assets",
        what=f"{evidence.orphan_assets.name} has no matching entity",
        means="the pairing is broken and the evidence is not conclusive; "
              "reported for the operator, never resolved by guess",
        evidence=ev,
        severity="soft",
    )


# ---------------------------------------------------------------------------
# Applying a reconciliation
# ---------------------------------------------------------------------------

def apply_reconciliation(proposal: Proposal, *, command: str, version: str,
                         now: Optional[Callable[[], str]] = None) -> None:
    """Perform a proposed re-pair: rename assets, fix sat:name, reindex.

    An archive re-pair also refreshes the collection's work index, because
    the rename changed every expression path beneath the archive — the
    same effect the safe mv verb maintains (ADR-024 section 6, ADR-022).
    """
    candidate = proposal.candidate
    old_assets = candidate / assets_name_for(proposal.old_name)
    new_assets = candidate / assets_name_for(proposal.new_name)
    if old_assets.exists():
        old_assets.rename(new_assets)
    write_name(candidate, proposal.role, proposal.new_name)
    _refresh_parent_index(candidate, proposal.role, command=command,
                          version=version, now=now)
    if proposal.role == ROLE_ARCHIVE:
        collection = candidate.parent
        write_work_index(collection, rebuild_index_data(collection),
                         command=command, version=version,
                         **({"now": now} if now else {}))


# ---------------------------------------------------------------------------
# The safe move (ADR-024 section 6): the four effects, and no more
# ---------------------------------------------------------------------------

def move_collection(collection: Path, new_name: str, *, parent: Path,
                    command: str, version: str, apply: bool = False,
                    now: Optional[Callable[[], str]] = None) -> list[str]:
    """Rename a collection directory, maintaining its records.

    Renaming a collection touches none of its internal work-index
    entries (their paths are relative to the collection root), so only
    the rename pair, the sat:name update, and the parent's children
    index change.
    """
    # A collection's parent index is the instance's sat role.
    return _move(collection, new_name, role=ROLE_COLLECTION, parent=parent,
                 parent_role=ROLE_SAT, refresh_work_index_root=None,
                 command=command, version=version, apply=apply, now=now)


def move_archive(archive: Path, new_name: str, *, collection: Path,
                 command: str, version: str, apply: bool = False,
                 now: Optional[Callable[[], str]] = None) -> list[str]:
    """Rename a language archive directory, maintaining its records.

    Renaming an archive changes every expression path beneath it, so the
    collection's work index is refreshed in addition to the rename pair,
    the sat:name update, and the collection's children index.
    """
    return _move(archive, new_name, role=ROLE_ARCHIVE, parent=collection,
                 parent_role=ROLE_COLLECTION,
                 refresh_work_index_root=collection,
                 command=command, version=version, apply=apply, now=now)


def _move(entity: Path, new_name: str, *, role: str, parent: Path,
          parent_role: str, refresh_work_index_root: Optional[Path],
          command: str, version: str, apply: bool,
          now: Optional[Callable[[], str]]) -> list[str]:
    old_name = entity.name
    destination = entity.parent / new_name

    plan = [
        f"rename {entity} -> {destination} (entity and .assets as one act)",
        f"update {NAME_FIELD} in the {role} role: {old_name} -> {new_name}",
        f"refresh the {parent_role} children index at {parent}",
    ]
    if refresh_work_index_root is not None:
        plan.append(f"refresh the work index at {refresh_work_index_root} "
                    f"(expression paths beneath the archive changed)")
    plan.append("digests unchanged (paths move, content does not)")

    if not apply:
        return plan

    # 1. Rename the entity directory; its inside assets move with it.
    entity.rename(destination)
    old_assets = destination / assets_name_for(old_name)
    new_assets = destination / assets_name_for(new_name)
    if old_assets.exists():
        old_assets.rename(new_assets)

    # 2. sat:name.
    write_name(destination, role, new_name)

    # 3. Parent children index.
    _refresh_parent_index(destination, role, command=command, version=version,
                          now=now, parent=parent, parent_role=parent_role)

    # 4. Work index where paths changed.
    if refresh_work_index_root is not None:
        works = rebuild_index_data(refresh_work_index_root)
        write_work_index(refresh_work_index_root, works,
                         command=command, version=version,
                         **({"now": now} if now else {}))

    return plan


def _refresh_parent_index(entity: Path, role: str, *, command: str,
                          version: str, now: Optional[Callable[[], str]],
                          parent: Optional[Path] = None,
                          parent_role: Optional[str] = None) -> None:
    """Rebuild the parent's children index after a re-pair or move."""
    if parent is None:
        parent = entity.parent
    if parent_role is None:
        parent_role = ROLE_COLLECTION if role == ROLE_ARCHIVE else ROLE_SAT
    kwargs = {"command": command, "version": version}
    if now is not None:
        kwargs["now"] = now
    refresh_children(parent, parent_role, **kwargs)


def crosses_archive(source: Path, destination: Path, root: Path) -> bool:
    """True if source and destination lie under different language archives."""
    return _archive_of(source, root) != _archive_of(destination, root)


def _archive_of(path: Path, root: Path) -> Optional[str]:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    parts = [p for p in relative.parts if not is_assets_name(p)]
    return parts[0] if parts else None
