#
# source
#   project: sat
#   path: en/lib/satlib/satlib/cataloging.py
#
"""satlib.cataloging — metadata cataloging at content ingress (ADR-023).

The step of ingress that reads a document's frontmatter, applies the
normative cataloging policy against the resolved cascade, and produces the
descriptive record, its per-field origins, the noted residue, and any
findings. `content ingress` is a thin caller: this module reads and strips
frontmatter and decides what each field's value and origin are; the tool
writes the sidecar, the prose, and the ingress record.

The vocabulary is the cataloguer's, not invented here (ADR-023): a value is
*transcribed* when taken from the item itself (frontmatter), *supplied* when
provided by the archive's intent (the cascade), by tooling, or by the
operator, and *noted* when recorded only in the ingress record and never
admitted to the sidecar. Transcribed values are never modified; an overridden
or refused claim still survives verbatim in the noted residue the tool writes.

This module is pure: it touches no filesystem and no clock. The operator or
tool computes the supplied date (the fallback order is settled in the
content-ingress implementation plan: transcribed, then operator `--date`,
then filesystem birth time where the platform exposes it, then the current
UTC time recorded as noted) and passes it in as `supplied_date`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import yaml

__all__ = [
    "CatalogResult",
    "Finding",
    "FrontmatterError",
    "read_frontmatter",
    "apply_cataloging_policy",
]


# ---------------------------------------------------------------------------
# Recognized frontmatter keys and their canonical Dublin Core fields
# ---------------------------------------------------------------------------

# Frontmatter keys that transcribe to a descriptive field. Plain author-
# facing aliases and the explicit dc: forms both resolve to one canonical
# field name (the worked example in ADR-023 uses the plain forms).
_TRANSCRIBABLE = {
    "title": "dc:title", "dc:title": "dc:title",
    "author": "dc:creator", "creator": "dc:creator", "dc:creator": "dc:creator",
    "contributor": "dc:contributor", "dc:contributor": "dc:contributor",
    "subject": "dc:subject", "dc:subject": "dc:subject",
    "description": "dc:description", "dc:description": "dc:description",
    "date": "dc:date", "dc:date": "dc:date",
    "publisher": "dc:publisher", "dc:publisher": "dc:publisher",
    "rights": "dc:rights", "dc:rights": "dc:rights",
}

# Language keys are read for the disagreement check, never accepted into the
# sidecar: the filesystem is the language declaration (ADR-001).
_LANGUAGE_KEYS = ("language", "lang", "dc:language", "dc:language_bcp47")

# Identity residue is noted verbatim as possible join evidence (ADR-022),
# never admitted to the sidecar.
_IDENTITY_RESIDUE = (
    "dc:identifier", "identifier",
    "sat_uuid", "sat:uuid", "sat:work",
    "translationKey", "translationkey",
)

# Cascade-owned fields where a transcribed claim is accepted as a deliberate,
# narrated exception rather than silently winning or being dropped.
_EXCEPTION_FIELDS = ("dc:publisher", "dc:rights")

# The canonical emission order for the descriptive sidecar and the origins
# map. Deterministic output; matches the ADR-023 worked example.
_FIELD_ORDER = (
    "dc:title",
    "dc:creator",
    "dc:contributor",
    "dc:subject",
    "dc:description",
    "dc:date",
    "dc:publisher",
    "dc:rights",
    "dc:language",
    "dc:language_bcp47",
    "dc:type",
    "dc:format",
)


# ---------------------------------------------------------------------------
# Data carriers
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """One cataloging finding, in the ADR-024 grammar.

    The same grammar the language-disagreement finding and the markdown
    house-rule findings (ADR-030) use, so the ingress record speaks one
    dialect throughout.
    """

    kind: str                                  # language-disagreement | transcribed-exception
    what: str
    means: str
    evidence: dict = field(default_factory=dict)
    do: str = ""
    severity: str = "soft"                     # "hard" | "soft"


@dataclass
class CatalogResult:
    """The outcome of applying the cataloging policy to one document.

    `sidecar` is the policy-applied descriptive record the tool writes to
    content/dc.yml. `origins` records each admitted field's origin for the
    ingress record. `noted` carries identity residue and unrecognized keys,
    which never enter the sidecar. `findings` are non-fatal observations in
    the ADR-024 grammar.
    """

    sidecar: dict = field(default_factory=dict)
    origins: dict = field(default_factory=dict)
    noted: dict = field(default_factory=dict)
    findings: list = field(default_factory=list)


class FrontmatterError(ValueError):
    """Frontmatter was present but could not be parsed as a YAML mapping."""


# ---------------------------------------------------------------------------
# Frontmatter reading and stripping (spec section 5)
# ---------------------------------------------------------------------------

# A leading YAML frontmatter block: --- on its own line, the block, then a
# closing --- on its own line. Only the leading block is matched; horizontal
# rules later in the prose are left untouched.
_FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(?:(?P<block>.*?)\r?\n)?---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)


def read_frontmatter(text: str) -> tuple[Optional[dict], str, str]:
    """Split a document into (frontmatter, body, raw_block).

    Returns the parsed frontmatter mapping (or None when the document has no
    leading block), the prose with the block removed, and the raw inner block
    text for the ingress record. A present-but-malformed block, or one that
    is not a mapping, raises FrontmatterError: content ingress does not guess
    at broken frontmatter.
    """
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return None, text, ""

    raw = match.group("block") or ""
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"frontmatter is not valid YAML: {exc}") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise FrontmatterError(
            "frontmatter must be a YAML mapping, "
            f"found {type(data).__name__}"
        )

    body = text[match.end():]
    return data, body, raw


# ---------------------------------------------------------------------------
# The cataloging policy (spec section 7 / ADR-023, normative)
# ---------------------------------------------------------------------------

def _as_list(value) -> list:
    """Coerce a scalar or None into a list; pass a list through."""
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    return [value]


def _primary_subtag(code: str) -> str:
    return str(code).split("-", 1)[0].strip().lower()


def _language_agrees(claim, bcp47, iso) -> bool:
    """True when a frontmatter language claim agrees with the archive.

    Agreement is exact against either the archive's bcp47 or iso code, or on
    the primary subtag (so en-CA agrees with an en archive).
    """
    c = str(claim).strip().lower()
    candidates = {str(x).strip().lower() for x in (bcp47, iso) if x}
    if c in candidates:
        return True
    primaries = {_primary_subtag(x) for x in (bcp47, iso) if x}
    return _primary_subtag(c) in primaries


def apply_cataloging_policy(
    frontmatter: Optional[dict],
    preseed: dict,
    *,
    archive_language: str,
    supplied_date: Optional[str] = None,
) -> CatalogResult:
    """Apply the normative cataloging policy to one document.

    `frontmatter` is the transcribed-claims source (None or empty means the
    document offered nothing to transcribe). `preseed` is the resolved
    cascade record from resolve_entity, the supplied side of every field.
    `archive_language` is the archive's bcp47 declaration, used for the
    disagreement message when the cascade does not carry its own. Returns a
    CatalogResult; writing is the caller's job.
    """
    fm = frontmatter or {}

    # Partition frontmatter into transcribed claims, a language claim,
    # identity residue, and unrecognized keys, preserving encounter order.
    transcribed: dict = {}
    language_claim = None
    noted: dict = {}
    unrecognized: dict = {}
    for key, value in fm.items():
        if key in _TRANSCRIBABLE:
            transcribed.setdefault(_TRANSCRIBABLE[key], value)
        elif key in _LANGUAGE_KEYS:
            if language_claim is None:
                language_claim = value
        elif key in _IDENTITY_RESIDUE:
            noted[key] = value
        else:
            unrecognized[key] = value
    if unrecognized:
        noted["unrecognized_keys"] = unrecognized

    result = CatalogResult(noted=noted)
    sidecar = result.sidecar
    origins = result.origins
    findings = result.findings

    # dc:title — transcribed only; the cascade never supplies a title.
    if "dc:title" in transcribed:
        sidecar["dc:title"] = transcribed["dc:title"]
        origins["dc:title"] = "transcribed"

    # dc:creator — transcribed wins; absent falls back to supplied.
    if "dc:creator" in transcribed:
        sidecar["dc:creator"] = transcribed["dc:creator"]
        origins["dc:creator"] = "transcribed"
    elif "dc:creator" in preseed:
        sidecar["dc:creator"] = preseed["dc:creator"]
        origins["dc:creator"] = "supplied"

    # dc:contributor — transcribed only; omitted entirely when absent.
    if "dc:contributor" in transcribed:
        sidecar["dc:contributor"] = transcribed["dc:contributor"]
        origins["dc:contributor"] = "transcribed"

    # dc:subject — union: transcribed first, then supplied, deduped, ordered.
    t_subject = _as_list(transcribed.get("dc:subject"))
    s_subject = _as_list(preseed.get("dc:subject"))
    if t_subject or s_subject:
        union: list = []
        for item in t_subject + s_subject:
            if item not in union:
                union.append(item)
        sidecar["dc:subject"] = union
        subject_origin: list = []
        if t_subject:
            subject_origin.append("transcribed")
        if s_subject:
            subject_origin.append("supplied")
        origins["dc:subject"] = subject_origin

    # dc:description — transcribed wins; absent is "", never <calculated>.
    if "dc:description" in transcribed:
        sidecar["dc:description"] = transcribed["dc:description"]
        origins["dc:description"] = "transcribed"
    else:
        sidecar["dc:description"] = ""
        origins["dc:description"] = "supplied"

    # dc:date — transcribed wins; else the supplied fallback (plan Decision 1).
    if "dc:date" in transcribed:
        sidecar["dc:date"] = transcribed["dc:date"]
        origins["dc:date"] = "transcribed"
    elif supplied_date is not None:
        sidecar["dc:date"] = supplied_date
        origins["dc:date"] = "supplied"

    # dc:publisher, dc:rights — cascade-owned; transcribed is a narrated
    # exception recorded as a finding, otherwise supplied.
    for cascade_field in _EXCEPTION_FIELDS:
        if cascade_field in transcribed:
            sidecar[cascade_field] = transcribed[cascade_field]
            origins[cascade_field] = "transcribed"
            findings.append(Finding(
                kind="transcribed-exception",
                what=f"{cascade_field} taken from frontmatter, not the cascade",
                means=(
                    "a cascade-owned field was overridden by a transcribed "
                    "claim; recorded as a deliberate, narrated exception"
                ),
                evidence={"field": cascade_field, "value": transcribed[cascade_field]},
                do="confirm the override is intended for this document",
                severity="soft",
            ))
        elif cascade_field in preseed:
            sidecar[cascade_field] = preseed[cascade_field]
            origins[cascade_field] = "supplied"

    # dc:language, dc:language_bcp47 — supplied always wins; a disagreeing
    # claim is a finding, never a choice.
    archive_iso = preseed.get("dc:language")
    archive_bcp47 = preseed.get("dc:language_bcp47") or archive_language
    if archive_iso is not None:
        sidecar["dc:language"] = archive_iso
        origins["dc:language"] = "supplied"
    if archive_bcp47 is not None:
        sidecar["dc:language_bcp47"] = archive_bcp47
        origins["dc:language_bcp47"] = "supplied"
    if language_claim is not None and not _language_agrees(
            language_claim, archive_bcp47, archive_iso):
        findings.append(Finding(
            kind="language-disagreement",
            what=f"{language_claim} claimed in frontmatter; archive is {archive_bcp47}",
            means=(
                "the document is either misfiled or mislabeled; the filesystem "
                "is the language declaration (ADR-001), so the archive wins"
            ),
            evidence={"claimed": language_claim, "archive": archive_bcp47},
            do=(
                f"if misfiled, move it to {language_claim}/ and re-catalog; "
                "the claim is preserved verbatim in the ingress record"
            ),
            severity="soft",
        ))

    # dc:type, dc:format — supplied by tooling inspecting the file, never by
    # claim. Carried through from the preseed here; the tool may refine them.
    for tooling_field in ("dc:type", "dc:format"):
        if tooling_field in preseed:
            sidecar[tooling_field] = preseed[tooling_field]
            origins[tooling_field] = "supplied"

    # Re-emit the sidecar and origins in canonical field order for
    # deterministic, spec-matching output.
    result.sidecar = {k: sidecar[k] for k in _FIELD_ORDER if k in sidecar}
    result.origins = {k: origins[k] for k in _FIELD_ORDER if k in origins}
    return result
