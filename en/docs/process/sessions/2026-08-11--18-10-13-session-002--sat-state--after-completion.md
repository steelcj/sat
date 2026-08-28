---
dc:title: "SAT State — End of Session, 2026-08-11"
dc:description: "End-of-session state after a real-world ingress test: a SAT instance and vishpala.com collection stood up inside the sat working tree, thirty documents catalogued with content ingress, and the anomalies that surfaced — the source-rewrite on ingress foremost — recorded for the egress work that follows."
dc:creator: "Christopher Steel"
dc:contributor: "Claude Opus 4.8 (Anthropic)"
dc:publisher: "Christopher Steel"
dc:date: "2026-08-11"
dc:modified: "2026-08-11"
dc:type: "Text"
dc:format: "text/markdown"
dc:language: "en"
dc:language_bcp47: "en"
dc:rights: "https://creativecommons.org/licenses/by-sa/4.0/"
dc:subject:
  - SAT
  - session state
  - content ingress
  - vishpala.com
  - cataloging
  - egress
dc:identifier: "sat-state-2026-08-11"
---

# SAT State — End of Session, 2026-08-11

Session scope: bring a directory of real-world content under SAT management end to end, to exercise `content ingress` against something other than seeded samples and to stage that content for the egress process still to be designed. The work stood up a fresh instance and a `vishpala.com` collection, copied in thirty documents from a live Eleventy site, and catalogued them. The tool is `sat-tools 0.8.0`. No egress was attempted; the session's product is a populated instance and the record of what ingress did to it.

## Instance and repository state

The instance lives at `~/2-areas/development/sat/ingress`, inside this working tree rather than beside it. Its name is `ingress`, its root carries both the `sat` and `collection` roles, and the three operator-identity fields were resolved by hand at `.ingress.assets/sat/dc.yml` to test values: creator `Christopher Steel`, publisher `vishpala.com`, rights `© 2026 vishpala.com. All rights reserved.` These are placeholders chosen to let ingress proceed, not attribution to stand behind.

The `vishpala.com` collection sits directly under the instance and holds two language archives. `en-CA` carries twenty-four documents across `blog/`, `foundations/`, and `legal/`; `fr-CA` carries six across `blogue/` and `mentions-legales/`. The French side is a partial translation — it has no `foundations` counterpart — which is a property of the source, not a fault of the tooling.

The content was copied, not moved, from the live site at `~/2-areas/development/sites/site-blankstudio.com/branding/vishpala.com/src/content/{en-ca,fr-ca}/`, where the archive directories are lower-case in the Eleventy convention. vishpala.com is a branding applied to the blankstudio.com template; the live site was not touched.

The instance is untracked. `git status` reports one entry, `ingress/`, and `git check-ignore` does not match it, so the whole test instance — records and copied content alike — would be committed by a bare `git add`. Whether a test instance belongs in this repository is an open decision recorded below.

The demo instantiation preseed was moved aside to `~/.config/sat/instantiate-preseed.yml.demo-backup` before `sat init`, so the instance came up with `<calculated>` tripwires rather than the preseed's demo identity. It has not been restored.

## What the session built

Three commands did the structural work: `sat init ~/2-areas/development/sat/ingress --language en-CA --language fr-CA` for the instance, `collection init …/ingress/vishpala.com --language en-CA --language fr-CA` for the collection, then `content ingress --tree <archive> ` once per archive. Both ingress runs reported every document processed and none skipped — twenty-four and six, zero failures.

Each document gained a content sidecar beside it: `identity.yml`, `dc.yml`, `provenance.yml`, `fixity.yml`, and a timestamped ingress record under `content/ingress/`. The section directories were catalogued too, so the sidecar count runs three and two above the document counts — twenty-seven under `en-CA`, eight under `fr-CA`. The cascade carried the instance identity into every record; a spot check of `en-CA/legal/terms.md` shows `dc:creator: Christopher Steel` and `dc:publisher: vishpala.com`, and the French records resolve `dc:language: fra` against `dc:language_bcp47: fr-CA`.

## What ingress did to the source documents

Two behaviours were checked against the ingested tree afterward. Both matter for egress, and neither is announced by the tool.

Ingress rewrote every source `.md`. All thirty documents lost their YAML frontmatter, which moved into `content/dc.yml`; the live originals still carry theirs, so it is the copies under management that were altered. The `--dry-run` plan disclosed only the sidecars it would write, never that it would modify the document, and the behaviour contradicts the tool's own help, which states that markdown normalization is deliberately not implemented in this increment. Stripping frontmatter is normalization by any plain reading. The consequence for the next phase is direct: the archived documents are now bare bodies, and egress must reconstruct frontmatter from the sidecar for any renderer that expects it.

Ingress did not honour an identity a document already declared. `en-CA/legal/terms.md` arrived with `sat:work: urn:uuid:c58f2a09…` in its frontmatter; the minted `identity.yml` records a different `sat:work: urn:uuid:8e591d00…`. Absent `--expression-of`, ingress mints fresh identity and the declared work is discarded silently. For any round trip — ingress, egress, re-ingress — this is an identity-stability hazard.

## Anomalies encountered

Beyond the two source-rewrite findings above, the session recorded the following. They are grouped by how much they change outcomes rather than by where they live.

Metadata and setup friction. `dc:type: Collection` cascades onto leaf documents — every article is typed a collection, which is wrong at the document layer and will propagate into whatever egress emits. Canonical casing is mandatory: `sat init --language en-ca` is rejected under ADR-003, which forces the copy-and-rename from the site's lower-case `en-ca`/`fr-ca` to `en-CA`/`fr-CA`. The instantiation preseed is read only from the fixed `~/.config/sat/instantiate-preseed.yml`; 0.8.0 exposes no path argument, so a per-project preseed needs a symlink.

Discoverability and documentation. `sat ingress` prints `sat init` help with no error — the dispatcher falls through unknown subcommands silently, and the tool is `content ingress`. `sat archive init` is a dead route: it targets a `sat-archive-init.py` that does not exist, while the working archive tool is `en/bin/archives/archive-init.py`. With the demo preseed in place, `sat init` bakes operator identity from it with no runtime signal that the tripwires were satisfied from a demo file. `sat init` always seeds an example `test-collection` and documentation into a purpose-built instance; only the docs and samples toggle through the preseed's `seed:` keys, never the example collection. The guides and the command reference say `content` is not on `PATH`, but in 0.8.0 it is.

Batch-scope resolution. `content ingress --archive en-CA`, run from the instance root, resolved `en-CA` against the current directory and catalogued the instance's own archive rather than the collection's, reporting a confident "0 processed, 1 skipped" against the wrong target. The collection-root fallback only engages when the relative path does not exist, so a same-named archive nearer the working directory wins without warning. `--tree` with an absolute path was the reliable form and is what the run used.

The MVP archives tool is a trap for this workflow. `archive-init.py` writes a flat `.language.yml` carrying a bare language code, not the `.<name>.assets/archive/` role sidecar the cascade reads, and its dry run lists `create file` for `index.md` paths that already hold content. It scaffolds directories; it does not bring anything under SAT management, and it was not used for the real run.

## Open items

The source-rewrite behaviour needs a decision before egress is designed. If moving frontmatter into the sidecar is intended, the help text is wrong and the dry-run plan is incomplete; if it is not intended, it is a defect that alters every document it touches. Either way, egress has to know where the frontmatter is.

`dc:type` inheritance onto leaf documents should be settled the same way — whether the document layer defaults to `Text`, or the cascade stops carrying `dc:type` past the collection.

The `ingress/` instance is untracked and unignored inside this repository. Decide whether test instances belong here; if not, add `ingress/` to `.gitignore` or relocate the instance. Its provenance records were written under `tool_version: 0.8.0`, so they are internally consistent, but they are write-once and travel with the tree.

The declared-`sat:work` question is open: whether ingress should adopt an identity a document already carries, or continue to mint and require `--expression-of` to link.

The demo preseed remains parked at `~/.config/sat/instantiate-preseed.yml.demo-backup`. Restore it, delete it, or replace it with real operator identity before the next instantiation.

## Where to start next

Design the egress process against this instance. The first question it has to answer is frontmatter reconstruction: given a bare `.md` and its `content/dc.yml`, produce a document a target renderer accepts, and decide which `dc:` fields become frontmatter and in what form. The `vishpala.com` collection is a fair test because it is bilingual, asymmetric across languages, and carries the `dc:type: Collection` artefact that egress will either surface or correct.

Once egress round-trips one archive to a test site, re-ingress the result and compare identities. That closes the loop on the declared-`sat:work` question and shows whether the pipeline is stable under repetition.

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.0 | Final | End-of-session state for 2026-08-11. Records the instance and `vishpala.com` collection built under `~/2-areas/development/sat/ingress`, the thirty-document ingress, the source-rewrite and identity findings, and the anomaly catalogue carried forward as open items for egress. |

## Licence

Copyright (C) 2026 Christopher Steel

This file is part of SAT (Source Archive Tools).

SAT is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

SAT is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with SAT. If not, see <https://www.gnu.org/licenses/>.

This document was prepared with AI assistance from **Claude (Anthropic)**.
