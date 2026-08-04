---
status: Proposed
date: 2026-07-31
version: 0.1.0
---

# ADR-029: Staging — Pre-Ingress Content Placement and Promotion

**Numbering note:** provisional. Per house practice, ADR numbering is
confirmed by listing `en/docs/architecture/adrs/` directly — search has
previously missed files in that directory. ADR-028 is referenced in
prior session memory as already filed (the `dc:` vs `dcterms:`
decision); this draft assumes the next free number is 029, to be
confirmed against the actual directory before filing.

## Context

`content ingress` (`content-ingress-specification-v0.2.1.md`) assumes
its target already lives inside a language archive — its cascade
resolution walks up through an archive role directory to resolve
`language.yml`, and that walk has nothing to find for a file sitting
outside any archive. But content does not arrive pre-sorted into
archives. Something has to hold it in the gap between "a file exists"
and "a file is filed."

This gap already has a name and a partial implementation, just no
ratifying decision. ADR-027 assumes it: *"uncataloged content in
`staging/` is digested at first touch, giving reconciliation its only
evidence for identity-less files."* ADR-026's seeding round built it:
`satlib.seed._seed_staging()` creates `<collection>/staging/` holding
raw Markdown with frontmatter — an en/fr pair plus one deliberately
misfiled sample, "load-bearing" for testing the language-disagreement
finding once cataloging existed to catch it. State-of-SAT v0.3.0 lists
the gap explicitly: *"cataloging and content ingress (ADR-023);
staging is placed, not ingressed."*

So the location and rough shape are already decided by precedent — this
ADR ratifies that precedent, closes the two things it left open (where
does fixity-at-first-touch actually record its digests, and what
operation takes a file from staging into an archive), and corrects one
assumption `content-ingress-specification-v0.2.1.md` made too
narrowly: that specification's Non-Goals section deferred staging as
"a separate, undecided question." It wasn't fully undecided — it was
decided in `seed.py` and never written down as a decision.

## Decision

### 1. `staging/` lives at the collection root, sibling to language archives

Confirmed from `_seed_staging(collection)`: `staging = collection /
"staging"`. Not inside any language archive — content arriving in
`staging/` has not yet been assigned a language by filesystem position
(ADR-001), which is exactly the point: assigning it that position is
what promotion (decision 3) does.

### 2. `staging/` carries no per-file SAT records

Per `seed.py`'s own docstring: *"staging is not language-structured
(it is pre-ingress), so nothing here carries SAT records."* No assets
directories, no identity, no role directories. A file in staging is
inert to every satlib mechanism except one: fixity-at-first-touch
(decision 4). This is deliberate, not an oversight — minting identity
or writing role records for content that hasn't been placed yet would
mean re-minting or discarding them at promotion, the exact
never-re-mint discipline ADR-021 exists to prevent.

### 3. Promotion is `content ingress` with an explicit destination, not a separate command

The seeded sample's own body text is the specification: *"Ingress this
file to practice cataloging."* Not "stage" or "promote" — ingress. This
ADR settles on a single verb doing both jobs in one narrated act rather
than two commands (a promote-then-ingest split was considered and
rejected; see Alternatives), extending `content-ingress-
specification-v0.2.1.md`'s CLI surface with a new form:

```
content ingress <path/in/staging.md> --to <archive>/<content-directory>/
    Moves the file out of staging/ into the named language archive
    location, then runs the standard ingress pipeline (cataloging,
    identity, fixity, the ingress record) against it at its new path.
    The move and the cataloging are one atomic, narrated act.
```

The destination is always operator-supplied, never inferred from
frontmatter. This is why the misfiled sample works as a lesson: its
body is French, its frontmatter claims `en`. An operator promoting by
what they can read moves it toward `fr/` — and cataloging then finds
the archive says `fr` while the frontmatter says `en`, firing the
exact language-disagreement finding ADR-023 defines. If destination
were inferred from frontmatter instead, this file would promote
straight to `en/` and the finding would never fire — the lesson only
works because a human, not the frontmatter, decides where content
belongs.

This requires a companion amendment to
`content-ingress-specification-v0.2.1.md`: add this CLI form and a
pipeline step 0 ("if the source is in staging/, move it to the
destination first"), and retire the Non-Goals entry that deferred
staging as undecided.

### 4. Fixity-at-first-touch lives in one collection-level derived record, not per file

Decision 2 rules out per-file `fixity.yml` — there is no assets
directory to hold one. But ADR-027 already promises staging content is
digested at first touch, and reconciliation's evidence hierarchy
(ADR-024, rank 4) depends on that digest existing for identity-less
files. The record is therefore collection-scoped and derived, matching
the shape `children.yml` and `work-index.yml` already established
(one file, one writer, generated-record header, rebuildable,
disposable):

```yaml
# .my-collection.assets/collection/staging-fixity.yml
#
#   To update, rescan using:
#     collection stage --scan
#
sat_version: "0.1"
generated: "2026-07-31T15:00:00Z"
generated_by:
  command: collection stage --scan
  version: "0.8.0"

entries:
  welcome.md:
    algorithm: sha256
    digest: "9f2b1c47a03d8e6b12f4c9a75e08d3b1a6c2f04e9d817b5a3c60e2f18b4d41ac"
  bienvenue.md:
    algorithm: sha256
    digest: "3c7d8e21b4a9f0c6d5e2a17b8f4c0d9e6a3b2c15d8e7f4a09b6c3d2e1f0a08be"
```

`collection stage --scan` walks `staging/`, digesting anything not yet
recorded and dropping entries whose file has vanished (promoted or
removed) — mirroring how `children.yml` is rebuilt, not incrementally
trusted. "First touch" is therefore whenever `--scan` next runs, not a
literal filesystem-event hook; the watcher (ADR-014, still deferred)
is the eventual automation, exactly as it is for every other
first-touch claim in this codebase. `content ingress --to` also
updates this record on promotion, removing the promoted entry, the
same incremental-update-falls-back-to-rebuild pattern `work-index.yml`
already uses.

### 5. Tier ownership

`staging/`'s existence and its `staging-fixity.yml` are collection-tier
concerns — declared and scanned through `bin/collection/`
(`collection stage --scan`), consistent with ADR-022's tier-permission
precedent (work/index operations are collection-tier; ingress itself
is content-tier). Promotion-and-ingress (`content ingress ... --to`)
remains content-tier, invoked through `bin/content/`, since it is
`content ingress` — no new tier boundary is introduced.

## Alternatives Considered

**A separate `collection stage promote` command, then `content ingress`
as a second step** — rejected. The seeded lesson content names the
single-step verb explicitly ("ingress this file"), and a two-command
split would mean a file sits promoted-but-uncataloged in an archive
with no identity — a state every other write-once mechanism in this
codebase (ADR-021, ADR-022) treats as a hazard to avoid, not a resting
point to design for.

**Destination inferred from frontmatter's `dc:language`/
`dc:language_bcp47`** — rejected. It would silently defeat the
misfiled-sample lesson (see decision 3) and, more generally, hands a
structural decision — which archive a document belongs to — to a
transcribed claim ADR-023 already treats as untrusted for exactly this
field ("read, never accepted").

**Per-file fixity sidecars in staging, via a lightweight non-role
record** — rejected. It reintroduces the per-file assets-directory
machinery decision 2 deliberately excludes, for content that by
definition hasn't been placed yet. The collection-level derived record
costs nothing extra and matches an already-established pattern instead
of inventing a new one.

**A filesystem-watcher hook for true first-touch** — rejected for this
ADR. ADR-014's watcher is itself still deferred; `collection stage
--scan` is the correct manual mechanism now, and the watcher, when
built, calls the same underlying function, exactly as ADR-022
established for its own automation story ("automation narrates").

## Consequences

- `staging/` at the collection root is ratified as SAT's pre-ingress
  holding area, formalizing what `seed.py` already implements
- `content-ingress-specification-v0.2.1.md` needs a companion
  amendment: the `--to` CLI form, pipeline step 0, and removal of the
  Non-Goals entry deferring staging
- satlib gains a small `staging.py` (or an addition to `children.py`'s
  neighborhood): `scan_staging()`, `staging-fixity.yml` read/write
  following the generated-record contract, and the promotion helper
  `content ingress --to` calls before running its existing pipeline
- `collection stage --scan` joins the CLI surface at the collection
  tier; no new permission tier is introduced
- The seeded lesson (`welcome.md`, `bienvenue.md`, the misfiled sample)
  now has a real command to complete it end to end, closing the
  sequencing note both ADR-026 and the cascade-round summary left open
  ("the full ingress lesson needs cataloging implemented")
- Reconciliation's evidence hierarchy (ADR-024 rank 4) gains a concrete
  source for staging digests, previously assumed but unimplemented

## References

- ADR-001: Language as filesystem structure
- ADR-014: Filesystem-event-driven tooling model
- ADR-018: Universal assets directory convention
- ADR-021: Stable identity at creation
- ADR-022: Work assignment, expression joining, and the work index (v0.1.6)
- ADR-023: Metadata cataloging at content ingress
- ADR-024: Discovery and reconciliation (v0.2.2)
- ADR-025: Role-named assets directories, sparse inheritance, and the resolution order (v0.2.1)
- ADR-026: Full-chain creation, the instantiation preseed, and seeding (v0.2.3)
- ADR-027: Fixity (v0.1.3)
- `content-ingress-specification-v0.2.1.md`
- `en/lib/satlib/satlib/seed.py` — existing precedent this ADR ratifies

## Licence

Copyright (C) 2026 Christopher Steel

This file is part of SAT (Source Archive Tools).

SAT is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

SAT is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with SAT. If not, see <https://www.gnu.org/licenses/>.

This document was prepared with AI assistance from **Claude (Anthropic)**.

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.0 | Proposed | Initial draft. Ratifies the staging/ location and shape already implemented in seed.py; decides fixity-at-first-touch as a collection-level derived record (staging-fixity.yml); decides promotion is content ingress with an explicit --to destination, not a separate command, per the seeded lesson's own wording; flags the required content-ingress-specification amendment. |
