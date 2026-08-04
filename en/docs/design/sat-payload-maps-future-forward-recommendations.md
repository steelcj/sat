---
dc:title: "SAT Payload Maps — Future-Forward Recommendations"
dc:description: "Idealized SAT payload maps: where each payload lives, by scope, kind, carrier, and layout, optimized for cascade clarity, onboarding, and preservation safety."
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
  - payload map
  - assets
  - canonical metadata
dc:identifier: "sat-configuration-payload-maps"
---

# SAT Payload Maps — Future-Forward Recommendations

> **Superseded where in conflict.** The ADR corpus is authoritative. Where the recommendations below conflict with [ADR-025](../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) (role-named assets directories, sparse inheritance, and the resolution order), [ADR-032](../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md) (the shipped defaults floor), or [ADR-034](../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md) (operator-side concern parents and the derived mapping projection), the ADRs win.

Idealized "perfect" maps of where each SAT payload lives, stated in the shared vocabulary (asset, payload, carrier, scope, canonical metadata). These describe target end-states, not migration steps or implementation cost.

> **Naming.** Assets directories follow ADR-018's literal per-entity transform, `.<name>.assets`: `test-collection/` carries `.test-collection.assets/`, `en/` carries `.en.assets/`, and `guide.md` is accompanied by `.guide.md.assets/`. A `.sat.assets/` appears only where the entity is literally named `sat`. A directory's assets directory lives *inside* the directory it describes; a file's lives *beside* the file.

---

## Design principles

Five principles, drawn from the considerations discussed, drive every map:

1. **Carrier follows purpose, not scope.** How a payload is stored is chosen by its lifecycle (working vs frozen vs media), not by which tier it sits in.
2. **Cascade the working records.** Payloads that operators tune resolve deepest-stated-value-wins across scopes, sparse at every level.
3. **Consolidate the preservation set for audit** — but never at the cost of a second source of truth.
4. **Weld media to its document.** Content-associated media travels with the body.
5. **Vocabulary and storage stay independent.** Maps name the *canonical metadata record*, never `dc`, so a change to the `canonical-metadata` setting never disturbs the map.

Derived metadata (og, schema) never appears as a source payload in any map: it is regenerated from the canonical metadata record on publish, and persisted — if at all — as a sidecar in the output tree.

---

## Recommendation 1 (primary) — In-tree source, derived projection

The recommended "perfect" map. All working records live in **per-entity assets directories (in-tree)** — inside the directory they describe, beside the file they describe (ADR-018) — so they cascade and travel with their subtree; content media live **inside their document's assets directory**; and the immutable preservation set is *additionally* visible as a **derived, read-only projection**, not a second source.

The projection is what resolves the classic "two trees to sync" problem, by never being a second tree at all: the in-tree records remain canonical, and the consolidated view of the write-once payloads is in the derived, disposable class (`children.yml`, `work-index.yml`, ADR-022; `sat config map`, ADR-034 decision 3) — regenerated on demand, never authoritative, never cached. It exists purely to be read: it answers audit questions in one place without ever becoming a place that could drift.

### Payload map

| Scope | Payload (kind) | Carrier | Layout | Cascades | Lifecycle |
|---|---|---|---|---|---|
| SAT | identity record | parallel | in-tree assets | no (own) | write-once |
| SAT | provenance record | parallel | in-tree assets | no | append-only |
| SAT | canonical metadata record | parallel | in-tree assets | yes (root floor) | sparse, override |
| SAT | fixity record | parallel | in-tree assets | no | write-once |
| SAT | children record | parallel | in-tree assets | no | regenerable |
| SAT | collection record (dual-role) | parallel | in-tree assets | yes | sparse, override |
| Collection | identity / provenance / fixity | parallel | in-tree assets | no | write-once / append |
| Collection | canonical metadata record | parallel | in-tree assets | yes | sparse, override |
| Collection | children record | parallel | in-tree assets | no | regenerable |
| Collection | collection record | parallel | in-tree assets | yes | sparse, override |
| Archive | identity / provenance / fixity | parallel | in-tree assets | no | write-once / append |
| Archive | canonical metadata record | parallel | in-tree assets | yes | sparse, override |
| Archive | children record | parallel | in-tree assets | no | regenerable |
| Archive | language record | parallel | in-tree assets | yes | sparse |
| Content-directory | identity / provenance | parallel | in-tree assets | no | write-once / append |
| Content-directory | canonical metadata record | parallel | in-tree assets | yes | sparse, override |
| Content-directory | children record | parallel | in-tree assets | no | regenerable |
| Content (item) | body payload | — | content tree | — | authored |
| Content (item) | media payload | parallel | **inside the file's assets dir** | — | write-once |
| Content (item) | canonical metadata record | parallel | in-tree assets | resolves cascade → frozen leaf | **immutable once resolved** |
| Content (item) | provenance / fixity | parallel | in-tree assets | no | write-once / append |
| Content (item) | derived metadata (og, schema) | sidecar | output tree | — | regenerated on publish |
| All (preservation set) | frozen canonical record + provenance + fixity + identity | — | **derived projection (on demand)** | n/a | derived, disposable; never cached |

### Illustrative layout

```yaml
# Source (canonical): per-entity assets directories in-tree (ADR-018),
# inside each directory, beside each file
~/sat/
  .sat.assets/                     # the instance's assets, inside it — named `.sat.assets`
                                   #   only because the entity is literally named `sat`
                                   #   (sat + collection dual-role)
  collections/
    test-collection/
      .test-collection.assets/     # the collection's assets, inside it
      en/
        .en.assets/                # the archive's assets, inside it
        docs/
          .docs.assets/            # the content-directory's assets, inside it
          guide.md                 # body payload
          .guide.md.assets/        # the file's assets, beside it
            figure-1.svg           # content-media payload, inside the assets dir

# Preservation projection: derived and read-only (`sat config map` class,
# ADR-034 decision 3) — rendered on demand from the in-tree records,
# never authoritative, never cached; there is no stored second tree
```

### How it serves the goals

- **Layering** — every tunable record cascades deepest-wins, sparse; the content-scope canonical record is the frozen leaf of that cascade.
- **Onboarding** — one rule for working config ("the entity's assets directory — inside a directory, beside a file"), one rule for media ("inside the document's assets directory"); the derived projection answers "show me all fixity / all provenance" in one read.
- **Preservation & safety** — the immutable set is consolidated for audit on demand without becoming a rival source of truth: a projection that is never stored can never drift.

---

## Recommendation 2 (alternative) — All in-tree

A single-carrier, development-first map: drop the derived projection; the preservation set stays in the per-entity assets directories in-tree with everything else. "Show me all fixity" becomes an ad-hoc tooling tree-walk rather than a rendered report.

- **Differs from primary:** the final table row (derived projection) is removed; the immutable payloads remain in-tree, write-once.
- **Best for:** active development and small instances where locality and a single rule outweigh consolidated audit.
- **Trade:** maximum simplicity and locality; audit-as-a-unit is a computed view, not a place.

---

## Recommendation 3 (alternative) — Detached mirror at rest

An archival/distribution map: the at-rest form is a **detached asset tree (out-of-tree)**, produced by export tooling from the in-tree source, so the content tree ships completely clean (bodies only, no in-tree assets). Content media are either inlined into the detached tree or referenced.

- **Best for:** shipping a read-only distribution, or cold archival, where a pristine content tree and one consolidated asset store matter most.
- **Trade:** cleanest possible content tree and unit-level handling; loses in-tree cascade and locality. This profile is a destination, never a working or authoritative form — it is an egress product, pairing naturally with Recommendation 1 as its export, and always regenerable from the in-tree source.

---

## Cross-cutting rules (all maps)

- **Media live in the document's assets directory, always.** A content-media payload is welded to its body by living inside the body's assets directory (`.guide.md.assets/figure-1.svg`, ADR-018), never as a dot-file sibling of the document. At rest (Recommendation 3), an export may inline or reference it, but the source placement does not change.
- **Derived metadata is output, not source.** og/schema are regenerated from the canonical metadata record on publish; persisted only as sidecars in the output tree, never in the metadata directory.
- **Canonical metadata record is the content-scope leaf.** Once the cascade resolves at a content item, its canonical metadata record is frozen and immutable by default.
- **The metadata directory is realized by the carrier.** In the source it is the entity's assets directory (inside a directory, beside a file, ADR-018); in an at-rest export it is the mirrored entry. Its vocabulary is whatever the `canonical-metadata` setting names.
- **Records may ride either carrier.** Nothing about a record's kind fixes its carrier; the profile does.

---

## At a glance

| | In-tree source, derived projection | All in-tree | Detached mirror at rest |
|---|---|---|---|
| Working records | in-tree assets | in-tree assets | detached (at-rest export) |
| Preservation set | derived projection (read-only, on demand) | in-tree assets | detached (in the export) |
| Content media | in the file's assets dir | in the file's assets dir | inlined / referenced |
| Cascade | yes | yes | no (at rest) |
| Content tree cleanliness | assets in-tree | assets in-tree | pristine (bodies only) |
| Audit-as-a-unit | yes (on-demand projection) | computed | yes |
| Best for | the general "perfect" default | development, small instances | distribution, cold archival |

---

## Recommendation

Adopt **Recommendation 1 (In-tree source, derived projection)** as the standing "perfect" map, and treat **Recommendation 3 (Detached mirror at rest)** as its export target for shipping or archival. **Recommendation 2 (All in-tree)** is the natural reduction for development and small instances. All three share the same cross-cutting rules, so a node can move between them without changing what its payloads *mean* — only where they are carried.
