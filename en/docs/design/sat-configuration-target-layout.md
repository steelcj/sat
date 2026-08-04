---
dc:title: "SAT Configuration Paths and Files — Target Layout"
dc:description: "A tree-style mapping of SAT configuration paths and files under the target pattern: per-entity assets directories in-tree, media inside the file's assets directory, a derived read-only projection, and quick instantiation with <language-root>/docs content."
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
  - target layout
  - paths and files
  - assets
dc:identifier: "sat-configuration-target-layout"
---

# SAT Configuration Paths and Files — Target Layout

> **Authority.** Where this layout conflicts with
> [ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md),
> [ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md),
> [ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md), or
> [ADR-034](../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md),
> the ADRs are authoritative and this document is superseded on the point of conflict.

## Description

A tree-style mapping of SAT configuration paths and files, rendered under the **target pattern** — the successor to the original `satconfigurationpathsandfilesmapping.md`. It shows where each payload lives by *scope*, *kind*, and *carrier*, using the profile **In-tree source, derived projection**.

## Goals (recap)

Standard, repeatable locations; easy to configure; complete coverage; safe by default; quick to spin up; and extensible. Full detail in *SAT Configuration Mapping — Goals*.

## Conventions

- **Illustrative entities, real conventions.** Entity names (`test-collection`, `guide.md`) are illustrative; the conventions they demonstrate are decided. Assets-directory names follow ADR-018's literal per-entity transform (`.<name>.assets`): `sat/` → `.sat.assets/`, `test-collection/` → `.test-collection.assets/`, `guide.md` → `.guide.md.assets/`. Record names (`dc.yml`, `identity.yml`, …) are stable, greppable, ADR-governed facts — never computed.
- **Carrier.** Working records use **in-tree assets directories** — each entity's own `.<name>.assets/` directory, placed *inside* the directory it describes and *beside* the file it describes (ADR-018 §3). Content-media live **inside the file's assets directory**, never as dot-file siblings. The effective mapping is made *visible* by a **derived projection** — the read-only `sat config map` report (ADR-034) — and declared by nothing but the filesystem and the ADR corpus.
- **Canonical metadata record.** `dc.yml`, and it stays `dc.yml`: filenames do not interpolate (ADR-034). Which vocabulary is canonical is stated by the shipped-floor value `sat:metadata_schema` (ADR-032 §5); a future vocabulary lands as its own file beside it, additively.
- **Scope subdirectory.** A node's assets directory holds one role subdirectory per role it bears (two at the dual-role root), each holding that role's flat record set (ADR-025 §2).

---

## Full layout

```text
sat/                                     # SAT instance root — dual-role (sat + collection)   [sat_root: sat]
├── .sat.assets/                         # the instance's assets directory — inside it (ADR-018;
│   │                                    #   the entity is literally named "sat")
│   ├── sat/                             # sat-scope records — flat set (ADR-025 §2)
│   │   ├── identity.yml
│   │   ├── provenance.yml
│   │   ├── dc.yml                       # canonical metadata record — named dc.yml (ADR-034)
│   │   ├── children.yml
│   │   └── resources/                   # reserved parent (ADR-025 §5) — e.g. resources/imgs/logo.png
│   └── collection/                      # collection-scope records (dual-role root)
│       ├── identity.yml
│       ├── provenance.yml
│       ├── dc.yml
│       ├── collection.yml
│       ├── work-index.yml
│       └── children.yml
├── bin/                                 # configuration inputs — definitions + floor (tooling)
│   ├── sat/
│   │   └── defaults/                    # shipped defaults floor (ADR-032 §1) — SAT's opinion,
│   │       │                            #   never delegated; ADR-032 writes this location as
│   │       │                            #   en/bin/sat/defaults/ in SAT's own tree
│   │       ├── sat/
│   │       │   └── metadata/
│   │       │       └── dc.yml           # shipped opinion for the sat tier
│   │       ├── collection/
│   │       │   └── metadata/
│   │       │       └── dc.yml
│   │       ├── archive/
│   │       │   └── metadata/
│   │       │       └── dc.yml
│   │       └── content/
│   │           ├── metadata/
│   │           │   └── dc.yml
│   │           └── markdown.yml         # single-file concern stays flat (ADR-032 §5)
│   └── …                                # archives/ collection/ content/ transmog/ definitions
└── collections/                         # [collections_root: collections]
    └── test-collection/                 # a collection
        ├── .test-collection.assets/     # per-entity name (ADR-018) — inside the directory
        │   └── collection/
        │       ├── identity.yml
        │       ├── provenance.yml
        │       ├── dc.yml
        │       ├── collection.yml
        │       ├── work-index.yml
        │       └── children.yml
        ├── en/                          # language archive — language root "en" — UNMIRRORED (independent)
        │   ├── .en.assets/
        │   │   └── archive/
        │   │       ├── identity.yml
        │   │       ├── provenance.yml
        │   │       ├── dc.yml
        │   │       ├── language.yml     # relationship: independent
        │   │       └── children.yml
        │   └── docs/                    # <language-root>/docs — content lives here   [documents_root: docs]
        │       ├── .docs.assets/
        │       │   └── content/         # content-directory-scope records for docs/
        │       │       ├── identity.yml
        │       │       ├── provenance.yml
        │       │       └── dc.yml
        │       ├── index.md             # body payload
        │       ├── .index.md.assets/    # the file's assets — beside it (ADR-018)
        │       │   └── content/
        │       │       ├── identity.yml
        │       │       ├── provenance.yml
        │       │       ├── dc.yml       # document metadata — seeded by cataloging, operator-owned (ADR-023)
        │       │       └── fixity.yml   # recorded digest (ADR-027)
        │       ├── guide.md             # body payload
        │       └── .guide.md.assets/
        │           ├── content/
        │           │   ├── identity.yml
        │           │   ├── provenance.yml
        │           │   ├── dc.yml
        │           │   └── fixity.yml
        │           └── hero.png         # content-media payload — inside the file's assets
        │                                #   directory, never a dot-file sibling (ADR-018 §3–4)
        └── fr/                          # language archive — language root "fr" — MIRRORED (mirrors en)
            ├── .fr.assets/
            │   └── archive/
            │       ├── identity.yml
            │       ├── provenance.yml
            │       ├── dc.yml
            │       ├── language.yml     # relationship: mirrored; mirrors: en
            │       └── children.yml
            └── docs/                    # mirrors en/docs structure
                ├── .docs.assets/
                │   └── content/ …
                ├── index.md
                ├── .index.md.assets/ …
                ├── guide.md
                └── .guide.md.assets/ …
```

> **Not today — the earned `metadata/` parent (ADR-034 decision 1).** Each role's `dc.yml` above sits flat, and stays flat while it is the only metadata file in operator space. When a second operator-side metadata file becomes real (`mods.yml`, operator-owned `og.yml`/`schema.yml`, …), the role directory gains a `metadata/` concern parent — symmetric with the shipped floor's — and `dc.yml` relocates to `metadata/dc.yml` in the same migration. `resources/` and (then) `metadata/` are the complete reserved-word set; no other families are minted.

### Resolution order — nine layers (ADR-025 §7, amended by ADR-032 §2)

Each tier's shipped-floor file is read immediately before that tier's operator layer:

```text
0a. bin/sat/defaults/sat/metadata/dc.yml          SAT's shipped opinion
1.  .sat.assets/sat/dc.yml                        operator's instance override

0b. bin/sat/defaults/collection/metadata/dc.yml   SAT's shipped opinion
2.  .<name>.assets/collection/dc.yml              operator's override

0c. bin/sat/defaults/archive/metadata/dc.yml      SAT's shipped opinion
3.  .<lang>.assets/archive/dc.yml                 operator's override; language.yml injects
                                                  the language fields

0d. bin/sat/defaults/content/metadata/dc.yml      SAT's shipped opinion
4.  .<dir>.assets/content/dc.yml                  operator's override, per content organizing
                                                  directory on the path, outermost first

5.  the document's own dc.yml                     .<file>.assets/content/dc.yml — or transcribed
                                                  frontmatter at ingress (ADR-023)
```

Precedence: the deepest tier that states a value wins; absence inherits; the shipped floor is simply the outermost candidate. The stagger is by tier, not directory depth (ADR-025 §8): the dual-role root contributes its `sat/` layer and then its `collection/` layer in that fixed order. Everything resolves read-time, never cached (ADR-032 §3).

### Derived projection — `sat config map` (ADR-034)

```text
sat config map [<path>]                  # render the effective paths-and-files mapping for
                                         #   the instance, or for one entity: every record,
                                         #   its role directory, its floor file, and the
                                         #   nine-layer walk that resolves it
                                         # derived, read-only, regenerated on demand —
                                         #   never authoritative, never cached
```

### Operator configuration inputs

```text
~/.config/sat/                           # operator configuration inputs
├── sat-preseed.yml                      # instance + collections topology
├── collection/collection-preseed.yml
├── instantiate-preseed.yml             # whole-chain instantiation seed (G6)
├── .meta/sat-meta.yml                   # metadata preseed — resolved into the instance-tier
│                                        #   dc.yml at instantiation (ADR-026)
└── cache/iana-registry.txt              # lookup cache (staleness policy)
```

---

## Walkthrough

### sat/

The instance root. Dual-role: it is both the **sat** scope and a **collection** scope, so its assets directory holds two role subdirectories. The record set per role is flat (ADR-025 §2), with `resources/` as the reserved concern parent.

```yaml
# sat/.sat.assets/sat/            (sat-scope records — flat, ADR-025 §2)
identity.yml
provenance.yml
dc.yml            # canonical metadata record
children.yml
resources/        # reserved parent (ADR-025 §5) — logos, licences, style items

# sat/.sat.assets/collection/     (collection-scope records — dual-role)
identity.yml
provenance.yml
dc.yml
collection.yml
work-index.yml
children.yml
```

### bin/sat/defaults/  (shipped defaults floor)

SAT's own opinions, shipped with the code, one directory per cascade tier, each tier's `dc.yml` under a `metadata/` concern folder (ADR-032 §1). Never delegated: the floor lives under `bin/sat/`, the one tier ADR-004 never hands out. The floor resolves like every other layer — read at read time, never cached — and `sat defaults --diff` reports, read-only, what a shipped change would newly affect (ADR-032 §6).

### collections/test-collection/

A collection node. Its assets directory — `.test-collection.assets/`, the per-entity transform of its own name — holds the **collection**-scope records, sparse and cascading from the instance.

```yaml
# collections/test-collection/.test-collection.assets/collection/
identity.yml
provenance.yml
dc.yml
collection.yml
work-index.yml
children.yml
```

### collections/test-collection/en/  (unmirrored language archive)

A language archive rooted at language root `en`; **independent** (unmirrored). Its assets directory — `.en.assets/` — holds the **archive**-scope records, including a `language.yml` recording the relationship.

```yaml
# …/en/.en.assets/archive/
identity.yml
provenance.yml
dc.yml
language.yml      # relationship: independent
children.yml
```

#### …/en/docs/  (documents directory)

The standard content location: `<language-root>/docs`. Bodies live here; each document's records live in the document's own assets directory **beside** it, and its media live **inside** that assets directory (ADR-018 §3–4). The organizing directory carries its own content-scope records inside `.docs.assets/`.

```yaml
# …/en/docs/.docs.assets/content/        (content-directory-scope records)
identity.yml
provenance.yml
dc.yml

# …/en/docs/.guide.md.assets/content/    (document records for guide.md)
identity.yml
provenance.yml
dc.yml            # canonical metadata record — seeded by cataloging, operator-owned thereafter (ADR-023)
fixity.yml        # recorded digest (ADR-027)

# …/en/docs/                             (content; each file's assets beside it)
index.md            # body payload
.index.md.assets/   # index.md's records, beside it (ADR-018)
guide.md            # body payload
.guide.md.assets/   # guide.md's records — and its media (hero.png) inside here,
                    #   never as a dot-file sibling of guide.md
```

### collections/test-collection/fr/  (mirrored language archive)

A language archive rooted at language root `fr` that **mirrors** `en`: its structure parallels the source archive and is kept in correspondence. The relationship is recorded in its archive record.

```yaml
# …/fr/.fr.assets/archive/language.yml
relationship: mirrored
mirrors: en
```

### Derived projection

The effective mapping is rendered on demand by `sat config map` — a derived, read-only report in the same disposable class as `children.yml` and `work-index.yml`: regenerated on demand, never authoritative, never cached (ADR-034 decision 3). It pairs with `sat defaults --diff` as the second member of a small family of read-only reports. The filesystem and the ADR corpus remain the only declaration of the mapping; the projection is how that declaration is *seen*, never a rival source of truth, and layout evolution ships as ADR amendments with one-time `sat migrate` moves — no `mapping_version`.

### Operator configuration inputs

Preseeds and caches under `~/.config/sat/` seed topology and metadata above the instance and enable one-command instantiation (G6). Below the instance, the cascade is the preseed — and below the entire operator cascade sits SAT's shipped defaults floor (ADR-032), the value an operator inherits when no tier has stated one.

---

## How this satisfies the goals

- **Repeatable pattern (G2).** One rule: an entity's records live in its own `.<name>.assets/` — inside a directory, beside a file — under a role subdirectory; media live inside the file's assets directory.
- **Easy to configure / onboard (G3, Q2).** "Where does X live?" is answered by scope + kind + carrier alone — and rendered on demand by `sat config map`.
- **Clear layering (Q1).** Records are sparse and cascade deepest-stated-wins through the nine-layer walk; the document's own `dc.yml` is the deepest layer, the shipped floor the outermost.
- **Safety (Q3).** Identity and provenance are write-once (ADR-021); the shipped floor sits under the never-delegated `bin/sat/` (ADR-032); the mapping is auditable through the read-only projection, which writes nothing.
- **Quick spin-up (G6).** Instance + collection + `en` (and `fr`) archives with content under `<language-root>/docs`.
- **Extensible (E1–E5).** A new vocabulary lands as its own file under the earned `metadata/` parent, with `sat:metadata_schema` stating which is canonical (ADR-034, ADR-032 §5); new formats and tools add a named file to the shipped floor — no new resolver, no new `bin/` location; `en` (unmirrored) and `fr` (mirrored) share one pattern via the archive's `language.yml`.
