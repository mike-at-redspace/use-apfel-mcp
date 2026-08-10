---
name: use-apfel-mcp
description: Use when operating under a tight or on-device token budget (~4096 tokens, "apfel"/Apple on-device model), when the user asks to save tokens or cut context/API cost, when caveman/terse mode is active, when a task touches secrets/credentials/PII that shouldn't reach a cloud model, or when the same lightweight transform needs to run over many items in a loop — compress local files/logs/docs before they enter context, offload trivial or sensitive tasks to apfel directly, and (if apfel-mcp tools exist) route fetches through the minimal-token tool with hard call/output caps.
---

# use-apfel-mcp

Token-efficient reading, delegation, and tool routing for tight/on-device (~4096-token) budgets — works whether or not `apfel-mcp` tools are connected.

Built for [**apfel**](https://github.com/Arthur-Ficial/apfel) + [**apfel-mcp**](https://github.com/Arthur-Ficial/apfel-mcp), both by [Arthur Ficial](https://github.com/Arthur-Ficial). `brew install apfel` / `brew install arthur-ficial/tap/apfel-mcp`. Per-tool cheatsheets live in [`references/`](references/) — this file is the decision rules.

## Delegate whole tasks to apfel

For a bounded task that needs no multi-file reasoning and no judgment about this repo, hand it to `apfel` instead of spending the primary model's tokens.

| Trigger | Action |
| :--- | :--- |
| Single-file/log/doc lookup | `apfel -f <path> "<question>"` |
| User asked to save tokens/cost | Delegate automatically, no need to ask each time — say what got delegated |
| Caveman/terse mode active | Ask once per session before delegating — terse ≠ "hand this to another model" |
| Content is sensitive (secrets, `.env`, credentials, PII, medical/financial) | Delegate automatically *regardless of budget* — the point is nothing leaves the machine, not cost |
| Same transform over hundreds of items | Loop `apfel` in a shell script, not N primary-model calls — avoids rate limits too |
| Branch diff too big for apfel's 4096 tokens *and* too big to read raw | Don't skip apfel — chunk it: `scripts/diff-chunk.sh main...HEAD` skeletons new files, delegates each modified file's own diff individually, leaves small diffs in `--stat`, then runs a *second* apfel pass to group the resulting one-liners into categories. Grouping the summaries is still text-on-text, not codebase reasoning — only skip apfel for a step that needs real repo judgment (e.g. "is this breaking"). |
| Multi-file reasoning, edits, judgment calls, **or writing actual code** | Keep on the primary model — apfel has a 4096-token window, no memory of this repo, and shouldn't author code that ships (correctness stakes, not a draft-and-review task) |

**Generation from what's already on screen** — bounded drafts, still reviewed before they ship:

| Task | Command |
| :--- | :--- |
| Commit message from staged diff | `git diff --staged \| apfel "Write a conventional commit message. Output only the message."` |
| Diff review against team conventions | `git diff HEAD~1 \| apfel -f CONVENTIONS.md "Review this diff against our conventions"` |
| Release notes from commit log | `git log v1.0.0..v1.1.0 --oneline \| apfel "Group into Features, Bug Fixes, Refactoring"` |
| Explain a failed build | `npm run build 2>&1 \| apfel "Explain why this failed in 2 sentences"` |
| JSON API response → TypeScript interface | `curl -s api.example.com/item/1 \| apfel --code "TS interface named Item for this JSON"` |
| Regex from plain English | `apfel "Regex for a US phone number, both (555) 123-4567 and 555-123-4567"` |

All verified against `apfel`'s real flags/[EXAMPLES.md](https://github.com/Arthur-Ficial/apfel/tree/main/docs/EXAMPLES.md) — `-f` attaches file(s) to a prompt, `--code` returns bare code (exit 7 if empty), `--schema` guarantees valid JSON, `-o json` for scripting. See [`references/apfel-cli.md`](references/apfel-cli.md).

## Preprocess before reading raw

Content over ~1-2k chars headed into context: pipe it through the matching script, not a raw `cat`/`Read` or a hand-rolled `grep`/`sed`.

| Input | Tool |
| :--- | :--- |
| Code or JSON file | `scripts/ast-skeleton.py` — signatures/exports/deps only (~150 tokens); regex fallback on syntax errors |
| Log/build output | `scripts/log-filter.py` — deduped errors, warnings, final status, timeline |
| Long doc/article | `scripts/relevance-rank.py "<query>"` — top 3 paragraphs, scored |
| PDF/Office/HTML | `command -v markitdown` first — found → pipe through it into the scripts above; missing → say so in one line, don't silently read the raw binary, don't auto-install |

```bash
cat src/Button.tsx | python3 scripts/ast-skeleton.py
python3 scripts/log-filter.py build.log
python3 scripts/relevance-rank.py "OKLCH color config" < docs.md
markitdown design-spec.pdf | python3 scripts/relevance-rank.py "OKLCH color config"
```

Stdlib-only (no YAML — no stdlib parser), pipe-friendly, <100ms typical. Skip when content's already short, or you need an exact-line edit (a skeleton drops line numbers/bodies).

## If apfel-mcp tools are present, route through them

`apfel-mcp` installs four real MCP servers: `apfel-mcp-search-and-fetch`, `apfel-mcp-url-fetch`, `apfel-mcp-fs`, `apfel-mcp-ddg-search` (deliberately excluded from this routing). Names may show up under a different MCP-server prefix per session (e.g. `mcp__search-and-fetch__search`) and are often deferred — `ToolSearch` for `apfel`/`search-and-fetch`/`4096` before assuming none are connected.

| Scenario | Tool | Limit | Cheatsheet |
| :--- | :--- | :--- | :--- |
| Search + read page | `apfel-mcp-search-and-fetch` | 1 call not 2, ~5k chars | [search-and-fetch](references/apfel-mcp-search-and-fetch.md) |
| Known URL | `apfel-mcp-url-fetch` | Strips DOM, 6k chars | [url-fetch](references/apfel-mcp-url-fetch.md) |
| Local file/log/config | `apfel-mcp-fs` | Read-only, 6k chars, allowlisted | [fs](references/apfel-mcp-fs.md) |

Name the real tool explicitly in any prompt to these — the small model invents a plausible-but-wrong tool name from vague phrasing (symptom: `No MCP server provides tool 'X'`).

**Hard rules:** max 2 tool calls/turn, no retries on error (report in one sentence), out of scope for whole-codebase work/writes/multi-site research, never hallucinate past a truncation marker.

## Output

250 words max, bullets over prose. On visible truncation, say so (`"Data truncated at 6k chars. Omitted: [topic]."`) — don't invent what was cut, and don't retry, the cap is final.
