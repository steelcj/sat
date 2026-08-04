---
dc:title: "SAT Configuration — Current Mapping"
dc:description: "A descriptive map of SAT's configuration as it exists today, expressed in the SAT configuration vocabulary: assets, payloads, carriers, scopes, and canonical metadata."
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
  - current mapping
  - assets
  - canonical metadata
dc:identifier: "sat-configuration-current-mapping"
---

# SAT Configuration — Current Mapping

A descriptive map of SAT's configuration **as it exists today**, re-expressed in the shared vocabulary (see *SAT Configuration — Definitions and Vocabulary*). This document reports the current state only; it makes no recommendations. Terms such as *asset*, *payload*, *carrier*, *scope*, and *canonical metadata record* are used as defined there.

> **Reading note.** Where a current file name embeds `dc` (e.g. `dc.yml`, `dc:` fields), that reflects the current value of the `canonical-metadata` setting (`dc` — [ADR-028](../architecture/adrs/adr-028--dublin-core-namespace-dc--for-mvp-dcterms--deferred.md)), not a fixed part of the model.

---

## 1. Orientation

- **Filesystem-first.** SAT keeps no runtime state and no database; all configuration is on-disk YAML.
- **Roles / tiers.** Four roles form the cascade, broad to narrow: **sat** (instance) → **collection** → **archive** (language archive) → **content**. The instance root is *dual-role* (sat + collection).
- **Tools.** Five tool groups under `en/bin/`: `sat`, `archives`, `collection`, `content`, `transmog` (transmog currently off).
- **`satlib`.** The newer tools (`sat`, `collection`, `content`) delegate discovery, roles, and the cascade to a shared `satlib` package; the older tools (`archives`, `transmog`) parse their own YAML and do not use it.
- **ADR-driven.** Behaviour is governed by Architecture Decision Records (ADR-003, -005, -021/022, -023, -029, -030, -033…), most centrally for this map: [ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md) (per-entity assets directories), [ADR-024](../architecture/adrs/adr-024-discovery-and-reconciliation-v0-2-2.md) (discovery and reconciliation), [ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) (role directories, sparse inheritance, resolution), [ADR-026](../architecture/adrs/adr-026-full-chain-creation-the-instantiation-preseed-and-seeding-v0-2-3.md) (full-chain creation and seeding), [ADR-028](../architecture/adrs/adr-028--dublin-core-namespace-dc--for-mvp-dcterms--deferred.md) (`dc:` namespace), [ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md) (shipped defaults floor), and [ADR-034](../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md) (concern parents; the derived mapping projection).

---

## 2. Two categories of configuration today

SAT's current configuration divides cleanly in the vocabulary:

- **Assets** — per-node payloads carried *parallel to* content in per-entity **assets directories** (`.<name>.assets/` — the literal [ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md) transform; inside a directory, beside a file), organized into role-named subdirectories ([ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md)). These are the records, canonical metadata, derived indexes, and media.
- **Configuration inputs** — files that are *not* per-node payloads: **definitions** (tool behaviour and what to build), **floor** (shipped baseline values that seed a cascade), and **preseeds & caches** (operator topology and lookup caches).

The rest of the document maps each category.

---

## 3. Where configuration lives — the roots

| # | Root | Holds (vocabulary) | Notes |
|---|------|--------------------|-------|
| R1 | `<repo>/en/bin/<tool>/definitions/` and `…/defaults/` | definitions + floor | shipped, versioned, read at runtime |
| R2 | `~/.config/sat/` | preseeds, `.meta`, caches | operator-owned; produced by `sat init` |
| R3 | `~/.local/share/sat-tool/<version>/` | seeded instance data | `sat_collection.path` in the preseed |
| R4 | `default_parent` (e.g. `~/projects/sat/…`) | the real collections and archives (bodies + assets) | a per-collection `parent:` overrides `default_parent:` |
| R5 | inside the instance tree | assets (per-node payloads) | where the cascade operates |

---

## 4. How SAT carries payloads today

This is the heart of the current map: which **carrier** delivers each **payload**, by **scope**. SAT today carries every in-tree payload in per-entity assets directories ([ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md)): role records in role-named subdirectories ([ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §2), and the content item's records and media in the file's own assets directory beside it. **Metadata sidecars** exist only as pipeline output — the three metadata sidecar types egress/transmog emit ([ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md)).

| Scope | Payload (kind) | Current carrier | Current location |
|---|---|---|---|
| SAT | identity, provenance, canonical metadata record, fixity, children, collection | parallel (tree) assets, in-tree | role directory `.<instance>.assets/sat/` inside the instance root (e.g. `.sat.assets/sat/` for an instance literally named `sat`) |
| Collection | identity, provenance, canonical metadata record, fixity, children, collection | parallel (tree) assets, in-tree | role directory `.<collection>.assets/collection/` (e.g. `.test-collection.assets/collection/`) |
| Archive | identity, provenance, canonical metadata record, fixity, children, language | parallel (tree) assets, in-tree | role directory `.<language>.assets/archive/` (e.g. `.en.assets/archive/`) |
| Content-directory | identity, provenance, canonical metadata record, children | parallel (tree) assets, in-tree | role directory `.<directory>.assets/content/` (e.g. `.docs.assets/content/`) |
| Content (item) | body payload | — (content, not an asset) | the document in the content tree |
| Content (item) | canonical metadata record | parallel (tree) assets, beside the file | `.<file>.assets/content/dc.yml` — the document's assets directory sits beside it ([ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md) §3); canonical, write-once |
| Content (item) | media payload | parallel (tree) assets, beside the file | *inside* the file's assets directory (e.g. `.my-doc.md.assets/figure-1.svg`, [ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md) §3–4) — never a dot-file sibling of the document |
| Content (item) | derived metadata (og, schema) | **metadata sidecar** (egress/transmog output only) | the `og.yml` / `schema.yml` sidecar types in the transmog output tree ([ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md)) |

The `<canonical>` file name (currently `dc.yml`) follows the `canonical-metadata` setting value; the content-scope canonical metadata record is the **frozen leaf** of the cascade — resolved at creation and immutable by default (ADR-023 / write-once primitives).

---

## 5. The cascade today

Records are **sparse** (each node states only what differs) and resolve **deepest-stated-value-wins** ([ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §7). The `markdown.yml` floor states the rule directly — an operator overrides a baseline "at whatever tier they own … sparse, deepest-stated-value wins … the floor, not a lock."

> **Implemented today: five layers, not nine.** `satlib.cascade.layers_for` walks ADR-025 §7's five operator tiers and nothing else — its own docstring says so, and nothing in `satlib` reads `defaults/<tier>/metadata/dc.yml`. The shipped defaults floor of [ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md) is **Proposed** (v0.1.1, 2026-07-31), not built: `sat:metadata_schema` has no reader, and the only `defaults/` file any code reads is `defaults/content/markdown.yml`, consumed by `satlib.markdown` for normalization toggles rather than as a metadata layer. The floor rows below are marked accordingly; strike them and the walk is what runs today.

The resolution order, base → most specific — floor rows per [ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md) §2 (proposed), operator rows per ADR-025 §7 (implemented):

```
0a. en/bin/sat/defaults/sat/metadata/dc.yml          SAT's shipped opinion   [proposed]
1.  .<instance>.assets/sat/dc.yml                    operator's instance override

0b. en/bin/sat/defaults/collection/metadata/dc.yml   SAT's shipped opinion   [proposed]
2.  .<collection>.assets/collection/dc.yml           operator's override

0c. en/bin/sat/defaults/archive/metadata/dc.yml      SAT's shipped opinion   [proposed]
3.  .<archive>.assets/archive/dc.yml                 operator's override

0d. en/bin/sat/defaults/content/metadata/dc.yml      SAT's shipped opinion   [proposed]
4.  .<directory>.assets/content/dc.yml               operator's override (per directory)

5.  .<file>.assets/content/dc.yml                    the document's own record
                                                     (or transcribed frontmatter at
                                                     ingress, ADR-023 — the frozen leaf)
```

The stagger is by tier, not by directory depth ([ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §8): a dual-role directory contributes its sat layer and then its collection layer in that fixed order. Preseeds are *not* a read-time layer: the instantiation preseed resolves at creation into `.<instance>.assets/sat/dc.yml` ([ADR-026](../architecture/adrs/adr-026-full-chain-creation-the-instantiation-preseed-and-seeding-v0-2-3.md)), and the cascade reads only the role records thereafter.

At resolution, SAT also fills `<calculated>` fields — e.g. `dc:language_bcp47` from the filesystem language root, and the ISO-639-2 form via a BCP-47 lookup against the cached IANA registry. A `<calculated>` at the owning tier is a hole no shallower layer may cover — resolved or reported, never papered over (ADR-025 §7).

---

## 6. Canonical metadata today

- **`canonical-metadata` setting value:** `dc` (Dublin Core Metadata Element Set 1.1) per [ADR-028](../architecture/adrs/adr-028--dublin-core-namespace-dc--for-mvp-dcterms--deferred.md): `dc:` throughout for the MVP, `dcterms:` refinements used explicitly (with the exception noted at the point of use) where no `dc:` equivalent exists. All current field names carry the `dc:` prefix. The setting is realized as the shipped-floor value `sat:metadata_schema` ([ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md) §5, adopted as committed work by [ADR-034](../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md) §2).
- **Canonical metadata record carrier:** at content scope, the content role's `dc.yml` in the document's assets directory beside it (`.<file>.assets/content/dc.yml`, [ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md), [ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §2); at higher scopes, the role directory's `dc.yml` within the in-tree parallel (tree) assets.
- **Canonical source of truth:** the content role's `dc.yml` in the document's assets directory. Egress strips source front matter and copies the record forward as a metadata **sidecar** — the term's narrowed, pipeline-output sense ([ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md)); transmog regenerates all **derived metadata** (front matter, og, schema) from it. Nothing is passed through from the author's original front matter.
- **Derived metadata:** regenerated on publish and persisted in the output tree as metadata sidecars — `dc.yml`, `og.yml`, and `schema.yml`, ADR-032's three metadata sidecar types.

---

## 7. The content pipeline today

Content moves through four stages; each is governed by a different configuration input or asset.

```
content ingress   → nursery/              cascade cataloging (ADR-023); writes canonical metadata record, provenance, fixity into the document's assets directory; work index
content egress    → egress/               default-content-spec.yml (floor: body transforms); body only + canonical metadata record copied forward as a sidecar
transmog          → transmog/<platform>/  <platform>-frontmatter-spec.yml (definition); derived metadata sidecars + prepared document
publication tool  → final output          MkDocs build / PDF renderer / static site
```

Illustrative on-disk result for one content item:

```yaml
archives/test/
  my-doc.md                 # body payload
  .my-doc.md.assets/        # the document's assets directory, beside it (ADR-018)
    content/                # the content role directory (ADR-025 §2)
      dc.yml                # canonical metadata record (canonical, write-once)
      provenance.yml        # provenance record
      fixity.yml            # fixity record
  egress/
    my-doc.md               # clean body-only document
    .my-doc.dc.yml          # metadata sidecar: canonical record copied forward (ADR-032 sense)
  transmog/mkdocs/
    my-doc.md               # prepared document (front matter + body)
    .my-doc.schema.yml      # metadata sidecar: derived metadata (schema type)
```

The term **sidecar** applies only in the `egress/` and `transmog/` output trees — the three metadata sidecar types of [ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md). In the source tree, everything about the document rides in its assets directory ([ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md) absorbed the earlier root sidecars).

---

## 8. Configuration inputs in detail

### 8.1 Definitions (tool behaviour and what to build)

| Path (under `en/bin/`) | Governs |
|------------------------|---------|
| `sat/definitions/defaults/sat.yml` | instance identity — name, version, language, license; `tools:` toggles |
| `sat/definitions/defaults/connection.yml` | `archive_connection` — location, protocol |
| `sat/definitions/defaults/discovery.yml` | root-discovery marker, `definitions:` map per tool, `tools:` toggles, `nursery:` |
| `archives/config/archives-parent.yml` | `archives.root` — where archives are created |
| `archives/config/archive-definition.yml` | an archive's directory `tree:` |
| `archives/definitions/archives/*.yml` | per-archive spec: name, parent, root, base_url, language, content_profile, tree |
| `transmog/definitions/mkdocs-transmog.yml` | a transmog target: platform + frontmatter spec + source/output |
| `transmog/definitions/frontmatter/{mkdocs,github,html,pdf}-frontmatter-spec.yml` | per-platform derived-metadata output rules |
| `transmog/definitions/frontmatter/default-frontmatter-spec.yml` | reference template for new platform specs |

### 8.2 Floor (shipped baseline values, cascade base)

| Path | Governs |
|------|---------|
| `sat/defaults/{sat,collection,archive,content}/metadata/dc.yml` | per-tier shipped metadata floor — the outermost candidate of each tier's layer ([ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md) §1–2); under `bin/sat/`, never delegated. **Proposed, not implemented:** no code reads these yet (see §5) |
| `sat/defaults/content/markdown.yml` | markdown house-rules baseline (toggles); overridable downstream at `.<name>.assets/<role>/markdown.yml` |
| `content/definitions/defaults/default-content-spec.yml` | egress body-transform baseline (self-documenting toggles) |

### 8.3 Preseeds & caches (operator topology and lookups, under `~/.config/sat/`)

| Path | Governs | Produced by |
|------|---------|-------------|
| `sat-preseed.yml` | version, language, `caches.iana_registry`, `sat_collection`, `collections` topology | `sat init` (from `sat-preseed.yml.example`) |
| `collection/collection-preseed.yml` | `collections.default_parent`, per-collection `archives` | `sat init` / `collection init` |
| `instantiate-preseed.yml` | whole-chain instantiation seed ([ADR-026](../architecture/adrs/adr-026-full-chain-creation-the-instantiation-preseed-and-seeding-v0-2-3.md)); resolved at creation into `.<instance>.assets/sat/dc.yml`, not read at resolution time | read once by `sat init` if present |
| `.meta/sat-meta.yml` | SAT-level canonical-metadata defaults that cascade into the canonical metadata record | `sat init` (from `.meta/sat-meta.yml`) |
| `cache/iana-registry.txt` | IANA registry cache (`staleness_days: 30`) | `sat init` |

---

## 9. Per-tool summary

- **`sat` (instance).** Bash dispatcher; computes the SAT root and routes to Python tools. Reads the `sat.yml`, `connection.yml`, and `discovery.yml` definitions. `sat init` instantiates the whole chain ([ADR-026](../architecture/adrs/adr-026-full-chain-creation-the-instantiation-preseed-and-seeding-v0-2-3.md)) and writes the sat/collection role records, archives, and children records; `sat migrate` moves a 0.5.0/0.6.0 tree into per-role assets directories ([ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §9); `sat licence check` is a read-only SPDX auditor (ADR-033).
- **`archives`.** Standalone (no `satlib`). Creates directory structures from archive definitions — directories only, deterministic. Reads `archives-parent.yml` and per-archive definition files.
- **`collection`.** Uses `satlib`. `collection init` creates a single-role collection: its collection role records, declared archives, children record, and a sparse canonical metadata record inheriting through the cascade. Also `collection-fixity`, `collection-mv`, `collection-reconcile` (discovery and reconciliation, [ADR-024](../architecture/adrs/adr-024-discovery-and-reconciliation-v0-2-2.md)), `collection-work`.
- **`content`.** Cross-platform Python dispatcher (`satlib`). `content init` mints a content-directory's identity, provenance, and sparse canonical metadata record; `content ingress` catalogs a document against the resolved cascade (ADR-023), mints identity, and writes the canonical metadata record, provenance, and fixity into the document's assets directory (`.<file>.assets/content/`, [ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md), [ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §2). Egress body transforms are governed by `default-content-spec.yml`; the markdown floor is read by `satlib.markdown`.
- **`transmog`.** Standalone (no `satlib`). Reads a transmog definition + a front-matter spec, then generates **derived metadata** (front matter, og, schema) from the content-item canonical metadata record per platform, persisted as metadata sidecars in the output tree ([ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md)). Shipped targets: mkdocs, github, html, pdf.

---

## 10. Canonical-metadata defaults (`sat-meta.yml`)

`sat-meta.yml` holds the SAT-scope canonical-metadata defaults that cascade down the collection, archive, and content tiers, each of which may override individual fields in its own `*-meta.yml`. These are creation-time seeds, not a read-time layer: values resolve at archive/content creation into the role records and the content-item canonical metadata record ([ADR-026](../architecture/adrs/adr-026-full-chain-creation-the-instantiation-preseed-and-seeding-v0-2-3.md)), then immutable by default; read-time resolution afterwards walks only the role-record layers of §5. Shipped defaults include agent fields (`dc:creator`, `dc:contributor`, `dc:publisher`), rights (`dc:rights` as a Creative Commons URI), language (`dc:language` and the SAT-local `dc:language_bcp47`, both `<calculated>`), format (`dc:format: text/markdown`), and type (`dc:type: Collection` at collection/archive, `Text` at content). Prefixes follow DCMES 1.1 — i.e. the current `canonical-metadata` value ([ADR-028](../architecture/adrs/adr-028--dublin-core-namespace-dc--for-mvp-dcterms--deferred.md)).

---

## 11. Glossary

Full definitions live in *SAT Configuration — Definitions and Vocabulary*. Terms used here:

- **Asset** — configuration/metadata kept parallel to content; a *payload* on a *carrier* at a *scope*.
- **Payload / carrier / scope** — what is carried / how it is carried (assets directory, parallel tree) / whose it is (the role).
- **Assets directory** — the per-entity carrier `.<name>.assets/` ([ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md)): the literal transform of the entity's on-disk name; inside a directory, beside a file. Media belonging to a file lives inside its assets directory.
- **Sidecar** — narrowed sense: a metadata file emitted into pipeline output by egress/transmog — the three metadata sidecar types `dc.yml`, `og.yml`, `schema.yml` ([ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md)). Not an in-tree carrier: ADR-018 absorbed the former root sidecars into assets directories.
- **Parallel (tree) assets** — the tree carrier, realized as per-entity assets directories in the content tree itself ([ADR-018](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md)). The former *twinned* / *detached* axis is retired: there is one in-tree carrier, and any out-of-tree rendering is a derived, read-only projection ([ADR-034](../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md)).
- **Canonical metadata record** — a node's descriptive metadata in the vocabulary named by the `canonical-metadata` setting (currently `dc`, [ADR-028](../architecture/adrs/adr-028--dublin-core-namespace-dc--for-mvp-dcterms--deferred.md)).
- **Derived metadata** — og/schema/front matter regenerated from the canonical metadata record.
- **Cascade / sparse / floor** — deepest-stated-value-wins resolution ([ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) §7) / stating only differences / the shipped defaults layer below every operator tier ([ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md)).

---

## 12. References

- [ADR-018: Universal Assets Directory Convention](../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md)
- [ADR-024: Discovery and Reconciliation](../architecture/adrs/adr-024-discovery-and-reconciliation-v0-2-2.md)
- [ADR-025: Role-Named Assets Directories, Sparse Inheritance, and the Resolution Order](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md)
- [ADR-026: Full-Chain Creation, the Instantiation Preseed, and Seeding](../architecture/adrs/adr-026-full-chain-creation-the-instantiation-preseed-and-seeding-v0-2-3.md)
- [ADR-028: Dublin Core Namespace — dc: for MVP, dcterms: Deferred](../architecture/adrs/adr-028--dublin-core-namespace-dc--for-mvp-dcterms--deferred.md)
- [ADR-032: The Shipped Defaults Floor Below the Operator Cascade](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md)
- [ADR-034: Operator-Side Concern Parents and the Derived Mapping Projection](../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md)
