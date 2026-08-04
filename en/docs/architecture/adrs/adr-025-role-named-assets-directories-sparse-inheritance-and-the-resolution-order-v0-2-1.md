---
status: Proposed
date: 2026-07-14
version: 0.2.1
---

# ADR-025: Role-Named Assets Directories, Sparse Inheritance, and the Resolution Order

## Context

A SAT directory can hold more than one tier of the cascade. SAT's own repository is the founding example: it is an instance and a collection in the same directory, with the `en/` archive at its root. Until now the collection role was inferred from position and the instance role from being the top of the walk. Nothing on disk declared either. Testing 0.6.0 surfaced the consequences: `collection init` demanded a preseed `sat init` never wrote, the work index landed in a `sat/` namespace that used the project's name where a tier's belonged, and "what declares the instance hat?" had no answer.

The organizing idea that resolves this already exists in the repository: the executable tree is organized by role — `bin/sat/`, `bin/collection/`, `bin/archives/`, `bin/content/`. This ADR applies the same idea to records, extends it to content organizing directories (which need metadata for cascade adjustments, identity for rename detection, and `sat:work` for directory translations), and settles where resources — logos, licences, style items — live and who may override them.

This ADR amends ADR-021 (flat record placement) and ADR-022 (the work index's `.assets/sat/` namespace). Both placements were correct in what they recorded and wrong only in where. How discovery locates role directories and reconciles them after filesystem changes is ADR-024's subject; this ADR defines what the directories declare and hold.

## Decision

### 1. Directory roles are declared with role-named .assets directories

A directory's roles are exactly the role-named directories inside its assets directory. For a SAT instance installed to a directory named `sat`, the assets directory looks like this:

```bash
sat/.sat.assets/sat/          # the instance's settings live here
```

The same pattern serves every role — inside a directory's assets, or beside a content file's:

```bash
# Directory roles
.<directory_name>.assets/sat/          # the instance role
.<directory_name>.assets/collection/   # the collection role
.<directory_name>.assets/archive/      # the archive role, in a
                                       #   language archive's assets
.<directory_name>.assets/content/      # the content role, in a content
                                       #   organizing directory's assets

# File role
.<file_name>.assets/content/           # the content role, in a
                                       #   document's assets
                                       #   (ADR-018 naming)
```

Content organizing directories — `products/`, `guides/` — carry the `content/` role, the same role documents carry, positionally disambiguated exactly as ADR-018 already distinguishes the two placements (assets inside a directory, beside a file). The tier is Content; its entities are documents and the directories that organize them; no fifth role name is minted. Enrolling these directories gives them settings for cascade adjustments (a per-directory author states it once), identity for rename and move detection (ADR-024's evidence hierarchy applies unchanged), and `sat:work` for directory translations: `products/` and `produits/` are two expressions of one work, so cross-language section correspondence is declared, never inferred.

How discovery locates role directories and reconciles them after filesystem changes is ADR-024's subject; this ADR defines only what the directories declare.

A directory that is both a SAT instance and a collection is a **dual-role directory**: it carries both role directories in one assets directory. SAT itself is the founding example:

```bash
sat/.sat.assets/sat/
sat/.sat.assets/collection/
```

A directory wearing one role — a collection created inside an existing instance, for example — is a **single-role directory** and carries only its own.

### 2. Each role directory holds that role's records

The uniform set per role: `identity.yml` (ADR-021), `provenance.yml` (ADR-020), and the role's Dublin Core metadata file, `dc.yml`.

Role-specific records join their role:

```bash
# Instance role
.sat.assets/sat/
  children.yml                # derived index of the instance's collections (ADR-024)

# Collection role
.my-collection.assets/collection/
  collection.yml              # the collection declaration (ADR-011, ADR-022)
  work-index.yml              # derived work lookup (ADR-022)
  children.yml                # derived index of the collection's archives (ADR-024)

# Archive role — archives are named by their language tag (ADR-001)
.en.assets/archive/
  language.yml                # the archive's language record (ADR-001, ADR-003)
  children.yml                # derived index of the archive's content directories (ADR-024)

# Content role, organizing directory
.products.assets/content/
  identity.yml                # dc:identifier and sat:work (ADR-010 v0.1.3)

# Content role, document — file assets keep the full filename (ADR-018)
.my-guide.md.assets/content/
  identity.yml                # dc:identifier and sat:work (ADR-010 v0.1.3)
  fixity.yml                  # recorded digest (ADR-027)
```

Every content entity — document or organizing directory — carries both `dc:identifier` and `sat:work`: one rule, lone-work by default, joinable (ADR-022). The document's descriptive record is its role's `dc.yml`, written by cataloging (ADR-023) and operator-owned thereafter — the same seeding pattern as every tier. The archive's `children.yml` is enrolled by this ADR: ADR-024 deferred it "until a need appears," and content directories carrying identity are that need.

A dual-role directory therefore carries two identities — one per role. That is the point: extraction is a pure move. Splitting a dual-role directory's collection out into its own directory takes its identity, its provenance, its settings, and its index with it. Nothing is re-minted; work index keys still resolve.

```text
sat/                                  ← instance AND collection: a dual-role directory
  .sat.assets/
    sat/
      identity.yml
      provenance.yml
      dc.yml                          ← instance settings: values live here
      children.yml
    collection/
      identity.yml
      provenance.yml
      dc.yml                          ← sparse: inherits unless overridden
      collection.yml
      work-index.yml
      children.yml
  en/
    .en.assets/
      archive/
        identity.yml
        provenance.yml
        dc.yml                        ← sparse
        language.yml
        children.yml
    products/
      .products.assets/
        content/
          identity.yml
          provenance.yml
          dc.yml                      ← sparse: e.g. a per-directory author
  fr/
```

### 3. Ownership is delegation

The role directory is the permission boundary (ADR-004). One ownership change on `.<directory_name>.assets/collection/` hands a collaborator the entire collection tier — its settings, its records, its resources (decision 5), and (paired with ownership of `bin/collection/`, per ADR-022's tier-permissions section) the operations that write them. The instance's role directory stays the instance operator's; defaults that cascade into other collections are protected by construction.

### 4. Sparse inheritance: every setting stated exactly once

A setting is written at the tier that decided it and nowhere else. Lower-tier `dc.yml` files ship nearly empty, carrying a template comment:

```yaml
# Settings flow down from the instance automatically.
# Only write something here if THIS tier needs a different answer.
```

An empty file means inherit; a stated value means this tier decided differently, on purpose. Because no value is ever stated twice, the stale-copy class of bug cannot occur, and any override stands out in a nearly-empty file as pure signal. `<calculated>` tripwires arm only at the tier that owns the question — the instance role at instantiation; an empty lower-tier file is inheriting, not unresolved.

### 5. Resources are cascade participants, inside the role

Resources — logos, licences, images, style items — live inside the providing role directory under a reserved `resources/` parent, organized by concern:

```bash
.sat.assets/sat/resources/imgs/logo.png          # the instance provides the official logo
.my-collection.assets/collection/resources/imgs/logo.png   # this collection overrides it
```

The relative path under `resources/` is the resource's identity across tiers: `resources/imgs/logo.png` at any tier is one resource, and resolution walks the tiers exactly as it does for fields — deepest-stated wins, absence inherits, sparse throughout. This is the pattern theme-override systems (Hugo, Sphinx) already prove; SAT borrows it rather than inventing one. The reserved `resources/` parent keeps concern names (`imgs/`, `licences/`) from ever colliding with future role-specific record names, and gives tooling one skip-rule word.

Two existing rules compose to answer "who wins," and no third rule is needed:

| | records (SAT's) | resources (operator's) |
| --- | --- | --- |
| between tiers | never cascade — each tier's own | cascade, deepest-permitted-stated wins |
| SAT versus operator | SAT writes, operator never | operator owns; SAT only seeds at creation |

Seeded resources (a default logo, ADR-026's samples) are written once at creation into the operator's space and are the operator's from that moment — exactly like the preseed-resolved `dc.yml`. Resources are carried by default (they travel with the assets directory through extraction and the safe `mv`), countable always (validation may report them without judging them), and catalogable by choice (a cataloged resource gains identity and fixity like any content; an uncataloged one is luggage, and luggage is not a defect). Resource *referencing* from content — and therefore link integrity across moves — is deferred, named work for the media round: resources are storage today, not linkable infrastructure, stated here so nothing builds on paths the safe `mv` does not yet maintain.

### 6. Resource policies: enforced or overridable, per descendant tier

Each providing role may carry a `policies.yml` — the operator's policy record, hand-edited, sparse — declaring, per resource, which descendant tiers may state their own version:

```yaml
# .sat.assets/sat/policies.yml — the instance operator's policy record
policies:
  - name: SAT Logo                 # human label, optional
    path: imgs/logo.png            # the resource key: relative path under resources/
    enforcement:                   # descendant tiers only; absent tier = overridable
      collection: overridable
      archive: enforced
      content: enforced
```

The controlled values are `enforced` and `overridable`, nothing else. Three rules govern:

1. **Enforcement controls who may state; resolution is otherwise untouched.** `enforced` at a tier means that tier may not state its own version; the resource still resolves as deepest-*permitted*-stated wins. In the example, a collection may override the logo; archives may not — so archives receive the collection's logo where one is stated, the instance's otherwise.
2. **Descendants may tighten, never loosen.** The effective grant at any tier is the most restrictive across all ancestors' policy records — ADR-004's same-or-fewer, governing files. A collection declaring `archive: overridable` under an instance's `archive: enforced` is void.
3. **Sparse throughout.** No `policies.yml`, no entry for a path, no tier in `enforcement:` — each means overridable. Only restrictions are ever written.

Enforcement is resolution-honored, never filesystem-prevented: nothing stops an operator from placing a shadowed file, and SAT does not pretend to own the filesystem. The resolver ignores the shadowing file and emits a soft finding in the ADR-024 grammar — `enforced-resource-shadowed`, naming the enforcing tier and its policy record, so the administrative conversation has an address.

### 7. The resolution order

The cascade's order is by tier, always. The walk gathers every tier's settings from the top down:

1. `.<instance_name>.assets/sat/dc.yml`
2. `.<instance_name>.assets/collection/dc.yml` (dual-role) or `.<collection_name>.assets/collection/dc.yml` (single-role)
3. `.<archive_name>.assets/archive/dc.yml`, where `language.yml` also injects the language fields
4. `.<directory_name>.assets/content/dc.yml` — each content organizing directory on the path, outermost first
5. The document's own `dc.yml`, and at ingress, transcribed frontmatter per the ADR-023 policy

The precedence: the deepest tier that states a value wins. Absence inherits; a stated value overrides deliberately; a `<calculated>` at the owning tier is a hole no shallower layer may cover — resolved or reported, never papered over. Resources resolve through the same walk using the relative path under `resources/` as the key, with enforcement (decision 6) pruning who may state.

```text
sat/sat/dc.yml                "CC BY-SA 4.0"        → candidate
sat/collection/dc.yml         (says nothing)        → inherit
fr archive archive/dc.yml     (says nothing)        → inherit
produits/ content/dc.yml      (says nothing)        → inherit
document dc.yml               "CC BY 4.0"           → deepest stated value: WINS
```

The document gets `CC BY 4.0`; every other document in the instance still gets `CC BY-SA 4.0`. One decision, one place, visible.

### 8. The stagger is by tier, not by directory depth

A dual-role directory contributes its `sat/` layer and then its `collection/` layer in that fixed order, exactly as if they were two directories. Single-role and dual-role topologies resolve identically because role directories, not directory boundaries, carry the tiers. Both are first-class: dual-role is the default and SAT's own shape; single-role collections are the growth shape for instances holding several. Discovery, resolution, work operations, and the index treat them identically.

### 9. Creation, mint triggers, and migration

Instance, collection, and archive role records are written at creation by their tier's tooling (ADR-026). Content organizing directories mint their records at first ingress into them — cataloging creates the chain of tier records it passes through — or by explicit `content init <directory>` for deliberate setup. A bare `mkdir` remains legal forever: a record-less content directory is `uncataloged-directory`, a soft finding in the ADR-024 grammar, pre-SAT rather than broken.

The 0.5.0 and 0.6.0 records migrate into role directories: flat `identity.yml`, `provenance.yml`, `dc.yml`, and `language.yml` into their tier's role directory; `.<collection_name>.assets/sat/work-index.yml` is deleted and rebuilt at `.<collection_name>.assets/collection/work-index.yml` — it is derived, so it migrates by regeneration. satlib provides a one-time migration with a dry-run-by-default CLI surface; the manual equivalent is documented. Pre-1.0 fix-forward: no compatibility shims, no dual-path readers.

## Alternatives Considered

**Instance role as positional inference (status quo)** — rejected. Position is honest but silent: it cannot be read from the directory itself, delegated, or carried through extraction. Declared roles make discovery a read, not a guess (ADR-024).

**A marker file instead of role directories** — rejected. A marker that could disagree with the records' placement is a silent-inconsistency generator; the role directory is simultaneously the declaration, the container, and the permission boundary — one mechanism, three jobs.

**Flat records with a shared dc.yml (ADR-021 status quo)** — rejected for multi-role directories. One flat settings file in a dual-role directory merges two cascade tiers into one file, makes extraction require a manual split, and cannot be delegated per tier.

**Flat dc.yml with optional role override** — rejected. Under delegation it degrades into per-role files asymmetrically, and a stale override silently shadowing a fresh flat edit is exactly the drift class sparse inheritance abolishes.

**A fifth role name for content organizing directories** — rejected. The tier is Content and `bin/content/` already serves documents and their directories; a `content-directory/` role would split one tier into two names for no payload. Positional disambiguation (assets inside versus beside) is already ADR-018's rule.

**Resources as a top-level stash beside the roles** — rejected. A stash outside the role directories is outside the cascade and outside the permission boundary: no inheritance, no override story, no delegation, and every future role name becomes a potential collision with someone's existing stash directory.

**Flat concern directories inside the role (`content/imgs/`)** — rejected in favour of the reserved `resources/` parent. Concern names would collide with future role-specific record names, and tooling would need a growing skip-list instead of one reserved word.

**A binary enforcement flag** — rejected in favour of per-descendant-tier grants. "Enforced for archives, overridable for collections" is a real administrative need the binary cannot express, and the per-tier mapping costs one YAML level.

**Filesystem-prevented enforcement** — rejected. POSIX cannot express "may not create a file of this name here," and pretending otherwise is unenforceable theatre. Resolution-honored enforcement with a narrated finding is the honest design, consistent with the safe-mv doctrine.

**Duplicated defaults in lower tiers (copy-down preseeds)** — rejected. Two copies of one fact is the definition of the drift problem; the cascade carries values down at read time.

**Role directories at the collection tier only** — rejected. Uniformity is the teaching win: one rule at every tier, and every tier needs the same extraction and delegation properties.

## Consequences

- ADR-021 is amended: identity and provenance records live in role directories; the write-once and refuse-if-present contracts are unchanged
- ADR-022 is amended: the work index lives at `.<collection_name>.assets/collection/work-index.yml`; its accepted text's `sat/identity.yml` example paths are patched to `content/identity.yml`; the work index admits directory expressions (the schema already fits: `languages:` keys, identifier and path per entry)
- ADR-024's archive-tier `children.yml` deferral is lifted: archives index their content directories
- Content organizing directories are content-tier entities: identity, provenance, sparse `dc.yml`, `sat:work`, reconcilable by ADR-024's hierarchy, translatable by ADR-022's join
- Resources live under `resources/` in the providing role, resolve by relative path with deepest-permitted-stated-wins, and are governed by sparse per-tier policy records; `enforced-resource-shadowed` and `uncataloged-directory` join the findings classification set
- satlib path changes in `identity.py`, `archive.py`, and `work.py`; the cascade resolver walks role-directory `dc.yml` files in the decision 7 order; a one-time migration moves existing records and rebuilds the index
- The instantiation preseed (ADR-026) resolves tripwires into `.<instance_name>.assets/sat/dc.yml`
- The controlled vocabulary gains *role directory*, *dual-role directory*, *single-role directory*, *sparse inheritance*, *resources*, *policy record*, *enforced*, and *overridable*; *co-located* and *nested* (as topology terms) retire to the retired-terms table
- Resource referencing from content is named, deferred work for the media round

## References

- ADR-001: Language as filesystem structure
- ADR-004: Self-replicating permission model
- ADR-010: Document identity and cross-language linking (v0.1.3)
- ADR-011: SAT collection model
- ADR-012: Conformant document schema (v0.1.1)
- ADR-018: Universal assets directory convention
- ADR-020: Controlled vocabulary and creation-event terminology
- ADR-021: Stable identity at creation (amended by this ADR)
- ADR-022: Work assignment, expression joining, and the work index (amended by this ADR)
- ADR-023: Metadata cataloging at content ingress (Proposed)
- ADR-024: Discovery and reconciliation
- ADR-026: Full-chain creation, the instantiation preseed, and seeding
- ADR-027: Fixity (Proposed)
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
| 0.2.1 | Accepted | Minor adjustments |
| 0.2.0 | Proposed | Full mint from review: decision 1 rewritten example-first with dual-role and single-role replacing the position terms; content organizing directories enrolled in the content role (identity, sparse dc.yml, sat:work for directory translations; archive children.yml deferral lifted; mint at first ingress or content init, uncataloged-directory soft finding); uniform record set settled with dc.yml as every role's descriptive record; role-specific records illustrated with concrete names; resources placed in-role under a reserved resources/ parent with relative-path identity, the two-rule who-wins matrix, and carried/countable/catalogable classes; per-descendant-tier resource policies (enforced or overridable, tighten-never-loosen, resolution-honored with the enforced-resource-shadowed finding); resolution order gains the content-directory layer and policy pruning; ADR-010 citation bumped to v0.1.3 with the executed supersession no longer restated |
| 0.1.0 | Proposed | Initial draft: roles declared by role-named assets directories, per-role record sets with two identities in dual-role directories, ownership as delegation, sparse inheritance, the five-layer resolution order with tier-not-depth stagger, both topologies first-class, one-time migration |
