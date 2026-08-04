# ADR-007: Entity Naming and Scoping via Hierarchical Semantic Containers

## Status
Accepted

## Context

In the semantic container model for archival and knowledge systems, entities are represented as directory-based containers rather than flat filenames.

A design question arises:

> Should entity names be globally unique, or only unique within a given directory scope?

This becomes especially important in distributed systems, multilingual archives, and DataLad-compatible dataset structures where replication, federation, and nesting are expected.

---

## Decision

Entity names are **not globally unique**.

Instead, entity identity is defined by:

> The full hierarchical path within the repository.

Example:

```text
architecture/adrs/adr-001-language-as-filesystem-structure/
research/adrs/adr-001-language-as-filesystem-structure/
```

These are valid and distinct entities.

------

## Consequences

### Positive

- Eliminates need for global naming registry
- Supports natural filesystem semantics
- Enables federation and dataset nesting
- Aligns with Git and DataLad path-based identity
- Allows reuse of semantic identifiers across domains
- Supports multilingual and domain-separated archives

------

### Negative

- Requires contextual awareness of entity location
- Names alone are not sufficient identifiers
- Potential ambiguity if paths are not preserved in external references

------

## Design Principles

This decision is based on the following principles:

1. **Path is identity**
   - The full directory path defines uniqueness
2. **Locality of meaning**
   - Entities are meaningful within their containing archive
3. **No global namespace assumption**
   - The system does not require centralized naming coordination
4. **Composable structure**
   - Entities can be reused across different branches of the archive

------

## Alignment with DataLad

This model aligns directly with DataLad's architecture:

- Datasets are identified by their repository path
- Subdatasets enable nested identity scopes
- No global registry of dataset names is required
- Git-based systems inherently resolve identity via path + history

------

## Implications for Semantic Container Model

Under this decision:

```text
entity/
  index.md
  meta/
```

becomes:

- A scoped unit of meaning
- Uniquely identified only within its parent container
- Freely reusable across different archive branches

------

## Conclusion

Entity naming in the semantic container model is **scoped, not global**.

This ensures scalability, supports federation, and aligns with DataLad and Git-based distributed architectures while preserving human-readable organization.

------

## Keywords (CAP)

ENTITY NAMING
SCOPED IDENTIFIERS
SEMANTIC CONTAINERS
DISTRIBUTED ARCHIVES
PATH-BASED IDENTITY
FEDERATED REPOSITORIES
DATASET SCOPING
DATA PRESERVATION SYSTEMS