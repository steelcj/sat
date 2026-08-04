---
status: Accepted
date: 2026-07-14
version: 0.1.3
---

# ADR-027: Fixity

## Context

An archive that cannot notice damage is not preserving anything; it is hoping.

Fixity answers exactly one question: is this file, bit for bit, what it was when its digest was recorded? It overlaps in appearance with three neighbors and replaces none of them. Auditing and logging answer who changed something and when; fixity does not know. Version control keeps history and can restore; fixity keeps no history and restores nothing. Backup keeps copies; fixity keeps thirty-two bytes and an honest opinion. SAT needs the one question answered cheaply at archive scale; the neighbors remain the right tools for their own questions.

Digital preservation names the required practice *fixity*: record a checksum when content is known good, compare later, and treat disagreement as a finding.

SAT needs fixity for two reasons that turn out to share one mechanism: 

1. knowing when corruption has taken place.
2. Providing reconciliation (ADR-024) content-grade evidence that survives copies and cross-filesystem moves, which filesystem metadata does not provide.

The governing doctrine is the integration doctrine (controlled vocabulary, Gold):

> sidecars record, stdlib computes, standard formats export, proven tools verify.

Fixity is that doctrine's founding case, the design that produced it.

In particular: mature verification and transfer tooling already exists (rclone, coreutils `sha256sum`), and SAT integrates it as interchangeable companions rather than dependencies.

The recorded expectation lives in SAT's own sidecars where it participates in creating the canonical record.

The design key, imported from the tradition: a checksum detects change. Whether a change is damage depends entirely on what kind of file changed, which is why decision 1 sorts files into classes before assigning meaning to a mismatch.

## Decision

### 1. Three classes of file, three meanings of a mismatch

**Write-once records** — `identity.yml`, `provenance.yml`. These may never legitimately change, so a fixity mismatch is unambiguous: corruption or tampering, a hard finding (`record-corruption`). This is fixity's cleanest win.

**Cataloged content** — content that has been through ingress and carries its records, including this fixity record. Cataloging is the metadata step inside ingress (ADR-023); content on the far side of that step is cataloged content, and that is the term used throughout. Operators legitimately edit their documents, so a mismatch here means *modified since cataloging*: a soft finding (`content-modified`) whose remedy is re-cataloging, not alarm.

One honesty note belongs in the finding itself. Container formats such as `.docx`, `.xlsx`, and `.pptx` are rewritten by some applications without any content edit: whether a bare open triggers a rewrite varies by application and version, and SAT cannot know which application touched the file. The finding's plain-language line states exactly that general truth and no more, or the soft class erodes trust. Plain-text formats do not behave this way, which is one more quiet virtue of markdown-first archives.

**Operator settings** — `dc.yml` and its kin. Meant to be edited; no fixity is recorded, because any edit detection requires a recorded baseline, and a baseline on a file that is supposed to change is fixity crying wolf on every legitimate edit. What checking may do is report without judging: `--check` may list operator settings with their last-modified times as information only, never as findings. Change history for settings remains version control's job.

### 2. What is recorded, and where

Every role directory may carry one `fixity.yml`, under the generated-record contract. It attests the role's write-once records; at the content role it additionally attests the content itself. The children index attests existence, never integrity.

```yaml
# .my-collection.assets/collection/fixity.yml — written at creation, updated by deliberate operations
records:
  identity.yml:
    algorithm: sha256
    digest: "9f2b1c47a03d8e6b12f4c9a75e08d3b1a6c2f04e9d817b5a3c60e2f18b4d41ac"
  provenance.yml:
    algorithm: sha256
    digest: "3c7d8e21b4a9f0c6d5e2a17b8f4c0d9e6a3b2c15d8e7f4a09b6c3d2e1f0a08be"
recorded: "2026-07-14T18:40:00Z"
recorded_by:
  command: collection init
  version: "0.7.0"
```

```yaml
# .my-guide.md.assets/content/fixity.yml — the content role adds the content entry
records:
  identity.yml:
    algorithm: sha256
    digest: "77aa41c8f2b90d3e6a15c4b7d8e0f2a9c6b3d1e4f70a8c5d2b9e6f3a01c4b2e0"
content:
  algorithm: sha256
  digest: "9f2b1c47a03d8e6b12f4c9a75e08d3b1a6c2f04e9d817b5a3c60e2f18b4d41ac"
  size: 4183
recorded: "2026-07-14T18:41:12Z"
recorded_by:
  command: content ingress
  version: "0.7.0"
```

The algorithm is recorded per entry (standard preservation practice: algorithm agility without record migration). The default is sha256 — the lingua franca of rclone, coreutils, and preservation tooling, which is what makes decision 5 free.

Uncataloged content in `staging/` is digested at first touch, giving reconciliation its only evidence for identity-less files (ADR-024, evidence rank 4).

Write-once records are digested at creation into their role's `fixity.yml`. This placement was settled against three alternatives: sibling fixity files per record pay two extra files per role directory for nothing this shape lacks; the children index carrying child digests leaves the instance root unguarded (it has no parent) and, being derived and rebuildable, would let its own documented remedy re-attest corrupted records; a root ledger is a second source of truth. The role's own `fixity.yml` guards every tier including the root, adds zero new record classes, and is written only by deliberate acts, never regenerated from the tree.

Every in-tree guard shares one limit: whatever reaches the tree reaches the guard beside the guarded. The answer is separation, and decision 5's dated exports are the separation — a `SHA256SUMS` kept off the tree (version control, another machine, any proven keeper among equals) is the tamper check no in-tree record can be.

### 3. When digests are computed and updated

digests are computed and updated only:

* At ingress (content)
* At creation (records)
* During deliberate operations

The safe `mv` verb (ADR-024) updates paths and never digests — content did not change, and a digest that *did* change during a move is itself a finding.

Re-cataloging refreshes a document's digest as part of writing its records. Nothing updates a digest silently: every digest write is a narrated act by a named command, stamped in `recorded_by`.

Computation is `hashlib` from the standard library: no dependency is taken for three lines of code.

### 4. Checking is a deliberate act, and findings are classified

Not as in classified secret, as in broken down into classes...

There is no ambient (always running in the background) fixity daemon at this time.

Checking runs only when invoked — `collection fixity --check`, or as a validation mode — because active content goes fixity-stale constantly and an always-on alarm is an ignored alarm.

Findings speak the ADR-024 grammar as well as in the sat-controlled-vocabulary document (classified, what, means, evidence, do, severity), the classes are exactly the three meanings of decision 1 plus `staging-unmatched`, and checking never writes: the loop closes through the operator.

### 5. Verification and transfer belong to proven tools

SAT exports a derived checksum manifest in the universal format, from the sidecars, disposable like every derived record:

```bash
collection fixity --export > SHA256SUMS   # derived from sidecars; delete and regenerate at any time
sha256sum -c SHA256SUMS                   # coreutils verifies
rclone check --checkfile SHA256SUMS remote:backup/henson-catalog   # rclone verifies a transfer
```

Regenerate-compare-replace was considered for the manifest and declined, because it conflates two different questions. The manifest is a projection of the sidecars: comparing a new export against an old one detects sidecar drift across time, which is a real question but not `--check`'s question (sidecars against content, now). Operators who want point-in-time history keep dated exports (`SHA256SUMS-2026-07-14`) and compare them with `diff`; the manifest file itself stays disposable, like every derived record.

SAT remains the system of record; the verification engine is interchangeable:

* rclone where its remotes and transfer verification earn their place
* coreutils where nothing more is needed

SAT's own check where findings classification matters, rclone is documented as the first-class verification-and-transfer companion and is never a dependency.

The installer's pending tarball checksum verification (its ROADMAP) is this same principle at the acquisition boundary and is noted, not implemented, here.

### 6. Tree-level fixity is a door, not a room

Aggregate digests — a directory's fixity as a hash over its children's hashes, Merkle-style, are the natural extension for whole-tree verification and are deliberately not designed here.

The per-file records and the children index leave the aggregate a clean arrival path; it is recorded as future work so nobody reinvents it cold.

## Alternatives Considered

**rclone as a hard dependency and fixity engine** — rejected, on ownership rather than capability. Memory could be built by parsing and persisting rclone's output, but then SAT's canonical fixity record would depend on the output format of a tool SAT does not control, version to version. The recorded expectation must live in SAT's sidecars, written by SAT's own writer, to be part of the archive's canonical record; and taking a Go binary as a dependency to avoid three lines of `hashlib` inverts every cost. rclone's real strengths, remotes and transfer verification, are fully available through the exported manifest.

**Ambient fixity (watcher-driven continuous checking)** — rejected. Active content changes constantly; a permanent alarm is an ignored alarm. Deliberate checking with classified findings keeps the corruption signal trustworthy. The ADR-014 watcher may someday *schedule* checks; it never becomes their correctness basis. It is possible that a filesystem watcher could be added to the stack but this is not currently on our ROADMAP.

**Fixity on operator settings** — rejected. Every legitimate edit would fire a finding; the class exists to be edited. Change history for settings is version control's job, not fixity's.

**git as the fixity mechanism** — rejected as the general answer. Instances are not required to be repositories, extracted trees must stay sovereign without git history, and git's object hashes attest to commits, not to the working tree an operator actually reads. Where an instance *is* a repository, git is a fine additional verifier — a proven tool consuming the same tree.

**Stronger or multiple algorithms by default** — rejected for now. sha256 is sufficient for integrity (the threat is rot and accident, not adversarial collision against a personal archive), and it is the format every proven verifier speaks. The per-record `algorithm` field is the agility door if that judgment ever changes.

**No fixity for cataloged content (records only)** — rejected. The modified-since-cataloging signal is what makes re-cataloging triggerable rather than guessed, and content digests are reconciliation's evidence for everything identity does not yet cover.

## Consequences

- satlib gains the fixity machinery: digest at ingress and creation, `fixity.yml` writes under the generated-record contract, deliberate check with classified findings, manifest export
- `record-corruption` (hard), `content-modified` (soft, with the binary-format honesty line), and `staging-unmatched` join the findings classification set
- Reconciliation (ADR-024) receives its rank-4 evidence; staging content becomes reconcilable at digest grade
- `SHA256SUMS` export makes coreutils and rclone interchangeable verifiers; rclone is documented as the transfer companion, never required
- The safe `mv` verb's contract is sharpened: paths change, digests never do
- Every role directory may carry `fixity.yml` attesting its write-once records; the children index attests existence, never integrity; dated off-tree exports are the tamper story
- Tree-level aggregate fixity and the installer's tarball verification are recorded as doors
- The controlled vocabulary gains *fixity* and the three-class model

## References

- ADR-014: Filesystem event-driven tooling model
- ADR-018: Universal assets directory convention
- ADR-021: Stable identity at creation
- ADR-023: Metadata cataloging at content ingress (Proposed)
- ADR-024: Discovery and reconciliation
- SAT Controlled Vocabulary (Gold: the integration doctrine)
- PREMIS Editorial Committee. (2015). *PREMIS data dictionary for preservation metadata* (Version 3.0). Library of Congress. https://www.loc.gov/standards/premis/

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
| 0.1.3 | Accepted | Write-once digest placement settled: the role's own fixity.yml gains a records section attesting the role's identity and provenance records, with the content role additionally attesting the content; children-index digests rejected (unguarded root; a rebuildable guard whose remedy re-attests corruption), sibling files rejected (cost without benefit), root ledger rejected (second source of truth); the in-tree adjacency limit stated with dated off-tree exports as the separation |
| 0.1.2 | Proposed | Creators Notes resolved: fixity-versus-neighbors paragraph added (auditing, version control, backup each keep their own question); the design-key line rewritten as prose; cataloged content defined at first use with cataloging as the metadata step inside ingress; container-format rewrite honesty stated as the general truth (varies by application, SAT cannot know); operator settings gain information-only reporting, never findings; manifest disposability defended with dated exports as the history practice; rclone rejection restated on record ownership rather than capability; em-dash reduction pass |
| 0.1.1 | Proposed | Lots of edits and Creators notes for clarity and comprehension |
| 0.1.0 | Proposed | Initial draft: three-class model (write-once, cataloged content, operator settings), fixity.yml under the generated-record contract with per-entry algorithm, digests only at deliberate acts, deliberate checking with classified findings, manifest export for coreutils and rclone as interchangeable verifiers, tree-level fixity and installer tarball verification recorded as doors |
