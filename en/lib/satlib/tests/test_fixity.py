#
# source
#   project: sat
#   path: en/lib/satlib/tests/test_fixity.py
#
"""Tests for satlib.fixity: digesting, recording, checking with
classified findings, the container-format honesty note, and the
SHA256SUMS export (ADR-027)."""

import pytest

from satlib.fixity import (
    check_fixity,
    digest_file,
    format_sha256sums,
    read_fixity,
    record_fixity,
)
from satlib.identity import write_identity
from satlib.roles import ROLE_ARCHIVE, ROLE_CONTENT, role_path, write_role_yaml

# Known sha256 vectors.
SHA256_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
SHA256_EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

CMD = "collection init"
VER = "0.7.0"
FIXED_NOW = "2026-07-15T10:00:00Z"


def _now():
    return FIXED_NOW


def _archive_role(directory):
    """An archive directory with its write-once role records."""
    directory.mkdir(parents=True, exist_ok=True)
    write_identity(directory, ROLE_ARCHIVE)
    write_role_yaml(directory, ROLE_ARCHIVE, "provenance.yml",
                    {"created": "2026-07-15T10:00:00Z", "tool": "sat-tools"})


def _content_identity(document):
    """A document's content-role identity, beside the file (is_dir=False)."""
    write_role_yaml(document, ROLE_CONTENT, "identity.yml",
                    {"dc:identifier": "urn:uuid:2b9d4e01-88af-4c37-9f1e-6a0c3d5b7e21"},
                    is_dir=False)


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

def test_digest_known_vectors(tmp_path):
    abc = tmp_path / "abc.txt"
    abc.write_bytes(b"abc")
    assert digest_file(abc) == SHA256_ABC
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    assert digest_file(empty) == SHA256_EMPTY


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------

def test_record_attests_present_write_once_records(tmp_path):
    archive = tmp_path / "en"
    _archive_role(archive)
    path = record_fixity(archive, ROLE_ARCHIVE, command=CMD, version=VER, now=_now)
    text = path.read_text("utf-8")
    assert text.startswith("# en/.en.assets/archive/fixity.yml\n")

    body = read_fixity(archive, ROLE_ARCHIVE)
    assert set(body["records"]) == {"identity.yml", "provenance.yml"}
    assert body["records"]["identity.yml"]["algorithm"] == "sha256"
    assert body["recorded"] == FIXED_NOW
    assert body["recorded_by"] == {"command": CMD, "version": VER}
    assert "content" not in body  # no content at the archive role


def test_content_role_attests_the_content(tmp_path):
    document = tmp_path / "guide.md"
    document.write_bytes(b"abc")
    _content_identity(document)
    record_fixity(document, ROLE_CONTENT, content_path=document,
                  is_dir=False, command=CMD, version=VER, now=_now)
    body = read_fixity(document, ROLE_CONTENT, is_dir=False)
    assert body["content"]["digest"] == SHA256_ABC
    assert body["content"]["size"] == 3
    # a document's content role carries identity.yml but no provenance.yml
    assert set(body["records"]) == {"identity.yml"}


# ---------------------------------------------------------------------------
# Checking: classified findings
# ---------------------------------------------------------------------------

def test_check_clean_after_record(tmp_path):
    archive = tmp_path / "en"
    _archive_role(archive)
    record_fixity(archive, ROLE_ARCHIVE, command=CMD, version=VER, now=_now)
    assert check_fixity(archive, ROLE_ARCHIVE) == []


def test_absent_baseline_has_nothing_to_check(tmp_path):
    archive = tmp_path / "en"
    _archive_role(archive)
    assert check_fixity(archive, ROLE_ARCHIVE) == []


def test_tampered_write_once_record_is_hard_corruption(tmp_path):
    archive = tmp_path / "en"
    _archive_role(archive)
    record_fixity(archive, ROLE_ARCHIVE, command=CMD, version=VER, now=_now)
    # Corrupt a write-once record after recording.
    role_path(archive, ROLE_ARCHIVE, "identity.yml", is_dir=True).write_text(
        "dc:identifier: urn:uuid:00000000-0000-4000-8000-000000000000\n", "utf-8")

    findings = check_fixity(archive, ROLE_ARCHIVE)

    assert len(findings) == 1
    assert findings[0].kind == "record-corruption"
    assert findings[0].hard
    assert "identity.yml" in findings[0].target


def test_vanished_record_is_hard_corruption(tmp_path):
    archive = tmp_path / "en"
    _archive_role(archive)
    record_fixity(archive, ROLE_ARCHIVE, command=CMD, version=VER, now=_now)
    role_path(archive, ROLE_ARCHIVE, "provenance.yml", is_dir=True).unlink()

    findings = check_fixity(archive, ROLE_ARCHIVE)

    assert [f.kind for f in findings] == ["record-corruption"]
    assert findings[0].hard


def test_edited_content_is_soft_modified(tmp_path):
    document = tmp_path / "guide.md"
    document.write_bytes(b"abc")
    _content_identity(document)
    record_fixity(document, ROLE_CONTENT, content_path=document,
                  is_dir=False, command=CMD, version=VER, now=_now)
    document.write_bytes(b"abc edited")  # legitimate operator edit

    findings = check_fixity(document, ROLE_CONTENT, content_path=document,
                            is_dir=False)

    assert len(findings) == 1
    assert findings[0].kind == "content-modified"
    assert not findings[0].hard  # soft: remedy is re-cataloging, not alarm


def test_container_format_carries_the_honesty_note(tmp_path):
    document = tmp_path / "report.docx"
    document.write_bytes(b"abc")
    _content_identity(document)
    record_fixity(document, ROLE_CONTENT, content_path=document,
                  is_dir=False, command=CMD, version=VER, now=_now)
    document.write_bytes(b"abc rewritten by Word")

    findings = check_fixity(document, ROLE_CONTENT, content_path=document,
                            is_dir=False)

    assert findings[0].kind == "content-modified"
    assert ".docx" in findings[0].means
    assert "cannot know which application" in findings[0].means


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def test_sha256sums_format():
    text = format_sha256sums([
        (SHA256_ABC, "en/products/guide.md"),
        (SHA256_EMPTY, "en/products/empty.md"),
    ])
    assert text == (
        f"{SHA256_ABC}  en/products/guide.md\n"
        f"{SHA256_EMPTY}  en/products/empty.md\n"
    )
