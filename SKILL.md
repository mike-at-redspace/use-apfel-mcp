---
name: use-apfel-mcp
description: Use when operating under a tight or on-device token budget (~4096 tokens, "apfel"/Apple on-device model), when the user asks to save tokens or cut context/API cost, or when caveman/terse mode is active — compress local files/logs/docs before they enter context, offload trivial single-file lookups to apfel directly, and (if apfel-mcp tools exist) route fetches through the minimal-token tool with hard call/output caps.
---

# use-apfel-mcp

Token-efficient reading, delegation, and tool routing for tight/on-device (~4096-token) budgets. Applies whether or not `apfel-mcp` tools are actually connected — the compression step below is tool-agnostic.

Built for [**apfel**](https://github.com/Arthur-Ficial/apfel) (Apple Intelligence from the command line — on-device via `FoundationModels`, no API keys, no cloud) and [**apfel-mcp**](https://github.com/Arthur-Ficial/apfel-mcp) (its token-budget MCP tools), both by [Arthur Ficial](https://github.com/Arthur-Ficial). `brew info apfel` / `brew info apfel-mcp` for install; homepage [apfel.franzai.com](https://apfel.franzai.com). Per-tool cheatsheets (exact invocation text, examples, caveats) live in [`references/`](references/) — this file covers the decision rules.

## Delegate trivial tasks to apfel entirely

This is the token-saving move, distinct from the preprocessing below: for a bounded task that doesn't need multi-file reasoning or judgment about this repo's conventions, hand the whole thing to `apfel` instead of spending the main model's tokens on it. Two shapes of task qualify:

- **Retrieval** — a single-file/log/doc lookup. `apfel -f <path> "<question>"` for a known local path (see [`references/apfel-cli.md`](references/apfel-cli.md)).
- **Generation from what's already on screen** — drafting where apfel doesn't need to understand the repo, just transform the input in front of it:

  | Task | Command |
  | :--- | :--- |
  | Commit message from staged diff | `git diff --staged \| apfel "Write a conventional commit message for this diff. Output only the message."` |
  | PR/release-notes draft from commit log | `git log v1.0.0..v1.1.0 --oneline \| apfel "Group these into Features, Bug Fixes, Refactoring"` |
  | Regex from a plain-English description | `apfel "Regex matching a US phone number, formats (555) 123-4567 and 555-123-4567"` |
  | Terminal error explainer | `cargo build 2>&1 \| apfel "Explain why this failed in 2 sentences"` |
  | Short rewrite/rephrase | `echo "$text" \| apfel "Make this more concise"` |

  Treat these as a *draft*, not a final answer — a commit message or PR description still needs your review before it ships, same as anything else generated. Don't delegate the parts that need project-specific judgment: a PR description that must match this repo's template, reference a specific ticket, or explain *why* a change was made (not just what changed) stays on the main model, which actually has that context.

- **User explicitly asked to save tokens/cost, and `apfel` is installed:** do either automatically, no need to ask each time — say in one line what got delegated so the split is visible.
- **Caveman/terse mode is active:** ask once per session — *"Want me to route trivial lookups/drafts through apfel to save tokens while caveman mode's on?"* Caveman mode means "be terse," not "hand this off to a different model," so it's an ask, not an assumption.
- **Keep on the main model:** multi-file reasoning, anything that edits code, anything needing judgment about this codebase's conventions or history. `apfel`'s on-device model has a 4096-token window and no memory of this repo — don't delegate what needs either.

## Preprocess before reading raw — always, regardless of which tool fetched it

If a code file, log, or doc/URL content is going to land in context and it's more than ~1-2k chars, don't `cat`/`Read` it whole and don't hand-roll a `grep`/`sed` one-liner — pipe it through the matching script first. They give consistent, structured output (deduped errors, scored paragraphs, clean signatures) instead of ad hoc line matches:

| Input | Tool | Effect |
| :--- | :--- | :--- |
| Code file (py/ts/js) | `scripts/ast-skeleton.py` | Full file → signatures/exports/imports only (~150 tokens) |
| Config file (`.json`) | `scripts/ast-skeleton.py` | Full file → top-level keys + dependency names, boilerplate dropped |
| Log/build output | `scripts/log-filter.py` | Raw log → deduped errors, warnings, final status, timeline |
| Long doc/article | `scripts/relevance-rank.py "<query>"` | Full doc → top 3 paragraphs matching the query, scored |
| PDF/Office/HTML | [`markitdown`](https://github.com/microsoft/markitdown) | Convert to markdown *first*, then pipe that into `relevance-rank.py`/`ast-skeleton.py` above — not stdlib, install separately (README) |

```bash
cat src/Button.tsx | python3 ~/.claude/skills/use-apfel-mcp/scripts/ast-skeleton.py
python3 ~/.claude/skills/use-apfel-mcp/scripts/log-filter.py build.log
python3 ~/.claude/skills/use-apfel-mcp/scripts/relevance-rank.py "OKLCH color config" < docs.md
markitdown design-spec.pdf | python3 ~/.claude/skills/use-apfel-mcp/scripts/relevance-rank.py "OKLCH color config"
```

Each is stdlib-only (no YAML support — Python has no stdlib YAML parser, so `.yml`/`.yaml` fall back to raw), pipe-friendly (stdin or file-path arg), <100ms on typical input.

**Skip preprocessing when:**
- Content is already short enough that raw wouldn't blow the budget.
- You need to make an exact edit at a known line (e.g. "fix line 42") — a skeleton throws away the line numbers and body you need to edit.

## If apfel-mcp tools are present, also route through them

`apfel-mcp` (`brew install arthur-ficial/tap/apfel-mcp`) installs four real MCP servers with these literal names — `apfel-mcp-url-fetch`, `apfel-mcp-ddg-search` (out of scope here, see below), `apfel-mcp-search-and-fetch`, `apfel-mcp-fs`. In a given session they may show up under a different MCP-server prefix (e.g. this environment exposes the same search-and-fetch behavior as `mcp__search-and-fetch__search`) and **often deferred** (won't show in a plain tool listing) — before assuming none are connected, run `ToolSearch` for keywords like `apfel`, `search-and-fetch`, or `4096`, don't just scan the visible tool list. `apfel-mcp-ddg-search` is explicitly excluded from this skill's routing — deliberately out of scope, not an oversight.

| Scenario | Tool | Limit | Cheatsheet |
| :--- | :--- | :--- | :--- |
| Search web + read page | `apfel-mcp-search-and-fetch` (e.g. `mcp__search-and-fetch__search`) | 1 call instead of 2. Cap ~5k chars. | [`references/apfel-mcp-search-and-fetch.md`](references/apfel-mcp-search-and-fetch.md) |
| Known URL | `apfel-mcp-url-fetch` | Strip DOM bloat. Cap 6k chars. | [`references/apfel-mcp-url-fetch.md`](references/apfel-mcp-url-fetch.md) |
| Local log/code/config | `apfel-mcp-fs` | Read-only, 6k-char cap, allowlisted — see cheatsheet. | [`references/apfel-mcp-fs.md`](references/apfel-mcp-fs.md) |

Every cheatsheet above includes the exact prompt text to use — naming the real tool explicitly matters, since the small on-device model sometimes invents a plausible-but-wrong tool name from loose natural language (symptom: `No MCP server provides tool 'X'`, where `X` isn't in the `mcp: ... - <tool>` line printed at startup).

**Hard rules:**
1. **Max 2 tool calls per turn.** Never loop searches.
2. **No retries** on HTTP error, SSRF block, or path rejection — report in 1 sentence.
3. **Out of scope:** whole-codebase refactors, file writes/edits, multi-site research — say so, don't force it.
4. **Never hallucinate** truncated code, brackets, or params.

## Output (always, apfel-mcp or not)

- 250 words max. Bullets/code blocks over prose.
- Content ends abruptly or shows `[TRUNCATED]`: don't invent the rest — state "Data truncated at 6k chars. Omitted section: [topic]." Truncation is final, retrying returns the same cap.
