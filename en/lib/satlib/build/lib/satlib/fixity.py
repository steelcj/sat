#
# source
#   project: sat
#   path: en/lib/satlib/satlib/fixity.py
#
"""satlib.fixity — recording and checking fixity (ADR-027).

Fixity answers one question: is this file, bit for bit, what it was when
its digest was recorded? SAT records the expectation in its own
sidecars, computes with the standard library, and exports the universal
format so proven tools (coreutils, rclone) can verify a copy or a
transfer.

Three classes of file, three meanings of a mismatch (ADR-027 decision
1). Write-once records — identity.yml, provenance.yml — may never
legitimately change, so a mismatch is record-corruption, a hard
finding. Cataloged content is legitimately edited, so a mismatch is
content-modified, a soft finding whose remedy is re-cataloging; the
finding carries the container-format honesty note, because some
applications rewrite .docx/.xlsx/.pptx with no content edit and SAT
cannot know which touched the file. Operator settings (dc.yml and kin)
carry no fixity at all: a baseline on a file meant to change is fixity
crying wolf on every edit.

Every role directory may carry one fixity.yml under a recorded — not
generated — contract: it is written by deliberate acts and stamped with
recorded/recorded_by, never regenerated from the tree (a rebuildable
guard whose documented remedy re-attests corrupted records is no
guard). The content role additionally attests the content itself. The
children index attests existence; fixity attests integrity.

Checking is deliberate — there is no ambient daemon — because active
content goes fixity-stale constantly and an always-on alarm is an
ignored alarm. Findings speak the ADR-024 grammar; the loop closes
through the operator, and checking never writes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Sequence

from .roles import read_role_yaml, role_path

__all__ = [
    "FIXITY_RECORD",
    "DEFAULT_ALGORITHM",
    "WRITE_ONCE_RECORDS",
    "CONTAINER_SUFFIXES",
    "FixityFinding",
    "digest_file",
    "record_fixity",
    "read_fixity",
    "check_fixity",
    "format_sha256sums",
]

FIXITY_RECORD = "fixity.yml"
DEFAULT_ALGORITHM = "sha256"

# The write-once records a role's fixity attests (ADR-027 decision 1).
WRITE_ONCE_RECORDS = ("identity.yml", "provenance.yml")

# Container formats some applications rewrite without a content edit
# (ADR-027 decision 1): the soft finding says so, and no more.
CONTAINER_SUFFIXES = (".docx", ".xlsx", ".pptx")

_CONTAINER_NOTE = (
    " — note: container formats such as .docx, .xlsx, and .pptx are "
    "rewritten by some applications without any content edit; SAT cannot "
    "know which application touched the file"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class FixityFinding:
    """One fixity divergence, in the ADR-024 findings grammar."""
    kind: str        # record-corruption | content-modified | staging-unmatched
    target: str      # the file the finding is about
    means: str       # the interpretation, honestly graded
    severity: str    # "hard" | "soft"
    remedy: str = ""

    @property
    def hard(self) -> bool:
        return self.severity == "hard"


# ---------------------------------------------------------------------------
# Computation (stdlib, no dependency for three lines of hashlib)
# ---------------------------------------------------------------------------

def digest_file(path: Path, algorithm: str = DEFAULT_ALGORITHM) -> str:
    """The hex digest of a file, read in chunks so large content is safe."""
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Recording (a deliberate act, stamped)
# ---------------------------------------------------------------------------

def _fixity_header(entity: Path, role: str) -> str:
    name = entity.name
    return (
        f"# {name}/.{name}.assets/{role}/{FIXITY_RECORD}\n"
        f"#\n"
        f"#   Written at creation, updated by deliberate operations.\n"
        f"#   Recorded digests; a mismatch is a fixity finding (ADR-027).\n"
        f"#\n"
    )


def record_fixity(entity: Path, role: str, *,
                  content_path: Optional[Path] = None,
                  is_dir: Optional[bool] = None,
                  command: str, version: str,
                  algorithm: str = DEFAULT_ALGORITHM,
                  now: Callable[[], str] = _utc_now) -> Path:
    """Digest a role's write-once records and write its fixity.yml.

    A deliberate act: computed at creation, at ingress, or during a
    named operation, and stamped in recorded_by. At the content role a
    content_path additionally attests the content itself (digest and
    size). Only the write-once records that exist are attested — a
    document's content role carries identity.yml but no provenance.yml,
    for instance, and the record reflects exactly what is present.
    """
    records: dict = {}
    for name in WRITE_ONCE_RECORDS:
        path = role_path(entity, role, name, is_dir=is_dir)
        if path.is_file():
            records[name] = {"algorithm": algorithm, "digest": digest_file(path, algorithm)}

    body: dict = {"records": records}
    if content_path is not None:
        body["content"] = {
            "algorithm": algorithm,
            "digest": digest_file(content_path, algorithm),
            "size": content_path.stat().st_size,
        }
    body["recorded"] = now()
    body["recorded_by"] = {"command": command, "version": version}

    path = role_path(entity, role, FIXITY_RECORD, is_dir=is_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    import yaml  # local import: only recording needs the dumper
    path.write_text(
        _fixity_header(entity, role)
        + yaml.safe_dump(body, sort_keys=False, allow_unicode=True),
        "utf-8",
    )
    return path


def read_fixity(entity: Path, role: str,
                is_dir: Optional[bool] = None) -> Optional[dict]:
    """Read a role's fixity record, or None if absent."""
    return read_role_yaml(entity, role, FIXITY_RECORD, is_dir=is_dir)


# ---------------------------------------------------------------------------
# Checking (deliberate; never writes)
# ---------------------------------------------------------------------------

def check_fixity(entity: Path, role: str, *,
                 content_path: Optional[Path] = None,
                 is_dir: Optional[bool] = None) -> list[FixityFinding]:
    """Compare recorded digests against the files, now. Never writes.

    Returns record-corruption (hard) for any write-once record whose
    digest no longer matches or that has vanished, and content-modified
    (soft) when the content's digest has changed, with the container-
    format honesty note where the suffix warrants it. An absent
    fixity.yml means no baseline was recorded — nothing to check, no
    findings.
    """
    body = read_fixity(entity, role, is_dir=is_dir)
    if body is None:
        return []

    findings: list[FixityFinding] = []
    for name, recorded in (body.get("records") or {}).items():
        path = role_path(entity, role, name, is_dir=is_dir)
        if not path.is_file():
            findings.append(FixityFinding(
                "record-corruption", str(path),
                f"{name} is recorded in fixity but absent from disk",
                "hard", "restore the record from version control or backup"))
            continue
        actual = digest_file(path, recorded.get("algorithm", DEFAULT_ALGORITHM))
        if actual != recorded.get("digest"):
            findings.append(FixityFinding(
                "record-corruption", str(path),
                f"{name} digest does not match the recorded value; a "
                f"write-once record has changed, which is corruption or "
                f"tampering",
                "hard", "restore the record from version control or backup"))

    content = body.get("content")
    if content and content_path is not None:
        if not content_path.is_file():
            findings.append(FixityFinding(
                "record-corruption", str(content_path),
                "content is recorded in fixity but absent from disk",
                "hard", "restore the content from version control or backup"))
        else:
            actual = digest_file(content_path,
                                 content.get("algorithm", DEFAULT_ALGORITHM))
            if actual != content.get("digest"):
                means = ("content has changed since it was cataloged; the "
                         "remedy is re-cataloging, not alarm")
                if content_path.suffix.lower() in CONTAINER_SUFFIXES:
                    means += _CONTAINER_NOTE
                findings.append(FixityFinding(
                    "content-modified", str(content_path), means,
                    "soft", "re-catalog the document to refresh its digest"))

    return findings


# ---------------------------------------------------------------------------
# Export: the universal manifest for proven verifiers (ADR-027 decision 5)
# ---------------------------------------------------------------------------

def format_sha256sums(entries: Sequence[tuple[str, str]]) -> str:
    """The coreutils SHA256SUMS format: '<digest>  <path>' per line.

    Derived from the sidecars and disposable like every derived record;
    `sha256sum -c` and `rclone check --checkfile` both consume it.
    """
    return "".join(f"{digest}  {path}\n" for digest, path in entries)
