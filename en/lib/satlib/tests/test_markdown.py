#
# source
#   project: sat
#   path: en/lib/satlib/tests/test_markdown.py
#
"""Tests for satlib.markdown: mdformat normalization and the three ADR-030
house-rule checks (no horizontal rules, fenced blocks carry a language, no
heading-level skips). check_house_rules is pure stdlib; normalize wraps
mdformat and is fatal when mdformat is absent."""

import pytest

from satlib.markdown import (
    DEFAULT_RULES,
    MarkdownError,
    check_house_rules,
    ensure_available,
    load_rules,
    normalize,
)


# ---------------------------------------------------------------------------
# normalize (mdformat)
# ---------------------------------------------------------------------------

def test_normalize_reflows_to_mdformat_canonical_form():
    import mdformat
    messy = "#   Title\n\n\n* a\n*  b\n\nsome   text  \n"
    assert normalize(messy) == mdformat.text(messy)


def test_normalize_is_idempotent_on_canonical_text():
    canonical = "# Title\n\n- a\n- b\n\nsome text\n"
    assert normalize(canonical) == canonical


def test_normalize_fatal_when_mdformat_absent(monkeypatch):
    import satlib.markdown as md

    def _boom():
        raise MarkdownError("mdformat is not installed")

    monkeypatch.setattr(md, "_mdformat", _boom)
    with pytest.raises(MarkdownError):
        md.normalize("# x\n")
    with pytest.raises(MarkdownError):
        md.ensure_available()


# ---------------------------------------------------------------------------
# check_house_rules: horizontal rules
# ---------------------------------------------------------------------------

def test_horizontal_rule_in_content_is_a_finding():
    findings = check_house_rules("# T\n\ntext\n\n---\n\nmore\n")
    kinds = [f.kind for f in findings]
    assert "markdown-horizontal-rule" in kinds


def test_horizontal_rule_inside_code_fence_is_ignored():
    text = "# T\n\n```text\n---\n```\n"
    assert not any(f.kind == "markdown-horizontal-rule"
                   for f in check_house_rules(text))


def test_star_and_underscore_rules_also_flagged():
    for rule in ("***", "___"):
        findings = check_house_rules(f"# T\n\n{rule}\n")
        assert any(f.kind == "markdown-horizontal-rule" for f in findings)


# ---------------------------------------------------------------------------
# check_house_rules: fenced code blocks require a language
# ---------------------------------------------------------------------------

def test_unlabeled_fence_is_a_finding():
    text = "# T\n\n```\nplain\n```\n"
    assert any(f.kind == "markdown-unlabeled-fence"
               for f in check_house_rules(text))


def test_labeled_fence_is_clean():
    text = "# T\n\n```python\nx = 1\n```\n"
    assert not any(f.kind == "markdown-unlabeled-fence"
                   for f in check_house_rules(text))


# ---------------------------------------------------------------------------
# check_house_rules: heading-level skips
# ---------------------------------------------------------------------------

def test_heading_level_skip_is_a_finding():
    text = "# H1\n\n### H3 skips H2\n"
    assert any(f.kind == "markdown-heading-skip"
               for f in check_house_rules(text))


def test_sequential_headings_are_clean():
    text = "# H1\n\n## H2\n\n### H3\n"
    assert not any(f.kind == "markdown-heading-skip"
                   for f in check_house_rules(text))


def test_going_shallower_is_never_a_skip():
    text = "# H1\n\n## H2\n\n### H3\n\n## back to H2\n"
    assert not any(f.kind == "markdown-heading-skip"
                   for f in check_house_rules(text))


def test_hashes_inside_code_fence_are_not_headings():
    text = "# T\n\n```python\n### not a heading\n```\n"
    assert not any(f.kind == "markdown-heading-skip"
                   for f in check_house_rules(text))


# ---------------------------------------------------------------------------
# Clean document and toggles
# ---------------------------------------------------------------------------

def test_clean_document_yields_no_findings():
    text = "# Title\n\n## Section\n\n```python\nx = 1\n```\n\nProse.\n"
    assert check_house_rules(text) == []


def test_a_disabled_rule_is_not_checked():
    text = "# T\n\n---\n"
    rules = {"no_horizontal_rules": False}
    assert not any(f.kind == "markdown-horizontal-rule"
                   for f in check_house_rules(text, rules))


def test_findings_use_the_adr024_grammar():
    findings = check_house_rules("# H1\n\n### H3\n")
    f = findings[0]
    assert f.kind and f.what and f.means and f.severity == "soft"


# ---------------------------------------------------------------------------
# check_house_rules: no hard line wraps
# ---------------------------------------------------------------------------

def test_hard_wrapped_paragraph_is_a_finding():
    text = "# T\n\nThis paragraph is hard wrapped\nacross two source lines.\n"
    assert any(f.kind == "markdown-hard-line-wrap"
               for f in check_house_rules(text))


def test_single_line_paragraph_is_clean():
    text = "# T\n\nThis paragraph flows on one line.\n"
    assert not any(f.kind == "markdown-hard-line-wrap"
                   for f in check_house_rules(text))


def test_list_items_on_separate_lines_are_not_hard_wraps():
    text = "# T\n\n- one\n- two\n- three\n"
    assert not any(f.kind == "markdown-hard-line-wrap"
                   for f in check_house_rules(text))


# ---------------------------------------------------------------------------
# check_house_rules: embedded base64 image data and inline svg
# ---------------------------------------------------------------------------

def test_embedded_base64_image_is_a_finding():
    text = "# T\n\n![x](data:image/png;base64,iVBORw0KGgo=)\n"
    assert any(f.kind == "markdown-embedded-image-data"
               for f in check_house_rules(text))


def test_base64_svg_data_uri_still_flagged_as_embedded_data():
    text = "# T\n\n![x](data:image/svg+xml;base64,PHN2Zz4=)\n"
    assert any(f.kind == "markdown-embedded-image-data"
               for f in check_house_rules(text))


def test_inline_svg_allowed_by_default_is_clean():
    text = "# T\n\n<svg viewBox='0 0 1 1'></svg>\n"
    assert not any(f.kind == "markdown-inline-svg"
                   for f in check_house_rules(text))


def test_inline_svg_flagged_when_disallowed():
    text = "# T\n\n<svg viewBox='0 0 1 1'></svg>\n"
    findings = check_house_rules(text, {"inline_svg_allowed": False})
    assert any(f.kind == "markdown-inline-svg" for f in findings)


# ---------------------------------------------------------------------------
# load_rules: the shipped-floor markdown.yml
# ---------------------------------------------------------------------------

def test_default_rules_has_all_six_toggles():
    assert set(DEFAULT_RULES) == {
        "no_horizontal_rules", "fenced_blocks_require_language",
        "no_heading_level_skips", "no_hard_line_wraps",
        "no_embedded_image_data", "inline_svg_allowed",
    }


def test_load_rules_missing_file_yields_defaults(tmp_path):
    assert load_rules(tmp_path / "nope.yml") == DEFAULT_RULES


def test_load_rules_merges_overrides_from_file(tmp_path):
    floor = tmp_path / "markdown.yml"
    floor.write_text("no_horizontal_rules: false\ninline_svg_allowed: false\n",
                     "utf-8")
    rules = load_rules(floor)
    assert rules["no_horizontal_rules"] is False
    assert rules["inline_svg_allowed"] is False
    assert rules["no_heading_level_skips"] is True  # untouched default


def test_load_rules_ignores_unknown_keys(tmp_path):
    floor = tmp_path / "markdown.yml"
    floor.write_text("bogus_key: true\nno_hard_line_wraps: false\n", "utf-8")
    rules = load_rules(floor)
    assert "bogus_key" not in rules
    assert rules["no_hard_line_wraps"] is False


def test_shipped_floor_markdown_yml_loads_and_is_all_on():
    from pathlib import Path
    floor = (Path(__file__).resolve().parents[3]
             / "bin" / "sat" / "defaults" / "content" / "markdown.yml")
    rules = load_rules(floor)
    # The shipped floor exists and every toggle it declares parses.
    assert floor.is_file()
    assert rules["no_horizontal_rules"] is True
    assert rules["no_embedded_image_data"] is True
