# content-egress-readme.md

Produces a clean, platform-neutral output document from a nursery Markdown
file and its canonical `.dc.yml` sidecar.

Egress is Stage 2 of the SAT content pipeline — it sits between content
ingress (normalization) and transmog (platform-specific output).

See the full pipeline: [content-pipeline.md](../../docs/architecture/content-pipeline.md)

---

## What it produces

Two files written to the output directory:

| File | Description |
| --- | --- |
| `<stem>.md` | Clean document — body only, no front matter |
| `.<stem>.dc.yml` | Canonical dc sidecar — copied alongside the clean document |

The output is deliberately platform-neutral. No front matter is written and
no derived metadata (OG, Schema.org) is generated at this stage — those are
transmog's responsibility.

Default output location: `egress/` subdirectory alongside the source file.

---

## Arguments

| Argument | Required | Description |
| --- | --- | --- |
| `--file <path/to/doc.md>` | Yes | Nursery Markdown file to process |
| `--sidecar <path>` | No | dc sidecar path (auto-discovered if absent) |
| `--spec <path>` | No | Content spec path (auto-discovered if absent) |
| `--output <dir>` | No | Output directory (default: `egress/` next to source) |
| `--overwrite` | No | Overwrite existing output files |
| `--dry-run` | No | Preview all outputs without writing |
| `--help` / `-h` | No | Print usage |

---

## Key behaviours

- The `.dc.yml` sidecar must exist before running egress — run
  `content-metadata-ingress.py` first if it does not
- Source front matter is always stripped — the clean document contains body only
- Body transformations are controlled by `default-content-spec.yml` — edit
  that file to change egress behaviour without touching any code
- The dc sidecar is copied to the output directory unchanged — transmog reads
  it from there to generate front matter and derived metadata
- Warns if required dc fields are missing from the sidecar, but continues
- Never overwrites existing output unless `--overwrite` is passed

---

## Auto-discovery

| Resource | Discovery method |
| --- | --- |
| dc sidecar | Looks for `.<stem>.dc.yml` alongside the source file |
| content spec | Walks upward from script to find `en/bin/content/definitions/defaults/default-content-spec.yml` |

---

## Body transformations

Transformations are applied in this order. Each can be enabled or disabled
in `default-content-spec.yml`.

| Transform | Default | Description |
| --- | --- | --- |
| `strip_front_matter` | `true` | Remove source front matter block |
| `strip_hr` | `true` | Remove `---`, `***`, `___` horizontal rules |
| `strip_emoji` | `true` | Remove emoji characters from body text |
| `clean_heading_markup` | `true` | Strip bold/italic from heading text |
| `heading_hierarchy` | `strict` | Enforce H1→H2→H3 — no skipping levels |
| `list_marker` | `dash` | Normalize unordered list markers to `-` |
| `code_fence_style` | `backtick` | Normalize fences to `` ``` `` |
| `trim_trailing_whitespace` | `true` | Strip trailing whitespace from all lines |
| `line_endings` | `lf` | Normalize to LF |
| `max_line_length` | `0` | `0` = no wrapping |

Code block contents are always protected — no transforms are applied inside
fenced code blocks.

---

## Usage

Dry run — preview without writing:

```bash
cd ~/projects/sat/prod/sat
python3 en/bin/content/content-egress.py \
  --file archives/test/my-doc.md \
  --dry-run
```

Write to default output directory (`egress/` next to source):

```bash
python3 en/bin/content/content-egress.py \
  --file archives/test/my-doc.md
```

Write to a specific output directory:

```bash
python3 en/bin/content/content-egress.py \
  --file archives/test/my-doc.md \
  --output /path/to/output/
```

---

## Output structure

```
archives/test/
├── my-doc.md                     ← source (nursery)
├── .my-doc.dc.yml                ← canonical sidecar (input)
└── egress/
    ├── my-doc.md                 ← clean document (body only)
    └── .my-doc.dc.yml            ← dc sidecar (copied)
```

---

## Required dc fields

Egress warns if any of these are missing from the `.dc.yml` sidecar:

`dc:title`, `dc:creator`, `dc:date`, `dc:rights`, `dc:language`,
`dc:identifier`, `dc:format`, `dc:type`

---

## Next steps after egress

The clean document and dc sidecar are ready for transmog. Pass the egress
output directory to the transmog tool with a platform target definition to
generate front matter, OG and Schema.org sidecars, and the final
publication-ready output.

See: [the-transmogrification-nut.md](../../docs/architecture/the-transmogrification-nut.md)
