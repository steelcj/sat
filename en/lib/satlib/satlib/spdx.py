"""satlib.spdx — SPDX license identifier validation (ADR-033).

The SPDX License List is the single authoritative source for license
identifier validation in SAT (ADR-033). SAT defines no list of its own;
it defers entirely to SPDX, the same relationship satlib.language has to
the IANA Language Subtag Registry (ADR-003). This module rides the
generic cache machinery in satlib.registry exactly as satlib.language
does — a CachedSource descriptor names the authority and its staleness
policy; the fetched JSON is parsed here.

Two published files carry the whole authority (ADR-033):

    licenses.json     every license identifier, with deprecation,
                      OSI approval, and FSF-libre status
    exceptions.json   every license-exception identifier, as used on
                      the right of a ``WITH`` operator

An identifier is valid in SAT if and only if it appears as a current,
non-deprecated identifier in the fetched ``licenses.json`` (ADR-033). A
deprecated identifier is not invalid — SPDX never removes a retired
identifier — but it is flagged. licenses.json does not itself carry a
replacement identifier for a deprecated one; the ``replacement`` field
is parsed defensively should the data ever provide it, and is otherwise
None. The classic deprecation the SAT repository cares about
(``GPL-3.0`` → ``GPL-3.0-or-later``) is a documentation matter, not a
field this module invents.

Matching follows the SPDX guideline that identifiers compare case
insensitively while a canonical casing exists: an exact hit validates
outright; a case-insensitive hit validates but records a casing finding
and names the canonical form, mirroring satlib.language's ADR-003
casing handling.

The SPDX license-expression grammar (``AND`` / ``OR`` / ``WITH``, the
``+`` operator, parentheses, and ``LicenseRef-`` / ``DocumentRef-``
custom references) is validated structurally. Operators are
case-sensitive uppercase per the SPDX specification; a lowercased
operator is recognised only to produce a precise finding.

This module validates and reports. It never rewrites a field: applying
a correction is a separate, deliberate act (the ``licence-apply`` tool
sketched in ADR-033's radar entry), exactly as satlib.language surfaces
a casing finding rather than silently normalising it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .registry import CachedSource

__all__ = [
    "SPDX_LICENSES_URL",
    "SPDX_EXCEPTIONS_URL",
    "spdx_licenses_source",
    "spdx_exceptions_source",
    "extract_list_version",
    "LicenseRecord",
    "ExceptionRecord",
    "LicenseList",
    "ExceptionList",
    "LicenseValidation",
    "ExpressionValidation",
    "validate_identifier",
    "validate_expression",
    "SPDX_TAG",
    "extract_spdx_tags",
]

# The canonical marker SAT declares a license with, everywhere: inside a
# ``dc:rights`` / ``dcterms:rights`` folded scalar, in a source-file
# header comment, in a LICENSE preamble. Whatever follows it on the line
# is the (possibly compound) license expression.
SPDX_TAG = "SPDX-License-Identifier:"

# A tag counts only in *declaration position*: what precedes it on the
# line is limited to whitespace and comment/indent lead-ins (YAML indent,
# ``#`` / ``//`` / ``*`` code comments, ``<!--`` HTML, ``>`` blockquote,
# ``-`` list). This excludes the marker where it appears as data — a
# string literal, a regex, inline-code prose discussing SPDX — which a
# license audit must not mistake for a real declaration.
_DECLARATION_PREFIX = re.compile(r"^[\s#/*;%>!<\-]*$")
# The expression must begin like an SPDX identifier (or an opening paren),
# so a documentation placeholder such as ``<expr>`` is never graded.
_IDENTIFIER_START = re.compile(r"[A-Za-z0-9(]")


def extract_spdx_tags(text: str) -> list[tuple[int, str]]:
    """Declaration-position ``SPDX-License-Identifier:`` expressions.

    Returns ``(line, expression)`` pairs, 1-based line numbers, in reading
    order. Only tags in declaration position are returned (see
    ``_DECLARATION_PREFIX``): the marker inside a quoted string, a regex,
    or inline-code prose is data, not a license, and is skipped. The
    expression is returned verbatim (whitespace-trimmed) for
    ``validate_expression`` to judge; a compound expression with spaces
    (``MIT OR Apache-2.0``) is kept whole. A tag with nothing after it, or
    followed by a non-identifier placeholder, is skipped.
    """
    tags: list[tuple[int, str]] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        position = raw.find(SPDX_TAG)
        if position == -1:
            continue
        if not _DECLARATION_PREFIX.match(raw[:position]):
            continue
        expression = raw[position + len(SPDX_TAG):].strip()
        if not expression or not _IDENTIFIER_START.match(expression[0]):
            continue
        tags.append((line_number, expression))
    return tags

# The SPDX-published raw data, tagged per release the same way SAT
# already fetches the IANA registry (ADR-003, ADR-033). The main branch
# always holds the current release; a specific release can be pinned by
# swapping the ref in the URL a CachedSource is built with.
SPDX_LICENSES_URL = (
    "https://raw.githubusercontent.com/spdx/license-list-data/main/json/"
    "licenses.json"
)
SPDX_EXCEPTIONS_URL = (
    "https://raw.githubusercontent.com/spdx/license-list-data/main/json/"
    "exceptions.json"
)


def extract_list_version(content: bytes) -> Optional[str]:
    """The ``licenseListVersion`` an SPDX data file declares, or None.

    Both licenses.json and exceptions.json carry it; it plays the same
    role for the freshness record that the IANA File-Date does
    (satlib.language.extract_file_date), so it is wired in as the
    CachedSource file-date extractor.
    """
    try:
        data = json.loads(content.decode("utf-8", errors="replace"))
    except (ValueError, UnicodeError):
        return None
    version = data.get("licenseListVersion") if isinstance(data, dict) else None
    return str(version) if version is not None else None


def spdx_licenses_source(cache_path: Path, staleness_days: int = 30,
                         source_url: str = SPDX_LICENSES_URL) -> CachedSource:
    """CachedSource descriptor for the SPDX ``licenses.json`` list."""
    return CachedSource(
        name="spdx-license-list",
        source_url=source_url,
        cache_path=cache_path,
        staleness_days=staleness_days,
        file_date_extractor=extract_list_version,
    )


def spdx_exceptions_source(cache_path: Path, staleness_days: int = 30,
                           source_url: str = SPDX_EXCEPTIONS_URL) -> CachedSource:
    """CachedSource descriptor for the SPDX ``exceptions.json`` list."""
    return CachedSource(
        name="spdx-license-exceptions",
        source_url=source_url,
        cache_path=cache_path,
        staleness_days=staleness_days,
        file_date_extractor=extract_list_version,
    )


# ---------------------------------------------------------------------------
# Parsing the published JSON
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LicenseRecord:
    """One entry of the SPDX license list.

    ``osi_approved`` and ``fsf_libre`` are tri-state: True and False are
    both claims SPDX makes, and None means the list did not say (the
    ``isFsfLibre`` key is absent from most entries, so its absence is
    genuinely "no statement", not "not libre").
    """

    license_id: str
    name: str = ""
    deprecated: bool = False
    osi_approved: Optional[bool] = None
    fsf_libre: Optional[bool] = None
    reference: Optional[str] = None
    replacement: Optional[str] = None


@dataclass(frozen=True)
class ExceptionRecord:
    """One entry of the SPDX license-exception list."""

    exception_id: str
    name: str = ""
    deprecated: bool = False
    reference: Optional[str] = None


class LicenseList:
    """Parsed SPDX ``licenses.json`` with case-tolerant lookup."""

    def __init__(self, records: dict[str, LicenseRecord],
                 list_version: Optional[str]):
        # Keyed by the exact canonical id; a folded index resolves a
        # case-insensitive hit back to the canonical record.
        self._records = records
        self._folded = {key.lower(): key for key in records}
        self.list_version = list_version

    @classmethod
    def parse(cls, content: bytes) -> "LicenseList":
        data = json.loads(content.decode("utf-8", errors="replace"))
        version = data.get("licenseListVersion") if isinstance(data, dict) else None
        records: dict[str, LicenseRecord] = {}

        for entry in (data.get("licenses") or []):
            license_id = entry.get("licenseId")
            if not license_id:
                continue
            records[license_id] = LicenseRecord(
                license_id=license_id,
                name=entry.get("name", ""),
                deprecated=bool(entry.get("isDeprecatedLicenseId", False)),
                osi_approved=entry.get("isOsiApproved"),
                fsf_libre=entry.get("isFsfLibre"),
                reference=entry.get("reference"),
                # Defensive: licenses.json does not currently carry a
                # replacement for a deprecated id, but a future release
                # may, and ADR-033 asks for it "where SPDX provides one".
                replacement=entry.get("preferredLicenseId")
                or entry.get("replacedBy"),
            )

        return cls(records, str(version) if version is not None else None)

    def get(self, license_id: str) -> Optional[LicenseRecord]:
        """Exact-case lookup, or None."""
        return self._records.get(license_id)

    def canonical(self, license_id: str) -> Optional[str]:
        """The canonical id for a case-insensitive match, or None."""
        return self._folded.get(license_id.lower())


class ExceptionList:
    """Parsed SPDX ``exceptions.json`` with case-tolerant lookup."""

    def __init__(self, records: dict[str, ExceptionRecord],
                 list_version: Optional[str]):
        self._records = records
        self._folded = {key.lower(): key for key in records}
        self.list_version = list_version

    @classmethod
    def parse(cls, content: bytes) -> "ExceptionList":
        data = json.loads(content.decode("utf-8", errors="replace"))
        version = data.get("licenseListVersion") if isinstance(data, dict) else None
        records: dict[str, ExceptionRecord] = {}

        for entry in (data.get("exceptions") or []):
            exception_id = entry.get("licenseExceptionId")
            if not exception_id:
                continue
            records[exception_id] = ExceptionRecord(
                exception_id=exception_id,
                name=entry.get("name", ""),
                deprecated=bool(entry.get("isDeprecatedLicenseId", False)),
                reference=entry.get("reference"),
            )

        return cls(records, str(version) if version is not None else None)

    def get(self, exception_id: str) -> Optional[ExceptionRecord]:
        return self._records.get(exception_id)

    def canonical(self, exception_id: str) -> Optional[str]:
        return self._folded.get(exception_id.lower())


# ---------------------------------------------------------------------------
# Single-identifier validation
# ---------------------------------------------------------------------------

@dataclass
class LicenseValidation:
    """Validation of one license identifier against the SPDX list."""

    identifier: str                          # as written, sans any '+'
    canonical: str                           # SPDX canonical casing
    registered: bool                         # a current or deprecated hit
    casing_valid: bool
    deprecated: bool = False
    or_later: bool = False                   # the '+' operator was present
    osi_approved: Optional[bool] = None
    fsf_libre: Optional[bool] = None
    replacement: Optional[str] = None        # SPDX-provided, else None
    custom_ref: bool = False                 # LicenseRef-/DocumentRef-
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


# A SPDX ``LicenseRef``/``DocumentRef`` custom identifier (spec: an
# idstring is letters, digits, ``.`` and ``-``).
_LICENSE_REF_RE = re.compile(
    r"^(DocumentRef-[A-Za-z0-9.\-]+:)?LicenseRef-[A-Za-z0-9.\-]+$"
)


def validate_identifier(identifier: str,
                        licenses: LicenseList) -> LicenseValidation:
    """Validate one simple SPDX identifier (a ``WITH``/operator operand).

    Accepts a trailing ``+`` (the "or later" operator) and a
    ``LicenseRef-`` / ``DocumentRef-…:LicenseRef-`` custom reference,
    which is structurally valid and never checked against the list.
    """
    raw = identifier
    or_later = raw.endswith("+")
    bare = raw[:-1] if or_later else raw

    result = LicenseValidation(
        identifier=bare, canonical=bare, registered=False,
        casing_valid=True, or_later=or_later,
    )

    if not bare:
        result.errors.append(f"{raw!r}: empty license identifier")
        return result

    if _LICENSE_REF_RE.match(bare):
        result.custom_ref = True
        result.registered = True  # a well-formed custom ref stands on its own
        result.canonical = bare
        if or_later:
            result.errors.append(
                f"{raw}: the '+' operator does not apply to a LicenseRef"
            )
        return result

    exact = licenses.get(bare)
    if exact is not None:
        _fill_from_record(result, exact, bare)
        return result

    canonical = licenses.canonical(bare)
    if canonical is not None:
        record = licenses.get(canonical)
        result.casing_valid = False
        result.canonical = canonical
        result.errors.append(
            f"{bare}: identifier is not in SPDX canonical casing; "
            f"expected {canonical!r}"
        )
        _fill_from_record(result, record, canonical, keep_canonical=True)
        return result

    result.errors.append(
        f"{bare}: not a current SPDX license identifier"
    )
    return result


def _fill_from_record(result: LicenseValidation, record: LicenseRecord,
                      canonical: str, keep_canonical: bool = False) -> None:
    result.registered = True
    if not keep_canonical:
        result.canonical = canonical
    result.deprecated = record.deprecated
    result.osi_approved = record.osi_approved
    result.fsf_libre = record.fsf_libre
    result.replacement = record.replacement
    if record.deprecated:
        hint = (f"; SPDX records {record.replacement!r} as the replacement"
                if record.replacement else "")
        result.errors.append(
            f"{canonical}: identifier is deprecated in the SPDX License "
            f"List{hint}"
        )


# ---------------------------------------------------------------------------
# License-expression validation (AND / OR / WITH / '+' / parens)
# ---------------------------------------------------------------------------

@dataclass
class ExpressionValidation:
    """Validation of a full SPDX license expression."""

    expression: str
    components: list[LicenseValidation] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors and all(c.valid for c in self.components)

    @property
    def deprecated(self) -> bool:
        return any(c.deprecated for c in self.components)


_OPERATORS = {"AND", "OR", "WITH"}
_OPERATORS_FOLDED = {op.lower(): op for op in _OPERATORS}


def _tokenize(expression: str) -> list[str]:
    """Split an expression into identifiers, operators, and parentheses.

    Parentheses are their own tokens; everything else is separated by
    whitespace. A trailing ``+`` stays glued to its identifier because
    SPDX writes it with no space.
    """
    spaced = expression.replace("(", " ( ").replace(")", " ) ")
    return spaced.split()


def validate_expression(expression: str, licenses: LicenseList,
                        exceptions: Optional[ExceptionList] = None
                        ) -> ExpressionValidation:
    """Validate a SPDX license expression, structurally and per-id.

    Recursive-descent over the SPDX grammar:

        or_expr   := and_expr (OR and_expr)*
        and_expr  := with_expr (AND with_expr)*
        with_expr := primary (WITH exception)?
        primary   := '(' or_expr ')' | identifier['+'] | license-ref

    Every license operand is validated against ``licenses`` (deprecation
    and casing surfaced as findings); every ``WITH`` operand is checked
    against ``exceptions`` when one is supplied. Malformed operator
    placement, unbalanced parentheses, and lowercased operators each
    produce a precise error.
    """
    result = ExpressionValidation(expression=expression)
    tokens = _tokenize(expression)
    if not tokens:
        result.errors.append("empty license expression")
        return result

    parser = _ExpressionParser(tokens, licenses, exceptions, result)
    parser.parse_or()
    if not parser.at_end:
        result.errors.append(
            f"unexpected token {parser.peek()!r} after a complete expression"
        )
    return result


class _ExpressionParser:
    """One-shot recursive-descent parser feeding an ExpressionValidation."""

    def __init__(self, tokens: list[str], licenses: LicenseList,
                 exceptions: Optional[ExceptionList],
                 result: ExpressionValidation):
        self._tokens = tokens
        self._pos = 0
        self._licenses = licenses
        self._exceptions = exceptions
        self._result = result

    # -- token cursor ----------------------------------------------------

    @property
    def at_end(self) -> bool:
        return self._pos >= len(self._tokens)

    def peek(self) -> Optional[str]:
        return None if self.at_end else self._tokens[self._pos]

    def _advance(self) -> str:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _canonical_operator(self, token: Optional[str]) -> Optional[str]:
        """The uppercase operator a token denotes, flagging bad casing."""
        if token is None:
            return None
        if token in _OPERATORS:
            return token
        folded = _OPERATORS_FOLDED.get(token.lower())
        if folded is not None:
            self._result.errors.append(
                f"operator {token!r} must be uppercase {folded!r} "
                f"(SPDX operators are case sensitive)"
            )
            return folded
        return None

    # -- grammar ---------------------------------------------------------

    def parse_or(self) -> None:
        self.parse_and()
        while self._canonical_operator(self.peek()) == "OR":
            self._advance()
            if self.at_end:
                self._result.errors.append("expression ends after 'OR'")
                return
            self.parse_and()

    def parse_and(self) -> None:
        self.parse_with()
        while self._canonical_operator(self.peek()) == "AND":
            self._advance()
            if self.at_end:
                self._result.errors.append("expression ends after 'AND'")
                return
            self.parse_with()

    def parse_with(self) -> None:
        self.parse_primary()
        if self._canonical_operator(self.peek()) == "WITH":
            self._advance()
            token = self.peek()
            if token is None or self._canonical_operator(token) is not None \
                    or token in ("(", ")"):
                self._result.errors.append(
                    "'WITH' must be followed by a license-exception identifier"
                )
                return
            self._advance()
            self._check_exception(token)

    def parse_primary(self) -> None:
        token = self.peek()
        if token is None:
            self._result.errors.append("expected a license identifier")
            return
        if token == "(":
            self._advance()
            self.parse_or()
            if self.peek() == ")":
                self._advance()
            else:
                self._result.errors.append("unbalanced '(' in expression")
            return
        if token == ")":
            self._result.errors.append("unexpected ')' in expression")
            self._advance()
            return
        if self._canonical_operator(token) is not None:
            self._result.errors.append(
                f"expected a license identifier, found operator {token!r}"
            )
            self._advance()
            return
        # A license operand.
        self._advance()
        self._result.components.append(
            validate_identifier(token, self._licenses)
        )

    # -- WITH operand ----------------------------------------------------

    def _check_exception(self, token: str) -> None:
        if self._exceptions is None:
            return  # no exception list supplied; structure accepted as-is
        if self._exceptions.get(token) is not None:
            record = self._exceptions.get(token)
            if record.deprecated:
                self._result.errors.append(
                    f"{token}: license exception is deprecated in the SPDX list"
                )
            return
        canonical = self._exceptions.canonical(token)
        if canonical is not None:
            self._result.errors.append(
                f"{token}: exception is not in SPDX canonical casing; "
                f"expected {canonical!r}"
            )
            return
        self._result.errors.append(
            f"{token}: not a current SPDX license-exception identifier"
        )
