"""Tests for satlib.assets against ADR-018."""

import pytest

from satlib.assets import (
    Orphan,
    asset_path,
    assets_dir_for,
    assets_name_for,
    entity_for,
    entity_name_for,
    find_orphans,
    is_assets_name,
    iter_entities,
    read_yaml_asset,
    write_yaml_asset,
)


class TestTransform:
    """ADR-018 decision 2: literal, injective, reversible."""

    @pytest.mark.parametrize("entity, assets", [
        ("sat", ".sat.assets"),
        ("en", ".en.assets"),
        ("docs", ".docs.assets"),
        ("sat-guide.md", ".sat-guide.md.assets"),      # extension preserved
        ("sat-guide.pdf", ".sat-guide.pdf.assets"),    # distinct entity
    ])
    def test_forward(self, entity, assets):
        assert assets_name_for(entity) == assets

    @pytest.mark.parametrize("entity", [
        "sat", "sat-guide.md", "Sat Guide.md", "UPPER",
    ])
    def test_round_trip_is_exact(self, entity):
        # Literal means literal: even non-slug names survive the round
        # trip unchanged. Slug conformance is ingress's job, not ours.
        assert entity_name_for(assets_name_for(entity)) == entity

    def test_no_reslugging(self):
        # The WRONG example from ADR-018 decision 2
        assert assets_name_for("sat-guide.md") != ".sat-guide-md.assets"

    def test_reverse_rejects_non_assets_names(self):
        assert entity_name_for("sat-guide.md") is None
        assert entity_name_for(".hidden") is None
        assert entity_name_for(".assets") is None      # empty entity name

    def test_is_assets_name(self):
        assert is_assets_name(".en.assets")
        assert not is_assets_name("en")
        assert not is_assets_name(".en.assets.bak")

    @pytest.mark.parametrize("bad", ["", ".", "..", "a/b"])
    def test_invalid_entity_names_rejected(self, bad):
        with pytest.raises(ValueError):
            assets_name_for(bad)


class TestPlacement:
    """ADR-018 decision 3: inside for directories, beside for files."""

    def test_directory_assets_inside(self, tmp_path):
        en = tmp_path / "en"
        en.mkdir()
        assert assets_dir_for(en) == en / ".en.assets"

    def test_file_assets_beside(self, tmp_path):
        guide = tmp_path / "docs" / "sat-guide.md"
        guide.parent.mkdir()
        guide.write_text("# guide")
        assert assets_dir_for(guide) == guide.parent / ".sat-guide.md.assets"

    def test_planning_mode_for_nonexistent_entities(self, tmp_path):
        # Dry-run support: is_dir supplied explicitly, no filesystem
        planned_dir = tmp_path / "fr"
        planned_file = tmp_path / "fr" / "docs" / "guide.md"
        assert assets_dir_for(planned_dir, is_dir=True) == planned_dir / ".fr.assets"
        assert assets_dir_for(planned_file, is_dir=False) == (
            planned_file.parent / ".guide.md.assets"
        )

    def test_nonexistent_without_is_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            assets_dir_for(tmp_path / "ghost")

    def test_reverse_placement_directory(self, tmp_path):
        assets = tmp_path / "en" / ".en.assets"
        assert entity_for(assets) == tmp_path / "en"

    def test_reverse_placement_file(self, tmp_path):
        assets = tmp_path / "docs" / ".sat-guide.md.assets"
        assert entity_for(assets) == tmp_path / "docs" / "sat-guide.md"


class TestReadWrite:
    def test_write_creates_assets_dir_and_reads_back(self, tmp_path):
        en = tmp_path / "en"
        en.mkdir()
        record = {"dc:language": "eng", "dc:language_bcp47": "en",
                  "sat:authority": "external"}

        path = write_yaml_asset(en, "language.yml", record)

        assert path == en / ".en.assets" / "language.yml"
        assert read_yaml_asset(en, "language.yml") == record

    def test_key_order_preserved(self, tmp_path):
        en = tmp_path / "en"
        en.mkdir()
        write_yaml_asset(en, "dc.yml", {"dc:title": "T", "dc:creator": "C",
                                        "dc:date": "2026-07-09"})
        text = asset_path(en, "dc.yml").read_text()
        assert text.index("dc:title") < text.index("dc:creator") < text.index("dc:date")

    def test_missing_asset_reads_as_none(self, tmp_path):
        en = tmp_path / "en"
        en.mkdir()
        assert read_yaml_asset(en, "language.yml") is None


class TestOrphanDetection:
    """ADR-018 decision 5: reported, never repaired."""

    def _instance(self, tmp_path):
        """A small valid tree: directory assets + file assets."""
        docs = tmp_path / "en" / "docs"
        docs.mkdir(parents=True)
        (tmp_path / "en" / ".en.assets").mkdir()
        guide = docs / "sat-guide.md"
        guide.write_text("# guide")
        (docs / ".sat-guide.md.assets").mkdir()
        return tmp_path

    def test_valid_tree_has_no_orphans(self, tmp_path):
        root = self._instance(tmp_path)
        assert find_orphans(root) == []

    def test_manual_rename_leaves_detectable_orphan(self, tmp_path):
        # The mv guides/ handbooks/ example from ADR-018 decision 5
        root = self._instance(tmp_path)
        guide = root / "en" / "docs" / "sat-guide.md"
        guide.rename(guide.with_name("quick-start.md"))  # assets not renamed

        orphans = find_orphans(root)

        assert orphans == [Orphan(
            assets_path=root / "en" / "docs" / ".sat-guide.md.assets",
            embedded_name="sat-guide.md",
            reason="no-entity",
        )]

    def test_sibling_directory_assets_reported_misplaced(self, tmp_path):
        # Directory assets belong inside, not beside (decision 3)
        root = self._instance(tmp_path)
        (root / "en" / "docs" / "guides").mkdir()
        (root / "en" / "docs" / ".guides.assets").mkdir()

        orphans = find_orphans(root)

        assert [(o.embedded_name, o.reason) for o in orphans] == [
            ("guides", "misplaced"),
        ]

    def test_parent_name_collision_reported(self, tmp_path):
        # The documented edge: file named as its parent directory
        b = tmp_path / "b"
        b.mkdir()
        (b / ".b.assets").mkdir()      # the directory's own assets
        (b / "b").write_text("data")   # a file claiming the same assets path

        orphans = find_orphans(tmp_path)

        assert [(o.embedded_name, o.reason) for o in orphans] == [
            ("b", "collision"),
        ]

    def test_orphan_scan_does_not_descend_into_assets(self, tmp_path):
        # An assets-shaped name INSIDE an assets directory is content
        # of metadata space, not a pairing to check
        root = self._instance(tmp_path)
        nested = root / "en" / ".en.assets" / ".stray.assets"
        nested.mkdir()
        assert find_orphans(root) == []


class TestExclusion:
    """ADR-018 decision 6: one exclusion pattern for enumeration."""

    def test_iter_entities_prunes_metadata_space(self, tmp_path):
        docs = tmp_path / "en" / "docs"
        docs.mkdir(parents=True)
        (tmp_path / "en" / ".en.assets").mkdir()
        (tmp_path / "en" / ".en.assets" / "dc.yml").write_text("dc:title: T")
        guide = docs / "sat-guide.md"
        guide.write_text("# guide")
        (docs / ".sat-guide.md.assets").mkdir()
        (docs / ".sat-guide.md.assets" / "figure-1.svg").write_text("<svg/>")

        seen = {p.relative_to(tmp_path).as_posix() for p in iter_entities(tmp_path)}

        assert seen == {"en", "en/docs", "en/docs/sat-guide.md"}

    def test_other_hidden_files_are_not_excluded(self, tmp_path):
        # The exclusion rule is .*.assets, not all dotfiles
        (tmp_path / ".gitignore").write_text(".venv/\n")
        seen = {p.name for p in iter_entities(tmp_path)}
        assert ".gitignore" in seen
