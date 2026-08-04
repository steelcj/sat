# ADR-002: Mixed Language Archive Naming Convention
# Status: Accepted
# Date: 2026-04-14

## Context

Some content genuinely exists in more than one language simultaneously
— Franglais literature, bilingual educational resources, ASL and English
mixed presentations. This content cannot be accurately placed in a
single-language archive without misrepresenting it. SAT's structural
language model (ADR-001) requires a directory naming convention that
can express this plurality.

## Decision

Mixed language archives use BCP 47 language tags joined by underscores
in alphabetical order:

```text
en-CA_fr-CA/    ← Canadian English and Quebec French
ase_en/         ← ASL and English
ar_fr/          ← Arabic and French
```

Alphabetical order is used because it is deterministic and politically
neutral. The directory name makes no statement about primacy. Primacy
is declared explicitly in `languages.yml` using the `role: primary`
field when human judgment about cultural or linguistic centrality is
needed.

Each component must be a valid BCP 47 language tag in canonical casing
as defined by the IANA Language Subtag Registry.

## Alternatives Considered

**Primary language first** — rejected because it encodes a political
statement about which language matters more into the directory name
itself, which is inappropriate for content that deliberately exists
between languages.

**Single flat directory with metadata** — rejected because it collapses
the mixed archive into an ambiguous category and loses the structural
clarity that makes SAT's language model work.

**A separate `mixed/` directory type** — rejected because it creates
a generic catch-all that obscures which languages are actually present.

## Consequences

- The IANA registry validates the components; SAT defines only the
  joining convention
- Pipeline must split on underscore and validate each component
  separately
- `languages.yml` carries the primacy declaration when needed
- The convention is extensible to any number of languages

## References

- Language in SAT: A Structural Approach v0.0.4
  en/docs/language/language-in-sat.md
- IANA Language Subtag Registry
  https://www.iana.org/assignments/language-subtag-registry