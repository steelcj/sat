#!/usr/bin/env python3
#
# en/bin/transmog/transmog.py
#
# Prepares clean egress documents for a specific publication platform.
#
# Reads a transmog definition file to determine the platform and front matter
# spec, then for each document in the source directory:
#   1. Reads the .dc.yml sidecar (canonical metadata)
#   2. Generates front matter from the dc sidecar per the front matter spec
#   3. Generates .og.yml and .schema.yml sidecars if enabled in the spec
#   4. Writes the prepared document (front matter + body) to the output directory
#
# Pipeline behaviour is driven entirely by the front matter spec — no
# separate pipeline configuration is needed.
#
# Usage:
#   transmog.py --definition <path/to/transmog.yml> [options]
#
# Options:
#   --source <dir>      Override source directory from definition
#   --output <dir>      Override output directory from definition
#   --overwrite         Overwrite existing output files
#   --dry-run           Preview without writing
#   --help / -h         Show this message

import sys
import re
import yaml
from pathlib import Path


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def usage():
    print(
        "usage: transmog.py\n"
        "  --definition <path/to/transmog.yml>  Transmog definition file\n"
        "  [--source <dir>]                     Override source directory\n"
        "  [--output <dir>]                     Override output directory\n"
        "  [--overwrite]                        Overwrite existing output files\n"
        "  [--dry-run]                          Preview without writing\n"
        "  [--help | -h]                        Show this message"
    )


def error(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg):
    print(f"warn : {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        error(f"failed to read {path}: {e}")


def render_yaml(data: dict) -> str:
    return yaml.dump(
        data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )


# ---------------------------------------------------------------------------
# DC sidecar discovery
# ---------------------------------------------------------------------------

def find_dc_sidecar(doc_path: Path):
    sidecar = doc_path.parent / f".{doc_path.stem}.dc.yml"
    return sidecar if sidecar.exists() else None


# ---------------------------------------------------------------------------
# Front matter generation
# ---------------------------------------------------------------------------

# Mapping from general front matter field names to dc sidecar fields
GENERAL_TO_DC = {
    "Title":             "dc:title",
    "Description":       "dc:description",
    "Author":            "dc:creator",
    "Contributor":       "dc:contributor",
    "Publisher":         "dc:publisher",
    "Date":              "dc:date",
    "Last_Modified_Date":"dc:modified",
    "License":           "dc:rights",
    "Tags":              "dc:subject",
    "Keywords":          "dc:keywords",
    "Language":          "dc:language",
    "Identifier":        "dc:identifier",
    "Source":            "dc:source",
    "Relation":          "dc:relation",
    "Coverage":          "dc:coverage",
    "Format":            "dc:format",
    "Type":              "dc:type",
}

# Mapping from mkdocs front matter field names to dc sidecar fields
MKDOCS_TO_DC = {
    "title":       "dc:title",
    "description": "dc:description",
    "tags":        "dc:subject",
}

DC_FIELD_ORDER = [
    "dc:title", "dc:creator", "dc:contributor", "dc:publisher",
    "dc:description", "dc:subject", "dc:keywords", "dc:date", "dc:modified",
    "dc:language", "dc:type", "dc:format", "dc:identifier", "dc:source",
    "dc:relation", "dc:coverage", "dc:rights", "dc:rights.uri", "dc:rights.holder",
]

DC_REQUIRED = {
    "dc:title", "dc:creator", "dc:date", "dc:rights",
    "dc:language", "dc:identifier", "dc:format", "dc:type",
}


def check_required(dc: dict, spec: dict):
    if not spec.get("warn_on_missing", True):
        return
    for field in DC_REQUIRED:
        if field not in dc:
            warn(f"required dc field missing: {field}")


def build_general_section(dc: dict, section_spec: dict) -> dict:
    fields_spec = section_spec.get("fields", {})
    result = {}
    for field, dc_key in GENERAL_TO_DC.items():
        if fields_spec.get(field, False) and dc_key in dc:
            result[field] = dc[dc_key]
    return result


def build_dc_section(dc: dict, section_spec: dict) -> dict:
    fields_spec = section_spec.get("fields", {})
    result = {}
    for dc_key in DC_FIELD_ORDER:
        if fields_spec.get(dc_key, False) and dc_key in dc:
            result[dc_key] = dc[dc_key]
    return result


def build_mkdocs_section(dc: dict, section_spec: dict) -> dict:
    fields_spec = section_spec.get("fields", {})
    result = {}
    for field, dc_key in MKDOCS_TO_DC.items():
        if fields_spec.get(field, False) and dc_key in dc:
            result[field] = dc[dc_key]
    return result


def build_robots_section(spec: dict) -> dict:
    robots_spec = spec.get("robots", {})
    if not robots_spec.get("enabled", False):
        return {}
    return {"Robots": robots_spec.get("default", "index, follow")}


def assemble_front_matter(dc: dict, spec: dict) -> dict:
    """
    Build the complete front matter dict from dc sidecar fields,
    driven by what is enabled in the front matter spec.
    Sections are assembled in a consistent order.
    """
    fm = {}

    # Platform-specific sections first (e.g. mkdocs — tools read these)
    if spec.get("mkdocs", {}).get("enabled", False):
        fm.update(build_mkdocs_section(dc, spec["mkdocs"]))

    # General human-readable section
    if spec.get("general", {}).get("enabled", False):
        fm.update(build_general_section(dc, spec["general"]))

    # Dublin Core section
    if spec.get("dc", {}).get("enabled", False):
        fm.update(build_dc_section(dc, spec["dc"]))

    # Robots
    if spec.get("robots", {}).get("enabled", False):
        fm.update(build_robots_section(spec))

    return fm


# ---------------------------------------------------------------------------
# OG sidecar generation
# ---------------------------------------------------------------------------

LANG_TO_LOCALE = {
    "en": "en_US", "fr": "fr_FR", "de": "de_DE", "es": "es_ES",
    "it": "it_IT", "pt": "pt_PT", "nl": "nl_NL", "ja": "ja_JP",
    "zh": "zh_CN", "ko": "ko_KR", "ar": "ar_SA", "ru": "ru_RU",
}

DC_TYPE_TO_OG = {
    "Text":                "article",
    "Image":               "og:image",
    "MovingImage":         "video.other",
    "Sound":               "music.song",
    "InteractiveResource": "website",
    "Dataset":             "website",
    "PhysicalObject":      "og:product",
}


def build_og_sidecar(dc: dict) -> dict:
    og = {}
    if "dc:title"       in dc: og["og:title"]       = dc["dc:title"]
    if "dc:description" in dc: og["og:description"]  = dc["dc:description"]
    if "dc:type"        in dc: og["og:type"]         = DC_TYPE_TO_OG.get(dc["dc:type"], "website")
    if "dc:identifier"  in dc: og["og:url"]          = dc["dc:identifier"]
    if "dc:language"    in dc: og["og:locale"]       = LANG_TO_LOCALE.get(dc["dc:language"], dc["dc:language"])

    article = {}
    if "dc:date"     in dc: article["published_time"] = dc["dc:date"]
    if "dc:modified" in dc: article["modified_time"]  = dc["dc:modified"]
    if "dc:creator"  in dc: article["author"]         = dc["dc:creator"]
    if "dc:subject"  in dc: article["tag"]            = dc["dc:subject"]
    if article:
        og["og:article"] = article

    return og


# ---------------------------------------------------------------------------
# Schema.org sidecar generation
# ---------------------------------------------------------------------------

DC_TYPE_TO_SCHEMA = {
    "Text":                "Article",
    "Image":               "ImageObject",
    "MovingImage":         "VideoObject",
    "Sound":               "AudioObject",
    "InteractiveResource": "WebPage",
    "Dataset":             "Dataset",
    "PhysicalObject":      "Product",
}


def contributor_type(name: str) -> str:
    return "SoftwareApplication" if "(" in name else "Person"


def build_schema_sidecar(dc: dict) -> dict:
    schema = {
        "@context": "https://schema.org",
        "@type": DC_TYPE_TO_SCHEMA.get(dc.get("dc:type", "Text"), "Article"),
    }
    if "dc:title"       in dc: schema["headline"]      = dc["dc:title"]
    if "dc:description" in dc: schema["description"]   = dc["dc:description"]
    if "dc:creator"     in dc: schema["author"]        = {"@type": "Person", "name": dc["dc:creator"]}
    if "dc:contributor" in dc:
        name = dc["dc:contributor"]
        schema["contributor"] = {"@type": contributor_type(name), "name": name}
    if "dc:date"        in dc: schema["datePublished"] = dc["dc:date"]
    if "dc:modified"    in dc: schema["dateModified"]  = dc["dc:modified"]
    if "dc:language"    in dc: schema["inLanguage"]    = dc["dc:language"]
    if "dc:rights.uri"  in dc: schema["license"]       = dc["dc:rights.uri"]
    elif "dc:rights"    in dc: schema["license"]       = dc["dc:rights"]
    if "dc:identifier"  in dc: schema["url"]           = dc["dc:identifier"]
    if "dc:subject"     in dc: schema["keywords"]      = dc["dc:subject"]
    return schema


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def write_file(path: Path, content: str, dry_run: bool, label: str):
    if dry_run:
        print(f"[dry-run] would write {label}: {path}")
    else:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                f.write(content)
            print(f"written  : {path}")
        except Exception as e:
            warn(f"failed to write {path}: {e}")


# ---------------------------------------------------------------------------
# Per-document processing
# ---------------------------------------------------------------------------

def process_document(doc_path: Path, fm_spec: dict, output_dir: Path,
                     overwrite: bool, dry_run: bool) -> bool:
    """
    Prepare a single document for the target platform.
    Returns True if output was written (or would be in dry-run).
    """
    dc_path = find_dc_sidecar(doc_path)
    if not dc_path:
        warn(f"no .dc.yml sidecar found — skipping: {doc_path.name}")
        return False

    dc = load_yaml(dc_path)
    check_required(dc, fm_spec)

    stem     = doc_path.stem
    out_doc  = output_dir / doc_path.name

    if out_doc.exists() and not overwrite:
        print(f"skip     : {doc_path.name}  (output exists — use --overwrite)")
        return False

    # --- Build front matter ---
    fm_data = assemble_front_matter(dc, fm_spec)
    fm_block = ""
    if fm_data:
        fm_block = f"---\n{render_yaml(fm_data)}---\n\n"

    # --- Read body ---
    try:
        with doc_path.open("r", encoding="utf-8") as f:
            body = f.read()
    except Exception as e:
        warn(f"failed to read {doc_path}: {e}")
        return False

    prepared_doc = fm_block + body

    # --- Write prepared document ---
    write_file(out_doc, prepared_doc, dry_run, "document")

    # --- OG sidecar ---
    og_spec = fm_spec.get("og", {})
    if og_spec.get("enabled", False):
        og_data = build_og_sidecar(dc)
        og_path = output_dir / f".{stem}.og.yml"
        write_file(og_path, render_yaml(og_data), dry_run, "og sidecar")

    # --- Schema sidecar ---
    schema_spec = fm_spec.get("schema", {})
    if schema_spec.get("enabled", False) and schema_spec.get("output") == "sidecar":
        schema_data = build_schema_sidecar(dc)
        schema_path = output_dir / f".{stem}.schema.yml"
        write_file(schema_path, render_yaml(schema_data), dry_run, "schema sidecar")

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    definition_path  = None
    source_override  = None
    output_override  = None
    overwrite        = False
    dry_run          = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--definition":
            i += 1
            if i >= len(args): usage(); sys.exit(1)
            definition_path = Path(args[i]).resolve()
        elif arg == "--source":
            i += 1
            if i >= len(args): usage(); sys.exit(1)
            source_override = Path(args[i]).resolve()
        elif arg == "--output":
            i += 1
            if i >= len(args): usage(); sys.exit(1)
            output_override = Path(args[i]).resolve()
        elif arg == "--overwrite":
            overwrite = True
        elif arg == "--dry-run":
            dry_run = True
        elif arg in ("--help", "-h"):
            usage(); sys.exit(0)
        else:
            print(f"error: unknown argument '{arg}'", file=sys.stderr)
            usage(); sys.exit(1)
        i += 1

    if not definition_path:
        usage(); sys.exit(1)
    if not definition_path.exists():
        error(f"definition file not found: {definition_path}")

    # --- Load definition ---
    defn = load_yaml(definition_path)

    # --- Resolve front matter spec (relative to definition file) ---
    fm_spec_rel = defn.get("frontmatter_spec")
    if not fm_spec_rel:
        error("definition is missing 'frontmatter_spec'")
    fm_spec_path = (definition_path.parent / fm_spec_rel).resolve()
    if not fm_spec_path.exists():
        error(f"front matter spec not found: {fm_spec_path}")

    fm_spec = load_yaml(fm_spec_path)

    # --- Resolve source and output directories ---
    source_dir = source_override or (Path(defn.get("source", "")).resolve() if defn.get("source") else None)
    output_dir = output_override or (Path(defn.get("output", "")).resolve() if defn.get("output") else None)

    if not source_dir:
        error("source directory not set — use --source or set 'source' in the definition file")
    if not output_dir:
        error("output directory not set — use --output or set 'output' in the definition file")
    if not source_dir.exists():
        error(f"source directory not found: {source_dir}")

    print(f"definition : {definition_path}")
    print(f"platform   : {defn.get('platform', '(unset)')}")
    print(f"fm spec    : {fm_spec_path}")
    print(f"source     : {source_dir}")
    print(f"output     : {output_dir}")
    print()

    # --- Collect source documents ---
    targets = sorted(source_dir.glob("*.md"))
    if not targets:
        error(f"no .md files found in source directory: {source_dir}")

    print(f"found      : {len(targets)} document(s)")
    print()

    # --- Process ---
    written = 0
    skipped = 0

    for doc in targets:
        result = process_document(doc, fm_spec, output_dir, overwrite, dry_run)
        if result:
            written += 1
        else:
            skipped += 1

    print()
    if dry_run:
        print(f"[dry-run] would prepare {written} document(s), skip {skipped}")
        print("[dry-run] no filesystem changes were made")
    else:
        print(f"done       : {written} document(s) prepared, {skipped} skipped")


if __name__ == "__main__":
    main()
