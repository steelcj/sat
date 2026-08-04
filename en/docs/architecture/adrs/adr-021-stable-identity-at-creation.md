---
status: Accepted
date: 2026-07-12
---

# ADR-021: Stable Identity at Creation

## Context

Every SAT tier stands on its own. A SAT instance, a collection, or an archive can be moved, renamed, or pulled out and used somewhere else.

For SAT to adjust to these changes, each item needs a permanent ID — something that stays the same no matter where the thing goes.

A file path can't be that ID. Paths and directory structures may change over time in order to better represent the desired structure.

ADR-010 v0.1.1 solved this for documents: each document gets a `dc:identifier` with a UUID, stored in its sidecar, created at content ingress.

But nothing above the document tier has an ID yet. The SAT instance root, SAT collections, and SAT archives have descriptive records (`dc.yml`, `language.yml`) and a provenance record (`provenance.yml`), but no permanent ID.

A radar assessment from 2026-06-14 asked the question directly: what is the smallest identity record an archive needs at creation?

This ADR answers this question.

The practical reason is that in order to give SAT users (operators) full control over their collections and the archives those collections hold, they need the ability to move things around when this is required.

ADR-014 needs to recognize that a moved thing is still the same thing. Future tools will need to link instances, collections, and archives to each other when locations are changed. So both need an ID that doesn't depend on the location on the file system or path.

## Decision

### Every tier gets a permanent ID at creation

When an instance is instantiated, and when a collection or archive is created, it gets a universally unique identifier (UUID).

Documents already have this under ADR-010, so nothing changes for them.

### The ID is a `dc:identifier` field holding a UUID

```yaml
dc:identifier: urn:uuid:7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e
```

The format is the same one ADR-010 chose: UUID version 4, lowercase, with the `urn:uuid:` prefix from RFC 9562.

One format for every tier means one validator works everywhere.

All of ADR-010's rules for generating and checking UUIDs apply here without change.

Instances, collections, and archives do not get a `sat:work` field. That field links translations of the same document.

These tiers don't have translations. A `fr/` archive is not a French version of an `en/` archive — it is its own archive holding French-language content, with its own unique ID.

### The ID lives in its own file, `identity.yml`

Each instance, collection, and archive assets directory (ADR-018) gets an `identity.yml` holding the entity's ID and nothing else:

```text
.{name}.assets/
  identity.yml      ← this ADR: written at creation, never changed
  provenance.yml    ← ADR-020: written at creation, never changed
  dc.yml            ← the operator fills this one in
  language.yml      ← archive tier only
```

## How it works

We keep the ID in a separate file, not in `dc.yml`, for these reasons:

### Same rules at every tier

ADR-012 already puts document identity in an `identity.yml` file. With this ADR, one rule covers everything: identity lives in `identity.yml`. Learn it once, know it everywhere.

### Operator(s) file

`dc.yml` belongs to the operator — the tool tells you to open it and fill in the `<calculated>` blanks.

### SAT system files

`identity.yml` and `provenance.yml` belong to SAT and are created and controlled by SAT.

An ID must never be edited, so it cannot live in the file the operator is told to edit.

### The ID never changes

`identity.yml` follows the same contract as the provenance record: written once at creation, never touched again. The ID is not regenerated when the directory is copied, moved, or renamed. Creation tools refuse to build in a place that already has an `identity.yml`, just like they refuse a place with a `provenance.yml`.

If an archive or collection is split in two, the original keeps its ID and the new one gets a fresh ID. If two merge, the survivor keeps its ID. A retired ID can be saved in a `dc:identifier_retired` list, the same way ADR-010 handles it for documents.

### satlib owns the code

All the code for making, checking, reading, and writing IDs lives in satlib (ADR-019). The tier CLIs call satlib — none of them has its own UUID code. The rebuilt validation tool flags anything that is missing its ID or has a bad one.

## Alternatives Considered

**No IDs above the document tier** — rejected. Without a permanent ID, every link and every move-check depends on paths, and paths are allowed to change. It would also answer the radar question with "nothing," which doesn't square with tiers that claim to stand on their own.

**Put `dc:identifier` inside `dc.yml`** — rejected. That mixes an untouchable value into a file the operator is told to edit. It also breaks the match with ADR-012's separate identity file, and it makes the refuse-if-present rule impossible — that rule only works when the record is its own file.

**Put the ID inside `provenance.yml`** — rejected. Identity and provenance are different things — what something *is* versus how it *came to exist*. The radar assessment separated them on purpose; merging the files would mix them back together.

**Use `sat:identifier` instead of `dc:identifier`** — rejected. Dublin Core already has `dc:identifier` for exactly this job, and the project uses `dc:` fields wherever they fit. The `sat:` prefix is saved for ideas that only exist in SAT, like `sat:authority` and `sat:work`. A UUID is not one of those.

**UUID v7, ULID, NanoID, content hashes** — rejected. ADR-010 already worked through all of these and the reasons hold at every tier. They are not re-argued here.

## Consequences

- Instantiation writes `identity.yml` at the instance root; collection and archive creation write it in their assets directories
- Instances, collections, and archives created before this ADR have no `identity.yml`; the pre-1.0 fix-forward rule applies — validation flags them, and a one-time backfill gives existing directories their IDs
- `identity.yml` joins `provenance.yml` under the write-once, refuse-if-present contract
- satlib gains an identity module for generation, validation, and record read/write; every tier CLI uses it
- Validation flags missing or malformed IDs at every tier
- The radar assessment graduates: the smallest identity record is the descriptive records plus `identity.yml`
- Links between tiers and ADR-014 move detection get a path-independent key at every tier

## References

- ADR-004: Self-replicating permission model
- ADR-009: Distribution by installer and instantiation
- ADR-010: Document identity and cross-language linking (v0.1.1)
- ADR-012: Conformant document schema
- ADR-014: Filesystem event-driven tooling model
- ADR-018: Universal assets directory convention
- ADR-019: satlib as single source of truth with thin-tier CLIs
- ADR-020: Controlled vocabulary and creation-event terminology
- SAT Controlled Vocabulary (en/docs/language/controlled-vocabulary.md) — records the identity terms this ADR introduces (ADR-020 §6)
- Radar assess: Archive identity, provenance, and definition as distinct concerns (2026-06-14)
- Internet Engineering Task Force. (2024). *Universally unique identifiers (UUIDs)* (RFC 9562). https://www.rfc-editor.org/rfc/rfc9562

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
| 0.1.5 | Accepted | Add reference to the controlled vocabulary (ADR-020 §6), which now records this ADR's identity terms |
| 0.1.4 | Accepted | Grammar and vocabulary corrections; ownership punchline restored; fr/en example clarified; reformatted to web-ready markdown (one line per paragraph) |
| 0.1.1--0.1.3 | Adjustment | Rewording drafts for comprehension |
| 0.1.0 | Proposed | Initial draft |
