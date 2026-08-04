---
status: Accepted
date: 2026-07-14
version: 0.2.2
---

# ADR-024: Discovery and Reconciliation

## Context

Discovery — how SAT tooling locates the instance, collection, and archive a given path belongs to — currently works by position: the collection root is the nearest ancestor holding a language-archive child, the instance is the top of the walk. It works, and it breaks the moment users move things around. Rename an entity directory and its assets directory does not follow (ADR-018 names the assets directory after the entity, and names are mutable filesystem metadata). The pairing that every record placement depends on is silently severed by a plain `mv`.

This is the path-is-not-identity lesson (ADR-010, ADR-021) recurring one level down: records were made path-independent while the record container's name stayed path-coupled. ADR-014 named the required capability — recognizing a moved thing as the same thing — and called it reconciliation, but no mechanism was ever decided. satlib already carries the seed: `find_orphans()` detects assets directories whose entity is missing.

ADR-025 (role directories) and ADR-026 (full-chain creation) both stand on discovery. This ADR is numbered ahead of them because they cannot state their own behaviour efficiently without the understanding decided here.

## Decision

### 1. Discovery has two layers: declared, then reconciled

**Primary discovery is a read of declarations.** A folder's roles are exactly the role-named directories inside its correctly paired assets directory (ADR-025). For every tree nothing has disturbed, discovery is a pure read: no inference, no guessing, fast.

**Secondary discovery is reconciliation.** When the pairing is broken — an assets directory whose entity is gone, an entity with no assets — tooling enters reconciliation: it gathers evidence, proposes the repair, and never acts on its own. Position and other inference may inform *suggestions*; nothing ever *operates* on an inferred role. This is the suggest-never-assume rule (ADR-022) applied to the filesystem itself.

Both layers follow the integration doctrine's process form (controlled vocabulary, Gold): stdlib computes, standard formats express, sidecars record, proven tools verify — with findings returning to the operator. Reconciliation's entire mechanism is set arithmetic over sidecar reads: no watcher dependency for correctness, no database, no platform change-notification API. The ADR-014 watcher, when it arrives, is acceleration calling these same functions, never a correctness requirement.

### 2. Every role records its entity's name

Each role's `dc.yml` carries the entity's directory name:

```yaml
# .{name}.assets/collection/dc.yml
sat:name: henson-catalog
```

The name is mutable — renames are legitimate operator acts — so it lives in the mutable, operator-owned settings file and never in `identity.yml`, whose contract is write-once. Placement in the role directory aligns the record with the permission to change it: whoever owns the role directory owns both the rename authority and the record of the name (ADR-004). This also aligns with ADR-015: the name lives beside the DC sidecar its slug derives from.

The self-recorded name proves an orphan's past: `.en.assets/` saying `sat:name: en` establishes what the assets directory belonged to, whatever the filesystem now shows.

### 3. Every parent maintains a children index

The self-record alone cannot say which *current* directory claims a displaced lineage. The parent closes the triangle: each role directory carries a derived `children.yml` mapping child name to child identifier:

```yaml
# {collection}/.{collection}.assets/collection/children.yml
#
#   To update, delete and rebuild using:
#     collection children --rebuild
#
sat_version: "0.1"
generated: "2026-07-14T14:20:00Z"
generated_by:
  command: collection init
  version: "0.7.0"

children:
  en: urn:uuid:9be20d11-4c6f-4d02-8a4e-1f3b7c25d90a
  fr: urn:uuid:c17f4a92-6b3d-4e80-95ab-2e8d1c0a4f31
```

The children index follows the work index's exact contract: derived, disposable, generated-record header from the single satlib writer, sidecars canonical, staleness is the detection signal, rebuild is the remedy. The instance role indexes its collections; the collection role indexes its archives. (Documents inside archives are already indexed by the work index; a per-archive children index for content directories is deferred until a need appears.)

### 4. The evidence hierarchy

Reconciliation weighs evidence in fixed order, strongest first:

1. **Identity** — the orphan's `identity.yml` UUID. The reason ADR-021 exists: the one value that survives every move.
2. **Self-recorded name** — the orphan's `sat:name`, proving its past pairing.
3. **Parent expectation** — the children index entry for that identifier, proving what the parent last knew.
4. **Fixity digest** (ADR-027) — recorded content hashes. A digest survives copies and cross-filesystem moves, so it outranks filesystem metadata; it proves content sameness, not identity sameness (identical content legitimately exists in copies), so it corroborates rather than concludes. For uncataloged content — staging files with no identity yet — the digest is the best available evidence, which is why fixity is recorded at first touch.
5. **Filesystem metadata** — inode continuity, timestamps, adjacency of exactly one orphan and one unadorned candidate. Corroboration only, never a sole basis: inodes do not survive copies or cross-filesystem moves.

The real evidentiary boundary is not directory-versus-file but **cataloged versus not**: identity-bearing entities reconcile with confidence at any tier (for documents, the work index's `path` field plays the parent-expectation role, so a file rename is its existing stale-path finding with a re-pair proposal attached); identity-less content gets digest-grade suggestions at best, reported as `staging-unmatched` without a confident proposal. The mechanism is format-agnostic — it never opens the entity — and ADR-018's full-filename naming means an extension change (`guide.md` to `guide.markdown`) orphans assets exactly like any rename: same finding class, same repair, no special case.

A worked rename, `sat/en/` moved to `sat/english/`:

```text
FINDING orphaned-assets: .en.assets/ has no entity 'en'
  identity:        urn:uuid:9be20d11-…d90a
  self-record:     sat:name: en
  parent index:    en → urn:uuid:9be20d11-…d90a (stale)
  candidate:       english/ (unadorned, same parent)
PROPOSE: rename .en.assets/ to .english.assets/; update sat:name to english; rebuild children index
No changes were made (--dry-run). Pass --apply to reconcile.
```

Reconciliation is dry-run by default, narrated in full (automation narrates), and applied only by the operator. Ambiguity — two candidates, conflicting evidence — is reported as findings, never resolved by guess.

### 5. The findings grammar

Every finding, from reconciliation, fixity checking, or index verification, speaks one grammar:

- **classified** — a named kind from a fixed set (`orphaned-assets`, `stale-path`, `record-corruption`, `content-modified`, `staging-unmatched`, ...), so severity is knowable without prose and scripts can filter
- **what** — the observation, values shown, nothing yet interpreted
- **means** — the interpretation in plain language, honestly graded: a finding that is normal says so (`content-modified` on an edited document is staleness, not alarm — classification is what keeps the alarming findings alarming)
- **evidence** — which records support the claim, so the operator can check the checker
- **do** — the remedy as a runnable command, pasted not composed
- **severity** — hard or soft, with the closing line stating that no changes were made and a nonzero exit when findings exist

Verification never writes. The loop closes through the operator, always.

### 6. A safe rename verb

Plain `mv` remains legal forever; SAT adds the safe path so it is also the easy path. Each tier's CLI gains a `mv` subcommand:

```bash
collection mv <old> <new>
archive mv <old> <new>
```

that renames the entity and its assets directory as one act and maintains the records that reference them. The triangle is the same as the work index's: tooling maintains, humans may bypass, reconciliation repairs.

SAT never installs, aliases, or shadows a binary named `mv`. The safe verb is a tier subcommand behind the existing wrappers (ADR-016); the system's `mv` is untouched on every platform, always.

The verb's effects are exactly these, shown in the dry-run PLAN before anything is written (`--apply` to perform):

1. The entity and its `.assets` directory are renamed as one act.
2. `sat:name` in the entity's role `dc.yml` is updated to the new name.
3. The parent's `children.yml` is refreshed, stamping the acting command.
4. The work index is refreshed where paths changed — renaming an archive touches every expression path beneath it; renaming a collection touches none of its internal index entries.

Nothing else changes: no digest is recomputed (ADR-027 — paths change, digests never do), no identity is ever touched, no write-once record is rewritten, no content is opened.

Document and content-directory `mv` are deferred: they arrive later as thin wrappers over the same satlib functions, and until then a document renamed with plain `mv` is handled by the stale-path finding and reconciliation — the break-detect-repair path that must work forever anyway.

One principle governs regardless of which verbs exist: **a move between language archives is never a rename.** Language is filesystem structure (ADR-001), so moving `en/products/guide.md` into `fr/` would change the expression's language, not its path — a semantic act with one-expression-per-language consequences (ADR-022). The verbs refuse cross-archive moves, and reconciliation reads an expression found in a different archive as a language question for the operator, never as a rename candidate.

One operational note for implementers: a rename that crosses filesystems becomes a copy-and-delete underneath, which is where inode continuity dies. The evidence hierarchy already prices this in (filesystem metadata is corroboration only); the verb's implementation must simply not assume same-filesystem semantics.

### 7. find_orphans is promoted

`find_orphans()` graduates from utility to the entry point of secondary discovery: orphaned assets directories and unadorned entities are its output, the evidence hierarchy consumes them, and `sat reconcile` (or the tier-appropriate command) is the operator surface. Validation runs the same detection and reports unreconciled findings.

## Alternatives Considered

**Position-only discovery (status quo)** — rejected as the sole mechanism. It works until the first rename, then fails silently: records keep existing while nothing can find them. The failure mode is invisible, which is the worst kind.

**Declaration-only discovery, no reconciliation ("never infers from position")** — rejected. Under a pure read, a folder that lost its pairing is simply *nothing*: tooling cannot even say "this looks like a collection missing its declaration." Absolutism buys purity at the cost of every user who moves a directory — the opposite of including more people.

**Name recorded in `identity.yml`** — rejected. The name is mutable and identity is write-once; storing a mutable value in the immutable record breaks the contract that makes identity trustworthy.

**Inode tracking as primary evidence** — rejected. Inodes are filesystem-local: they do not survive copies, backups, or cross-filesystem moves, and some filesystems recycle them. Corroboration, never foundation.

**No children index (identity plus self-record only)** — rejected. Without the parent's expectation, reconciliation can prove what an orphan *was* but not detect that anything is missing from where it stood, and cannot distinguish a rename from a deletion-plus-unrelated-arrival. The third side of the triangle is what makes proposals confident.

**Mandatory tooling for renames (plain `mv` forbidden)** — rejected. SAT does not own the filesystem and must not pretend to; forbidding `mv` would be unenforceable theatre. The safe verb plus reconciliation is the honest design.

## Consequences

- Discovery is two-layered: declared read first, reconciliation second; nothing operates on inferred roles
- Each role's `dc.yml` gains `sat:name`; creation tooling writes it, the `mv` verb maintains it
- Each parent role directory gains a derived `children.yml` under the generated-record contract; creation, `mv`, and rebuild commands maintain it; staleness is a validation finding
- satlib gains the reconciliation machinery (evidence gathering, proposal generation) with `find_orphans()` as its entry point; tier CLIs gain `mv` and `reconcile` surfaces, dry-run by default
- ADR-014's reconciliation model receives its mechanism; ADR-021's identity records receive their headline use case
- ADR-025 and ADR-026 build on this ADR: role directories are what primary discovery reads; creation tooling writes the names and children indexes this ADR requires
- The controlled vocabulary gains *primary discovery*, *reconciliation*, *children index*, and the findings grammar's classification set
- Fixity digests (ADR-027) join the evidence hierarchy at rank 4; fixity at first touch is what gives uncataloged staging content any reconciliation evidence at all
- The manual testing guide for this round includes the worked rename: break the pairing with plain `mv`, watch reconciliation propose the repair, apply it

## References

- ADR-004: Self-replicating permission model
- ADR-005: Tool self-discovery from filesystem context
- ADR-010: Document identity and cross-language linking (v0.1.1)
- ADR-014: Filesystem event-driven tooling model
- ADR-015: Slug pattern language and sidecar-derived slugs
- ADR-018: Universal assets directory convention
- ADR-021: Stable identity at creation
- ADR-022: Work assignment, expression joining, and the work index
- ADR-025: Role-named assets directories, sparse inheritance, and the resolution order
- ADR-026: Full-chain creation, the instantiation preseed, and seeding
- ADR-027: Fixity
- Complete Filesystem Cascade: Goals (v0.2.0)
- SAT Controlled Vocabulary (Gold: the integration doctrine)

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
| 0.2.2 | Accepted | A safe rename verb updated for clarity and code readability via code block rather than in text code |
| 0.2.1 | Proposed | A safe rename verb section reworked for understanding |
| 0.2.0 | Proposed | Process resolved: integration doctrine pipeline cited as the mechanism's shape; fixity digests added to the evidence hierarchy at rank 4 with the cataloged-versus-uncataloged boundary stated; format agnosticism and the extension-rename case recorded; findings grammar added as decision 5 (classified, what, means, evidence, do, severity; verification never writes); subsequent decisions renumbered |
| 0.1.0 | Proposed | Initial draft: two-layer discovery (declared read, then reconciliation that suggests and never acts), sat:name in each role's dc.yml, derived children index per parent under the generated-record contract, fixed evidence hierarchy with filesystem metadata as corroboration only, safe mv verb per tier, find_orphans promoted to secondary discovery's entry point |
