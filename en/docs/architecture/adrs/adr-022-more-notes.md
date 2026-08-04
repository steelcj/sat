# ADR-022-more-notes

What do you think, do you want to handle transforming ADR-021 into code or should we create a handoff file for the claude cli?

Small correction first: ADR-021 is already code — shipped and verified in 0.5.0. You mean **ADR-022**, and my answer is: both, in the same sequence that worked last time. I build and test it here against the tree, then produce a handoff carrying tested files rather than instructions to write code. The handoff session reconciles against your real tree instead of implementing from prose — that division is what made the ADR-021 round land cleanly.

What I'd build here:

**satlib `work.py`** — the whole mechanism layer: work assignment (fresh `sat:work` via the existing `identity` module), the join operation (rewrite `sat:work`, append the structured `sat:work_retired` entry), the three-address-form resolver (file path → sidecar; `dc:identifier` → index; work UUID → direct), index build-from-sidecars, incremental update, read, and rebuild-and-compare — plus the generated-record-header writer, which belongs in satlib as the single writer the convention requires.

**Tests** in the house style: assignment defaults, join semantics and retirement trail, one-expression-per-language enforcement, index rebuild equivalence (incremental result == full rebuild), staleness detection, address resolution, header shape.

**Deliberately thin or deferred**: the `bin/collection/` and `bin/content/` CLI wrappers sketched but left for the handoff session (they touch your dispatcher conventions and the tier-permission layout, which live in your tree, not mine); document-tier ingress itself (`content ingress` end-to-end) is the bigger beast and can be phase two — the work/join/index machinery stands alone and is testable without it.

One honest caveat: my tree is still pre-refactor 0.4.8, so as before I write against the post-ADR-020 names and the handoff carries a reconciliation note.

If that split suits you, I start with `work.py` and the index writer now.

## Round 1

The assets name keeps the full filename including extension: `.guide-rasoir.md.assets`. Test fix:155 passed — the 134 baseline plus 21 new. Wiring the package exports and packaging the handoff:Rolled. Three deliverables, all carrying source headers per the convention:

**`work.py`** — the complete ADR-022 mechanism layer: document identity (fresh-work default, declared-work option, re-mint refused), join with the structured retirement trail, three-form address resolution, and the full index lifecycle — rebuild-from-sidecars (enforcing one-expression-per-language by raising on duplicates), the single writer producing your exact generated record header, incremental update that falls back to full rebuild when the index is absent, and `compare_index` returning typed findings across six divergence kinds.

**`test_work.py`** — 21 tests, built on the henson-catalog en/fr fixture from the ADR's own example. The one worth reading first is the last: **move a file, `compare_index` reports stale-path, rebuild, clean** — the canonical/derived contract exercised end to end. Also verified: incremental result equals full rebuild after both ingress-shaped and join-shaped updates, the header's first line is the path comment, and `generated_by` round-trips as the command/version mapping. Suite green at 155 (134 + 21).

**The handoff** — four tasks: drop-in module, the `collection work` command family (join with the ADR's exact PLAN output, find, index --rebuild/--check), version-source wiring, and a smoke sequence whose transcript is a required deliverable. Reconciliation note covers the assets-naming assumption (`.{full-filename}.assets/`) with reconcile-toward-the-tree instructions. Deliberately out of scope: `content ingress` end-to-end (phase two), suggestion machinery, validation integration.

One design honesty note: `resolve_expression_of` scans sidecars rather than the index for identifier lookup — correct-by-construction since sidecars are canonical, at linear cost. The index-accelerated path is a one-line optimization the handoff session or phase two can add once the index is reliably present.

When the handoff lands, the remaining ADR-022 arc is: `content ingress` (phase two), the rebuilt sat-validate absorbing `compare_index` and the backfill, the 7th-grade ADR-022 twin — and eventually 0.6.0 carrying all of it.