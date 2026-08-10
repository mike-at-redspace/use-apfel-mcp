# `apfel-mcp-url-fetch` cheatsheet

Fetches a known URL and strips DOM bloat, trimmed to apfel's 4096-token window. Use this instead of `apfel-mcp-search-and-fetch` when you already have the URL — no need to search for it.

## Exact call text

```bash
apfel --mcp $(which apfel-mcp-url-fetch) "fetch https://example.com/docs and summarize the color-token section"
```

Include both the URL and what you want out of it in one prompt — the tool fetches once, so an underspecified prompt means a second round-trip.

## Limits

- Cap 6k chars — a long page truncates, first slice only.
- Max 2 tool calls per turn.
- No retries on HTTP error/SSRF block/redirect failure — report in one sentence instead of looping.
- Never hallucinate content past a visible truncation marker.

## Recommendation

If the target page is long and you only need one section, pipe the raw fetch through `scripts/relevance-rank.py "<query>"` (see [`SKILL.md`](../SKILL.md)) rather than trusting the 6k-char cap to land on the right part.
