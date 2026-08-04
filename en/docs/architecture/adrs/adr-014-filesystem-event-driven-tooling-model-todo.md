# ADR-014: Filesystem-Event-Driven Tooling Model

Version: 0.1.1
Status: Todo
Date: 2026-05-20
Style Guide: style-guide--technical-documentation-for-technologists-v0.2.0.md

## Abstract

This document records the open questions that must be resolved before ADR-014 can be written. It captures what is already proven and spoken — the settled decisions this ADR will draw on — and the six open questions that block or qualify the ADR's core decisions. It is intended as a working document to be resolved in a single session before the ADR is drafted.

## What is already settled

The following decisions are proven and spoken across earlier ADRs and working sessions. ADR-014 will state these as given and build on them without re-arguing them.

Every SAT archive is always a member of a collection. A standalone single-language archive is a collection of one. There is no such thing as a SAT archive that exists outside a collection. The collection is the fundamental unit.

The collection root is always identified by the presence of `.sat_meta/`. Discovery always walks upward from the current working directory until `.sat_meta/` is found. If no `.sat_meta/` is found, the working directory is not inside a SAT collection.

The watcher starts from the collection root and watches recursively downward. It receives all filesystem events in the collection tree and filters for the rename events it needs to handle.

Two categories of paired rename are required. An archive rename — renaming a language archive directory such as `en/` to `en-CA/` — requires the corresponding `.en_meta/` to be renamed to `.en-CA_meta/` as part of the same operation. A document rename — renaming a content file such as `henson-aircraft-aluminum.md` to `henson-al13-aluminum.md` — requires the corresponding `.henson-aircraft-aluminum_meta/` to be renamed to `.henson-al13-aluminum_meta/` as part of the same operation.

The watcher uses Python Watchdog as the cross-platform abstraction layer. Watchdog provides inotify on Linux, FSEvents on macOS, and ReadDirectoryChangesW on Windows, with a polling fallback. Windows requires a small debounce before acting on rename events because ReadDirectoryChangesW returns the event before the underlying I/O is complete.

A Git pre-commit hook serves as a secondary safety net. It catches any inconsistencies the watcher missed — for example if the watcher was not running — and refuses the commit, reporting what needs to be fixed. `sat validate` is an on-demand consistency check the author can run at any time. These are the second and third lines of defence. The watcher is the primary mechanism.

## Open questions — blocking

These three questions must be resolved before the ADR can be written. The ADR's core decisions depend on the answers.

### 1. Watcher lifecycle

How does the watcher process start and stop?

The options identified are:

- A daemon started at system boot or user login, running continuously in the background
- A process the author starts manually when beginning work in an archive, and stops when done
- A process started automatically when the author enters a SAT collection directory, using a shell hook such as direnv
- A per-command invocation — the watcher runs only during a specific SAT command and exits when the command completes

The choice affects everything about how the tool is described, installed, and used. It also affects the Windows behaviour — a continuously running daemon on Windows has different characteristics from a process started and stopped per session.

**Decision needed:** which lifecycle model does SAT adopt for v0.1?

### 2. Direct metadata directory rename

If an author renames `.en_meta/` to `.en-CA_meta/` directly — without first renaming `en/` to `en-CA/` — what does the watcher do?

Three possible positions:

- It is a valid operation. The watcher detects the metadata directory rename and renames the corresponding archive directory to match.
- It is an error. The watcher rejects the operation, reports what the author should have done, and does not act.
- It is ignored. The watcher does not watch hidden metadata directories directly. The author is responsible for keeping metadata directory names consistent with their archive directories.

The answer also affects whether the watcher watches hidden directories or only non-hidden directories.

**Decision needed:** what is the rule?

### 3. Move versus rename on Windows

On Linux and macOS, moving a file or directory to a different location fires a single rename event carrying both the old path and the new path. Watchdog's `on_moved()` handler receives both.

On Windows, Watchdog documents that it "tries hard to convert renames to movement events" but may represent a move as a delete event followed by a create event rather than a single rename event. This means a document move between content directories may not trigger the paired rename handler on Windows.

Three possible positions:

- Accept the limitation. Document moves on Windows may not trigger the paired rename. The Git pre-commit hook catches the inconsistency before it is committed.
- Require a solution. The watcher must handle the delete-and-create pair on Windows and reconstruct the move semantics before acting.
- Avoid the problem by design. Define that document moves between content directories are performed via a SAT command rather than direct filesystem operations. Direct moves are unsupported; `sat move` is the correct operation.

**Decision needed:** which position does SAT adopt?

## Open questions — important but deferrable

These three questions are important but can be noted as open decisions in the ADR without blocking it. They are listed here so they are not forgotten.

### 4. Multiple collection roots

Can one watcher instance watch multiple collection roots simultaneously — for example, a developer working across two SAT collections in different directories?

The expected answer for v0.1 is no — one watcher instance per collection root. But this should be stated explicitly rather than assumed.

### 5. Document move within a collection

When a document moves between two content directories within the same archive — for example from `en/products/` to `en/razors/` — the sibling `.{slug}_meta/` directory moves with it automatically because it is a sibling in the same parent directory. The filesystem handles this for free.

Does the watcher need to do anything in this case? The expected answer is no — but this should be stated explicitly. The watcher should confirm the sibling metadata directory moved correctly and report if it did not, rather than silently assuming the move was clean.

### 6. Watcher installation

Is the watcher installed as part of the SAT instantiation defined in ADR-009, or is it installed separately?

This question cannot be fully resolved until ADR-009 moves from Proposed to Accepted. The ADR-014 dependency on ADR-009 should be noted explicitly. For the purposes of writing ADR-014, assume the watcher is a component of an instantiated SAT instance and note the ADR-009 dependency.

## References

- ADR-001: Language as filesystem structure
- ADR-005: Tool self-discovery from filesystem context (Proposed)
- ADR-009: Distribution by installer and instantiation (Proposed)
- ADR-011: SAT collection model
- ADR-013: Non-standard language archive naming convention
- Python Watchdog documentation: https://python-watchdog.readthedocs.io/
- fswatch cross-platform file change monitor: https://emcrisostomo.github.io/fswatch/

## Changelog

| Version | Status | Notes |
|---|---|---|
| 0.1.1 | Todo | Vocabulary updated per ADR-020: birth/midwife -> instantiation/installer |
| 0.1.0 | Todo | Initial todo document — open questions to resolve before ADR is written |
