---
status: Proposed
date: 2026-07-31
version: 0.1.0
---

# ADR-030: Markdown Normalization at Content Ingress

**Numbering note:** provisional, same caveat as ADR-029 — confirm
against `ls en/docs/architecture/adrs/` before filing.

## Context

*Complete Filesystem Cascade: Goals* (v0.3.0) names this on the horizon,
explicitly "recorded, not designed": *"Markdown document normalization
— what 'well-formed SAT markdown' means at ingress."* The mechanism
question is no longer open — the radar bake-off settled it on
2026-05-31: `mdformat` is Adopted (`adopt/markdown/`), `flowmark` sits
in Assess, `goldmark` merged and moved to Hold. What remains is the
design question this ADR answers: how does the adopted tool actually
fit into `content ingress`'s pipeline, and what does "well-formed"
mean in checkable terms.

mdformat's own radar entry is explicit about its limits: it *"enforces
a canonical form but emits no per-rule findings, and it will not
enforce non-CommonMark house rules such as 'no horizontal rules in
content' or 'every fenced block carries a language identifier.'
Those remain the job of a separate validator."* That validator was
adopted in the same decision, in principle, but never built. This ADR
also gives it a shape.

## Decision

### 1. Normalization runs after the frontmatter strip, before fixity

Content ingress's existing pipeline (`content-ingress-
specification-v0.2.1.md` §4) strips frontmatter at step 9 and records
fixity at step 10. Normalization inserts as step 9.5: mdformat runs
against the prose body only, after frontmatter has already been
separated into `content/dc.yml`. This ordering does two things at
once. It means mdformat never has to see or preserve frontmatter —
sidestepping mdformat's own documented risk of escaping angle-bracket
placeholders in template-like content, since none is present in the
file by the time mdformat touches it. And it means fixity attests the
document's true final state: frontmatter stripped and body
normalized, not an intermediate form that would immediately register
as `content-modified` the next time anyone checks.

### 2. Normalization is mandatory by default, cascaded per tier — not a CLI flag

`sat:normalize_markdown: true` joins the settings a `dc.yml` layer can
carry, resolved through the exact cascade mechanism already built
(ADR-025 §7): sparse, deepest-stated-value-wins, no new machinery. An
archive holding content that must stay byte-for-byte as authored (a
verbatim historical corpus, for instance) sets `sat:normalize_markdown:
false` once, at whatever tier owns that decision, and every document
under it inherits the opt-out. No flag is added to `content ingress`
itself — the setting already answers the question a flag would.

### 3. Normalization participates in the existing dry-run-by-default plan

No new safety mechanism is needed. `content ingress`'s PLAN output
(§3.1) already narrates a line per file operation; normalization adds
one, using `mdformat --check` during planning (non-mutating) and
`mdformat` in place during `--apply`:

```
PLAN: ingress fr/produits/guide-rasoir.md
  fr/produits/guide-rasoir.md   strip frontmatter (11 lines removed)
                                 normalize with mdformat (4 lines would change)
  content/dc.yml         write descriptive sidecar (6 fields resolved)
  ...
```

If `sat:normalize_markdown` resolves to `false` for this document, the
line is omitted entirely rather than shown as skipped — consistent
with sparse inheritance meaning "this tier decided differently," not
"an exception was made."

### 4. "Well-formed SAT markdown" is defined as: mdformat-canonical, plus three house-rule checks

This answers the horizon item's actual question. A document is
well-formed when mdformat's canonical form produces no further changes
(mechanical: whitespace, blank lines, heading style, list markers,
code fence style, line endings) **and** it passes:

| Rule | Source | Check |
| --- | --- | --- |
| No horizontal rules in content | mdformat radar entry; `markdown--no-horizontal-rules-v0-3-1.md` | No `---`/`***`/`___` rule lines outside the frontmatter delimiters |
| Every fenced code block carries a language identifier | mdformat radar entry | No ` ``` ` fence opens without a following language tag |
| No heading level skips (H1 → H3 without an H2) | `content-egress.py`'s `normalize_heading_hierarchy`, prior art from the retired nursery pipeline | Sequential heading levels only |

The third rule wasn't in mdformat's original two-rule pairing note, but
it's tested, working logic that already exists in a file whose
retirement is pending (`adr-023-amendment-...md`, flagged not ruled).
Reusing the *rule*, not the code, avoids losing something real to a
cleanup that was never about this decision.

### 5. The validator is a satlib function, called by both content ingress and the future `sat validate`

`satlib.markdown.check_house_rules(text) -> list[Finding]` — pure
Python, stdlib `re`, no new dependency (consistent with the project's
own doctrine: *"sidecars record, stdlib computes, standard formats
export, proven tools verify"* — mdformat is the proven tool for
normalization; three line-pattern checks don't need one). `content
ingress` calls it after normalization and records violations as
non-fatal findings in the ingress record, same grammar as the
language-disagreement finding (ADR-023 §7.2) — narrated, not blocking.
Cataloging's job is identity and metadata; prose-quality issues need
author attention, not a refused ingest. The same function becomes
`sat validate`'s markdown check when that tool is rebuilt, so the rule
is defined once and enforced twice: at arrival and on demand.

### 6. mdformat absence is a fatal, explicit error

Matching the old `content-ingress.py`'s pattern for flowmark (worth
keeping even though the file itself is retired): if `mdformat` is not
on PATH, `content ingress` fails explicitly with an install command,
never silently skips normalization.

## Alternatives Considered

**A `--normalize` CLI flag instead of a cascaded setting** — rejected.
It would let normalization be silently forgotten per-invocation, where
a tier-level setting is stated once, visible in a sparse `dc.yml`, and
impossible to forget for everything beneath it.

**Running mdformat before frontmatter is stripped** — rejected. mdformat
would then have to parse and preserve frontmatter it has no
documented obligation to leave untouched, reintroducing exactly the
placeholder-escaping risk its own radar entry warns about, for no
benefit.

**Folding the house-rule checks into `cataloging.py` directly rather
than a separate `satlib.markdown` module** — rejected. The checks need
to be callable by `sat validate` independent of a full ingest run;
housing them where only cataloging can reach them would mean
duplicating the logic when validate is rebuilt, the exact drift class
this codebase consistently designs against.

**Treating a house-rule violation as fatal, refusing ingest** — rejected.
Identity and cataloging are the parts of ingress that must not proceed
on bad input (per ADR-023's tripwire discipline); a horizontal rule or
an untagged fence is an authoring quality issue, not a structural one,
and blocking ingest over it would make cataloging a de facto style
gate it was never designed to be.

## Consequences

- `content-ingress-specification-v0.2.1.md` needs a companion amendment:
  pipeline step 9.5, the PLAN line format, the `sat:normalize_markdown`
  cascade field, and the mdformat-absence failure mode
- satlib gains `markdown.py` (or a similarly named module): mdformat
  subprocess invocation (check and apply modes) and
  `check_house_rules()`, both stdlib-only beyond the mdformat call
  itself
- The three-rule table becomes the operational definition of
  "well-formed SAT markdown," closing the horizon item
- `content-egress.py`'s heading-hierarchy logic is credited and its
  rule reused; the file's own retirement disposition is still open
  from the ADR-023 amendment and is not decided here
- `sat validate`, when rebuilt, gains a markdown conformance check for
  free — same function, no new design work at that point

## References

- ADR-014: Filesystem-event-driven tooling model
- ADR-023: Metadata cataloging at content ingress
- ADR-025: Role-named assets directories, sparse inheritance, and the resolution order (v0.2.1)
- Complete Filesystem Cascade: Goals (v0.3.0) — the horizon item this ADR closes
- `content-ingress-specification-v0.2.1.md`
- `adr-023-amendment-nursery-pipeline-disposition.md` — content-egress.py's still-open retirement
- `uc-radar/en/docs/radar/adopt/markdown/mdformat--commonmark-compliant-markdown-formatter.md`
- `en/docs/automa/markdown/defaults/markdown--no-horizontal-rules-v0-3-1.md`

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
| 0.1.0 | Proposed | Initial draft. Places mdformat as pipeline step 9.5 (after frontmatter strip, before fixity); decides normalization is a cascaded sat:normalize_markdown setting, not a flag; defines well-formed SAT markdown as mdformat-canonical plus three house-rule checks (borrowing the heading-hierarchy rule from the still-unretired content-egress.py); houses the validator as a satlib function shared by content ingress and the future sat validate. |
