---
dc:title: "Running the content ingress Test Suites"
dcterms:version: "0.1.0"
dc:creator: "Christopher Steel"
dc:contributor: "Claude Fable 5 (Anthropic)"
dc:description: "How to run the two content ingress test suites: the satlib unit suite and the content tool integration suite, including the editable install with the markdown extra."
dcterms:created: "2026-08-03"
dcterms:modified: "2026-08-03"
dc:format: "text/markdown"
dc:language: "en"
sat:language_bcp47: "en"
dc:identifier: "content-ingress-tests-readme"
dcterms:rightsHolder: "Christopher Steel"
dc:rights: >
  Copyright 2026 Christopher Steel.
  SPDX-License-Identifier: AGPL-3.0-or-later
sat:uuid: ""
sat:repository: "sat"
sat:path: "en/bin/content/tests/"
sat:migration_status: pre-sat
sat:changelog:
  - version: "0.1.0"
    date: "2026-08-03"
    author: "Christopher Steel, Claude Fable 5 (Anthropic)"
    notes: "Initial note, merging content-ingress-tests.md and content-ingress-tool-implementation-testing-v0-1-0.md from en/docs/implementation/, both of which it supersedes. Stale output snapshots dropped."
---

# Running the content ingress Test Suites

Two suites cover the ingress pipeline: the satlib unit suite (cataloging,
staging, markdown, and the rest of the library) and the content tool
integration suite (the end-to-end pipeline against hermetic fixtures).

One-time setup, from the repository root: activate the venv and install
satlib editable with the markdown extra, which brings in mdformat for the
step 9.5 normalization tests.

```bash
source en/lib/satlib/.venv/bin/activate
python -m pip install -e 'en/lib/satlib[markdown]'
```

Run the satlib suite:

```bash
cd en/lib/satlib
python -m pytest -q
```

Run the tool suite, from the repository root:

```bash
python -m pytest en/bin/content/tests -o python_files='content-ingress-tests.py' -q
```

Both suites must be green before a release; expected counts live in the
implementation plans' execution records, not here, so this note does not go
stale as the suites grow.
