# ADR-023-planning-process

Naming it properly matters here because the obvious candidates all collide with vocabulary we've already spent:

- **merge** — implies symmetric combination; ours is precedence, and git owns the word anyway
- **reconciliation** — ADR-014's word for recognizing a moved thing as the same thing
- **resolution / resolve** — the cascade's verb (`resolve_entity`)
- **settlement** — "settled decisions" is ADR vocabulary
- **description** — the true archival-science term for this exact activity, but it would give *description* two meanings in a project where `dc:description` is a field, violating one-term-one-definition

My recommendation: **metadata intake**. Plain English, a 7th grader parses it, zero collisions in SAT, and it's honest about what happens — the document arrives, its claims are taken in, examined against the archive's intent, and a record is produced. "Intake" also correctly scopes it as *one step of ingress*, not a synonym for ingress itself.

And your library-science tradition supplies the per-field vocabulary, which is the part I'd genuinely love your judgment on: cataloging distinguishes **transcribed** elements (taken from the item itself) from **supplied** elements (provided by the cataloger or authority). That's *exactly* our split — frontmatter is transcribed, cascade is supplied — and it means each sidecar field can carry its origin using words your discipline has trusted for a century.

The intake policy table, best guesses per field — the seed of ADR-023:

| Field                                                        | Owner               | Frontmatter present?                  | Conflict behaviour                                           | Origin recorded        |
| ------------------------------------------------------------ | ------------------- | ------------------------------------- | ------------------------------------------------------------ | ---------------------- |
| `dc:title`                                                   | Document            | transcribed                           | n/a — closest declaration wins                               | transcribed            |
| `dc:creator`                                                 | Document            | transcribed                           | n/a                                                          | transcribed            |
| `dc:subject`                                                 | Document + cascade  | transcribed, cascade may add          | union or replace — the open `dc:subject` merge question finally forced | transcribed / supplied |
| `dc:description`                                             | Document            | transcribed                           | n/a; never `<calculated>`                                    | transcribed            |
| `dc:date`                                                    | Document            | transcribed                           | n/a; absent → filesystem `st_birthtime` or operator          | transcribed / supplied |
| `dc:language`, `dc:language_bcp47`                           | Archive (structure) | read, never accepted                  | supplied wins; disagreement is a **finding**, narrated, review-flagged — ingress never picks | supplied               |
| `dc:publisher`, `dc:rights`                                  | Cascade             | transcribed overrides only if present | frontmatter is a deliberate per-document exception; narrated | transcribed / supplied |
| `dc:type`, `dc:format`                                       | Cascade/tooling     | ignored                               | tooling knows better than claims                             | supplied               |
| `dc:identifier`, `sat_uuid`, `translationKey`, any identity residue | Nobody              | **quarantined**                       | never merged; preserved verbatim in the ingress record as possible join evidence | quarantined            |

Plus the two standing rules: transcribed values are never modified (the claim is recorded verbatim in the ingress record even when overridden), and the entire stripped frontmatter block is preserved in the ingress record — relocated, never destroyed.

Note what row 3 does: the `dc:subject` cascade merge-versus-replace question — open since before this conversation began — can't be dodged once intake exists. ADR-023 is where it finally dies.

If **metadata intake** and **transcribed/supplied** land for you (with *quarantined* as my invented third — happy to hear a better cataloging term for "recorded but never admitted"), I'll draft ADR-023 around this table.