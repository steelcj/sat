# ADR-011: SAT Collection Model

```yaml
status: Proposed
date: 2026-05-20
amended: 2026-07-10 (assets convention; sat:work linkage; description as mirrored work; see Amendments)
version: 0.1.1
```

## Context

SAT organises content as language archives — self-contained directory trees rooted at a BCP 47 language tag (ADR-001). A language archive is a complete, independently valid unit. However, a publication typically spans multiple language archives. The Henson AL13 product store has an English archive and a French archive. The universalcake.com corpus will eventually contain multiple publications, each spanning multiple languages.

Nothing in the earlier ADRs defines how language archives are grouped into a named publication, what the intended relationship between those archives is, or how tooling discovers the collection boundaries when processing individual documents. ADR-008 describes the repository structure but treats language directories as the primary organising unit. It does not define a collection as a first-class entity with its own declared intent.

Without an explicit collection model, publishing vectors must infer collection membership from directory conventions. Inference from convention is fragile: it breaks when archives are renamed, when a collection moves within a larger repository, or when a repository contains multiple peer collections.

Three requirements drive this decision:

**Rename-safety.** SAT archives must be renameable without losing their relationships. Renaming `en/` to `en-CA/` is a legitimate archival operation that corrects a language declaration (ADR-001, ADR-003). The system must accommodate this without breaking collection membership or publishing vector output. Rename-safety is achieved by upward-walking discovery: a document discovers its collection by walking upward from its own path until it finds the structural marker that declares a collection boundary. The document does not store this context internally. The next processing run after a rename derives the correct context from the new structure automatically.

**Separation of concerns.** An archive carries several distinct categories of metadata — SAT infrastructure, language declaration, administrative metadata, and human-readable description — each maintained on a different timescale by different processes. These live as separate records with single responsibilities rather than being conflated in one file.

**Intent over state.** A collection description declares what the collection is trying to be, not what it currently is. The current state of the archives — how complete a translation is, how many documents exist — is a fact discovered by tooling at inspection time, not declared in the collection description. This distinction is fundamental.

Since this record was first drafted, ADR-018 established the universal assets directory convention (`.<name>.assets/`), superseding the `.{language}_meta/` structure this record originally specified, and ADR-010 (as amended) established the `dc:identifier`/`sat:work` identity model that mirrored relationships link through.

## Decision

### 1. The collection root is declared by collection.yml in the collection's assets

A SAT collection is a directory whose assets directory contains a `collection.yml` record. The presence of `.{name}.assets/collection.yml` is what makes a directory a collection root. The record lives in the assets directory per ADR-018 — everything regarding an entity lives in its assets — and drops the `sat-` filename prefix for the same reason archive sidecars dropped their leading dots: the assets directory already establishes the namespace.

The record contains three things and nothing else: the SAT specification version, the human-readable collection name, and the declared relationships between the archives in the collection. It does not contain prose descriptions, Dublin Core metadata, language declarations, or publishing vector configuration. Dublin Core metadata for the collection lives beside it in the same assets directory as `dc.yml`, the cascade source for the collection's archives.

Minimum conformant `collection.yml`:

```yaml
# henson-catalog/.henson-catalog.assets/collection.yml
sat_version: "0.1"
name: Henson Razor Product Catalog
relationships:
  - type: mirrored
    language_source: /en
    archives:
      - /en
      - /fr
```

**`sat_version`** — the SAT specification version this collection conforms to. Required. Archives in the collection conform to the collection's declared version; per-archive version declarations are not maintained separately.

**`name`** — the human-readable name of the collection as a whole, not tied to any specific language. Required.

**`relationships`** — one or more declared relationships between the archives in the collection. Required. See section 4.

### 2. Archive metadata structure

Each language archive carries its records in its assets directory per ADR-018. The assets directory name is derived mechanically from the archive directory name; when the archive is renamed, the assets directory is renamed with it as part of the same tool-mediated operation (ADR-018 decision 5).

```text
en/
  .en.assets/
    dc.yml            ← administrative metadata; inherits collection defaults via the cascade
    language.yml      ← language declaration and authority (ADR-003, ADR-005)
    provenance.yml    ← creation provenance: timestamp, tool version, registry File-Date
  products/
    henson-aircraft-aluminum.md
    .henson-aircraft-aluminum.md.assets/
      dc.yml          ← dc:identifier, sat:work, document metadata (ADR-010)
```

```text
fr/
  .fr.assets/
    dc.yml
    language.yml
    provenance.yml
  produits/
    henson-aluminium-aeronautique.md
    .henson-aluminium-aeronautique.md.assets/
      dc.yml
```

The separation of concerns survives the relocation: `language.yml` changes only if the archive is renamed or its authority status changes; `dc.yml` changes when rights or attribution change; `provenance.yml` never changes. Different lifecycles, different records, one home.

### 3. Archive metadata records

#### language.yml

Declares the language of the archive and the authority under which it is validated (ADR-003). This is the machine-readable elaboration of what the directory name already declares structurally (ADR-001). The directory name itself is the canonical SAT identifier; it is not duplicated into the record, so a rename touches the structure and its assets pairing only, never a third copy inside a file.

`dc:language` carries the ISO 639-2 code. `dc:language_bcp47` carries the interoperability representation for external systems. For IANA-registered languages these derive directly from the validated tag. For non-standard languages (ADR-013) the directory uses the `sat-x-` prefix and `dc:language_bcp47` carries the CLDR-compatible `und-x-` form, because CLDR-based publishing tools reject whole-tag `x-` as a primary language subtag.

```yaml
# en/.en.assets/language.yml
dc:language: "eng"
dc:language_bcp47: "en"
sat:authority: "external"
```

```yaml
# sat-x-asl-west/.sat-x-asl-west.assets/language.yml
dc:language: "und"
dc:language_bcp47: "und-x-asl-west"
sat:authority: "none"
sat:authority_note: "Regional ASL variant, no registered subtag exists"
```

For non-standard languages, `dc:language` defaults to `und` — the honest machine answer when no mapping exists. Where a close registered code exists (for `sat-x-asl-west`, `ase` approximates), the operator may set it explicitly, with the authority note documenting the precision of the approximation. The tool never guesses; the operator may refine.

#### dc.yml

Carries the Dublin Core administrative metadata for the archive, resolved through the metadata cascade from the collection's defaults. Fields awaiting the cascade are written as `<calculated>` at creation and resolved at instantiation; `dc:description` and `dc:identifier` never inherit.

```yaml
# en/.en.assets/dc.yml (resolved)
dc:identifier: "urn:uuid:3c9d1e2f-8a4b-4c6d-9e0f-5a7b8c9d0e1f"
dc:title: "Henson Razor Product Catalog (English)"
dc:creator: "Christopher Steel"
dc:rights: "Copyright 2026 Christopher Steel. All rights reserved."
dc:language: "eng"
dc:language_bcp47: "en"
dc:description: ""
```

#### The collection description

The collection's human-readable description is not an assets record — it is content: a document in each language archive, participating in the same translation workflow as any other document, its language versions linked by a shared `sat:work` (ADR-010). The collection record names that work:

```yaml
# .henson-catalog.assets/collection.yml (extended)
sat_version: "0.1"
name: Henson Razor Product Catalog
description_work: "urn:uuid:018f4b2c-7d1e-4f3a-9b5c-2e6d8a0c1f4b"
relationships:
  - type: mirrored
    language_source: /en
    archives:
      - /en
      - /fr
```

A missing description in a given language is an untranslated document, reported by tooling — not a structural error. The description may be as brief or as expansive as the archivist requires: a paragraph for a product catalog, several pages of archival context for a historically complex collection.

### 4. Relationships

The `relationships` block declares the intended relationship between archives. It describes intent, not state. A `type: mirrored` relationship with an incomplete French translation is not a malformed collection — it is a collection whose current state does not yet match its declared intention. The gap is reported by tooling, not recorded in `collection.yml`.

**`language_source`** is optional. When present it identifies the archive from which the relationship originates. For translation relationships this is the archive in the originating language. For remediation relationships this is the archive being corrected. For relationships where no archive has primacy — thematic parallels, multilingual originals — `language_source` is absent. The field is named `language_source` rather than `source` to make explicit that it refers to linguistic or archival origin, not a technical default or fallback instruction.

**`archives`** lists the paths of the participating archives relative to the collection root.

```yaml
# mirrored translation
relationships:
  - type: mirrored
    language_source: /en
    archives:
      - /en
      - /fr

# thematic parallel — no directionality
relationships:
  - type: thematic-parallel
    archives:
      - /en
      - /fr

# multilingual original — created simultaneously in both languages
relationships:
  - type: multilingual-original
    archives:
      - /en
      - /fr-CA

# critical remediation
relationships:
  - type: critical-remediation
    language_source: /en-dewey
    archives:
      - /en-dewey
      - /en-remediated

# multiple relationships in one collection
relationships:
  - type: mirrored
    language_source: /en
    archives:
      - /en
      - /fr
  - type: sign-language-parallel
    language_source: /en
    archives:
      - /en
      - /sat-x-asl-west
```

### 5. Relationship type vocabulary

| Type | Meaning | language_source |
|---|---|---|
| `mirrored` | Every document in the source archive is intended to have a corresponding translated document in each target archive, linked by `sat:work` | Required |
| `thematic-parallel` | Archives contain independent works related by subject, not by document correspondence | Absent |
| `multilingual-original` | The work was created in all listed languages simultaneously; no archive is the linguistic source | Absent |
| `complementary` | Archives contain different but related content serving the same collection purpose | Optional |
| `sign-language-parallel` | A sign language archive is the visual-language equivalent of a spoken or written language archive | Required |
| `critical-remediation` | One archive corrects, critiques, or reclassifies the content of another | Required |
| `scholarly-commentary` | One archive contains commentary on or analysis of the content of another | Required |

Custom relationship types use the same lowercase hyphenated naming convention as the controlled vocabulary. They must not duplicate a controlled vocabulary term. Authors are encouraged to document custom types in the collection description. If a custom type proves broadly useful it may be proposed for inclusion in the controlled vocabulary.

### 6. Language-native content directories

Content directories inside a language archive are named in the language of that archive. The English archive contains `products/`. The French archive contains `produits/`. The archive is linguistically self-consistent at every level.

```text
en/products/henson-aircraft-aluminum.md
fr/produits/henson-aluminium-aeronautique.md
```

This is a direct consequence of ADR-001: language is structural. A French directory name inside an English archive is a structural inconsistency. Each archive owns its own path vocabulary. Cross-language document linking is handled by `sat:work` (ADR-010), not by path mirroring.

The content directory structure — what goes inside `products/` or `produits/`, what the document schema looks like — is defined in ADR-012.

### 7. Discovery by upward walking

A document discovers its collection by walking upward from its own path until it finds a directory whose assets contain `collection.yml`. A document discovers its language context by walking upward until it finds a language archive root — a directory whose name passes the language pattern test (ADR-005), including the `sat-x-` structural marker for non-standard archives (ADR-013). Two independent discoveries, one mechanism, different questions.

```text
en/products/henson-aircraft-aluminum.md
  ↑ walk upward
en/
  name validates as a language tag ← language context: en
  ↑ continue
henson-catalog/
  .henson-catalog.assets/collection.yml found ← collection: Henson Razor Product Catalog
```

After renaming `en/` to `en-CA/` (with `.en.assets/` renamed to `.en-CA.assets/` in the same tool-mediated operation, ADR-018 decision 5):

```text
en-CA/products/henson-aircraft-aluminum.md
  ↑ walk upward
en-CA/
  name validates as a language tag ← language context: en-CA
  ↑ continue
henson-catalog/
  .henson-catalog.assets/collection.yml found ← collection unchanged
```

The document's collection membership is unchanged. Its language context is updated from the renamed directory. No document-internal metadata was modified. `collection.yml` was not touched.

### 8. Evolution path

The model supports incremental evolution. The structural layer is stable across all stages.

**Stage 1 — pragmatic start:** `collection.yml` and `dc.yml` in the collection's assets; `dc.yml`, `language.yml`, and `provenance.yml` in each archive's assets. No description documents yet. Structurally complete and tooling-ready.

**Stage 2 — primary description added:** the description document authored in the source-language archive, its `sat:work` recorded as `description_work` in `collection.yml`. Other language descriptions absent — reported by tooling, not an error.

**Stage 3 — fully described:** description expressions exist in every language archive, all carrying the shared `sat:work`. `collection.yml` has not changed since Stage 2.

## Alternatives Considered

**Loose `sat-collection.yml` at the collection root** — the original form of this record. Superseded by ADR-018: everything regarding an entity lives in its assets directory, and a loose marker file at the root is exactly the per-concern-location pattern the assets convention absorbed. The marker function survives unchanged; only its address moved.

**`.{language}_meta/` directory with `sat/`, `archive/`, `collection/` subdirectories** — the original metadata structure. Superseded by ADR-018's flat assets records. The separation-of-concerns rationale survives as separate files with distinct lifecycles; the subdirectory taxonomy added depth without adding a concern the filenames do not already express.

**Single file combining version, language, and Dublin Core** — rejected because it conflates three concerns with different lifecycles. A tool validating language declarations should not need to parse rights metadata.

**Generic `.meta/` directory without a name binding** — rejected for the reason ADR-018 also rejected fixed-name assets: the directory becomes structurally unmoored from its entity, and the pairing is invisible without opening it.

**`collection-description.md` loose at the archive root** — rejected because it mixes infrastructure with browsable content. Resolved on amendment in the opposite direction: the description is fully content — an ordinary mirrored document — and the collection record points at its work identifier.

**Inline multilingual prose in the collection record** — rejected because it mixes structural declarations with language-specific prose and introduces English key names into a language-neutral file.

**Language-independent content directory names (English throughout)** — rejected as a structural inconsistency under ADR-001. Cross-language linking is handled by `sat:work`, not path mirroring.

## Consequences

- A directory becomes a SAT collection by carrying `collection.yml` in its assets directory
- `collection.yml` contains `sat_version`, `name`, `relationships`, and optionally `description_work` — nothing else
- The collection's `dc.yml` beside it is the cascade source for its archives (satlib Step 11)
- Archive metadata lives in each archive's assets per ADR-018: `dc.yml`, `language.yml`, `provenance.yml`
- The collection description is content: one document per language, linked by a shared `sat:work`, named by `description_work`
- Renaming an archive renames its assets directory in the same tool-mediated operation; discovery re-derives context on the next run
- Content directories are named in the language of their archive
- `language_source` is optional and present only where archival direction is meaningful; the word "default" does not appear in collection declarations
- Collections are position-independent and rename-safe
- Non-standard language archives use the `sat-x-` directory prefix with `und-x-` BCP 47 representation (ADR-013)
- ADR-012 defines the content layer — document schema, frontmatter, and what lives inside language-native content directories

## Amendments

| Date | Change |
|------|--------|
| 2026-07-10 | `sat-collection.yml` relocated into the collection's assets as `collection.yml` per ADR-018; `.{language}_meta/` structure superseded by assets records; key style modernised (`dc:` and `sat:` namespaces); `language_authority` vocabulary replaced by `sat:authority` levels; redundant `language:` field dropped — the directory name is the sole declaration; mirrored linkage updated from shared `sat_uuid` to `sat:work` per ADR-010 as amended; collection description redefined as a mirrored content document named by `description_work`; per-archive `version.yml` folded into the collection's `sat_version`; `dc:language` for non-standard archives defaults to `und` with operator refinement permitted. |
| 2026-07-12 | `born.yml` renamed to `provenance.yml` per ADR-020 throughout. |

## References

- ADR-001: Language as Filesystem Structure
- ADR-002: Mixed Language Archive Naming Convention
- ADR-003: IANA Language Subtag Registry as Authoritative Source
- ADR-005: Tool Self-Discovery from Filesystem Context
- ADR-008: Top-Level Repository Structure with Language-Scoped Archives
- ADR-010: Document Identity and Cross-Language Linking (as amended)
- ADR-012: Conformant Document Schema
- ADR-013: Non-Standard Language Archive Naming Convention
- ADR-018: Universal Assets Directory Convention
- satlib Design and Rationale v0.2.0 (ratification rows 10–12, superseded by this amendment)
