#
# source
#   project: sat
#   path: en/lib/satlib/satlib/staging.py
#
"""satlib.staging — pre-ingress placement and promotion (ADR-029).

`staging/` lives at the collection root, sibling to the language archives,
and holds raw content that has not yet been assigned a language by
filesystem position and carries no SAT records. Promotion is the act of
moving a staged file into a language archive location, where `content
ingress` then catalogs it (ADR-029 decision 3): one narrated act, one verb.

`content ingress` owns only the promotion entry point, which is this
module's `promote`. The rest of ADR-029 — `scan_staging()`, the
collection-level `staging-fixity.yml` fixity-at-first-touch record, and
`collection stage --scan` — is collection-tier work and is deliberately out
of scope here (content-ingress-specification section 14).

The destination is always operator-supplied, never inferred from the file's
frontmatter: a human who can read the content decides where it belongs, and
cataloging then fires the language-disagreement finding when the frontmatter
disagrees with the chosen archive. Validating that the destination resolves
to a real archive location is the caller's job (it owns role discovery);
this module performs the move.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["StagingError", "promote"]


class StagingError(RuntimeError):
    """A staging promotion could not be performed."""


def promote(source, destination_dir) -> Path:
    """Move a staged file into destination_dir, returning its new path.

    The file keeps its name. The destination directory is created if needed
    (pipeline step 2 mints its content records afterward). Refuses to
    overwrite an existing file at the destination, and leaves the source in
    place on refusal. The move is a single os.replace, atomic within a
    filesystem.
    """
    source = Path(source).resolve()
    if not source.is_file():
        raise StagingError(f"not a file to promote: {source}")

    destination_dir = Path(destination_dir)
    new_path = destination_dir / source.name
    if new_path.exists():
        raise StagingError(
            f"destination already holds {source.name}: {new_path}"
        )

    destination_dir.mkdir(parents=True, exist_ok=True)
    os.replace(source, new_path)
    return new_path.resolve()
