# ADR-003: IANA Language Subtag Registry as Authoritative Source
# Status: Accepted
# Date: 2026-04-14

## Context

SAT uses BCP 47 language tags as directory names (ADR-001, ADR-002).
The pipeline must validate these names and enforce canonical casing.
Two options exist: SAT maintains its own lookup table, or SAT defers
to an external authoritative source.

## Decision

The IANA Language Subtag Registry is the single authoritative source
for language directory name validation in SAT. SAT does not define or
maintain a language naming convention. It defers entirely to the
registry.

```text
https://www.iana.org/assignments/language-subtag-registry
```

Canonical casing follows the registry convention:

```text
primary language subtag  → lowercase   (en, fr, ase)
region subtag            → UPPERCASE   (CA, GB, FR)
script subtag            → Title case  (Latn, Cyrl)
variant subtag           → lowercase   (blasl)
```

## Alternatives Considered

**SAT-maintained lookup table** — rejected because it creates a
maintenance burden, can fall out of sync with the actual standard,
and requires SAT-specific knowledge that the registry already provides
universally.

**Case-insensitive matching with normalisation** — rejected because
it obscures errors and produces inconsistent directory names across
different operating systems and filesystems.

**All-lowercase SAT convention** — rejected because it requires
learning a SAT-specific rule and departs from the universally
understood canonical form without providing any benefit for human
or machine readability.

## Consequences

- New languages added to the IANA registry are automatically supported
  by SAT without any code changes
- Deprecated tags with preferred values are handled by the registry
- Pipeline validation requires access to the registry or a cached copy
- The registry is a large text file — pipeline tooling must implement
  efficient lookup
- Human contributors can validate directory names using standard BCP 47
  tools without SAT-specific knowledge

## References

- Language in SAT: A Structural Approach v0.0.4
  en/docs/language/language-in-sat.md
- BCP 47: Tags for Identifying Languages
  https://www.rfc-editor.org/rfc/bcp/bcp47.txt
- IANA Language Subtag Registry
  https://www.iana.org/assignments/language-subtag-registry