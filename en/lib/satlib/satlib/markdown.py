#
# source
#   project: sat
#   path: en/lib/satlib/satlib/markdown.py
#
"""satlib.markdown — markdown normalization and house-rule checks (ADR-030).

Pipeline step 9.5 of content ingress: after the frontmatter is stripped and
before fixity, a document's prose is normalized to mdformat's canonical form
and checked against the SAT markdown house rules. Normalizing before fixity
means the digest attests the document's true final state.

Three surfaces:

- `normalize(text)` runs mdformat. mdformat is the one external dependency
  ADR-030 introduces; its absence is fatal (never silently skipped), and
  `ensure_available()` lets a caller fail fast before doing any writes.
- `check_house_rules(text, rules=None)` is pure stdlib `re` and implements
  the six toggles SAT ships an opinion about (ADR-030 plus the two later
  additions): no horizontal rules in content, fenced blocks carry a
  language, no heading-level skips, no hard line wraps, no embedded base64
  image data, and whether inline `<svg>` is allowed. Findings use the
  ADR-024 grammar (shared with satlib.cataloging), non-fatal by design:
  prose quality wants author attention, not a refused ingress. The same
  function is intended to back `sat validate`'s markdown check when that
  tool is rebuilt, so the rule is defined once and enforced twice.
- `load_rules(path)` reads the shipped-floor `markdown.yml` (ADR-032:
  `en/bin/sat/defaults/content/markdown.yml`) and merges its toggles over
  the built-in defaults. The caller supplies the path, since satlib does
  not hard-code the repository layout. Full per-tier operator override — the
  cascaded `.assets/<role>/markdown.yml`, deepest-stated-value wins — is
  ADR-032's own resolver work and is not implemented here; this reads the
  floor.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .cataloging import Finding

__all__ = [
    "MarkdownError",
    "normalize",
    "ensure_available",
    "check_house_rules",
    "load_rules",
    "DEFAULT_RULES",
]

# The toggles SAT ships an opinion about (matches
# en/bin/sat/defaults/content/markdown.yml). inline_svg_allowed is a
# permission, not a prohibition: True means inline <svg> is fine.
DEFAULT_RULES = {
    "no_horizontal_rules": True,
    "fenced_blocks_require_language": True,
    "no_heading_level_skips": True,
    "no_hard_line_wraps": True,
    "no_embedded_image_data": True,
    "inline_svg_allowed": True,
}


class MarkdownError(RuntimeError):
    """mdformat is required but unavailable."""


# ---------------------------------------------------------------------------
# Normalization (mdformat)
# ---------------------------------------------------------------------------

def _mdformat():
    """Return the mdformat module, or raise MarkdownError with an install
    command. Isolated so callers (and tests) have one place to intercept."""
    try:
        import mdformat
    except ImportError as exc:  # pragma: no cover - exercised via monkeypatch
        raise MarkdownError(
            "mdformat is not available; content ingress cannot normalize "
            "markdown. Install it with: pip install mdformat"
        ) from exc
    return mdformat


def ensure_available() -> None:
    """Raise MarkdownError now if mdformat is unavailable, so a caller can
    fail before performing any writes."""
    _mdformat()


def normalize(text: str) -> str:
    """Return the mdformat canonical form of the prose body."""
    return _mdformat().text(text)


# ---------------------------------------------------------------------------
# Shipped-floor config (ADR-032)
# ---------------------------------------------------------------------------

def load_rules(path) -> dict:
    """Load house-rule toggles from a shipped-floor markdown.yml.

    The file's toggles are merged over the built-in defaults; only recognized
    keys are honored. A missing or unreadable file yields the built-in
    defaults, so an install without the floor still applies SAT's opinion.
    """
    rules = dict(DEFAULT_RULES)
    p = Path(path)
    if p.is_file():
        data = yaml.safe_load(p.read_text("utf-8")) or {}
        if isinstance(data, dict):
            for key, value in data.items():
                if key in DEFAULT_RULES:
                    rules[key] = value
    return rules


# ---------------------------------------------------------------------------
# House-rule checks (pure stdlib)
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^(?P<indent>\s*)(?P<ticks>`{3,}|~{3,})(?P<info>.*)$")
_RULE_RE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
_LIST_RE = re.compile(r"^\s*([-*+]\s+|\d+[.)]\s+)")
_BLOCKQUOTE_RE = re.compile(r"^\s*>")
_TABLE_RE = re.compile(r"^\s*\|")
_INDENTED_CODE_RE = re.compile(r"^ {4,}\S")
_DATA_URI_RE = re.compile(r"data:[^;\s]+;base64,", re.IGNORECASE)
_SVG_RE = re.compile(r"<svg[\s>]", re.IGNORECASE)


def _finding(kind: str, what: str, means: str, line: int) -> Finding:
    return Finding(
        kind=kind,
        what=what,
        means=means,
        evidence={"line": line},
        do="normalize the prose to well-formed SAT markdown, or leave as a "
           "recorded finding for author attention",
        severity="soft",
    )


def _is_blockish(line: str) -> bool:
    """A non-prose block line (list item, blockquote, table row, indented
    code). Such lines break a prose paragraph and are not counted as part of
    a hard-wrapped run."""
    return bool(
        _LIST_RE.match(line)
        or _BLOCKQUOTE_RE.match(line)
        or _TABLE_RE.match(line)
        or _INDENTED_CODE_RE.match(line)
    )


def check_house_rules(text: str, rules=None) -> list:
    """Return the SAT markdown house-rule findings for a prose body.

    Fenced code blocks are tracked so no rule fires on their contents. The
    caller passes already-stripped prose; there is no frontmatter to consider.
    Pass `rules` (for example from `load_rules`) to honor a shipped-floor or
    operator override; absent that, the built-in defaults apply.
    """
    active = dict(DEFAULT_RULES)
    if rules:
        active.update(rules)

    findings: list = []
    in_fence = False
    fence_marker = ""
    previous_heading_level = None
    para_run = 0
    para_start = 0

    def flush_paragraph():
        nonlocal para_run, para_start
        if active["no_hard_line_wraps"] and para_run >= 2:
            findings.append(_finding(
                "markdown-hard-line-wrap",
                "a paragraph is hard-wrapped across multiple source lines",
                "prose should flow on one line per paragraph; mdformat "
                "preserves manual line breaks rather than reflowing them",
                para_start,
            ))
        para_run = 0
        para_start = 0

    for number, line in enumerate(text.splitlines(), start=1):
        fence = _FENCE_RE.match(line)
        if fence:
            flush_paragraph()
            ticks = fence.group("ticks")
            info = fence.group("info").strip()
            if not in_fence:
                in_fence = True
                fence_marker = ticks[0] * 3
                if active["fenced_blocks_require_language"] and not info:
                    findings.append(_finding(
                        "markdown-unlabeled-fence",
                        "a fenced code block opens without a language identifier",
                        "unlabeled fences lose syntax highlighting and machine "
                        "readability; every fence should name its language",
                        number,
                    ))
            elif ticks[0] * 3 == fence_marker and not info:
                in_fence = False
                fence_marker = ""
            continue

        if in_fence:
            continue

        if not line.strip():
            flush_paragraph()
            continue

        if _RULE_RE.match(line):
            flush_paragraph()
            if active["no_horizontal_rules"]:
                findings.append(_finding(
                    "markdown-horizontal-rule",
                    "a horizontal rule appears in content",
                    "horizontal rules are presentational and not used in "
                    "well-formed SAT markdown content",
                    number,
                ))
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            if (active["no_heading_level_skips"]
                    and previous_heading_level is not None
                    and level > previous_heading_level + 1):
                findings.append(_finding(
                    "markdown-heading-skip",
                    f"heading level jumps from H{previous_heading_level} "
                    f"to H{level}",
                    "skipping a heading level breaks the document outline; "
                    "headings should descend one level at a time",
                    number,
                ))
            previous_heading_level = level
            continue

        # Inline content rules apply to any non-code line.
        if active["no_embedded_image_data"] and _DATA_URI_RE.search(line):
            findings.append(_finding(
                "markdown-embedded-image-data",
                "a base64 data URI is embedded in the content",
                "embedded base64 bloats the source, breaks diffs, and is "
                "filesystem-invisible; reference a file instead",
                number,
            ))
        if not active.get("inline_svg_allowed", True) and _SVG_RE.search(line):
            findings.append(_finding(
                "markdown-inline-svg",
                "inline <svg> markup appears in content",
                "inline SVG is disallowed by this archive's markdown policy",
                number,
            ))

        if _is_blockish(line):
            flush_paragraph()
            continue

        # A plain prose line: extend the current paragraph run.
        if para_run == 0:
            para_start = number
        para_run += 1

    flush_paragraph()
    return findings
