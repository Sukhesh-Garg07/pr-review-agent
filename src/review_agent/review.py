"""The review pipeline: parse -> retrieve -> prompt -> provider -> render."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .diff_parser import parse_diff
from .prompt import build_prompt
from .providers import LLMProvider
from .retriever import CodebaseIndex, Chunk

CATEGORIES = ("bug", "missing_test", "style", "question")
_HEADINGS = {
    "bug": "Potential bugs",
    "missing_test": "Missing tests",
    "style": "Style and consistency",
    "question": "Questions for the author",
}


@dataclass
class Finding:
    category: str
    file: str
    message: str
    line: int | None = None


@dataclass
class Review:
    summary: str
    findings: list[Finding] = field(default_factory=list)
    context_chunks: list[Chunk] = field(default_factory=list)
    prompt: str = ""


def parse_review_json(raw: str) -> tuple[str, list[Finding]]:
    """Parse the provider's reply into (summary, findings).

    Tolerates a reply wrapped in prose or a code fence by extracting the
    outermost JSON object.
    """
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("provider reply did not contain a JSON object")
    data = json.loads(raw[start : end + 1])
    findings = []
    for item in data.get("findings", []):
        category = item.get("category", "question")
        if category not in CATEGORIES:
            category = "question"
        line = item.get("line")
        findings.append(
            Finding(
                category=category,
                file=str(item.get("file", "")),
                message=str(item.get("message", "")),
                line=int(line) if isinstance(line, (int, float)) else None,
            )
        )
    return str(data.get("summary", "")), findings


def render_markdown(review: Review) -> str:
    out = ["# Pull request review", "", "## Summary", "", review.summary, ""]
    for category in CATEGORIES:
        items = [f for f in review.findings if f.category == category]
        out.append(f"## {_HEADINGS[category]}")
        out.append("")
        if not items:
            out.append("None found.")
        for f in items:
            loc = f"`{f.file}`" + (f":{f.line}" if f.line else "")
            out.append(f"- {loc} -- {f.message}")
        out.append("")
    if review.context_chunks:
        out.append("## Context used")
        out.append("")
        for c in review.context_chunks:
            out.append(f"- `{c.path}` (lines {c.start_line}-{c.end_line})")
        out.append("")
    return "\n".join(out)


def run_review(
    diff_text: str,
    repo_path: str,
    provider: LLMProvider,
    top_k_per_file: int = 3,
) -> Review:
    changes = parse_diff(diff_text)
    index = CodebaseIndex(repo_path)
    context = index.context_for_changes(changes, top_k_per_file=top_k_per_file)
    prompt = build_prompt(diff_text, context)
    raw = provider.complete(prompt)
    summary, findings = parse_review_json(raw)
    return Review(summary=summary, findings=findings, context_chunks=context, prompt=prompt)
