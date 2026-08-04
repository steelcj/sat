# SAT Configuration — Current Mapping

*A descriptive map of every configuration file Source Archive Tools (SAT) reads or produces today, where each file lives, and how values resolve. This document describes the current state only — it makes no recommendations.*

> **Superseded — retained as a working artifact.** This document predates access to the ADR corpus and describes SAT in vocabulary the corpus has since retired. Assets directories are per-entity, `.<name>.assets`, inside the directory they describe and beside the file they describe, with media *inside* a file's assets directory ([ADR-018](../../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md)); *co-located* and *nested* are retired as topology terms and the flat record set governs role directories ([ADR-025](../../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md)); resolution is the nine-layer walk above the shipped defaults floor ([ADR-032](../../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md)); *sidecar* is narrowed to the egress/transmog output sense ([ADR-034](../../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md)). The current-state document maintained against the corpus is [`../sat-configuration-current-mapping.md`](../sat-configuration-current-mapping.md). The body below is unchanged; the ADRs are authoritative on every point of conflict.

> **Scope note:** Built from the delivered `en/bin/` tree (the `sat`, `archives`, `collection`, `content`, and `transmog` tools) and the one-page paths mapping. The internals of the shared `satlib` package were not in the bundle; where behaviour depends on it, that is noted as *(via `satlib`)*.

---

## 1. What SAT is, structurally

SAT is a filesystem-first framework for managing **source archives**. There is no database and no runtime state — configuration is entirely YAML files on disk, diffable and filesystem-visible.

Four facts orient the whole map:

- **Tiers / roles.** SAT models four roles, broad to narrow: **sat** (the instance), **collection**, **archive** (a language archive), and **content** (a content-organizing directory). The instance root is *dual-role* — simultaneously the sat role and a collection role (ADR-026). Roles are the axis configuration cascades along.
- **Tools.** Five tool groups live under `en/bin/`: `sat`, `archives`, `collection`, `content`, `transmog`. Each is individually enabled or disabled; `transmog` is currently off.
- **`satlib`.** The newer tools (`sat`, `collection`, `content`) delegate their real work to a shared `satlib` package (discovery, roles, cascade, cataloging, language/BCP-47, SPDX, fixity, children indexes). The older tools (`archives`, `transmog`) are standalone — they parse their own YAML and do not use `satlib`.
- **ADR-driven.** Behaviour is governed by Architecture Decision Records (ADR-003, -005, -021/022, -023, -025, -026, -029, -030, -032, -033…); the YAML files are downstream of those decisions.

---

## 2. The five families of configuration

Every config file in SAT belongs to one of five families. The families differ in who owns them, how long they live, and whether they participate in the cascade.

| Family | What it is | Owner / lifetime | Representative files |
|--------|-----------|------------------|----------------------|
| **Definitions** | Shipped files describing tool behaviour and what to build | SAT project; versioned in the repo | `sat.yml`, `discovery.yml`, `connection.yml`, `archives/definitions/archives/*.yml`, `transmog/definitions/**` |
| **Defaults / "floor"** | Shipped baseline opinions that may be overridden downstream | SAT project; base layer of a cascade | `defaults/content/markdown.yml`, `default-content-spec.yml` |
| **Records** | Sparse per-node state written into the archive tree, resolved by cascade | Written by SAT tools; live in the instance tree | role records: `identity`, `provenance`, `dc.yml`, `fixity`, `children.yml`, `collection.yml`, language records |
| **Sidecars** | Per-document metadata beside a single document | Written next to content; largely immutable | `.<stem>.dc.yml` (canonical), `.og.yml`, `.schema.yml` (derived) |
| **Preseeds & caches** | Operator-level topology and lookup caches | Operator; under `~/.config/sat/` | `sat-preseed.yml`, `collection-preseed.yml`, `.meta/sat-meta.yml`, `instantiate-preseed.yml`, `cache/iana-registry.txt` |

---

## 3. Where configuration lives — the five roots

Configuration is spread across five distinct roots.

| # | Root | Holds | Notes |
|---|------|-------|-------|
| R1 | `<repo>/en/bin/<tool>/definitions/` and `…/defaults/` | Definitions + floor | Shipped, versioned, read at runtime |
| R2 | `~/.config/sat/` | Preseeds, `.meta`, caches | Operator-owned; produced by `sat init` from the `*.example` templates |
| R3 | `~/.local/share/sat-tool/<version>/` | The seeded sat collection / data | Referenced as `sat_collection.path` in the preseed |
| R4 | `default_parent` (e.g. `~/projects/sat/…`) | The real collections and archives | A per-collection `parent:` overrides `default_parent:` |
| R5 | Inside the instance tree | Per-role records and document sidecars | Where the cascade operates |

---

## 4. The cascade — how a value resolves

Records are **sparse**: a node states only what differs from what it inherits. Resolution is **deepest-stated-value wins** (ADR-025 §7), walking from the shipped base down to the specific node. The `markdown.yml` floor states the rule directly — an operator who disagrees with a baseline "overrides it at whatever tier they own … sparse, deepest-stated-value wins … this file is only the floor, not a lock."

Resolution order, base → most specific:

```
shipped floor / definitions        (R1)   markdown.yml, default-content-spec.yml, sat.yml …
  ⤷ operator preseed & .meta        (R2)   sat-meta.yml DC defaults, topology
      ⤷ sat (instance) role records (R5)
          ⤷ collection role records
              ⤷ archive role records
                  ⤷ content role records
                      ⤷ document .dc.yml sidecar   (canonical, write-once)
= effective configuration for a node
```

Two properties define the model as it stands: values live in exactly one place and are inherited (sparse records), and resolved metadata is **frozen into a `.dc.yml` sidecar at creation time and immutable by default** thereafter (ADR-023 / write-once primitives). At that resolution moment SAT also fills `<calculated>` fields — for example `dc:language_bcp47` is derived from the filesystem language root, and `dc:language` from it via a BCP-47 → ISO 639-2 lookup against the cached IANA registry.

For content specifically, cataloging against the resolved cascade is performed by `satlib.cataloging` (ADR-023) during `content ingress`.

---

## 5. The content pipeline and where config enters

Content moves through four stages; each stage is governed by a different config family.

```
content ingress   → nursery/              cascade cataloging (ADR-023); writes .dc.yml, provenance, fixity, work index
content egress    → egress/               default-content-spec.yml (body transforms); body only + copied .dc.yml
transmog          → transmog/<platform>/  <platform>-frontmatter-spec.yml; front matter + .og.yml/.schema.yml sidecars
publication tool  → final output          MkDocs build / PDF renderer / static site generator
```

The `.dc.yml` sidecar is the pipeline's pivot: it is the **single canonical metadata source of truth**. Egress strips all source front matter and copies the sidecar forward unchanged; transmog then regenerates front matter, Open Graph, and Schema.org entirely *from the sidecar* per the platform spec. Nothing is carried through from the author's original front matter.

Typical on-disk result for one document:

```
archives/test/
├── my-doc.md                     ← source (nursery)
├── .my-doc.dc.yml                ← canonical DC sidecar (input to egress)
├── egress/
│   ├── my-doc.md                 ← clean body-only document
│   └── .my-doc.dc.yml            ← DC sidecar copied forward
└── transmog/
    └── mkdocs/
        ├── my-doc.md             ← prepared document (mkdocs front matter + body)
        └── .my-doc.schema.yml    ← Schema.org sidecar (when enabled in the spec)
```

---

## 6. File-by-file inventory

### 6.1 Shipped configuration (under `en/bin/`)

| Path | Family | Role in the system |
|------|--------|--------------------|
| `sat/definitions/defaults/sat.yml` | Definition | Instance identity — `name`, `version`, `language`, `license`; `tools:` toggles (`sat`, `archives`, `content`, `transmog`) |
| `sat/definitions/defaults/connection.yml` | Definition | `archive_connection` — `location` (local / localhost / remote) and `protocol` (filesystem / ssh / wireguard / mount) |
| `sat/definitions/defaults/discovery.yml` | Definition | Root-discovery `marker:`, a `definitions:` map per tool, `tools:` toggles, and `nursery:` |
| `sat/defaults/content/markdown.yml` | Floor | Markdown house-rules baseline as toggles (e.g. `no_horizontal_rules`, `fenced_blocks_require_language`, `no_heading_level_skips`, `no_hard_line_wraps`, `no_embedded_image_data`, `inline_svg_allowed`); overridable at `.assets/<role>/markdown.yml` |
| `sat/examples/sat-preseed.yml.example` | Preseed template | Seeds `~/.config/sat/sat-preseed.yml`: `sat` (version, language, `caches.iana_registry`), `sat_collection`, `collections` topology |
| `sat/examples/collection-preseed.yml.example` | Preseed template | Seeds collection topology (`collections.default_parent`, per-collection `archives`) |
| `sat/examples/.meta/sat-meta.yml` | Preseed template | SAT-level Dublin Core defaults that cascade into `.dc.yml` |
| `archives/config/archive-definition.yml` | Definition | An archive's directory `tree:` (nested `areas:` → sub-areas) |
| `archives/config/archives-parent.yml` | Definition | `archives.root` — where archives are created relative to the project root |
| `archives/definitions/archives/*.yml` | Definition | Per-archive spec (see §7.2) |
| `content/definitions/defaults/default-content-spec.yml` | Floor | Egress body-transform spec — self-documenting toggles (see §7.4) |
| `transmog/definitions/mkdocs-transmog.yml` | Definition | A transmog target: `platform`, `frontmatter_spec`, `source`, `output`, and DC metadata |
| `transmog/definitions/frontmatter/default-frontmatter-spec.yml` | Floor / template | Reference template for new platform specs (not used directly by any tool) |
| `transmog/definitions/frontmatter/mkdocs-frontmatter-spec.yml` | Definition | MkDocs target: front matter `title`/`description`/`tags`, Schema.org sidecar on |
| `transmog/definitions/frontmatter/github-frontmatter-spec.yml` | Definition | GitHub target: all sections off (no front matter) |
| `transmog/definitions/frontmatter/html-frontmatter-spec.yml` | Definition | HTML target: OG injected into `<head>`, Schema.org sidecar |
| `transmog/definitions/frontmatter/pdf-frontmatter-spec.yml` | Definition | PDF target: DC fields passed to the renderer for the title page / XMP |

### 6.2 Produced at runtime (not in the repo)

| Path | Family | Produced by |
|------|--------|-------------|
| `~/.config/sat/sat-preseed.yml` | Preseed | `sat init` (from the example template) |
| `~/.config/sat/collection/collection-preseed.yml` | Preseed | `sat init` / `collection init` |
| `~/.config/sat/instantiate-preseed.yml` | Preseed | Read once by `sat init` if present |
| `~/.config/sat/.meta/sat-meta.yml` | Preseed | `sat init` (from `.meta/sat-meta.yml`) |
| `~/.config/sat/cache/iana-registry.txt` | Cache | `sat init` (IANA registry; `staleness_days: 30`) |
| `.assets/<role>/{identity,provenance,dc.yml,fixity,children.yml,collection.yml}` | Records | `sat`/`collection`/`content` init and ingress (via `satlib`) |
| `.<stem>.dc.yml` | Sidecar | `content-metadata-ingress` / `content ingress` (canonical) |
| `.og.yml`, `.schema.yml` | Sidecar | `transmog` (derived from the DC sidecar) |

---

## 7. Per-tool configuration detail

### 7.1 `sat` (instance tier)

The `sat` bash dispatcher computes the SAT root as three directories above itself and routes to Python tools. Its configuration surface:

- **`sat.yml`** declares instance identity and the `tools:` map. In the shipped default: `name: "Source Archive Tools"`, `version: "0.1.0"`, `language: "en"`, `license: "GPL-3.0-or-later"`; tools `sat`, `archives`, `content` on and `transmog` off. (The authoritative version lives in a `VERSION` file at the repo root, which `sat migrate` reads.)
- **`connection.yml`** declares how an archive is reached — `location` and `protocol`.
- **`discovery.yml`** carries a `marker:` path used to locate the SAT root, a `definitions:` map naming each tool's definitions directory, a `tools:` map, and a `nursery:` name.
- **`sat init`** instantiates a whole instance in one command (ADR-026): the sat role, the dual-role collection role (with `collection.yml`), the language archives, children indexes at every parent, and seeded documentation / example collection / staged samples. It reads `~/.config/sat/instantiate-preseed.yml` once if present; below the instance there is no preseed — "the cascade is the preseed."
- **`sat migrate`** is a one-time, dry-run-by-default move of a 0.5.0/0.6.0 tree into role directories (ADR-025): flat `identity`/`provenance`/`dc`/`language` records move into their tier's role directory, the dual-role root's collection role is minted, the old work index is rebuilt, children indexes are built, and fixity is recorded.
- **`sat licence check`** is a read-only SPDX auditor (ADR-033): it reads `SPDX-License-Identifier:` markers and the `sat.license` field, validates them against the SPDX list (cached like the IANA registry), and reports hard/soft findings without ever writing.

### 7.2 `archives` (archive creation)

A standalone tool (no `satlib`) that creates directory structures from explicit YAML definitions — "directories only," deterministic, no implicit behaviour.

- **`archives/config/archives-parent.yml`** — `archives.root` (e.g. `"archives"`), the location archives are created under.
- **`archive-definition.yml`** — an archive `tree:` expressed as nested mappings; leaves may be `null`, the string `file`, an empty map `{}`, or further nested maps.
- **`archives/definitions/archives/*.yml`** — per-archive definitions with fields: `archive_name`, `parent_directory`, `archive_root`, optional `base_url`, a `language:` block (`code`, `relationship`), optional `content_profile` (e.g. `commonmark`), and a `tree:` skeleton of documents to create. Shipped examples: `sat-en-docs.yml`, `sat-fr-docs.yml`, `chrissteel.com-en.yml`, `universalcake.com-en.yml`, `operations-guides-en.yml`.

`archive-init.py` reads a definition plus the parent definition and creates the tree (`--dry-run` previews).

### 7.3 `collection` (collection tier)

The `collection` bash dispatcher routes to Python tools that use `satlib`.

- **`collection init <path>`** creates an additional single-role collection inside an existing instance (ADR-026): its collection role records, declared archives, children index, and a sparse `dc.yml` inheriting through the cascade; it refreshes the instance role's children index. There is no `~/.config` preseed below the instance.
- **`collection-preseed.yml.example`** defines collection topology: `collections.default_parent` and, per collection, an `archives:` map. A collection may set its own `parent:` to override `default_parent`.
- Additional collection tools present: `collection-fixity.py`, `collection-mv.py`, `collection-reconcile.py`, `collection-work.py`.

### 7.4 `content` (content tier)

`content.py` is a cross-platform Python dispatcher (runs on Linux/macOS/Windows, resolves its own interpreter) routing `init` and `ingress`.

- **`content init <dir>`** mints a content-organizing directory's records (ADR-025 §9): content role identity (`dc:identifier` and `sat:work`), provenance, a sparse `dc.yml`, and a refresh of the enclosing archive's children index. A bare `mkdir` remains legal; this is the deliberate path.
- **`content ingress <doc.md>`** brings an arriving document under management (content-ingress spec v0.3.1): it reads the document's front matter, catalogs metadata against the resolved cascade (ADR-023, via `satlib.cataloging`), mints identity (ADR-021/022), writes the DC sidecar, provenance, and fixity, records the ingress event, and updates the work index. `dc:date` falls back transcribed → `--date` → `st_birthtime` → UTC-now.
- **`default-content-spec.yml`** controls egress body normalization through self-documenting toggles, applied in a fixed order: `strip_front_matter`, `strip_hr`, `strip_emoji`, `clean_heading_markup`, `heading_hierarchy` (strict/warn/off), `heading_style` (atx/setext), `list_marker`, `code_fence_style`, `code_fence_min_length`, `link_style`, `normalize_tables`, `line_endings`, `trim_trailing_whitespace`, `max_line_length` (0 = no wrap). Code-block contents are always protected.
- **`markdown.yml`** (under `sat/defaults/content/`) is the shipped "well-formed SAT markdown" floor, read at read time by `satlib.markdown`'s `check_house_rules()`.

### 7.5 `transmog` (publication preparation)

A standalone tool (no `satlib`). It reads a **transmog definition** naming a platform and a **front-matter spec**, then for each document reads the `.dc.yml` sidecar, generates front matter per the spec, generates `.og.yml` / `.schema.yml` sidecars when enabled, and writes the prepared document. "Pipeline behaviour is driven entirely by the front matter spec — no separate pipeline configuration is needed."

The shipped platform specs:

| Platform | Front matter | OG sidecar | Schema sidecar |
|----------|-------------|-----------|----------------|
| mkdocs | `title`, `description`, `tags` | no | yes |
| github | none | no | no |
| html | none (OG injected into `<head>`) | yes (`head`) | yes |
| pdf | none (fields passed to renderer) | no | no |

The `default-frontmatter-spec.yml` is the documented template for adding a new platform (copy it, set `platform`, enable sections). All field values are read from the DC sidecar via the documented DC → front matter / OG / Schema.org mappings; the sidecar is the canonical record.

---

## 8. Dublin Core metadata defaults (`sat-meta.yml`)

`sat-meta.yml` holds the SAT-level Dublin Core defaults that cascade downward through the collection, archive, and content tiers, each of which may override individual fields in its own `*-meta.yml`. Values are resolved at archive or content creation and written to the `.dc.yml` sidecar, then immutable by default. Shipped defaults include agent fields (`dc:creator`, `dc:contributor`, `dc:publisher`), rights (`dc:rights` as a Creative Commons URI), language (`dc:language` and the SAT-local extension `dc:language_bcp47`, both `<calculated>` by `sat init`), format (`dc:format: text/markdown`), and type (`dc:type: Collection` at the collection/archive tiers, `Text` at the content tier). The `dc:` prefix follows DCMES 1.1.

---

## 9. Glossary

- **Role / tier** — a level configuration cascades along: **sat** (instance) → **collection** → **archive** (language archive) → **content**. The instance root is *dual-role* (sat + collection).
- **Cascade** — resolution by walking base → node, deepest-stated-value wins (ADR-025 §7).
- **Sparse record** — a per-node file stating only what differs from its inherited value.
- **Floor** — a shipped baseline (e.g. `markdown.yml`) that sets defaults but can be overridden downstream — "the floor, not a lock."
- **Definition** — a shipped file describing tool behaviour or what to build (archive trees, transmog targets, front-matter specs).
- **Sidecar** — a per-document metadata file beside the content: `.dc.yml` (canonical), `.og.yml` / `.schema.yml` (derived).
- **Preseed** — an operator-level file under `~/.config/sat/` that seeds topology or metadata; "below the instance, the cascade is the preseed."
- **Nursery** — the staging area for arriving content during ingress.
- **Transmog** — pipeline stage 3: turning a clean egress document plus its `.dc.yml` into platform-ready output.
- **DC** — Dublin Core Metadata Element Set 1.1; the canonical descriptive vocabulary, carried as `dc:`-prefixed keys.
- **`satlib`** — the shared Python library the newer tiers delegate to for discovery, roles, cascade, cataloging, language, SPDX, and fixity.
