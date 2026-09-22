# Architecture Decision Records

Use an ADR for a significant decision that affects architecture, contracts, security boundaries, operational behavior, or the direction of future work.

Do not create an ADR for every code change. Write one when recording the reasoning will help a future reader understand why a meaningful choice was made.

## Naming

Use sequential names:

```text
0001-short-decision-title.md
0002-another-decision.md
```

Copy [0000-template.md](0000-template.md) and replace its placeholders. Keep ADRs concise enough to reread during later phases.

## Status lifecycle

- **Proposed** — under discussion; implementation should not rely on it yet.
- **Accepted** — the current decision.
- **Superseded** — replaced by a later ADR; link to the replacement.
- **Rejected** — considered and intentionally not chosen.

Do not edit history to make an old decision look better. If circumstances change, preserve the old ADR and supersede it with a new one.
