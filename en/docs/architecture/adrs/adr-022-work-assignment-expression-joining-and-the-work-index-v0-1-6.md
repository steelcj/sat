---
status: Accepted
version: 0.1.6
date: 2026-07-12
---

# ADR-022: Work Assignment, Expression Joining, and the Work Index

## Context

ADR-010 v0.1.1 gives every document two UUIDs: `dc:identifier` (the expression's own identity) and `sat:work` (the work it expresses). ADR-012 places both in `sat/identity.yml` in the document's assets directory. The goals document *Document Identity at Content Ingress* (v0.3.0) states what the ingress implementation must achieve. Three design questions remain open, and this ADR decides them.

First, assignment: when a document arrives, ingress must assign a `sat:work` UUID — either a fresh one (a new work) or an existing one (a new expression of a known work). The file itself does not say which, and a wrong join silently ties unrelated documents together, which is the class of inconsistency SAT is designed to refuse.

Second, discovery at scale: relating expressions by scanning sidecars is cheap for one document and prohibitive for a site. SAT is Universal Cake from the ground up — multilingual support is foundational, not additive — so the design must remain cheap at twenty-six language archives, not two.

Third, the expression model's axes: whether expression identity is keyed by language alone, or by language plus a variant dimension (plain-language, easy-read, and other access expressions). Accessibility is the first priority of the project. Put in lay persons terms, design decisions are made in ways that lead to the inclusion of more people over time without a redesign.

The investigation that most shaped this ADR is Plone's translation model: content objects carry UUIDs, translations share a group UUID, and a rebuildable catalog maps groups to objects by language and current path, so content may move freely and be reorganized, without breaking relationships between documents.

## Decision

### Default assignment: a new document is a new work

Ingress mints a fresh `sat:work` for every document unless the operator declares otherwise. A wrong "new work" is cheap to repair with the link operation below; a wrong join is a silent inconsistency. The default is therefore never to join.

```yaml
# en/products/.razor-guide.md.assets/content/identity.yml — written at ingress
dc:identifier: urn:uuid:2b9d4e01-88af-4c37-9f1e-6a0c3d5b7e21
sat:work: urn:uuid:7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e
```

### Declaration is supported both at ingress and afterward

Both moments are supported because they serve different needs: declare at ingress when the work is known at drop time; link afterward for repair, batch work, and backfill. The link operation is required regardless — ingress declaration is the convenience built on top of it.

#### At Ingress

At ingress, the operator may declare the work directly. Humans remember filenames and titles, not UUIDs, so `--expression-of` accepts three address forms everywhere it appears, resolved in this order: a path (resolved through the document's own sidecar), a `dc:identifier` (resolved through the work index), or a `sat:work` UUID (used directly). The path form is the expected common case:

```text
content ingress fr/produits/guide-rasoir.md --expression-of en/products/razor-guide.md
```

For the "I know it's called something like razor" moment, a lookup command searches the index's paths and the expressions' `dc:title` values and prints the matching works with their UUIDs and expressions:

```text
collection work find razor
work urn:uuid:7f3ac291-…5c6e
  en  en/products/razor-guide.md   "Razor Maintenance Guide"
```

#### After Ingress

After ingress, the join operation joins an existing document to a work. The operation is named *join*, not *link*: to developers, *link* means filesystem hard and symbolic links, a live collision in a filesystem-native tool. Dry-run by default, per the house rule:

```text
collection work join fr/produits/guide-rasoir.md --expression-of en/products/razor-guide.md
PLAN: fr expression joins work urn:uuid:7f3ac291-…5c6e (currently a work of one)
  sat:work        urn:uuid:d901e4b2-…44aa → urn:uuid:7f3ac291-…5c6e
  sat:work_retired append: {uuid: urn:uuid:d901e4b2-…44aa, retired: <now>, by: "collection work join --apply"}
No records were written (--dry-run). Pass --apply to join.
```

`dc:identifier` is immutable without exception. `sat:work` is operator-adjustable through the join operation only — a deliberate, recorded act, never an ingress side effect. 

The document's previous lone `sat:work` is retired into `sat:work_retired`: an append-only list of mappings, each recording the retired UUID, when it was retired, and the operation that retired it — a provenance trail, because that is what retirement is.

```yaml
sat:work_retired:
  - uuid: urn:uuid:d901e4b2-…44aa
    retired: "2026-07-12T21:40:00Z"
    by: "collection work join --apply"
```

ADR-010's `dc:identifier_retired` is flagged for the same structured shape at its next amendment, so the two retirement records do not diverge.

### Tooling may suggest a work; it never assumes one

When the collection declares a `mirrored` relationship (ADR-011) and the work index contains a plausible counterpart, ingress records a suggestion in the ingress record and its report. Clarity on what `mirrored` means here, stated in the project's own terms: `mirrored` declares intent — these archives are meant to translate a language source. Completeness is state — full, partial, or missing — and state is never declared, only discovered. The work index is that discovery: a work with an `en` expression and no `fr` expression under a mirrored declaration is a translation gap, findable in one lookup. 

> Partial translation is therefore not a relationship type; it is the normal, observable state of a mirrored collection in progress.

```text
NOTE: fr/produits/guide-rasoir.md ingressed as a new work.
  A mirrored counterpart may exist: en/products/razor-guide.md
  (work urn:uuid:7f3ac291-…5c6e has no fr expression).
  To join: collection work join fr/produits/guide-rasoir.md --expression-of en/products/razor-guide.md
```

Suggestions are evidence for the operator, never input to assignment.

> No filename matching, no path matching, and no relationship declaration ever causes an automatic join.

### Expression identity is keyed by language alone, with a structural extension point

In our MVP, a work has at most one expression per language. Two same-language expressions claiming one work is a validation finding. Again, this is the **MVP model**.

#### Future forward configuration style for accessibility

After the MVP we can leverage the variant axis. For example, technical-language, easy-read, and other access expressions of one work, is an accessibility infrastructure this project may be able to leverage in future SAT versions.

It is deliberately not designed here.

You will notice that the schema below reserves its place structurally: expressions nest under an explicit `languages:` key, so a future axis arrives as a sibling key without moving anything that exists.

Opening that door requires two things first: a decision on the canonical sidecar declaration of variant (its own ADR), and only then the index reflecting it. Schema follows declaration; the index never leads the sidecars.

### The work index: a derived, disposable lookup

Tooling maintains a work index answering "every expression of this work" in one lookup instead of a scan of every language archive.

```yaml
# Derived record. Sidecars are canonical.
# Delete and rebuild at any time.

sat_version: "0.1"
generated: "2026-07-12T21:40:00Z"
generated_by: "sat-ingress 0.5.0"
path: ...

works:
  urn:uuid:7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e:
    languages:
      en:
        identifier: urn:uuid:2b9d4e01-88af-4c37-9f1e-6a0c3d5b7e21
        path: en/products/razor-guide.md
      fr:
        identifier: urn:uuid:c4a17f92-3d6b-4e08-ab55-1f8e2c9d0a43
        path: fr/produits/guide-rasoir.md
# Potential future expansion of works axis's, needs development, ADR
#    style_guides:
#      technical:
#        identifier: urn:uuid:...
#        path: ...
```

The header above is the generated record header defined in the source header convention (v0.3.0): a path line, the rebuild remedy, then `sat_version`, `generated`, and `generated_by` as a mapping of the invoking `command` and the sat-tools `version`. One satlib writer stamps it on every write, so the shape cannot vary by command.

Schema commitments:

one entry per work, keyed by `sat:work`; expressions under `languages:`, keyed by language — the one-per-language rule is therefore structurally unrepresentable to violate; each expression carries exactly `identifier` and `path`, nothing descriptive (that is `dc.yml`'s job, and duplication is the divergence the canonical rule exists to prevent); the generated record header marks the record as tool-written and carries the remedy, per the source header convention.

Placement is governed by ADR-025's role directories, which superseded this section's original flat-versus-operational-namespace principle: the work index is a collection-tier record and lives in the collection role directory, `{collection}/.{collection}.assets/collection/work-index.yml`, beside `collection.yml` and the children index.

The role directory is also the permission boundary made concrete (ADR-004, ADR-025): everything SAT writes at this tier is protectable with one filesystem grant. The collection declaration is settled as `collection.yml`, in the collection role directory — ADR-011's `sat-collection.yml` name drops its prefix, since location already namespaces it.

The relationships the collection declares (intent, in `collection.yml`) and the index those relationships materialize (state, in `sat/work-index.yml`) live in the same assets directory, intent flat and state in the operational namespace.

### Consistency model: canonical sidecars, incremental updates, rebuild as remedy

Sidecars are canonical; the index is derived. If they disagree, the index is wrong by definition.

Ingress and link operations update the index incrementally as they write sidecars. But SAT has no transaction — a plain `mv` touches no index — so staleness is accepted as a known cost rather than engineered away. The remedies: any tool that finds the index missing or inconsistent with the sidecars it reads may rebuild it; a rebuild command exists for the operator; and validation rebuilds and compares as a conformance check, reporting divergence as a finding. This is Plone's catalog relationship with weaker consistency, stated honestly: Plone reindexes transactionally on move; SAT repairs by rebuild.

One principle is set now for that future: **automation narrates.** When the filesystem watcher (ADR-014) eventually automates index maintenance, every automated act writes a legible, operator-readable record — what changed, what was rebuilt, and why. The origin of this rule, from the creator during this ADR's drafting: a project that exists to increase understanding cannot ship tooling that behaves like magic — Clarke's third law ("any sufficiently advanced technology is indistinguishable from magic") is, for SAT, both a  warning and an aspiration. If it appears to be magic then documentation needs to be significantly better in order for humans; developers, users and potential users are able to grasp the underlying concepts.

### satlib owns the machinery

Work assignment, link semantics including retirement, index build, incremental update, read, and comparison live in satlib (ADR-019). `content ingress`, `collection work join`, `collection work find`, `collection work index --rebuild`, and validation are thin callers.

### Tier executables own the permissions

satlib provides every mechanism this ADR defines; which executable tier may invoke each mechanism is a permission concern, delegated by the filesystem (ADR-004). Work assignment at ingress is a content-tier act, invoked through `bin/content/`. Joining expressions, finding works, and rebuilding the index modify or read collection-scoped records, and are collection-tier acts, invoked through `bin/collection/`: `collection work join`, `collection work find`, `collection work index --rebuild`. Nothing in `bin/sat/` performs work or index operations — the instance tier instantiates and delegates; it does not manage a collection's works.

The permission boundary is enforceable with filesystem ownership at both ends: the tier's executable directory (`bin/collection/`) and the records it writes (`.{collection}.assets/sat/`) can be owned by the same collection operator, so the ability to run the operation and the ability to modify its records are one grant.

## Alternatives Considered

**Join by inference — filename, path symmetry, or `mirrored` declarations as assignment input** — rejected. `fr/produits/guide-rasoir.md` beside `en/products/razor-guide.md` is suggestive and nothing more; inference converts a suggestion into a silent join, the exact failure the default exists to prevent. Inference survives only as operator-facing suggestion text.

**Declaration at ingress only, no join operation** — rejected. It forces the operator to be present and informed at drop time, fails batch ingress entirely, and provides no repair path for wrong assignments or pre-existing content. Join is required regardless; ingress declaration is the convenience, not the foundation.

**Join operation only, no ingress declaration** — rejected as needless friction. When the operator already knows the work at ingress time, forcing a second command adds a step and a window in which the archive is knowingly wrong.

**No index — scan sidecars on demand** — rejected. Correct but priced for two languages, not twenty-six. The multilingual commitment is foundational; the design must not tax it linearly per language.

**Index as a second source of truth (authoritative registry)** — rejected. A registry that must be right invites the divergence problem; a derived record that is allowed to be wrong and cheap to rebuild cannot diverge in any way a rebuild does not cure. Plone's rebuildable catalog is the precedent.

**Language keys directly under the work (no `languages:` wrapper)** — rejected. It silently occupies the only extension point; adding any second axis would restructure every entry. The wrapper costs one nesting level and buys structural room for the variant axis.

**A `style:`/variant block in the MVP schema** — rejected for now, in three parts: it is the variant axis, which is deliberately deferred; no canonical sidecar declares variant yet, and the index may never lead the sidecars; and flat booleans (`7th-grade: true`) name that an expression exists without locating it. The variant axis, when opened, nests structured entries carrying identifier and path, shaped like `languages:`.

**link as the operation name** — rejected. To developers, *link* means hard and symbolic links; in a filesystem-native tool the collision is live, not theoretical. *join* carries the intended meaning in plain English, invites a work-scoped command family (`collection work join`, `collection work find`), and *link* is retired in the controlled vocabulary so it is not innocently reinvented.

**Paths excluded from the index (UUIDs only)** — rejected. An index that answers "the expression exists somewhere" still forces the scan it exists to avoid. Path is included as the deliberately volatile field, following Plone; staleness is the accepted cost and rebuild the remedy.

## Consequences

- Ingress always assigns `sat:work`: fresh by default, declared via `--expression-of` (path, `dc:identifier`, or `sat:work` UUID) when the operator knows the work; `collection work find` translates names to UUIDs
- `collection work join` (dry-run by default) joins existing documents to works; the previous lone work UUID is appended to `sat:work_retired` with timestamp and acting operation; ADR-010's retirement record is flagged for the same structured shape
- `dc:identifier` is immutable; `sat:work` changes only through the join operation
- Suggestions from `mirrored` relationships and the index appear in ingress records and reports; they never cause assignment
- One expression per language per work; violations are validation findings
- The variant axis is a recorded extension point: sibling key to `languages:`, blocked on a sidecar-declaration ADR, no redesign required to open
- `work-index.yml` lives in the collection role directory (`.{collection}.assets/collection/`, ADR-025): derived, disposable, incrementally updated by ingress and join, rebuildable by command, verified by validation's rebuild-and-compare
- satlib gains the work/join/index machinery; work and index operations are collection-tier (`bin/collection/`), ingress is content-tier (`bin/content/`); CLIs stay thin
- Automation narrates: future automated index maintenance (ADR-014) writes operator-readable records of every automated act
- The goals document (v0.3.0) is satisfied on every point it states; its schema section and this ADR's section 5 are the same schema
- This ADR is deliberately authored in two registers — a technologist document and a 7th grade document. Under this ADR's own model they are two works, since both are English and a work has at most one expression per language. Their pairing is mise en place: deliberate practice for the variant axis, producing the authoring experience the future variant ADR will draw on. When that axis opens, they become the first candidates for joining as variant expressions of one work


## References

- ADR-010: Document identity and cross-language linking (v0.1.1)
- ADR-011: SAT collection model
- ADR-012: Conformant document schema
- ADR-018: Universal assets directory convention
- ADR-019: satlib as single source of truth with thin-tier CLIs
- ADR-020: Controlled vocabulary and creation-event terminology
- ADR-021: Stable identity at creation
- Document Identity at Content Ingress: Goals (v0.3.0)
- Source header convention (v0.2.0)
- Plone Foundation. (2024). *plone.app.multilingual documentation*. Plone Foundation. https://github.com/plone/plone.app.multilingual

## Licence

Copyright (C) 2026 Christopher Steel

This file is part of SAT (Source Archive Tools).

SAT is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

SAT is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with SAT. If not, see <https://www.gnu.org/licenses/>.

This document was prepared with AI assistance from **Claude (Anthropic)**.

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.6 | Accepted | PATCH per accepted ADR-025: document identity example path corrected to content/identity.yml (ADR-010 v0.1.3); work index placement updated to the collection role directory; the flat-versus-operational-namespace paragraph superseded by role directories |
| 0.1.5 | Accepted | Creators Notes resolved: link renamed to join (filesystem-link collision) with the work-scoped command family under bin/collection; generated record header adopted per source header convention v0.3.0 (path line, rebuild remedy, generated_by as command/version mapping); index placed in the collection's sat/ operational namespace with the flat-records-versus-operational-namespace principle stated; collection declaration settled as collection.yml flat in assets; tier-permissions stub drafted in full |
| 0.1.4 | Accepted | Edits for clarity and better understanding and adherence to the SAT Controlled Vocabulary, additional creators notes |
| 0.1.3 | Accepted | Accepted status, minor rewrites for clarity and better understanding |
| 0.1.2 | Proposed | Creators Notes resolved into decided text: three address forms for --expression-of with sat work find; structured append-only sat:work_retired (uuid, retired, by) with ADR-010 flagged for the same shape; mirrored clarified as intent with completeness as discovered state; automation-narrates principle set with Clarke's third law recorded as its origin; dual-register consequence corrected to two works with mise en place framing |
| 0.1.1 | Proposed | Added Creators Notes and some minor edits |
| 0.1.0 | Proposed | Initial draft: new-work default, dual declaration paths with sat link and work retirement, suggest-never-assume, one-axis expression model with variant door, work index schema and consistency model, Plone lineage recorded |
