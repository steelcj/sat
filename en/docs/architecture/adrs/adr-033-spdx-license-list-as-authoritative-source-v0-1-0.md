---
status: Proposed
date: 2026-07-31
version: 0.1.0
---

# ADR-033: SPDX License List as Authoritative Source

**Numbering note:** provisional. Per house practice, confirm against
`ls en/docs/architecture/adrs/` before filing — 032 was the last
confirmed number as of this draft.

## Context

SAT uses SPDX license identifiers in every document's `dc:rights` field
(the separate uc-radar project's
`uc-radar/en/docs/references/reference--spdx-license-identifiers-v0-1-0.md`
already documents the split: `AGPL-3.0-or-later` for this repository's
own documents, `GPL-3.0-or-later` for downstream tooling code). There
is currently no local validation that an identifier used is real,
current, and correctly spelled. Two concrete, confirmed defects exist
because of this: `sat.yml` carries the vague, non-SPDX string
`"GPL v3"`, and `pyproject.toml` carries `GPL-3.0-only`, one version
narrower than the `-or-later` the reference doc calls for.

This is the same shape of problem ADR-003 already solved for language
tags: a short, structured identifier that must validate against an
external, versioned, authoritative list, or SAT either invents its own
lookup table (a maintenance burden, per ADR-003's own rejected
alternative) or ships nothing and lets typos like `sat.yml`'s stand
uncaught indefinitely.

The radar entry `uc-radar/en/docs/radar/adopt/spdx/spdx-license-list--
machine-readable-license-identifiers.md` (in the separate uc-radar
project, the canonical home for radar entries) has already evaluated
the SPDX License List against exactly this question and recommends
adoption at low risk: *"the integration pattern, download, cache
locally, check for updates periodically, is identical to what SAT
already does for language standards... no unknowns remain."* This ADR
ratifies that
recommendation as SAT's decision, the same relationship ADR-028 has to
its own radar entry.

## Decision

The SPDX License List is the single authoritative source for license
identifier validation in SAT. SAT does not define or maintain its own
list of valid license identifiers; it defers entirely to SPDX.

```text
https://github.com/spdx/license-list-data
```

The two files relevant to SAT are `licenses.json` (every license) and
`exceptions.json` (every license exception), both published as part of
the same versioned, GitHub-tagged release SAT already checks the IANA
registry against by the same pattern (ADR-003).

An identifier is valid in SAT if and only if it appears as a current,
non-deprecated identifier in the fetched `licenses.json`. A deprecated
identifier is not invalid — SPDX itself never removes retired
identifiers — but it is flagged, with the current replacement
identifier suggested where SPDX's data provides one.

This ADR does not design the caching mechanism, the CLI surface, or
the `licence-check`/`licence-apply` tools the radar entry sketches.
Those are implementation and specification work, following this ADR
the same way `content-ingress-specification` follows ADR-023 — a
companion document, not this decision record.

## Alternatives Considered

**SAT-maintained list of accepted identifiers** — rejected for the
same reason ADR-003 rejected a SAT-maintained language table: it
creates a maintenance burden, falls out of sync with the real
standard, and duplicates work a foundation-backed, ISO-standardised
list already does for the entire open-source ecosystem.

**No validation; rely on manual review** — rejected. This is the
status quo, and it has already produced two confirmed, live defects
(`sat.yml`, `pyproject.toml`) that manual review did not catch.

**Validate only at document-authoring time, not for `sat.yml`/
`pyproject.toml`** — rejected. Nothing about SPDX identifiers is
document-specific; the same validation applies wherever a `dc:rights`
or license-classifier field states one, tool configuration included.

## Consequences

- New or superseding SPDX license versions are automatically available
  to SAT without code changes, same benefit ADR-003 records for
  language tags
- A companion specification is needed to design the caching mechanism
  (a local `~/.config/sat/cache/` entry, parallel to the existing IANA
  registry cache), the CLI surface, and the `licence-check`/
  `licence-apply` tools the radar entry sketches — not designed here
- `sat.yml`'s `"GPL v3"` and `pyproject.toml`'s `GPL-3.0-only` remain
  known, confirmed defects until that tooling exists to catch them
  automatically; fixing them by hand in the meantime does not require
  waiting on this ADR
- Every document's `dc:rights` field gains a validation path it
  currently lacks entirely

## References

- ADR-003: IANA Language Subtag Registry as Authoritative Source
  (structural precedent this ADR mirrors)
- ADR-023: Metadata Cataloging at Content Ingress (`dc:rights` is a
  cataloging-policy field this validation would apply to)
- ADR-028: Dublin Core Namespace — `dc:` for MVP (same
  radar-entry-ratification relationship)
- Radar entry (adopted, uc-radar project): `uc-radar/en/docs/radar/
  adopt/spdx/spdx-license-list--machine-readable-license-identifiers.md`
- Radar entry (adopted, tool sketch, uc-radar project):
  `uc-radar/en/docs/radar/adopt/spdx/sat-licence-check-py.md`
- `uc-radar/en/docs/references/reference--spdx-license-identifiers-v0-1-0.md`
  (uc-radar project) — the AGPL/GPL split this ADR's validation would
  enforce
- `en/docs/specifications/dependency-licence-management.md` — adjacent,
  separate concern (third-party package licenses, not SAT's own)

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
| 0.1.0 | Proposed | Initial draft, modeled directly on ADR-003's structure and scope. Ratifies the already-adopted SPDX License List radar entry as SAT's decision. Deliberately narrow, same relationship ADR-003 has to its own offline-registry-cache specification: this ADR names the authoritative source only; caching mechanism, CLI surface, and the licence-check/licence-apply tools are companion work, not designed here. |
