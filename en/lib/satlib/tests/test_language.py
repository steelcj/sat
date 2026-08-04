"""Tests for satlib.language against spec sections 1.1, 3, and 4.

The fixture registry is a minimal record-jar file containing exactly
the records the tests require; the real IANA file is never needed.
"""

import pytest

from satlib.language import (
    DEFAULT_AUTHORITY_NOTE,
    SubtagRegistry,
    extract_file_date,
    non_authority_expression,
    validate_expression,
)

FIXTURE = b"""File-Date: 2026-06-20
%%
Type: language
Subtag: en
Description: English
Added: 2005-10-16
Suppress-Script: Latn
%%
Type: language
Subtag: fr
Description: French
Added: 2005-10-16
%%
Type: language
Subtag: es
Description: Spanish
Description: Castilian
Added: 2005-10-16
%%
Type: language
Subtag: zh
Description: Chinese
Added: 2005-10-16
Scope: macrolanguage
%%
Type: language
Subtag: ase
Description: American Sign Language
Added: 2005-10-16
Macrolanguage: sgn
%%
Type: language
Subtag: sgn
Description: Sign languages
Added: 2005-10-16
Scope: macrolanguage
%%
Type: language
Subtag: iw
Description: Hebrew
Added: 2005-10-16
Deprecated: 1989-01-01
Preferred-Value: he
%%
Type: script
Subtag: Hant
Description: Han (Traditional variant)
Added: 2005-10-16
%%
Type: region
Subtag: CA
Description: Canada
Added: 2005-10-16
%%
Type: region
Subtag: TW
Description: Taiwan, Province of China
Added: 2005-10-16
%%
Type: variant
Subtag: blasl
Description: Black American Sign Language dialect
Added: 2023-04-25
Prefix: ase
"""


@pytest.fixture(scope="module")
def registry():
    return SubtagRegistry.parse(FIXTURE)


class TestParsing:
    def test_file_date_extracted(self, registry):
        assert extract_file_date(FIXTURE) == "2026-06-20"
        assert registry.file_date == "2026-06-20"

    def test_lookup_is_typed_and_case_insensitive(self, registry):
        assert registry.lookup("language", "en").descriptions == ("English",)
        assert registry.lookup("language", "EN") is not None
        assert registry.lookup("region", "en") is None  # wrong type

    def test_repeated_description_fields_collected(self, registry):
        assert registry.lookup("language", "es").descriptions == (
            "Spanish", "Castilian",
        )

    def test_macrolanguage_and_deprecation_fields(self, registry):
        assert registry.lookup("language", "ase").macrolanguage == "sgn"
        record = registry.lookup("language", "iw")
        assert record.deprecated and record.preferred_value == "he"


class TestDerivationTable:
    """The worked examples of spec section 3.2, verbatim."""

    @pytest.mark.parametrize("tag, dc_language, dc_bcp47", [
        ("en", "eng", "en"),
        ("en-CA", "eng", "en-CA"),
        ("fr-CA", "fra", "fr-CA"),
        ("ase", "sgn", "ase"),
        ("ase-blasl", "sgn", "ase-blasl"),
        ("zh-Hant-TW", "zho", "zh-Hant-TW"),
    ])
    def test_spec_row(self, registry, tag, dc_language, dc_bcp47):
        result = validate_expression(tag, registry)
        assert result.valid, result.errors + result.components[0].errors
        assert result.dc_language == dc_language
        assert result.dc_language_bcp47 == dc_bcp47
        assert result.sat_authority == "external"


class TestCanonicalCasing:
    """ADR-003 section 8.2: casing errors are surfaced, not normalised."""

    @pytest.mark.parametrize("tag, canonical", [
        ("EN", "en"),
        ("fr-ca", "fr-CA"),
        ("zh-hant-TW", "zh-Hant-TW"),
    ])
    def test_wrong_casing_is_invalid_and_names_canonical(
        self, registry, tag, canonical
    ):
        result = validate_expression(tag, registry)
        assert not result.valid
        assert any(canonical.split("-")[-1] in e or canonical in e
                   for c in result.components for e in c.errors)
        assert result.components[0].canonical == canonical


class TestMixedExpressions:
    """ADR-002: underscore joining, alphabetical order."""

    def test_valid_mixed_expression(self, registry):
        result = validate_expression("ase_en", registry)
        assert result.valid
        assert result.sat_authority == "external"
        assert result.dc_language == "und"  # no single primary language
        assert result.dc_language_bcp47 == "ase_en"

    def test_wrong_order_is_invalid(self, registry):
        result = validate_expression("en_ase", registry)
        assert not result.valid
        assert any("alphabetical" in e for e in result.errors)

    def test_mixed_with_regions(self, registry):
        result = validate_expression("en-CA_fr-CA", registry)
        assert result.valid
        assert result.dc_language_bcp47 == "en-CA_fr-CA"


class TestAuthority:
    """Spec section 3.3."""

    def test_registered_and_canonical_is_external(self, registry):
        assert validate_expression("en", registry).sat_authority == "external"

    def test_deprecated_subtag_is_partial_with_note(self, registry):
        result = validate_expression("iw", registry)
        assert result.sat_authority == "partial"
        assert result.sat_authority_note  # note required

    def test_unregistered_subtag_is_none_with_note(self, registry):
        result = validate_expression("qq", registry)
        assert result.sat_authority == "none"
        assert "2026-06-20" in result.sat_authority_note

    def test_extension_singletons_rejected(self, registry):
        result = validate_expression("en-u-ca-gregory", registry)
        assert not result.valid


class TestNonAuthorityModel:
    """Spec section 4: the humpback_songs worked example."""

    def test_generated_private_use_tag(self):
        result = non_authority_expression("humpback_songs", "2026-06-20")
        assert result.dc_language_bcp47 == "x-humpback-songs"
        assert result.dc_language == "und"  # honest default, not a failure
        assert result.sat_authority == "none"
        assert result.sat_authority_note == DEFAULT_AUTHORITY_NOTE.format(
            cache_date="2026-06-20"
        )

    def test_unknown_cache_date_recorded_honestly(self):
        result = non_authority_expression("humpback_songs", None)
        assert "unknown" in result.sat_authority_note


class TestKnownLimitation:
    """Documented MVP behaviour: 3-letter subtags without a
    Macrolanguage record pass through as their own dc:language."""

    def test_three_letter_without_macrolanguage_passes_through(self, registry):
        result = validate_expression("sgn", registry)
        assert result.dc_language == "sgn"
