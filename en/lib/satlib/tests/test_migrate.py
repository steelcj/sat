#
# source
#   project: sat
#   path: en/lib/satlib/tests/test_migrate.py
#
"""Tests for satlib.migrate: the one-time 0.6.0 -> role-directory
migration (ADR-025 section 9). A synthetic 0.6.0 tree is built with flat
records and the old sat/ namespace, migrated dry-run then apply, and the
result verified against the role-directory layout."""

import pytest
import yaml

from satlib.assets import read_yaml_asset
from satlib.cascade import resolve_entity, verify
from satlib.migrate import MIGRATE_COMMAND, migrate, plan_migration
from satlib.roles import (
    ROLE_ARCHIVE,
    ROLE_COLLECTION,
    ROLE_SAT,
    declared_roles,
    read_name,
)

VER = "0.7.0"


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), "utf-8")


def _uuid(n):
    return f"urn:uuid:{n:08d}-0000-4000-8000-000000000000"


def _legacy_tree(tmp_path):
    """A 0.6.0 founding-repo shape: a dual-role root with flat records and
    the sat/ namespace, two archives, and two joined documents."""
    root = tmp_path / "my-sat"
    assets = root / ".my-sat.assets"

    # Flat instance records at the assets top level (0.6.0 placement).
    _write(assets / "identity.yml", {"dc:identifier": _uuid(1)})
    _write(assets / "provenance.yml", {
        "created": "2026-06-01T10:00:00+00:00", "tool": "sat-tools",
        "tool_version": "0.6.0", "registry_file_date": "2026-05-20"})
    _write(assets / "dc.yml", {
        "dc:creator": "Christopher Steel",
        "dc:publisher": "SAT – Source Archive Tools",
        "dc:rights": "CC BY-SA 4.0", "dc:description": ""})
    # The 0.6.0 work index in the sat/ operational namespace.
    _write(assets / "sat" / "work-index.yml", {"sat_version": "0.1", "works": {}})

    # Two language archives with flat records.
    work = _uuid(100)
    for i, (lang, iso) in enumerate((("en", "eng"), ("fr", "fra")), start=2):
        adir = root / lang
        aassets = adir / f".{lang}.assets"
        _write(aassets / "identity.yml", {"dc:identifier": _uuid(i)})
        _write(aassets / "provenance.yml", {
            "created": "2026-06-01T10:00:00+00:00", "tool": "sat-tools",
            "tool_version": "0.6.0", "registry_file_date": "2026-05-20"})
        _write(aassets / "dc.yml", {
            "dc:title": f"SAT Documentation ({lang})",
            "dc:creator": "<calculated>", "dc:rights": "<calculated>",
            "dc:language": iso, "dc:language_bcp47": lang, "dc:description": ""})
        _write(aassets / "language.yml", {
            "dc:language": iso, "dc:language_bcp47": lang,
            "sat:authority": "external"})
        # One document per archive, joined as one work, with 0.6.0 identity.
        doc = adir / "products" / f"guide-{lang}.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(f"# Guide {lang}\n", "utf-8")
        docassets = doc.parent / f".guide-{lang}.md.assets"
        _write(docassets / "sat" / "identity.yml",
               {"dc:identifier": _uuid(200 + i), "sat:work": work})
    return root


# ---------------------------------------------------------------------------
# Dry run writes nothing
# ---------------------------------------------------------------------------

def test_dry_run_writes_nothing(tmp_path):
    root = _legacy_tree(tmp_path)
    before = sorted(p.name for p in (root / ".my-sat.assets").iterdir())

    lines = plan_migration(root)

    assert any(line.startswith("MOVE") for line in lines)
    assert any("MINT" in line for line in lines)
    # The flat records are untouched by a dry run.
    after = sorted(p.name for p in (root / ".my-sat.assets").iterdir())
    assert before == after
    assert (root / ".my-sat.assets" / "identity.yml").is_file()  # still flat
    assert not (root / ".my-sat.assets" / ROLE_SAT / "identity.yml").is_file()


# ---------------------------------------------------------------------------
# Apply: the role-directory layout
# ---------------------------------------------------------------------------

def test_apply_moves_instance_records_into_sat_role(tmp_path):
    root = _legacy_tree(tmp_path)
    migrate(root, version=VER, apply=True)

    assets = root / ".my-sat.assets"
    # Flat records now live in the sat role; the flat copies are gone.
    assert (assets / ROLE_SAT / "identity.yml").is_file()
    assert (assets / ROLE_SAT / "provenance.yml").is_file()
    assert not (assets / "identity.yml").is_file()
    # The instance identity is preserved (continuity lives in sat/).
    assert read_yaml_asset(root, f"{ROLE_SAT}/identity.yml", is_dir=True) == \
        {"dc:identifier": _uuid(1)}
    # sat:name recorded.
    assert read_name(root, ROLE_SAT) == "my-sat"


def test_apply_mints_a_fresh_collection_role(tmp_path):
    root = _legacy_tree(tmp_path)
    migrate(root, version=VER, apply=True)

    # Dual-role root now declares both roles.
    assert declared_roles(root) == [ROLE_SAT, ROLE_COLLECTION]
    # The collection identity is fresh, not the instance's.
    sat_id = read_yaml_asset(root, f"{ROLE_SAT}/identity.yml", is_dir=True)
    coll_id = read_yaml_asset(root, f"{ROLE_COLLECTION}/identity.yml", is_dir=True)
    assert coll_id["dc:identifier"] != sat_id["dc:identifier"]
    # The collection provenance records creation by sat migrate, not the
    # instance's 2026-06-01 instantiation.
    prov = read_yaml_asset(root, f"{ROLE_COLLECTION}/provenance.yml", is_dir=True)
    assert prov["tool"] == MIGRATE_COMMAND
    assert prov["tool_version"] == VER
    assert not prov["created"].startswith("2026-06-01")
    # sat:name in both roles.
    assert read_name(root, ROLE_SAT) == "my-sat"
    assert read_name(root, ROLE_COLLECTION) == "my-sat"


def test_apply_moves_archive_records_and_documents(tmp_path):
    root = _legacy_tree(tmp_path)
    migrate(root, version=VER, apply=True)

    en = root / "en"
    assert (en / ".en.assets" / ROLE_ARCHIVE / "language.yml").is_file()
    assert (en / ".en.assets" / ROLE_ARCHIVE / "identity.yml").is_file()
    assert not (en / ".en.assets" / "language.yml").is_file()
    assert read_name(en, ROLE_ARCHIVE) == "en"

    # Document identity moved from sat/ to content/, old sat/ dir cleaned.
    doc_assets = en / "products" / ".guide-en.md.assets"
    assert (doc_assets / "content" / "identity.yml").is_file()
    assert not (doc_assets / "sat").exists()  # no stray sat role beside a file
    guide = en / "products" / "guide-en.md"
    assert declared_roles(guide, is_dir=False) == ["content"]


def test_apply_rebuilds_work_index_in_collection_role(tmp_path):
    root = _legacy_tree(tmp_path)
    migrate(root, version=VER, apply=True)

    assets = root / ".my-sat.assets"
    # Old namespace index deleted; rebuilt in the collection role.
    assert not (assets / "sat" / "work-index.yml").is_file()
    index = read_yaml_asset(root, f"{ROLE_COLLECTION}/work-index.yml", is_dir=True)
    # Both documents share one work with en and fr expressions.
    assert len(index["works"]) == 1
    (entry,) = index["works"].values()
    assert set(entry["languages"]) == {"en", "fr"}


def test_apply_builds_children_indexes(tmp_path):
    root = _legacy_tree(tmp_path)
    migrate(root, version=VER, apply=True)

    collection_children = read_yaml_asset(
        root, f"{ROLE_COLLECTION}/children.yml", is_dir=True)["children"]
    assert set(collection_children) == {"en", "fr"}


def test_migrated_tree_resolves_through_the_cascade(tmp_path):
    root = _legacy_tree(tmp_path)
    migrate(root, version=VER, apply=True)

    record = resolve_entity(root, root / "fr")
    assert record["dc:creator"] == "Christopher Steel"   # inherited from sat/
    assert record["dc:rights"] == "CC BY-SA 4.0"
    assert record["dc:language"] == "fra"                # archive language.yml
    assert verify(record).clean


def test_idempotent_second_run_is_a_noop(tmp_path):
    root = _legacy_tree(tmp_path)
    migrate(root, version=VER, apply=True)
    # A second migration finds no flat records to move.
    lines = migrate(root, version=VER, apply=True)
    assert not any(line.startswith("MOVE") for line in lines)
