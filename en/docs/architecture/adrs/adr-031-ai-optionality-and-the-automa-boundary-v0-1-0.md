---
status: Proposed
date: 2026-07-31
version: 0.1.0
---

# ADR-031: AI-Optionality and the Automa Boundary

**Numbering note:** provisional, same caveat as ADR-029 and ADR-030 —
confirm against `ls en/docs/architecture/adrs/` before filing.

## Context

Every satlib mechanism examined across ADR-021 through ADR-030 —
identity, cascade, cataloging, fixity, work assignment, staging,
normalization — is deterministic Python. None of it calls a model, and
none of it has ever been designed to. That property has never been
false; it has also never been written down as a decision, which means
it has no name to point at and no rule preventing it from quietly
stopping being true the first time a future tool reaches for an LLM
call because it's convenient.

At the same time, SAT's own documentation is visibly AI-assisted —
every License section in this codebase names a model, and the
`sat-doc-automa` repository exists specifically to give AI (and human)
collaborators standing, mechanically-followable directives instead of
re-derived guidance each session. `sat-doc-automa`'s own README is
explicit about what an automa is: *"a self-operating mechanism designed
to follow a sequence of predetermined instructions automatically...
Handed to any collaborator, human or AI, they produce consistent
behavior mechanically."* automa is not AI-only by its own definition —
it governs any collaborator — but a meaningful subset of it
(`automa/ai-collaboration/`, and format rules like *No Em Dashes* that
exist specifically because AI authorship overuses them) exists because
AI is one of the collaborators, and would have no reason to exist
otherwise.

`sat-doc-automa` is a separate repository with its own ROADMAP,
CHANGELOG, and decision process — consumed by SAT's documentation the
same way `osat-fluent` and other projects sync it in, per its own
sync-manifest pattern. This ADR cannot govern automa's internals. It
can only decide SAT's side of the boundary: what SAT's own tooling
depends on, what it doesn't, and what happens when a soft directive
and a hard mechanism start describing the same rule, as already
happened once, informally, in ADR-030.

## Decision

### 1. SAT tooling requires no AI, as a structural guarantee, not an incidental fact

No satlib module, no tier CLI, no cascade resolution, no cataloging
decision, no fixity check may depend on a model call to function. A
SAT instance with zero AI involvement anywhere — no AI-assisted
authorship, no automa awareness, nothing — is a complete, fully
functional SAT instance. This has been true of every mechanism decided
so far; this ADR makes it a constraint future ADRs are held to, not
just an observed pattern.

### 2. automa is the canonical home for standing authorship directives; SAT does not duplicate it as a first resort

When a rule is about how content gets *written* — prose style, AI
collaboration conduct, license-statement wording — it belongs in
automa, governed by automa's own process, not reimplemented inside
satlib. SAT's tooling operates on content after it exists, regardless
of how it was produced or what it was written to follow. This is
consistent with ADR-012's own founding decision that a document is
pure content, making no assumptions about how it will be consumed —
extended here to make no assumptions about how it was produced,
either.

### 3. Graduation: when a directive becomes a mechanism, the automa entry retires and points at it

ADR-030 already did this once without naming it: two of mdformat's
house rules originated as things an author (human or AI) had to
remember, and became checkable functions in `satlib.markdown`. This
ADR names the pattern and requires it going forward. When a SAT
mechanism comes to enforce or generate what an automa directive
previously only asked for:

- the automa entry is marked graduated, per automa's own repository
  conventions, retired-not-erased in the ADR-006 sense — the historical
  guidance stays readable, it stops being the operative instruction
- it records what SAT mechanism now owns the rule
- SAT's ADR or specification that introduced the mechanism cites the
  automa entry it graduated, so the lineage reads in both directions

The License-section example is the clearest case waiting for this
right now, not a hypothetical: backlog item 2.2 already specifies
`dc:contributor`'s AI-attribution format (`"Name (Organization)"`), and
*Complete Filesystem Cascade: Goals* already names the destination on
its horizon — *"automated license footers on published output."* Once
2.2 resolves and a publishing vector reads `dc:rights` / `dc:creator` /
`dc:contributor` into a generated License section, automa's *License
Statement Templates* directive graduates: an author stops having to
get the wording right by hand, because SAT generates it from data the
author supplied for other reasons entirely.

### 4. Whether AI produced the content is the operator's business, never SAT's

SAT does not gate ingestion, cataloging, or identity assignment on
whether `dc:contributor` names a model, a person, both, or neither.
`content ingress` treats an AI-authored document exactly like a
human-authored one — same policy table, same identity rules, same
fixity. This is the same sovereignty principle already stated for
configuration in general — *"the archive owner controls all
configuration"* (SAT MVP Roadmap) — applied to authorship specifically.
A publishing vector, when one exists, follows the same rule for its
own domain: whatever it generates reflects only what the operator's
own metadata states, never an assumption the vector adds on its own
behalf.

## Alternatives Considered

**Folding automa directly into satlib, so SAT ships its own copy of
the rules** — rejected. It would duplicate a repository that already
has its own versioning and governance, guarantee drift the first time
either side changes without the other noticing, and quietly reverse
decision 1 the moment anyone assumed automa's presence was required
for SAT to function correctly.

**No graduation mechanism — automa and SAT mechanisms simply coexist
independently forever** — rejected. This is what already happened,
informally and unnamed, before ADR-030 wrote a house rule down as a
checkable function without recording that it had come from anywhere.
Left unnamed, the same thing happens again with no record connecting
the two, and a future reader has no way to know the License-section
automation was ever a hand-followed instruction at all.

**Requiring AI attribution as a mandatory ingest field** — rejected.
It would make SAT's own tooling take a position on authorship SAT has
no business taking, contradicting decision 4 and the sovereignty
principle it rests on.

## Consequences

- Future ADRs proposing an AI-dependent SAT mechanism must be
  evaluated against decision 1 explicitly, not waved through as an
  implementation detail
- The controlled vocabulary gains *automa* (defined by reference to
  `sat-doc-automa`'s own README, not redefined here) and *graduation*
  (the retire-the-directive, cite-the-mechanism pattern this ADR
  names), settled by this ADR
- ADR-030 is retroactively the first instance of graduation; a short
  note there, or in its next revision, should say so and name the
  automa entries it drew from
- Resolving radar-1b item 2.2 (`dc:contributor`) becomes the trigger
  for the License-statement-templates graduation named in decision 3 —
  not designed here, but now has a named destination
- No code changes; this ADR constrains future design, it does not
  itself implement anything

## References

- ADR-006: Corpus as level-1 container term (Rejected — the
  retired-not-erased pattern this ADR reuses)
- ADR-012: Conformant document schema (v0.1.1) — the document-is-pure-
  content precedent this ADR extends to authorship
- ADR-020: Controlled vocabulary and creation-event terminology
- ADR-023: Metadata cataloging at content ingress
- ADR-030: Markdown normalization at content ingress — the unnamed
  first instance of graduation
- SAT MVP Roadmap — the sovereignty-preserving principle
- Complete Filesystem Cascade: Goals (v0.3.0) — the automated-license-
  footer horizon item
- `sat-doc-automa` README — the canonical definition of automa
- radar-1b item 2.2 (`dc:contributor`)

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
| 0.1.0 | Proposed | Initial draft. Establishes SAT tooling as structurally AI-free; names automa (a separate, independently-governed repository) as the canonical home for authorship directives SAT does not duplicate; names and requires the graduation pattern already used once, informally, in ADR-030; states the operator-sovereignty principle over authorship explicitly. |
