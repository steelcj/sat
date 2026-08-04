# ADR-015: Slug Pattern Language and Sidecar-Derived Slugs
# Status: Proposed
# Date: 2026-06-04

## Context

SAT tools produce and manage files whose names carry metadata — date, author, language, type — encoded in ad hoc conventions that vary across archives and operators. The CV collection that motivated this ADR contained files named under at least five different conventions simultaneously: `cv_Christopher-Steel-2023-03-08-french.odt`, `2024-08-13-globalgreengrants-resume-christopher-steel.html`, `cv_Chris_Steel_Dec2016-en (copy).odt`. These are not pathological cases; they are the normal accumulation of naming decisions made independently over time, by the same operator, without a shared specification.

Two problems compound each other. The first is that the slug carries metadata the filesystem cannot query, validate, or normalise. A slug is a string; the date embedded in it is not a date to any tool that reads it, the author is not a person, and the language is not a language tag. The second is that there is no agreed vocabulary for what the parts of a slug mean. When we examined the CV collection we found that formalising the parts required reaching into archival science (provenance, facet, citation order), RDA (genre/form, content type), and Dublin Core (dc:date, dc:creator, dc:language) before we could describe what was already there informally.

A previous attempt to resolve this by embedding richer metadata directly in the slug failed. Trying to make the slug carry dc:provenance, a local variant term, and a language constraint simultaneously asked the filename to do a job it is not equipped for — it has no namespace, no schema, no way to express confidence or authority, and no way to be queried as data. The result was a pattern that was harder to read than the informal names it was meant to replace.

A second problem was the conflation of the slug creator's responsibilities with the ingress pipeline's responsibilities. Normalising `french` to `fr` is not the slug creator's job. By the time the slug creator writes a value it should already be canonical. Separating these concerns is a precondition for a clean design.

## Decision

### 1. The slug is derived from the sidecar, not the other way around

The DC sidecar is built first. The slug is a projection of the sidecar's values into a human-readable, sortable, filesystem-safe identifier. The slug asserts nothing on its own authority. A slug that reads `2023-03-08-cv-christopher-steel--fr` is a rendering of `dc:date`, `dc:type` (via `sat:genre`), `dc:creator`, and `dc:language_bcp47` from the sidecar — not four independent facts the filename is declaring.

This separation means the sidecar can carry the full authority record — provenance, confidence, the source of each value, the cascade level that supplied it — while the slug carries only what the operator considers useful for identification and sorting at the filesystem level.

### 2. A user-facing pattern language specifies the slug shape

The slug shape for a directory is declared by an operator-authored pattern string. The pattern string is the user interface; it is designed to be readable and writable without knowledge of the DC sidecar structure or the SAT namespace.

```text
{date}-{"cv"}-{author}--{for-org?}-{lang?en,fr}
```

The pattern string declares the citation order of the slug — the sequence of facet values from left to right — and whether each slot is required or optional. It does not declare where values come from; that is the token vocabulary's responsibility.

### 3. A token vocabulary maps pattern tokens to resolution sources

The token vocabulary is a YAML file that declares which tokens are available and where each token's value comes from. Resolution sources are DC elements, the filename cascade, or interactive operator prompt.

```yaml
date:    dc:date
author:  dc:creator
lang:    dc:language_bcp47
for-org: prompt
```

The vocabulary and the pattern are stored together in `slug-scheme.yml`. In the current implementation one `slug-scheme.yml` applies to one directory. The configuration cascade across archive, collection, and SAT levels is the intended future model.

### 4. The slug pattern language syntax

The pattern string syntax defines five constructs:

**Tokens** — `{name}` for required, `{name?}` for optional. An optional token and its preceding separator are omitted when no value is available.

**Literals** — `{"value"}` for constant strings that are the same for every file in the directory. Used when the value does not vary and a token lookup would be redundant.

**Single hyphen** — the standard separator between elements.

**Double hyphen** — a grouping separator that produces a literal `--` in the slug, marking a semantic boundary between the document identity group and the context group. Omitted when the right group is entirely absent.

**Output constraints** — `{name?value1,value2}` restricts the slug creator to writing only the declared values. A resolved value outside the constraint set causes the slug creator to fall through the configuration cascade; if no cascade level satisfies the constraint the token is treated as absent. Output constraints check canonical values; they do not perform normalisation.

### 5. Language values use dc:language_bcp47, not dc:language

The SAT sidecar holds language in two fields: `dc:language` as an ISO 639-2 three-letter code (`eng`, `fra`) and `dc:language_bcp47` as a BCP 47 two-letter tag (`en`, `fr`). Slug output constraints declare BCP 47 short forms. The token vocabulary must therefore map `lang` to `dc:language_bcp47`. A mapping to `dc:language` would never satisfy a constraint of `{lang?en,fr}` because the sidecar holds `eng`, not `en`.

### 6. Per-file slug scheme overrides use the filename.schema/ convention

Per-file slug scheme overrides are placed at `filename.schema/slug-scheme.yml`, consistent with the `filename.meta/` directory convention used for metadata sidecars. This allows multiple schema types to coexist in the same directory without naming collisions and without requiring a special case in the tool's file discovery logic.

### 7. Normalisation is the ingress pipeline's responsibility, not the slug creator's

The slug creator receives canonical values from the sidecar and writes them. It does not map `french` to `fr`, `francais` to `fr`, or `English` to `en`. That normalisation happens during ingress when the sidecar is built. The output constraint `{lang?en,fr}` checks the value the sidecar already holds; it does not transform it.

## Alternatives considered

**Embedding richer metadata directly in the slug** — rejected. A slug is an identifier, not a metadata record. It has no namespace, no schema, no authority model, and no query interface. Attempting to embed provenance, variant status, and language constraints in a filename produced a pattern harder to read than the informal names it was meant to replace. The sidecar is the right location for metadata; the slug is a projection of it.

**A single flat token vocabulary with no pattern layer** — rejected. Without a pattern string the operator cannot control citation order, separator style, or which tokens appear in a given directory's slugs. The vocabulary and the pattern are separate concerns: the vocabulary declares what tokens mean; the pattern declares how they are composed. Conflating them would require the vocabulary to carry ordering and formatting information it is not equipped to express.

**Deriving the slug from the filename directly, without a sidecar** — rejected. The filename is not a canonical declaration. The same information appears in at least three different forms in the CV collection alone (`french`, `francais`, `fr`). The slug creator cannot trust the filename to be normalised, complete, or consistently structured. The sidecar is built first precisely to resolve these inconsistencies before any slug is written.

**A single canonical slug format, fixed across all archives** — rejected. Different content categories require different facet schemes and different citation orders. A CV archive and a correspondence archive have different identification needs at the filesystem level. The pattern language accommodates this without requiring changes to the tool.

**Requiring the operator to declare language using ISO 639-2 codes in the pattern** — rejected. ISO 639-2 three-letter codes (`eng`, `fra`) are not the form operators use in filenames or recognise naturally. BCP 47 two-letter tags (`en`, `fr`) are the established human-facing convention. The sidecar holds both; the pattern language uses the form operators already know.

**Mapping `lang` to `dc:language` rather than `dc:language_bcp47`** — rejected. `dc:language` holds ISO 639-2 codes that would never satisfy a BCP 47 output constraint. Using `dc:language_bcp47` as the resolution source for slug language tokens keeps the vocabulary consistent with the form the constraint declares and the form that appears in filenames.

## Consequences

- The sidecar must exist before a slug can be written; the ingress pipeline builds it if absent
- The slug is reproducible — running the slug creator twice on the same sidecar produces the same slug
- Slug inconsistencies across a collection are detectable by comparing slugs against their sidecars
- The pattern language is readable without knowledge of DC or RDA; operators write `{author}` not `dc:creator`
- The double-hyphen grouping separator produces `--` in slugs; tooling that splits on single hyphens must account for this
- Language output constraints require `dc:language_bcp47` to be populated in the sidecar; archives that populate only `dc:language` will produce language-omitted slugs until `dc:language_bcp47` is added
- Per-file slug scheme overrides require the `filename.schema/` directory to exist; tools that do not create this directory will not support per-file overrides
- The configuration cascade across collection, archive, and directory levels is architectural intent; the current implementation is directory-scoped only

## References

- ADR-001: Language as Filesystem Structure
- ADR-002: Mixed Language Archive Naming Convention
- ADR-003: IANA Language Subtag Registry as Authoritative Source
- ADR-005: Tool Self-Discovery from Filesystem Context
- SAT Slug Pattern Language: User Interface Specification v0.2.2
- SAT Filesystem and Configuration Cascade Specification v0.0.2
- SAT Language Validation and Offline Registry Cache Specification sidecar
