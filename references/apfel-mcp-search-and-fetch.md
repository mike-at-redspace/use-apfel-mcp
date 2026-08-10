# `apfel-mcp-search-and-fetch` cheatsheet

The flagship compound tool — search *and* fetch in one call, trimmed to apfel's 4096-token window. Prefer this over chaining `apfel-mcp-ddg-search` + `apfel-mcp-url-fetch` (that's 2 calls where this is 1, and `ddg-search` is out of scope for this skill anyway — see [`SKILL.md`](../SKILL.md)).

## Exact call text

```bash
apfel --mcp $(which apfel-mcp-search-and-fetch) "use the search tool to find Swift 7 release date"
```

Name the tool ("use the search tool") rather than leaving it fully implicit — same tool-name-hallucination risk as any other apfel-mcp tool.

## In a Claude Code session

The equivalent may already be connected under a different MCP-server prefix — e.g. `mcp__search-and-fetch__search` (alias `web_search`), whose own description literally says "tuned for apfel's 4096-token context window." Check with `ToolSearch` for keywords like `apfel`, `search-and-fetch`, or `4096` before assuming nothing's connected — these tools are often deferred and won't show in a plain tool listing.

## Limits

- Default 2 results, ~1.8k chars/result, ~5k chars total.
- Max 2 tool calls per turn — never loop searches if the first pass doesn't land.
- No retries on HTTP error/SSRF block — report in one sentence instead.

## Recommendation

Pass a specific, narrow query — the combined 5k-char cap is shared across however many results you ask for, so 2 focused results beat 5 generic ones.
