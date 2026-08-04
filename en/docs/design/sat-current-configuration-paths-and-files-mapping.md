---
dc:title: "SAT Configuration Paths and Files Mapping"
dc:description: "The original current-state mapping of SAT configuration paths and files, re-expressed in the shared vocabulary: scopes, records, carriers, and the canonical metadata record."
dc:creator: "Christopher Steel"
dc:contributor: "Claude Opus 4.8 (Anthropic)"
dc:publisher: "Christopher Steel"
dc:date: "2026-08-04"
dc:modified: "2026-08-04"
dc:type: "Text"
dc:format: "text/markdown"
dc:language: "en"
dc:language_bcp47: "en"
dc:rights: "https://creativecommons.org/licenses/by-sa/4.0/"
dc:subject:
  - SAT
  - configuration
  - paths and files
  - mapping
  - assets
dc:identifier: "sat-configuration-paths-and-files-mapping"
---

# SAT Configuration Paths and Files Mapping

## Description

Mapping out SAT configuration files and paths. This is the original current-state map, re-expressed in the shared vocabulary (see *SAT Configuration — Definitions and Vocabulary*): each directory is named by its **scope**, each file by its **payload kind**, and each grouping by its **carrier**. It describes the layout as recorded today; it is not the target pattern.

> **Reading note.** `dc.yml` is the **canonical metadata record**; `dc` is the current value of the `canonical-metadata` setting ([ADR-028](../architecture/adrs/adr-028--dublin-core-namespace-dc--for-mvp-dcterms--deferred.md)), not a fixed part of the name. Assets directory names follow the literal per-entity transform of [ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md): `.<name>.assets`, inside the directory it describes, beside the file it describes.

## Goals

The goals are to:

* Come up with standard configuration locations using a repeatable pattern
* Make it easier to configure SAT
* Gather all the records and metadata SAT currently produces
* Uncover better configuration design patterns
* Create a desired design pattern for mapping out configuration paths and files

---

## sat/

The SAT instance root — **dual-role** (it is both the *sat* scope and a *collection* scope).

```yaml
sat_root: sat
```

### .sat.assets/

The instance's **assets directory** (the in-tree records carrier): the per-entity assets directory of a root literally named `sat` — the [ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md) transform of the directory's own name, not a fixed name; an instance named otherwise gets `.<that-name>.assets/`. It holds one role-named subdirectory per role the root bears ([ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md)) — here two, because the root is dual-role. Records are written at creation by tier tooling ([ADR-026](../architecture/adrs/adr-026-full-chain-creation-the-instantiation-preseed-and-seeding-v0-2-3.md)) and reconciled after filesystem changes by discovery ([ADR-024](../architecture/adrs/adr-024-discovery-and-reconciliation-v0-2-2.md)).

Each role's sparse `dc.yml` resolves deepest-stated-value-wins through the **five operator tiers** ([ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §7) — the walk `satlib.cascade.layers_for` performs today. [ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md) §2 would read each tier's shipped-floor file (`en/bin/sat/defaults/<tier>/metadata/dc.yml`) immediately before that tier's operator `dc.yml`, making nine layers; that ADR is Proposed and the floor has no reader in `satlib`.

### .sat.assets/collection/

The **collection-scope** records, carried in the instance's assets directory.

```yaml
children.yml      # children record
collection.yml    # collection record
dc.yml            # canonical metadata record   (canonical-metadata: dc)
fixity.yml        # fixity record
identity.yml      # identity record
provenance.yml    # provenance record
```

### .sat.assets/sat/

The **sat-scope** records, carried in the instance's assets directory. Same record kinds as the collection scope, minus the collection record.

```yaml
children.yml      # children record
dc.yml            # canonical metadata record   (canonical-metadata: dc)
fixity.yml        # fixity record
identity.yml      # identity record
provenance.yml    # provenance record
```

### collections/

The collections root — where collections of archives are stored.

```yaml
collections_root: collections
```

#### test-collection/

A **collection** (collection scope). A collection contains one or more language archives. Its own collection-scope records are carried in its own assets directory: `.test-collection.assets/collection/` — the [ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md) transform of the collection's own name, never a generic `.sat.assets/`.

##### en

A **language archive**, rooted at **language root** `en` (archive scope). Its archive-scope records ride in `.en.assets/archive/` (identity, provenance, sparse `dc.yml`, `language.yml`, `children.yml` — [ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §2).

```yaml
language_archive_root: en
```

###### docs

The **documents directory** — the standard content location `<language-root>/docs` (content-directory scope). As a content organizing directory it carries its content-role records in `.docs.assets/content/` where minted (at first ingress or `content init` — [ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §9).

```yaml
documents_root: docs
```

**Content**

The content itself. Each document is a **body payload**. Everything about the document rides in its own assets directory beside it ([ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md) — a file's assets directory sits beside the file and keeps the full filename): its records (canonical metadata record, provenance, fixity, identity) in `.sample.md.assets/content/`, and any associated **content-media payloads** *inside* the same assets directory (e.g. `.sample.md.assets/figure-1.svg`) — never as dot-file siblings of the document.

```yaml
sample.md         # body payload
```

##### staging

A staging area for working with archives and content — a holding area for **body payloads** not yet brought under management (the *nursery* role in current tooling).

```yaml
bienvenue.md      # body payload (work in progress)
note-de-service.md
welcome.md
```

---

## Vocabulary key

- **Scope** — the role a node/payload belongs to: *sat* (instance), *collection*, *archive* (language archive), *content-directory*, *content* (item).
- **Record** — a metadata payload about a node: identity, provenance, canonical metadata, fixity, children, collection.
- **Canonical metadata record** — a node's descriptive metadata in the vocabulary named by the `canonical-metadata` setting (currently `dc`, [ADR-028](../architecture/adrs/adr-028--dublin-core-namespace-dc--for-mvp-dcterms--deferred.md)).
- **Carrier** — how a payload is stored in-tree: the **assets directory** — a per-entity `.<name>.assets/` directory, inside a directory / beside a file ([ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md)), holding one role-named record directory per role the entity bears ([ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md)).
- **Sidecar** — reserved for the egress/transmog output sense only: the three metadata sidecar types (`dc.yml`, `og.yml`, `schema.yml`) the pipeline emits into its output tree ([ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md)). Not an in-tree carrier — ADR-018 absorbed the former root sidecars into assets directories.
- **Body payload** — a content document; the material being described, not an asset.
- **Language root / documents directory** — the top-level language directory (`en`) and its standard content location (`<language-root>/docs`).
