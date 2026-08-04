---
dc:title: "SAT Configuration Mapping — Goals"
dc:description: "The goals of the SAT configuration mapping effort: gather the current configuration, standardize locations via a repeatable pattern, define a forward-looking design pattern optimized for layering, onboarding, and safety, enable quick instantiation of a working SAT, and keep the layout extensible for new metadata, formats, libraries, and languages."
dc:creator: "Christopher Steel"
dc:contributor: "Claude Opus 4.8 (Anthropic)"
dc:publisher: "Christopher Steel"
dc:date: "2026-08-04"
dc:modified: "2026-08-04"
dc:type: "Text"
dc:format: "text/markdown"
dc:language: "en"
dc:language_bcp47: "en"
dc:rights: "https://creativecommons.org/licenses/by-sa/4.0/"
dc:subject:
  - SAT
  - configuration
  - goals
  - mapping
  - design pattern
  - extensibility
  - instantiation
dc:identifier: "sat-configuration-goals"
---

# SAT Configuration Mapping — Goals

The goals guiding this effort: map how SAT is configured today, design a more effective forward-looking pattern for where its configuration lives, and keep that pattern open to expansion.

---

## 1. Purpose

SAT (Source Archive Tools) is a filesystem-first framework whose behaviour is driven entirely by on-disk configuration. This effort has a single purpose: to **map SAT's current configuration completely**, to **define a repeatable, forward-looking pattern** for configuration paths and files, and to ensure that pattern **remains extensible** — so that configuring SAT becomes standard, discoverable, safe, and open to growth.

---

## 2. Primary goals

The original goals of the mapping, restated and sharpened:

- **G1 — Gather the current configuration.** Collect every configuration file SAT currently reads or produces, into one complete map.
- **G2 — Standardize locations with a repeatable pattern.** Establish standard configuration locations governed by a single, repeatable rule rather than case-by-case placement. (The repeatable rule is standing doctrine: [ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md)'s universal assets-directory convention and [ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md)'s role-named directories and resolution order.)
- **G3 — Make SAT easier to configure.** Reduce the effort and uncertainty of configuring SAT, for both new and experienced operators.
- **G4 — Uncover better design patterns.** Identify configuration-design patterns that improve on the current arrangement.
- **G5 — Define the desired pattern.** Produce a target design pattern for mapping configuration paths and files — the "perfect" future map.
- **G6 — Spin up a working SAT quickly.** A user should be able to instantiate a complete, working SAT with minimal effort ([ADR-026](../architecture/adrs/adr-026-full-chain-creation-the-instantiation-preseed-and-seeding-v0-2-3.md): `sat init` runs the whole chain) — a SAT instance, a collection, and one or more language archives — where each archive serves its content from the language root's documents directory, `<language-root>/docs` (e.g. `en/docs`):
  - **Language root** — the top-level language directory of a language archive (e.g. `en`, `fr`).
  - **Documents directory (`docs`)** — the standard content location within a language root: `<language-root>/docs`.

---

## 3. Quality goals (what the target pattern optimizes for)

SAT is a framework/platform, so the target pattern is judged against three qualities:

- **Q1 — Clearer layering.** Configuration should resolve through an explicit, predictable cascade (sparse records, deepest-stated-value-wins), so it is always clear which value applies and why.
- **Q2 — Easier onboarding.** A newcomer should be able to answer "where does this setting live, and what applies to this node?" from a small number of consistent rules.
- **Q3 — Validation & safety.** The design should support catching bad configuration early and protecting canonical, write-once records — favouring safety over silent failure.

---

## 4. Extensibility goals (what the pattern must grow to accommodate)

The pattern must absorb new capabilities by **extension** — adding a definition or an entry — never by restructuring. It should accommodate:

- **E1 — Swappable canonical metadata.** Changing the `canonical-metadata` setting to a different vocabulary (e.g. MODS, MARC, Schema.org, or a custom scheme) must require no change to the layout, carriers, or metadata directory. This rests on the standing invariant that *vocabulary is independent of storage*. (Decided: the swap runs through the shipped-defaults floor's `sat:metadata_schema` value, not through filenames — [ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md) §5, [ADR-034](../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md) decision 2; [ADR-028](../architecture/adrs/adr-028--dublin-core-namespace-dc--for-mvp-dcterms--deferred.md) governs the current value: `dc:` for the MVP, `dcterms:` deferred.)
- **E2 — Additional metadata types.** Accommodate new metadata kinds or additional vocabularies alongside the canonical one (e.g. a secondary descriptive standard, or a new record kind) without reworking the pattern. (An additional vocabulary lands as its own file beside the canonical one — [ADR-034](../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md) decisions 1–2, using [ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md) §5's file-or-directory pattern.)
- **E3 — Additional document formats.** Support content formats beyond Markdown — with their own content profiles, specs, and publication targets — by adding definitions, not by changing the pattern.
- **E4 — Additional libraries, tools, and configurations.** New tool groups or libraries introduce their own definitions into standard locations and are absorbed by the pattern without bespoke placement.
- **E5 — Mirrored and unmirrored language archives.** Support adding both kinds of language archive, and new languages, within the same repeatable pattern:
  - **Unmirrored (independent) language archive** — a language archive that stands alone, with its own structure and content (current `language.relationship: independent`).
  - **Mirrored language archive** — a language archive whose structure, and optionally content, parallels another language archive and is kept in correspondence (e.g. a translation set).

  Both kinds are declared by the archive role's `language.yml` relationship record — see [ADR-034](../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md), Consequences.

---

## 5. Success criteria

We will consider the effort successful when:

- Every configuration file SAT produces is accounted for in a single current map. *(G1)*
- A newcomer can locate any configuration by kind alone, using one repeatable rule. *(G2, Q2)*
- The target pattern expresses every payload's home by *scope*, *kind*, and *carrier* without exception. *(G5)*
- Layering is explicit end-to-end: any effective value can be traced to the layer that set it. *(Q1)*
- Canonical records have a defined immutability and a path to validation. *(Q3)*
- Changing the canonical-metadata vocabulary requires zero changes to layout or carriers. *(E1)*
- New metadata types, document formats, libraries, and languages are added by adding definitions or entries — never by reworking the pattern. *(E2–E5)*
- Both mirrored and unmirrored language archives fit the same pattern. *(E5)*
- From nothing, a single standard flow produces a working instance, a collection, and one or more language archives, each serving content from `<language-root>/docs`. *(G6)*
- A shared vocabulary lets all of the above be described unambiguously. *(supports all)*

---

## 6. Non-goals

To keep the effort focused, this work does **not**:

- Decide final file or directory names (naming is deferred until the pattern is agreed).
- Produce an implementation or migration plan, or change SAT's tooling.
- Refactor `satlib` or any tool's code.
- Enumerate every possible metadata standard, document format, or language now — only ensure the pattern can accommodate them.
- Prescribe a single layout for all situations — the target pattern allows profiles for different purposes (development, distribution, archival).

---

## 7. How the documents serve the goals

The document set produced during this effort maps to the goals as follows:

| Document | Goals served |
|----------|--------------|
| *Definitions and Vocabulary* | Shared language — foundation for all goals; encodes the invariants behind E1–E2 |
| *Current Mapping* | G1 (gather), baseline for G2/G4 |
| *Assets* (carriers: sidecar vs parallel tree) | Vocabulary for G2, G4 |
| *Payload Maps* (future-forward) | G2, G4, G5 + Q1–Q3; profiles support E-series growth |
| *Current Mapping & Future Pattern — Overview* | G4, G5 (friction and future patterns) |

---

## 8. Guiding principle

One sentence to hold it all: **every piece of SAT configuration should have an obvious, repeatable home — described by its scope, kind, and carrier — that layers predictably, is easy to find, is safe by default, spins up a working SAT with little effort, and grows by extension: new metadata types, formats, libraries, and languages are added, never bolted on.**
