---
dc:title: "SAT Configuration Paths and Files Mapping — Recommended Pattern"
dc:description: "The recommended target pattern for SAT configuration paths and files: a self-describing mapping manifest plus namespaced payload families inside each role directory, designed for maximum, easy expansion."
dc:creator: "Christopher Steel"
dc:contributor: "Claude (Anthropic)"
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
  - paths and files mapping
  - mapping manifest
  - namespaced assets
  - extensibility
dc:identifier: "sat-configuration-paths-and-files-mapping-recommendation"
---

# SAT Configuration Paths and Files Mapping — Recommended Pattern

> **Superseded.** This document predates access to the ADR corpus. Its two central proposals — the five-lifecycle-families reorganization of role directories and the authoritative, versioned mapping manifest — are withdrawn. It is superseded by [ADR-034: Operator-Side Concern Parents and the Derived Mapping Projection](../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md). The body below is retained unchanged as the historical record that ADR-034's Context cites.

The single best recommendation, stated up front:

> **Make the mapping itself a configuration document.** Ship a versioned **mapping manifest** (`mapping.yml`) that declares where every payload kind lives, and organize each role directory into **namespaced payload families** (`metadata/`, `integrity/`, `structure/`, `policy/`, `derived/`). Tooling resolves every path through the manifest — never through a hardcoded path — so expanding SAT means *adding an entry or adding a file*, and evolving the layout itself means *versioning one document*.

Everything below is the working-out of that sentence, grounded in the mechanics now confirmed from `satlib` (ADR-005, -018, -024, -025, and the Step 11 cascade).

---

## 1. Grounding: what `satlib` actually pins down

Reading `en/lib/satlib` corrects and sharpens the earlier documents:

- **The assets directory is per-entity, not a fixed name (ADR-018).** Every entity `<name>` has exactly one assets directory `.<name>.assets` — `.sat.assets` is simply the transform applied to a directory named `sat`; `test-collection` twins as `.test-collection.assets`. The transform is injective and reversible; a directory's assets live *inside* it, a file's assets live *beside* it; anything matching `.*.assets` is metadata space, excluded from content enumeration; orphans are reported, never repaired.
- **Roles are read off the filesystem (ADR-024/-025).** The role subdirectories present inside an assets directory *are* the entity's declared roles (`sat/`, `collection/`, `archive/`, `content/`); two role directories make a dual-role entity.
- **The cascade has a three-state field vocabulary (Step 11).** `<calculated>` is an unresolved hole and a deliberate tripwire — it never wins and must be surfaced if never filled; `""` is a deliberate empty that wins like any value; anything else is concrete, deepest-concrete-wins. `dc:description` is never inherited. An archive's `language.yml` is injected as an override layer at its own level.
- **Discovery is registry-backed (ADR-005).** A tool finds its language root by walking up to the nearest ancestor whose name is a valid BCP 47 expression validated against the IANA registry.

These are load-bearing behaviours. The recommendation below **keeps every one of them** and changes only what sits *inside* a role directory — plus how tooling knows what sits there.

---

## 2. The two moves

### Move 1 — Namespaced payload families inside each role directory

Today a role directory holds a flat set of records (`dc.yml`, `fixity.yml`, `identity.yml`, …). Flat works until it grows; namespacing makes growth free. Group records into **families**, one subdirectory per family, with room for per-vocabulary expansion beneath:

```text
.<name>.assets/<role>/
├── identity.yml               # write-once; stays at root — it names the entity
├── metadata/                  # descriptive metadata — the vocabulary space
│   ├── dc.yml                 # canonical metadata record (canonical-metadata: dc)
│   ├── dc/                    # optional per-vocabulary expansion
│   │   └── overrides.yml      #   e.g. field-level overrides, mappings, profiles
│   └── mods.yml               # an additional vocabulary — added, never bolted on
├── integrity/                 # preservation records
│   ├── fixity.yml
│   └── provenance.yml
├── structure/                 # tree and relationship records
│   ├── children.yml
│   └── language.yml           # archive role; relationship: independent | mirrored
├── policy/                    # behavioural overrides owned at this tier
│   ├── collection.yml         # collection role
│   ├── markdown.yml           # per-tier floor override (ADR-030/-032 cascade)
│   └── content-spec.yml       # per-tier egress override
└── derived/                   # regenerable projections — safe to delete
    ├── og.yml
    └── schema.yml
```

Why these five families: they partition by **lifecycle**, which is the property tooling actually cares about — `identity.yml` write-once at the root; `metadata/` cascading and vocabulary-swappable; `integrity/` write-once/append-only; `structure/` regenerable or relationship-bearing; `policy/` operator-owned overrides; `derived/` disposable. A backup tool, an auditor, and a cache cleaner can each name their target with one path.

The user-anticipated forms fall out directly: `<asset-directory>/metadata/dc.yml` is the canonical metadata record; `<asset-directory>/metadata/dc/overrides.yml` is a per-vocabulary expansion point that exists the moment someone needs it, with no new convention required.

### Move 2 — The mapping manifest: the layout as configuration

Ship one versioned document that *declares* the entire paths-and-files mapping. Tooling — `satlib.assets`, `satlib.roles`, `satlib.cascade`, every `init` — resolves paths through it.

```yaml
# definitions/mapping/sat-mapping.yml  (shipped floor; overridable at instance scope)
mapping_version: 2

assets:
  transform: ".{name}.assets"        # ADR-018 — unchanged
  placement:
    directory: inside                # ADR-018 decision 3 — unchanged
    file: beside

roles: [sat, collection, archive, content]   # ADR-025 — unchanged

records:
  identity:
    family: root                     # stays at the role-directory root
    file: identity.yml
    lifecycle: write-once
  canonical-metadata:
    family: metadata
    file: "{canonical-metadata}.yml" # follows the setting — E1 for free
    lifecycle: cascading -> frozen-leaf
  fixity:        {family: integrity, file: fixity.yml,     lifecycle: write-once}
  provenance:    {family: integrity, file: provenance.yml, lifecycle: append-only}
  children:      {family: structure, file: children.yml,   lifecycle: regenerable}
  language:      {family: structure, file: language.yml,   roles: [archive]}
  collection:    {family: policy,    file: collection.yml, roles: [sat, collection]}
  og:            {family: derived,   file: og.yml,         lifecycle: regenerable}
  schema:        {family: derived,   file: schema.yml,     lifecycle: regenerable}

families:
  metadata:  {path: metadata,  expansion: per-vocabulary-subdirectory}
  integrity: {path: integrity}
  structure: {path: structure}
  policy:    {path: policy}
  derived:   {path: derived,   disposable: true}
```

Three properties make this the expansion engine:

- **The mapping is data, so extending SAT is editing data.** A new record kind, a new family, a new vocabulary: one entry. No code path changes, because no code path ever knew a literal path.
- **The mapping is versioned, so the layout itself can evolve.** `mapping_version: 1` *is* today's flat layout — the manifest describes the current tree exactly as it stands, which makes `sat migrate` (already dry-run-by-default, already precedented for exactly this kind of move) a mechanical translation between two manifest versions. Old instances remain readable forever: a tool that honours the manifest honours whichever version the instance declares.
- **The mapping cascades — narrowly.** The shipped manifest is the floor; an *instance* may override it (recorded in its sat-role `policy/`), and the choice is frozen at `sat init`. It does **not** vary per collection or archive — one instance, one layout — which keeps discovery deterministic while still letting different instances (dev vs archival, per the payload-map profiles) choose different layouts with the same tooling.

---

## 3. The full recommended tree

```text
sat/                                          # instance root — dual-role (ADR-024)
├── .sat.assets/                              # = .<name>.assets, name = "sat" (ADR-018)
│   ├── sat/                                  # instance role
│   │   ├── identity.yml
│   │   ├── metadata/dc.yml
│   │   ├── integrity/{fixity.yml, provenance.yml}
│   │   ├── structure/children.yml
│   │   └── policy/mapping.yml                # instance's frozen mapping choice
│   └── collection/                           # collection role (dual-role root)
│       ├── identity.yml
│       ├── metadata/dc.yml
│       ├── integrity/{fixity.yml, provenance.yml}
│       ├── structure/children.yml
│       └── policy/collection.yml
├── en/                                       # language root (ADR-005 discovery)
│   ├── bin/…                                 # configuration inputs: definitions + floor
│   │   └── sat/definitions/mapping/sat-mapping.yml    # the shipped manifest
│   ├── lib/satlib/…
│   └── docs/                                 # documents directory (G6)
└── collections/
    └── test-collection/
        ├── .test-collection.assets/          # per-entity naming (ADR-018)
        │   └── collection/
        │       ├── identity.yml
        │       ├── metadata/dc.yml
        │       ├── integrity/{fixity.yml, provenance.yml}
        │       ├── structure/children.yml
        │       └── policy/collection.yml
        ├── en/                               # unmirrored language archive
        │   ├── .en.assets/
        │   │   └── archive/
        │   │       ├── identity.yml
        │   │       ├── metadata/dc.yml
        │   │       ├── integrity/{fixity.yml, provenance.yml}
        │   │       └── structure/{children.yml, language.yml}   # independent
        │   └── docs/
        │       ├── .docs.assets/
        │       │   └── content/              # content-directory role
        │       │       ├── identity.yml
        │       │       ├── metadata/dc.yml
        │       │       └── structure/children.yml
        │       ├── guide.md                  # body payload
        │       ├── .guide.md.assets/         # file assets, beside (ADR-018)
        │       │   └── content/
        │       │       ├── metadata/dc.yml   # frozen leaf
        │       │       ├── integrity/{fixity.yml, provenance.yml}
        │       │       └── derived/{og.yml, schema.yml}
        │       └── .guide.hero.png           # content-media payload (sidecar)
        └── fr/                               # mirrored language archive
            └── .fr.assets/archive/structure/language.yml   # relationship: mirrored, mirrors: en
```

Note what did **not** change: the ADR-018 transform, the inside/beside placement, role detection, the `.*.assets` exclusion, the cascade's three-state vocabulary, discovery. The recommendation is a re-organization *inside* the role directory plus a manifest that describes it — the smallest change that buys the largest expansion surface.

---

## 4. Expansion vectors — what "easy" looks like

| Expansion | Action required | Goal |
|---|---|---|
| Swap canonical metadata (`dc` → `mods`) | Change the `canonical-metadata` setting; the manifest's `{canonical-metadata}.yml` interpolation follows; `metadata/mods.yml` becomes the record | E1 |
| Add a secondary vocabulary alongside | Drop `metadata/<vocab>.yml`; optionally add a record entry | E2 |
| Field-level vocabulary expansion | Create `metadata/<vocab>/overrides.yml` (or `profiles.yml`, `mappings.yml`) under the existing expansion rule | E2 |
| Add a new record kind (e.g. `rights.yml`, `access.yml`) | One `records:` entry naming its family and lifecycle | E2 |
| Add a document format | New content profile + egress/transmog definitions; per-tier override lands in `policy/` | E3 |
| Add a tool or library | Its `definitions/` directory joins the configuration inputs; any per-tier behaviour claims a `policy/` file via one manifest entry | E4 |
| Add a language archive, mirrored or not | `structure/language.yml` carries `relationship: independent | mirrored` (+ `mirrors:`) — same pattern either way | E5 |
| Spin up a working SAT | `sat init` reads the same manifest to write the whole chain — instance, collection, archives, `<language-root>/docs` | G6 |
| Evolve the layout itself | Publish `mapping_version: N+1`; `sat migrate` translates; old versions stay readable | all |

---

## 5. Why this is the best available shape

- **It converts layout knowledge into declared data.** Today the mapping lives in code (`role_path(entity, role, "language.yml")`) and in humans. The manifest makes it inspectable, diffable, validatable — and therefore schema-checkable, which is Q3's fail-fast made real for the *layout itself*, not just file contents.
- **Lifecycle-partitioned families give every future payload an obvious home.** The question "where does X go?" reduces to "what is X's lifecycle?" — and each family's answer also tells you its backup, audit, and cleanup policy for free (Q1, Q2).
- **It is the smallest change to the running system.** ADR-018/-024/-025 mechanics are untouched; `mapping_version: 1` describes the existing flat layout, so nothing existing is invalidated on day one.
- **It composes with everything already decided.** The payload-map profiles (twinned source, detached projection) become manifest choices; the detached projection is itself just `derived:`-family thinking applied at instance scale.

**Alternatives weighed and set aside:** keeping flat role directories (cheapest today, but every added record raises collision and clutter cost, and vocabulary expansion has no home); deep per-record directories (`metadata/dc/record.yml` for everything — uniform but noisy for the common case; the recommendation reserves subdirectories for when expansion actually arrives); encoding the mapping only in code (status quo — invisible, unversionable, unswappable).

---

## 6. Open decisions

- **Family names.** `metadata / integrity / structure / policy / derived` are proposed; naming remains deferred per the goals' non-goal.
- **Manifest override scope.** Instance-only-frozen-at-init is recommended; confirm no per-collection layout variance is ever wanted.
- **`identity.yml` placement.** Root of the role directory (recommended — it names the entity and is write-once) vs inside `integrity/`.
- **Merge semantics for list-valued fields.** `dc:subject` deepest-wins-replace is pinned as provisional in `satlib.cascade`; the manifest is the natural place to declare merge-vs-replace per field when that decision lands.
