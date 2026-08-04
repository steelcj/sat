#
# source
#   project: sat
#   path: en/lib/satlib/tests/test_children.py
#
"""Tests for satlib.children: discovery per parent tier, the generated
record header, rebuild/read, refresh, and the ADR-024 findings grammar."""

import pytest

from satlib.children import (
    ChildFinding,
    child_role_for,
    compare_children,
    discover_children,
    read_children,
    refresh_children,
    write_children,
)
from satlib.identity import has_identity, write_identity
from satlib.roles import (
    ROLE_ARCHIVE,
    ROLE_COLLECTION,
    ROLE_CONTENT,
    ROLE_SAT,
    write_role_yaml,
)

CMD = "collection init"
VER = "0.7.0"
FIXED_NOW = "2026-07-15T09:00:00Z"


def _now():
    return FIXED_NOW


def _collection(directory, name, child_archives=()):
    """A collection directory declaring the collection role, with
    identified language archives beneath it."""
    directory.mkdir(parents=True, exist_ok=True)
    write_role_yaml(directory, ROLE_COLLECTION, "dc.yml", {"sat:name": name})
    if not has_identity(directory, ROLE_COLLECTION):  # idempotent for re-use
        write_identity(directory, ROLE_COLLECTION)
    archives = {}
    for lang in child_archives:
        archive = directory / lang
        archive.mkdir()
        write_role_yaml(archive, ROLE_ARCHIVE, "dc.yml", {"sat:name": lang})
        archives[lang] = write_identity(archive, ROLE_ARCHIVE)
    return archives


# ---------------------------------------------------------------------------
# child_role_for
# ---------------------------------------------------------------------------

def test_child_role_mapping():
    assert child_role_for(ROLE_SAT) == ROLE_COLLECTION
    assert child_role_for(ROLE_COLLECTION) == ROLE_ARCHIVE
    assert child_role_for(ROLE_ARCHIVE) == ROLE_CONTENT


def test_content_role_has_no_children_index():
    with pytest.raises(Exception):
        child_role_for(ROLE_CONTENT)


# ---------------------------------------------------------------------------
# Collection role indexes archives, keyed by name
# ---------------------------------------------------------------------------

def test_collection_indexes_archives_by_name(tmp_path):
    collection = tmp_path / "henson-catalog"
    archives = _collection(collection, "henson-catalog", child_archives=("en", "fr"))

    children = discover_children(collection, ROLE_COLLECTION)

    assert children == {"en": archives["en"], "fr": archives["fr"]}


# ---------------------------------------------------------------------------
# Instance role indexes collections, keyed by relative path
# ---------------------------------------------------------------------------

def test_instance_indexes_collections_by_relative_path(tmp_path):
    instance = tmp_path / "sat"
    instance.mkdir()
    # Dual-role instance: it declares the collection role itself.
    write_role_yaml(instance, ROLE_SAT, "dc.yml", {"sat:name": "sat"})
    write_identity(instance, ROLE_SAT)
    dual = _collection(instance, "sat", child_archives=("en",))
    # A single-role collection in the standard collections home.
    single = _collection(instance / "collections" / "test-collection",
                         "test-collection", child_archives=("en",))

    children = discover_children(instance, ROLE_SAT)

    # The dual-role collection keyed as itself ("."), the single-role by path.
    assert children["."]  # the dual-role collection's own identity
    assert "collections/test-collection" in children
    assert len(children) == 2


# ---------------------------------------------------------------------------
# Archive role indexes content organizing directories, by relative path
# ---------------------------------------------------------------------------

def test_archive_indexes_content_directories(tmp_path):
    archive = tmp_path / "en"
    archive.mkdir()
    write_role_yaml(archive, ROLE_ARCHIVE, "dc.yml", {"sat:name": "en"})
    products = archive / "products"
    products.mkdir()
    products_id = write_identity(products, ROLE_CONTENT)
    razors = archive / "products" / "razors"
    razors.mkdir()
    razors_id = write_identity(razors, ROLE_CONTENT)

    children = discover_children(archive, ROLE_ARCHIVE)

    assert children == {"products": products_id, "products/razors": razors_id}


# ---------------------------------------------------------------------------
# The generated record header, write/read roundtrip
# ---------------------------------------------------------------------------

def test_write_carries_the_generated_header(tmp_path):
    collection = tmp_path / "henson-catalog"
    _collection(collection, "henson-catalog", child_archives=("en",))
    path = refresh_children(collection, ROLE_COLLECTION, command=CMD, version=VER,
                            now=_now)
    text = path.read_text("utf-8")
    assert text.startswith(
        "# henson-catalog/.henson-catalog.assets/collection/children.yml\n")
    assert "collection children --rebuild" in text
    body = read_children(collection, ROLE_COLLECTION)
    assert body["sat_version"] == "0.1"
    assert body["generated"] == FIXED_NOW
    assert body["generated_by"] == {"command": CMD, "version": VER}
    assert set(body["children"]) == {"en"}


# ---------------------------------------------------------------------------
# Comparison: the ADR-024 findings grammar
# ---------------------------------------------------------------------------

def test_fresh_index_compares_clean(tmp_path):
    collection = tmp_path / "c"
    _collection(collection, "c", child_archives=("en", "fr"))
    refresh_children(collection, ROLE_COLLECTION, command=CMD, version=VER, now=_now)
    assert compare_children(collection, ROLE_COLLECTION) == []


def test_missing_index_reads_every_child_as_missing(tmp_path):
    collection = tmp_path / "c"
    _collection(collection, "c", child_archives=("en", "fr"))
    findings = compare_children(collection, ROLE_COLLECTION)
    assert {f.kind for f in findings} == {"missing-child"}
    assert {f.key for f in findings} == {"en", "fr"}


def test_new_archive_after_index_is_missing_child(tmp_path):
    collection = tmp_path / "c"
    _collection(collection, "c", child_archives=("en",))
    refresh_children(collection, ROLE_COLLECTION, command=CMD, version=VER, now=_now)
    _collection(collection, "c", child_archives=("fr",))  # add fr afterward
    findings = compare_children(collection, ROLE_COLLECTION)
    assert findings == [ChildFinding("missing-child", "fr",
                                     "fr on disk, absent from index")]


def test_removed_archive_is_extra_child(tmp_path):
    collection = tmp_path / "c"
    _collection(collection, "c", child_archives=("en", "fr"))
    refresh_children(collection, ROLE_COLLECTION, command=CMD, version=VER, now=_now)
    # The fr archive's role directory is removed from disk.
    import shutil
    shutil.rmtree(collection / "fr")
    findings = compare_children(collection, ROLE_COLLECTION)
    assert findings == [ChildFinding("extra-child", "fr",
                                     "fr in index, absent from disk")]
