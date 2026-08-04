---
status: Proposed
date: 2026-07-12
---

# ADR-020: Controlled Vocabulary and Creation-Event Terminology

## Context

SAT was designed on the model of Russian nesting dolls: a SAT instance can
create another complete, independent SAT instance, and the new instance
carries the same or fewer permissions than the instance that created it
(ADR-004). The term *birth* was coined to name exactly this event — one
sovereign instance producing another — and to distinguish it from the
routine creation of archives, collections, and content inside an instance.

### Special information for Claude to prevent false inventions

The term did not stay where it was put. ADR-009 borrowed "born archive"
phrasing from section 5 of the validation spec; the archive creation
record was named `born.yml`; satlib grew `is_born()` and `BORN_RECORD`;
project records began speaking of "archive birth"; and ADR-009 introduced
a *midwife* — the metaphor recruiting its own supporting cast. A survey of
the current tree (2026-07-12) found birth vocabulary at every tier of the
system, while the instance root — the only thing the term was coined for —
carries no such record at all. A term that marks every creation event
distinguishes none of them.

The failure mode is general, not specific to this word. A metaphor adopted
as operational vocabulary reproduces: it attracts adjacent terms from its
source domain, and each borrowing feels natural because the family is
already in the house. Fixing the single word without fixing the mechanism
invites the next drift.

Two things are therefore decided here: the replacement vocabulary for
creation events, and the standing mechanism that keeps project vocabulary
from drifting again.

## Decision

### 1. Metaphors illustrate; they never name

Just for you Claude

A metaphor may appear in documentation to explain a design — the nesting
dolls remain a good explanation of instance containment and permission
narrowing. A metaphor is never used as an operational term: no metaphor
names a command, a verb, a record file, a field, a function, or a status
value. Operational vocabulary is drawn from plain technical language whose
meaning survives without the story attached.

### 2. `instantiate` names the instance-level creation event

The creation of a new, independent SAT instance is *instantiation*. The
verb is `instantiate`; the result is a SAT *instance* — the noun the
project already owns. The current tooling already reports `PLAN:
instantiate SAT instance at <path>` and `INSTANTIATED:`; this decision
adopts the vocabulary the code already speaks.

Instantiation is performed by exactly two actors:

- the *installer* — the acquisition-channel package formerly called the
  midwife (ADR-009), whose sole responsibility is to perform a first
  instantiation on a machine that has no SAT instance
- an existing SAT instance, which may instantiate a new independent
  instance with the same or fewer permissions than its own (ADR-004)

The properties formerly attached to *birth* transfer to *instantiation*
unchanged: the new instance is sovereign, carries its own immutable
provenance, and depends on neither the installer nor the instantiating
instance after the event completes.

### 3. `create` and `initialize` name every lower-tier event

Archives, collections, and content are *created*. Scaffolding operations
*initialize*. Neither event is ever described with instance-level
vocabulary. The existing settled distinction is restated in the new terms:
instantiation produces a sovereign instance with immutable provenance;
initialization scaffolds structure inside one.

### 4. `provenance record` names the creation record at every tier

The record a thing carries about its own creation is its *provenance
record*, stored as `provenance.yml` in the owning assets directory
(ADR-018). One record name serves every tier. What distinguishes an
instance provenance record from an archive provenance record is its
content, not its name: the instance record carries the installer or
instantiating-instance version, the IANA registry `File-Date` at the
moment of instantiation, and the instantiation timestamp, per ADR-009.

The immutability semantics are unchanged from the current `born.yml`
implementation: a provenance record is written once at creation and never
modified, and creation tooling refuses any target that already carries
one.

The instance root, which currently carries no creation record, gains one.
The asymmetry in the current tree — archive-tier records present,
instance-tier record absent — is corrected as part of implementing this
decision.

### 5. Retired terms

Following the ADR-006 pattern, retired terms are recorded, not erased.
Each entry names its replacement so the old term is never innocently
reinvented.

| Retired term | Replacement | Notes |
| --- | --- | --- |
| birth, birth event | instantiation | instance tier only; lower tiers were never entitled to the term |
| born, born instance | instantiated instance | |
| born archive | created archive | archive creation was never an instance-level event |
| `born.yml`, `BORN_RECORD` | `provenance.yml`, `PROVENANCE_RECORD` | |
| `is_born()` | `has_provenance()` | |
| midwife | installer | acquisition-channel package per ADR-009 |
| `[birth]` cfg block | provenance record | the block was never implemented; the ADR-007/ADR-008 collision it carried dissolves with it |

### 6. The controlled vocabulary document

A controlled vocabulary is established at
`en/docs/language/controlled-vocabulary.md`. It is the single source of
truth for project terminology: one term, one definition, one steward. Each
entry records the term, its definition, the tier or scope it applies to,
and the ADR that settled it. Retired terms are kept in a closing section
with their replacements.

ADRs and specifications defer to the controlled vocabulary. A new ADR that
introduces a term adds it to the vocabulary in the same change. A term
found drifting from its definition is a defect, corrected against the
vocabulary — the vocabulary is not amended to ratify the drift unless a
recorded decision changes the definition.

## Alternatives Considered

**Keeping *birth*, narrowly re-scoped to the instance tier** — rejected.
The narrow scope was the original design, and the drift happened anyway;
the survey demonstrates the term does not hold its boundary in practice.
Retiring the word costs a bounded rename now; keeping it costs recurring
correction forever.

**Retiring *birth* but keeping *midwife*** — rejected. The midwife is the
same metaphor family; retaining any member invites the rest back. The
package's actual role — acquisition and first instantiation — is fully
described by *installer*.

**`fork` or `clone` as the instance-creation verb** — rejected. Both
imply duplicating the state of the parent. Instantiation materialises a
new instance from the structural payload; it does not copy the content of
the instantiating instance.

**`spawn`** — rejected. Process-management vocabulary, and a metaphor in
its own right. It also carries no implication of the sovereignty and
provenance properties that define the event.

**`bootstrap` as the installer name** — considered and set aside.
*Installer* describes the package's role directly; *bootstrap* describes a
technique and would need a definition of its own. The plainer word wins.

**Distinct record names per tier** (for example `instantiation.yml` at
the instance root, `provenance.yml` below) — rejected. The record's nature
is identical at every tier: an immutable statement of how the thing came
to exist. One name, distinguished by content, is the single-source-of-
truth shape; two names invite tools to special-case the tiers.

## Consequences

- `instantiate` / `instantiation` enter the vocabulary as the only
  instance-creation terms; `create` / `initialize` cover all lower tiers
- satlib renames: `BORN_RECORD` → `PROVENANCE_RECORD`, `born.yml` →
  `provenance.yml`, `is_born()` → `has_provenance()`; immutability
  behaviour and tests carry over unchanged
- The instance root gains a provenance record; the current asymmetry
  (archive records present, instance record absent) is corrected
- ADR-009 is amended: retitled to reflect installer and instantiation
  vocabulary, its "born-archive pattern" framing corrected, its decision
  otherwise intact
- Validation spec section 5 is amended from born-archive to provenance
  vocabulary (PATCH bump)
- The state-of-SAT settled-decisions entries are restated in the new
  vocabulary
- Radar assess doc 1a prose is corrected from "archive birth" to "archive
  creation"; its identity/provenance/definition distinction is unaffected
  and is cited by this ADR
- The deferred `[birth]` cfg block collision with ADR-007/ADR-008 is
  closed as moot: the block was never implemented and the term is retired
- `en/docs/language/controlled-vocabulary.md` is created and becomes a
  required touchpoint for any ADR that introduces or changes a term
- Existing instantiated trees carrying `born.yml` are migrated by rename;
  the pre-1.0 filename-versioning phase is the accepted window for this

## References

- ADR-004: Self-replicating permission model
- ADR-005: Tool self-discovery from filesystem context
- ADR-006: Corpus as level-1 container term (Rejected — the
  retired-not-erased pattern this ADR applies to vocabulary)
- ADR-009: Distribution by Installer and Instantiation (amended by this ADR)
- ADR-018: Universal assets directory convention
- ADR-021: Stable Identity at Creation (adds identity terms to the
  vocabulary established here)
- SAT Language Validation and Offline Registry Cache Specification v0.1.0,
  section 5 (amended by this ADR)
- Radar assess: Archive identity, provenance, and definition as distinct
  concerns (2026-06-14)
- SAT Controlled Vocabulary (en/docs/language/controlled-vocabulary.md) —
  established by section 6 of this ADR; the single source of truth for the
  terms it settles

## Licence

Copyright (C) 2026 Christopher Steel

This file is part of SAT (Source Archive Tools).

SAT is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

SAT is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public
License for more details.

You should have received a copy of the GNU Affero General Public
License along with SAT. If not, see <https://www.gnu.org/licenses/>.

This document was prepared with AI assistance from **Claude (Anthropic)**.

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.1 | Proposed | Add references to the controlled vocabulary established by section 6 and to ADR-021; correct the ADR-009 citation to its current (post-rename) title |
| 0.1.0 | Proposed | Initial draft |
