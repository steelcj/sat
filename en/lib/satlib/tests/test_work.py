#
# source
#   project: sat
#   path: en/lib/satlib/tests/test_work.py
#
"""Tests for satlib.work: assignment, join, resolution, and the index.

The fixture builds a small mirrored collection — henson-catalog with en
and fr archives — because that is the worked example the governing ADR
uses. Ends with the staleness test: a moved file makes the index wrong,
compare reports it, rebuild repairs it.
"""

import pytest

from satlib.identity import is_valid_identifier
from satlib.work import (
    WORK_FIELD,
    WORK_RETIRED_FIELD,
    IDENTIFIER_FIELD,
    DocumentIdentityExistsError,
    DuplicateExpressionError,
    Finding,
    MalformedDocumentIdentityError,
    UnresolvedAddressError,
    WorkError,
    assign_document_identity,
    compare_index,
    has_document_identity,
    join_work,
    read_document_identity,
    read_work_index,
    rebuild_index_data,
    resolve_expression_of,
    update_index_for_document,
    write_work_index,
)

FIXED_NOW = "2026-07-12T21:47:12Z"
CMD = "collection work index --rebuild"
VER = "0.6.0-test"


def _now():
    return FIXED_NOW


@pytest.fixture
def collection(tmp_path):
    root = tmp_path / "henson-catalog"
    (root / "en" / "products").mkdir(parents=True)
    (root / "fr" / "produits").mkdir(parents=True)
    en = root / "en" / "products" / "razor-guide.md"
    fr = root / "fr" / "produits" / "guide-rasoir.md"
    en.write_text("# Razor Maintenance Guide\n", "utf-8")
    fr.write_text("# Guide d'entretien du rasoir\n", "utf-8")
    return root, en, fr


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------

def test_assignment_mints_both_uuids(collection):
    _, en, _ = collection
    record = assign_document_identity(en)
    assert is_valid_identifier(record[IDENTIFIER_FIELD])
    assert is_valid_identifier(record[WORK_FIELD])
    assert record[IDENTIFIER_FIELD] != record[WORK_FIELD]


def test_new_document_is_a_new_work(collection):
    _, en, fr = collection
    assert assign_document_identity(en)[WORK_FIELD] != \
        assign_document_identity(fr)[WORK_FIELD]


def test_index_excludes_inner_collection_documents(collection):
    """A dual-role collection's index excludes documents owned by a
    single-role collection under its collections home (ADR-025)."""
    from satlib.identity import write_identity
    from satlib.roles import ROLE_COLLECTION, write_role_yaml

    root, en, fr = collection
    assign_document_identity(en)
    assign_document_identity(fr)
    # A single-role collection below the root, with its own document.
    inner = root / "collections" / "other"
    (inner / "en").mkdir(parents=True)
    write_role_yaml(inner, ROLE_COLLECTION, "dc.yml", {"sat:name": "other"})
    write_identity(inner, ROLE_COLLECTION)
    inner_doc = inner / "en" / "theirs.md"
    inner_doc.write_text("# Theirs\n", "utf-8")
    assign_document_identity(inner_doc)

    works = rebuild_index_data(root)

    # The dual-role collection indexes only its own two expressions; the
    # inner collection's document is not mis-keyed under 'collections'.
    languages = {lang for entry in works.values() for lang in entry["languages"]}
    assert languages == {"en", "fr"}
    all_paths = {expr["path"] for entry in works.values()
                 for expr in entry["languages"].values()}
    assert not any("collections/other" in p for p in all_paths)


def test_declared_work_is_used(collection):
    _, en, fr = collection
    work = assign_document_identity(en)[WORK_FIELD]
    assert assign_document_identity(fr, work=work)[WORK_FIELD] == work


def test_assignment_refuses_existing_identity(collection):
    _, en, _ = collection
    assign_document_identity(en)
    with pytest.raises(DocumentIdentityExistsError):
        assign_document_identity(en)


def test_read_flags_missing_and_malformed(collection):
    _, en, _ = collection
    with pytest.raises(MalformedDocumentIdentityError):
        read_document_identity(en)


# ---------------------------------------------------------------------------
# Join
# ---------------------------------------------------------------------------

def test_join_moves_work_and_retires_previous(collection):
    _, en, fr = collection
    work = assign_document_identity(en)[WORK_FIELD]
    lone = assign_document_identity(fr)[WORK_FIELD]
    record = join_work(fr, work, now=_now)
    assert record[WORK_FIELD] == work
    assert record[WORK_RETIRED_FIELD] == [
        {"uuid": lone, "retired": FIXED_NOW,
         "by": "collection work join --apply"}
    ]


def test_join_preserves_identifier(collection):
    _, en, fr = collection
    work = assign_document_identity(en)[WORK_FIELD]
    identifier = assign_document_identity(fr)[IDENTIFIER_FIELD]
    assert join_work(fr, work, now=_now)[IDENTIFIER_FIELD] == identifier


def test_join_appends_across_joins(collection):
    _, en, fr = collection
    first = assign_document_identity(en)[WORK_FIELD]
    assign_document_identity(fr)
    join_work(fr, first, now=_now)
    second_record = join_work(fr, _fresh(), now=_now)
    assert len(second_record[WORK_RETIRED_FIELD]) == 2


def _fresh():
    from satlib.identity import new_identifier
    return new_identifier()


def test_join_to_current_work_is_refused(collection):
    _, en, _ = collection
    work = assign_document_identity(en)[WORK_FIELD]
    with pytest.raises(WorkError):
        join_work(en, work, now=_now)


# ---------------------------------------------------------------------------
# Address resolution
# ---------------------------------------------------------------------------

def test_resolve_by_file_path(collection):
    root, en, _ = collection
    work = assign_document_identity(en)[WORK_FIELD]
    assert resolve_expression_of("en/products/razor-guide.md", root) == work


def test_resolve_by_identifier(collection):
    root, en, _ = collection
    record = assign_document_identity(en)
    assert resolve_expression_of(record[IDENTIFIER_FIELD], root) == \
        record[WORK_FIELD]


def test_resolve_work_uuid_passes_through(collection):
    root, en, _ = collection
    work = assign_document_identity(en)[WORK_FIELD]
    assert resolve_expression_of(work, root) == work


def test_resolve_rejects_garbage(collection):
    root, _, _ = collection
    with pytest.raises(UnresolvedAddressError):
        resolve_expression_of("no/such/file.md", root)


# ---------------------------------------------------------------------------
# Index lifecycle
# ---------------------------------------------------------------------------

def _mirrored(collection):
    root, en, fr = collection
    work = assign_document_identity(en)[WORK_FIELD]
    assign_document_identity(fr, work=work)
    return root, en, fr, work


def test_rebuild_shape(collection):
    root, en, fr, work = _mirrored(collection)
    works = rebuild_index_data(root)
    assert set(works) == {work}
    langs = works[work]["languages"]
    assert set(langs) == {"en", "fr"}
    assert langs["en"]["path"] == "en/products/razor-guide.md"
    assert is_valid_identifier(langs["fr"]["identifier"])


def test_duplicate_same_language_expression_raises(collection):
    root, en, _, work = _mirrored(collection)
    sibling = root / "en" / "products" / "razor-guide-2.md"
    sibling.write_text("# Second claimant\n", "utf-8")
    assign_document_identity(sibling, work=work)
    with pytest.raises(DuplicateExpressionError):
        rebuild_index_data(root)


def test_write_and_read_roundtrip_with_header(collection):
    root, *_ = _mirrored(collection)
    path = write_work_index(root, rebuild_index_data(root),
                            command=CMD, version=VER, now=_now)
    text = path.read_text("utf-8")
    assert text.startswith(
        "# henson-catalog/.henson-catalog.assets/collection/work-index.yml\n")
    assert "collection work index --rebuild" in text
    body = read_work_index(root)
    assert body["sat_version"] == "0.1"
    assert body["generated"] == FIXED_NOW
    assert body["generated_by"] == {"command": CMD, "version": VER}


def test_incremental_update_equals_full_rebuild(collection):
    root, en, fr, work = _mirrored(collection)
    write_work_index(root, rebuild_index_data(root),
                     command=CMD, version=VER, now=_now)
    late = root / "fr" / "produits" / "nouveau.md"
    late.write_text("# Nouveau\n", "utf-8")
    assign_document_identity(late)
    update_index_for_document(root, late, command="content ingress",
                              version=VER, now=_now)
    assert read_work_index(root)["works"] == rebuild_index_data(root)


def test_incremental_update_reflects_join(collection):
    root, en, fr, work = _mirrored(collection)
    write_work_index(root, rebuild_index_data(root),
                     command=CMD, version=VER, now=_now)
    late = root / "fr" / "produits" / "nouveau.md"
    late.write_text("# Nouveau\n", "utf-8")
    assign_document_identity(late)
    update_index_for_document(root, late, command="content ingress",
                              version=VER, now=_now)
    # Join can't target work (fr taken) — use a new en doc's lone work.
    en2 = root / "en" / "products" / "nouveau-en.md"
    en2.write_text("# New EN\n", "utf-8")
    target = assign_document_identity(en2)[WORK_FIELD]
    join_work(late, target, now=_now)
    update_index_for_document(root, late, command="collection work join --apply",
                              version=VER, now=_now)
    update_index_for_document(root, en2, command="content ingress",
                              version=VER, now=_now)
    assert read_work_index(root)["works"] == rebuild_index_data(root)


def test_missing_index_rebuilds_on_update(collection):
    root, en, *_ = _mirrored(collection)
    update_index_for_document(root, en, command="content ingress",
                              version=VER, now=_now)
    assert read_work_index(root)["works"] == rebuild_index_data(root)


# ---------------------------------------------------------------------------
# Staleness: sidecars canonical, index wrong by definition
# ---------------------------------------------------------------------------

def test_move_makes_index_stale_and_compare_reports_it(collection):
    root, en, fr, work = _mirrored(collection)
    write_work_index(root, rebuild_index_data(root),
                     command=CMD, version=VER, now=_now)
    assert compare_index(root) == []
    moved = root / "fr" / "produits" / "guide-rasoir-v2.md"
    fr.rename(moved)
    assets = fr.parent / ".guide-rasoir.md.assets"
    assets.rename(moved.parent / ".guide-rasoir-v2.md.assets")
    findings = compare_index(root)
    assert any(f.kind == "stale-path" and f.language == "fr"
               for f in findings)
    write_work_index(root, rebuild_index_data(root),
                     command=CMD, version=VER, now=_now)
    assert compare_index(root) == []


def test_compare_flags_extra_work(collection):
    root, *_ = _mirrored(collection)
    works = rebuild_index_data(root)
    works["urn:uuid:00000000-0000-4000-8000-000000000000"] = {
        "languages": {"en": {"identifier":
                             "urn:uuid:00000000-0000-4000-8000-000000000001",
                             "path": "en/ghost.md"}}}
    write_work_index(root, works, command=CMD, version=VER, now=_now)
    assert any(f.kind == "extra-work" for f in compare_index(root))
