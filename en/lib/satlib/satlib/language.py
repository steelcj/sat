"""satlib.language — BCP 47 validation and standard derivation.

Implements sections 1.1, 3, and 4 of the SAT Language Validation and
Offline Registry Cache Specification (v0.1.0) on top of the generic
cache machinery in satlib.registry:

- record-jar parsing of the IANA Language Subtag Registry (ADR-003)
- the BCP 47 pattern test for single and mixed archive directory
  names (ADR-001, ADR-002)
- canonical casing enforcement (ADR-003 section 8.2)
- derivation of dc:language (ISO 639-2) and dc:language_bcp47
- sat:authority declaration (spec section 3.3)
- the non-authority model for unregistered expressions (section 4)

Known limitation, deliberate for MVP: a three-letter primary subtag
without a Macrolanguage record is passed through as its own
dc:language value. ISO 639-3 codes that have no ISO 639-2 equivalent
are therefore emitted as-is rather than detected; detecting them
would require embedding the full ISO 639-2 membership set. Flagged in
tests as the documented behaviour.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .iso639 import iso639_2t_for_part1
from .registry import CachedSource

__all__ = [
    "IANA_REGISTRY_URL",
    "iana_source",
    "extract_file_date",
    "SubtagRegistry",
    "SubtagRecord",
    "TagValidation",
    "ComponentValidation",
    "validate_expression",
    "non_authority_expression",
    "DEFAULT_AUTHORITY_NOTE",
]

IANA_REGISTRY_URL = "https://www.iana.org/assignments/language-subtag-registry"

_FILE_DATE_RE = re.compile(r"^File-Date:\s*(\S+)", re.MULTILINE)

DEFAULT_AUTHORITY_NOTE = (
    "No entry found in the IANA Language Subtag Registry for this "
    "expression. This archive exists on the community's terms. SAT "
    "makes no claim of linguistic or institutional authority. "
    "Registry cache consulted: {cache_date}."
)


def extract_file_date(content: bytes) -> Optional[str]:
    """The File-Date header of the IANA registry, or None."""
    match = _FILE_DATE_RE.search(content.decode("utf-8", errors="replace"))
    return match.group(1) if match else None


def iana_source(cache_path: Path, staleness_days: int = 30,
                source_url: str = IANA_REGISTRY_URL) -> CachedSource:
    """CachedSource descriptor for the IANA Language Subtag Registry."""
    return CachedSource(
        name="iana-language-subtag-registry",
        source_url=source_url,
        cache_path=cache_path,
        staleness_days=staleness_days,
        file_date_extractor=extract_file_date,
    )


# ---------------------------------------------------------------------------
# Registry parsing (record-jar format)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SubtagRecord:
    """One registry record, keyed by (type, subtag-or-tag)."""

    type: str
    subtag: str
    descriptions: tuple[str, ...] = ()
    deprecated: Optional[str] = None
    preferred_value: Optional[str] = None
    macrolanguage: Optional[str] = None
    prefixes: tuple[str, ...] = ()


class SubtagRegistry:
    """Parsed IANA Language Subtag Registry with typed lookup."""

    def __init__(self, records: dict[tuple[str, str], SubtagRecord],
                 file_date: Optional[str]):
        self._records = records
        self.file_date = file_date

    @classmethod
    def parse(cls, content: bytes) -> "SubtagRegistry":
        text = content.decode("utf-8", errors="replace")
        file_date = extract_file_date(content)
        records: dict[tuple[str, str], SubtagRecord] = {}

        for chunk in text.split("\n%%\n"):
            fields: dict[str, list[str]] = {}
            current: Optional[str] = None
            for line in chunk.splitlines():
                if line.startswith("  ") and current is not None:
                    fields[current][-1] += " " + line.strip()
                    continue
                name, sep, value = line.partition(":")
                if not sep:
                    continue
                current = name.strip()
                fields.setdefault(current, []).append(value.strip())

            record_type = fields.get("Type", [None])[0]
            key_value = fields.get("Subtag", fields.get("Tag", [None]))[0]
            if record_type is None or key_value is None:
                continue  # the File-Date preamble and malformed chunks

            record = SubtagRecord(
                type=record_type,
                subtag=key_value,
                descriptions=tuple(fields.get("Description", ())),
                deprecated=fields.get("Deprecated", [None])[0],
                preferred_value=fields.get("Preferred-Value", [None])[0],
                macrolanguage=fields.get("Macrolanguage", [None])[0],
                prefixes=tuple(fields.get("Prefix", ())),
            )
            records[(record_type, key_value.lower())] = record

        return cls(records, file_date)

    def lookup(self, record_type: str, subtag: str) -> Optional[SubtagRecord]:
        return self._records.get((record_type, subtag.lower()))


# ---------------------------------------------------------------------------
# Canonical casing (ADR-003 section 8.2)
# ---------------------------------------------------------------------------

def _canonical_case(role: str, subtag: str) -> str:
    if role == "script":
        return subtag[:1].upper() + subtag[1:].lower()
    if role == "region":
        return subtag.upper()
    # primary language, extlang, and variant subtags are lowercase
    return subtag.lower()


# ---------------------------------------------------------------------------
# Structural parse of a single BCP 47 tag
# ---------------------------------------------------------------------------

_ALPHA = re.compile(r"^[A-Za-z]+$")
_DIGIT = re.compile(r"^[0-9]+$")
_ALNUM = re.compile(r"^[A-Za-z0-9]+$")


@dataclass
class _Parsed:
    primary: Optional[str] = None
    script: Optional[str] = None
    region: Optional[str] = None
    variants: list[str] = field(default_factory=list)
    private: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _parse_single_tag(tag: str) -> _Parsed:
    """Structural decomposition: language [-script] [-region] *(-variant) [-x-...].

    Extension singletons other than x are out of scope for archive
    directory names and are rejected explicitly.
    """
    parsed = _Parsed()
    subtags = tag.split("-")
    index = 0

    if subtags and subtags[0].lower() == "x":
        # Whole-tag private use: x-...
        parsed.private = subtags[1:]
        if not parsed.private:
            parsed.errors.append(f"{tag}: private use tag has no subtags")
        for sub in parsed.private:
            if not _ALNUM.match(sub) or not (1 <= len(sub) <= 8):
                parsed.errors.append(f"{tag}: invalid private use subtag {sub!r}")
        return parsed

    first = subtags[0] if subtags else ""
    if _ALPHA.match(first) and 2 <= len(first) <= 3:
        parsed.primary = first
        index = 1
    else:
        parsed.errors.append(f"{tag}: no valid primary language subtag")
        return parsed

    remaining = subtags[index:]
    position = 0

    if position < len(remaining):
        sub = remaining[position]
        if _ALPHA.match(sub) and len(sub) == 4:
            parsed.script = sub
            position += 1

    if position < len(remaining):
        sub = remaining[position]
        if (_ALPHA.match(sub) and len(sub) == 2) or (_DIGIT.match(sub) and len(sub) == 3):
            parsed.region = sub
            position += 1

    while position < len(remaining):
        sub = remaining[position]
        is_variant = _ALNUM.match(sub) and (
            5 <= len(sub) <= 8 or (len(sub) == 4 and sub[0].isdigit())
        )
        if is_variant:
            parsed.variants.append(sub)
            position += 1
            continue
        if len(sub) == 1:
            parsed.errors.append(
                f"{tag}: extension singleton {sub!r} is not permitted in "
                f"archive directory names"
            )
        else:
            parsed.errors.append(f"{tag}: unrecognised subtag {sub!r}")
        return parsed

    return parsed


# ---------------------------------------------------------------------------
# Validation results
# ---------------------------------------------------------------------------

@dataclass
class ComponentValidation:
    """Validation of one BCP 47 tag (one component of a mixed name)."""

    tag: str
    canonical: str
    registered: bool
    casing_valid: bool
    deprecated: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class TagValidation:
    """Validation of a full archive directory name expression."""

    expression: str
    components: list[ComponentValidation]
    dc_language: str
    dc_language_bcp47: str
    sat_authority: str                      # external | partial | none
    sat_authority_note: Optional[str] = None
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors and all(not c.errors for c in self.components)


# ---------------------------------------------------------------------------
# Component validation against the registry
# ---------------------------------------------------------------------------

def _validate_component(tag: str, registry: SubtagRegistry) -> ComponentValidation:
    parsed = _parse_single_tag(tag)
    result = ComponentValidation(
        tag=tag, canonical=tag, registered=False, casing_valid=True,
        errors=list(parsed.errors),
    )
    if parsed.errors:
        return result

    if parsed.private:
        # Structurally valid private use tag: never registered, casing
        # is lowercase throughout by convention.
        canonical = "x-" + "-".join(s.lower() for s in parsed.private)
        result.canonical = canonical
        result.casing_valid = tag == canonical
        if not result.casing_valid:
            result.errors.append(
                f"{tag}: casing is not canonical; expected {canonical}"
            )
        return result

    roles: list[tuple[str, str, str]] = [("language", "primary", parsed.primary)]
    if parsed.script:
        roles.append(("script", "script", parsed.script))
    if parsed.region:
        roles.append(("region", "region", parsed.region))
    for variant in parsed.variants:
        roles.append(("variant", "variant", variant))

    canonical_parts: list[str] = []
    registered = True
    deprecated = False

    for record_type, role, subtag in roles:
        canonical = _canonical_case(role, subtag)
        canonical_parts.append(canonical)
        if subtag != canonical:
            result.casing_valid = False
            result.errors.append(
                f"{tag}: subtag {subtag!r} is not in canonical casing; "
                f"expected {canonical!r} (ADR-003)"
            )
        record = registry.lookup(record_type, subtag)
        if record is None:
            registered = False
            result.errors.append(
                f"{tag}: {record_type} subtag {subtag!r} is not in the "
                f"IANA Language Subtag Registry"
            )
        elif record.deprecated:
            deprecated = True

    result.canonical = "-".join(canonical_parts)
    result.registered = registered
    result.deprecated = deprecated
    return result


# ---------------------------------------------------------------------------
# Derivation (spec section 3.2)
# ---------------------------------------------------------------------------

def _derive_dc_language(component: ComponentValidation,
                        registry: SubtagRegistry) -> str:
    parsed = _parse_single_tag(component.tag)
    if parsed.private or parsed.primary is None:
        return "und"

    primary = parsed.primary.lower()
    if len(primary) == 2:
        mapped = iso639_2t_for_part1(primary)
        return mapped if mapped else "und"

    # Three-letter primary subtag. Sign languages and other
    # macrolanguage members map to their macrolanguage's collective
    # code (ase -> sgn, spec section 3.2). Where the registry maps the
    # macrolanguage itself to a two-letter code (e.g. cmn -> zh), the
    # two-letter path applies transitively.
    record = registry.lookup("language", primary)
    if record is not None and record.macrolanguage:
        macro = record.macrolanguage.lower()
        if len(macro) == 2:
            mapped = iso639_2t_for_part1(macro)
            return mapped if mapped else "und"
        return macro

    # Documented MVP limitation: passed through as-is. ISO 639-3
    # codes with no ISO 639-2 equivalent are not detected.
    return primary


# ---------------------------------------------------------------------------
# Expression validation (single and mixed, spec sections 1.1 and 3.1)
# ---------------------------------------------------------------------------

def validate_expression(expression: str,
                        registry: SubtagRegistry) -> TagValidation:
    """Validate an archive directory name expression.

    A single tag is one BCP 47 tag. A mixed expression (ADR-002) is
    two or more tags joined by underscores in alphabetical order.
    """
    components = [
        _validate_component(part, registry) for part in expression.split("_")
    ]
    errors: list[str] = []

    if len(components) > 1:
        lowered = [c.tag.lower() for c in components]
        if lowered != sorted(lowered):
            errors.append(
                f"{expression}: mixed language components must be in "
                f"alphabetical order (ADR-002); expected "
                f"{'_'.join(sorted(lowered))}"
            )

    all_registered = all(c.registered for c in components)
    any_deprecated = any(c.deprecated for c in components)
    casing_valid = all(c.casing_valid for c in components)

    if all_registered and casing_valid and not any_deprecated:
        authority = "external"
        note = None
    elif all_registered and casing_valid and any_deprecated:
        # Registered but the representation is incomplete: a deprecated
        # subtag has a preferred value the expression does not use.
        authority = "partial"
        note = (
            "One or more subtags are deprecated in the IANA Language "
            "Subtag Registry. The registry records a preferred value "
            "this expression does not use."
        )
    else:
        authority = "none"
        note = DEFAULT_AUTHORITY_NOTE.format(
            cache_date=registry.file_date or "unknown"
        )

    if len(components) == 1:
        dc_language = _derive_dc_language(components[0], registry)
        dc_bcp47 = components[0].canonical
    else:
        # A mixed archive has no single primary language; und is the
        # honest ISO 639-2 value. Full fidelity lives in the bcp47
        # field, which preserves the joined expression.
        dc_language = "und"
        dc_bcp47 = "_".join(c.canonical for c in components)

    return TagValidation(
        expression=expression,
        components=components,
        dc_language=dc_language,
        dc_language_bcp47=dc_bcp47,
        sat_authority=authority,
        sat_authority_note=note,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Non-authority model (spec section 4)
# ---------------------------------------------------------------------------

def non_authority_expression(directory_name: str,
                             cache_date: Optional[str]) -> TagValidation:
    """Language record for a directory name that is not a BCP 47 tag.

    A private use x- tag is generated from the directory name:
    underscores become hyphens, casing is lowered, and the x- prefix
    is added. dc:language is und — the honest ISO 639-2 value when no
    mapping exists, not a failure value.
    """
    slug = re.sub(r"[^a-z0-9-]+", "-", directory_name.lower().replace("_", "-"))
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    generated = f"x-{slug}"

    return TagValidation(
        expression=directory_name,
        components=[
            ComponentValidation(
                tag=generated, canonical=generated,
                registered=False, casing_valid=True,
            )
        ],
        dc_language="und",
        dc_language_bcp47=generated,
        sat_authority="none",
        sat_authority_note=DEFAULT_AUTHORITY_NOTE.format(
            cache_date=cache_date or "unknown"
        ),
    )
