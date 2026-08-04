#
# source
#   project: sat
#   path: en/lib/satlib/tests/test_staging.py
#
"""Tests for satlib.staging: the promotion helper content ingress calls at
pipeline step 0 (ADR-029). The broader ADR-029 surface (scan_staging,
staging-fixity.yml, collection stage --scan) is collection-tier work and is
out of scope here."""

import pytest

from satlib.staging import StagingError, promote


def test_promote_moves_file_keeping_its_name(tmp_path):
    src = tmp_path / "staging" / "note.md"
    src.parent.mkdir(parents=True)
    src.write_text("# note\n", "utf-8")
    dest_dir = tmp_path / "fr" / "produits"

    new_path = promote(src, dest_dir)

    assert not src.exists()
    assert new_path == (dest_dir / "note.md").resolve()
    assert new_path.read_text("utf-8") == "# note\n"


def test_promote_creates_missing_destination_directories(tmp_path):
    src = tmp_path / "staging" / "note.md"
    src.parent.mkdir(parents=True)
    src.write_text("x\n", "utf-8")
    dest_dir = tmp_path / "fr" / "deep" / "new"  # none of these exist

    new_path = promote(src, dest_dir)

    assert new_path.is_file()
    assert new_path.parent == dest_dir.resolve()


def test_promote_refuses_existing_destination_and_leaves_source(tmp_path):
    src = tmp_path / "staging" / "note.md"
    src.parent.mkdir(parents=True)
    src.write_text("# incoming\n", "utf-8")
    dest_dir = tmp_path / "fr"
    dest_dir.mkdir()
    (dest_dir / "note.md").write_text("# already here\n", "utf-8")

    with pytest.raises(StagingError):
        promote(src, dest_dir)

    assert src.exists()  # source untouched on refusal
    assert (dest_dir / "note.md").read_text("utf-8") == "# already here\n"


def test_promote_rejects_a_non_file_source(tmp_path):
    missing = tmp_path / "staging" / "gone.md"
    with pytest.raises(StagingError):
        promote(missing, tmp_path / "fr")
