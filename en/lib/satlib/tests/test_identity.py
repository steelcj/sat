#
# source
#   project: sat
#   path: en/lib/satlib/tests/test_identity.py
#
"""Tests for satlib.identity: format, immutability, records, backfill.

Ends with the integration test: an archive created via plan/create
carries a conformant identity record beside its other records, and
refuses re-creation on the strength of identity alone.
"""

import pytest

from satlib.archive import ArchiveExistsError, create_archive, plan_archive
from satlib.assets import asset_path, read_yaml_asset
from satlib.identity import (
    IDENTIFIER_FIELD,
    IDENTITY_RECORD,
    IdentityExistsError,
    MalformedIdentityError,
    backfill_identity,
    build_identity_record,
    has_identity,
    is_valid_identifier,
    new_identifier,
    read_identity,
    write_identity,
)
from satlib.language import SubtagRegistry, validate_expression
from satlib.roles import ROLE_ARCHIVE, role_path
from tests.test_archive import FIXED_NOW
from tests.test_language import FIXTURE


@pytest.fixture(scope="module")
def registry():
    return SubtagRegistry.parse(FIXTURE)


# ---------------------------------------------------------------------------
# Identifier format (ADR-010 pattern, urn:uuid: form)
# ---------------------------------------------------------------------------

def test_new_identifier_is_valid():
    assert is_valid_identifier(new_identifier())


def test_new_identifiers_are_unique():
    assert new_identifier() != new_identifier()


@pytest.mark.parametrize("bad", [
    None,
    42,
    "",
    "7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e",           # missing urn prefix
    "urn:uuid:7F3AC291-4B2E-4D1A-9C8F-3E2B1A0D5C6E",  # uppercase
    "urn:uuid:7f3ac291-4b2e-1d1a-9c8f-3e2b1a0d5c6e",  # version 1
    "urn:uuid:7f3ac291-4b2e-4d1a-1c8f-3e2b1a0d5c6e",  # bad variant
    "urn:uuid:7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6",   # short
    "urn:uuid:7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e ",  # trailing space
])
def test_invalid_identifiers_rejected(bad):
    assert not is_valid_identifier(bad)


def test_valid_literal_accepted():
    assert is_valid_identifier("urn:uuid:7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e")


# ---------------------------------------------------------------------------
# Record shape
# ---------------------------------------------------------------------------

def test_build_record_mints_when_unsupplied():
    record = build_identity_record()
    assert set(record) == {IDENTIFIER_FIELD}
    assert is_valid_identifier(record[IDENTIFIER_FIELD])


def test_build_record_accepts_conformant_value():
    value = new_identifier()
    assert build_identity_record(value) == {IDENTIFIER_FIELD: value}


def test_build_record_refuses_malformed_value():
    with pytest.raises(ValueError):
        build_identity_record("not-a-urn")


# ---------------------------------------------------------------------------
# Write once, read back, refuse re-mint
# ---------------------------------------------------------------------------

def test_write_and_read_roundtrip(tmp_path):
    entity = tmp_path / "en"
    entity.mkdir()
    written = write_identity(entity, ROLE_ARCHIVE)
    assert has_identity(entity, ROLE_ARCHIVE)
    assert read_identity(entity, ROLE_ARCHIVE) == written


def test_write_refuses_existing(tmp_path):
    entity = tmp_path / "en"
    entity.mkdir()
    write_identity(entity, ROLE_ARCHIVE)
    with pytest.raises(IdentityExistsError):
        write_identity(entity, ROLE_ARCHIVE)


def test_identity_is_per_role(tmp_path):
    """A dual-role directory carries two identities, one per role."""
    entity = tmp_path / "sat"
    entity.mkdir()
    sat_id = write_identity(entity, "sat")
    collection_id = write_identity(entity, "collection")
    assert sat_id != collection_id
    assert read_identity(entity, "sat") == sat_id
    assert read_identity(entity, "collection") == collection_id


def test_record_holds_identifier_and_nothing_else(tmp_path):
    entity = tmp_path / "en"
    entity.mkdir()
    write_identity(entity, ROLE_ARCHIVE)
    record = read_yaml_asset(entity, f"{ROLE_ARCHIVE}/{IDENTITY_RECORD}", is_dir=True)
    assert set(record) == {IDENTIFIER_FIELD}


def test_read_flags_absent_record(tmp_path):
    entity = tmp_path / "en"
    entity.mkdir()
    with pytest.raises(MalformedIdentityError):
        read_identity(entity, ROLE_ARCHIVE)


def test_read_flags_missing_field(tmp_path):
    entity = tmp_path / "en"
    entity.mkdir()
    path = role_path(entity, ROLE_ARCHIVE, IDENTITY_RECORD, is_dir=True)
    path.parent.mkdir(parents=True)
    path.write_text("dc:title: wrong record\n", "utf-8")
    with pytest.raises(MalformedIdentityError):
        read_identity(entity, ROLE_ARCHIVE)


def test_read_flags_malformed_value(tmp_path):
    entity = tmp_path / "en"
    entity.mkdir()
    path = role_path(entity, ROLE_ARCHIVE, IDENTITY_RECORD, is_dir=True)
    path.parent.mkdir(parents=True)
    path.write_text(f"{IDENTIFIER_FIELD}: not-a-urn\n", "utf-8")
    with pytest.raises(MalformedIdentityError):
        read_identity(entity, ROLE_ARCHIVE)


# ---------------------------------------------------------------------------
# Backfill
# ---------------------------------------------------------------------------

def test_backfill_mints_once(tmp_path):
    entity = tmp_path / "en"
    entity.mkdir()
    minted = backfill_identity(entity, ROLE_ARCHIVE)
    assert read_identity(entity, ROLE_ARCHIVE) == minted
    with pytest.raises(IdentityExistsError):
        backfill_identity(entity, ROLE_ARCHIVE)


# ---------------------------------------------------------------------------
# Integration: archive creation carries identity
# ---------------------------------------------------------------------------

def _plan(parent, registry):
    validation = validate_expression("en", registry)
    return plan_archive(
        parent=parent,
        validation=validation,
        tool="sat-tool",
        tool_version="0.0.0-test",
        registry_file_date="2026-06-16",
        now=lambda: FIXED_NOW,
    )


def test_created_archive_carries_identity(tmp_path, registry):
    plan = _plan(tmp_path, registry)
    assert IDENTITY_RECORD in plan.records
    directory = create_archive(plan)
    assert has_identity(directory, ROLE_ARCHIVE)
    assert is_valid_identifier(read_identity(directory, ROLE_ARCHIVE))


def test_dry_run_plan_shows_conformant_record(tmp_path, registry):
    record = _plan(tmp_path, registry).records[IDENTITY_RECORD]
    assert set(record) == {IDENTIFIER_FIELD}
    assert is_valid_identifier(record[IDENTIFIER_FIELD])


def test_identity_alone_blocks_recreation(tmp_path, registry):
    plan = _plan(tmp_path, registry)
    directory = create_archive(plan)
    # Strip every record except identity: identity alone must refuse.
    for name in list(plan.records):
        if name != IDENTITY_RECORD:
            role_path(directory, ROLE_ARCHIVE, name, is_dir=True).unlink()
    with pytest.raises(ArchiveExistsError):
        create_archive(_plan(tmp_path, registry))
