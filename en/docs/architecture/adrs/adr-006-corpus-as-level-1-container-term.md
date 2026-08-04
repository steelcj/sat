# ADR-006: Corpus as the Term for the Level 1 Container
```yaml
Status: Rejected
Date: 2026-05-11
Rejected: 2026-05-13
```

## Rejection Rationale

 "Corpus" is highly technical domain vocabulary from linguistics and computational text analysis. It carries connotations — annotated text collections, statistical analysis, NLP training data — that do not match what SAT's level 1 container actually is. The term raises the barrier to entry for operators outside that domain without providing structural clarity in return. The level 1 container term remains "collection" as established in the SAT Filesystem and Configuration Cascade Specification.

## Context

SAT uses the term "collection" for the Level 1 directory scope — the
container that groups all language archives belonging to a single site,
project, or publication. `universalcake.com/` is a SAT collection.
`vishpala.org/` is a SAT collection. The SAT root contains multiple
SAT collections.

Sveltia CMS, identified as the authoring interface for the SAT content
tier, uses the term "collection" for an entirely different concept: a
content type definition with a named field schema pointing to a folder
in the repository. A Sveltia collection is equivalent to a Plone
Dexterity content type — it defines what fields a document has, not
where it lives in the hierarchy.

These two uses of "collection" refer to orthogonal concepts and will
appear together in documentation, configuration, and conversation as
SAT and Sveltia CMS are used alongside each other. The collision is
not resolvable by context — both concepts are present in the same
documents and the same tooling decisions.

## Decision

The Level 1 container in SAT is renamed from "collection" to "Corpus"
(singular) and "Corpora" (plural).

```text
sat/
├── universalcake.com/    ← Corpus
├── vishpala.org/         ← Corpus
└── sat-docs/             ← Corpus
```

The SAT root contains multiple Corpora. Each Corpus contains one or
more language archives at Level 2. The Corpus carries shared metadata
defaults — `dc:rights`, `dc:creator`, `dc:identifier` — that cascade
into every archive it contains.

Corpus is used in formal specification and documentation. The CLI and
tooling may surface Corpus as the user-facing term or adopt an
equivalent operational term (see Alternatives Considered).

## Alternatives Considered

**Nebula** — memorable, unused in adjacent tooling, and the metaphor
holds: a nebula contains many distinct bodies in a shared space.
Considered for the CLI and tooling layer where memorability outweighs
formal precision. Not chosen as the primary term because it requires
explanation in every formal context and does not carry the archival
weight that Corpus does. Remains a candidate for the tooling register
alongside Corpus in the specification.

**Domain** — accurate for the common case where the Level 1 scope maps
to a DNS domain. Rejected because it is overloaded in computing and DNS
contexts and does not generalise to non-web publications.

**Site** — plain and accurate for the web case. Rejected because it is
too narrow — a SAT Corpus may be a project, a publication, or an
archive that is not a website.

**Publication** — accurate in the archival sense. A publication contains
language editions. Rejected in favour of Corpus because Corpus is more
precise in the library science and Dublin Core tradition that SAT's
metadata model is grounded in.

**Retaining "collection" with a SAT-specific qualifier** — for example
"SAT collection" vs "Sveltia collection". Rejected because qualifier
discipline degrades in practice. Documentation authors drop qualifiers
under time pressure and the ambiguity returns.

## Consequences

- The Level 1 scope is unambiguously named in all contexts where SAT
  and Sveltia CMS documentation appear together
- "Collection" is freed for use in the Sveltia sense without collision
- The following documents require updates:
  - SAT Filesystem and Configuration Cascade Specification — version
    bump to 0.0.3, Section 1.1 Level 1 definition, all instances of
    "collection" referring to Level 1
  - `en/docs/architecture/three-tier-architecture.md`
  - `en/docs/architecture/declarative-archive-architecture-in-sat.md`
  - `README.md`
  - Any `definitions/` YAML files that use "collection" as a key
- The plural form Corpora is standard Latin and established in both
  archival and linguistic literature. New contributors unfamiliar with
  the Latin plural will encounter it once and remember it.
- CLI commands and tool names that currently use "collection" as a
  subcommand or argument will be updated in the next tooling release

## References

- ADR-001: Language as Filesystem Structure
- ADR-004: Self-Replicating Permission Model
- SAT Filesystem and Configuration Cascade Specification v0.0.2
  en/docs/specifications/sat-filesystem-and-configuration-cascade-specification-v0.0.2.md
