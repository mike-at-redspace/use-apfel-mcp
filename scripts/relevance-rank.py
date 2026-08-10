#!/usr/bin/env python3
"""Rank a doc's paragraphs by relevance to a query, return top 3. Stdlib only.

Usage: relevance-rank.py "<query>" [file]   (reads stdin if no file given)
       relevance-rank.py --selftest
"""
import re
import sys

HEADER_RE = re.compile(r"^#+\s*(.+)$")


def split_sections(text):
    """[(title, body)] — body is text under the nearest preceding header."""
    sections, title, buf = [], "(untitled)", []
    for line in text.splitlines():
        h = HEADER_RE.match(line)
        if h:
            if buf and "".join(buf).strip():
                sections.append((title, "\n".join(buf).strip()))
            title, buf = h.group(1).strip(), []
        else:
            buf.append(line)
    if buf and "".join(buf).strip():
        sections.append((title, "\n".join(buf).strip()))
    return [(t, b) for t, b in sections if b]


def score(query_terms, text):
    words = re.findall(r"\w+", text.lower())
    if not words:
        return 0.0
    hits = sum(words.count(t) for t in query_terms)
    coverage = sum(1 for t in query_terms if t in words) / len(query_terms)
    density = hits / len(words)
    return coverage * 0.7 + min(density * 10, 1.0) * 0.3


def run(query, text, top_n=3):
    terms = re.findall(r"\w+", query.lower())
    sections = split_sections(text)
    scored = sorted(((score(terms, body), title, body) for title, body in sections), key=lambda x: -x[0])
    top = [s for s in scored if s[0] > 0][:top_n]
    max_score = top[0][0] if top else 1.0

    out = [f'## Relevance Ranking: "{query}"', "", "### Top Matches", ""]
    for i, (raw, title, body) in enumerate(top, 1):
        out.append(f"#### {i}. {title} (score: {raw / max_score:.2f})")
        out.append(body)
        out.append("")
    if not top:
        out.append("(no paragraph matched the query terms)")
    out += ["---", "**Note:** Ranked by term overlap + coverage. Full document available in source."]
    return "\n".join(out)


def selftest():
    doc = (
        "## Installation\n\nRun npm install.\n\n"
        "## OKLCH Syntax\n\nOKLCH stands for Oklab Chroma Hue. Format: oklch(l c h).\n\n"
        "## Theme Overrides\n\nCreate a brand-name.json file to override colors.\n"
    )
    out = run("OKLCH color config", doc)
    assert "OKLCH Syntax" in out.split("Theme Overrides")[0]  # OKLCH section ranks first
    print("ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    args = [a for a in sys.argv[1:] if a != "--selftest"]
    if not args:
        sys.exit("usage: relevance-rank.py \"<query>\" [file]")
    query, rest = args[0], args[1:]
    text = open(rest[0], encoding="utf-8").read() if rest else sys.stdin.read()
    print(run(query, text))
