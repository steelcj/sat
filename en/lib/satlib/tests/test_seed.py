#
# source
#   project: sat
#   path: en/lib/satlib/tests/test_seed.py
#
"""Tests for satlib.seed: the example collection joined as one work, the
staged samples with the deliberately misfiled document, and seeded
documentation — the standing-integration-test property (ADR-026)."""

import datetime

import pytest

from satlib.assets import read_yaml_asset
from satlib.cascade import resolve_entity, verify
from satlib.children import read_children
from satlib.create import create_collection_role, create_instance_role
from satlib.language import SubtagRegistry, validate_expression
from satlib.roles import ROLE_ARCHIVE, ROLE_COLLECTION, ROLE_SAT, declared_roles
from satlib.seed import MISFILED_SAMPLE, seed_documentation, seed_example_collection
from satlib.work import has_document_identity, read_work_index
from tests.test_language import FIXTURE

VER = "0.7.0"
FIXED = datetime.datetime(2026, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)


def _now():
    return FIXED


@pytest.fixture(scope="module")
def registry():
    return SubtagRegistry.parse(FIXTURE)


@pytest.fixture
def instance(tmp_path):
    root = tmp_path / "sat"
    root.mkdir()
    create_instance_role(root, version=VER, creator="Christopher Steel",
                         publisher="SAT", rights="CC BY-SA 4.0", now=_now)
    create_collection_role(root, version=VER, now=_now)
    return root


def _validations(registry, *langs):
    return [validate_expression(lang, registry) for lang in langs]


# ---------------------------------------------------------------------------
# The example collection
# ---------------------------------------------------------------------------

def test_example_collection_is_single_role(instance, registry):
    collection = seed_example_collection(
        instance, _validations(registry, "en", "fr"),
        collections_home="collections", version=VER, now=_now)
    assert collection == instance / "collections" / "test-collection"
    assert declared_roles(collection) == [ROLE_COLLECTION]


def test_samples_are_joined_as_one_work(instance, registry):
    collection = seed_example_collection(
        instance, _validations(registry, "en", "fr"),
        collections_home="collections", version=VER, now=_now)

    index = read_work_index(collection)
    assert len(index["works"]) == 1                 # one work
    (entry,) = index["works"].values()
    assert set(entry["languages"]) == {"en", "fr"}  # two expressions
    # Both sample documents carry identity.
    assert has_document_identity(collection / "en" / "sample.md")
    assert has_document_identity(collection / "fr" / "sample-fr.md")


def test_collection_children_index_lists_the_archives(instance, registry):
    collection = seed_example_collection(
        instance, _validations(registry, "en", "fr"),
        collections_home="collections", version=VER, now=_now)
    children = read_children(collection, ROLE_COLLECTION)["children"]
    assert set(children) == {"en", "fr"}


def test_sample_resolves_project_rights_through_the_cascade(instance, registry):
    collection = seed_example_collection(
        instance, _validations(registry, "en", "fr"),
        collections_home="collections", version=VER, now=_now)
    record = resolve_entity(instance, collection / "en" / "sample.md",
                            entity_is_dir=False)
    # Inherited from the instance, through the single-role collection.
    assert record["dc:rights"] == "CC BY-SA 4.0"
    assert record["dc:creator"] == "Christopher Steel"
    assert record["dc:language"] == "eng"


# ---------------------------------------------------------------------------
# Staged samples
# ---------------------------------------------------------------------------

def test_staging_holds_the_pair_and_the_misfiled_document(instance, registry):
    collection = seed_example_collection(
        instance, _validations(registry, "en", "fr"),
        collections_home="collections", version=VER, sample_content=True,
        now=_now)
    staging = collection / "staging"
    assert (staging / "welcome.md").is_file()
    assert (staging / "bienvenue.md").is_file()
    # The deliberately misfiled document: French body, frontmatter claims en.
    misfiled = staging / MISFILED_SAMPLE
    assert misfiled.is_file()
    text = misfiled.read_text("utf-8")
    assert "dc:language_bcp47: en" in text          # the wrong claim
    assert "français" in text                        # the French body


def test_sample_content_switch_off_stages_nothing(instance, registry):
    collection = seed_example_collection(
        instance, _validations(registry, "en", "fr"),
        collections_home="collections", version=VER, sample_content=False,
        now=_now)
    assert not (collection / "staging").exists()


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------

def test_seed_documentation_mints_a_content_directory_and_document(instance, registry):
    from satlib.archive import create_archive, plan_archive
    en = create_archive(
        plan_archive(instance, validate_expression("en", registry),
                     tool="sat init", tool_version=VER,
                     registry_file_date=registry.file_date, title="Docs"),
        command="sat init", version=VER)

    guide = seed_documentation(en, version=VER, now=_now)

    assert guide == en / "docs" / "getting-started.md"
    assert has_document_identity(guide)
    # docs/ carries the content role.
    from satlib.roles import ROLE_CONTENT, has_role
    assert has_role(en / "docs", ROLE_CONTENT, is_dir=True)
