---
dc:title: "SAT State — End of Session, 2026-08-04"
dc:description: "End-of-session state of the sat-mapping working tree: what the docs-only reconciliation pass changed, what was verified against satlib, what remains open, and where the next session should start."
dc:creator: "Christopher Steel"
dc:contributor: "Claude Opus 5 (Anthropic)"
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
  - session state
  - reconciliation
  - ADR-034
  - configuration mapping
dc:identifier: "sat-state-2026-08-04"
---

# SAT State — End of Session, 2026-08-04

Session scope: execute `.claude/sat-mapping-make-it-so-handoff.md` — a documentation-only reconciliation of `docs/design/` against the ADR corpus, plus the minting of ADR-034. Work extended past the handoff at the project owner's direction: git history, a published design page, a verification of the docs against `satlib`, an initialization guide, and a root `VERSION` file.

## Repository state

The working tree is a git repository as of this session; it was not one before. Thirteen commits, working tree clean, 151 tracked files.

```text
67ab4b6 chore: add root VERSION file declaring 0.7.0
3aa7d9a docs: add the SAT initialization guide
68b24e0 docs: distinguish proposed floor layers from implemented cascade (T9)
1f20122 docs: add the reconciled configuration design page (session artifact)
2abcfda docs: verification pass and supersession banners for prior artifacts (T8)
4955a28 docs: add ADR cross-references to the goals document (T7)
2713cd7 docs: reconcile current-state mapping documents against ADR corpus (T6)
3e0fdc2 docs: reconcile target layout against ADR corpus (T5)
435cccd docs: reconcile payload maps against ADR corpus (T4)
092605f docs: reconcile definitions-and-vocabulary against ADR corpus (T3)
a800699 docs: mark the pre-corpus recommendation superseded (T2)
e8b5706 docs: mint ADR-034 (Proposed)
b7dfe94 chore: initial commit of the sat-mapping tree (pre-reconciliation baseline)
```

The baseline commit carries the design corpus at its pre-pass state, recovered from `en/docs.zip`, which proved to be a pristine snapshot — every design document matched its pre-pass byte size exactly. The per-task commits therefore carry real diffs rather than whole-file additions, and T1 records as a `git mv` from the draft filename.

`.gitignore` excludes `en.zip` and `en/docs.zip` (snapshot archives of the tracked tree), `en/lib/satlib/.venv`, `__pycache__`/`*.pyc`, and local editor state. Without those exclusions the baseline would have been 2,407 files instead of 148.

## What the reconciliation changed

ADR-034 is minted at `en/docs/architecture/adrs/adr-034-operator-side-concern-parents-and-the-derived-mapping-projection-v0-1-0.md`, `status: Proposed`, version 0.1.0. It was already present as a draft; the session renamed it to the corpus convention and verified its header.

Every design document now agrees with the corpus on four points: assets directories are per-entity (`.<name>.assets`, inside a directory and beside a file); media live inside the file's assets directory rather than as dot-file siblings; *sidecar* means only the egress/transmog output type; and *co-located*, *nested*, *twinned*, and *detached* are retired as topology terms, surviving only in explicitly flagged historical notes.

Supersession banners were added to `sat-configuration-paths-and-files-mapping-recommendation.md` (the pre-corpus draft ADR-034's Context cites) and to all four documents under `docs/design/artifacts/`. The artifacts were outside the handoff's task list but inside its verification grep; the parallel-assets artifact needed a banner most, since it recommends *twinned assets* as the house term and defines sidecar as a co-located file.

Verification passes: retired terms appear only in historical framing, every `.sat.assets` attaches to an entity literally named `sat`, no dot-file media siblings remain in live documents, and all fifteen ADR link targets resolve with 034 as the ceiling.

## What verification against satlib found

The reconciliation was documentation-only, but two claims in it were checked against the code afterwards. One held and one did not.

The preseed correction holds. `instantiate-preseed.yml` has exactly one reader, `en/bin/sat/sat-init.py`, whose docstring states the rule directly: below the instance there is no preseed, the cascade is the preseed. `satlib/cascade.py` contains no reference to preseeds or `.meta`, and nothing anywhere reads `sat-meta.yml`. The `preseed` parameter in `cataloging.apply_cataloging_policy` is a name collision — its docstring identifies it as the resolved cascade record from `resolve_entity`.

The nine-layer walk is not implemented. `cascade.layers_for` builds ADR-025 §7's five operator tiers and nothing else. No code reads `defaults/<tier>/metadata/dc.yml`, `sat:metadata_schema` has no reader, and the only `defaults/` file consumed anywhere is `defaults/content/markdown.yml`, read by `satlib.markdown` for normalization toggles rather than as a metadata layer. T6 had written the nine layers into three current-state documents as present-tense behaviour, following the handoff's own instruction; T9 corrected this by keeping the structure and marking the floor rows as proposed.

The general lesson for the next pass: the handoff assumed the ADR corpus describes current behaviour. It does not uniformly. ADR-018, ADR-021, ADR-024, and ADR-026 are Accepted; ADR-025, ADR-028, ADR-032, and ADR-034 are Proposed. ADR-025 is Proposed but implemented, and ADR-032 is Proposed and not implemented, so status alone does not predict what runs.

## Deliverables beyond the handoff

A design page renders the reconciled state as a self-contained HTML document at `en/docs/process/sessions/2026-08-04--12-41-56--sat-configuration-design.html`, also published as a private artifact at `https://claude.ai/code/artifact/a23d47b4-223a-43cc-8b5a-5ce012dbd782`. It is derived from the reconciled documents and authoritative over nothing.

An initialization guide at `en/docs/guides/sat/sat-initialization-guide.md` documents `sat init`. Its procedure sections were executed against a scratch instance rather than illustrated: the dry run, the creation run, the re-run refusal, and the resulting record tree are captured output. Three troubleshooting entries are reproduced failures with real output; the registry-unavailable entry is derived from source and labelled unreproduced in place.

A root `VERSION` file declares `0.7.0`, chosen by the project owner from three conflicting candidates. Verified: `sat init --version` prints `sat-tools 0.7.0`, and a scratch instance created afterwards records `tool_version: 0.7.0`.

## Open items

The root `.venv` does not exist. `en/bin/sat/sat` hardcodes `$SAT_ROOT/.venv/bin/python3` and fails with exit 127 before doing anything; the only virtual environment in the tree is `en/lib/satlib/.venv`, which the dispatcher does not fall back to. Every command captured in the initialization guide was run by invoking `sat-init.py` through satlib's environment directly. Creating the root environment was started this session and deliberately stopped; it remains the first thing to do before the CLI is usable as documented.

No `instantiate-preseed.yml.example` ships. The examples directory carries `sat-preseed.yml.example` and `collection-preseed.yml.example`, which are different files serving different purposes. The initialization guide's preseed key list is read from `sat-init.py` rather than from a template.

`--offline-confirm` does not currently permit an offline run. With no registry cache the flag routes to a code path returning no registry content, and `sat init` then reports that unvalidated operation is not supported and exits 1. A working cache or reachable network is a hard requirement today. This was read from source, not reproduced.

ADR-034 remains Proposed. Its consequences commit two pieces of follow-on work not performed here: `sat config map` as a read-only derived projection, and converting `cataloging.py`'s hardcoded Dublin Core assumption into a value read from `sat:metadata_schema`.

Provenance records written before the `VERSION` file existed carry `tool_version: unknown` permanently, since provenance is write-once. Nothing in this repository is affected — the only instances created were scratch instances, since removed — but instances initialized elsewhere from this checkout are.

`en/docs/process/sessions/session-001.md` appeared in the tree mid-session and is transcript text from the chat that produced the handoff. It is committed in the baseline; remove it if that was not intended.

## Where to start next

Create the root virtual environment with `satlib` installed, then re-run the initialization guide end to end through the `sat` dispatcher rather than through `sat-init.py`. That both unblocks the CLI and verifies the guide against the interface it documents.

After that, the substantive decision is whether ADR-025, ADR-028, ADR-032, and ADR-034 move to Accepted. ADR-034's Consequences enumerate the docs/design reconciliation items, and those are now complete.

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.0 | Final | End-of-session state for 2026-08-04. Records the T1–T9 reconciliation, the satlib verification and its one correction, deliverables beyond the handoff, and six open items. |

## Licence

Copyright (C) 2026 Christopher Steel

This file is part of SAT (Source Archive Tools).

SAT is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

SAT is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with SAT. If not, see <https://www.gnu.org/licenses/>.

This document was prepared with AI assistance from **Claude (Anthropic)**.
