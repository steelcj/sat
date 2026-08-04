#
# source
#   project: sat
#   path: en/lib/satlib/tests/test_create.py
#
"""Tests for satlib.create: the instance, collection, and content-
directory role creators, and the full chain resolving through the
cascade (ADR-025, ADR-026)."""

import datetime

import pytest

from satlib.assets import read_yaml_asset
from satlib.cascade import CALCULATED, resolve_entity, verify
from satlib.create import (
    COLLECTIONS_HOME_FIELD,
    create_collection_role,
    create_content_directory,
    create_instance_role,
)
from satlib.fixity import check_fixity
from satlib.identity import IdentityExistsError
from satlib.roles import (
    ROLE_COLLECTION,
    ROLE_CONTENT,
    ROLE_SAT,
    declared_roles,
    read_name,
)

VER = "0.7.0"
FIXED = datetime.datetime(2026, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)


def _now():
    return FIXED


# ---------------------------------------------------------------------------
# Instance role
# ---------------------------------------------------------------------------

def test_instance_role_states_settings_and_arms_holes(tmp_path):
    root = tmp_path / "my-sat"
    root.mkdir()
    create_instance_role(root, version=VER, creator="Christopher Steel",
                         now=_now)

    dc = read_yaml_asset(root, f"{ROLE_SAT}/dc.yml", is_dir=True)
    assert dc["sat:name"] == "my-sat"
    assert dc[COLLECTIONS_HOME_FIELD] == "collections"
    assert dc["dc:creator"] == "Christopher Steel"     # supplied -> stated
    assert dc["dc:rights"] == CALCULATED               # absent -> tripwire armed
    # Fixity baseline recorded at creation and clean.
    assert check_fixity(root, ROLE_SAT) == []


def test_instance_role_refuses_recreation(tmp_path):
    root = tmp_path / "my-sat"
    root.mkdir()
    create_instance_role(root, version=VER, now=_now)
    with pytest.raises(IdentityExistsError):
        create_instance_role(root, version=VER, now=_now)


def test_collections_home_is_configurable(tmp_path):
    root = tmp_path / "mon-sat"
    root.mkdir()
    create_instance_role(root, version=VER, collections_home="collections-fr",
                         now=_now)
    dc = read_yaml_asset(root, f"{ROLE_SAT}/dc.yml", is_dir=True)
    assert dc[COLLECTIONS_HOME_FIELD] == "collections-fr"


# ---------------------------------------------------------------------------
# Collection role
# ---------------------------------------------------------------------------

def test_collection_role_is_sparse_with_declaration(tmp_path):
    collection = tmp_path / "test-collection"
    collection.mkdir()
    create_collection_role(collection, version=VER, now=_now)

    # Sparse dc.yml led by the template comment.
    text = (collection / ".test-collection.assets" / ROLE_COLLECTION
            / "dc.yml").read_text("utf-8")
    assert text.startswith("# Settings flow down from the instance")
    dc = read_yaml_asset(collection, f"{ROLE_COLLECTION}/dc.yml", is_dir=True)
    assert dc["sat:name"] == "test-collection"
    assert dc["dc:type"] == "Collection"
    assert "dc:creator" not in dc  # inherits from the instance

    declaration = read_yaml_asset(collection, f"{ROLE_COLLECTION}/collection.yml",
                                  is_dir=True)
    assert declaration["sat:name"] == "test-collection"
    assert declaration["sat:relationships"] == {}


def test_dual_role_root_carries_both_roles(tmp_path):
    root = tmp_path / "sat"
    root.mkdir()
    create_instance_role(root, version=VER, now=_now)
    create_collection_role(root, version=VER, now=_now)
    assert declared_roles(root) == [ROLE_SAT, ROLE_COLLECTION]
    # Two identities, one per role.
    sat_id = read_yaml_asset(root, f"{ROLE_SAT}/identity.yml", is_dir=True)
    coll_id = read_yaml_asset(root, f"{ROLE_COLLECTION}/identity.yml", is_dir=True)
    assert sat_id["dc:identifier"] != coll_id["dc:identifier"]


# ---------------------------------------------------------------------------
# Content organizing directory
# ---------------------------------------------------------------------------

def test_content_directory_is_a_work(tmp_path):
    products = tmp_path / "products"
    products.mkdir()
    record = create_content_directory(products, version=VER, now=_now)
    assert "sat:work" in record
    assert read_name(products, ROLE_CONTENT) == "products"
    stored = read_yaml_asset(products, f"{ROLE_CONTENT}/identity.yml", is_dir=True)
    assert stored["dc:identifier"] == record["dc:identifier"]
    assert stored["sat:work"] == record["sat:work"]


# ---------------------------------------------------------------------------
# The chain resolves through the cascade
# ---------------------------------------------------------------------------

def test_full_chain_resolves_and_verifies_clean(tmp_path):
    from satlib.archive import create_archive, plan_archive
    from satlib.language import SubtagRegistry, validate_expression
    from tests.test_language import FIXTURE

    registry = SubtagRegistry.parse(FIXTURE)
    root = tmp_path / "sat"
    root.mkdir()
    create_instance_role(root, version=VER, creator="Christopher Steel",
                         publisher="SAT", rights="CC BY-SA 4.0", now=_now)
    create_collection_role(root, version=VER, now=_now)
    create_archive(plan_archive(root, validate_expression("en", registry),
                                tool="sat init", tool_version=VER,
                                registry_file_date=registry.file_date,
                                title="SAT Documentation (en)"),
                   command="sat init", version=VER)

    record = resolve_entity(root, root / "en")
    assert record["dc:creator"] == "Christopher Steel"   # from the instance
    assert record["dc:rights"] == "CC BY-SA 4.0"
    assert record["dc:language"] == "eng"
    assert verify(record).clean
