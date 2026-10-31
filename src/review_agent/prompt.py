"""Prompt assembly: diff + retrieved context + output schema."""

from __future__ import annotations

from .retriever import Chunk

SCHEMA_INSTRUCTIONS = """\
Respond with a single JSON object and nothing else, in exactly this shape:
{
  "summary": "two or three sentences on what the change does and its overall risk",
  "findings": [
    {"category": "bug",          "file": "path/in/repo.py", "line": 42, "message": "what is wrong and why"},
    {"category": "missing_test", "file": "path/in/repo.py", "line": null, "message": "what behaviour is untested"},
    {"category": "style",        "file": "path/in/repo.py", "line": 7,  "message": "what is inconsistent and with what"},
    {"category": "question",     "file": "path/in/repo.py", "line": 13, "message": "a concrete question for the author"}
  ]
}
Rules:
- Every finding must name the file it refers to; use the line number in the
  new version of the file when the finding is about a specific added line.
- Ground bug and style findings in the diff or in the retrieved context;
  do not invent APIs or callers that are not shown.
- Prefer a few high-confidence findings over many speculative ones.
"""


def build_prompt(diff_text: str, context_chunks: list[Chunk]) -> str:
    parts = [
        "You are a senior engineer reviewing a pull request. The diff under "
        "review is followed by excerpts retrieved from the same codebase "
        "(callers, related modules and tests) so you can judge the change "
        "against how the code is actually used.",
        "",
        "## Pull request diff",
        "```diff",
        diff_text.rstrip(),
        "```",
        "",
        "## Retrieved context from the codebase",
    ]
    if context_chunks:
        for chunk in context_chunks:
            parts.append(f"### {chunk.path} (lines {chunk.start_line}-{chunk.end_line})")
            parts.append("```python")
            parts.append(chunk.text)
            parts.append("```")
            parts.append("")
    else:
        parts.append("(no relevant context retrieved)")
        parts.append("")
    parts.append("## Output format")
    parts.append(SCHEMA_INSTRUCTIONS)
    return "\n".join(parts)
