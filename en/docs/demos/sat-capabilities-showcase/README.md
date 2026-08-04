Four files created under `en/docs/demos/sat-capabilities-showcase/` in the `sat` repo, all matching the repo's automa (Dublin Core frontmatter, `Version:`/`Status:`/`Style Guide:` block, AGPL license line, changelog, no em-dashes, no horizontal rules):

- [demo-runbook-v0-1-0.md](https://claude.ai/sat/en/docs/demos/sat-capabilities-showcase/demo-runbook-v0-1-0.md) — the timed 15-min presenter script: 7 beats, exact commands, talking points, reset/teardown, and a fallback section.
- [demo-value-brief-v0-1-0.md](https://claude.ai/sat/en/docs/demos/sat-capabilities-showcase/demo-value-brief-v0-1-0.md) — the plain-language, no-CLI one-pager for the room.
- [resources/messy-source-sample.md](https://claude.ai/sat/en/docs/demos/sat-capabilities-showcase/resources/messy-source-sample.md) — the deliberately raw input to ingress live.
- [resources/demo-preseed.yml](https://claude.ai/sat/en/docs/demos/sat-capabilities-showcase/resources/demo-preseed.yml) — prewired answers so setup is one command.

Two honest flags:

1. **The messy sample intentionally breaks the house rules** (numbered headings, em-dashes, a horizontal rule, no metadata) — that's the "before" state the demo normalizes. It carries a top comment saying so, so nobody mistakes it for an automa violation or "fixes" it.
2. **The publish beat names the transmog vector but doesn't pin a subcommand** — I only verified `sat init`, `content ingress`, and the `collection` commands against the sources. The runbook's "Command verification status" section says to confirm `transmog --help` during rehearsal and pin it in. Want me to nail down the exact transmog publish command now so the runbook is fully concrete?