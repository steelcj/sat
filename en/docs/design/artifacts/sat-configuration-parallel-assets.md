# Parallel Assets in SAT -  Detached Trees vs Twinned Directories

*A naming model for the two ways SAT can lay out configuration and metadata "assets" in parallel to its content, and the vocabulary to tell them apart cleanly.*

> **Superseded — retained as a working artifact.** This document predates access to the ADR corpus, and the vocabulary it recommends has since been decided against. [ADR-018](../../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md) settles the carrier: one per-entity assets directory, `.<name>.assets`, placed *inside* the directory it describes and *beside* the file it describes — not a fixed `.sat.assets` twin beside each node, and media live *inside* a file's assets directory rather than as dot-file siblings. [ADR-025](../../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md) retires *co-located* and *nested* as topology terms, and [ADR-034](../../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md) narrows *sidecar* to the egress/transmog output sense only. *Twinned assets*, *detached asset tree*, and the *in-tree / out-of-tree* axis are therefore retired: read them as the ADR-018 assets directory with its inside/beside placement rule. The body below is unchanged as the historical record of how the terms were chosen; the ADRs are authoritative on every point of conflict.

---

## 1. What "parallel assets" means

SAT can store a node's configuration and metadata in three broad ways:

- **Records** — sparse per-role files written *into* the archive tree and resolved by the cascade.
- **Sidecars** — per-document files sitting *beside* a single document (`.dc.yml`, `.og.yml`, `.schema.yml`).
- **Parallel assets** — assets kept in a directory structure that *mirrors* the SAT tree rather than being embedded in it.

This document is about that third option. "Parallel assets" is the umbrella term: the assets shadow the shape of the content, but live in their own directory hierarchy. There are two distinct forms of it, and they behave differently enough that they deserve different names.

---

## 2. The naming axis: in-tree vs out-of-tree

The two forms differ on exactly two properties:

1. **Where the mirror lives** — off in a separate location, or right beside the content.
2. **Whether it repeats per level** — one consolidated store, or a twin at every directory that cascades.

The clearest axis to name them on is one developers already know from build systems — **out-of-source vs in-source builds** — reduced here to **out-of-tree** and **in-tree**. Everything else follows from that single distinction.

---

## 3. Detached asset tree (out-of-tree)

One consolidated mirror that lives somewhere else entirely — a single store, one hop away from the content, that does **not** cascade.

**Example**

```yaml
# The SAT tree
~/sat

# The assets tree (separate root)
~/.local/share/sat
~/.local/share/sat.assets
```

**Reads as:** *the assets are detached from the content and kept in one external place.*

**Recommended term:** **detached asset tree** (a.k.a. *out-of-tree assets*)
**Alternates:** external asset tree, central asset store, shadow store, asset vault

**Why it lands:** it is exactly a GPG **detached signature** or an **out-of-source build** — the thing that describes the tree lives apart from the tree. "Detached" also signals the defining property: the assets do **not** travel with the content, so moving or copying the content alone leaves them behind.

**Best suited to:** shipped or consolidated assets you want to audit, back up, or permission as a single unit.

---

## 4. Twinned assets (in-tree)

A `.sat.assets` directory paired with its SAT directory at each level, cascading down the tree. Because the config sits right next to whatever you are editing — and each level takes part in deepest-wins resolution — this is the form that is friendliest during active development.

**Example**

```yaml
# A SAT directory and its twin, side by side, at each level
~/sat
~/.sat.assets
```

**Reads as:** *every SAT directory has a twin assets directory beside it, and they cascade together.*

**Recommended term:** **twinned assets** (a.k.a. *in-tree parallel assets*, *cascading twins*)
**Alternates:** paired assets, sibling assets, co-located parallel assets

**Why it lands:** the **town-twinning** metaphor — two structures that stay separate but walk in step. A spelling nuance worth keeping: *twinned* (paired, like twins) is more accurate than *twined* (braided/intertwined), because the point is that the two trees stay parallel rather than interleave.

**Best suited to:** active development and local, per-level overrides that resolve through the cascade.

---

## 5. At a glance

| | Detached asset tree | Twinned assets |
|---|---|---|
| **Axis** | out-of-tree | in-tree |
| **Location** | separate root (e.g. an XDG data dir) | sibling beside each SAT dir |
| **Count** | one consolidated store | one twin per level |
| **Cascades?** | no — single store | yes — deepest-wins down the pair |
| **Travels with content?** | no | yes (moves with the subtree) |
| **Best for** | shipped / consolidated, audit-as-a-unit | active development, local overrides |

---

## 6. Terminology hygiene

Keep three words pointing at exactly one thing each, so the vocabulary never blurs:

- **Sidecar** — a co-located *per-document* file (`.dc.yml`, `.og.yml`, `.schema.yml`). Do **not** call a twinned directory a "sidecar."
- **Twinned assets** — a *per-directory*, in-tree parallel assets directory that cascades.
- **Detached asset tree** — a single, out-of-tree parallel assets store that does not cascade.

---

## 7. Glossary additions

- **Parallel assets** — configuration/metadata stored in a directory structure that mirrors the SAT tree rather than being embedded in it. Comes in two forms: *detached* and *twinned*.
- **Detached asset tree (out-of-tree assets)** — one consolidated assets mirror in a separate location; does not cascade; does not travel with the content.
- **Twinned assets (in-tree parallel assets)** — a `.sat.assets` twin beside each SAT directory; cascades deepest-wins; moves with its subtree.
- **In-tree / out-of-tree** — the axis distinguishing the two, borrowed from in-source vs out-of-source builds.
