# ADR-014: Filesystem-Event-Driven Tooling Model

Status: Proposed
Date: 2026-05-21

## Context

ADR-012 defines the conformant document schema and the ingress process for documents arriving in a SAT archive. ADR-011 defines the collection model including paired rename requirements for archive directories and their `.{language}_meta/` counterparts. Both of these specifications require a tooling layer that responds to filesystem events in real time — detecting new files, paired rename requirements, and inconsistencies — without requiring the author to manually invoke SAT commands after every filesystem operation.

The alternative to event-driven tooling is batch validation — the author works freely and runs a validation command periodically or at commit time. This approach works but it widens the window between when an inconsistency occurs and when it is detected. An author who renames `en/` to `en-CA/`, does an hour of writing, and then commits will encounter a list of issues at commit time that are disconnected from the actions that caused them. Event-driven tooling closes this window to milliseconds for authors who start the watcher, and falls back to commit-time detection for authors who do not.

Three requirements drive this decision:

**Immediate feedback.** Inconsistencies should be detected and reported at the moment they occur, not deferred to commit time. An author who renames an archive directory should know immediately that the metadata directory rename is required or has been performed.

**Cross-platform consistency.** The tooling must work on Linux, macOS, and Windows. The underlying filesystem event APIs differ across platforms in ways that affect how move and rename events are reported. The tooling must handle these differences gracefully without platform-specific workarounds that introduce fragility.

**Resilience without the watcher.** Authors may not always start the watcher. The tooling model must provide a reliable fallback that catches everything the watcher missed, without requiring the author to understand the difference between the two paths.

## Decision

### 1. The four-command tooling model

SAT's filesystem tooling is expressed through four commands with distinct responsibilities:

**`sat watch`** — starts the filesystem watcher. Discovers the collection root by walking upward from the current directory until `.sat_meta/` is found. If no collection root is found, reports that the current directory is not inside a SAT collection and exits. Watches the entire collection tree recursively. Runs in the foreground until stopped with `Ctrl+C`. The `--detach` flag runs it as a background process for the current terminal session, stopped by `sat unwatch` or terminal exit.

**`sat status`** — reports the current state of the archive without modifying anything. Lists uninitiated documents, stale metadata directory names, incomplete ingress records, missing translation group entries, and any other detectable inconsistencies. Safe to run at any time. Does not require the watcher to be running.

**`sat fix`** — resolves all detectable inconsistencies automatically within the author's permission level (ADR-004). Reports what it did and what it could not do. Requires the author to review the report before proceeding when actions affect content rather than infrastructure. Does not require the watcher to be running.

**`sat unwatch`** — stops a detached watcher process. No-op if no watcher is running.

### 2. Watcher lifecycle

The watcher is session-scoped and manually started. It is not a system daemon and does not persist across terminal sessions or system restarts. This is a deliberate choice consistent with SAT's lightweight, sovereign philosophy — the tool does not install background services or modify system configuration.

The author starts `sat watch` before working in the archive. If they forget, the pre-commit hook and `sat fix` provide the fallback path. The working experience differs between the two paths:

**With watcher running** — inconsistencies are detected and reported immediately. The author is notified at the moment of the triggering action and can respond in context.

**Without watcher running** — the author works normally. The pre-commit hook catches inconsistencies at commit time and refuses the commit, reporting what needs fixing. The author runs `sat fix` to resolve. The archive is never committed in an inconsistent state.

Neither path produces lost data or silent corruption. The watcher provides a better working experience. The hook provides a reliable safety net.

### 3. Watch scope

The watcher watches the entire collection tree recursively from the collection root, including hidden directories. There is no hidden/non-hidden boundary in the watch scope.

Watching hidden directories is necessary for complete archive visibility. A metadata directory that is accidentally deleted, a `sat/identity.yml` that is corrupted, or a direct rename of a `.{language}_meta/` directory — all of these are only detectable with full watch scope. Excluding hidden directories would require the hook to catch these cases, widening the detection window and reducing the value of real-time watching.

The watcher observes all events and dispatches to the appropriate handler based on event type and path. The handler decides what action, if any, is appropriate. The watcher is an observer, not a filter.

### 4. Paired rename handling

When the author renames a language archive directory — `en/` to `en-CA/` — the watcher detects the rename event and performs the corresponding metadata directory rename:

```text
Author renames: en/ → en-CA/
    ↓
Watcher fires on_moved(): src=en/ dest=en-CA/
    ↓
Handler checks: .en_meta/ exists at collection root level
Handler performs: .en_meta/ → .en-CA_meta/
Handler reports: "Renamed .en_meta/ to .en-CA_meta/"
```

When the author renames a document — `henson-jet-black.md` to `henson-al13-jet-black.md` — the watcher performs the corresponding metadata directory rename:

```text
Author renames: henson-jet-black.md → henson-al13-jet-black.md
    ↓
Watcher fires on_moved(): src=.../henson-jet-black.md dest=.../henson-al13-jet-black.md
    ↓
Handler checks: .henson-jet-black_meta/ exists as sibling
Handler performs: .henson-jet-black_meta/ → .henson-al13-jet-black_meta/
Handler reports: "Renamed .henson-jet-black_meta/ to .henson-al13-jet-black_meta/"
```

When the author renames a content directory — `en/products/` to `en/razors/` — the metadata directories inside it move with it automatically because they are siblings of the documents they describe. The watcher verifies the move was complete and reports. No paired rename is required at the content directory level.

### 5. Direct metadata directory rename

When the author renames a metadata directory directly — `.en_meta/` to `.en-CA_meta/` — without renaming the corresponding archive directory, the watcher detects an inconsistency immediately:

```text
Author renames: .en_meta/ → .en-CA_meta/
    ↓
Watcher fires on_moved(): src=.en_meta/ dest=.en-CA_meta/
    ↓
Handler checks: is there a corresponding archive directory en-CA/?
    en-CA/ does not exist — no corresponding rename detected
    ↓
Handler reports immediately:
  "SAT: .en-CA_meta/ renamed but en-CA/ not found.
   Did you mean to rename en/ to en-CA/?
   Run `sat fix` to complete the paired rename, or
   Run `sat revert` to restore .en_meta/"
```

The watcher does not perform the archive directory rename automatically. Renaming a hidden infrastructure directory is a low-consequence action. Renaming an archive root directory moves all content and is a high-consequence action that requires explicit author intent. The watcher reports and offers options. The author decides.

### 6. Ingress triggering

The watcher triggers the ingress process defined in ADR-012 when a new `.md` file appears in a content directory with no corresponding metadata directory. The ingress process evaluates format, frontmatter presence, and slug conformance, and produces an ingress record at `.{slug}_meta/ingress/`.

The watcher dispatches ingress and paired rename as separate handlers. They do not interfere with each other.

### 7. Cross-platform behaviour and the Windows move case

SAT uses Python Watchdog as the cross-platform filesystem event abstraction layer. Watchdog uses inotify on Linux, FSEvents on macOS, and ReadDirectoryChangesW on Windows, with a polling fallback for environments without a dedicated event API.

On Linux and macOS, a file or directory move fires a single `on_moved()` event carrying both the source path and the destination path. The paired rename handler and the ingress handler both receive complete information from this single event.

On Windows, ReadDirectoryChangesW may represent a file move between directories as a delete event in the source directory followed by a create event in the destination directory, rather than a single move event. This is a consequence of how the Windows kernel reports filesystem changes — it is not a Watchdog bug, not a SAT bug, and not something that should be "fixed" at the event layer.

**Why we do not attempt to reconstruct move semantics from delete and create pairs on Windows:**

The tempting approach is to implement platform-specific logic that matches delete and create events by filename, timing, or content hash to reconstruct move semantics. This approach is fragile by design. It introduces timing dependencies — the create must arrive within a certain window after the delete. It fails for large files where the create event arrives significantly after the delete. It produces false positives when a file genuinely is deleted and a different file with the same name is created shortly after. It adds platform-specific complexity that is difficult to test and easy to break.

More importantly, this approach is unnecessary. The SAT architecture already handles this correctly at a higher level through UUID-based reconciliation in the ingress process.

**How UUID-based reconciliation handles the Windows move case correctly:**

When Windows reports a file move as delete + create, the watcher sees a new `.md` file in the destination directory with no metadata directory. The ingress process fires. Before generating a new UUID and treating the file as a new document, the ingress process scans the collection for orphaned metadata directories — metadata directories whose corresponding document file no longer exists at the expected path. If an orphaned metadata directory is found whose `sat_uuid` matches the arriving file, the ingress process recognises this as a moved document, not a new one. It moves the orphaned metadata directory to sit alongside the file, updates the ingress record noting the reconciliation, and preserves the document's identity. No new UUID is generated. The document's identity is intact.

```text
Windows reports file move as delete + create:
    DELETE: en/products/henson-jet-black.md
    CREATE: en/razors/henson-jet-black.md
    ↓
Watcher fires on_deleted() — handler notes orphaned metadata candidate
Watcher fires on_created() — ingress process starts
    ↓
Ingress: new .md file, no metadata directory
    ↓
Ingress scans for orphaned .henson-jet-black_meta/ directories
    Found: en/products/.henson-jet-black_meta/
    Reads: sat_uuid from sat/identity.yml
    ↓
Ingress recognises: moved document, not new document
Ingress moves: en/products/.henson-jet-black_meta/
           to: en/razors/.henson-jet-black_meta/
Ingress records: reconciliation event in ingress record
    ↓
Document identity preserved. No new UUID. No data loss.
```

This reconciliation logic runs on all platforms, not just Windows. On Linux and macOS the `on_moved()` event fires correctly and the paired rename handler runs before the ingress process would see the file as new. The reconciliation path is a fallback that is never reached on Linux and macOS under normal conditions. On Windows it is the primary path for cross-directory moves.

A developer reading this code should understand: the reconciliation logic is not a workaround. It is the correct architectural response to the fact that file identity is expressed by UUID, not by path. A file that moves is the same document. The tool recognises this by checking UUID, not by reconstructing move events from delete and create pairs.

**The directory rename debounce:**

For directory renames on Windows, Watchdog documents that ReadDirectoryChangesW returns the event before the underlying I/O is complete. The handler applies a 100ms debounce before acting on directory rename events. This is the only platform-specific timing accommodation in the tooling model. It is not a workaround — it is an acknowledgement that the Windows API makes a different guarantee about event timing than inotify and FSEvents.

### 8. Pre-commit hook

The pre-commit hook runs `sat status` before every commit. If any inconsistencies are detected, the commit is refused and the author is shown the status report. The author runs `sat fix` to resolve the issues and then commits again.

The hook is installed as part of SAT instantiation (ADR-009, Proposed). It runs in the Git environment, which provides Unix-like path semantics on all platforms including Windows with Git Bash. The hook implementation is a single shell script that does not require platform-specific logic.

The hook is the safety net for sessions where the watcher was not running. It ensures the SAT invariants hold at every commit regardless of how the author worked during the session. A SAT archive should never have a committed state where a language archive directory has been renamed but its metadata directory has not, or where a document exists without a corresponding metadata directory.

### 9. Collection root discovery

All four commands discover the collection root by walking upward from the current working directory until `.sat_meta/` is found. This is the same upward-walking discovery mechanism used throughout the SAT architecture (ADR-001, ADR-005, ADR-011). The tool can be invoked from any directory inside the collection tree — a content directory, an archive root, the collection root itself — and it always finds the right starting point.

If no `.sat_meta/` is found, the command reports that the current directory is not inside a SAT collection and exits cleanly. No error, no crash — the tool simply has nothing to watch or fix.

## Alternatives Considered

**System daemon** — a continuously running background process started at system boot. Rejected because it requires installation as a system service with different procedures on each operating system, runs even when the author is not working in a SAT archive, and is inconsistent with SAT's lightweight sovereign philosophy. The session-scoped manual start provides the same event-driven behaviour without the system-level footprint.

**direnv-style automatic start** — the watcher starts automatically when the author enters a SAT collection directory using a shell hook. Rejected for v0.1 because it requires shell profile configuration that can fail silently and adds a setup step that is not obviously required. Manual start is simpler and more predictable. direnv-style start remains a candidate for a future convenience feature.

**Per-command invocation** — the watcher runs only during a specific SAT command. Rejected because it cannot respond to external events such as drag-and-drop or editor saves that occur outside SAT command invocations.

**Excluding hidden directories from watch scope** — watching only non-hidden directories and files. Rejected because direct metadata directory renames, accidental metadata directory deletions, and metadata file corruption would not be detected until commit time. Full watch scope with handler-level policy is simpler and more complete.

**Platform-specific move reconstruction on Windows** — implementing timing-based logic to reconstruct move semantics from delete and create pairs on Windows. Rejected because it introduces timing dependencies and fragility. UUID-based reconciliation in the ingress process handles this correctly at the architectural level without platform-specific code.

**`sat move` command** — requiring authors to use a SAT-mediated move command rather than native filesystem moves. Rejected because it adds friction for a problem the architecture already handles through UUID-based reconciliation. Authors should be free to use their filesystem naturally.

**Batch validation only — no watcher** — relying entirely on `sat status` and the pre-commit hook. Rejected because it widens the inconsistency detection window unnecessarily for authors who want real-time feedback. The watcher is optional — authors who prefer batch validation can simply not run it.

## Consequences

- The watcher is session-scoped and manually started — not a system daemon
- `sat watch`, `sat status`, `sat fix`, and `sat unwatch` are the four tooling commands
- The watcher watches the entire collection tree recursively including hidden directories
- Paired renames are performed automatically by the watcher for archive directory renames and document renames
- Direct metadata directory renames are detected immediately and reported with options — the watcher does not perform the corresponding archive directory rename automatically
- Ingress is triggered by the watcher when a new `.md` file appears without a metadata directory
- On Windows, file moves between directories may be reported as delete + create — UUID-based reconciliation in the ingress process handles this correctly without platform-specific code
- A 100ms debounce is applied to directory rename events on Windows to accommodate ReadDirectoryChangesW timing
- The pre-commit hook runs `sat status` before every commit and refuses commits with detected inconsistencies
- Collection root is discovered by upward-walking from the current directory — the tool can be invoked from anywhere inside the collection tree
- The tooling model does not require Git — all commands work without Git present, with the ingress record providing inline recovery data when Git is unavailable (ADR-012)

## References

- ADR-001: Language as filesystem structure
- ADR-004: Self-replicating permission model
- ADR-005: Tool self-discovery from filesystem context (Proposed)
- ADR-009: Distribution by installer and instantiation (Proposed)
- ADR-011: SAT collection model
- ADR-012: Conformant document schema
- Python Watchdog. (2024). *Watchdog documentation*. https://python-watchdog.readthedocs.io/
- Microsoft. (2024). *ReadDirectoryChangesW function*. https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-readdirectorychangesw

## Licence

This document by **Christopher Steel**, with contributions from AI systems including **ChatGPT (OpenAI)**, **Claude Sonnet 4.6 (Anthropic)**, and **Claude Sonnet 4.7 (Anthropic)**, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 International Licence](https://creativecommons.org/licenses/by-sa/4.0/).

## Changelog

| Version | Status | Notes |
|---|---|---|
| 0.1.1 | Proposed | Vocabulary updated per ADR-020: birth/midwife -> instantiation/installer |
| 0.1.0 | Proposed | Initial draft — supersedes todo document |
