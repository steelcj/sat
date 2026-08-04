---
status: Proposed
date: 2026-08-04
version: 0.1.0
---

# ADR-034: Operator-Side Concern Parents and the Derived Mapping Projection

## Context

The configuration-mapping effort (docs/design: goals, definitions-and-vocabulary, current mapping, payload maps) asked for a paths-and-files pattern allowing maximum, easy expansion — new metadata vocabularies, new formats, new tools, mirrored and unmirrored archives — and produced a pre-corpus recommendation with two central moves: reorganizing role directories into five lifecycle families, and an authoritative, versioned mapping manifest that tooling would resolve paths through.

Auditing that recommendation against the ADR corpus shows the house design has already settled most of this ground, in some places more precisely:

- **Concern parents exist and are *earned*, not preemptive.** ADR-025 §5 reserves `resources/` inside role directories; ADR-032 v0.1.1 nests the shipped floor's `dc.yml` under `defaults/<tier>/metadata/` — explicitly because `og.yml` and `schema.yml` are already-real siblings — while single-file concerns (`markdown.yml`) stay flat until growth is real. ADR-025 explicitly **rejected** flat concern directories inside the role ("concern names would collide with future role-specific record names, and tooling would need a growing skip-list instead of one reserved word").
- **Expansion-by-adding-a-file is the standing doctrine.** ADR-018: one assets directory "scales to new concerns by adding a file, not a convention." ADR-032: "a new feature adds a new named file to an existing, already-permission-scoped directory… no resolver change is required, per feature, ever again," with the file-or-directory escape hatch (`markdown.yml` ⇄ `markdown/github.yml`, one merged namespace — the Ansible `group_vars` pattern).
- **The filesystem is the declaration.** ADR-025 rejected a marker file because "a marker that could disagree with the records' placement is a silent-inconsistency generator; the role directory is simultaneously the declaration, the container, and the permission boundary." ADR-024 makes discovery "a read, not a guess."
- **The vocabulary swap is already anticipated.** ADR-028 fixes `dc:` for the MVP with `dcterms:` deferred and exceptions explicit; ADR-032 §5 makes the Dublin Core assumption expressible as a shipped-floor value (`sat:metadata_schema: dublin_core`), flagged as follow-on work.

Against that corpus, the pre-corpus recommendation's two moves resolve as follows. The **five-families reorganization is withdrawn**: it is the shape ADR-025 already considered and rejected, and the flat record set of ADR-025 §2 is ratified. The **authoritative mapping manifest is withdrawn**: it is ADR-025's rejected marker file at larger scale — a second declaration that can disagree with the filesystem it describes. What survives, sharpened by the corpus, is three genuinely open items, decided here.

## Decision

### 1. The operator-side `metadata/` concern parent — when it is earned

When a second descriptive-metadata file becomes real in operator space — an additional vocabulary (`mods.yml`), a per-vocabulary expansion (`dc/overrides.yml`), or operator-owned `og.yml`/`schema.yml` records — role directories gain a `metadata/` concern parent, symmetric with the shipped floor's (ADR-032 §1), under the same earned-not-preemptive rule:

```text
.<name>.assets/<role>/
  identity.yml            # unchanged, flat (ADR-021, ADR-025 §2)
  provenance.yml          # unchanged, flat
  dc.yml                  # unchanged, flat — TODAY, while it is the only metadata file
  …
  resources/…             # existing reserved parent (ADR-025 §5)
  metadata/               # SECOND reserved parent — created only when a second
    mods.yml              #   metadata file actually lands; dc.yml relocates to
    dc.yml                #   metadata/dc.yml in the same change, one migration
```

This amends ADR-025 §2 the way ADR-032 amended §7: the flat set stays ratified until the growth condition triggers; when it triggers, `metadata/` joins `resources/` as the second reserved word (one more skip-rule entry, not a growing list), and the file-or-directory escape hatch of ADR-032 §5 applies inside it unchanged. No other families are minted. Fixity, provenance, children, and the rest remain flat records: their names are stable, singular, and ADR-governed — the collision risk that earned `resources/` and `metadata/` their parents does not exist for them.

### 2. The canonical-vocabulary swap runs through the floor, not through filenames

The `canonical-metadata` concept from the design vocabulary is realized as ADR-032 §5 already sketches it: a shipped-floor value (`sat:metadata_schema`, exact field per implementation), resolved through the nine-layer walk like any other value, with `cataloging.py`'s Dublin Core assumption converted from hardcoded fact to read value (the ADR-032 follow-on, adopted here as committed work). ADR-028 governs the current value: `dc:` for MVP, `dcterms:` refinements explicit, per-field exceptions noted at the point of use.

Filenames do not interpolate. `dc.yml` remains `dc.yml`; a future vocabulary lands as its own file (`mods.yml`) beside it under `metadata/`, and `sat:metadata_schema` states which one is canonical. This keeps the swap **additive and reversible** — both records can coexist during a transition, which a renamed single file cannot do — and keeps every filename a stable, greppable fact rather than a computed one.

### 3. The mapping is projected, never declared: `sat config map`

The paths-and-files mapping remains declared by exactly what declares it today — the filesystem (ADR-018/-024/-025) and the ADR corpus — and becomes *visible* through a derived, read-only projection:

```text
sat config map [<path>]      # render the effective paths-and-files mapping
                             #   for the instance, or for one entity:
                             #   every record, its role directory, its floor
                             #   file, and the nine-layer walk that resolves it
```

The projection is in the derived, disposable class (`children.yml`, `work-index.yml`, ADR-022 §5): regenerated on demand, never authoritative, never cached — read-time like everything else (ADR-032 §3). It is the discoverability payoff the withdrawn manifest was after, with no second source of truth and no drift channel. It pairs with `sat defaults --diff` (ADR-032 §6) as the second member of a small family of read-only reports; like `--diff`, it is not gated behind `--apply` because it writes nothing.

Layout evolution needs no `mapping_version`: the layout's version *is* the ADR corpus, and layout changes ship as ADR amendments with one-time `sat migrate` moves, dry-run by default, pre-1.0 fix-forward with no dual-path readers (ADR-025 §9 precedent).

## Alternatives Considered

**Five lifecycle families at the role root (`metadata/`, `integrity/`, `structure/`, `policy/`, `derived/`)** — withdrawn. This is ADR-025's rejected "flat concern directories inside the role" with more members: five reserved words where the doctrine earns them one at a time, a reorganization of ratified flat records that carries migration cost with no resolver payoff, and a lifecycle partition already served by existing classes (write-once contracts per record ADR-021/-027; derived-disposable per ADR-022; operator policy per ADR-025 §6).

**An authoritative, versioned mapping manifest resolved by all tooling** — withdrawn. A declaration that can disagree with the filesystem is ADR-025's marker-file rejection at full scale; ADR-024 already makes the filesystem readable as the declaration. The manifest's real benefits split cleanly: discoverability → the derived projection (decision 3); evolvability → ADR + migrate (already precedented); validation → schema work against the ADR-defined layout, which needs no manifest to exist.

**Interpolated canonical filenames (`{canonical-metadata}.yml`)** — rejected. Computed filenames make the tree's most-read record un-greppable by name, break the additive-transition property (old and new vocabulary cannot coexist as one interpolated file), and buy nothing the `sat:metadata_schema` value does not already provide.

**Creating `metadata/` in role directories preemptively (today)** — rejected. ADR-032's own rule: a concern parent is earned by a real second file, not a hypothetical one. `dc.yml` alone does not earn it; the trigger and the relocation are specified (decision 1) so that when it is earned, the move is one decision already made.

## Consequences

- ADR-025 §2 gains a specified amendment trigger: the operator-side `metadata/` concern parent, created when a second metadata file lands, relocating `dc.yml` in the same migration; `resources/` + `metadata/` become the complete reserved-word set, and the skip rule stays two words long.
- ADR-032's `sat:metadata_schema` follow-on is adopted as committed work; ADR-028 remains the governing decision for the current value. The design vocabulary's `canonical-metadata` setting maps onto this mechanism rather than introducing a parallel one.
- New CLI surface: `sat config map` (name provisional), read-only, derived-class, paired with `sat defaults --diff`. Implementation is follow-on work, not performed under this ADR.
- The docs/design corpus requires a reconciliation pass against this ADR and the decisions it cites — specifically: media payloads live *inside* a file's assets directory (`.guide.md.assets/figure-1.svg`, ADR-018 §3–4), not as dot-file siblings; per-entity assets naming (`.test-collection.assets`, never a generic `.sat.assets` beside every node); "sidecar" reserved for the egress/transmog output sense (ADR-032's "three metadata sidecar types") now that ADR-018 has absorbed the root sidecars; and the retired topology terms (*co-located*, *nested*, per ADR-025's consequences) removed from the definitions document.
- Every expansion vector from the goals lands on an existing or here-decided mechanism: new vocabulary → `metadata/<vocab>.yml` + `sat:metadata_schema` (E1/E2); new format or tool → a named file in the shipped floor + its `bin/` tier (E3/E4, ADR-032 §5); mirrored/unmirrored archives → the archive role's `language.yml` relationship (E5); one-command spin-up → ADR-026, unchanged (G6).

## References

- ADR-018: Universal Assets Directory Convention (v0.1.1)
- ADR-021: Stable Identity at Creation
- ADR-024: Discovery and Reconciliation (v0.2.2)
- ADR-025: Role-Named Assets Directories, Sparse Inheritance, and the Resolution Order (v0.2.1) — §2 amended by this ADR's decision 1 trigger
- ADR-026: Full-Chain Creation, the Instantiation Preseed, and Seeding (v0.2.3)
- ADR-028: Dublin Core Namespace — dc: for MVP, dcterms: Deferred
- ADR-032: The Shipped Defaults Floor Below the Operator Cascade (v0.1.1) — §5's escape hatch and `sat:metadata_schema` adopted; `--diff` paired
- docs/design: *SAT Configuration Mapping — Goals*; *Definitions and Vocabulary*; *Payload Maps*
- Superseded: `docs/design/sat-configuration-paths-and-files-mapping-recommendation.md` (pre-corpus draft)

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
| 0.1.0 | Proposed | Minted from the post-corpus audit of the pre-corpus recommendation: five-families and authoritative manifest withdrawn against ADR-025's rejections; operator-side `metadata/` concern parent specified with its earned trigger; canonical swap routed through ADR-032 §5's `sat:metadata_schema`; derived `sat config map` projection replaces the manifest; docs/design reconciliation items enumerated. |
