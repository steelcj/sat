# ADR-001: Language as Filesystem Structure
# Status: Accepted
# Date: 2026-04-14

## Context

SAT needs to handle multilingual content archives. The conventional
approach in CMS and static site generator systems is to represent
language as a metadata value — a `dc:language` field in a sidecar, a
`lang` key in frontmatter, or a configuration value in a site generator.
This approach is unreliable because the value can be absent, wrong, or
inconsistent across documents in the same archive.

## Decision

Language is expressed by the filesystem directory name at the archive
root. Every archive is a language archive. The directory name is the
language declaration. No metadata value is required to determine the
language of a document — the path provides it.

```text
universalcake.com/
  en/       ← English archive
  fr-CA/    ← Quebec French archive
  ase/      ← American Sign Language archive
```

The pipeline derives `dc:language` (ISO 639-2) and `dc:language_bcp47`
(BCP 47) from the directory name automatically. Authors do not supply
language metadata for individual documents.

## Alternatives Considered

**Frontmatter language field** — rejected because it is optional,
author-dependent, and silently defaults to English when absent.

**Collection-level language configuration** — rejected because it
applies a single language to all documents in a collection, which does
not support multilingual collections.

**Language subdirectory as convention only** — rejected because
convention without structural enforcement is indistinguishable from
metadata after the fact.

## Consequences

- Language cannot be missing from any document
- Language cannot be inconsistent within an archive
- SAT tools themselves live in language archives (`sat/en/`)
- Mixed language archives require a naming convention (see ADR-002)
- Sign languages are first-class archives, not accessibility sections
- The pipeline must map BCP 47 directory names to ISO 639-2 for DC
  metadata output

## References

- Language in SAT: A Structural Approach v0.0.4
  en/docs/language/language-in-sat.md