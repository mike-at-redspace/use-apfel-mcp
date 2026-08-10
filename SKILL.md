---
name: use-apfel-mcp
description: Use when operating under a tight or on-device token budget (~4096 tokens, "apfel"/Apple on-device model), when the user asks to save tokens or cut context/API cost, when caveman/terse mode is active, when a task touches secrets/credentials/PII that shouldn't reach a cloud model, or when the same lightweight transform needs to run over many items in a loop — compress local files/logs/docs before they enter context, offload trivial or sensitive tasks to apfel directly, and (if apfel-mcp tools exist) route fetches through the minimal-token tool with hard call/output caps.
---

# use-apfel-mcp

Route retrieval and bounded text work through `apfel` (on-device, ~4096 tokens) instead of spending primary-model tokens on it. Routing layer only — confirm `apfel`/`apfel-mcp` are actually installed (`command -v apfel`; `ToolSearch` for apfel-mcp tools) before delegating. Built on [apfel](https://github.com/Arthur-Ficial/apfel) + [apfel-mcp](https://github.com/Arthur-Ficial/apfel-mcp) by [Arthur Ficial](https://github.com/Arthur-Ficial). Cheatsheets: [`references/`](references/).

## Always, first: preprocess before anything reads raw

Content over ~1-2k chars entering context gets compressed before it's read — regardless of which branch below handles the actual task, sensitive or not, since these run 100% locally too. Your shell's `cwd` is usually the project you're working in, not this skill's folder — use the absolute path below (`$SKILL` = `~/.agents/skills/use-apfel-mcp`, wherever your runtime symlinks from), not a bare `scripts/...` that only resolves if `cwd` happens to be here:

| Input | Tool |
| :--- | :--- |
| Code/JSON file | `$SKILL/scripts/ast-skeleton.py` — signatures/exports/deps (~150 tokens); regex fallback on syntax errors |
| Log/build output | `$SKILL/scripts/log-filter.py` — deduped errors/warnings/status/timeline |
| Long doc | `$SKILL/scripts/relevance-rank.py "<query>"` — top 3 paragraphs, scored |
| Branch diff too big for 4096 tokens | `$SKILL/scripts/diff-chunk.sh <range>` — per-file, then a *second* apfel pass groups the digest (still text-on-text, not codebase reasoning) |
| PDF/Office/HTML | `command -v markitdown` first — found → pipe through it; missing → say so, don't read the raw binary, don't auto-install |

Skip only when content's already short, or you need an exact-line edit (a skeleton drops line numbers).

## Then: decide where the task itself goes

| Trigger | Action |
| :--- | :--- |
| Single-file/log/doc lookup | `apfel -f <path> "<question>"` |
| Sensitive content (secrets, `.env`, credentials, PII, medical/financial) | Delegate regardless of budget — the point is nothing leaves the machine, not cost |
| User asked to save tokens/cost | Delegate automatically, no need to ask each time — say what got delegated |
| Caveman/terse mode active | Ask once per session first — terse ≠ "hand this to another model" |
| Same transform over hundreds of items | Loop `apfel`, not N primary-model calls — avoids rate limits too |
| Bounded draft from on-screen text (commit message, PR notes, diff review, build-failure explanation, JSON→TS) | Delegate — still reviewed before it ships, see examples below |
| Cutoff-agnostic (regex, algorithms/data structures, reformatting, stable shell one-liners, generic explanations) | Delegate — correctness here is timeless, not dependent on training data |
| Multi-file reasoning, edits, judgment calls, or code depending on current framework/library APIs | **Primary model** — apfel's cutoff and lack of repo memory make this a correctness risk, not a draft-and-review task |

```bash
git diff --staged | apfel "Write a conventional commit message. Output only the message."
git diff HEAD~1 | apfel -f CONVENTIONS.md "Review this diff against our conventions"
git log v1.0.0..v1.1.0 --oneline | apfel "Group into Features, Bug Fixes, Refactoring"
npm run build 2>&1 | apfel "Explain why this failed in 2 sentences"
curl -s api.example.com/item/1 | apfel --code "TS interface named Item for this JSON"
apfel "Regex for a US phone number, both (555) 123-4567 and 555-123-4567"
apfel --code "python function that deduplicates a list preserving order"
```

Flags are real, confirmed against apfel's own [EXAMPLES.md](https://github.com/Arthur-Ficial/apfel/tree/main/docs/EXAMPLES.md); prompts above are illustrative, not all verbatim. See [`references/apfel-cli.md`](references/apfel-cli.md).

**If `apfel` itself fails** (non-zero exit, crash, timeout, or `--code` exits 7 on an empty response): don't retry with a reworded prompt — say so in one line (`apfel failed/unavailable, falling back to primary model`) and do that step yourself instead. One exception: `command -v apfel` failing at the very start just means it's not installed — that's an availability check, not a failure, so report it once and skip delegation for the rest of the turn rather than repeating the notice per task.

## If apfel-mcp tools are present, route fetches through them

Real MCP servers, may appear under a different prefix per session (e.g. `mcp__search-and-fetch__search`) and are often deferred — `ToolSearch` for `apfel`/`search-and-fetch`/`4096` before assuming none are connected. Name the real tool explicitly in any prompt to these — vague phrasing lets the small model invent a tool name that doesn't exist (symptom: `No MCP server provides tool 'X'`).

| Scenario | Tool | Limit | Cheatsheet |
| :--- | :--- | :--- | :--- |
| Search + read page | `apfel-mcp-search-and-fetch` | 1 call not 2, ~5k chars | [search-and-fetch](references/apfel-mcp-search-and-fetch.md) |
| Known URL | `apfel-mcp-url-fetch` | Strips DOM, 6k chars | [url-fetch](references/apfel-mcp-url-fetch.md) |
| Local file/log/config | `apfel-mcp-fs` | Read-only, 6k chars, allowlisted | [fs](references/apfel-mcp-fs.md) |

**Hard rules:** max 2 tool calls/turn, no retries on error (report in one sentence), out of scope for whole-codebase work/writes/multi-site research, never hallucinate past a truncation marker.

## Output

250 words max, bullets over prose. On visible truncation, say so (`"Data truncated at 6k chars. Omitted: [topic]."`) — don't invent what was cut, and don't retry, the cap is final.
