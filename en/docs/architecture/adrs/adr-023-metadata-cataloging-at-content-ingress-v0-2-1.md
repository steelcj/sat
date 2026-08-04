---
status: Proposed
date: 2026-07-12
version: 0.2.1
---

# ADR-023: Metadata Cataloging at Content Ingress

## Context

Ingress must populate a document's descriptive sidecar. Two sources hold claims about every arriving document, and they answer different questions. Frontmatter, when present, is the document's claim about itself: its title, its creator, its subjects. The cascade (instance → collection → archive → content directory) is the archive's declared intent: what documents here default to. ADR-012 requires the prose to leave ingress pure, so frontmatter must be read and removed regardless; the design question is what happens between reading and writing.

This is not a new problem. Library cataloging has distinguished for over a century between elements *transcribed* from the item itself and elements *supplied* by the cataloger or an authority. SAT mechanizes that practice: the process this ADR defines is cataloging — specifically, the metadata portion of it — and its vocabulary is drawn from the tradition rather than invented.

One standing question is forced to a decision here: the cascade's merge-versus-replace behaviour for `dc:subject`, open since before ADR-020, cannot be dodged once cataloging exists.

Identity is out of scope: `dc:identifier` and `sat:work` are minted by work assignment (ADR-022) and are never imported from content. What this ADR decides is how everything else gets into the sidecar, and what happens when the two sources disagree.

## Decision

### The process is metadata cataloging

The step of ingress that reads a document's frontmatter, applies the cataloging policy against the cascade, and writes the descriptive sidecar is *metadata cataloging*. It lives in satlib as `cataloging.py` (ADR-019); `content ingress` is a thin caller. The pipeline order is mechanical: read frontmatter, strip it, resolve the cascade preseed, apply the cataloging policy field by field, then write three things — the descriptive sidecar, the pure prose, and the ingress record.

### Every field records its origin

Each value written to the sidecar carries one of three origins, recorded in the ingress record:

- **transcribed** — taken from the item itself (frontmatter), verbatim
- **supplied** — provided by the archive's intent (cascade), by tooling, or by the operator
- **noted** — recorded in the ingress record only; never admitted to the sidecar

Transcribed values are never modified. When a transcribed claim is overridden or refused, the claim is still recorded verbatim in the ingress record — the provenance of the claim survives the decision about it.

### The cataloging policy

The policy is per-field, because the sources own different questions. This table is normative.

| Field | Owner | Frontmatter handling | Conflict behaviour |
| --- | --- | --- | --- |
| `dc:title` | Document | transcribed | Closest declaration wins; cascade never supplies a title |
| `dc:creator` | Document | transcribed | Transcribed wins; absent → supplied from cascade |
| `dc:contributor` | Document | transcribed | Transcribed wins; absent → omitted entirely, never an empty string |
| `dc:subject` | Document and cascade | transcribed | Union: transcribed first, then supplied, deduplicated, order preserved |
| `dc:description` | Document | transcribed | Transcribed wins; absent → empty string, never `<calculated>` |
| `dc:date` | Document | transcribed | Transcribed wins; absent → supplied from filesystem (`st_birthtime`) or operator |
| `dc:publisher`, `dc:rights` | Cascade | transcribed accepted as deliberate exception | Transcribed wins when present and the exception is narrated; absent → supplied |
| `dc:language`, `dc:language_bcp47` | Archive structure | read, never accepted | Supplied wins always; disagreement is a finding (below) |
| `dc:type`, `dc:format` | Tooling | ignored | Supplied by tooling, which inspects the file rather than trusting claims |
| `dc:identifier`, `sat_uuid`, `translationKey`, any identity residue | Nobody | noted | Never admitted; preserved verbatim as possible join evidence (ADR-022) |
| Unrecognized frontmatter keys | Nobody | noted | Preserved verbatim in the ingress record; the operator decides their fate |

The `dc:subject` decision doubles as the answer to the standing cascade question, scoped to cataloging: subjects are additive by nature — catalogers layer subject headings, they do not overwrite them — so cataloging takes the union. Whether the cascade itself merges or replaces `dc:subject` between its own tiers is aligned to the same rule and recorded in the cascade documentation as a consequence of this ADR.

`dc:contributor` is omitted, not blanked, when nothing is transcribed — the one field in this table with no cascade fallback and no calculated default, consistent with the tradition (contributor is an optional element that should not be included when not applicable). When an author or operator states AI assistance in frontmatter, SAT's local convention represents the assistant as a plain string in the form `"Name (Organization)"` — for example `"Claude Sonnet 4.6 (Anthropic)"` — consistent with DCMI's recommendation to use a literal value when no URI is available. This is a formatting convention for a transcribed value; `cataloging.py` performs no AI-assistance detection of its own.

### Language disagreement is a finding, never a choice

A document claiming `fr` in frontmatter while sitting in an `en/` archive is either misfiled or mislabeled, and only the operator knows which. Cataloging must not pick. The document is ingressed with the archive's language (ADR-001: the filesystem is the language declaration), the disagreement is recorded as a finding in the ingress record, and the report narrates it:

```text
FINDING: fr claimed in frontmatter; archive is en.
  Ingested with dc:language_bcp47: en (the archive's declaration).
  If the document is misfiled, move it to fr/ and re-catalog.
  The claim is preserved verbatim in the ingress record.
```

### Nothing is destroyed, only relocated

The entire stripped frontmatter block is preserved wholesale in the ingress record, byte for byte. An author's claims are never silently discarded — overridden claims, noted identity residue, and unrecognized keys all survive in the record. Automation narrates, applied to metadata.

### Worked example

An arriving document:

```markdown
---
title: Guide d'entretien du rasoir
author: A. Henson
subject: [rasoirs, entretien]
language: fr
sat_uuid: 7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e
---
# Guide d'entretien du rasoir
...
```

Dropped into `en/products/` (misfiled — the finding fires), with the archive cascade supplying publisher and rights, cataloging writes the descriptive sidecar:

```yaml
# .guide-rasoir.md.assets/dublin-core/dublin-core.yml
dc:title: "Guide d'entretien du rasoir"
dc:creator: "A. Henson"
dc:subject:
  - rasoirs
  - entretien
  - grooming
dc:description: ""
dc:publisher: "Henson Shaving"
dc:rights: "CC BY-SA 4.0"
dc:language: eng
dc:language_bcp47: en
```

and the ingress record carries the origins (`dc:title: transcribed`, `dc:publisher: supplied`, ...), the language finding, the noted `sat_uuid`, and the verbatim frontmatter block. The prose file leaves with no frontmatter at all.

### Disposition of the pre-ADR-018 pipeline

Five artifacts predate ADR-018 (Universal Assets Directory Convention) and were flagged as writing to a location the current architecture does not read:

- `en/bin/content/content-metadata-ingress.py`
- `en/bin/content/content-metadata.py`
- `en/bin/content/content-ingress.py`
- `en/bin/content/definitions/defaults/default-canonical-metadata.yml`
- `en/bin/content/content-ingress-readme.md`

Examining each against `cataloging.py`/`content ingress`, they split into three concerns, not one, and each gets its own ruling. **Nothing is ported** — no code from these five files is reused — but two of the three concerns are not simply dropped; each already has a named home elsewhere in the architecture, and this ruling points at it so neither is quietly lost.

#### 1. Metadata generation — retire, no port

`content-metadata-ingress.py` (frontmatter extraction via a "richness heuristic" across namespaces) and `content-metadata.py` (sidecar generation from `default-canonical-metadata.yml`) are fully superseded by `cataloging.py`. The new tool does strictly more, with correct placement:

| | Old (`content-metadata*.py`) | New (`cataloging.py` / ADR-023) |
| --- | --- | --- |
| Sidecar location | `.{stem}.dc.yml` (pre-ADR-018) | `.{file}.assets/content/dc.yml` (ADR-018, ADR-025) |
| Frontmatter/cascade conflict | Richness heuristic (longest value wins) | Per-field cataloging policy (transcribed/supplied/noted), normative |
| Identity | None | `dc:identifier` + `sat:work`, write-once (ADR-021, ADR-022) |
| Fixity | None | Content and record digests (ADR-027) |
| Audit trail | None | Ingress record, origins + findings (ADR-023 §"Every field records its origin") |

There is no capability in the old tools that the new pipeline lacks. **Retired outright**: `content-metadata-ingress.py`, `content-metadata.py`, and `default-canonical-metadata.yml` have been deleted. This also resolves radar-1b items 2.1 (language 639-1 vs 639-2) and 2.7 (baked `dc:publisher` default) as a side effect — both defects lived only in the deleted files; the new architecture never had them (`language.py` already emits 639-2 forms, confirmed in `test_archive.py`; the instance-tier `dc.yml` has no baked publisher default, only an operator-stated tripwire).

#### 2. Nursery staging — retire the code, keep the concept on record

`content-ingress.py`'s actual job — hold arriving content in `nursery/` for review before an archive definition exists — is a real capability the new pipeline doesn't have. `content ingress` (the new tool) assumes the document already lives inside an established language archive; it has no answer for "I have a pile of files and haven't decided where they belong yet."

This is not a new gap. It already has a name on the record, twice:

- ADR-027 decision 2 assumes a `staging/` area exists ("uncataloged content in `staging/` is digested at first touch")
- `content-ingress-specification-v0.2.1.md` §14 lists it as a Non-Goal: "whether SAT adopts a formal pre-archive staging convention is a separate, undecided question"

**Retire the code, not the concept.** `content-ingress.py` and its readme are to be deleted; the nursery workflow it implements is superseded in intent by the `staging/` convention already referenced but never formally designed. A future ADR should design `staging/` properly — this ruling does not do that design, it just makes sure the nursery tool's retirement doesn't erase the requirement along with the code.

#### 3. Markdown normalization (flowmark) — same treatment

`content-ingress.py`'s second job, running `flowmark --auto` against the nursery copy, is also not replaced by anything in the new pipeline. `content ingress` reads and strips frontmatter; it does not normalize the prose body.

This too already has a name: *Complete Filesystem Cascade: Goals* (v0.2.0) lists, on the horizon and explicitly "recorded, not designed": *"Markdown document normalization — what 'well-formed SAT markdown' means at ingress."*

**Retire the code, keep the horizon item.** Whether normalization becomes a `content ingress` pipeline step or a separate deliberate tool, and whether `flowmark` remains the mechanism, is that future ADR's decision, not this ruling's. (ADR-030 has since taken this up.)

#### Out of scope for this ruling

`content-egress.py` and `en/bin/transmog/` were part of the same nursery/egress/transmog pipeline but were not directly examined here — their concern (platform-specific publishing output) already has a separate, more-current home in ADR-017's publishing-vector pattern (Hugo, on HOLD) and radar-005 (mkdocs-transmog), which is a different two-phase design (`hugo-transmog`/`hugo-assemble` under the `sat-tools` content tier) from the `en/bin/transmog/` implementation referenced in `content-pipeline.md`. Whether those are the same code or two competing transmog systems is worth a dedicated look before anything there gets deleted — flagged, not ruled on.

## Alternatives Considered

**Blanket frontmatter-wins** — rejected. It hands archive-structural fields to per-document claims: a stray `language:` key would contradict the filesystem, and `dc:type`/`dc:format` claims would override what tooling can verify by inspection.

**Blanket cascade-wins** — rejected. It discards the closest declaration for exactly the fields where the document knows best — its own title, creator, and subjects — forcing the operator to re-enter what the author already wrote.

**Blending or normalizing values ("convergence")** — rejected. Nothing is averaged or nudged toward agreement; every value arrives whole from exactly one owner, and disagreement survives on the record. Convergence invites the wrong mental model and was set aside as a name for the same reason.

**Importing identity from frontmatter** — rejected. Imported identity is how UUID collisions and silent joins arrive. Identity is minted by work assignment (ADR-022); residue is noted as evidence, never admitted.

**Replace semantics for `dc:subject`** — rejected. Subjects layer; replacement would make the cascade's subjects and the author's subjects mutually destructive, and catalogers' practice is additive. Union with deduplication keeps both, transcribed first.

**Discarding unrecognized frontmatter keys** — rejected. Silent data destruction; the noted origin exists precisely so nothing the author wrote is lost.

**quarantined as the third origin** — rejected in favour of *noted*, the tradition's own word for information recorded about an item without entering its description; *quarantined* is a contamination metaphor doing operational work.

**metadata intake as the process name** — retired before use in favour of *cataloging*, which names the actual practice being mechanized and imports a century of settled distinctions (transcribed/supplied) instead of inventing parallel ones.

## Consequences

- satlib gains `cataloging.py`: frontmatter reading and stripping, cascade preseed application, the cataloging policy, origin recording, and finding generation; `content ingress` is a thin caller
- The cataloging policy table above is normative; changing a row is an amendment to this ADR
- Every sidecar field's origin (transcribed, supplied, noted) is recorded in the ingress record; transcribed claims are preserved verbatim even when overridden
- Language disagreement produces a finding and a narrated report line, never a silent choice
- The stripped frontmatter block is preserved wholesale in the ingress record
- The standing `dc:subject` merge-versus-replace question is settled as union (transcribed first, deduplicated); the cascade documentation is updated to align
- No document sidecar ever carries `<calculated>`; an unresolvable field at cataloging time is a tripwire error
- The controlled vocabulary (v0.4.0) gains *metadata cataloging*, *cataloging policy*, *transcribed*, *supplied*, and *noted*; *quarantined* and *metadata intake* are recorded as rejected before use
- `content-metadata-ingress.py`, `content-metadata.py`, and `default-canonical-metadata.yml` are retired outright, fully superseded by `cataloging.py`, and have been deleted from the repository; radar-1b items 2.1 and 2.7 close as a consequence of the deletion, not a fix to the deleted file
- `content-ingress.py` (nursery staging) and its flowmark normalization step are retired as code but not yet deleted; both capabilities remain open requirements, already on record — `staging/` (ADR-024, ADR-027, content-ingress-specification §14) and markdown normalization (Complete Filesystem Cascade: Goals, horizon; taken up by ADR-030) — and await their own future ADRs rather than being silently dropped
- `content-pipeline.md` and the Layer 2 section of `sat-mvp-roadmap.md` need updating to mark the nursery/metadata stages retired rather than describing live tooling
- `content-egress.py` and `en/bin/transmog/`'s relationship to ADR-017/radar-005 is flagged as a follow-on question, not resolved here

## References

- ADR-001: Language as filesystem structure
- ADR-012: Conformant document schema
- ADR-017: Publishing-vector pattern (Hugo, on HOLD)
- ADR-018: Universal assets directory convention
- ADR-019: satlib as single source of truth with thin-tier CLIs
- ADR-020: Controlled vocabulary and creation-event terminology
- ADR-022: Work Assignment, Expression Joining, and the Work Index
- ADR-024: Discovery and reconciliation
- ADR-025: Role-named assets directories, sparse inheritance, and the resolution order
- ADR-027: Fixity
- ADR-030: Markdown normalization at content ingress
- Document Identity at Content Ingress: Goals (v0.3.1)
- Calculated metadata placeholder convention (v0.1.1)
- Complete Filesystem Cascade: Goals (v0.2.0)
- `content-ingress-specification-v0.2.1.md`
- `adr-022-session-close-out-review.md` — flagged item that opened this ruling
- radar-1b items 2.1, 2.7
- Svenonius, E. (2000). *The intellectual foundation of information organization*. MIT Press.

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
| 0.2.1 | Proposed | `dc:contributor` added to the cataloging policy table, closing radar-1b item 2.2: transcribed only, no cascade supply, omitted entirely (not an empty string) when absent — the one field with no fallback. Local `"Name (Organization)"` convention recorded for AI-assisted authorship as a formatting note, not a new mechanism. || 0.2.0 | Proposed | Amendment folded in: rules on the retire-vs-port action item opened at the 0.6.0 release (`adr-022-session-close-out-review.md`). New Decision subsection "Disposition of the pre-ADR-018 pipeline" added, closing five pre-ADR-018 artifacts split into three concerns — metadata generation retired outright and deleted (`content-metadata-ingress.py`, `content-metadata.py`, `default-canonical-metadata.yml`); nursery staging and markdown normalization retired as code (`content-ingress.py`, `content-ingress-readme.md`, not yet deleted) but preserved as already-recorded horizon items (`staging/`, per ADR-024/027; markdown normalization, per Complete Filesystem Cascade Goals, since taken up by ADR-030); `content-egress.py`/transmog's disposition flagged as a separate follow-on, not ruled on here. Consequences and References updated accordingly. |
| 0.1.0 | Proposed | Initial draft: cataloging as the process name with transcribed/supplied/noted origins, the normative cataloging policy table, language disagreement as finding, verbatim preservation rules, dc:subject settled as union, worked example |
