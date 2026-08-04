# ADR-008: Top-Level Repository Structure with Language-Scoped Archives

## Status
Accepted

## Context

The system is a semantic container architecture designed for distributed, multilingual, and DataLad-compatible archival structures.

Earlier assumptions treated language directories (`en/`, `fr/`) as top-level or parallel structures. This is incorrect for the intended model.

The system requires:
- a single unified repository root
- language-scoped archival layers inside the repository
- consistent structure across all languages
- support for entities, collections, and archives within each language domain

---

## Decision

The repository root is a **unified archive container** that contains language-scoped sub-archives.

### Canonical structure

```text
repository/
  en/
    archives/
    collections/
    entities/
    content/

  fr/
    archives/
    collections/
    entities/
    content/

  <other-languages>/
    archives/
    collections/
    entities/
    content/ 
```

## Key Principles

### 1. Repository as a unified archive system

The root `repository/` is itself an archive container, not a functional partition.

It serves as:

- a global aggregation layer
- a synchronization boundary (e.g., DataLad dataset root)
- a federation entry point

------

### 2. Language-scoped structural replication

Each language directory is a **complete structural mirror** of the system:

- archives
- collections
- entities
- content

This ensures:

- consistent navigation across languages
- independent evolution of language-specific content
- predictable automation and tooling behavior

------

### 3. No top-level functional separation outside language scope

The system does NOT use:

```text
repository/archives/
repository/entities/
```

Instead, all functional separation occurs **within each language scope**.

------

## Rationale

### 1. Multilingual integrity

Each language is a self-contained archival ecosystem, not a partial view of a global structure.

### 2. DataLad compatibility

Each language directory can function as:

- a subdataset
- a replication unit
- a federated node

### 3. Avoids cross-language structural drift

By replicating structure per language:

- schema consistency is preserved
- translation workflows remain aligned
- structural evolution is synchronized

------

## Consequences

### Positive

- Strong multilingual consistency model
- Clear separation of language domains
- Each language can be independently versioned and federated
- Aligns with dataset/subdataset logic in DataLad

------

### Negative

- Structural duplication across languages
- Requires synchronization of schema changes
- Slightly higher maintenance overhead for structural updates

------

## Alternatives Considered

### 1. Global functional directories

```text
repository/
  archives/
  entities/
  collections/
  en/
  fr/
```

Rejected due to:

- cross-language fragmentation
- inconsistent structural mapping per language

------

### 2. Language-only root partitioning

```text
en/
fr/
```

Rejected because:

- loses global repository identity
- weakens archive-level aggregation
- reduces federation clarity

------

## Implementation Notes

- Each language directory MAY be a DataLad dataset

- Internal structure MUST remain consistent across languages

- Entities SHOULD be self-contained semantic containers:

  ```text
  entity-name/
    index.md
    meta/
    assets/
  ```

- Cross-language linking SHOULD occur at entity metadata level, not structure level

------

## Alignment with Prior ADRs

- ADR-006: Entity Naming and Scoping via Hierarchical Semantic Containers
- ADR-007: Semantic Container Model for Entity-Centric Architecture

This ADR refines those models by introducing **language-scoped structural replication**.

------

## Keywords (CAP)

MULTILINGUAL ARCHITECTURE
SEMANTIC CONTAINERS
DATA LAD STRUCTURE
FEDERATED ARCHIVES
LANGUAGE SCOPING
REPOSITORY DESIGN
DISTRIBUTED KNOWLEDGE SYSTEMS
ENTITY-BASED ARCHITECTURE

```
---
```