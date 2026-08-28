Good steer — I'll write it as an executable work plan a Claude Code session can pick up directly: discrete tasks, real file paths, rationale, and verifiable acceptance checks, ordered by dependency. First let me confirm the source tree layout so every path in the plan is correct for the repo the next session will edit (not the read-only installed artifact):

All source paths confirmed. Writing the plan as an executable, Claude-CLI-ready work plan:

Plan written:

**[2026-08-11--18-19-29-session-002--sat-tooling-improvements--plan.md](https://claude.ai/home/initial/2-areas/development/sat/en/docs/process/sessions/2026-08-11--18-19-29-session-002--sat-tooling-improvements--plan.md)**

It's built to be executable by a Claude Code session, not just read. Every path was verified against the source repo (not the read-only installed artifact), so the next session can edit directly.

**Structure — 17 tasks, 6 phases, ordered by dependency:**

| Phase                           | Focus                                                        | Tasks   |
| ------------------------------- | ------------------------------------------------------------ | ------- |
| **0** Correctness / data safety | the ingress source-rewrite, declared `sat:work`, `dc:type` on leaves | T01–T03 |
| **1** Dispatcher integrity      | silent fall-through, dead `archive init` route, unwired `collection` verbs, tool status | T04–T07 |
| **2** Config ergonomics         | **`--preseed PATH`** + `SAT_PRESEED`, run-time preseed notice, matching example file | T08–T10 |
| **3** Batch-scope safety        | unambiguous `--archive`, scope header on every run           | T11–T12 |
| **4** Footprint / adoption      | optional example collection, first-class directory adoption, actionable casing error | T13–T15 |
| **5** Docs                      | reconcile guides/command-ref with 0.8.0, tool matrix into ROADMAP | T16–T17 |

**Claude-CLI-compatible touches:**

- Each task = **Change / Files / Why / Accept**, where *Accept* is a runnable command or observable — so a session knows when it's done.
- Anchored on function/symbol names, not line numbers (which drift).
- A **task summary table** with explicit `Depends on`, plus a suggested work order (small dispatcher fixes T04–T06 first to make everything else testable).
- A safety note pinning tests to a `/tmp/plan-check` scratch instance and keeping `~/…/sat/ingress` untouched as the egress fixture.

Your `--preseed` example is **T08**, written with full precedence (`--preseed` flag → `SAT_PRESEED` env → default path → absent) and a paired task (T10) to ship the matching `instantiate-preseed.yml.example`, since the current examples are misnamed relative to what the code reads.

Two judgment calls I'd flag for you: **T01** (the frontmatter rewrite) and **T14** (first-class adoption) are the two biggest — T01 because it's a semantic decision only you can make (intended sidecar model vs. defect), and T14 because it's the largest build and the thing that would've made this whole session a one-liner. Both are called out as such in the doc.