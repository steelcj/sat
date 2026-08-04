"""Tests for satlib.discovery against ADR-005 and spec sections 1.1-1.2."""

import pytest

from satlib.discovery import discover, is_language_root
from satlib.language import SubtagRegistry
from tests.test_language import FIXTURE


@pytest.fixture(scope="module")
def registry():
    return SubtagRegistry.parse(FIXTURE)


def make_tool(root, *parts):
    tool = root.joinpath(*parts)
    tool.parent.mkdir(parents=True, exist_ok=True)
    tool.write_text("#!/usr/bin/env python3\n")
    return tool


class TestSpecWalkExamples:
    """The three worked examples of spec section 1.2."""

    def test_en_artifact(self, tmp_path, registry):
        tool = make_tool(tmp_path, "sat", "en", "bin", "sat", "sat-init.py")

        result = discover(tool, registry)

        assert result.found
        assert result.matched_dir == tmp_path / "sat" / "en"
        assert result.context.dc_language == "eng"
        assert result.context.dc_language_bcp47 == "en"
        assert result.context.sat_authority == "external"
        # walk: sat/ (tool dir) -> bin/ -> en/ <- match
        assert result.walked == ["sat", "bin", "en"]

    def test_region_subtag_root(self, tmp_path, registry):
        tool = make_tool(tmp_path, "universalcake.com", "fr-CA", "bin",
                         "content", "content-ingress.py")

        result = discover(tool, registry)

        assert result.found
        assert result.context.dc_language == "fra"
        assert result.context.dc_language_bcp47 == "fr-CA"

    def test_no_match_applies_non_authority_fallback(self, tmp_path, registry):
        tool = make_tool(tmp_path, "archives", "humpback_songs", "bin",
                         "content", "content-ingress.py")

        result = discover(tool, registry)

        assert not result.found
        assert result.matched_dir is None
        # The nearest ancestor above the bin/ tier, per the example
        assert result.fallback_name == "humpback_songs"


class TestRegistryBackedPatternTest:
    """Structural plausibility is not enough (spec section 1.1)."""

    def test_bin_and_sat_do_not_match_despite_shape(self, tmp_path, registry):
        # Both are 3-alpha strings — structurally valid primary
        # subtags — but neither is registered, so the walk passes over
        # them. Without the registry, discovery would stop at sat/.
        tool = make_tool(tmp_path, "sat", "en", "bin", "sat", "sat")
        result = discover(tool, registry)
        assert result.matched_dir == tmp_path / "sat" / "en"

    def test_wrong_casing_is_not_a_root_and_walk_continues(self, tmp_path, registry):
        tool = make_tool(tmp_path, "fr", "EN", "bin", "sat", "sat")
        result = discover(tool, registry)
        # EN/ fails canonical casing; the walk continues to fr/
        assert result.matched_dir == tmp_path / "fr"
        assert result.context.dc_language_bcp47 == "fr"

    def test_mixed_expression_root_matches(self, tmp_path, registry):
        tool = make_tool(tmp_path, "ase_en", "bin", "content", "tool.py")
        result = discover(tool, registry)
        assert result.found
        assert result.context.dc_language_bcp47 == "ase_en"

    def test_private_use_root_matches(self, tmp_path, registry):
        # A previously generated non-authority archive root is
        # discoverable like any other language root
        tool = make_tool(tmp_path, "x-humpback-songs", "bin", "content", "t.py")
        result = discover(tool, registry)
        assert result.found
        assert result.context.dc_language_bcp47 == "x-humpback-songs"
        assert result.context.sat_authority == "none"


class TestResolvedArtifactPath:
    """ADR-005 clarification: the walk runs on the resolved path."""

    def test_symlinked_wrapper_resolves_into_the_artifact(self, tmp_path, registry):
        # ~/.local/share/sat-tool/0.4.0/en/bin/sat/sat  <- the artifact
        artifact_tool = make_tool(
            tmp_path, ".local", "share", "sat-tool", "0.4.0",
            "en", "bin", "sat", "sat",
        )
        # ~/projects/sat/bin/sat -> artifact (a delegated symlink)
        instance_bin = tmp_path / "projects" / "sat" / "bin"
        instance_bin.mkdir(parents=True)
        link = instance_bin / "sat"
        link.symlink_to(artifact_tool)

        result = discover(link, registry)

        assert result.found
        # Matched inside the artifact, not inside the instance
        assert "sat-tool" in result.matched_dir.parts
        assert result.matched_dir.name == "en"

    def test_directory_start_is_accepted(self, tmp_path, registry):
        make_tool(tmp_path, "sat", "en", "bin", "sat", "sat")
        result = discover(tmp_path / "sat" / "en" / "bin" / "sat", registry)
        assert result.found
        assert result.matched_dir.name == "en"


class TestFilesystemRootTermination:
    def test_walk_terminates_and_reports_no_fallback_without_bin(self, tmp_path, registry):
        tool = make_tool(tmp_path, "somewhere", "tools", "t.py")
        result = discover(tool, registry)
        assert not result.found
        assert result.fallback_name is None  # no bin/ tier to anchor on


class TestIsLanguageRoot:
    def test_helper_agrees_with_the_walk(self, tmp_path, registry):
        (tmp_path / "fr-CA").mkdir()
        (tmp_path / "notalang").mkdir()
        assert is_language_root(tmp_path / "fr-CA", registry) is not None
        assert is_language_root(tmp_path / "notalang", registry) is None
