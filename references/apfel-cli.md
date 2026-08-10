# `apfel` CLI cheatsheet

Base command for everything below. Verified against `apfel --help` (v1.9.1).

```
apfel [OPTIONS] <prompt>       Send a single prompt
apfel [OPTIONS] -- <prompt>    "--" ends options; prompt may start with "-"
apfel -f <file> <prompt>       Attach file content to prompt
apfel --chat                   Interactive conversation
apfel --stream <prompt>        Stream a single response
apfel --serve                  Start OpenAI-compatible HTTP server
apfel --count-tokens <prompt>  Preflight token count (no inference)
```

## Recommendations

| Goal | Use | Why |
| :--- | :--- | :--- |
| Read a known local file | `-f <path> "<prompt>"` | Attaches content directly — no MCP tool-call guess, no chance of a hallucinated tool name |
| Call a specific `apfel-mcp` tool | Name it explicitly in the prompt: `"Call the read_file tool with path=..."` | The CLI has no `--tool`/`--arg` flag; the model must parse the tool name from your prompt, and will invent one if you're vague |
| Check budget before spending it | `--count-tokens --strict <prompt>` | Exits 4 if over budget — cheaper than finding out mid-response |
| Need machine-parseable output | `--schema <path>` | Guarantees valid JSON matching your schema, instead of hoping the model formats it right |
| Trim wrapper prose from output | `--code` | Prints only the first fenced block, or the bare response if unfenced |
| Deterministic output for a test/demo | `--temperature 0 --seed <n>` | Reproducible across runs |

## Common mistake

```bash
# Wrong — vague prompt, model invents a tool name:
apfel --mcp $(which apfel-mcp-fs) "Read package.json"
# → tool: readPackageJson failed: No MCP server provides tool 'readPackageJson'

# Right — name the real tool, or skip the MCP round-trip entirely:
apfel --mcp $(which apfel-mcp-fs) "Call the read_file tool with path=package.json"
apfel -f package.json "Summarize this package.json"
```
