"""Tests for satlib.cascade: resolution, tripwire, dc:description."""

import pytest

from satlib.assets import write_yaml_asset
from satlib.cascade import (
    CALCULATED,
    cascade,
    is_calculated,
    layers_for,
    resolve_entity,
    verify,
)


class TestThreeStateVocabulary:
    def test_calculated_is_only_the_placeholder(self):
        assert is_calculated("<calculated>")
        assert not is_calculated("")          # deliberately empty
        assert not is_calculated("value")     # resolved
        assert not is_calculated(None)


class TestCascadeResolution:
    def test_deepest_concrete_value_wins(self):
        record = cascade([
            {"dc:rights": "CC BY-SA 4.0"},
            {"dc:rights": "CC0-1.0"},
        ])
        assert record["dc:rights"] == "CC0-1.0"

    def test_empty_string_is_a_real_value_and_wins(self):
        record = cascade([
            {"dc:publisher": "SAT"},
            {"dc:publisher": ""},             # deliberate emptiness
        ])
        assert record["dc:publisher"] == ""

    def test_calculated_never_wins_over_concrete(self):
        # The cascade is precisely the mechanism that fills holes:
        # a deeper <calculated> must not mask a shallower value.
        record = cascade([
            {"dc:creator": "Christopher Steel"},
            {"dc:creator": CALCULATED},
        ])
        assert record["dc:creator"] == "Christopher Steel"

    def test_calculated_everywhere_stays_visible_for_the_tripwire(self):
        record = cascade([
            {"dc:creator": CALCULATED},
            {"dc:creator": CALCULATED},
        ])
        assert record["dc:creator"] == CALCULATED  # not silently dropped

    def test_shallow_value_flows_to_bottom_unopposed(self):
        record = cascade([
            {"dc:rights": "CC BY-SA 4.0"},
            {},
            {},
        ])
        assert record["dc:rights"] == "CC BY-SA 4.0"


class TestDescriptionException:
    """dc:description: never inherited, never <calculated>."""

    def test_never_inherited(self):
        record = cascade([
            {"dc:description": "The collection"},
            {},                                # entity layer says nothing
        ])
        assert record["dc:description"] == ""  # deliberate empty, not inherited

    def test_entity_own_description_used(self):
        record = cascade([
            {"dc:description": "The collection"},
            {"dc:description": "This archive"},
        ])
        assert record["dc:description"] == "This archive"

    def test_calculated_description_preserved_for_violation_report(self):
        record = cascade([{}, {"dc:description": CALCULATED}])
        report = verify(record)
        assert report.description_violation
        assert not report.clean


class TestTripwire:
    def test_clean_record_passes(self):
        assert verify({"dc:creator": "C", "dc:description": ""}).clean

    def test_every_offender_reported_together(self):
        record = {
            "dc:creator": CALCULATED,
            "dc:rights": CALCULATED,
            "dc:title": "Fine",
            "dc:description": "",
        }
        report = verify(record)
        assert report.unresolved == ["dc:creator", "dc:rights"]
        assert len(report.messages()) == 2

    def test_messages_name_the_principle(self):
        report = verify({"dc:creator": CALCULATED})
        assert "not a fallback" in report.messages()[0]


class TestFilesystemCascade:
    """The guide's Step 11 worked example, end to end on disk."""

    def _instance(self, tmp_path):
        root = tmp_path / "sat"
        for lang in ("en", "fr"):
            (root / lang).mkdir(parents=True)

        # Instance defaults live in the sat role dc.yml (ADR-025): the
        # instance owns these settings; lower tiers inherit them.
        write_yaml_asset(root, "sat/dc.yml", {
            "dc:creator": "Christopher Steel",
            "dc:publisher": "SAT – Source Archive Tools",
            "dc:rights": "CC BY-SA 4.0",
        }, is_dir=True)

        # Archive role dc.yml is sparse (ADR-025 section 4): it states the
        # fields the archive owns and inherits the rest. language.yml
        # lives in the archive role too and injects the language fields.
        for lang, iso, title in (("en", "eng", "SAT Documentation (English)"),
                                 ("fr", "fra", "SAT Documentation (français)")):
            write_yaml_asset(root / lang, "archive/dc.yml", {
                "sat:name": lang,
                "dc:title": title,
                "dc:description": "",
            }, is_dir=True)
            write_yaml_asset(root / lang, "archive/language.yml", {
                "dc:language": iso,
                "dc:language_bcp47": lang,
                "sat:authority": "external",
            }, is_dir=True)
        return root

    def test_fr_archive_resolves_exactly_as_the_guide_shows(self, tmp_path):
        root = self._instance(tmp_path)

        record = resolve_entity(root, root / "fr")

        assert record["dc:title"] == "SAT Documentation (français)"
        assert record["dc:creator"] == "Christopher Steel"          # inherited
        assert record["dc:publisher"] == "SAT – Source Archive Tools"
        assert record["dc:rights"] == "CC BY-SA 4.0"                 # inherited
        assert record["dc:language"] == "fra"        # archive record overrides
        assert record["dc:language_bcp47"] == "fr"
        assert record["dc:description"] == ""
        assert verify(record).clean

    def test_language_record_overrides_inherited_default(self, tmp_path):
        root = self._instance(tmp_path)
        # An (incorrect) inherited language default at the instance level
        write_yaml_asset(root, "sat/dc.yml", {
            "dc:creator": "Christopher Steel",
            "dc:publisher": "SAT – Source Archive Tools",
            "dc:rights": "CC BY-SA 4.0",
            "dc:language": "eng",
            "dc:language_bcp47": "en",
        }, is_dir=True)

        record = resolve_entity(root, root / "fr")

        assert record["dc:language"] == "fra"  # the archive's own record wins
        assert record["dc:language_bcp47"] == "fr"

    def test_unresolved_hole_trips_after_filesystem_resolution(self, tmp_path):
        root = self._instance(tmp_path)
        # The instance owns dc:rights; leaving it <calculated> at the
        # owning tier arms the tripwire (ADR-025 section 4).
        write_yaml_asset(root, "sat/dc.yml", {
            "dc:creator": "Christopher Steel",
            "dc:publisher": "SAT – Source Archive Tools",
            "dc:rights": CALCULATED,
        }, is_dir=True)

        report = verify(resolve_entity(root, root / "fr"))

        assert report.unresolved == ["dc:rights"]

    def test_file_entity_cascades_through_all_levels(self, tmp_path):
        root = self._instance(tmp_path)
        docs = root / "en" / "docs"
        docs.mkdir()
        guide = docs / "sat-guide.md"
        guide.write_text("# guide")
        write_yaml_asset(guide, "content/dc.yml", {
            "dc:title": "SAT Guide",
            "dc:description": "How to use SAT.",
        }, is_dir=False)

        record = resolve_entity(root, guide, entity_is_dir=False)

        assert record["dc:title"] == "SAT Guide"
        assert record["dc:creator"] == "Christopher Steel"   # from instance root
        assert record["dc:language"] == "eng"                # from en/ archive
        assert record["dc:description"] == "How to use SAT."  # its own, not inherited

    def test_entity_outside_root_rejected(self, tmp_path):
        root = self._instance(tmp_path)
        with pytest.raises(ValueError):
            layers_for(root, tmp_path / "elsewhere")


class TestRoleDirectoryCascade:
    """The ADR-025 section 7 walk over role directories: dual-role and
    single-role topologies, the content-directory layer, and the
    worked dc:rights example, resolved live on disk."""

    def _dual_role_instance(self, tmp_path):
        """SAT's own shape: a dual-role root (sat + collection), an fr
        archive, a produits/ content directory, and one document."""
        root = tmp_path / "sat"
        document = root / "fr" / "produits" / "guide-rasoir.md"
        document.parent.mkdir(parents=True)
        document.write_text("# Guide du rasoir\n", "utf-8")

        # Instance role: the settings live here.
        write_yaml_asset(root, "sat/dc.yml", {
            "sat:name": "sat",
            "dc:creator": "Christopher Steel",
            "dc:publisher": "SAT – Source Archive Tools",
            "dc:rights": "CC BY-SA 4.0",
        }, is_dir=True)
        # Collection role of the dual-role root: sparse, says nothing.
        write_yaml_asset(root, "collection/dc.yml", {"sat:name": "sat"}, is_dir=True)
        # Archive role: sparse, plus the injected language record.
        write_yaml_asset(root / "fr", "archive/dc.yml",
                         {"sat:name": "fr", "dc:description": ""}, is_dir=True)
        write_yaml_asset(root / "fr", "archive/language.yml", {
            "dc:language": "fra", "dc:language_bcp47": "fr",
            "sat:authority": "external",
        }, is_dir=True)
        # Content organizing directory: sparse.
        write_yaml_asset(root / "fr" / "produits", "content/dc.yml",
                         {"sat:name": "produits"}, is_dir=True)
        return root, document

    def test_dc_rights_worked_example_document_override_wins(self, tmp_path):
        root, document = self._dual_role_instance(tmp_path)
        # The document states its own rights; the deepest stated value wins.
        write_yaml_asset(document, "content/dc.yml", {
            "sat:name": "guide-rasoir.md",
            "dc:title": "Guide du rasoir",
            "dc:rights": "CC BY 4.0",
            "dc:description": "",
        }, is_dir=False)

        record = resolve_entity(root, document, entity_is_dir=False)

        assert record["dc:rights"] == "CC BY 4.0"                 # document wins
        assert record["dc:creator"] == "Christopher Steel"        # inherited
        assert record["dc:language"] == "fra"                     # archive language
        assert record["dc:title"] == "Guide du rasoir"

    def test_every_other_document_inherits_the_instance_rights(self, tmp_path):
        root, document = self._dual_role_instance(tmp_path)
        # A sibling document states nothing about rights.
        sibling = root / "fr" / "produits" / "guide-tondeuse.md"
        sibling.write_text("# Tondeuse\n", "utf-8")
        write_yaml_asset(sibling, "content/dc.yml", {
            "sat:name": "guide-tondeuse.md",
            "dc:title": "Guide de la tondeuse",
            "dc:description": "",
        }, is_dir=False)

        record = resolve_entity(root, sibling, entity_is_dir=False)

        assert record["dc:rights"] == "CC BY-SA 4.0"              # inherited, visible

    def test_sat_name_never_leaks_across_tiers(self, tmp_path):
        root, document = self._dual_role_instance(tmp_path)
        write_yaml_asset(document, "content/dc.yml", {
            "sat:name": "guide-rasoir.md", "dc:title": "G", "dc:description": "",
        }, is_dir=False)
        record = resolve_entity(root, document, entity_is_dir=False)
        # sat:name is a name record, not an inherited setting.
        assert "sat:name" not in record

    def test_single_role_collection_does_not_inherit_dual_role_override(self, tmp_path):
        """A single-role collection under collections/ inherits the
        instance, not the dual-role collection beside it (nearest
        collection wins, ADR-025 section 7)."""
        root, _ = self._dual_role_instance(tmp_path)
        # The dual-role collection overrides rights for its own documents.
        write_yaml_asset(root, "collection/dc.yml",
                         {"sat:name": "sat", "dc:rights": "CC BY-NC 4.0"},
                         is_dir=True)
        # A single-role collection in the standard collections home.
        doc = root / "collections" / "test-collection" / "en" / "sample.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Sample\n", "utf-8")
        collection = root / "collections" / "test-collection"
        write_yaml_asset(collection, "collection/dc.yml",
                         {"sat:name": "test-collection"}, is_dir=True)
        write_yaml_asset(collection / "en", "archive/dc.yml",
                         {"sat:name": "en", "dc:description": ""}, is_dir=True)
        write_yaml_asset(collection / "en", "archive/language.yml", {
            "dc:language": "eng", "dc:language_bcp47": "en",
            "sat:authority": "external",
        }, is_dir=True)
        write_yaml_asset(doc, "content/dc.yml",
                         {"sat:name": "sample.md", "dc:title": "Sample",
                          "dc:description": ""}, is_dir=False)

        record = resolve_entity(root, doc, entity_is_dir=False)

        # The instance's rights, not the dual-role collection's override.
        assert record["dc:rights"] == "CC BY-SA 4.0"
        assert record["dc:creator"] == "Christopher Steel"
        assert record["dc:language"] == "eng"


class TestProvisionalListBehaviour:
    """OPEN DECISION (pinned): dc:subject currently replaces, not
    merges, down the cascade. If merge is chosen instead, this test
    is the one that changes."""

    def test_subject_replacement_is_the_current_behaviour(self):
        record = cascade([
            {"dc:subject": ["archives", "language"]},
            {"dc:subject": ["sat init"]},
        ])
        assert record["dc:subject"] == ["sat init"]
