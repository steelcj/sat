#
# source
#   project: sat
#   path: en/bin/content/tests/content-ingress-tests.py
#
"""Tool-level tests for content ingress (content-ingress.py).

The section-4 pipeline end to end against a hermetic cascade fixture built
under tmp_path, offline (mirroring test_work.py / test_create.py rather than
seed_example_collection, which pulls the IANA registry). Steps 0 (staging)
and 9.5 (markdown normalization) are out of this increment.

Written before the tool exists, per the SAT development cycle's test stage.
Run with, from the repo root and the satlib venv:

    python -m pytest en/bin/content/tests -o python_files='content-ingress-tests.py'
"""

import importlib.util
import pathlib

import pytest

from satlib.roles import (
    ROLE_ARCHIVE,
    ROLE_COLLECTION,
    ROLE_CONTENT,
    ROLE_SAT,
    has_role,
    read_role_yaml,
    write_role_yaml,
)
from satlib.work import has_document_identity, read_document_identity


# ---------------------------------------------------------------------------
# Load the hyphenated tool file as a module
# ---------------------------------------------------------------------------

_TOOL_PATH = pathlib.Path(__file__).resolve().parents[1] / "content-ingress.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("content_ingress", _TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_dispatcher():
    path = _TOOL_PATH.parent / "content.py"
    spec = importlib.util.spec_from_file_location("content_dispatch", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Hermetic cascade fixture (offline)
# ---------------------------------------------------------------------------

def build_instance(tmp_path, *, lang="en", iso="eng", bcp47="en"):
    """An instance -> collection -> language-archive tree that resolves
    clean (no <calculated>), with the supplied side of every policy field."""
    root = tmp_path / "instance"
    write_role_yaml(root, ROLE_SAT, "dc.yml", {
        "sat:name": "instance",
        "dc:creator": "Archive Default Author",
        "dc:publisher": "Henson Shaving",
        "dc:rights": "CC BY-SA 4.0",
        "dc:type": "Text",
        "dc:format": "text/markdown",
    }, is_dir=True)

    collection = root / "collections" / "test-collection"
    collection.mkdir(parents=True, exist_ok=True)
    write_role_yaml(collection, ROLE_COLLECTION, "dc.yml",
                    {"sat:name": "test-collection"}, is_dir=True)

    archive = collection / lang
    archive.mkdir(parents=True, exist_ok=True)
    write_role_yaml(archive, ROLE_ARCHIVE, "dc.yml", {"sat:name": lang}, is_dir=True)
    write_role_yaml(archive, ROLE_ARCHIVE, "language.yml",
                    {"dc:language": iso, "dc:language_bcp47": bcp47}, is_dir=True)
    return root, collection, archive


def write_doc(directory, name, text):
    directory.mkdir(parents=True, exist_ok=True)
    doc = directory / name
    doc.write_text(text, "utf-8")
    return doc


def assets_dir(doc):
    return doc.parent / f".{doc.name}.assets"


def ingress_record(doc):
    """Load the single ingress record written for a document."""
    records = sorted((assets_dir(doc) / "content" / "ingress").glob("ingress-*.yml"))
    assert records, "no ingress record written"
    import yaml
    return yaml.safe_load(records[-1].read_text("utf-8"))


SAMPLE = (
    "---\n"
    "title: Guide d'entretien\n"
    "author: A. Henson\n"
    "subject: [rasoirs, entretien]\n"
    "description: How to care for a razor.\n"
    "---\n"
    "# Guide\n\nBody text.\n"
)


# ---------------------------------------------------------------------------
# Single document, happy path
# ---------------------------------------------------------------------------

def test_single_document_writes_the_full_record_set(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "sample.md", SAMPLE)

    rc = tool.main([str(doc)])
    assert rc == 0

    assert has_document_identity(doc)
    sidecar = read_role_yaml(doc, ROLE_CONTENT, "dc.yml", is_dir=False)
    assert sidecar["dc:title"] == "Guide d'entretien"
    assert sidecar["dc:creator"] == "A. Henson"
    assert sidecar["dc:subject"] == ["rasoirs", "entretien"]
    assert sidecar["dc:publisher"] == "Henson Shaving"       # supplied
    assert sidecar["dc:language_bcp47"] == "en"              # supplied
    assert read_role_yaml(doc, ROLE_CONTENT, "provenance.yml", is_dir=False)
    assert read_role_yaml(doc, ROLE_CONTENT, "fixity.yml", is_dir=False)


def test_frontmatter_is_stripped_from_prose(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "sample.md", SAMPLE)
    tool.main([str(doc)])
    body = doc.read_text("utf-8")
    assert body == "# Guide\n\nBody text.\n"
    assert "---" not in body.splitlines()[0]


def test_fixity_attests_the_stripped_prose(tmp_path):
    tool = load_tool()
    from satlib.fixity import digest_file, read_fixity
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "sample.md", SAMPLE)
    tool.main([str(doc)])
    record = read_fixity(doc, ROLE_CONTENT, is_dir=False)
    assert record["content"]["digest"] == digest_file(doc)


def test_ingress_record_shape(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "sample.md", SAMPLE)
    tool.main([str(doc)])
    rec = ingress_record(doc)
    assert rec["frontmatter_present"] is True
    assert rec["origins"]["dc:title"] == "transcribed"
    assert rec["origins"]["dc:publisher"] == "supplied"
    assert "original_frontmatter" in rec and "title: Guide" in rec["original_frontmatter"]
    assert rec["recorded_by"]["command"] == "content ingress"


# ---------------------------------------------------------------------------
# Refusal and idempotency
# ---------------------------------------------------------------------------

def test_refuse_reingest_single_scope(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "sample.md", SAMPLE)
    assert tool.main([str(doc)]) == 0
    # Second run must refuse and change nothing.
    assert tool.main([str(doc)]) != 0


def test_no_frontmatter_document_still_ingresses(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "plain.md", "# Already Pure\n\nProse.\n")
    assert tool.main([str(doc)]) == 0
    rec = ingress_record(doc)
    assert rec["frontmatter_present"] is False
    sidecar = read_role_yaml(doc, ROLE_CONTENT, "dc.yml", is_dir=False)
    assert sidecar["dc:creator"] == "Archive Default Author"  # supplied fallback


# ---------------------------------------------------------------------------
# Content-directory chain minting (step 2)
# ---------------------------------------------------------------------------

def test_directory_chain_is_minted(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive / "products", "guide.md", SAMPLE)
    assert tool.main([str(doc)]) == 0
    # The intervening content-organizing directory gained the content role.
    assert has_role(archive / "products", ROLE_CONTENT, is_dir=True)


# ---------------------------------------------------------------------------
# Expression-of (work joining at ingress, section 8)
# ---------------------------------------------------------------------------

def test_expression_of_path_form_joins_the_work(tmp_path):
    tool = load_tool()
    _, collection, archive = build_instance(tmp_path)
    en_doc = write_doc(archive, "sample.md", SAMPLE)
    assert tool.main([str(en_doc)]) == 0
    en_work = read_document_identity(en_doc)["sat:work"]

    fr_archive = collection / "fr"
    write_role_yaml(fr_archive, ROLE_ARCHIVE, "dc.yml", {"sat:name": "fr"}, is_dir=True)
    write_role_yaml(fr_archive, ROLE_ARCHIVE, "language.yml",
                    {"dc:language": "fra", "dc:language_bcp47": "fr"}, is_dir=True)
    fr_doc = write_doc(fr_archive, "exemple.md", "---\ntitle: Exemple\n---\n# Exemple\n")

    assert tool.main([str(fr_doc), "--expression-of", str(en_doc)]) == 0
    assert read_document_identity(fr_doc)["sat:work"] == en_work


def test_expression_of_unresolved_is_fatal_before_write(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "sample.md", SAMPLE)
    rc = tool.main([str(doc), "--expression-of", "does/not/exist.md"])
    assert rc != 0
    assert not has_document_identity(doc)


# ---------------------------------------------------------------------------
# Failure modes (section 12)
# ---------------------------------------------------------------------------

def test_malformed_frontmatter_is_fatal(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "bad.md", "---\ntitle: : broken\n  - x\n---\nbody\n")
    rc = tool.main([str(doc)])
    assert rc != 0
    assert not has_document_identity(doc)


def test_calculated_tripwire_is_fatal(tmp_path):
    tool = load_tool()
    root, _, archive = build_instance(tmp_path)
    # Poison the instance with an unresolved <calculated> field.
    write_role_yaml(root, ROLE_SAT, "dc.yml", {
        "sat:name": "instance",
        "dc:creator": "<calculated>",
        "dc:publisher": "Henson Shaving",
        "dc:rights": "CC BY-SA 4.0",
    }, is_dir=True)
    doc = write_doc(archive, "sample.md", "---\n---\n# T\n")  # nothing transcribed
    rc = tool.main([str(doc)])
    assert rc != 0
    assert not has_document_identity(doc)


# ---------------------------------------------------------------------------
# dc:date fallback (plan Decision 1)
# ---------------------------------------------------------------------------

def test_date_transcribed_wins(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "d.md", "---\ntitle: T\ndate: 2020-01-01\n---\n# T\n")
    tool.main([str(doc)])
    sidecar = read_role_yaml(doc, ROLE_CONTENT, "dc.yml", is_dir=False)
    assert str(sidecar["dc:date"]) == "2020-01-01"
    assert ingress_record(doc)["origins"]["dc:date"] == "transcribed"


def test_date_operator_flag_used_when_absent(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "d.md", "---\ntitle: T\n---\n# T\n")
    tool.main([str(doc), "--date", "1999-12-31"])
    sidecar = read_role_yaml(doc, ROLE_CONTENT, "dc.yml", is_dir=False)
    assert sidecar["dc:date"] == "1999-12-31"
    assert ingress_record(doc)["origins"]["dc:date"] == "supplied"


def test_date_falls_through_to_utc_now_and_is_noted(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "d.md", "---\ntitle: T\n---\n# T\n")
    tool.main([str(doc)])  # no transcribed date, no --date; Linux has no birthtime
    rec = ingress_record(doc)
    assert rec["origins"]["dc:date"] == "supplied"
    assert "date_fallback" in rec["noted"]


# ---------------------------------------------------------------------------
# Language disagreement survives as a finding (sections 7.2, 10)
# ---------------------------------------------------------------------------

def test_language_disagreement_recorded_as_finding(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)  # en archive
    doc = write_doc(archive, "misfiled.md", "---\ntitle: T\nlanguage: fr\n---\n# T\n")
    assert tool.main([str(doc)]) == 0
    rec = ingress_record(doc)
    kinds = [f["kind"] for f in rec["findings"]]
    assert "language-disagreement" in kinds
    sidecar = read_role_yaml(doc, ROLE_CONTENT, "dc.yml", is_dir=False)
    assert sidecar["dc:language_bcp47"] == "en"  # archive wins


# ---------------------------------------------------------------------------
# Dry-run writes nothing
# ---------------------------------------------------------------------------

def test_dry_run_writes_nothing(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "sample.md", SAMPLE)
    rc = tool.main([str(doc), "--dry-run"])
    assert rc == 0
    assert not has_document_identity(doc)
    assert not assets_dir(doc).exists()
    assert doc.read_text("utf-8") == SAMPLE  # untouched


# ---------------------------------------------------------------------------
# Batch scope via --tree
# ---------------------------------------------------------------------------

def test_tree_batch_processes_and_skips_identified(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    a = write_doc(archive / "products", "a.md", SAMPLE)
    b = write_doc(archive / "products", "b.md", SAMPLE)
    # Pre-identify a; batch must skip it, process b, and not error.
    assert tool.main([str(a)]) == 0
    rc = tool.main(["--tree", str(archive / "products")])
    assert rc == 0
    assert has_document_identity(b)


# ---------------------------------------------------------------------------
# Increment 2: staging promotion (ADR-029)
# ---------------------------------------------------------------------------

MISFILED = (  # French body, frontmatter wrongly claims English (the lesson)
    "---\n"
    "dc:title: \"Note de service\"\n"
    "dc:language_bcp47: en\n"
    "---\n"
    "# Note de service\n\nCeci est un document en français.\n"
)


def test_to_promotes_then_catalogs(tmp_path):
    tool = load_tool()
    root, collection, _ = build_instance(tmp_path, lang="fr", iso="fra", bcp47="fr")
    staging = collection / "staging"
    src = write_doc(staging, "welcome.md",
                    "---\ntitle: Welcome\n---\n# Welcome\n\nProse.\n")
    fr_archive = collection / "fr"

    rc = tool.main([str(src), "--to", str(fr_archive)])
    assert rc == 0
    assert not src.exists()                       # moved out of staging
    moved = fr_archive / "welcome.md"
    assert has_document_identity(moved)           # cataloged at new path
    sidecar = read_role_yaml(moved, ROLE_CONTENT, "dc.yml", is_dir=False)
    assert sidecar["dc:language_bcp47"] == "fr"


def test_to_invalid_destination_is_fatal_before_move(tmp_path):
    tool = load_tool()
    root, collection, _ = build_instance(tmp_path)
    staging = collection / "staging"
    src = write_doc(staging, "welcome.md", SAMPLE)
    # A destination with no archive ancestor.
    outside = tmp_path / "nowhere" / "here"
    rc = tool.main([str(src), "--to", str(outside)])
    assert rc != 0
    assert src.exists()                           # not moved
    assert not (outside / "welcome.md").exists()


def test_to_destination_never_inferred_language_finding_fires(tmp_path):
    """The misfiled sample: French body, frontmatter claims en. Promoting it
    to the fr archive fires the language-disagreement finding, because the
    operator, not the frontmatter, chose the destination (ADR-029 decision 3)."""
    tool = load_tool()
    root, collection, _ = build_instance(tmp_path, lang="fr", iso="fra", bcp47="fr")
    staging = collection / "staging"
    src = write_doc(staging, "note-de-service.md", MISFILED)
    fr_archive = collection / "fr"

    assert tool.main([str(src), "--to", str(fr_archive)]) == 0
    moved = fr_archive / "note-de-service.md"
    rec = ingress_record(moved)
    kinds = [f["kind"] for f in rec["findings"]]
    assert "language-disagreement" in kinds
    sidecar = read_role_yaml(moved, ROLE_CONTENT, "dc.yml", is_dir=False)
    assert sidecar["dc:language_bcp47"] == "fr"   # archive wins


def test_to_dry_run_moves_nothing(tmp_path):
    tool = load_tool()
    root, collection, _ = build_instance(tmp_path, lang="fr", iso="fra", bcp47="fr")
    staging = collection / "staging"
    src = write_doc(staging, "welcome.md", SAMPLE)
    fr_archive = collection / "fr"
    rc = tool.main([str(src), "--to", str(fr_archive), "--dry-run"])
    assert rc == 0
    assert src.exists()                           # not moved
    assert not (fr_archive / "welcome.md").exists()


def test_to_into_new_content_directory_mints_chain(tmp_path):
    tool = load_tool()
    root, collection, _ = build_instance(tmp_path, lang="fr", iso="fra", bcp47="fr")
    staging = collection / "staging"
    src = write_doc(staging, "guide.md", SAMPLE)
    dest = collection / "fr" / "produits"         # does not exist yet
    assert tool.main([str(src), "--to", str(dest)]) == 0
    moved = dest / "guide.md"
    assert has_document_identity(moved)
    assert has_role(dest, ROLE_CONTENT, is_dir=True)  # content dir minted


# ---------------------------------------------------------------------------
# Increment 3: markdown normalization (ADR-030, pipeline step 9.5)
# ---------------------------------------------------------------------------

MESSY = (  # frontmatter + a body mdformat will reflow
    "---\ntitle: T\n---\n"
    "#   Messy Title\n\n\n* a\n*  b\n\nsome   text  \n"
)


def test_normalization_applied_by_default(tmp_path):
    tool = load_tool()
    import mdformat
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "m.md", MESSY)
    assert tool.main([str(doc)]) == 0
    # The stripped body reflowed to mdformat's canonical form.
    stripped = "#   Messy Title\n\n\n* a\n*  b\n\nsome   text  \n"
    assert doc.read_text("utf-8") == mdformat.text(stripped)


def test_normalization_off_when_cascade_disables_it(tmp_path):
    tool = load_tool()
    root, _, archive = build_instance(tmp_path)
    # Turn normalization off at the instance tier.
    write_role_yaml(root, ROLE_SAT, "dc.yml", {
        "sat:name": "instance",
        "dc:creator": "Archive Default Author",
        "dc:publisher": "Henson Shaving",
        "dc:rights": "CC BY-SA 4.0",
        "sat:normalize_markdown": False,
    }, is_dir=True)
    doc = write_doc(archive, "m.md", MESSY)
    assert tool.main([str(doc)]) == 0
    # Body is the stripped prose, untouched by mdformat.
    assert doc.read_text("utf-8") == "#   Messy Title\n\n\n* a\n*  b\n\nsome   text  \n"


def test_house_rule_violation_recorded_as_finding(tmp_path):
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "h.md",
                    "---\ntitle: T\n---\n# T\n\n```\nplain fence\n```\n")
    assert tool.main([str(doc)]) == 0
    rec = ingress_record(doc)
    kinds = [f["kind"] for f in rec["findings"]]
    assert "markdown-unlabeled-fence" in kinds


def test_shipped_floor_rule_flows_through_to_ingress_record(tmp_path):
    """A rule that lives only in the shipped-floor markdown.yml (embedded
    base64 image data, not one of ADR-030's original three) fires through the
    tool, proving the toggles are read from the floor, not hardcoded."""
    tool = load_tool()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "img.md",
                    "---\ntitle: T\n---\n"
                    "# T\n\n![x](data:image/png;base64,iVBORw0KGgo=)\n")
    assert tool.main([str(doc)]) == 0
    kinds = [f["kind"] for f in ingress_record(doc)["findings"]]
    assert "markdown-embedded-image-data" in kinds


def test_mdformat_absence_is_fatal_before_writes(tmp_path, monkeypatch):
    tool = load_tool()
    import satlib.markdown as md
    from satlib.markdown import MarkdownError

    def _boom():
        raise MarkdownError("mdformat is not available")

    monkeypatch.setattr(md, "_mdformat", _boom)
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "m.md", MESSY)
    rc = tool.main([str(doc)])
    assert rc != 0
    assert not has_document_identity(doc)     # failed before any write
    assert doc.read_text("utf-8") == MESSY    # prose untouched


# ---------------------------------------------------------------------------
# The content dispatcher routes to the tool
# ---------------------------------------------------------------------------

def test_dispatcher_routes_ingress(tmp_path):
    disp = load_dispatcher()
    _, _, archive = build_instance(tmp_path)
    doc = write_doc(archive, "sample.md", SAMPLE)
    rc = disp.main(["ingress", str(doc)])
    assert rc == 0
    assert has_document_identity(doc)


def test_dispatcher_unknown_subcommand_errors(tmp_path):
    disp = load_dispatcher()
    assert disp.main(["frobnicate"]) != 0
