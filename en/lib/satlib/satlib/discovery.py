"""satlib.discovery — tool self-discovery from filesystem context.

Implements ADR-005 and spec section 1: a SAT tool determines its own
operational language context by walking upward from its resolved
location to the nearest ancestor directory whose name is a valid
BCP 47 language expression — a single tag or an ADR-002 mixed
expression, in canonical casing, validated against the IANA registry.

Discovery operates on the resolved artifact path: symlinks (the
operator's wrapper, delegated bin tiers) are resolved first, so the
walk runs inside the language-structured installed artifact
($SAT_TOOL_ROOT/en/bin/...), never inside an instance's symlink
farm.

The pattern test is registry-backed, not merely structural. This is
what stops bin/ and sat/ — both structurally plausible primary
subtags — from matching: they fail registry lookup and the walk
continues (spec section 1.1). Well-formed private use tags
(x-humpback-songs) are valid BCP 47 and do match, so previously
generated non-authority archive roots are discoverable like any
other.

When no ancestor matches before the filesystem root, the
non-authority model applies (spec section 4). The fallback candidate
name is the nearest ancestor above the innermost bin/ tier — the
humpback_songs of the spec's worked example — surfaced on the result
for the caller to pass to language.non_authority_expression. The
tool does not fail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .language import SubtagRegistry, TagValidation, validate_expression

__all__ = ["DiscoveryResult", "discover", "is_language_root"]

_BIN = "bin"


@dataclass
class DiscoveryResult:
    """Outcome of the self-discovery walk.

    context is the validated language expression of the matched
    ancestor, or None when the walk reached the filesystem root
    without a match — in which case fallback_name carries the
    directory name the non-authority model should be applied to, if
    one could be identified.
    """

    context: Optional[TagValidation]
    matched_dir: Optional[Path]
    fallback_name: Optional[str] = None
    walked: list[str] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return self.context is not None


def is_language_root(directory: Path, registry: SubtagRegistry) -> Optional[TagValidation]:
    """The validated expression if this directory is a language
    archive root, else None.

    A directory name that fails validation — unregistered, wrong
    casing, wrong mixed ordering — is not a language archive root
    (spec section 1.1); the distinction between its failure modes
    belongs to validation reporting, not to discovery.
    """
    result = validate_expression(directory.name, registry)
    return result if result.valid else None


def discover(tool_path: Path, registry: SubtagRegistry) -> DiscoveryResult:
    """Walk upward from a tool's location to its language context.

    tool_path may be the tool file itself or the directory containing
    it; symlinks are resolved before the walk (ADR-005 clarification:
    discovery operates on the resolved artifact path, not the
    wrapper).
    """
    resolved = tool_path.resolve()
    start = resolved.parent if resolved.is_file() else resolved

    walked: list[str] = []
    fallback: Optional[str] = None
    previous: Optional[Path] = None

    current = start
    while True:
        walked.append(current.name or str(current))

        match = is_language_root(current, registry)
        if match is not None:
            return DiscoveryResult(
                context=match, matched_dir=current, walked=walked,
            )

        # Track the non-authority fallback: the nearest ancestor
        # sitting directly above a bin/ tier (spec section 1.2,
        # humpback_songs/bin/ -> humpback_songs).
        if fallback is None and previous is not None and previous.name == _BIN:
            if current.name and current.name != _BIN:
                fallback = current.name

        if current.parent == current:  # filesystem root reached
            return DiscoveryResult(
                context=None, matched_dir=None,
                fallback_name=fallback, walked=walked,
            )
        previous = current
        current = current.parent
