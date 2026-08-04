#
# source
#   project: sat
#   path: en/lib/satlib/tests/test_reconcile.py
#
"""Tests for satlib.reconcile: the ADR-024 worked rename (break the
pairing with plain mv, watch reconciliation propose the repair, apply
it) and the safe move verb's four effects."""

import pytest

from satlib.children import read_children, refresh_children
from satlib.identity import write_identity
from satlib.reconcile import (
    apply_reconciliation,
    find_reconcilable,
    gather_evidence,
    move_archive,
    move_collection,
)
from satlib.roles import (
    ROLE_ARCHIVE,
    ROLE_COLLECTION,
    read_name,
    write_role_yaml,
)
from satlib.work import (
    assign_document_identity,
    compare_index,
    rebuild_index_data,
    write_work_index,
)

CMD = "collection reconcile --apply"
VER = "0.7.0"
NOW = "2026-07-15T12:00:00Z"


def _now():
    return NOW


def _collection_with_archive(tmp_path, archive_name="en"):
    """A collection with one identified archive and a fresh children index."""
    collection = tmp_path / "henson-catalog"
    collection.mkdir()
    write_role_yaml(collection, ROLE_COLLECTION, "dc.yml",
                    {"sat:name": "henson-catalog"})
    write_identity(collection, ROLE_COLLECTION)

    archive = collection / archive_name
    archive.mkdir()
    write_role_yaml(archive, ROLE_ARCHIVE, "dc.yml", {"sat:name": archive_name})
    archive_id = write_identity(archive, ROLE_ARCHIVE)

    refresh_children(collection, ROLE_COLLECTION, command="collection init",
                     version=VER, now=_now)
    return collection, archive, archive_id


# ---------------------------------------------------------------------------
# The ADR-024 worked rename: plain mv, then reconcile
# ---------------------------------------------------------------------------

def test_plain_mv_orphans_the_assets(tmp_path):
    collection, archive, archive_id = _collection_with_archive(tmp_path)
    # A plain rename: the directory moves, its inside assets keep the old name.
    archive.rename(collection / "english")

    findings = find_reconcilable(collection)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.kind == "orphaned-assets"
    assert finding.proposal is not None
    assert finding.proposal.old_name == "en"
    assert finding.proposal.new_name == "english"
    assert finding.proposal.identity == archive_id
    # the parent index still knew the old pairing — confident evidence
    assert finding.evidence["parent index"] == "confirms"


def test_evidence_reads_identity_and_self_name(tmp_path):
    collection, archive, archive_id = _collection_with_archive(tmp_path)
    archive.rename(collection / "english")
    orphan = collection / "english" / ".en.assets"

    evidence = gather_evidence(collection, orphan)

    assert evidence.identity == archive_id
    assert evidence.self_name == "en"        # proves the past pairing
    assert evidence.candidate == collection / "english"
    assert evidence.parent_confirms


def test_apply_repairs_the_pairing(tmp_path):
    collection, archive, archive_id = _collection_with_archive(tmp_path)
    archive.rename(collection / "english")
    english = collection / "english"

    proposal = find_reconcilable(collection)[0].proposal
    apply_reconciliation(proposal, command=CMD, version=VER, now=_now)

    # The assets directory now matches the entity.
    assert (english / ".english.assets").is_dir()
    assert not (english / ".en.assets").exists()
    # sat:name updated to the new name.
    assert read_name(english, ROLE_ARCHIVE) == "english"
    # The parent children index is rebuilt and keyed by the new name.
    children = read_children(collection, ROLE_COLLECTION)["children"]
    assert children == {"english": archive_id}
    # No orphans remain.
    assert find_reconcilable(collection) == []


def test_identityless_orphan_reported_without_a_proposal(tmp_path):
    """An assets directory with no identity gets no confident proposal."""
    collection = tmp_path / "c"
    (collection / "ghost").mkdir(parents=True)
    # An assets directory declaring a role but carrying no identity record.
    role_dir = collection / "ghost" / ".stray.assets" / ROLE_ARCHIVE
    role_dir.mkdir(parents=True)
    (role_dir / "dc.yml").write_text("sat:name: stray\n", "utf-8")

    findings = find_reconcilable(collection)

    assert len(findings) == 1
    assert findings[0].proposal is None  # never resolved by guess


# ---------------------------------------------------------------------------
# Cross-archive: a language question, never a rename (ADR-024 section 6)
# ---------------------------------------------------------------------------

def test_cross_archive_candidate_is_not_proposed_as_a_rename(tmp_path):
    collection, archive, _ = _collection_with_archive(tmp_path, archive_name="en")
    # A second archive, and a document in en/ with content identity.
    fr = collection / "fr"
    fr.mkdir()
    write_role_yaml(fr, ROLE_ARCHIVE, "dc.yml", {"sat:name": "fr"})
    write_identity(fr, ROLE_ARCHIVE)
    guide = collection / "en" / "guide.md"
    guide.write_text("# Guide\n", "utf-8")
    assign_document_identity(guide)
    # Plain mv the document across the archive boundary; its assets stay.
    guide.rename(collection / "fr" / "guide.md")

    findings = find_reconcilable(collection)

    # The orphaned en assets match a guide.md now in fr/ — a different
    # language archive. That is a language question, not a rename.
    match = [f for f in findings if "different language archive" in f.what]
    assert len(match) == 1
    assert match[0].proposal is None                 # never re-paired
    assert "language question" in match[0].means
    assert "ADR-001" in match[0].means


# ---------------------------------------------------------------------------
# The safe move verb: the four effects
# ---------------------------------------------------------------------------

def test_move_archive_dry_run_writes_nothing(tmp_path):
    collection, archive, _ = _collection_with_archive(tmp_path)

    plan = move_archive(archive, "eng", collection=collection,
                        command="archive mv", version=VER, apply=False, now=_now)

    assert archive.exists()                     # nothing moved
    assert not (collection / "eng").exists()
    assert any("digests unchanged" in line for line in plan)
    assert any("work index" in line for line in plan)


def test_move_archive_apply_performs_the_four_effects(tmp_path):
    collection, archive, archive_id = _collection_with_archive(tmp_path)

    move_archive(archive, "eng", collection=collection,
                 command="archive mv", version=VER, apply=True, now=_now)

    eng = collection / "eng"
    assert eng.is_dir()                                     # 1. renamed
    assert (eng / ".eng.assets").is_dir()
    assert read_name(eng, ROLE_ARCHIVE) == "eng"           # 2. sat:name
    children = read_children(collection, ROLE_COLLECTION)["children"]
    assert children == {"eng": archive_id}                 # 3. children index


def test_reconciled_archive_rename_refreshes_the_work_index(tmp_path):
    """Repairing an archive rename leaves the work index matching the
    sidecars — the same effect the safe mv verb maintains."""
    collection, archive, _ = _collection_with_archive(tmp_path, archive_name="en")
    doc = archive / "doc.md"
    doc.write_text("# Doc\n", "utf-8")
    assign_document_identity(doc)
    write_work_index(collection, rebuild_index_data(collection),
                     command="collection init", version=VER, now=_now)

    archive.rename(collection / "english")           # plain mv
    proposal = find_reconcilable(collection)[0].proposal
    apply_reconciliation(proposal, command=CMD, version=VER, now=_now)

    # The work index now agrees with the sidecars at the new path.
    assert compare_index(collection) == []


def test_move_collection_renames_and_reindexes(tmp_path):
    instance = tmp_path / "sat"
    instance.mkdir()
    write_role_yaml(instance, "sat", "dc.yml", {"sat:name": "sat"})
    write_identity(instance, "sat")
    collection = instance / "collections" / "old-name"
    collection.mkdir(parents=True)
    write_role_yaml(collection, ROLE_COLLECTION, "dc.yml", {"sat:name": "old-name"})
    collection_id = write_identity(collection, ROLE_COLLECTION)
    refresh_children(instance, "sat", command="collection init", version=VER, now=_now)

    move_collection(collection, "new-name", parent=instance,
                    command="collection mv", version=VER, apply=True, now=_now)

    new = instance / "collections" / "new-name"
    assert new.is_dir()
    assert read_name(new, ROLE_COLLECTION) == "new-name"
    children = read_children(instance, "sat")["children"]
    assert children == {"collections/new-name": collection_id}
