# use-apfel-mcp

Stop spending your primary model's context on trivial lookups.

This skill teaches your agent to route bounded retrieval — a URL fetch, a log skim, a doc question, a single-file read — through [`apfel`](https://github.com/Arthur-Ficial/apfel)'s on-device model and a handful of deterministic compression scripts, and keep the expensive model's tokens for work that actually needs them. Use the big model for reasoning. Use apfel for "what was that URL again?"

Skill for Claude Code, Codex CLI, and Cursor. Built on [apfel](https://github.com/Arthur-Ficial/apfel) + [apfel-mcp](https://github.com/Arthur-Ficial/apfel-mcp), both by [Arthur Ficial](https://github.com/Arthur-Ficial) — this repo is the routing/compression layer in front of them, not a replacement. `apfel` also runs standalone for plenty outside an agent session — clipboard rewrites ([apfel-clip](https://github.com/Arthur-Ficial/apfel-clip)), a hotkey overlay ([apfel-quick](https://github.com/Arthur-Ficial/apfel-quick)), on-device OCR ([auge](https://github.com/Arthur-Ficial/auge)), speech-to-text ([ohr](https://github.com/Arthur-Ficial/ohr)) — see apfel's own README for that catalog; this one stays scoped to what an agent does with it.

## Routing, in one table

| Task | Route |
| :--- | :--- |
| Code/JSON file, log, or long doc about to enter context | Compress first — `scripts/ast-skeleton.py` / `log-filter.py` / `relevance-rank.py` |
| Search the web + read the result | `apfel-mcp-search-and-fetch` |
| Known URL | `apfel-mcp-url-fetch` |
| Local file/log/config read | `apfel-mcp-fs` |
| Trivial single-file lookup, tokens are the point | Delegate the whole task to `apfel` |
| Commit message, PR draft, regex, quick rewrite — drafting, not deciding | Delegate to `apfel` as a first pass, you still review it |
| Multi-file reasoning, edits, anything needing judgment | Normal tools — apfel has no memory of your repo and a 4096-token window |

`apfel-mcp-ddg-search` exists upstream but is deliberately left out of this routing — not an oversight. Full per-tool detail (exact call text, limits): [`SKILL.md`](SKILL.md) + [`references/`](references/).

## Why this exists

Apfel's context window is tiny on purpose. It truncates raw input at ~6000 chars — that's a feature, not a bug, but it means a raw file/log/doc dump lands you the *first* slice, not the *useful* slice. The scripts here extract signal deterministically — 0 LLM tokens, <100ms — before that truncation ever happens.

Not for whole-codebase analysis or deep research. That's what your primary model is still for.

## Install

Clone into `~/.agents/skills/` — the canonical, cross-runtime location — then symlink for whichever tool you use:

```bash
git clone https://github.com/mike-at-redspace/use-apfel-mcp.git ~/.agents/skills/use-apfel-mcp
```

| Tool | Setup |
| :--- | :--- |
| **Claude Code** | `ln -s ../../.agents/skills/use-apfel-mcp ~/.claude/skills/use-apfel-mcp` |
| **Codex CLI** | Nothing — reads `~/.agents/skills/` natively |
| **Cursor** | Copy/symlink `.cursor/rules/use-apfel-mcp.mdc` into your project's `.cursor/rules/`, or paste it into Settings → Rules → User Rules for a global setup |

## What's inside

- **[SKILL.md](SKILL.md)** — the decision rules: when to preprocess, when to delegate a whole task to `apfel`, the tool-routing table
- **`scripts/ast-skeleton.py`** — code/JSON → signatures, exports, deps (~150 tokens); regex fallback if the file has a syntax error
- **`scripts/log-filter.py`** — raw log → deduped errors, warnings, final status, timeline
- **`scripts/relevance-rank.py`** — long doc → top 3 paragraphs matching a query, scored
- **`references/`** — one cheatsheet per apfel/apfel-mcp tool, with exact call text

```bash
python3 scripts/ast-skeleton.py --selftest   # every script self-checks
cat src/Button.tsx | python3 scripts/ast-skeleton.py
python3 scripts/log-filter.py build.log
python3 scripts/relevance-rank.py "OKLCH color config" < docs.md
```

For PDF/Office/HTML input, the scripts expect text/markdown — pipe through [`markitdown`](https://github.com/microsoft/markitdown) first (`pipx install markitdown`, not bundled here).

## Limitations, up front

- `apfel-mcp-fs` is read-only, one file at a time, 6000-char hard cap, allowlisted to `APFEL_MCP_FS_ROOTS`. Not a general filesystem tool — see [`references/apfel-mcp-fs.md`](references/apfel-mcp-fs.md).
- The `apfel` CLI has no explicit tool-call flag. A vague prompt lets the on-device model invent a tool name that doesn't exist (`No MCP server provides tool 'X'`) — name the tool explicitly, or use `-f <path>` to skip the MCP round-trip. See [`references/apfel-cli.md`](references/apfel-cli.md).
- No YAML support in the scripts — Python's stdlib has no YAML parser.
- Free and on-device (no API keys, no cloud) — that much is verifiable from apfel's own README. Making a bigger claim than that (e.g. "greener") isn't backed by anything here, so we don't.

## License

MIT
