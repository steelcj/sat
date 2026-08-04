"""Tests for satlib.archive: plan/create, immutability, composition.

Ends with the scaffold integration test: registry -> validation ->
plan -> create -> cascade -> tripwire, the whole library in one path.
"""

import datetime

import pytest

from satlib.archive import (
    ArchiveCollisionError,
    ArchiveExistsError,
    create_archive,
    has_provenance,
    plan_archive,
)
from satlib.assets import read_yaml_asset, write_yaml_asset
from satlib.cascade import CALCULATED, resolve_entity, verify
from satlib.language import (
    SubtagRegistry,
    non_authority_expression,
    validate_expression,
)
from tests.test_language import FIXTURE

FIXED_NOW = datetime.datetime(
    2026, 7, 9, 14, 32, 7,
    tzinfo=datetime.timezone(datetime.timedelta(hours=-4)),
)


@pytest.fixture(scope="module")
def registry():
    return SubtagRegistry.parse(FIXTURE)


def plan_en(parent, registry, **overrides):
    kwargs = dict(
        tool="sat-tool",
        tool_version="0.4.0",
        registry_file_date=registry.file_date,
        now=lambda: FIXED_NOW,
    )
    kwargs.update(overrides)
    return plan_archive(parent, validate_expression("en", registry), **kwargs)


class TestPlan:
    def test_plan_is_pure(self, tmp_path, registry):
        plan = plan_en(tmp_path, registry)
        assert plan.directory == tmp_path / "en"
        assert not plan.directory.exists()          # nothing written

    def test_records_match_the_guide_step_9(self, tmp_path, registry):
        plan = plan_en(tmp_path, registry, title="SAT Documentation (English)")

        assert plan.records["language.yml"] == {
            "dc:language": "eng",
            "dc:language_bcp47": "en",
            "sat:authority": "external",
        }
        assert plan.records["provenance.yml"] == {
            "created": "2026-07-09T14:32:07-04:00",
            "tool": "sat-tool",
            "tool_version": "0.4.0",
            "registry_file_date": "2026-06-20",
        }
        dc = plan.records["dc.yml"]
        assert dc["sat:name"] == "en"              # the self-recorded name
        assert dc["dc:title"] == "SAT Documentation (English)"
        assert dc["dc:date"] == "2026-07-09"
        assert dc["dc:description"] == ""          # never <calculated>
        # creator, publisher, rights inherit from the instance — a sparse
        # archive states none of them (ADR-025 section 4)
        assert "dc:creator" not in dc
        assert "dc:publisher" not in dc
        assert "dc:rights" not in dc
        # language lives in language.yml, injected by the cascade
        assert "dc:language" not in dc

    def test_missing_title_is_a_visible_hole_not_a_blank(self, tmp_path, registry):
        plan = plan_en(tmp_path, registry)
        assert plan.records["dc.yml"]["dc:title"] == CALCULATED

    def test_supplied_defaults_leave_no_holes(self, tmp_path, registry):
        plan = plan_en(tmp_path, registry, title="T", creator="C",
                       publisher="P", rights="R")
        dc = plan.records["dc.yml"]
        assert CALCULATED not in dc.values()

    def test_invalid_expression_refused_at_plan_time(self, tmp_path, registry):
        bad = validate_expression("EN", registry)  # wrong casing
        with pytest.raises(ValueError, match="invalid expression"):
            plan_archive(tmp_path, bad, tool="t", tool_version="0",
                         registry_file_date=None)

    def test_naive_timestamp_refused(self, tmp_path, registry):
        with pytest.raises(ValueError, match="timezone-aware"):
            plan_en(tmp_path, registry,
                    now=lambda: datetime.datetime(2026, 7, 9))


class TestDirectoryNaming:
    def test_mixed_expression_keeps_underscore_form(self, tmp_path, registry):
        plan = plan_archive(
            tmp_path, validate_expression("ase_en", registry),
            tool="t", tool_version="0", registry_file_date=None,
            now=lambda: FIXED_NOW,
        )
        assert plan.directory.name == "ase_en"

    def test_non_authority_keeps_the_community_name(self, tmp_path, registry):
        # spec section 4: the community named the directory; SAT
        # generated only the x- tag
        validation = non_authority_expression("humpback_songs", registry.file_date)
        plan = plan_archive(
            tmp_path, validation,
            tool="t", tool_version="0", registry_file_date=registry.file_date,
            now=lambda: FIXED_NOW,
        )
        assert plan.directory.name == "humpback_songs"
        assert plan.records["language.yml"]["dc:language_bcp47"] == "x-humpback-songs"
        assert plan.records["language.yml"]["dc:language"] == "und"
        assert "sat:authority_note" in plan.records["language.yml"]


class TestCreate:
    def test_create_writes_all_records_into_the_archive_role(self, tmp_path, registry):
        directory = create_archive(plan_en(tmp_path, registry, title="T"))

        assert directory == tmp_path / "en"
        assert has_provenance(directory)
        assert read_yaml_asset(directory, "archive/language.yml")["sat:authority"] == "external"
        assert read_yaml_asset(directory, "archive/provenance.yml")["tool_version"] == "0.4.0"
        assert read_yaml_asset(directory, "archive/dc.yml")["dc:title"] == "T"
        assert read_yaml_asset(directory, "archive/dc.yml")["sat:name"] == "en"
        assert read_yaml_asset(directory, "archive/dc.yml")["dc:type"] == "Collection"

    def test_reinitialisation_refused_as_immutable(self, tmp_path, registry):
        create_archive(plan_en(tmp_path, registry))

        with pytest.raises(ArchiveExistsError) as exc:
            create_archive(plan_en(tmp_path, registry))

        message = str(exc.value)
        assert "immutable" in message
        assert "not a merge" in message
        assert "No records were written" in message

    def test_colliding_structure_refused(self, tmp_path, registry):
        (tmp_path / "en").mkdir()
        (tmp_path / "en" / "stray.md").write_text("content")

        with pytest.raises(ArchiveCollisionError):
            create_archive(plan_en(tmp_path, registry))

    def test_existing_empty_directory_is_acceptable(self, tmp_path, registry):
        (tmp_path / "en").mkdir()
        directory = create_archive(plan_en(tmp_path, registry))
        assert has_provenance(directory)


class TestScaffoldIntegration:
    """The whole library in one path: registry fixture -> validate ->
    plan -> create -> instance defaults -> cascade -> tripwire.
    This is Step 9 followed by Step 11, clean end to end."""

    def test_created_archive_resolves_clean_through_the_cascade(self, tmp_path, registry):
        instance = tmp_path / "sat"
        instance.mkdir()
        write_yaml_asset(instance, "sat/dc.yml", {
            "dc:creator": "Christopher Steel",
            "dc:publisher": "SAT – Source Archive Tools",
            "dc:rights": "CC BY-SA 4.0",
        }, is_dir=True)

        for expression, title in (("en", "SAT Documentation (English)"),
                                  ("fr", "SAT Documentation (français)"),
                                  ("es", "SAT Documentation (español)")):
            create_archive(plan_archive(
                instance, validate_expression(expression, registry),
                tool="sat-tool", tool_version="0.4.0",
                registry_file_date=registry.file_date,
                title=title, now=lambda: FIXED_NOW,
            ))

        record = resolve_entity(instance, instance / "fr")

        assert record["dc:title"] == "SAT Documentation (français)"
        assert record["dc:creator"] == "Christopher Steel"     # cascade filled the hole
        assert record["dc:rights"] == "CC BY-SA 4.0"
        assert record["dc:language"] == "fra"                  # archive record
        assert record["dc:language_bcp47"] == "fr"
        assert record["dc:description"] == ""
        assert verify(record).clean                            # the tripwire passes

    def test_missing_instance_default_trips_exactly_one_field(self, tmp_path, registry):
        instance = tmp_path / "sat"
        instance.mkdir()
        # The instance owns the creator/publisher/rights holes (ADR-025
        # section 4): an unfilled rights hole arms the tripwire at the
        # instance tier, not at the sparse archive below it.
        write_yaml_asset(instance, "sat/dc.yml", {
            "dc:creator": "Christopher Steel",
            "dc:publisher": "SAT – Source Archive Tools",
            "dc:rights": CALCULATED,             # unfilled at the owning tier
        }, is_dir=True)
        create_archive(plan_archive(
            instance, validate_expression("en", registry),
            tool="sat-tool", tool_version="0.4.0",
            registry_file_date=registry.file_date,
            title="SAT Documentation (English)", now=lambda: FIXED_NOW,
        ))

        report = verify(resolve_entity(instance, instance / "en"))

        assert report.unresolved == ["dc:rights"]
        assert "not a fallback" in report.messages()[0]
