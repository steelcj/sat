"""Tests for satlib.spdx against ADR-033.

The fixtures are minimal licenses.json / exceptions.json documents
holding exactly the entries the tests require; the real SPDX files are
never fetched. Shapes match the SPDX-published JSON: a top-level
``licenseListVersion`` plus a ``licenses`` / ``exceptions`` array whose
entries carry ``licenseId`` / ``licenseExceptionId``,
``isDeprecatedLicenseId``, and the optional ``isOsiApproved`` /
``isFsfLibre`` flags.
"""

import json

import pytest

from satlib.spdx import (
    ExceptionList,
    LicenseList,
    extract_list_version,
    extract_spdx_tags,
    validate_expression,
    validate_identifier,
)

LICENSES = json.dumps({
    "licenseListVersion": "3.24",
    "licenses": [
        {
            "licenseId": "AGPL-3.0-or-later",
            "name": "GNU Affero General Public License v3.0 or later",
            "isDeprecatedLicenseId": False,
            "isOsiApproved": True,
            "isFsfLibre": True,
            "reference": "https://spdx.org/licenses/AGPL-3.0-or-later.html",
        },
        {
            "licenseId": "GPL-3.0-or-later",
            "name": "GNU General Public License v3.0 or later",
            "isDeprecatedLicenseId": False,
            "isOsiApproved": True,
        },
        {
            "licenseId": "MIT",
            "name": "MIT License",
            "isDeprecatedLicenseId": False,
            "isOsiApproved": True,
        },
        {
            "licenseId": "Apache-2.0",
            "name": "Apache License 2.0",
            "isDeprecatedLicenseId": False,
            "isOsiApproved": True,
        },
        {
            "licenseId": "CC-BY-SA-4.0",
            "name": "Creative Commons Attribution Share Alike 4.0 International",
            "isDeprecatedLicenseId": False,
        },
        {
            "licenseId": "GPL-3.0",
            "name": "GNU General Public License v3.0 only",
            "isDeprecatedLicenseId": True,
            "isOsiApproved": True,
        },
    ],
}).encode("utf-8")

EXCEPTIONS = json.dumps({
    "licenseListVersion": "3.24",
    "exceptions": [
        {
            "licenseExceptionId": "Classpath-exception-2.0",
            "name": "Classpath exception 2.0",
            "isDeprecatedLicenseId": False,
        },
        {
            "licenseExceptionId": "Nokia-Qt-exception-1.1",
            "name": "Nokia Qt LGPL exception 1.1",
            "isDeprecatedLicenseId": True,
        },
    ],
}).encode("utf-8")


@pytest.fixture(scope="module")
def licenses():
    return LicenseList.parse(LICENSES)


@pytest.fixture(scope="module")
def exceptions():
    return ExceptionList.parse(EXCEPTIONS)


class TestParsing:
    def test_list_version_extracted(self, licenses):
        assert extract_list_version(LICENSES) == "3.24"
        assert licenses.list_version == "3.24"

    def test_list_version_of_garbage_is_none(self):
        assert extract_list_version(b"not json") is None

    def test_record_carries_flags(self, licenses):
        record = licenses.get("AGPL-3.0-or-later")
        assert record.osi_approved is True
        assert record.fsf_libre is True
        assert record.deprecated is False

    def test_absent_fsf_flag_is_none_not_false(self, licenses):
        # isFsfLibre is absent from most entries: absence is "no
        # statement", never a claim of "not libre".
        assert licenses.get("MIT").fsf_libre is None

    def test_deprecated_flag_parsed(self, licenses):
        assert licenses.get("GPL-3.0").deprecated is True


class TestSingleIdentifier:
    def test_current_identifier_is_valid(self, licenses):
        result = validate_identifier("AGPL-3.0-or-later", licenses)
        assert result.valid
        assert result.registered
        assert not result.deprecated
        assert result.osi_approved is True

    def test_unknown_identifier_is_invalid(self, licenses):
        result = validate_identifier("GPL-99.9", licenses)
        assert not result.valid
        assert not result.registered
        assert any("not a current SPDX" in e for e in result.errors)

    def test_deprecated_identifier_is_registered_but_flagged(self, licenses):
        result = validate_identifier("GPL-3.0", licenses)
        assert result.registered
        assert result.deprecated
        assert not result.valid  # deprecation is a finding
        assert any("deprecated" in e for e in result.errors)

    def test_wrong_casing_names_the_canonical_form(self, licenses):
        result = validate_identifier("mit", licenses)
        assert not result.valid
        assert result.registered  # it is a real license, just miscased
        assert result.canonical == "MIT"
        assert not result.casing_valid
        assert any("canonical casing" in e for e in result.errors)

    def test_or_later_operator_is_accepted(self, licenses):
        result = validate_identifier("Apache-2.0+", licenses)
        assert result.valid
        assert result.or_later
        assert result.identifier == "Apache-2.0"

    def test_license_ref_is_custom_and_unchecked(self, licenses):
        result = validate_identifier("LicenseRef-MyCompany-Proprietary",
                                     licenses)
        assert result.valid
        assert result.custom_ref
        assert result.registered

    def test_document_ref_license_ref_is_custom(self, licenses):
        result = validate_identifier("DocumentRef-spdx-tool:LicenseRef-1",
                                     licenses)
        assert result.valid
        assert result.custom_ref

    def test_plus_on_license_ref_is_rejected(self, licenses):
        result = validate_identifier("LicenseRef-Foo+", licenses)
        assert not result.valid
        assert any("'+' operator does not apply" in e for e in result.errors)


class TestExpression:
    def test_single_current_license(self, licenses):
        result = validate_expression("AGPL-3.0-or-later", licenses)
        assert result.valid
        assert len(result.components) == 1

    def test_and_of_two_current_licenses(self, licenses):
        result = validate_expression("MIT AND Apache-2.0", licenses)
        assert result.valid
        assert len(result.components) == 2

    def test_or_of_two_current_licenses(self, licenses):
        result = validate_expression("MIT OR GPL-3.0-or-later", licenses)
        assert result.valid

    def test_parenthesised_expression(self, licenses):
        result = validate_expression(
            "(MIT OR Apache-2.0) AND CC-BY-SA-4.0", licenses)
        assert result.valid
        assert len(result.components) == 3

    def test_with_exception_validated(self, licenses, exceptions):
        result = validate_expression(
            "GPL-3.0-or-later WITH Classpath-exception-2.0",
            licenses, exceptions)
        assert result.valid

    def test_with_unknown_exception_is_invalid(self, licenses, exceptions):
        result = validate_expression(
            "GPL-3.0-or-later WITH No-Such-exception",
            licenses, exceptions)
        assert not result.valid
        assert any("license-exception" in e for e in result.errors)

    def test_with_deprecated_exception_flagged(self, licenses, exceptions):
        result = validate_expression(
            "GPL-3.0-or-later WITH Nokia-Qt-exception-1.1",
            licenses, exceptions)
        assert not result.valid
        assert any("deprecated" in e for e in result.errors)

    def test_deprecated_component_surfaces_on_expression(self, licenses):
        result = validate_expression("GPL-3.0 OR MIT", licenses)
        assert not result.valid
        assert result.deprecated

    def test_unknown_component_invalidates_expression(self, licenses):
        result = validate_expression("MIT AND Bogus-1.0", licenses)
        assert not result.valid


class TestExtractSpdxTags:
    def test_tag_in_yaml_folded_scalar(self):
        text = (
            "dc:rights: >\n"
            "  Copyright 2026 Christopher Steel.\n"
            "  SPDX-License-Identifier: AGPL-3.0-or-later\n"
        )
        assert extract_spdx_tags(text) == [(3, "AGPL-3.0-or-later")]

    def test_tag_in_source_comment(self):
        text = "#!/usr/bin/env python3\n# SPDX-License-Identifier: GPL-3.0-or-later\n"
        assert extract_spdx_tags(text) == [(2, "GPL-3.0-or-later")]

    def test_compound_expression_kept_whole(self):
        text = "SPDX-License-Identifier: MIT OR Apache-2.0\n"
        assert extract_spdx_tags(text) == [(1, "MIT OR Apache-2.0")]

    def test_multiple_tags_ordered_and_numbered(self):
        text = "SPDX-License-Identifier: MIT\n\n\nSPDX-License-Identifier: GPL-3.0-or-later\n"
        assert extract_spdx_tags(text) == [
            (1, "MIT"), (4, "GPL-3.0-or-later"),
        ]

    def test_empty_tag_is_skipped(self):
        assert extract_spdx_tags("SPDX-License-Identifier:   \n") == []

    def test_no_tag_returns_empty(self):
        assert extract_spdx_tags("just some prose, no license here\n") == []

    def test_tag_inside_string_literal_is_ignored(self):
        # As it appears in this test file and in spdx.py itself: the
        # marker is data, preceded by a quote, not a declaration.
        text = '        "  SPDX-License-Identifier: AGPL-3.0-or-later\\n"\n'
        assert extract_spdx_tags(text) == []

    def test_tag_in_inline_code_prose_is_ignored(self):
        text = "the field carries `SPDX-License-Identifier: MIT` inline\n"
        assert extract_spdx_tags(text) == []

    def test_placeholder_after_tag_is_ignored(self):
        text = "    SPDX-License-Identifier: <expr>   anywhere in a doc\n"
        assert extract_spdx_tags(text) == []


class TestMalformedExpression:
    def test_empty_expression(self, licenses):
        result = validate_expression("   ", licenses)
        assert not result.valid
        assert any("empty" in e for e in result.errors)

    def test_trailing_operator(self, licenses):
        result = validate_expression("MIT AND", licenses)
        assert not result.valid
        assert any("ends after 'AND'" in e for e in result.errors)

    def test_leading_operator(self, licenses):
        result = validate_expression("OR MIT", licenses)
        assert not result.valid

    def test_two_licenses_without_operator(self, licenses):
        result = validate_expression("MIT Apache-2.0", licenses)
        assert not result.valid
        assert any("after a complete expression" in e for e in result.errors)

    def test_unbalanced_paren(self, licenses):
        result = validate_expression("(MIT OR Apache-2.0", licenses)
        assert not result.valid
        assert any("unbalanced" in e for e in result.errors)

    def test_lowercase_operator_is_flagged(self, licenses):
        result = validate_expression("MIT and Apache-2.0", licenses)
        assert not result.valid
        assert any("must be uppercase" in e for e in result.errors)

    def test_with_missing_exception(self, licenses, exceptions):
        result = validate_expression("GPL-3.0-or-later WITH", licenses,
                                     exceptions)
        assert not result.valid
        assert any("WITH" in e for e in result.errors)
