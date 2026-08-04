---
dc:title: "SAT Configuration — Definitions and Vocabulary"
dc:description: "Controlled vocabulary and definitions for SAT configuration: assets, payloads, carriers, scopes, and canonical metadata."
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
  - vocabulary
  - assets
  - metadata
  - canonical metadata
dc:identifier: "sat-configuration-definitions-and-vocabulary"
---

# SAT Configuration — Definitions and Vocabulary

A controlled vocabulary for how SAT stores configuration and metadata. Terms are grouped by theme; each entry is a single definition. Where a term supersedes an earlier draft name, the change is noted inline; where a term has a governing ADR, the ADR is cited. This revision reconciles the vocabulary with the ADR corpus through [ADR-034].

---

## 1. Foundations

- **Node** — a directory or item in the SAT tree that can bear a role and carry payloads.
- **Role** — the function a node plays in SAT: *sat*, *collection*, *archive*, or *content*. Declared on disk by role directories ([ADR-025] §1), never inferred from position. Determines which payloads it bears.
- **Tier** — a level in the role hierarchy (sat → collection → archive → content); used interchangeably with *role* when emphasizing depth or precedence. The cascade staggers by tier, not by directory depth ([ADR-025] §8).
- **Role directory** — a role-named directory inside a node's assets directory (`.<name>.assets/<role>/`). It is simultaneously the declaration of the role, the container for that tier's records, and the permission boundary for delegation ([ADR-025] §1, §3).
- **Dual-role directory** — a directory carrying two role directories in one assets directory — e.g. an instance that is also a collection: `.sat.assets/sat/` and `.sat.assets/collection/`. Each role carries its own identity, so extraction is a pure move ([ADR-025] §1–2). *(Supersedes the bare "dual-role".)*
- **Single-role directory** — a directory wearing one role, carrying only its own role directory — e.g. a collection created inside an existing instance. Both topologies are first-class and resolve identically ([ADR-025] §1, §8).
- **Cascade** — resolution of a payload's effective value by walking the tiers from the broadest scope down to the node, with SAT's shipped floor read immediately before each operator tier ([ADR-025] §7, as amended by [ADR-032] §2).
- **Resolution order** — the nine-layer walk: for each of the four tiers, the shipped-floor file (`en/bin/sat/defaults/<tier>/metadata/dc.yml`) then the operator's role-directory `dc.yml`, ending at the document's own record or, at ingress, transcribed frontmatter ([ADR-025] §7; [ADR-032] §2). Read at read time, never cached ([ADR-032] §3). *Implementation status: `satlib.cascade` walks the five operator tiers today; the four floor layers are [ADR-032] (Proposed) and have no reader yet.*
- **Deepest-stated-value-wins** — the cascade rule: among all layers stating a value, the one closest to the node prevails. Absence inherits; a stated value overrides deliberately.
- **Sparse inheritance** — the rule that every setting is stated exactly once, at the tier that decided it, and nowhere else. An empty lower-tier file means inherit; a stated value means this tier decided differently, on purpose ([ADR-025] §4).
- **Sparse record** — a record stating only the values that differ from those inherited through the cascade; the file-level expression of sparse inheritance.
- **Shipped defaults floor** — SAT's own shipped opinions, at `en/bin/sat/defaults/<tier>/`, one directory per cascade tier, under `bin/sat/` and therefore never delegated. Each tier's floor file is read immediately before that tier's operator layer; a floor value is the value an operator inherits if nobody, at any tier, has stated an opinion. Read-time, no caching, no exception; `sat defaults --diff` reports floor changes on demand ([ADR-032]). *(Supersedes the bare "floor".)* Note: permission (copy-once delegation) and the defaults floor (read-time, SAT-owned) are two different mechanisms, deliberately kept apart ([ADR-032] §4).

---

## 2. The asset model

- **Asset** — configuration or metadata kept *parallel to* the content it describes, rather than embedded in it. Characterized by a payload, a carrier, and a scope.
- **Payload** — *what* an asset carries: a record, metadata, or content-associated data. Independent of the carrier.
- **Carrier** — *how* an asset is stored and attached to a node: the per-entity **assets directory** ([ADR-018]) and, within it, the **role directory** ([ADR-025]). *(Supersedes the earlier sidecar / parallel-tree carrier pair; see § 3 and the retired terms note.)*
- **Scope** — *whose* the payload is: the role it belongs to. Fixes its place in the cascade.

> An asset is named by all three attributes when precision is required: *[scope] [kind] payload carried as [carrier]* — e.g. "an archive fixity record carried in the archive's role directory."

---

## 3. Carriers

- **Assets directory** — the primary carrier: every file and directory `<name>` has exactly one hidden assets directory named `.<name>.assets`, produced by the literal transform — prepend `.`, append `.assets`; no slugging or substitution; reversible ([ADR-018] §1–2). Everything regarding the entity — records, media, derived renditions — lives there. It travels with the entity: any copy, move, clone, or tar carries it.
- **Placement rule** — a directory's assets directory lives *inside* the directory it describes; a file's assets directory lives *beside* the file, since a file can contain nothing ([ADR-018] §3). Inside placement is what preserves self-containment at every tier, including the instance root.
- **Role directory** — the role-named subdivision of an assets directory that carries a tier's records (see § 1; [ADR-025] §1–2).
- **Concern parent (reserved word)** — a reserved directory name inside a role directory grouping one concern's files, giving tooling one skip-rule word instead of a growing list. Concern parents are *earned* by a real second file, never created preemptively: `resources/` exists today ([ADR-025] §5); an operator-side `metadata/` joins it when a second metadata file actually lands, relocating `dc.yml` to `metadata/dc.yml` in the same migration ([ADR-034] §1). The shipped floor already nests its `metadata/` concern folder because `og.yml` and `schema.yml` are already-real siblings in the egress pipeline ([ADR-032] §1).
- **Resources** — the reserved `resources/` parent inside a providing role directory, holding operator resources — logos, licences, images, style items — organized by concern (`resources/imgs/`, `resources/licences/`). The relative path under `resources/` is the resource's identity across tiers; resolution walks the tiers exactly as it does for fields — deepest-permitted-stated wins, absence inherits, sparse throughout ([ADR-025] §5).
- **Sidecar** — *narrowed to the egress sense only*: a metadata file produced as pipeline output by egress/transmog — one of the three metadata sidecar types generated from one cataloging pass: `dc.yml`, `og.yml`, `schema.yml` ([ADR-032] §1). The former in-tree sense — hidden dot-files beside an archive root (`.dc.yml`, `.provenance.yml`, `.language.yml`) — is absorbed by the assets directory: those records now live as `dc.yml`, `provenance.yml`, `language.yml` inside `.<archive>.assets/` ([ADR-018], Consequences). Do not use *sidecar* for records stored in the tree.
- **Exclusion rule** — anything matching `.*.assets/` is metadata space: excluded from content enumeration, from ingress, and from the language directory walk ([ADR-018] §6).
- **Orphan** — a `.*.assets/` directory whose pairing with an entity is broken (e.g. after a manual rename). Reported, never silently repaired; classes are `no-entity`, `misplaced`, and `collision` ([ADR-018] §5). Renames are tool-mediated so the entity and its assets directory move as one.

### 3.1 Retired carrier terms (historical — do not reuse)

*Co-located* and *nested*, as topology terms, are retired by [ADR-025] (Consequences). This document's earlier carrier pair is likewise superseded by the assets-directory placement rule: *sidecar (the file carrier)* versus *parallel (tree) assets*, along with *twinned assets*, *detached asset tree*, and the *in-tree / out-of-tree* axis. Where an older draft uses any of these, read them as the ADR-018 assets directory with its inside/beside placement.

---

## 4. Payload scope

- **Payload scope** — the role a payload attaches to.
- **SAT payload** — a payload of the SAT instance (sat role); the cascade-root scope of the operator cascade. (The shipped defaults floor sits below it; [ADR-032].)
- **Collection payload** — a payload of a collection (collection role).
- **Archive payload** — a payload of a language archive (archive role).
- **Content-directory payload** — a payload of a content-organizing directory (content role; a container of content, not a document). Content organizing directories are content-tier entities with identity, sparse metadata, and `sat:work` ([ADR-025] §1–2).
- **Content payload** — a payload of an individual content item (a single document and its associated data). The document's assets directory sits beside the file and holds everything but the body; subdivided below.

### 4.1 Content-scope subdivisions

- **Body payload** — the source document itself (e.g. Markdown); the content being described, not an asset.
- **Content-media payload** — media associated with a document (e.g. images), stored *inside* the file's assets directory — `.my-guide.md.assets/figure-1.svg` — never as a dot-file sibling of the document ([ADR-018] §3–4).
- **Content-metadata payload** — metadata about a document, stored in the file's assets directory: records in its `content/` role directory ([ADR-025] §2), derived renditions alongside ([ADR-018] §4).

---

## 5. Payload kind

- **Payload kind** — the type of data a payload holds, independent of scope and carrier.

### 5.1 Record kinds (metadata about a node)

- **Identity record** — a node's stable identifier and work marker: `identity.yml`, written once at creation, never changed, refuse-if-present ([ADR-021]).
- **Provenance record** — a node's origin, custody, and recorded events: `provenance.yml`, under the same write-once contract ([ADR-021]).
- **Canonical metadata record** — a node's descriptive metadata, expressed in the canonical-metadata vocabulary: the role directory's `dc.yml` ([ADR-025] §2). The filename is literal and stable, never interpolated from the setting ([ADR-034] §2). *(Supersedes the earlier "descriptive record (dc)"; `dc` reflects the current setting value, not part of the name.)*
- **Fixity record** — a node's checksums/digests and verification data: `fixity.yml` ([ADR-027]).
- **Children record** — a node's derived index of its child nodes: `children.yml` ([ADR-024]); a member of the derived (disposable) class.
- **Collection record** — a collection-role declaration or policy: `collection.yml` ([ADR-025] §2).
- **Language record** — a language archive's language / BCP-47 data: `language.yml`.
- **Policy record** — a providing role's `policies.yml`: the operator's hand-edited, sparse record declaring, per resource, which descendant tiers may state their own version ([ADR-025] §6).
- **Enforced / overridable** — the two controlled enforcement values in a policy record, nothing else. *Enforced* at a tier means that tier may not state its own version of the resource; *overridable* means it may. Absence — no policy record, no entry, no tier — means overridable; descendants may tighten, never loosen; enforcement is resolution-honored, never filesystem-prevented ([ADR-025] §6).

### 5.2 Derived-metadata kinds (generated from the canonical metadata record)

- **Open Graph payload (og)** — derived social/link metadata; emitted at egress as an `og.yml` sidecar ([ADR-032] §1).
- **Schema.org payload (schema)** — derived structured metadata; emitted at egress as a `schema.yml` sidecar ([ADR-032] §1).

### 5.3 Content-substance kinds (the material itself)

- **Body payload** — the source document.
- **Media payload** — content-associated media (e.g. images), stored inside the owning file's assets directory ([ADR-018] §3–4).

### 5.4 The derived (disposable) class

- **Derived (disposable) class** — records generated from canonical sources rather than authored: the work index and children indexes ([ADR-022]; [ADR-024]), and the `sat config map` projection ([ADR-034] §3). Never authoritative, never cached; delete and rebuild at any time. If a derived record disagrees with the records it derives from, the derived record is wrong by definition.

---

## 6. Canonical metadata

- **Canonical metadata** — the one metadata vocabulary SAT treats as authoritative for descriptive metadata; the source of truth from which all derived metadata is generated. A role, not a fixed standard.
- **`canonical-metadata` setting** — the SAT setting whose value names the vocabulary currently serving as canonical metadata. Realized as the shipped-floor value `sat:metadata_schema` ([ADR-032] §5, adopted as committed work by [ADR-034] §2), resolved through the nine-layer walk like any other value. The current value is governed by [ADR-028]: `dc:` (Dublin Core) for the MVP; `dcterms:` deferred, with explicit, per-field exceptions (e.g. `dcterms:created`) noted at the point of use.
- **Canonical-metadata vocabulary** — the vocabulary named by the setting; supplies the canonical record's field namespace/prefix (currently `dc:`). Changes with the setting — but never with the filenames: `dc.yml` remains `dc.yml`; a future vocabulary lands as its own file (`mods.yml`) beside it under the earned `metadata/` concern parent, and `sat:metadata_schema` states which one is canonical. The swap is additive and reversible — both records can coexist during a transition — and no filename is ever computed from the setting ([ADR-034] §1–2).
- **Canonical metadata record** — a node's descriptive-metadata record, expressed in the canonical-metadata vocabulary.
- **Derived metadata** — metadata generated *from* the canonical metadata record (e.g. Open Graph, Schema.org, publication front matter); never authored directly, always regenerable.

---

## 7. Metadata storage

- **Metadata** — the umbrella for a node's metadata payloads: the canonical metadata record, other records (identity, provenance, fixity, children…), and derived metadata.
- **Metadata location** — a node's metadata lives in its assets directory, in the role directory of the tier it belongs to ([ADR-018]; [ADR-025] §2). Records sit flat in the role directory today; a `metadata/` concern parent is earned when a second descriptive-metadata file actually lands, relocating `dc.yml` to `metadata/dc.yml` in the same migration ([ADR-034] §1). It is *where* metadata lives; the `canonical-metadata` setting (`sat:metadata_schema`) governs *what* the canonical record says. *(Supersedes "metadata directory" and its carrier choice; the carrier is the assets directory, always.)*
- **Shipped-floor metadata** — SAT's shipped descriptive defaults, one `dc.yml` per tier at `en/bin/sat/defaults/<tier>/metadata/` ([ADR-032] §1). Nested under `metadata/` from the start because `og.yml` / `schema.yml` floors are an already-precedented possibility.

---

## 8. Invariants

- **Vocabulary is independent of storage** — changing `sat:metadata_schema` changes which record is canonical and which prefix the canonical record uses, not any filename or placement ([ADR-034] §2).
- **Storage is independent of vocabulary** — moving a record (e.g. the earned `metadata/` relocation of [ADR-034] §1) changes where it is stored, not which vocabulary is canonical.
- **Filenames are literal** — no filename is interpolated from a setting; `dc.yml` stays `dc.yml`, and every filename remains a stable, greppable fact ([ADR-034] §2). Likewise the assets-directory transform is literal and reversible ([ADR-018] §2).
- **The filesystem is the declaration** — roles, records, and the mapping between them are declared by what is on disk and the ADR corpus, never by a manifest or marker file; the mapping is *projected*, read-only, via `sat config map` ([ADR-034] §3).

---

## 9. Map — scope × kind × carrier

| Scope | Role | Typical payload kinds | Carrier |
|---|---|---|---|
| SAT | sat (instance) | identity, provenance, canonical metadata, children | `.<instance>.assets/sat/` (inside the instance root) |
| Collection | collection | identity, provenance, canonical metadata, collection, work index, children | `.<collection>.assets/collection/` (inside; shares the assets directory in a dual-role directory) |
| Archive | archive | identity, provenance, canonical metadata, language, children | `.<lang>.assets/archive/` (inside the archive root) |
| Content-directory | content (container) | identity, provenance, canonical metadata | `.<dirname>.assets/content/` (inside the directory) |
| Content | content (item) | body; records (identity, canonical metadata, fixity); media; derived renditions | body = the file itself; everything else in `.<filename>.assets/` beside the file — records under `content/`, media and renditions directly inside |

Beneath every operator tier, the shipped defaults floor contributes that tier's `en/bin/sat/defaults/<tier>/metadata/dc.yml` ([ADR-032] §2).

---

## 10. Usage notes

- **Name by attributes.** Give an asset its *scope*, *kind*, and *carrier* when precision matters; drop attributes that are clear from context.
- **Keep the two questions separate.** *Carrier* answers where a payload lives (the assets directory — inside a directory, beside a file — and which role directory within it); *kind* answers what it is (record, metadata, media).
- **Keep the setting and its value distinct.** "Canonical metadata" is the role; Dublin Core (`dc:`) is the current value of the `sat:metadata_schema` setting, per [ADR-028].
- **Keep the two mechanisms distinct.** *Permission* is copy-once delegation of a tier; the *defaults floor* is read-time, SAT-owned resolution. The same filename (`dc.yml`) appears in both; the mechanisms never mix ([ADR-032] §4).
- **One word per idea.** *Assets directory* = the carrier; *role directory* = a tier's records inside it; *sidecar* = an egress-output metadata file, nothing else; *record* = a metadata payload kind; *resources* = the reserved parent for operator resources.

---

[ADR-018]: ../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md
[ADR-021]: ../architecture/adrs/adr-021-stable-identity-at-creation.md
[ADR-022]: ../architecture/adrs/adr-022-work-assignment-expression-joining-and-the-work-index-v0-1-6.md
[ADR-024]: ../architecture/adrs/adr-024-discovery-and-reconciliation-v0-2-2.md
[ADR-025]: ../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md
[ADR-027]: ../architecture/adrs/adr-027-fixity-v0-1-3.md
[ADR-028]: ../architecture/adrs/adr-028--dublin-core-namespace-dc--for-mvp-dcterms--deferred.md
[ADR-032]: ../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md
[ADR-034]: ../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md
