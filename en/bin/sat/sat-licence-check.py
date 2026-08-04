#!/usr/bin/env python3
#
# source
#   project: sat
#   path: en/bin/sat/sat-licence-check.py
#
"""sat licence check [path] — audit SPDX licence identifiers (ADR-033).

A read-only auditor. It walks a tree, finds every declared SPDX licence
identifier, and validates each against the SPDX License List (cached the
same way `sat init` caches the IANA registry, ADR-003). It never writes:
correcting an identifier is a separate, deliberate act (the future
`licence-apply` tool), the same way `satlib.language` surfaces a casing
finding rather than silently normalising it.

What it reads (the canonical marker plus one named exception):

    SPDX-License-Identifier: <expr>   anywhere — a `dc:rights` /
                                      `dcterms:rights` folded scalar, a
                                      source-file header, a LICENSE
                                      preamble
    sat.yml   the bare `sat.license` field (ADR-033 names it directly)

What it reports, per the SPDX data:

    hard   an identifier that is not a current SPDX identifier, or a
           malformed AND/OR/WITH expression — the audit fails
    soft   a deprecated identifier, or one not in SPDX canonical
           casing — reported as a warning; `--strict` makes it fail

    sat licence check [path]            audit a tree (default: the repo)
    sat licence check --offline-confirm proceed on a stale/absent cache
    sat licence check --strict          treat soft findings as failures
    sat licence check --version
"""

import argparse
import sys
from pathlib import Path

from satlib import CacheUnavailableError, RegistryCache
from satlib.spdx import (
    ExceptionList,
    LicenseList,
    extract_spdx_tags,
    spdx_exceptions_source,
    spdx_licenses_source,
    validate_expression,
)

CONFIG_DIR = Path.home() / ".config" / "sat"
LICENSES_CACHE = CONFIG_DIR / "cache" / "spdx-licenses.json"
EXCEPTIONS_CACHE = CONFIG_DIR / "cache" / "spdx-exceptions.json"

# Directories that are never content: version control, virtualenvs, and
# tool caches. Pruned before descent, not filtered after.
SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
}

# Suffixes worth reading for a licence tag. A binary asset carries no
# SPDX declaration; reading it would only risk a decode error.
TEXT_SUFFIXES = {
    ".md", ".py", ".yml", ".yaml", ".toml", ".txt", ".cfg", ".ini",
    ".sh", ".rst", ".json",
}

# Extension-less files that conventionally carry a licence declaration.
TEXT_NAMES = {"LICENSE", "LICENCE", "COPYING", "NOTICE"}


def sat_root() -> Path:
    """en/bin/sat/sat-licence-check.py -> three parents above en/."""
    return Path(__file__).resolve().parent.parent.parent.parent


def tool_version() -> str:
    try:
        return (sat_root() / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "unknown"


# ---------------------------------------------------------------------------
# Authority resolution (the SPDX License List, cached like the IANA registry)
# ---------------------------------------------------------------------------

def resolve_lists(offline_confirmed: bool):
    """Resolve the licence list (required) and exception list (optional).

    The licence list is the authority; without it there is nothing to
    validate against, and the tool refuses rather than pass everything.
    The exception list only sharpens `WITH` operands, so an absent one
    degrades to structural acceptance of exceptions, not a refusal.
    """
    cache = RegistryCache(spdx_licenses_source(LICENSES_CACHE))
    try:
        result = cache.resolve(offline_confirmed=offline_confirmed)
    except CacheUnavailableError as exc:
        print(f"[SAT ERROR] {exc}", file=sys.stderr)
        print("  Pass --offline-confirm to proceed, or restore network "
              "access to seed the SPDX cache.", file=sys.stderr)
        sys.exit(1)
    for warning in result.warnings:
        print(f"[SAT WARNING] {warning}", file=sys.stderr)
    if result.content is None:
        print("[SAT ERROR] The SPDX Licence List is unavailable and no cache "
              "exists; there is nothing to validate against.", file=sys.stderr)
        sys.exit(1)
    licenses = LicenseList.parse(result.content)
    print(f"spdx:      {result.status.value} "
          f"(licenseListVersion: {licenses.list_version})")

    exceptions = None
    ex_cache = RegistryCache(spdx_exceptions_source(EXCEPTIONS_CACHE))
    try:
        ex_result = ex_cache.resolve(offline_confirmed=True)
    except CacheUnavailableError:
        ex_result = None
    if ex_result is not None and ex_result.content is not None:
        exceptions = ExceptionList.parse(ex_result.content)
    return licenses, exceptions


# ---------------------------------------------------------------------------
# Walking and reading
# ---------------------------------------------------------------------------

def iter_text_files(root: Path):
    """Yield readable files under root, pruning version control and caches."""
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name)
        except (PermissionError, NotADirectoryError):
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name not in SKIP_DIRS:
                    stack.append(entry)
                continue
            if entry.suffix in TEXT_SUFFIXES or entry.name in TEXT_NAMES:
                yield entry


def candidates_in(path: Path) -> list[tuple[int, str, str]]:
    """Every (line, source, expression) licence candidate in one file.

    `source` labels where the expression came from — the SPDX tag, or the
    bare `sat.license` field this tool is asked to police by name.
    """
    try:
        text = path.read_text("utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    found = [(line, "SPDX-License-Identifier", expr)
             for line, expr in extract_spdx_tags(text)]

    if path.name == "sat.yml":
        found.extend(_sat_yml_license(text))

    return found


def _sat_yml_license(text: str) -> list[tuple[int, str, str]]:
    """The bare `sat.license` field of a sat.yml, if present.

    Read leniently: a licence audit must not fall over on a malformed
    settings file, and the field is a plain scalar in practice.
    """
    import yaml
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return []
    value = ((data or {}).get("sat") or {}).get("license") \
        if isinstance(data, dict) else None
    if not isinstance(value, str) or not value.strip():
        return []
    line = 0
    for index, raw in enumerate(text.splitlines(), start=1):
        if "license:" in raw:
            line = index
            break
    return [(line, "sat.license", value.strip())]


# ---------------------------------------------------------------------------
# Grading one candidate against the SPDX data
# ---------------------------------------------------------------------------

def grade(expression: str, licenses, exceptions):
    """Return (severity, messages) for one licence expression.

    hard  a not-current identifier or a malformed expression — an
          identifier SAT cannot vouch for
    soft  a deprecated or mis-cased identifier — real, but not what SAT
          would write today
    None  clean
    """
    validation = validate_expression(expression, licenses, exceptions)
    structural = bool(validation.errors)
    unknown = any(not c.registered for c in validation.components)
    miscased = any(not c.casing_valid for c in validation.components)

    if structural or unknown:
        return "hard", _messages(validation)
    if validation.deprecated or miscased:
        return "soft", _messages(validation)
    return None, []


def _messages(validation) -> list[str]:
    out = list(validation.errors)
    for component in validation.components:
        out.extend(component.errors)
    return out


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------

def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        print(f"[SAT ERROR] {root}: no such path", file=sys.stderr)
        return 1

    licenses, exceptions = resolve_lists(args.offline_confirm)

    hard = soft = clean = 0
    for path in iter_text_files(root):
        for line, source, expression in candidates_in(path):
            severity, messages = grade(expression, licenses, exceptions)
            if severity is None:
                clean += 1
                continue
            if severity == "hard":
                hard += 1
            else:
                soft += 1
            rel = path.relative_to(root) if path.is_relative_to(root) else path
            label = "FINDING" if severity == "hard" else "WARNING"
            where = f"{rel}:{line}" if line else str(rel)
            print(f"[{label}] {where} ({source}): {expression}")
            for message in messages:
                print(f"    {message}")

    print(f"\nchecked: {clean + hard + soft} identifier(s) "
          f"in {root.name}/ — {clean} clean, {soft} warning(s), "
          f"{hard} finding(s)")

    if hard:
        return 1
    if soft and args.strict:
        print("[SAT] --strict: soft findings treated as failures.")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sat licence check",
        description="Audit SPDX licence identifiers against the SPDX "
                    "Licence List (read-only).",
    )
    parser.add_argument(
        "path", nargs="?", default=str(sat_root()),
        help="tree to audit (default: the SAT repository root)")
    parser.add_argument(
        "--offline-confirm", action="store_true",
        help="proceed when the SPDX cache is stale or absent and the "
             "source is unreachable")
    parser.add_argument(
        "--strict", action="store_true",
        help="treat deprecated/mis-cased identifiers as failures too")
    parser.add_argument(
        "--version", action="version",
        version=f"sat licence check {tool_version()}")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
