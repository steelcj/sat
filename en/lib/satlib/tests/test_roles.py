#
# source
#   project: sat
#   path: en/lib/satlib/tests/test_roles.py
#
"""Tests for satlib.roles: role-directory location, declaration
detection, dual-role directories, ADR-018 file placement, and the
self-recorded sat:name (ADR-024, ADR-025)."""

from pathlib import Path

import pytest

from satlib.assets import assets_dir_for, read_yaml_asset
from satlib.roles import (
    DC_RECORD,
    NAME_FIELD,
    ROLE_ARCHIVE,
    ROLE_COLLECTION,
    ROLE_CONTENT,
    ROLE_SAT,
    ROLES,
    RoleError,
    declared_roles,
    has_role,
    read_name,
    read_role_yaml,
    role_dir,
    role_path,
    write_name,
    write_role_yaml,
)


# ---------------------------------------------------------------------------
# Role directory location
# ---------------------------------------------------------------------------

def test_role_dir_is_inside_the_assets_directory(tmp_path):
    entity = tmp_path / "my-sat"
    entity.mkdir()
    assert role_dir(entity, ROLE_SAT) == \
        assets_dir_for(entity, is_dir=True) / "sat"


def test_role_dir_for_a_planned_directory(tmp_path):
    entity = tmp_path / "not-yet"
    # is_dir supplied explicitly: the entity need not exist (dry-run).
    assert role_dir(entity, ROLE_COLLECTION, is_dir=True) == \
        entity / ".not-yet.assets" / "collection"


def test_role_path_joins_a_record_name(tmp_path):
    entity = tmp_path / "en"
    entity.mkdir()
    assert role_path(entity, ROLE_ARCHIVE, "language.yml") == \
        assets_dir_for(entity, is_dir=True) / "archive" / "language.yml"


def test_content_role_beside_a_document_uses_full_filename(tmp_path):
    """ADR-018 file placement: a document's assets sit beside it and
    keep the full filename, so the content role is
    .<file>.assets/content/."""
    document = tmp_path / "my-guide.md"
    document.write_text("# guide\n", "utf-8")
    assert role_dir(document, ROLE_CONTENT, is_dir=False) == \
        tmp_path / ".my-guide.md.assets" / "content"


def test_unknown_role_is_refused(tmp_path):
    entity = tmp_path / "x"
    entity.mkdir()
    with pytest.raises(RoleError):
        role_dir(entity, "instance")  # the role is 'sat', not 'instance'


# ---------------------------------------------------------------------------
# Declaration detection
# ---------------------------------------------------------------------------

def test_no_assets_directory_declares_nothing(tmp_path):
    entity = tmp_path / "bare"
    entity.mkdir()
    assert declared_roles(entity) == []


def test_single_role_directory(tmp_path):
    entity = tmp_path / "henson-catalog"
    entity.mkdir()
    write_role_yaml(entity, ROLE_COLLECTION, DC_RECORD, {NAME_FIELD: "henson-catalog"})
    assert declared_roles(entity) == [ROLE_COLLECTION]
    assert has_role(entity, ROLE_COLLECTION)
    assert not has_role(entity, ROLE_SAT)


def test_dual_role_directory_reports_both_in_tier_order(tmp_path):
    """A directory that is both instance and collection carries both
    role directories; the report is in canonical tier order."""
    entity = tmp_path / "sat"
    entity.mkdir()
    # Create collection first to prove ordering is by tier, not by
    # creation order or filesystem listing.
    write_role_yaml(entity, ROLE_COLLECTION, DC_RECORD, {NAME_FIELD: "sat"})
    write_role_yaml(entity, ROLE_SAT, DC_RECORD, {NAME_FIELD: "sat"})
    assert declared_roles(entity) == [ROLE_SAT, ROLE_COLLECTION]


def test_roles_constant_is_the_four_tiers_in_order():
    assert ROLES == ("sat", "collection", "archive", "content")


# ---------------------------------------------------------------------------
# The self-recorded name
# ---------------------------------------------------------------------------

def test_read_name_absent_is_none(tmp_path):
    entity = tmp_path / "x"
    entity.mkdir()
    assert read_name(entity, ROLE_SAT) is None


def test_write_then_read_name(tmp_path):
    entity = tmp_path / "en"
    entity.mkdir()
    write_name(entity, ROLE_ARCHIVE, "en")
    assert read_name(entity, ROLE_ARCHIVE) == "en"


def test_write_name_prepends_when_absent_and_preserves_settings(tmp_path):
    entity = tmp_path / "col"
    entity.mkdir()
    write_role_yaml(entity, ROLE_COLLECTION, DC_RECORD, {"dc:rights": "CC BY-SA 4.0"})
    write_name(entity, ROLE_COLLECTION, "col")
    record = read_role_yaml(entity, ROLE_COLLECTION, DC_RECORD)
    assert record[NAME_FIELD] == "col"
    assert record["dc:rights"] == "CC BY-SA 4.0"  # nothing else disturbed
    # sat:name leads the sparse body.
    assert list(record) == [NAME_FIELD, "dc:rights"]


def test_write_name_updates_in_place(tmp_path):
    entity = tmp_path / "en"
    entity.mkdir()
    write_name(entity, ROLE_ARCHIVE, "en")
    write_name(entity, ROLE_ARCHIVE, "english")  # the rename
    assert read_name(entity, ROLE_ARCHIVE) == "english"


def test_write_name_preserves_a_leading_comment_block(tmp_path):
    entity = tmp_path / "col"
    entity.mkdir()
    path = role_path(entity, ROLE_COLLECTION, DC_RECORD)
    path.parent.mkdir(parents=True)
    path.write_text(
        "# Settings flow down from the instance automatically.\n"
        "# Only write something here if THIS tier needs a different answer.\n"
        "#\n",
        "utf-8",
    )
    write_name(entity, ROLE_COLLECTION, "col")
    text = path.read_text("utf-8")
    assert text.startswith("# Settings flow down from the instance")
    assert "sat:name: col" in text
    assert read_name(entity, ROLE_COLLECTION) == "col"
