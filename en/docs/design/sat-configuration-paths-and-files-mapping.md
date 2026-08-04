# SAT configuration paths and files mapping

## Description

### SAT Mapping

Mapping out SAT configuration files and paths

## Goals

The goals are to:

* Come up with standard configuration locations using a repeatable pattern
* Make it easier to configure SAT

* Gather all yml configs that SAT currently produces
* Uncover better configuration design patterns
* Create a desired design pattern for mapping out configuration paths and files

> **Naming note.** Every assets directory name below is the literal per-entity transform of [ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md): `.<name>.assets`, inside the directory it describes, beside the file it describes. The root below is literally named `sat`, so its assets directory is `.sat.assets/` — any other instance name would produce `.<that-name>.assets/`. Records inside are organized by role-named directories per [ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md).

## sat/

The sat root directory — dual-role (instance + collection), so its assets directory carries two role directories.

```yaml
sat_root: sat
```

### .sat.assets/collection/

The collection role's records ([ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §2), written at creation ([ADR-026](../architecture/adrs/adr-026-full-chain-creation-the-instantiation-preseed-and-seeding-v0-2-3.md)).

```yaml
children.yml
collection.yml
dc.yml
fixity.yml
identity.yml
provenance.yml
```

### .sat.assets/sat/

The instance role's records. `dc.yml` (the `dc` vocabulary per [ADR-028](../architecture/adrs/adr-028--dublin-core-namespace-dc--for-mvp-dcterms--deferred.md)) is sparse and resolves deepest-stated-value-wins through the five operator tiers ([ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §7) — what `satlib.cascade` walks today. [ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md) §2 would interleave each tier's shipped floor file (`en/bin/sat/defaults/<tier>/metadata/dc.yml`) immediately before that tier's operator `dc.yml`, making nine layers; that ADR is Proposed and no code reads the floor yet.

```yaml
children.yml
dc.yml
fixity.yml
identity.yml
provenance.yml
```

### collections/

A directory where collections of archives are stored

```yaml
collections_root: collections
```

#### test-collection/

A collection directory contains one or more language archives. Its collection-role records live inside it, in `.test-collection.assets/collection/` — the ADR-018 transform of the directory's own name, never a generic `.sat.assets/`. Discovery locates and reconciles the role directories ([ADR-024](../architecture/adrs/adr-024-discovery-and-reconciliation-v0-2-2.md)).

##### en

A language archive. Its archive-role records live inside it, in `.en.assets/archive/` (identity, provenance, sparse `dc.yml`, `language.yml`, `children.yml` — [ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §2).

```yaml
language_archive_root: en
```

###### docs

A language archive's documents_root. As a content organizing directory, it carries its content-role records in `.docs.assets/content/` where minted (at first ingress or `content init` — [ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §9).

```yaml
documents_root: docs
```

**Content**

An example of content in the form of a markdown document.

```yaml
sample.md
```

The document's records ride beside it in `.sample.md.assets/content/` (`dc.yml`, `provenance.yml`, `fixity.yml`, `identity.yml`) — a file's assets directory sits beside the file, and keeps the full filename including extension ([ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md)). Media belonging to the document lives *inside* that assets directory (e.g. `.sample.md.assets/figure-1.svg`), never as a dot-file sibling of the document.

##### staging

Staging directory for working with archives and content

```yaml
bienvenue.md
note-de-service.md
welcome.md
```

## References

- [ADR-018: Universal Assets Directory Convention](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md)
- [ADR-024: Discovery and Reconciliation](../architecture/adrs/adr-024-discovery-and-reconciliation-v0-2-2.md)
- [ADR-025: Role-Named Assets Directories, Sparse Inheritance, and the Resolution Order](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md)
- [ADR-026: Full-Chain Creation, the Instantiation Preseed, and Seeding](../architecture/adrs/adr-026-full-chain-creation-the-instantiation-preseed-and-seeding-v0-2-3.md)
- [ADR-028: Dublin Core Namespace — dc: for MVP, dcterms: Deferred](../architecture/adrs/adr-028--dublin-core-namespace-dc--for-mvp-dcterms--deferred.md)
- [ADR-032: The Shipped Defaults Floor Below the Operator Cascade](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md)


