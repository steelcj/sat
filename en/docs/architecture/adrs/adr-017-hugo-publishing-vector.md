# ADR-017: Hugo Publishing Vector (hugo-transmog)

```yaml
status: HOLD
date: 2026-07-12
```

## Description

Ignore this ADR for now. We will resume work on this once the required infrastructure for SAT has been implimented.

On hold pending implementation of ADR-010 v0.1.1 identity infrastructure (per-expression `dc:identifier`, `sat:work`). Section 4 in particular reflects superseded ADR-010 semantics.

All of the information contained in this ADR is subject to change depending on SAT development

## Context



SAT archives are pure content — no publishing-vector frontmatter, no SSG-specific
metadata embedded in documents (ADR-012). Publishing vectors are responsible for
reading the canonical metadata sidecar structure and producing whatever output
their target SSG requires. This ADR defines the architectural decisions for the
Hugo publishing vector.

Hugo is the first publishing vector implemented for SAT. The decisions made here
establish patterns that subsequent vectors (mkdocs-transmog, eleventy-transmog,
and others) will follow. Getting the architecture right matters beyond Hugo itself.

Three questions drive this ADR:

**Output format.** Hugo supports both flat content files
(`content/posts/my-slug.md`) and leaf bundles
(`content/posts/my-slug/index.md`). The choice is structural and
difficult to reverse once a Hugo site is in production.

**Phase separation.** Transforming DC metadata into Hugo frontmatter and
assembling the final Hugo content tree are two distinct operations with
different permission requirements, different triggering conditions, and
different consumers. Whether they belong in one tool or two is an
architectural question.

**Section mapping.** SAT archives use language-native content directory
names (`products/` in English, `produits/` in French). Hugo uses a
single language-neutral `content/` tree. The mapping between them must
be derived from the archive structure rather than configured separately.

## Decision

### 1. Leaf bundles as the output format

Hugo leaf bundles — `content/{section}/{slug}/index.md` — are the
output format for the Hugo publishing vector.

Hugo has been progressively deprecating flat content files in favour of
bundles. Bundles are where Hugo's content model is settled. Building on
the native convention now means `hugo-transmog` does not need to be
revisited when Hugo eventually makes bundles mandatory or when themes
start assuming bundle layout.

Leaf bundles also align with SAT's own document model. ADR-012 treats
each document as a directory-scoped unit — the document file plus its
`.{slug}_meta/` sibling directory. Hugo's leaf bundle is the same
mental model: a document is a directory, not a flat file. The
structural consistency between the SAT archive representation and the
Hugo output representation reduces cognitive load for operators working
across both.

When SAT documents gain asset support (images, diagrams, attachments),
those assets have a natural home in the bundle directory alongside
`index.md`. With flat files this would require retrofitting. With
bundles it is already correct.

### 2. Two-phase architecture

The Hugo publishing vector is implemented as two separate tools:

**Phase 1 — `hugo-transmog`** reads the SAT metadata cascade for each
document and writes a derived `hugo/frontmatter.yml` file inside the
document's `.{slug}_meta/` directory. This is the transmog step — it
transforms canonical DC metadata into Hugo vocabulary and caches the
result inside the archive.

**Phase 2 — `hugo-assemble`** reads each document's prose and its
cached `hugo/frontmatter.yml` and writes a Hugo leaf bundle to the
configured output directory. This is the assembly step — it produces
the Hugo content tree from the cached derivations.

The phases are independent. Phase 1 output is a file inside the SAT
archive. Phase 2 output is outside the archive entirely. They have
different permission requirements: Phase 1 requires Content Admin
write access to `.{slug}_meta/hugo/`; Phase 2 requires no archive
write access at all.

The filesystem watcher (ADR-014) triggers Phase 1 per-document when
metadata changes. Phase 2 is triggered by the operator or a build
pipeline. Coupling them into one tool would force the watcher to run
the assembly step on every metadata change, writing to the output
directory on every keystroke — incorrect behaviour.

### 3. Section mapping derived from the mirrored relationship

SAT archives use language-native content directory names. Hugo uses a
single language-neutral `content/` tree. The mapping between them is
not configured — it is derived from the `relationships` declaration in
`sat-collection.yml`.

For a `mirrored` relationship with a declared `language_source`:

```yaml
relationships:
  - type: mirrored
    language_source: /en
    archives:
      - /en
      - /fr
```

The Hugo section name for a document is the content directory name of
the corresponding document in the `language_source` archive, resolved
via `sat_uuid`. A French document in `fr/produits/` whose English
counterpart (`sat_uuid` match) lives in `en/products/` maps to Hugo
section `products/`. No explicit section map is required or supported.

For relationship types without a `language_source`
(`thematic-parallel`, `multilingual-original`), each archive's content
directory name is used as-is as the Hugo section name.

An unmapped document — one whose `sat_uuid` has no counterpart in the
`language_source` archive — produces a warning and uses the content
directory name as-is.

### 4. translationKey = sat_uuid

The Hugo `translationKey` frontmatter field links translations of the
same page across independently-pathed content directories. Per ADR-010,
the `sat_uuid` value is used directly as the `translationKey` value.
No mapping table is required. The UUID is both the SAT document
identity and the Hugo translation link.

```yaml
# Generated hugo/frontmatter.yml
sat_uuid: 7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e
translationKey: 7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e
```

The duplication is deliberate. `sat_uuid` is the SAT archive field.
`translationKey` is the Hugo field. They carry the same value by
convention in the Hugo vector. Other publishing vectors use `sat_uuid`
directly and do not require `translationKey`.

### 5. Shared filesystem library

`hugo-transmog` and `hugo-assemble` depend on filesystem walking and
DC cascade resolution that is not specific to Hugo. These concerns are
extracted into a shared library at `~/bin/sat-tools/lib/`:

```
~/bin/sat-tools/
  lib/
    sat_walk.py       ← filesystem walking, no registry dependency
    sat_config.py     ← reads ~/.config/sat/config.yml
    sat_cascade.py    ← five-level DC cascade resolver
  content/
    hugo-transmog.py
    hugo-assemble.py
```

`sat_walk.py` is a deliberately registry-free extraction of the
upward-walking logic in `bin/sat/lib/discovery.py`. The existing
`discovery.py` is admin-tier code tightly coupled to `registry.py` via
relative imports. Content-tier tools must not depend on registry
machinery — language context is read from the already-written
`language.yml`, not re-derived from the IANA registry.

### 6. Operator configuration

Machine-local configuration lives in `~/.config/sat/config.yml` under
a `transmogs:` section:

```yaml
transmogs:
  hugo:
    output_root: ~/projects/sat/output/hugo
    bundle_format: leaf
    draft_default: false
```

The `transmogs:` section is read-only to the transmog tools. They do
not write to `~/.config/sat/` under any circumstances. If the
`transmogs:` section is absent, `hugo-transmog` fails explicitly with
a message describing what must be added. It does not silently write
defaults.

## Alternatives Considered

**Flat content files** — rejected. Hugo is moving toward bundles as the
primary content model. Flat files would require migration when themes
assume bundle layout. Bundle output also aligns structurally with SAT's
own document-as-directory model.

**Single-phase tool combining transmog and assembly** — rejected. The
phases have different permission requirements and different triggering
conditions. The watcher (ADR-014) requires per-document Phase 1
triggering without running assembly. Coupling the phases forces
incorrect watcher behaviour.

**Explicit section_map in sat-collection.yml** — rejected. The
`mirrored` relationship type and `language_source` already carry the
information needed to derive the Hugo section mapping. An explicit
`section_map` would duplicate information already present in the
collection declaration, creating a second source of truth that can
diverge.

**Content-tier tools importing from `bin/sat/lib/`** — rejected. The
existing admin-tier lib is tightly coupled via relative imports.
Content-tier tools importing from it would cross the ADR-004 permission
boundary and drag in registry machinery that content-tier tools have no
business touching.

## Consequences

- Hugo leaf bundles are the output format; flat file output is not supported
- Two tools: `hugo-transmog` (Phase 1) and `hugo-assemble` (Phase 2)
- `hugo-transmog` writes `.{slug}_meta/hugo/frontmatter.yml` — one file per document
- `hugo-assemble` writes outside the archive entirely — no archive write access required
- Section mapping is derived from `sat-collection.yml` relationships, never configured
- `translationKey` = `sat_uuid` — the Hugo translation link is the SAT UUID
- A shared `~/bin/sat-tools/lib/` is introduced for registry-free filesystem walking
  and cascade resolution; the existing `bin/sat/lib/` is untouched
- `~/.config/sat/config.yml` is read-only to all transmog tools
- The two-phase pattern established here is the reference for all subsequent
  publishing vector implementations

## References

- ADR-001: Language as filesystem structure
- ADR-004: Self-replicating permission model
- ADR-005: Tool self-discovery from filesystem context
- ADR-010: Document identity and cross-language linking
- ADR-011: SAT collection model
- ADR-012: Conformant document schema
- ADR-014: Filesystem-event-driven tooling model (Todo)
- ADR-015: Slug pattern language and sidecar-derived slugs
- ADR-016: Operator wrapper script convention and sat-tools directory structure
- Hugo. (2026). *Page bundles*. The Hugo Authors.
  https://gohugo.io/content-management/page-bundles/
- Hugo. (2026). *Multilingual mode — translationKey*. The Hugo Authors.
  https://gohugo.io/content-management/multilingual/

## Licence

Copyright (C) 2026 Christopher Steel

This file is part of SAT (Source Archive Tools).

SAT is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

SAT is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public
License for more details.

You should have received a copy of the GNU Affero General Public
License along with SAT. If not, see <https://www.gnu.org/licenses/>.

This document was prepared with AI assistance from
**Claude Sonnet 4.6 (Anthropic)**.

## Changelog

| Version | Status   | Notes         |
| ------- | -------- | ------------- |
| 0.1.1 | HOLD | Placed on hold pending SAT identity infrastructure; body frozen as reference and subject to revision
| 0.1.0   | Proposed | Initial draft |
