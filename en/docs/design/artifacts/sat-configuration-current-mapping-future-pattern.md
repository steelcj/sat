# SAT Configuration — Current Map & Future Pattern

*A mapping of every configuration file Source Archive Tools (SAT) reads or produces, the patterns already at work, and a grounded proposal for more effective configuration mapping.*

> **Superseded — retained as a working artifact.** This document predates access to the ADR corpus; its future-pattern proposals and open questions have since been decided there. The assets-directory spelling it raises as an open question (`.assets/<role>/` vs `.sat.assets/<role>/`) is settled by [ADR-018](../../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md): the name is the per-entity transform `.<name>.assets`, inside the directory it describes and beside the file it describes, with media *inside* a file's assets directory. Role directories, the flat record set, and the retirement of *co-located* and *nested* are governed by [ADR-025](../../architecture/adrs/adr-025-role-named-assets-directories-sparse-inheritance-and-the-resolution-order-v0-2-1.md); the nine-layer resolution above the shipped defaults floor by [ADR-032](../../architecture/adrs/adr-032-shipped-defaults-floor-below-the-operator-cascade-v0-1-1.md); discovery-as-a-read by [ADR-024](../../architecture/adrs/adr-024-discovery-and-reconciliation-v0-2-2.md); and the narrowed sense of *sidecar* plus the projected-never-declared mapping by [ADR-034](../../architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md). The body below is unchanged as the historical record; the ADRs are authoritative on every point of conflict.

> **Status:** Draft for discussion, **revised after reading `en/bin/`**. My first pass was built from the one-page mapping alone and inferred the wrong model; this version is grounded in the actual tooling (`sat`, `archives`, `collection`, `content`, `transmog`, and the `satlib` calls they make). Anything I still couldn't see directly — chiefly the internals of `satlib` — is flagged as *Assumption*.

---

## 1. Purpose

SAT is a filesystem-first framework for managing **source archives**: an instance holds collections, collections hold language archives, archives hold content. Its behaviour is driven entirely by small YAML files on disk — there is no runtime state and no database, by design (the "filesystem-visible, no runtime state" principle referenced in `markdown.yml`).

This document does three things:

1. **Maps** all of SAT's configuration — the file families, the locations they live in, and the order they resolve in.
2. **Names the patterns** SAT already uses well, so a redesign preserves rather than reinvents them.
3. **Proposes** more effective configuration-mapping patterns, using SAT's own vocabulary (roles, tiers, cascade, sparse records, floor, sidecar, definition, preseed) and respecting its ADR history.

It is aimed at the three goals you set — **clearer layering**, **easier onboarding**, and **validation & safety** — and at the mapping doc's own goals: *standard locations via a repeatable pattern*, *gathering every YAML SAT produces*, and *uncovering a better design pattern*.

---

## 2. How SAT is built (orientation)

A few structural facts shape everything about the configuration:

- **Tiers / roles.** SAT models four roles, from broad to narrow: **sat** (the instance), **collection**, **archive** (a language archive), and **content** (a content-organizing directory). The instance root is *dual-role* — it is both the sat role and a collection role at once (ADR-026). Roles are the axis that configuration cascades along.
- **Tools.** Five tool groups live under `en/bin/`: `sat`, `archives`, `collection`, `content`, `transmog`. Each can be toggled on/off (`transmog` currently off).
- **`satlib`.** The newer tools (`sat`, `collection`, `content`) delegate all real logic to a shared `satlib` package — discovery, roles, the cascade, cataloging, language/BCP-47, SPDX, fixity, children indexes. The older tools (`archives`, `transmog`) are **standalone**: they parse their own YAML and never touch `satlib`. This split matters a lot below.
- **ADR-driven.** Nearly every behaviour cites an Architecture Decision Record (ADR-003, -005, -021/022, -023, -025, -026, -029, -030, -032, -033…). The ADRs are the real spec; the YAML is downstream of them.

---

## 3. The current configuration map

### 3.1 Five families of configuration

Every config file in SAT falls into one of five families. Keeping these distinct is the single most clarifying move for the whole map, because they have different owners, lifetimes, and override rules.

| Family | What it is | Owner / lifetime | Examples |
|--------|-----------|------------------|----------|
| **Definitions** | Shipped files that describe *tool behaviour* and *what to build* | SAT project; versioned in the repo | `definitions/defaults/sat.yml`, `discovery.yml`, `connection.yml`, `archives/definitions/archives/*.yml`, `transmog/definitions/**` |
| **Defaults / "floor"** | Shipped baseline opinions that an operator may override downstream | SAT project; the base layer of a cascade | `defaults/content/markdown.yml`, `content/definitions/defaults/default-content-spec.yml` |
| **Records** | Sparse per-node state written into the archive tree, resolved by cascade | Written by SAT tools at init/ingress; live in the instance tree | role records: `identity`, `provenance`, `dc.yml`, `fixity`, `children.yml`, `collection.yml`, language records |
| **Sidecars** | Per-document metadata derived from / canonical to a single document | Written once next to content; largely immutable | `.<stem>.dc.yml` (canonical), `.og.yml`, `.schema.yml` (derived) |
| **Preseeds & caches** | Operator-level topology and lookup caches, generated by `init` | Operator; live under `~/.config/sat/` | `sat-preseed.yml`, `collection-preseed.yml`, `.meta/sat-meta.yml`, `instantiate-preseed.yml`, `cache/iana-registry.txt` |

### 3.2 Where configuration lives — the roots

Config is not in one place; it is spread across five roots. A newcomer's first confusion is usually *which root* a setting lives in, so naming them explicitly is half the mapping job.

| # | Root | Holds | Notes |
|---|------|-------|-------|
| R1 | `<repo>/en/bin/<tool>/definitions/` and `…/defaults/` | Definitions + floor | Shipped, versioned, read-only at runtime |
| R2 | `~/.config/sat/` | Preseeds, `.meta`, caches | Operator-owned; produced by `sat init` from the `*.example` templates |
| R3 | `~/.local/share/sat-tool/<version>/` | The seeded sat collection / data | `sat_collection.path` in the preseed |
| R4 | `default_parent` (e.g. `~/projects/sat/…`) | The real collections & archives | Per-collection `parent:` overrides `default_parent:` |
| R5 | Inside the instance tree | Role records + document sidecars | The cascade operates here |

### 3.3 The cascade — how a value is resolved *(the layering model already exists)*

SAT already has the layered-override model your "clearer layering" goal is asking for. It is stated in ADR-025 §7 and visible throughout the tooling: records are **sparse** (a node states only what differs) and resolution is **deepest-stated-value wins**. The `markdown.yml` floor says it plainly — *"an operator who disagrees with a rule overrides it at whatever tier they own … sparse, deepest-stated-value wins … this file is only the floor, not a lock."*

Resolution order, base → most specific:

```
shipped floor / definitions        (R1)   e.g. markdown.yml, default-content-spec.yml
  ⤷ operator preseed & .meta        (R2)   sat-meta.yml DC defaults, topology
      ⤷ sat (instance) role records (R5)
          ⤷ collection role records
              ⤷ archive role records
                  ⤷ content role records
                      ⤷ document .dc.yml sidecar   (canonical, write-once)
= effective configuration for a node
```

Two properties make this strong and worth protecting: records are **sparse** (no duplication — a value lives in exactly one place and is inherited), and the resolved metadata is **frozen into a `.dc.yml` sidecar at creation and then immutable by default** (ADR-023 / write-once primitives). SAT even resolves `<calculated>` fields (e.g. `dc:language_bcp47` from the filesystem language root, `dc:language` via an IANA/BCP-47 lookup) at this moment.

*This is the core finding: the "future" layering pattern is largely present today. The opportunity is less "invent layering" and more "make the layering uniform, discoverable, and validated" (§6).*

### 3.4 The content pipeline — where config enters each stage

Content flows through four stages, each governed by a different config family. This is the clearest way to see "which file controls what":

```
content ingress   → nursery/            governed by the cascade (ADR-023 cataloging) + writes .dc.yml, provenance, fixity
content egress    → egress/             governed by default-content-spec.yml (body transforms) — body only + copied .dc.yml
transmog          → transmog/<platform>/ governed by <platform>-frontmatter-spec.yml — front matter + .og.yml/.schema.yml
publication tool  → final output        MkDocs build / PDF renderer / static site
```

The pivot of the whole pipeline is the **`.dc.yml` sidecar as the single canonical metadata source of truth**: egress strips all source front matter, and transmog *regenerates* front matter, Open Graph, and Schema.org entirely from the sidecar per the platform spec. Nothing is passed through from the author's original front matter.

### 3.5 File-by-file inventory (shipped `en/bin/`)

Every configuration file in the delivered `bin/` tree, by tool:

| Path (under `en/bin/`) | Family | Role in the system |
|---|---|---|
| `sat/definitions/defaults/sat.yml` | Definition | Instance identity: name, version, language, license; `tools:` toggles |
| `sat/definitions/defaults/connection.yml` | Definition | Archive connection: location (local/remote), protocol (filesystem/ssh/…) |
| `sat/definitions/defaults/discovery.yml` | Definition | Root-discovery marker + `definitions:` map per tool + `nursery` |
| `sat/defaults/content/markdown.yml` | Floor | Markdown house-rules baseline (toggles), overridable at `.assets/<role>/markdown.yml` |
| `sat/examples/sat-preseed.yml.example` | Preseed template | Seeds `~/.config/sat/sat-preseed.yml` (version, caches, collections topology) |
| `sat/examples/collection-preseed.yml.example` | Preseed template | Seeds collection topology |
| `sat/examples/.meta/sat-meta.yml` | Preseed template | SAT-level Dublin Core defaults that cascade into `.dc.yml` |
| `archives/config/archive-definition.yml` | Definition | An archive's directory tree (areas → sub-areas) |
| `archives/config/archives-parent.yml` | Definition | `archives.root` — where archives are created |
| `archives/definitions/archives/*.yml` | Definition | Per-archive spec: name, parent, root, base_url, language, content_profile, tree |
| `content/definitions/defaults/default-content-spec.yml` | Floor | Egress body-transform spec (self-documenting toggles) |
| `transmog/definitions/mkdocs-transmog.yml` | Definition | A transmog target: platform + frontmatter_spec + source/output |
| `transmog/definitions/frontmatter/default-frontmatter-spec.yml` | Floor/template | Reference template for new platform specs (not used directly) |
| `transmog/definitions/frontmatter/{mkdocs,github,html,pdf}-frontmatter-spec.yml` | Definition | Per-platform front-matter/OG/Schema output rules |

**Produced at runtime (not in the repo):** `~/.config/sat/{sat-preseed,collection/collection-preseed,instantiate-preseed}.yml`, `~/.config/sat/.meta/sat-meta.yml`, `~/.config/sat/cache/iana-registry.txt`; and in the instance tree, per-role `identity`/`provenance`/`dc.yml`/`fixity`/`children.yml`/`collection.yml` records plus `.<stem>.dc.yml`, `.og.yml`, `.schema.yml` sidecars.

---

## 4. What the current design gets right

These are genuine strengths — the redesign should build on them, not around them:

- **A real cascade already exists.** Sparse records + deepest-wins (ADR-025) is exactly the layering model that makes config DRY and overrides local. Most systems wish they had this.
- **One canonical metadata source.** The `.dc.yml` sidecar is the single source of truth; front matter, OG, and Schema.org are all *derived* from it. Change one file, every output follows.
- **Self-documenting spec files.** `default-content-spec.yml`, `markdown.yml`, and the front-matter specs list every option inline with its default and allowed values. This is excellent onboarding-by-design.
- **Write-once / read-only-auditor discipline.** Sidecars are immutable by default; `sat licence check` audits without ever writing (correction is a separate, deliberate act). Mutation and inspection are cleanly separated.
- **Platform decoupling.** Content is authored once; each publication target is a self-contained spec (`github` = no front matter, `mkdocs` = three fields, `html` = head injection, `pdf` = renderer metadata). Adding a target is copy-a-spec, not touch-the-code.
- **Traceable decisions.** Every behaviour cites an ADR, so the *why* behind each file is recoverable.

---

## 5. Friction & inconsistencies (evidence-based)

Each item is drawn from the actual files, tagged with the goal it blocks.

| # | Friction | Evidence in the tree | Goal |
|---|----------|----------------------|------|
| F1 | **Two tool generations with different config-loading.** `sat`/`collection`/`content` use `satlib`'s cascade; `archives`/`transmog` parse YAML directly and never see the cascade. | `archive-init.py`/`transmog.py` import `yaml` and roll their own; the others `from satlib import …`. | Layering |
| F2 | **Discovery is done three+ different ways.** A marker file, a bash `dirname ../../..`, and a Python `parent.parent.parent.parent` repeated in every script. | `discovery.yml` marker vs `SAT_ROOT="$(cd …/../../.. )"` vs `sat_root()` in each `.py`. | Onboarding / Safety |
| F3 | **Hardcoded paths & language root.** `en/bin/...` and depth-4 roots are baked into files and code; layout changes break silently. | `discovery.yml` `marker:` hardcodes its own path; `sat_root()` assumes exactly four parents. | Safety |
| F4 | **No schema/validation for definitions or specs.** A mistyped toggle key is silently ignored — transmog just "sees what is enabled." | Every spec is free-form YAML; no schema files ship. | Validation |
| F5 | **Duplicated sources of truth.** `tools:` toggles appear in *both* `sat.yml` and `discovery.yml`; version appears in `sat.yml` (0.1.0), the preseed (0.4.0), and the authoritative `VERSION` file. | Two `tools:` blocks; three version strings. | Safety |
| F6 | **Directory-name vocabulary drift.** Config lives under `config/`, `definitions/`, `defaults/`, `.assets/<role>/`, and `.sat.assets/<role>/` depending on the tool. | `archives/config/…` vs `…/definitions/…` vs mapping doc's `.sat.assets/` vs `markdown.yml`'s `.assets/<role>/`. | Onboarding |
| F7 | **Stale/incorrect path headers.** File header comments name paths that don't match the file. | `archive-definition.yml` header says `en/bin/archive/config/archive.yml`; `archives-parent.yml` header says `parent.yml`. | Onboarding |
| F8 | **Two markdown-ish configs, unclear relationship.** `content_profile: commonmark` (archive def) and the `markdown.yml` house-rules floor both govern markdown, with no stated wiring. | `sat-en-docs.yml` sets `content_profile`; `markdown.yml` is a separate floor. | Onboarding |
| F9 | **Known dead code / latent discovery bug.** Flagged in the repo itself. | `sat/TODO.md`: unreachable return + dead code in `discovery.py`'s `_find_non_bin_ancestor`. | Safety |

---

## 6. Proposed future patterns

The theme is not "add layering" — SAT has that — but **make the one model uniform, discoverable, and enforced**. Six moves, each independently shippable.

### 6.1 One config taxonomy and one directory vocabulary

Adopt the five families from §3.1 as SAT's official vocabulary, and collapse the directory drift (F6) to a single rule per family:

- **Definitions & floor** → always under `en/bin/<tool>/definitions/` (retire the lone `archives/config/`).
- **Records** → always under `.assets/<role>/` beside the node (pick one spelling — `.assets` or `.sat.assets` — and use it everywhere).
- **Sidecars** → always `.<stem>.<kind>.yml` next to the document.
- **Preseeds & caches** → always under `~/.config/sat/`.

A newcomer can then answer "where does X live?" from the *kind* of X alone. Pair this with generated, always-correct path headers (fixes F7) instead of hand-typed ones.

### 6.2 One discovery mechanism

Make `satlib.discover()` the single way any tool finds the SAT root, the tier it's in, and the definitions map — and delete the bash `dirname ../../..`, the repeated `sat_root()` depth-4 walks, and the self-referential `discovery.yml` marker (F2, F3). Discovery should find the root by walking up for a stable marker (e.g. the `VERSION` file or a `.sat/` marker dir), never by counting parents or hardcoding `en/bin/...`. Fix the `_find_non_bin_ancestor` dead code (F9) as part of this.

### 6.3 Unify the two tool generations on `satlib`

Bring `archives` and `transmog` onto `satlib` so their definitions participate in the cascade and validation like everything else (F1). Concretely: archive definitions and transmog/front-matter specs become **definition-family files resolved through `satlib.discover()`**, so an operator can override a shipped spec at a tier they own (e.g. a collection-local `mkdocs-frontmatter-spec.yml`) using the same sparse/deepest-wins rule that already governs `dc.yml`. Today those specs can only be edited in place.

### 6.4 Schemas + a `sat config validate` / lint

Give every definition and spec a **versioned JSON Schema** and validate before use (F4). This pairs perfectly with the existing self-documenting style: the inline "options: true, false" comments become machine-checked. Add a `schema_version` key per file, ship `schemas/<name>.vN.schema.json` with SAT, and run a lint in CI and as a pre-flight that checks: files parse, keys are known and correctly typed, required fields are present per role, `children` entries resolve, and `tree` nodes are well-formed. Errors name *file · key · role*, failing fast and close to the cause.

### 6.5 Single sources of truth for cross-cutting values

Collapse the duplications in F5:

- **Version** lives only in `VERSION`; `sat.yml` and preseeds reference it, never restate it (migrate already treats `VERSION` as authoritative).
- **Enabled tools** live in exactly one registry (keep `discovery.yml`'s, drop `sat.yml`'s copy, or vice-versa) so they can't drift.
- **Language root** is derived once by discovery, not hardcoded as `en/` across paths — the necessary precondition for SAT ever being genuinely multi-language (ADR-003/005 already treat language as a filesystem root; the tooling paths haven't caught up).

### 6.6 `sat config map` — effective config with provenance

Ship the tool that answers the question this whole exercise is about: **given a node, show the effective configuration and *which layer/file set each value*.** This reuses SAT's own provenance instinct, turned on configuration itself, and directly serves onboarding — "why is this value what it is?" becomes one command instead of reading five roots by hand. A generated `CONFIG.md` catalog (built from the schemas, so it never drifts) rounds it out. In effect, SAT would generate the very map this document had to assemble by hand.

---

## 7. Migration path

Ordered so SAT keeps working at every step and each phase stands alone:

1. **Ratify vocabulary (docs only).** Adopt the five families, the resolution order, and one directory rule. No code change.
2. **Schema the files you already ship (§6.4).** Author schemas from the current self-documenting specs; wire `sat config validate` into CI. Immediate safety win, zero layout change.
3. **Unify discovery (§6.2).** One `satlib.discover()`; retire boilerplate and hardcoded markers; clear the `TODO.md` dead code.
4. **Collapse duplicated truth (§6.5).** VERSION-only version; single `tools:` registry; discovery-derived language root.
5. **Fold `archives` + `transmog` into `satlib` (§6.3).** Their specs join the cascade and gain per-tier override + validation.
6. **Ship `sat config map` + generated `CONFIG.md` (§6.6).** The onboarding capstone.

Each phase is valuable on its own, so the work can pause after any step and still leave SAT better mapped, safer, and easier to onboard into.

---

## 8. Assumptions & open questions

Please confirm or correct — the model adapts cleanly to any of these:

- **A1** `satlib` is the shared home for discovery, roles, and the cascade (inferred from imports; internals weren't in the `bin` bundle). The §6 proposals assume `satlib` is the right place to consolidate.
- **A2** The mapping doc's `.sat.assets/<role>/` and `markdown.yml`'s `.assets/<role>/` are the *same* per-node record convention under two spellings. If they're deliberately different, F6/§6.1 need adjusting.
- **A3** `archives` and `transmog` are intended to stay as tools but *should* eventually share `satlib`'s config handling (they're described as MVP/"locked" and "standalone"). If they're meant to stay fully independent, §6.3 is optional rather than recommended.
- **Q1** How should `content_profile` (e.g. `commonmark`) and the `markdown.yml` house-rules floor relate — is one meant to select the other (F8)?
- **Q2** Is `nursery` (from `discovery.yml`) the same staging concept as the mapping doc's `staging/`, and should staging carry its own role records?
- **Q3** Should the archive-definition `tree:` skeletons also be schema-validated (they mix `null`, `file`, `{}`, and nested maps as leaf markers — a small grammar worth pinning down)?
- **Q4** Which single location should own the `tools:` toggle and the version reference — `discovery.yml` or `sat.yml`?

---

## 9. Glossary (SAT's vocabulary)

- **Role / tier** — a level config cascades along: **sat** (instance) → **collection** → **archive** (language archive) → **content**. The instance root is *dual-role* (sat + collection).
- **Cascade** — resolution by walking base → node, **deepest-stated-value wins** (ADR-025 §7).
- **Sparse record** — a per-node file stating only what differs from its inherited value; the reason config isn't duplicated.
- **Floor** — a shipped baseline (e.g. `markdown.yml`) that sets defaults but can be overridden downstream — "the floor, not a lock."
- **Definition** — a shipped file describing tool behaviour or what to build (archive trees, transmog targets, front-matter specs).
- **Sidecar** — a per-document metadata file beside the content: `.dc.yml` (canonical), `.og.yml` / `.schema.yml` (derived).
- **Preseed** — an operator-level file under `~/.config/sat/` that seeds topology/metadata; "below the instance, the cascade is the preseed."
- **Nursery** — the staging area for arriving content during ingress.
- **Transmog** — pipeline stage 3: turn a clean egress document + `.dc.yml` into platform-ready output.
- **DC** — Dublin Core Metadata Element Set 1.1; the canonical descriptive vocabulary, carried as `dc:`-prefixed keys.
- **`satlib`** — the shared Python library the newer tiers delegate to for discovery, roles, cascade, cataloging, language, SPDX, fixity.
