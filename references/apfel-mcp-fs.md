# `apfel-mcp-fs` cheatsheet

Read-only local file reader for apfel's 4096-token window. Not a general filesystem tool.

## Exact call text

```bash
APFEL_MCP_FS_ROOTS="$HOME/path/to/project" \
  apfel --mcp $(which apfel-mcp-fs) "Call the read_file tool with path=package.json"
```

Name the tool (`read_file`) explicitly — a vague prompt like `"Read package.json"` risks the model inventing a tool name instead (symptom: `No MCP server provides tool 'X'`). If you already know the local path, skip the MCP round-trip entirely:

```bash
apfel -f package.json "Summarize this package.json"
```

## Caveats

- **No writes.** No create, edit, move, rename, or delete — reads only. The on-device model is refusal-heavy on destructive file ops and the 4096-token context can't hold enough state to organize a folder safely. Point a bigger model/agent at the filesystem for anything write-shaped.
- **One file at a time, hard-capped at 6000 chars (~1500 tokens).** A large file is truncated with a visible suffix — you get the first slice, not the whole thing. Run it through `scripts/ast-skeleton.py` or `scripts/log-filter.py` (see [`SKILL.md`](../SKILL.md)) *before* reading raw instead of relying on the tool's own truncation to land on the useful part.
- **Text only.** Files containing NUL bytes are refused outright rather than dumped in as garbage — don't retry, it'll refuse the same way every time.
- **Allowlisted.** Reads are confined to `APFEL_MCP_FS_ROOTS` (colon-separated absolute paths, defaults to CWD). Paths outside — including via `..` or a symlink that resolves outside — are refused. A rejected read means the allowlist is working, not a bug to route around.

## Recommendation

Set `APFEL_MCP_FS_ROOTS` to exactly the directories you want apfel to see — don't default to CWD if you're calling from somewhere broader than the project root.
