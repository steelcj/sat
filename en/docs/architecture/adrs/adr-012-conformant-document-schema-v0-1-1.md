# ADR-012: Conformant Document Schema

Version: 0.1.1 Status: Proposed Date: 2026-05-21

## Context

Earlier ADRs establish the structural properties of SAT archives — language as filesystem structure (ADR-001), document identity and cross-language linking (ADR-010), the collection model (ADR-011), and the non-standard language naming convention (ADR-013). What none of them defines is what a conformant SAT document actually contains — what fields it carries, where its metadata lives, and how it relates to the publishing vectors that consume it.

The conventional approach in static site generators and content management systems is to embed metadata in document frontmatter — a YAML or TOML block at the top of the Markdown file that declares title, date, slug, language, and any other properties the publishing system needs. This approach couples the document to the publishing vector. A document authored for Hugo carries Hugo-specific frontmatter. A document authored for MkDocs carries MkDocs-specific frontmatter. Neither is portable without modification. When the publishing vector changes — as happened when MkDocs 2.0 broke the existing implementation — the documents themselves must be updated.

This coupling is incompatible with SAT's archival philosophy. An archive must remain valid and readable regardless of which publishing vector is current. A document authored in 2026 must be as navigable in 2046 as it is today, without depending on any particular tool remaining available or compatible.

A second problem is that different publishing vectors support different frontmatter schemas. Hugo and MkDocs are both Markdown-based static site generators and they do not share a frontmatter vocabulary. A PDF pipeline, a JSON API, or a print catalog have entirely different metadata requirements. Attempting to satisfy all of them from a single frontmatter block produces either an incomplete record for each consumer or a frontmatter block that is an unmaintainable accumulation of fields from multiple systems.

The third problem is long-term metadata governance. Frontmatter embedded in documents is difficult to update at scale. Changing a rights statement, updating creator attribution, or correcting a language declaration across a large archive requires editing every document. Metadata that lives in a separate, well-structured location can be updated independently of the document content it describes.

## Decision

### 1. The document is pure content

A SAT document is a Markdown file containing prose content. It carries no publishing-vector frontmatter. It makes no assumptions about how it will be published. The document's only responsibility is to contain the content it was written to contain.

The document file has no YAML front matter block. No `---` delimiters. No title field. No date. No slug. No language declaration. Those are all metadata and they all live in the document's metadata directory.

```markdown
Precision-machined safety razor featuring an aircraft aluminum finish
and mild shaving configuration. The AL13 is designed for close,
comfortable shaving with minimal blade exposure.
```

That is a complete, conformant SAT document. Everything else is external to the file.

### 2. SAT identity lives in content/identity.yml

Every SAT document has a corresponding assets directory at `.<file_name>.assets/` beside it (ADR-018). Within that assets directory, the `content/` role directory (ADR-025) carries SAT identity fields — the fields that are SAT-specific, format-independent, and required for the archive to function.

```yaml
# en/products/.henson-aircraft-aluminum.md.assets/content/identity.yml
dc:identifier: urn:uuid:7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e
sat:work: urn:uuid:a1b2c3d4-e5f6-4890-abcd-ef1234567890
sat_version: "0.1"
```

**`dc:identifier`** — the document's permanent, immutable identity. UUID version 4 in `urn:uuid:` lowercase form. Generated once at document creation. Never changed. Full specification in ADR-010 v0.1.3. Required.

**`sat:work`** — the work UUID shared by all expressions of one work. Every document carries one; a document with no translations simply carries a `sat:work` no other document shares yet. Expression lookup is served by the derived work index (ADR-022) — the sidecars are canonical. Full specification in ADR-010 v0.1.3 and ADR-022. Required.

**`sat_version`** — the SAT schema version this document conforms to. Required.

The `content/identity.yml` file is always present for every SAT document regardless of which canonical metadata format the collection uses. It is the SAT infrastructure layer. It is the one file a SAT tool can always find, always trust, and always read without knowing anything about the collection's canonical metadata format.

### 3. Canonical metadata lives in {format}/

The document's canonical metadata lives in a subdirectory of `.<file_name>.assets/` named after the canonical metadata format declared in `collection.yml`. For a Dublin Core collection that directory is `dublin-core/`. For a Schema.org collection it would be `schema-org/`. For a MODS collection it would be `mods/`.

The canonical metadata format is declared in `collection.yml` via the `canonical_metadata` field and discovered by upward-walking from the document's collection root (ADR-011). If the collection does not declare `canonical_metadata`, the walk continues upward through the SAT hierarchy until a declaration is found. The SAT root collection always declares `canonical_metadata: dublin-core` as the system-wide default. The walk always terminates.

```text
en/
  products/
    henson-aircraft-aluminum.md        ← pure prose, no frontmatter
    .henson-aircraft-aluminum.md.assets/
      sat/
        identity.yml                   ← dc:identifier, sat:work, sat_version
      dublin-core/                     ← canonical metadata (format-named)
        dublin-core.yml                ← base document metadata
        dc-relation.yml                ← translation relationships
        dc-product.yml                 ← collection-type extensions
      hugo/                            ← derived (generated at publish time)
        frontmatter.yml
      pdf/                             ← derived (generated at publish time)
        xmp-metadata.yml
```

### 4. Dublin Core as the default canonical format

Dublin Core is the SAT default canonical metadata format. It is well-understood, archivally respected, widely supported, and sufficient for the range of content SAT is designed to manage. The Dublin Core Metadata Initiative provides a stable, documented vocabulary maintained by an independent international organisation — consistent with SAT's preference for open, durable, externally-governed standards.

The base Dublin Core file for a product document:

```yaml
# en/products/.henson-aircraft-aluminum.md.assets/dublin-core/dublin-core.yml
dc_title: Henson AL13 - Aircraft Aluminum
dc_description: Precision-machined safety razor featuring an aircraft aluminum finish and mild shaving configuration.
dc_identifier: henson-aircraft-aluminum
dc_date_created: "2026-05-21"
dc_creator: Christopher Steel
dc_rights: "Copyright 2026 Christopher Steel. All rights reserved."
dc_language: eng
dc_format: physical-product
dc_type: product
```

`dc:creator` and `dc:rights` in the document's `dublin-core.yml` override the values cascaded from `.<archive_name>.assets/archive/dc.yml` when they differ. When they do not differ, the document's `dublin-core.yml` need not repeat them — the cascade provides them. This is the structural metadata cascade established in ADR-011: collection level → archive level → document level → fragment level, more specific values taking precedence.

### 5. Dublin Core fragments

The `dublin-core/` directory may contain granular fragment files alongside the base `dublin-core.yml`. Fragments carry Dublin Core elements with distinct lifecycles — elements that change on a different schedule from the base metadata and benefit from being maintained independently.

#### dc-relation.yml

Carries `dcterms:relation` and its refinements. For a translated document this carries the `dcterms:isTranslationOf` relationship expressed in standards-compliant Dublin Core terms. References the related document by `dc:identifier` — never by path.

```yaml
# en/products/.henson-aircraft-aluminum.md.assets/dublin-core/dc-relation.yml
dcterms_isTranslationOf:
  - dc:identifier: urn:uuid:9d8c7b6a-5e4f-4210-8edc-ba9876543210
    dc_language: fra
    language_bcp47: fr
```

`dc-relation.yml` is additive — it adds relations to any `dc:relation` entries in `dublin-core.yml`. It does not replace them.

#### Collection-type extension fragments

Collections of specific types carry additional metadata fragments for fields outside the Dublin Core core vocabulary. These are SAT extensions to Dublin Core, prefixed with the collection type to signal that they are domain-specific rather than standard Dublin Core terms.

For `product-catalog` collections:

```yaml
# en/products/.henson-aircraft-aluminum.md.assets/dublin-core/dc-product.yml
product_price_cad: 100.00
product_blade_count: 25
product_finish: aircraft-aluminum
product_exposure: mild
product_stripe_link:
  en: https://buy.stripe.com/REPLACE_EN
  fr: https://buy.stripe.com/REPLACE_FR
product_image_source: henson-aircraft-aluminum.jpg
product_image_alt: Henson AL13 safety razor in aircraft aluminum finish
```

The `product_stripe_link` field carries locale-keyed values because Stripe payment links are language-specific. This is the one case where language-specific data lives in a document that is otherwise language-independent. The keys are BCP 47 language tags.

#### Fragment merge semantics

Fragment files interact with `dublin-core.yml` according to element type:

- **Scalar elements** (`dc_title`, `dc_rights`, `dc_creator`) — the fragment overrides the corresponding element in `dublin-core.yml`. The most specific value wins, consistent with the cascade principle.
- **List elements** (`dc_relation`, `dc_subject`) — the fragment is additive. Its entries are appended to any entries in `dublin-core.yml`. Lists accumulate through the cascade; they are not replaced.
- **Extension elements** (`product_*`, `software_*`) — always additive. Extension fragments add domain-specific metadata. They do not interact with standard Dublin Core elements.

### 6. Derived publishing vector metadata

Publishing vector metadata is generated from the canonical metadata at publish time. It is never hand-authored. It is stored in vector-named subdirectories of `.<file_name>.assets/` and treated as build artifacts — regenerable, not authoritative.

```text
.henson-aircraft-aluminum.md.assets/
  sat/
    identity.yml                  ← authoritative — SAT infrastructure
  dublin-core/                    ← authoritative — canonical metadata
    dublin-core.yml
    dc-relation.yml
    dc-product.yml
  hugo/                           ← derived — generated at publish time
    frontmatter.yml               ← Hugo-compatible YAML frontmatter
  pdf/                            ← derived — generated at publish time
    xmp-metadata.yml              ← XMP metadata for PDF embedding
  sat-web/                        ← derived — generated for SAT web interface
    metadata.yml
```

The publishing pipeline reads the canonical metadata format declared in `collection.yml`, applies the appropriate transformer, and writes the derived metadata to the vector subdirectory. If a derived metadata file is missing or stale, it is regenerated. If the canonical metadata changes, all derived metadata is regenerated. The canonical metadata is the single source of truth.

A Hugo transformer reads `dublin-core.yml`, `dc-relation.yml`, and any extension fragments, and produces `hugo/frontmatter.yml`:

```yaml
# .henson-aircraft-aluminum.md.assets/hugo/frontmatter.yml
title: Henson AL13 - Aircraft Aluminum
date: "2026-05-21"
slug: henson-aircraft-aluminum
translationKey: 7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e
params:
  price_cad: 100.00
  blade_count: 25
  stripe_link_en: https://buy.stripe.com/REPLACE_EN
  stripe_link_fr: https://buy.stripe.com/REPLACE_FR
```

Hugo reads this file as the document's frontmatter. It never reads `dublin-core.yml` directly. The transformer is the bridge between SAT's canonical metadata and Hugo's requirements.

### 7. The metadata directory naming and the ingress sequence

The document metadata directory is named `.<file_name>.assets/` where `slug` is derived from the document's descriptive record (ADR-015). This creates a bootstrapping dependency — the metadata directory is named after a field that lives inside it. The dependency is real and it is resolved by the ingress sequence, which establishes the slug before the metadata directory is created.

The ingress sequence for a document created by the SAT tool directly is:

1. Author provides a title in the language of the archive
2. Tool derives a conformant slug from the title — lowercase, hyphens as word separators, ASCII letters and digits, no spaces or special characters
3. Tool generates the document's `dc:identifier` and `sat:work`
4. Tool creates the document file at `{archive}/{content-dir}/{slug}.md`
5. Tool creates the metadata directory at `{archive}/{content-dir}/.<file_name>.assets/`
6. Tool writes `content/identity.yml` with `dc:identifier`, `sat:work`, and `sat_version`
7. Tool writes `dublin-core/dublin-core.yml` with `dc_title`, `dc_identifier`, `dc_date_created`, and any fields cascaded from the archive level

This sequence has no circular dependency. The title is the input. The slug is derived from the title. The metadata directory is named from the slug. The dependency is linear.

For rename-safety, the document's identity in `content/identity.yml` is the evidence that survives any rename: a SAT tool never trusts a name alone. Name drift is detected and repaired through discovery and reconciliation (ADR-024), which supersedes the earlier ADR-014 sketch of rename handling. The data is never lost — only the convenience name is out of sync.

### 8. The collection description document

A collection description document is a SAT document like any other: it follows the same schema, has its own `.<file_name>.assets/content/identity.yml` with its own `dc:identifier`, and, when translated, shares a `sat:work` with its translations in other language archives.

```text
en/
  .en.assets/
    collection/
      description.md
      .description.assets/
        sat/
          identity.yml           ← dc:identifier, sat:work, sat_version
        dublin-core/
          dublin-core.yml        ← dc:title is the collection name in English
```

The `collection/description.md` document does not have a `dc_identifier` slug in the URL-path sense — it is not published as a navigable page. Its `dc_identifier` is `collection-description` by convention. Its `dc_title` is the collection name in the language of the archive.

### 9. The nesting principle

The document schema is consistent at every level of the SAT hierarchy. A document, a collection description, an archive description, and a SAT tool documentation file all follow the same pattern: pure content in a Markdown file, SAT identity in `sat/identity.yml`, canonical metadata in `{format}/`, derived metadata in `{vector}/`. The mechanism is identical at every scale.

This is the Russian nesting doll property of the SAT architecture. Each level is complete and self-describing. Each level inherits context from its container through upward-walking discovery. Each level can be extracted from the hierarchy and operated on independently. Sovereignty and inheritance coexist — the document is sovereign because it carries its own `dc:identifier`, and it is contextualised because it inherits canonical metadata format, rights, and language from the levels above it.

### 10. Document ingress

Not all documents enter the archive through the SAT tool's own creation workflow. Authors drag and drop files, save from external editors, copy from other locations, or receive files from contributors. The ingress process handles any file that arrives in a language archive content directory without a corresponding `.<file_name>.assets/` directory.

The ingress process evaluates three conditions in order.

#### Condition 1 — file format

Is the file a format SAT can ingest? The currently supported format is Markdown (`.md`). Files with other extensions are flagged as unsupported format and left unchanged. No error, no rejection — a report is generated noting that the file requires a format handler not yet available. The file remains in place. This preserves the option to add format handlers in future versions without altering the archive structure.

#### Condition 2 — frontmatter presence

If the file is Markdown, does it contain a YAML frontmatter block — a `---` delimited block at the top of the file?

If frontmatter is present, the tool conserves it rather than discarding it. The process requires Archive Admin permissions — the tool is modifying a file it did not create. With those permissions:

- The frontmatter block is extracted from the document
- The document is written back as pure prose with the frontmatter removed
- Recognised frontmatter fields are mapped to Dublin Core equivalents — `title` → `dc_title`, `date` → `dc_date_created`, `author` → `dc_creator` — and written to `dublin-core/dublin-core.yml`
- Unmapped fields are recorded in the ingress report for author review
- The original frontmatter is preserved in the ingress record (see below)

Without Archive Admin permissions, the tool flags the frontmatter as present and does not modify the file. It reports that Archive Admin action is needed to complete ingress.

If no frontmatter is present, the file is already pure prose. Condition 2 passes without action.

#### Condition 3 — slug conformance

The filename stem is the candidate slug. A conformant slug consists of lowercase ASCII letters, digits, and hyphens only — no spaces, no underscores, no special characters, no uppercase letters.

If the slug is conformant, the tool proceeds with UUID generation and metadata directory creation using the filename stem as `dc_identifier`.

If the slug is non-conformant, the tool does not rename the file automatically. Renaming a file the author placed is a modification requiring explicit permission. Instead the tool flags the non-conformant filename, suggests a conformant alternative derived from the filename, and waits for the author to act. It creates the metadata directory using the non-conformant name as-is and records the non-conformance in the ingress report.

#### The ingress record

Every ingress event produces a timestamped record at `.<file_name>.assets/ingress/ingress-{timestamp}.yml`. This record serves two purposes: it is an audit trail of what the tool did to the file, and it is a recovery document that allows the author to restore the original state if needed.

The recovery mechanism depends on whether the archive uses Git.

**With Git available**, the tool commits the original file before performing any modifications. The ingress record carries the pre-ingress commit hash and a ready-to-run recovery command:

```yaml
sat_version: "0.1"
ingress_timestamp: "2026-05-21T14:32:00Z"
ingress_source: en/products/henson-jet-black.md
performed_by: sat-tool-0.1.0
permissions_level: archive-admin

version_control: git
pre_ingress_commit: a3f8b2c1
recovery_method: git
recovery_command: "git checkout a3f8b2c1 -- en/products/henson-jet-black.md"

format_detected: markdown
slug_conformant: true
slug: henson-jet-black

frontmatter_present: true
frontmatter_mapped:
  title: "Henson AL13 - Jet Black"
  date: "2026-05-21"
frontmatter_unmapped:
  - tags: [razor, grooming]
  - custom-field: some-value

identifier_generated: urn:uuid:7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e

actions_required:
  - Review unmapped frontmatter fields in ingress record
  - Confirm dc_title is correct in dublin-core/dublin-core.yml
```

**Without Git**, the tool preserves the original frontmatter verbatim in the ingress record with a human-readable recovery instruction:

```yaml
sat_version: "0.1"
ingress_timestamp: "2026-05-21T14:32:00Z"
ingress_source: en/products/henson-jet-black.md
performed_by: sat-tool-0.1.0
permissions_level: archive-admin

version_control: none
recovery_method: inline
recovery_note: "Original frontmatter preserved below. To restore, prepend this block to en/products/henson-jet-black.md between --- delimiters."
original_frontmatter: |
  title: Henson AL13 - Jet Black
  date: 2026-05-21
  tags:
    - razor
    - grooming
  custom-field: some-value

format_detected: markdown
slug_conformant: true
slug: henson-jet-black

frontmatter_present: true
frontmatter_mapped:
  title: "Henson AL13 - Jet Black"
  date: "2026-05-21"
frontmatter_unmapped:
  - tags: [razor, grooming]
  - custom-field: some-value

identifier_generated: urn:uuid:7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e

actions_required:
  - Review unmapped frontmatter fields in ingress record
  - Confirm dc_title is correct in dublin-core/dublin-core.yml
```

If no frontmatter was present and the slug was conformant, `recovery_method` is `none` and `actions_required` is empty. The ingress record still exists as an audit trail but the author is not prompted.

The `version_control` field supports future version control systems beyond Git — `mercurial`, `svn`, or `none`. The recovery command syntax varies per system. The architecture supports this without changes to the ingress record structure.

#### Ingress and the watcher

The filesystem watcher (ADR-014) detects new files and triggers the ingress process. The ingress process is distinct from the rename-handling process — the watcher dispatches to the appropriate handler based on the event type. A `created` event for a `.md` file with no corresponding metadata directory triggers ingress. A `renamed` event for a directory triggers the paired rename handler.

## Alternatives Considered

**Publishing-vector frontmatter in the document** — the conventional approach. Rejected because it couples the document to a specific publishing vector, creates format-specific documents that are not portable, and makes large-scale metadata updates impossible without editing every document. The MkDocs 2.0 event demonstrated the cost of this coupling directly.

**A single unified metadata file per document** — one file containing SAT identity, canonical metadata, and all publishing vector metadata. Rejected because it conflates three concerns with different lifecycles, different consumers, and different authoring responsibilities. The structured separation of `sat/`, `{format}/`, and `{vector}/` subdirectories makes each concern independently maintainable.

**Metadata embedded in the document filename or directory name** — for example, encoding the document date or language in the filename. Rejected because it makes document identity dependent on a mutable filesystem property, which is the failure mode the UUID model exists to prevent.

**A single canonical metadata format mandated by SAT** — requiring all collections to use Dublin Core. Rejected because different archival domains have different metadata requirements. Library science uses MODS. Cultural heritage uses LIDO. Scientific data uses DataCite. SAT's architecture supports all of these by making the canonical format a collection-level declaration rather than a system-level mandate. Dublin Core remains the default because it is the most broadly applicable vocabulary for the current use cases.

## Consequences

- SAT documents are pure Markdown prose with no embedded frontmatter
- Every document has a `.<file_name>.assets/` directory containing `sat/identity.yml` as the minimum required infrastructure
- `dc:identifier` and `sat:work` live in `content/identity.yml` — not in the document, not in the canonical metadata
- Canonical metadata lives in a format-named subdirectory — `dublin-core/` by default
- `canonical_metadata` is declared in `collection.yml` and discovered by upward walking — the SAT root always provides `dublin-core` as the fallback
- Derived publishing vector metadata lives in vector-named subdirectories and is always regenerable from canonical metadata
- The structural metadata cascade applies at the document level — document-level canonical metadata overrides archive-level metadata for scalar elements and is additive for list elements
- Fragment files with distinct lifecycles live as separate files within the canonical metadata directory
- The `collection/description.md` document follows the same schema as all other documents
- Publishing vectors never read canonical metadata directly — they read derived metadata generated by a transformer
- The architecture supports any canonical metadata format by declaring it in `collection.yml` and providing a transformer
- Files arriving in the archive from outside the SAT tool are handled by the ingress process — format check, frontmatter extraction, slug validation, UUID generation
- Frontmatter extraction from ingested files requires Archive Admin permissions
- Every ingress event produces a timestamped record in `.<file_name>.assets/ingress/` carrying the recovery command or inline recovery data depending on Git availability
- The author is prompted only when `actions_required` is non-empty — silent ingress for clean files
- ADR-014 defines the tooling model that maintains metadata directory consistency through filesystem events and triggers the ingress process for new files

## References

- ADR-001: Language as filesystem structure
- ADR-010: Document identity and cross-language linking
- ADR-011: SAT collection model
- ADR-013: Non-standard language archive naming convention
- ADR-014: Filesystem-event-driven tooling model (Todo)
- Dublin Core Metadata Initiative. (2024). *DCMI metadata terms*. https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
- Dublin Core Metadata Initiative. (2024). *Dublin Core usage guide*. https://www.dublincore.org/specifications/dublin-core/usageguide/
- Internet Engineering Task Force. (2024). *A universally unique identifier (UUID) URN namespace* (RFC 9562). https://www.rfc-editor.org/rfc/rfc9562

## Licence

This document by **Christopher Steel**, with contributions from AI systems including **ChatGPT (OpenAI)**, **Claude Sonnet 4.6 (Anthropic)**, and **Claude Sonnet 4.7 (Anthropic)**, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 International Licence](https://creativecommons.org/licenses/by-sa/4.0/).

## Changelog

| Version | Status   | Notes                                                        |
| ------- | -------- | ------------------------------------------------------------ |
| 0.1.1   | Proposed | Revised section 7 with linear ingress sequence; added section 10 on document ingress covering three ingress conditions, permissions model, ingress record, Git and non-Git recovery mechanisms |
| 0.1.0   | Proposed | Initial draft                                                |
