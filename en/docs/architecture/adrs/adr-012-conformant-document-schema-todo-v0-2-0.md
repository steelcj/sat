# ADR-012: Conformant Document Schema — Todo

Version: 0.2.0
Status: Superseded
Date: 2026-05-20
Style Guide: style-guide--technical-documentation-for-technologists-v0.2.0.md

## Abstract

This document recorded the open questions that blocked ADR-012's drafting on 2026-05-20. ADR-012 was subsequently written, and the decisions of ADR-018 through ADR-025 resolved or dissolved every blocking question. This version supersedes the todo: each question is mapped to its resolving decision below, and the surviving residues are tracked in living documents, not here. The original questions are preserved under the resolution table for the record — retired, not erased.

Do not read the original "What is already settled" section as current: it predates ADR-018 and ADR-020, and states as settled several things later retired (identity in frontmatter, `sat_uuid`/`sat_tg`, the `.sat_meta/translations/` index, `_meta` paths).

## Resolution table

| Question | Resolution | Resolved by |
|---|---|---|
| 1. Model A versus Model B for structured data | Model A (all metadata in frontmatter) rejected wholesale: documents are pure content and carry no frontmatter. Sidecar metadata is the Model-B shape. Residue — where collection-type structured data (price, blade count) lives — remains open, tracked on the Complete Filesystem Cascade goals horizon (type extensions, Dublin Core usage standards). | ADR-012 §1; ADR-018; cascade goals v0.2.0 |
| 2. Required versus optional frontmatter fields | Dissolved: no frontmatter exists. Fragments landed elsewhere — identity required (`dc:identifier` and `sat:work`, every document); `created` in the provenance record; `slug` derived from the sidecar; `title` in the descriptive record via cataloging. | ADR-012 §1; ADR-010 v0.1.3; ADR-022; ADR-020; ADR-015; ADR-023 |
| 3. Dublin Core fragment merge semantics | Mostly resolved: `dc:subject` merges as union (transcribed first, deduplicated, order preserved); the cascade's general rule is deepest-stated-value-wins. Residue — additive-list elements such as `dc:relation`, and the fragment-file model itself — travels with ADR-012's deferred decisions 3–5 (trigger: the ADR-023 implementation). | ADR-023; ADR-025 (resolution order); ADR-012 v0.1.1 changelog |
| 4. collection/description.md schema | Dissolved by role directories: collection descriptive metadata is the collection role's `dc.yml`. A prose description, if wanted, is an ordinary document with an ordinary document schema. | ADR-025 |
| 5. Collection-type-specific schema extensions | Still open, correctly deferred; recorded on the cascade goals horizon so it is not reinvented cold. | Cascade goals v0.2.0 (horizon) |
| 6. Slug language-independence | Resolved by construction: slugs stay language-specific; the work index is the cross-language lookup (`sat:work` to per-language identifier and path). No canonical slug exists or is needed. | ADR-022 |

Nothing below this line is current. The original todo follows for the record.

---

## Original todo (2026-05-20, superseded)

### What is already settled (superseded — see warning above)

Every SAT document carries a `sat_uuid` field in its frontmatter. The UUID is version 4, lowercase, 36-character standard format. It is the document's own permanent identity, unique to that document, immutable after creation. It is generated once at document creation time and never changed. Full specification in ADR-010.

Every SAT document that participates in a translation relationship carries a `sat_tg` field in its frontmatter. The `sat_tg` value is the UUID of the translation group to which the document belongs. All translations of the same document carry the same `sat_tg` value. The translation group itself is stored in `.sat_meta/translations/{sat_tg}.yml` at the collection root, containing only the `sat_tg` UUID and the `sat_uuid` of each member document — no paths. The `sat_tg` field is optional — a document with no translation carries no `sat_tg`.

The language of a document is not stored in the document. It is derived from the archive root directory name by upward-walking discovery (ADR-001, ADR-011).

Collection membership is not stored in the document. It is derived from the `.sat_meta/` directory at the collection root by upward-walking discovery (ADR-011).

Document-level Dublin Core metadata lives in `.{slug}_meta/dublin-core/` alongside the content file in the content directory. The directory is named after the document filename stem. The Dublin Core directory may contain a `dublin-core.yml` file for base document-level overrides and granular fragment files — `dc-relation.yml`, `dc-rights.yml` and so on — for elements with distinct lifecycles. Fragment files are additive or override depending on the element — this merge rule is an open question below.

Content directories inside a language archive are named in the language of that archive — `products/` in English, `produits/` in French. This is a consequence of ADR-001 and ADR-011.

The `collection/description.md` file in `.{language}_meta/collection/` is itself a SAT document. It has a `sat_uuid` and, when translated, a `sat_tg`. It participates in the same translation workflow as any other document in the archive.

Archive-level Dublin Core in `.{language}_meta/archive/dublin-core.yml` cascades into all documents in the archive. Document-level Dublin Core in `.{slug}_meta/dublin-core/` overrides or extends the cascaded values. The structural metadata cascade is: collection level → archive level → document level → fragment level, with more specific values taking precedence.

### Open questions — blocking (all resolved; see table)

#### 1. Model A versus Model B for structured data

For collections of type `product-catalog`, documents carry structured data — price, purchase links, blade count, finish, image references — alongside prose content. Two models were identified.

**Model A — all metadata in frontmatter.** The document is self-contained. Structured product fields live in the frontmatter alongside `sat_uuid`, `sat_tg`, title, slug, and other base fields. The publishing vector reads a single file to get everything it needs. Language-specific fields are nested under locale keys within the frontmatter. Language-independent fields such as price and blade count appear once.

**Model B — content file references a data sidecar.** The Markdown file contains `sat_uuid`, `sat_tg`, title, slug, and body prose. Structured product data lives in a separate YAML sidecar — for example `henson-aircraft-aluminum.yml` alongside `henson-aircraft-aluminum.md`. The publishing vector reads both. Language-independent structured data lives cleanly in the sidecar without locale nesting. Language-specific prose lives in the Markdown file.

Model A is simpler — one file per document. Model B separates prose from structured data, which matters when structured data is complex, has its own translation concerns, or needs to be consumed independently by non-publishing-vector tools such as a pricing API or PDF catalog generator.

For the Henson collection specifically, product data is bilingual in some fields (title, description, alt text) and language-independent in others (price, blade count, finish colour name in the archive language). Model A forces bilingual fields to use locale-keyed nesting in frontmatter. Model B lets the sidecar carry language-independent data cleanly, with the Markdown file carrying the language-specific content.

**Decision needed:** which model does SAT adopt as the base schema? Is the choice collection-type-specific — Model B for `product-catalog`, Model A for `documentation` — or is one model universal?

#### 2. Required versus optional frontmatter fields

The base schema must define which fields are required in every conformant SAT document regardless of collection type, and which are optional.

Candidates for required:

- `sat_uuid` — established in ADR-010, required
- `sat_tg` — established in session, required when a translation relationship exists, optional otherwise
- `title` — human-readable document title in the language of the archive
- `slug` — the URL-safe identifier used to construct the path, in the language of the archive
- `created` — ISO 8601 date of document creation
- `sat_version` — the SAT schema version this document conforms to

Candidates for optional:

- `modified` — ISO 8601 date of last modification
- `draft` — boolean, whether the document is a draft
- Any collection-type-specific fields

The question of whether `created` and `slug` are required or optional is genuinely open. `created` is language-independent — it should be the same across all translations. `slug` is language-specific — the English slug and French slug are different.

**Decision needed:** which fields are required, which are optional, and which are language-independent versus language-specific?

#### 3. Dublin Core fragment merge semantics

The `.{slug}_meta/dublin-core/` directory may contain both a `dublin-core.yml` base file and granular fragment files such as `dc-relation.yml` and `dc-rights.yml`.

When both are present, the merge rule must be defined. Two candidates:

- **Override** — the fragment file replaces the corresponding element in `dublin-core.yml` entirely. A `dc-rights.yml` fragment replaces `dc:rights` in `dublin-core.yml`.
- **Additive** — the fragment file adds to the corresponding element. A `dc-relation.yml` fragment adds relations to any `dc:relation` entries already in `dublin-core.yml`.

The answer is probably element-specific. `dc:rights` is a scalar — override is correct. `dc:relation` is a list — additive is correct. `dc:title` is a scalar — override is correct.

The same question applies between cascade levels. Does a document-level `dc:rights` replace the archive-level `dc:rights`, or can it add to it? For rights the answer is almost certainly replace. For `dc:relation` the answer is almost certainly additive — a document-level relation does not cancel archive-level relations.

**Decision needed:** define the merge semantics per element type, or define a general rule with explicit exceptions.

#### 4. collection/description.md schema

`collection/description.md` in `.{language}_meta/collection/` is a SAT document. It has a `sat_uuid` and participates in the translation workflow via `sat_tg`.

But its frontmatter schema is different from a content document. It does not have a `slug` in the URL-path sense — it is not published as a navigable page. It does not have a price or purchase link. It may have a `title` — the name of the collection in this language — and a `created` date.

**Decision needed:** does `collection/description.md` use the base document schema with a subset of fields, or does it have its own schema defined separately? What fields are required?

### Open questions — important but deferrable

#### 5. Collection-type-specific schema extensions

ADR-011 defines a controlled vocabulary of collection types including `product-catalog`, `documentation`, `archive`, `publication`, `portfolio`, and `mixed`. Each type implies different document fields.

A `product-catalog` document needs price, purchase links, and product identifiers. A `documentation` document needs version, product name, and applicable software version. A `publication` document needs chapter number, part, and ISBN.

**Decision needed:** does ADR-012 define type-specific schema extensions, or does it define only the base schema and defer type-specific extensions to separate documents? If the latter, are those separate ADRs or a different kind of specification document?

#### 6. Slug language-independence question

The `slug` field is language-specific — `henson-aircraft-aluminum` in English, `henson-aluminium-aeronautique` in French. This is established in the architecture and aligns with ADR-013's principle of language-native paths.

However, the `sat_uuid` is language-independent. A publishing vector that needs to construct a URL for a translated document must read the `slug` from the correct language archive's document. There is no cross-language slug lookup.

**Decision needed:** is this confirmed as the correct behaviour — slug is always language-specific, always read from the document in the target language archive — or is there a case for a language-independent canonical slug that the language-specific slug overrides?

## References

- ADR-010: Document identity and cross-language linking (v0.1.3)
- ADR-011: SAT collection model
- ADR-012: Conformant document schema (v0.1.1)
- ADR-018: Universal assets directory convention
- ADR-022: Work assignment, expression joining, and the work index
- ADR-023: Metadata cataloging at content ingress (Proposed)
- ADR-025: Role-named assets directories, sparse inheritance, and the resolution order (Proposed)
- Complete Filesystem Cascade: Goals (v0.2.0)
- Dublin Core Metadata Initiative. (2024). *DCMI metadata terms*. https://www.dublincore.org/specifications/dublin-core/dcmi-terms/

## Changelog

| Version | Status | Notes |
|---|---|---|
| 0.2.0 | Superseded | All six questions resolved or dissolved by ADR-012 and ADR-018 through ADR-025; resolution table added mapping each question to its resolving decision; residues (structured-data placement, additive-list merge, type extensions) confirmed as tracked in living documents; original text preserved below the table with a staleness warning on the settled section |
| 0.1.0 | Todo | Initial todo document — open questions to resolve before ADR is written |
