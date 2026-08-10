# use-apfel-mcp

Route small retrieval tasks through [apfel](https://github.com/Arthur-Ficial/apfel) instead of spending primary-model context on them.

This skill keeps low-value retrieval out of the primary model’s context. Web searches, URL fetches, log skims, document extraction, and other bounded tasks are handled locally by apfel, leaving the primary context and token usage for the work that actually needs it.

For Claude Code, Codex CLI, and Cursor.

Built on [apfel](https://github.com/Arthur-Ficial/apfel) and [apfel-mcp](https://github.com/Arthur-Ficial/apfel-mcp), both by [Arthur Ficial](https://github.com/Arthur-Ficial). This repo is the routing and preprocessing layer; it doesn't replace either project.

## Routing

| Task | Route |
| :--- | :--- |
| Code, JSON, logs, or long docs | Preprocess before they enter the primary context |
| Search the web and read a result | `apfel-mcp-search-and-fetch` |
| Read a known URL | `apfel-mcp-url-fetch` |
| Read a local file, log, or config | `apfel-mcp-fs` |
| Small, self-contained lookup | Delegate to `apfel` |
| Commit message, PR draft, regex, quick rewrite | Draft with `apfel`; review before using |
| Secrets, credentials, PII, or other sensitive local data | Delegate to `apfel` to keep the input on-device |
| Same transformation across many items | Loop `apfel` instead of making one primary-model call per item |
| Large branch diff | `~/.agents/skills/use-apfel-mcp/scripts/diff-chunk.sh main...HEAD` |
| Multi-file reasoning, edits, judgment, or production code | Keep it in the primary model |

## Why the preprocessing exists

Apfel intentionally has a small context window and bounded tool output. Raw input is truncated at roughly 6000 characters, so passing a large file directly can leave the model with the beginning of a document rather than the part that matters.

It also has a knowledge cutoff, so it isn't the right model for questions that depend on current or external knowledge, or for modern code generation — framework APIs, library versions, and current conventions drift faster than a local model's training data. What it's still good for is cutoff-agnostic, self-contained work where correctness depends on timeless logic, not what shipped last month:

- Regex, from a plain-English description
- Standard algorithm/data-structure logic — sorting, deduping, parsing a known format
- Text/data reformatting — JSON ↔ CSV ↔ Markdown table, case conversion, whitespace cleanup
- Stable shell/POSIX one-liners (`find`, `awk`, `sed`, `jq`)
- Core language syntax that hasn't materially changed — loops, string ops, stdlib basics
- Generic conceptual explanations — HTTP status codes, CLI flags, what an exception class generally means

And for text you provide to it directly, it's still capable at generation, rewriting, and summarization of that text — the input is already in front of it, so cutoff doesn't matter.

That’s where the split works well: use apfel for transforming text you already have; use the primary model when the task requires broader context, current knowledge, or deeper reasoning.

The scripts reduce that input before it reaches the model:

- `ast-skeleton.py` extracts code/JSON structure
- `log-filter.py` reduces logs to errors, warnings, status, and timeline
- `relevance-rank.py` selects relevant sections from long documents
- `diff-chunk.sh` breaks large diffs into small, independent summaries

These transformations are deterministic and require no LLM tokens.

The goal is simple: use a bounded local model where a bounded local model is enough, and keep larger-context reasoning for tasks that actually require it.

## Install

Clone into `~/.agents/skills/`:

```bash
git clone https://github.com/mike-at-redspace/use-apfel-mcp.git ~/.agents/skills/use-apfel-mcp
```

Then configure the runtime you use:

| Tool | Setup |
| :--- | :--- |
| **Claude Code** | `ln -s ../../.agents/skills/use-apfel-mcp ~/.claude/skills/use-apfel-mcp` |
| **Codex CLI** | Reads `~/.agents/skills/` directly |
| **Cursor** | Copy or symlink `.cursor/rules/use-apfel-mcp.mdc` into `.cursor/rules/`, or add it to User Rules |

The skill only provides the routing instructions. The corresponding `apfel` and `apfel-mcp` installations and MCP configuration still need to be available to the agent.

## What's included

- **[`SKILL.md`](SKILL.md)** — routing rules, delegation criteria, and tool usage
- **`scripts/ast-skeleton.py`** — reduces code/JSON to signatures, exports, and dependencies
- **`scripts/log-filter.py`** — reduces logs to relevant errors, warnings, status, and timeline
- **`scripts/relevance-rank.py`** — selects the most relevant sections of a long document
- **`scripts/diff-chunk.sh`** — breaks a large branch diff into bounded per-file summaries, then groups the results
- **`references/`** — per-tool notes with limits and example invocations

Run the script self-tests:

```bash
SKILL=~/.agents/skills/use-apfel-mcp
python3 "$SKILL/scripts/ast-skeleton.py" --selftest
```

Example (commands work from any directory — the agent's shell `cwd` is usually your project root, not the skill folder, so paths below are absolute):

```bash
cat src/Button.tsx | python3 "$SKILL/scripts/ast-skeleton.py"
python3 "$SKILL/scripts/log-filter.py" build.log
python3 "$SKILL/scripts/relevance-rank.py" "OKLCH color config" < docs.md
```

For PDF, Office, or HTML input, pipe the content through [`markitdown`](https://github.com/microsoft/markitdown) first. If `markitdown` is installed, the skill can detect and use it; otherwise it reports the missing dependency rather than attempting to read the raw binary.

## Limitations

- `apfel-mcp-fs` is read-only, operates on one file at a time, and has a 6000-character limit. Paths are restricted by `APFEL_MCP_FS_ROOTS`.
- The `apfel` CLI does not expose an explicit tool-call flag. When using MCP through the CLI, name the intended tool explicitly or use `-f <path>` to avoid the MCP round-trip. See [`references/apfel-cli.md`](references/apfel-cli.md).
- The preprocessing scripts don't parse YAML.
- Apfel runs on-device and doesn't require API keys. See the upstream [apfel README](https://github.com/Arthur-Ficial/apfel) for its current capabilities and configuration.

## License

MIT
