#
# source
#   project: sat
#   path: en/lib/satlib/tests/test_cataloging.py
#
"""Tests for satlib.cataloging: frontmatter reading and stripping, and
the normative ADR-023 cataloging policy (transcribed / supplied / noted),
including the dc:subject union, the language-disagreement finding, and the
dc:date fallback order settled in the content-ingress implementation plan.

Written before satlib.cataloging exists, per the SAT development cycle's
test stage: each specified behaviour, failure mode, and invariant has a
corresponding assertion here."""

import pytest

from satlib.cataloging import (
    CatalogResult,
    Finding,
    FrontmatterError,
    apply_cataloging_policy,
    read_frontmatter,
)


# ---------------------------------------------------------------------------
# Frontmatter reading and stripping (spec section 5)
# ---------------------------------------------------------------------------

def test_read_frontmatter_happy_splits_block_and_body():
    text = (
        "---\n"
        "title: A Guide\n"
        "author: A. Henson\n"
        "---\n"
        "# A Guide\n\nBody text.\n"
    )
    fm, body, raw = read_frontmatter(text)
    assert fm == {"title": "A Guide", "author": "A. Henson"}
    assert body == "# A Guide\n\nBody text.\n"
    # The raw block is preserved for the ingress record, delimiters excluded.
    assert "title: A Guide" in raw
    assert "---" not in raw


def test_read_frontmatter_absent_returns_none_and_unchanged_body():
    text = "# Already Pure\n\nNo frontmatter here.\n"
    fm, body, raw = read_frontmatter(text)
    assert fm is None
    assert body == text
    assert raw == ""


def test_read_frontmatter_empty_block_is_empty_mapping():
    text = "---\n---\n# Title\n"
    fm, body, raw = read_frontmatter(text)
    assert fm == {}
    assert body == "# Title\n"


def test_read_frontmatter_malformed_raises_does_not_guess():
    text = "---\ntitle: : : broken\n  - unbalanced\n---\nbody\n"
    with pytest.raises(FrontmatterError):
        read_frontmatter(text)


def test_read_frontmatter_non_mapping_block_raises():
    text = "---\n- just\n- a\n- list\n---\nbody\n"
    with pytest.raises(FrontmatterError):
        read_frontmatter(text)


def test_read_frontmatter_only_strips_leading_block_not_rule_lines():
    text = "---\ntitle: T\n---\nbefore\n\n---\n\nafter\n"
    fm, body, raw = read_frontmatter(text)
    assert fm == {"title": "T"}
    # A horizontal rule later in the body must survive untouched.
    assert body == "before\n\n---\n\nafter\n"


# ---------------------------------------------------------------------------
# Cataloging policy: transcribed wins (spec section 7 / ADR-023)
# ---------------------------------------------------------------------------

def _preseed(**over):
    base = {
        "dc:creator": "Archive Default Author",
        "dc:publisher": "Henson Shaving",
        "dc:rights": "CC BY-SA 4.0",
        "dc:language": "eng",
        "dc:language_bcp47": "en",
        "dc:type": "Text",
        "dc:format": "text/markdown",
    }
    base.update(over)
    return base


def test_transcribed_title_creator_description_win_verbatim():
    fm = {
        "title": "Guide d'entretien",
        "author": "A. Henson",
        "description": "How to care for a razor.",
    }
    r = apply_cataloging_policy(fm, _preseed(), archive_language="en")
    assert isinstance(r, CatalogResult)
    assert r.sidecar["dc:title"] == "Guide d'entretien"
    assert r.sidecar["dc:creator"] == "A. Henson"
    assert r.sidecar["dc:description"] == "How to care for a razor."
    assert r.origins["dc:title"] == "transcribed"
    assert r.origins["dc:creator"] == "transcribed"
    assert r.origins["dc:description"] == "transcribed"


def test_title_never_supplied_by_cascade_and_omitted_when_absent():
    r = apply_cataloging_policy({}, _preseed(**{"dc:title": "Should Be Ignored"}),
                                archive_language="en")
    assert "dc:title" not in r.sidecar


def test_creator_falls_back_to_supplied_when_absent():
    r = apply_cataloging_policy({}, _preseed(), archive_language="en")
    assert r.sidecar["dc:creator"] == "Archive Default Author"
    assert r.origins["dc:creator"] == "supplied"


def test_contributor_omitted_not_blanked_when_absent():
    r = apply_cataloging_policy({}, _preseed(), archive_language="en")
    assert "dc:contributor" not in r.sidecar
    assert "dc:contributor" not in r.origins


def test_contributor_transcribed_when_present():
    fm = {"contributor": "Claude Sonnet 4.6 (Anthropic)"}
    r = apply_cataloging_policy(fm, _preseed(), archive_language="en")
    assert r.sidecar["dc:contributor"] == "Claude Sonnet 4.6 (Anthropic)"
    assert r.origins["dc:contributor"] == "transcribed"


def test_description_empty_string_default_never_calculated():
    r = apply_cataloging_policy({}, _preseed(), archive_language="en")
    assert r.sidecar["dc:description"] == ""
    assert r.origins["dc:description"] == "supplied"


# ---------------------------------------------------------------------------
# dc:subject union (spec section 7.1)
# ---------------------------------------------------------------------------

def test_subject_union_transcribed_first_then_supplied_deduped_ordered():
    fm = {"subject": ["rasoirs", "entretien"]}
    r = apply_cataloging_policy(
        fm, _preseed(**{"dc:subject": ["entretien", "grooming"]}),
        archive_language="en",
    )
    assert r.sidecar["dc:subject"] == ["rasoirs", "entretien", "grooming"]
    assert r.origins["dc:subject"] == ["transcribed", "supplied"]


def test_subject_scalar_transcribed_is_coerced_to_list():
    fm = {"subject": "rasoirs"}
    r = apply_cataloging_policy(fm, _preseed(), archive_language="en")
    assert r.sidecar["dc:subject"] == ["rasoirs"]
    assert r.origins["dc:subject"] == ["transcribed"]


def test_subject_only_supplied_when_no_transcribed():
    r = apply_cataloging_policy({}, _preseed(**{"dc:subject": ["grooming"]}),
                                archive_language="en")
    assert r.sidecar["dc:subject"] == ["grooming"]
    assert r.origins["dc:subject"] == ["supplied"]


# ---------------------------------------------------------------------------
# publisher / rights: cascade-owned, transcribed is a narrated exception
# ---------------------------------------------------------------------------

def test_publisher_rights_supplied_by_default_no_finding():
    r = apply_cataloging_policy({"title": "T"}, _preseed(), archive_language="en")
    assert r.sidecar["dc:publisher"] == "Henson Shaving"
    assert r.sidecar["dc:rights"] == "CC BY-SA 4.0"
    assert r.origins["dc:publisher"] == "supplied"
    assert not any(f.kind == "transcribed-exception" for f in r.findings)


def test_publisher_transcribed_wins_and_is_narrated_as_exception():
    fm = {"title": "T", "publisher": "Someone Else Press"}
    r = apply_cataloging_policy(fm, _preseed(), archive_language="en")
    assert r.sidecar["dc:publisher"] == "Someone Else Press"
    assert r.origins["dc:publisher"] == "transcribed"
    exc = [f for f in r.findings if f.kind == "transcribed-exception"]
    assert len(exc) == 1
    assert exc[0].evidence.get("field") == "dc:publisher"


# ---------------------------------------------------------------------------
# language: supplied always wins; disagreement is a finding (spec 7.2)
# ---------------------------------------------------------------------------

def test_language_always_supplied_from_cascade():
    fm = {"title": "T"}
    r = apply_cataloging_policy(fm, _preseed(), archive_language="en")
    assert r.sidecar["dc:language"] == "eng"
    assert r.sidecar["dc:language_bcp47"] == "en"
    assert r.origins["dc:language"] == "supplied"
    assert r.origins["dc:language_bcp47"] == "supplied"


def test_language_disagreement_produces_finding_archive_wins():
    fm = {"title": "T", "language": "fr"}
    r = apply_cataloging_policy(fm, _preseed(), archive_language="en")
    # Archive declaration wins regardless of the claim.
    assert r.sidecar["dc:language_bcp47"] == "en"
    finds = [f for f in r.findings if f.kind == "language-disagreement"]
    assert len(finds) == 1
    assert finds[0].evidence.get("claimed") == "fr"
    assert finds[0].evidence.get("archive") == "en"


def test_language_agreement_produces_no_finding():
    fm = {"title": "T", "language": "en"}
    r = apply_cataloging_policy(fm, _preseed(), archive_language="en")
    assert not any(f.kind == "language-disagreement" for f in r.findings)


def test_language_region_variant_agrees_on_primary_subtag():
    fm = {"title": "T", "language": "en-CA"}
    r = apply_cataloging_policy(fm, _preseed(), archive_language="en")
    assert not any(f.kind == "language-disagreement" for f in r.findings)


# ---------------------------------------------------------------------------
# noted: identity residue and unrecognized keys (spec section 10)
# ---------------------------------------------------------------------------

def test_identity_residue_is_noted_never_admitted():
    fm = {"title": "T", "sat_uuid": "7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e"}
    r = apply_cataloging_policy(fm, _preseed(), archive_language="en")
    assert r.noted["sat_uuid"] == "7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e"
    assert "sat_uuid" not in r.sidecar
    assert "dc:identifier" not in r.sidecar


def test_unrecognized_keys_preserved_verbatim_under_noted():
    fm = {"title": "T", "tags": ["rasoirs"], "custom-field": "some-value"}
    r = apply_cataloging_policy(fm, _preseed(), archive_language="en")
    assert r.noted["unrecognized_keys"] == {
        "tags": ["rasoirs"],
        "custom-field": "some-value",
    }
    assert "tags" not in r.sidecar


# ---------------------------------------------------------------------------
# dc:date fallback order (implementation plan Decision 1)
# ---------------------------------------------------------------------------

def test_date_transcribed_wins():
    fm = {"title": "T", "date": "2020-01-01"}
    r = apply_cataloging_policy(fm, _preseed(), archive_language="en",
                               supplied_date="2026-08-01")
    assert r.sidecar["dc:date"] == "2020-01-01"
    assert r.origins["dc:date"] == "transcribed"


def test_date_falls_back_to_supplied_when_absent():
    r = apply_cataloging_policy({}, _preseed(), archive_language="en",
                               supplied_date="2026-08-01")
    assert r.sidecar["dc:date"] == "2026-08-01"
    assert r.origins["dc:date"] == "supplied"


def test_date_omitted_when_neither_transcribed_nor_supplied():
    r = apply_cataloging_policy({}, _preseed(), archive_language="en")
    assert "dc:date" not in r.sidecar


# ---------------------------------------------------------------------------
# empty frontmatter: nothing transcribed, policy still holds
# ---------------------------------------------------------------------------

def test_none_frontmatter_treated_as_no_transcribed_claims():
    r = apply_cataloging_policy(None, _preseed(), archive_language="en")
    assert r.sidecar["dc:creator"] == "Archive Default Author"
    assert r.sidecar["dc:description"] == ""
    assert r.noted == {}
    assert r.findings == []


# ---------------------------------------------------------------------------
# canonical field ordering in the emitted sidecar (deterministic output)
# ---------------------------------------------------------------------------

def test_sidecar_field_order_is_canonical():
    fm = {
        "title": "T",
        "author": "A",
        "subject": ["s"],
        "description": "d",
        "date": "2020-01-01",
    }
    r = apply_cataloging_policy(fm, _preseed(), archive_language="en")
    order = list(r.sidecar.keys())
    expected = [
        "dc:title", "dc:creator", "dc:subject", "dc:description",
        "dc:date", "dc:publisher", "dc:rights", "dc:language",
        "dc:language_bcp47", "dc:type", "dc:format",
    ]
    assert order == expected
