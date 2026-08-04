---
status: Accepted
date: 2026-07-14
version: 0.2.3
---

# ADR-026: Full-Chain Creation, the Instantiation Preseed, and Seeding

## Context

The cascade was always described as each tier creating the setup for the tier below, but 0.6.0 testing found the chain broken at its first link: `collection init` demands a preseed file at `~/.config/sat/collection/collection-preseed.yml` that `sat init` never writes, and `collection init` accepts no path argument, so it cannot be told where to build. The error message documents an intention no code fulfils.

ADR-025 supplies the structural half of the fix: role directories and sparse inheritance make the filesystem itself the cascade, so no tier below the instance needs any file in `~/.config` at all. This ADR supplies the behavioural half: what `sat init` creates, what `collection init` becomes, what single file remains in userland, and what a new instance ships with.

One principle from the goals document governs the seeding decisions: a fresh install is a standing integration test. An instance that arrives with documentation, a test collection, and sample content staged for ingress proves the whole chain runs, on every machine, at every install.

## Decision

### 1. sat init runs the whole chain

`sat init` performs the complete cascade in one act: the instance role records, the dual-role collection role records (including `collection.yml`, per ADR-025), the language archives with their role records, the derived children indexes at every parent (ADR-024), and — because the seeded documentation tree contains content organizing directories — the content role records those directories carry (ADR-025 section 9: seeding is deliberate setup, so `sat init` mints them exactly as `content init` would). One command produces a working whole. Dry-run shows the full plan, as today.

```text
sat init --language en --language fr my-sat
PLAN: instantiate SAT instance at my-sat
  my-sat/.my-sat.assets/sat/          identity, provenance, dc, children (instance role)
  my-sat/.my-sat.assets/collection/   identity, provenance, dc (sparse), collection.yml, children (dual-role collection)
  my-sat/en/  my-sat/fr/              archives: identity, provenance, dc (sparse), language, children
  my-sat/en/docs/ ...                 seeded documentation, with content role records on its directories
  my-sat/collections/test-collection/ single-role example collection, in the standard collections home
  seeded: documentation, test-collection, staged samples (per preseed)
```

### 2. collection init creates single-role collections, by path

`collection init <path>` gains the path argument it lacks and creates an additional, single-role collection inside an existing instance: its collection role records, its declared archives, its children index, its sparse `dc.yml` inheriting through the cascade — and it refreshes the instance role's children index to record the new collection (ADR-024).

The standard home for single-role collections is a plain directory at the instance root whose name is configuration, not constant: `sat:collections_home` in the instance role's `dc.yml`, default `collections`, settable in the instantiation preseed. An instance operated in French, Spanish, or German names its container in its own language (`colecciones/`, `Sammlungen/`) — the instance root speaks the operator's language, per the golden rule. The setting belongs to the instance role specifically: the container organizes the instance's collections whether the root is dual-role or carries the sat role alone; the collection role never owns it. Tooling resolves the conventional parent through the setting and never assumes the English default; the children index already keys collections by relative path, so any name works unchanged. Renaming later is a documented two-step — edit the setting, rename the plain directory — followed by a children rebuild; the container has no records, so it is the cheapest rename in the system. With the default name, the home is `collections/`: the dual-role collection's own archives live at the root, and every other collection lives under one roof, so the root stays legible as the instance grows. `collections/` is organizational only — no role, no records; the cascade walks role directories, not filesystem depth, so the container is invisible to resolution, and the collections inside carry their own identity for reconciliation. The instance's children index keys collections by relative path (`collections/test-collection`), since bare names could collide across containers. The path argument remains free: `collection init` builds wherever it is pointed; `collections/` is the documented convention, not a constraint. The `~/.config` preseed dependency is removed entirely; the wizard remains for interactive use but reads its defaults through the cascade from the enclosing instance. The old error message and the file it demanded are retired.

### 3. Below the instance, the cascade is the only preseed

No tier below the instance reads `~/.config` for defaults. A collection's defaults are the instance's records resolved downward; an archive's are the collection's. Extracted instances are sovereign: everything a tier inherits travels inside the tree that contains it. The retired `collection-preseed.yml` mechanism is recorded in the controlled vocabulary's retired terms.

### 4. One userland file: the instantiation preseed

Exactly one preseed lives in userland: `~/.config/sat/instantiate-preseed.yml`, read by `sat init` alone. It answers, in advance, the questions instantiation would otherwise leave as `<calculated>` tripwires, plus the shape of the instance to create. Edited before the instance exists, in any text editor — the same idea Debian installers call preseeding.

```yaml
# ~/.config/sat/instantiate-preseed.yml
#
#   Edit this file BEFORE running sat init.
#   Every answer here arrives in the new instance already resolved,
#   in the instance role's settings: .<instance_name>.assets/sat/dc.yml
#
dc:creator: "Christopher Steel"
dc:publisher: "SAT – Source Archive Tools"
dc:rights: "CC BY-SA 4.0"
languages:
  - en
  - fr
collections_home: collections    # optional; the instance's collections directory name, in your language
seed:
  documentation: true
  sample_content: true
```

The preseed is a convenience door, never a requirement: absent, `sat init` behaves exactly as today — tripwires armed, resolved afterward in the instance role's `dc.yml`. Present, its answers land as resolved values and the `[unresolved: ...]` note simply does not appear. Command-line arguments override preseed values; the preseed overrides nothing after instantiation — it is read once, at creation, and the instance's own records are canonical from that moment.

### 5. Seeded documentation

A new instance ships SAT's user documentation as ordinary content in the dual-role collection's language archives — the shape the founding repository already has (`en/docs/`). SAT documents itself in SAT: the docs and their organizing directories participate in identity, the work index, and (when translated) `sat:work` joining like any other content (ADR-025). Translating the manual — documents and section directories alike — is ordinary translation work, not a separate system.

### 6. The test collection and staged samples

A new instance ships a single-role collection at `<collections_home>/test-collection/` (default `collections/test-collection/`): the playground, in the standard collections home. It holds one identified sample document per language — the end state, and the first `collection work join` target — and a `staging/` directory holding raw markdown files with frontmatter awaiting ingress: en and fr pairs, plus one deliberately misfiled document so the language finding (ADR-023) fires somewhere safe.

Samples are small, self-describing (their own frontmatter says they are samples), carry `CC BY-SA 4.0` matching the project, and every seeded element is removable in one documented command with a verification step. Seeded resources — a default logo, licence texts, style items — land under `resources/` in the providing role directory per ADR-025 section 5, written once at instantiation and the operator's from that moment. The example collection is not a preseed switch: it ships with every instance, because a playground included is more people included, and removal is one documented command for the operator who wants a bare tree. `documentation` and `sample_content` remain preseed switches; a switch for the example collection is a door this ADR leaves closed until a reason to open it appears.

Sequencing: the staged samples' full ingress lesson completes when cataloging (ADR-023) is implemented; this ADR stages the content and enables the join lesson now.

### 7. Every install is an integration test

The seeded instance exercises, on arrival: instantiation with the full role-record chain, sparse inheritance resolving through real tiers, the work index over real joined works in `test-collection/`, and — once cataloging lands — ingress over the staged samples. An install that completes is a chain that works; a seeded element that fails is a release finding.

## Alternatives Considered

**Honor the old message: sat init writes `~/.config/sat/collection/collection-preseed.yml`** — rejected. `~/.config` is machine configuration while instances are directories; one machine may hold many instances, and a single machine-level preseed cannot say which instance it belongs to. The ambiguity is structural, and the cascade already carries the same information without it.

**Mandatory instantiation preseed** — rejected. It would turn a convenience into a gate and break the current zero-configuration first run. Absent-file behaviour must remain today's behaviour exactly.

**Wizard-only collection creation (status quo interface)** — rejected as the sole interface. Interactive wizards cannot be scripted, tested, or documented as runnable code blocks; the path-argument form is the primary interface and the wizard becomes sugar over it.

**No seeding — bare instances only** — rejected. It discards the standing-integration-test property and hands every newcomer an empty room with no safe place to practice. The cost of seeding is bounded and removable; the cost of bareness is paid by every new operator.

**Pre-ingressed samples only, no staging directory** — rejected. Cataloged samples show the result but not the act; the staging directory is the ingress lesson, and it is the cheapest possible preparation for the ADR-023 round.

**Seeding as a post-init command instead of an init default** — considered and folded in rather than rejected: the preseed's `seed:` switches provide the opt-out, and a future `sat seed` command re-running the seeding idempotently is noted as a possible convenience, not required by this ADR.

## Consequences

- `sat init` creates the full chain: instance role, dual-role collection role, archives, children indexes, seeded content, and the content role records of seeded organizing directories, per the preseed
- `collection init <path>` is implemented, with the instance's collections home (`sat:collections_home`, default `collections`, preseed-settable, localizable) as the documented standard parent for single-role collections; the `~/.config` collection preseed and its error path are removed; the wizard reads through the cascade
- `~/.config/sat/` holds exactly one SAT preseed: `instantiate-preseed.yml`, optional, read once at instantiation, overridden by command-line arguments
- Retired: `collection-preseed.yml` and its `~/.config/sat/collection/` directory (recorded in the controlled vocabulary)
- Seeded: documentation in the dual-role collection and staged samples per their preseed switches; `collections/test-collection/` with every instance, unswitched; seeded resources under `resources/` in their providing roles; each element removable by one documented, verified command
- The manual testing guide for this round doubles as the seeded documentation's first pages — written once, shipped twice
- The install path becomes a standing integration test; seeding failures are release findings
- ADR-009's instantiation-by-instance path gains a defined configuration story: the instantiating instance supplies the answers the preseed would, from its own records

## References

- ADR-004: Self-replicating permission model
- ADR-009: Distribution by installer and instantiation
- ADR-011: SAT collection model
- ADR-020: Controlled vocabulary and creation-event terminology
- ADR-022: Work assignment, expression joining, and the work index
- ADR-023: Metadata cataloging at content ingress (Proposed — the staged samples' lesson completes with it)
- ADR-024: Discovery and reconciliation
- ADR-025: Role-named assets directories, sparse inheritance, and the resolution order
- Complete Filesystem Cascade: Goals (v0.2.0)
- Debian Project. (2024). *Appendix B. Automating the installation using preseeding*. Debian installation guide. https://www.debian.org/releases/stable/amd64/apb.en.html

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
| 0.2.3 | Accepted | The collections home name is configuration: sat:collections_home in the instance role's dc.yml, default collections, settable in the preseed, localizable per the golden rule; tooling resolves the parent through the setting; rename documented as setting-edit plus directory rename plus children rebuild |
| 0.2.2 | Proposed | The example collection ships with every instance and is not a preseed switch (removal remains one documented command); the seed: block retains documentation and sample_content only |
| 0.2.1 | Proposed | Standard collections home: single-role collections live under a plain collections/ directory at the instance root (organizational only — no role, no records, invisible to resolution); the seeded example becomes collections/test-collection/; the instance children index keys collections by relative path |
| 0.2.0 | Proposed | Aligned with accepted ADR-024 and ADR-025 v0.2.1: dual-role and single-role replace the position terms; sat init's chain gains the children indexes at every parent and the content role records of seeded documentation directories; collection init refreshes the instance's children index; seeded resources placed under resources/ in the providing role; preseed path in ADR-018 placeholder notation |
| 0.1.0 | Proposed | Initial draft: sat init runs the whole chain, collection init gains its path argument and loses the ~/.config dependency, cascade-as-preseed below the instance, the optional instantiation preseed with seed switches, seeded documentation and test collection with staged samples, install as standing integration test |
