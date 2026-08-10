#!/usr/bin/env python3
"""Filter a build/app log down to errors, warnings, final status, timeline. Stdlib only.

Usage: log-filter.py [file]   (reads stdin if no file given)
       log-filter.py --selftest
"""
import re
import sys
from collections import OrderedDict

TS_RE = re.compile(r"\[?(\d{2}:\d{2}:\d{2})\]?")
LEVEL_RE = re.compile(r"\b(ERROR|WARN(?:ING)?|FAIL(?:ED)?|EXCEPTION)\b", re.IGNORECASE)
STATUS_RE = re.compile(r"\b(Build (?:failed|succeeded)|Success|Passed|Rolled back)\b.*", re.IGNORECASE)


def parse(text):
    lines = text.splitlines()
    errors = OrderedDict()  # message -> {count, location}
    warnings = OrderedDict()
    timeline = []
    final_status, final_ts = None, None

    for i, line in enumerate(lines):
        ts_match = TS_RE.search(line)
        ts = ts_match.group(1) if ts_match else None

        status_match = STATUS_RE.search(line)
        if status_match:
            # A "Build failed: N errors" summary line also matches LEVEL_RE (contains
            # "failed") — treat it as the final-status line only, not another error.
            final_status, final_ts = status_match.group(0), ts
            continue

        level_match = LEVEL_RE.search(line)
        if level_match:
            level = level_match.group(1).upper()
            msg = line[level_match.end():].strip(" :")
            loc = None
            for j in (i + 1, i + 2):
                if j < len(lines):
                    loc_match = re.search(r"([\w./-]+\.\w+):(\d+)", lines[j])
                    if loc_match:
                        loc = f"{loc_match.group(1)}:{loc_match.group(2)}"
                        break
            bucket = errors if level.startswith(("ERROR", "FAIL", "EXCEPTION")) else warnings
            key = msg or line.strip()
            if key in bucket:
                bucket[key]["count"] += 1
            else:
                bucket[key] = {"count": 1, "location": loc}
            if ts:
                timeline.append((ts, f"{level} {msg[:60]}"))

    return errors, warnings, timeline, final_status, final_ts


def render(errors, warnings, timeline, final_status, final_ts):
    out = ["## Build/Log Summary", "", "### Status"]
    out.append(f"{final_status or 'unknown'}" + (f" at {final_ts}" if final_ts else ""))

    out += ["", f"### Errors ({len(errors)})"]
    for n, (msg, info) in enumerate(errors.items(), 1):
        suffix = f" (x{info['count']})" if info["count"] > 1 else ""
        out.append(f"{n}. {msg}{suffix}")
        if info["location"]:
            out.append(f"   - Location: {info['location']}")

    out += ["", f"### Warnings ({len(warnings)})"]
    for n, (msg, info) in enumerate(warnings.items(), 1):
        suffix = f" (x{info['count']})" if info["count"] > 1 else ""
        out.append(f"{n}. {msg}{suffix}")

    out += ["", "### Timeline"]
    out += [f"- {ts} {event}" for ts, event in timeline] or ["- (none found)"]
    return "\n".join(out)


def run(text):
    return render(*parse(text))


def selftest():
    log = (
        "[12:34:56] Starting build...\n"
        "[12:35:15] ERROR: Cannot find module './token-colors.ts'\n"
        "  at src/components/Button/index.ts:3:1\n"
        "[12:35:16] Build failed: 1 error\n"
    )
    errors, warnings, _, final_status, _ = parse(log)
    assert len(errors) == 1, f"'Build failed: N errors' summary line leaked into errors: {errors}"
    assert "Cannot find module" in next(iter(errors))
    assert next(iter(errors.values()))["location"] == "src/components/Button/index.ts:3"
    assert final_status and final_status.lower().startswith("build failed")
    print("ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    args = [a for a in sys.argv[1:] if a != "--selftest"]
    text = open(args[0], encoding="utf-8").read() if args else sys.stdin.read()
    print(run(text))
