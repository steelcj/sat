---
dc:title: "SAT Tooling Improvements — Plan for Next Session"
dc:description: "An executable, task-ordered plan of recommended changes to the SAT executables and their options, drawn from the 2026-08-11 ingress test. Written for a Claude Code session to pick up directly: each task carries its target files, rationale, and a verifiable acceptance check, ordered by dependency from data-safety through dispatcher integrity, configuration ergonomics, scope safety, adoption, and documentation."
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
  - tooling
  - CLI
  - roadmap
  - content ingress
  - preseed
dc:identifier: "sat-tooling-improvements-plan-2026-08-11"
---

# SAT Tooling Improvements — Plan for Next Session

Companion to `2026-08-11--18-10-13-session-002--sat-state--after-completion.md`. That document records what the ingress test found; this one turns the findings into an ordered set of changes to the SAT executables and their options, phrased so a Claude Code session can execute them one at a time.

## How to use this plan

Every task below is self-contained. Work them in phase order — a later phase assumes the earlier ones landed. Each task carries:

- **Change** — what to do, in one or two sentences.
- **Files** — the source paths to edit, relative to the repository root (`~/2-areas/development/sat/`). These are the source, not the installed artifact under `~/.local/share/sat-tool/`; the artifact is regenerated on release.
- **Why** — the finding it answers.
- **Accept** — a command or observable that confirms the task is done.

Line numbers are deliberately omitted; anchor on the named function or symbol, which survives edits. Tool version at time of writing is `0.8.0` (`cat VERSION`). Run the whole suite through the `sat`/`content`/`collection` dispatchers on `PATH`, not by calling the scripts directly, so the acceptance checks exercise the interface a user meets.

A scratch instance is the safe test bed for every behavioural task: `sat init /tmp/plan-check --language en-CA --language fr-CA`, exercise, then `rm -rf /tmp/plan-check`. Do not test against `~/2-areas/development/sat/ingress`; that instance is the egress fixture and should stay as ingested.

## Phase 0 — Correctness and data safety

These change what the tool does to a user's documents. They come first because every later phase assumes ingress behaves predictably.

### T01 — Decide and disclose the ingress source-rewrite

- **Change:** Decide if `content ingress` must move a document's YAML frontmatter into `content/dc.yml`. If the tool must move it, name this action in the `--dry-run` plan. Show the plan line "will rewrite source: frontmatter → sidecar". Then add a `--keep-frontmatter` flag for callers who must keep the source unchanged. If the tool must not move it, stop the rewrite. Keep the frontmatter in the file. In both cases, change the `--help` text. The `--help` text now says that the tool does not do markdown normalization. This statement is wrong.
- **Files:**
  - `en/bin/content/content-ingress.py` — the `ingress_document` write path, the dry-run plan printer, and the argparse help block.
  - `en/lib/satlib/satlib/markdown.py` — the rewrite can be in this file.
- **Why:** The 30 documents in the test lost their frontmatter. The dry run gave no warning. The `--help` text says the opposite. This is the most important finding for egress.
- **Accept:** Make a scratch document that has frontmatter. Run `content ingress <doc> --dry-run`. The plan must name the source rewrite. If you choose the other option, the run keeps the file byte-for-byte the same. Then `content ingress --help` must agree with the real behavior.

### T02 — Honour a declared `sat:work` on ingress

- **Change:** When an arriving document's frontmatter already carries a `sat:work` (or `dc:identifier`), adopt it instead of minting a new one, or require an explicit `--mint-new` to override. Keep `--expression-of` for the join case.
- **Files:** `en/bin/content/content-ingress.py` (identity minting, `_mint_chain` / the call into `satlib.identity`); `en/lib/satlib/satlib/identity.py`.
- **Why:** `terms.md` declared `sat:work: …c58f2a09…`; ingress recorded `…8e591d00…`. A round trip (ingress → egress → re-ingress) cannot be identity-stable while declared identity is discarded silently.
- **Accept:** Ingressing a document that declares a `sat:work` records that same UUID in `identity.yml`, unless `--mint-new` is passed.

### T03 — Stop `dc:type` inheriting onto leaf documents

- **Change:** Make the document layer default `dc:type` to `Text` (or transcribe it from frontmatter) rather than inheriting `Collection` from the collection tier. `dc:type` should not cascade past the container that owns it.
- **Files:** `en/lib/satlib/satlib/cascade.py` (layer assembly) and `en/lib/satlib/satlib/cataloging.py` (the field-resolution policy and any hardcoded default).
- **Why:** Every ingested article was typed `dc:type: Collection`. That error will surface in whatever egress emits.
- **Accept:** A freshly ingested leaf `.md` with no `dc:type` in frontmatter resolves `dc:type: Text` in its `content/dc.yml`; a collection still resolves `Collection`.

## Phase 1 — Dispatcher integrity

Broken and silent routing. Fix these before adding options, so new options land on dispatchers that behave.

### T04 — Make `sat` reject unknown subcommands

- **Change:** The `sat` dispatcher falls through anything it does not recognise to `sat-init.py`, so `sat ingress` prints init help with no error. Add an explicit unknown-subcommand branch that prints a usage line and exits non-zero. Use `en/bin/content/content.py` as the model — it already does this correctly.
- **Files:** `en/bin/sat/sat`.
- **Why:** Silent fall-through misleads; a user typing a real-but-unrouted verb gets no signal.
- **Accept:** `sat bogus` exits non-zero with `usage: sat <init|licence|...>`, not `sat init` help.

### T05 — Repair or remove the dead `sat archive init` route

- **Change:** `sat archive init` execs `en/bin/sat/sat-archive-init.py`, which does not exist. Either point the route at the working `en/bin/archives/archive-init.py`, or remove the route and document `archive` as its own dispatcher (see T07).
- **Files:** `en/bin/sat/sat`; cross-check `en/bin/archives/archive` (the archive dispatcher) and `en/bin/archives/archive-init.py`.
- **Why:** The route advertises a capability that errors with a file-not-found.
- **Accept:** `sat archive init --help` either prints archive-init usage or a clean "not a sat subcommand" message — never a Python `No such file` traceback.

### T06 — Wire `collection` reconcile, fixity, and mv

- **Change:** The `collection` dispatcher routes only `init` and `work`, yet `collection-reconcile.py`, `collection-fixity.py`, and `collection-mv.py` ship beside them, fully argparse'd. Add routes for `reconcile`, `fixity`, and `mv`, and give the dispatcher an unknown-subcommand branch (it currently falls through to `collection-init.py --help`).
- **Files:** `en/bin/collection/collection`.
- **Why:** Three implemented operations are unreachable through the wrapped command; the command reference documents them only as direct script invocations.
- **Accept:** `collection fixity --check`, `collection reconcile`, and `collection mv --help` all reach their scripts; `collection bogus` exits non-zero with usage.

### T07 — Decide the status of `sat migrate`, `archive`, and `transmog`

- **Change:** `sat-migrate.py` exists but is unrouted by the `sat` dispatcher; `en/bin/archives/archive` and `en/bin/transmog/transmog.py` are not on `PATH` at all. For each, decide: wire and wrap it, or mark it internal and say so. If `transmog` is provisional (as the command reference states), keep it off `PATH` deliberately and note that in one place.
- **Files:** `en/bin/sat/sat`; the installer/wrapper generator (search the release scripts, e.g. `publish-release.py`, for where `sat` and `collection` wrappers are emitted); `en/bin/archives/archive`; `en/bin/transmog/transmog.py`.
- **Why:** The surface a user can reach and the surface that exists have drifted apart; each gap should be a decision, not an accident.
- **Accept:** A short matrix (in `ROADMAP.md` or the command reference) lists every tool and whether it is wrapped, script-only, or internal, and the dispatchers match it.

## Phase 2 — Configuration ergonomics (the preseed work)

### T08 — Add `--preseed PATH` to `sat init` and `collection init`

- **Change:** Add a `--preseed PATH` option that reads the instantiation preseed from any location, overriding the fixed `~/.config/sat/instantiate-preseed.yml`. Resolution precedence: `--preseed` flag, then `SAT_PRESEED` environment variable, then the default path, then absent. Have `read_preseed()` take the resolved path as a parameter instead of closing over the module constant.
- **Files:** `en/bin/sat/sat-init.py` (`PRESEED_PATH`, `read_preseed`, the argparse block); `en/bin/collection/collection-init.py` for the same flag; factor the resolver into `satlib` if both tiers share it.
- **Why:** A per-project preseed cannot be passed today; the only workaround is symlinking a file over the fixed path. Named this explicitly as the motivating example.
- **Accept:** `sat init /tmp/plan-check --language en-CA --preseed /tmp/my-preseed.yml` folds that file's `dc:creator`/`publisher`/`rights` into the instance `dc.yml`; `SAT_PRESEED=/tmp/my-preseed.yml sat init …` does the same; the flag wins over the env var when both are set.

### T09 — Announce the preseed source at run time

- **Change:** When a preseed supplies operator identity, print a one-line notice naming the file it came from ("identity from preseed: <path>"), and record the provenance of each resolved field (transcribed, preseed, or operator) in the instance provenance record. Absent a preseed, keep the existing `<calculated>` tripwire behaviour.
- **Files:** `en/bin/sat/sat-init.py` (the creation reporter and the provenance writer); `en/lib/satlib/satlib` provenance module.
- **Why:** The demo preseed baked "SAT Demo Presenter Chris" into records with no runtime signal; the fields looked resolved with no hint they came from a demo file.
- **Accept:** A run with a preseed present prints the source line; the instance `sat/provenance.yml` distinguishes preseed-supplied fields from tripwire-resolved ones.

### T10 — Ship `instantiate-preseed.yml.example` and align the names

- **Change:** Add an example file whose name matches what the code actually reads (`instantiate-preseed.yml.example`), carrying the keys `sat-init.py` consumes. Reconcile it with the existing `sat-preseed.yml.example` and `collection-preseed.yml.example`, which are differently named and easily mistaken for it.
- **Files:** `en/bin/sat/examples/`; the initialization guide's preseed section, which currently notes the missing example in prose.
- **Why:** No shipped example matches the read path; the mismatch has already caused confusion, flagged in the initialization guide itself.
- **Accept:** `en/bin/sat/examples/instantiate-preseed.yml.example` exists, its keys match `read_preseed`, and the guide references it instead of describing its absence.

## Phase 3 — Batch-scope safety

### T11 — Make `content ingress --archive <lang>` unambiguous

- **Change:** Resolve `--archive <lang>` against the enclosing collection first, not against a path relative to the current directory. If `<lang>` also names a directory relative to cwd, do not silently prefer it; warn, or require `--tree <path>` for arbitrary locations. Print the resolved absolute target before processing.
- **Files:** `en/bin/content/content-ingress.py` (`_discover_batch`).
- **Why:** Run from the instance root, `--archive en-CA` catalogued the instance's own archive and reported "0 processed, 1 skipped" against the wrong target; the collection archive holding twenty-four documents was never touched.
- **Accept:** From an instance root that has both `en-CA/` and `vishpala.com/en-CA/`, `content ingress --archive en-CA` either resolves to the intended collection archive or refuses with a message naming both candidates — never silently picks the nearer one.

### T12 — Give every batch run a scope header

- **Change:** Before processing, print a single header line: the resolved absolute scope path and the count of documents matched. Keep the per-document plan lines under `--dry-run`.
- **Files:** `en/bin/content/content-ingress.py` (`_run_batch`).
- **Why:** "24 documents processed" with no path is the only signal a run targeted what the caller meant; T11's silent mis-target would have been obvious with a scope header.
- **Accept:** `content ingress --tree <path> --dry-run` opens with `scope: <abs path> (N documents)`.

## Phase 4 — Instantiation footprint and adoption

### T13 — Make the example `test-collection` optional

- **Change:** Add a way to instantiate without the always-on example collection — a `--no-example-collection` flag, or honour a preseed `seed.example_collection: false`. Keep it on by default so a fresh install still self-tests.
- **Files:** `en/bin/sat/sat-init.py` (seeding path); `en/lib/satlib/satlib/seed.py`.
- **Why:** A purpose-built ingress instance carries `collections/test-collection/` it never asked for; only docs and samples toggle today.
- **Accept:** `sat init /tmp/plan-check --language en-CA --no-example-collection` produces no `collections/test-collection/`.

### T14 — First-class adoption of an existing directory

- **Change:** Provide a supported path to bring an existing populated directory under management as a collection archive, without the manual copy-and-rename this session used. Candidate shape: `collection init --adopt <src> --language <TAG>`, which stamps the collection and archive roles over (or beside) existing content and canonicalises the archive directory name. Reuse `content ingress --tree` for the cataloging step.
- **Files:** `en/bin/collection/collection-init.py`; `en/lib/satlib/satlib/create.py`; coordinate with `en/bin/archives/archive-init.py`, whose MVP `.language.yml` output is not the role sidecar the cascade reads.
- **Why:** The whole session's friction — canonical casing, fresh archives that do not adopt, an MVP archives tool that writes a non-SAT `.language.yml` and would clobber existing `index.md` — traces to there being no first-class "adopt this directory" operation.
- **Accept:** One command turns a directory of markdown into a catalogued collection archive inside an instance, with the `.<name>.assets/archive/` role sidecar present and `content ingress` succeeding against it.

### T15 — Make the casing error actionable

- **Change:** When a language tag is rejected for non-canonical casing (ADR-003), have the error suggest the canonical form and, where an existing lower-case directory is the source, point at the adoption path from T14.
- **Files:** wherever `sat init`/`collection init` validate `--language` (the language validation in `satlib`, `en/lib/satlib/satlib/language.py` or `iso639.py`).
- **Why:** `--language en-ca` fails with a correct but terse ADR-003 message; real Eleventy sites use lower-case directories, so this is the first wall every site adoption hits.
- **Accept:** `sat init /tmp/x --language en-ca` prints "did you mean en-CA?" and, when relevant, names the adopt flow.

## Phase 5 — Documentation alignment

### T16 — Reconcile the guides and command reference with 0.8.0

- **Change:** Fix the drift the test surfaced: `content` is on `PATH` in 0.8.0, so the `content()` helper in the test-instance guide is unnecessary and the "only `sat` and `collection` are wrapped" claim is wrong; note the dead `sat archive init` route (until T05 lands); resolve the dangling "Creators Note" stub in the test-instance guide.
- **Files:** `en/docs/guides/sat/setting-up-and-ingressing-a-test-instance-v0-1-1.md`; the SAT Command Reference; `en/docs/guides/sat/sat-initialization-guide.md`.
- **Why:** Following the guides verbatim produces unnecessary steps and, for `sat archive init`, a dead end.
- **Accept:** A reader can follow the test-instance guide top to bottom in 0.8.0 with no helper definition and no dead route, and the Creators Note either answers its question or is removed.

### T17 — Fold the tool matrix into ROADMAP.md

- **Change:** Record the T07 tool matrix (wrapped / script-only / internal) and link these tasks from `ROADMAP.md` so the next release cut can see the surface decisions in one place.
- **Files:** `ROADMAP.md`.
- **Why:** The near-term items already note the collection routing gap; the rest of the surface belongs beside it.
- **Accept:** `ROADMAP.md` lists the tool matrix and references this plan.

## Task summary

| ID | Phase | Task | Depends on |
| --- | --- | --- | --- |
| T01 | 0 | Decide and disclose the ingress source-rewrite | — |
| T02 | 0 | Honour a declared `sat:work` on ingress | — |
| T03 | 0 | Stop `dc:type` inheriting onto leaf documents | — |
| T04 | 1 | Make `sat` reject unknown subcommands | — |
| T05 | 1 | Repair or remove the dead `sat archive init` route | — |
| T06 | 1 | Wire `collection` reconcile, fixity, mv | — |
| T07 | 1 | Decide status of `sat migrate`, `archive`, `transmog` | T05 |
| T08 | 2 | Add `--preseed PATH` to `sat init` / `collection init` | — |
| T09 | 2 | Announce the preseed source at run time | T08 |
| T10 | 2 | Ship `instantiate-preseed.yml.example` | T08 |
| T11 | 3 | Make `--archive <lang>` unambiguous | — |
| T12 | 3 | Give every batch run a scope header | — |
| T13 | 4 | Make the example `test-collection` optional | — |
| T14 | 4 | First-class adoption of an existing directory | T06 |
| T15 | 4 | Make the casing error actionable | T14 |
| T16 | 5 | Reconcile guides and command reference with 0.8.0 | T05 |
| T17 | 5 | Fold the tool matrix into ROADMAP.md | T07 |

Suggested order of work: T04, T05, T06 first — small, contained dispatcher fixes that make the rest testable — then the Phase 0 behavioural trio (T01–T03), then T08–T10, T11–T12, and the adoption arc T14/T15 last, as it is the largest and depends on the dispatcher and routing work.

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.0 | Final | First version. Seventeen tasks in six phases, derived from the 2026-08-11 ingress test, each with target files and an acceptance check, ordered by dependency. |

## Licence

Copyright (C) 2026 Christopher Steel

This file is part of SAT (Source Archive Tools).

SAT is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

SAT is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with SAT. If not, see <https://www.gnu.org/licenses/>.

This document was prepared with AI assistance from **Claude (Anthropic)**.
