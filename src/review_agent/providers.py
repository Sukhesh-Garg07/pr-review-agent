"""LLM providers.

A provider takes an assembled prompt and returns the model's raw text
reply (expected to be the JSON review described in the prompt). Two
implementations:

- AnthropicProvider: the real provider. Reads ANTHROPIC_API_KEY from
  the environment; the key is never hardcoded or logged.
- MockProvider: a deterministic, offline stand-in. It runs a small set
  of transparent heuristic checks over the diff section of the prompt
  and emits findings in the same JSON schema. It exists so the whole
  pipeline (parsing, retrieval, prompt assembly, rendering) can be
  developed, tested and evaluated without an API key. It is not a
  language model and its findings are only as good as its heuristics;
  the evaluation harness measures exactly that, honestly labelled.
"""

from __future__ import annotations

import json
import os
import re
from typing import Protocol


class LLMProvider(Protocol):
    name: str

    def complete(self, prompt: str) -> str:
        """Return the model's raw reply to the prompt."""
        ...


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4-5", max_tokens: int = 4096):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Export it, or use --mock to run offline."
            )
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "the 'anthropic' package is not installed; run: pip install anthropic"
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, prompt: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in message.content if block.type == "text")


_DIFF_FENCE_RE = re.compile(r"```diff\n(.*?)```", re.DOTALL)
_MUTABLE_DEFAULT_RE = re.compile(r"def\s+\w+\s*\([^)]*=\s*(\{\}|\[\]|dict\(\)|list\(\))")
_BARE_EXCEPT_RE = re.compile(r"^except\s*:")
_EVAL_RE = re.compile(r"\b(eval|exec)\s*\(")
_PRINT_RE = re.compile(r"^\s*print\s*\(")
_DEF_RE = re.compile(r"^(\+?)\s*def\s+(\w+)\s*\(")


def _extract_diff(prompt: str) -> str:
    m = _DIFF_FENCE_RE.search(prompt)
    return m.group(1) if m else ""


class MockProvider:
    """Deterministic offline provider based on explicit heuristics.

    Checks, applied to added lines of each changed file:
      * mutable default argument in a function signature -> bug
      * bare `except:` that swallows errors              -> bug
      * eval()/exec() on dynamic input                    -> bug
      * print() left in non-test library code             -> style
      * a source file changed with no test file changed  -> missing_test
      * a public function added/changed                   -> question
        (are existing callers in the retrieved context compatible?)
    """

    name = "mock"

    def complete(self, prompt: str) -> str:
        from .diff_parser import parse_diff

        diff_text = _extract_diff(prompt)
        changes = parse_diff(diff_text)
        findings: list[dict] = []

        changed_paths = {c.path for c in changes}
        any_test_changed = any(c.is_test_file for c in changes)
        context_has_test_for: dict[str, bool] = {}
        for path in changed_paths:
            stem = path.rsplit("/", 1)[-1].replace(".py", "")
            context_has_test_for[path] = f"test_{stem}" in prompt or f"{stem}_test" in prompt

        for change in changes:
            for ln in change.added_lines():
                text = ln.content
                loc = {"file": change.path, "line": ln.new_lineno}
                if _MUTABLE_DEFAULT_RE.search(text):
                    findings.append(
                        {
                            **loc,
                            "category": "bug",
                            "message": (
                                "mutable default argument: the default object is created once "
                                "and shared across calls, so mutations leak between calls. "
                                "Use None as the default and create the object inside."
                            ),
                        }
                    )
                if _BARE_EXCEPT_RE.match(text.strip()):
                    findings.append(
                        {
                            **loc,
                            "category": "bug",
                            "message": (
                                "bare except: swallows every exception, including real bugs; "
                                "catch a specific exception type and handle or re-raise it."
                            ),
                        }
                    )
                m = _EVAL_RE.search(text)
                if m:
                    findings.append(
                        {
                            **loc,
                            "category": "bug",
                            "message": (
                                f"{m.group(1)}() executes dynamically supplied code; if any part "
                                "of the expression is user-controlled this is a code injection "
                                "risk. Parse the expression instead."
                            ),
                        }
                    )
                if _PRINT_RE.match(text) and not change.is_test_file:
                    findings.append(
                        {
                            **loc,
                            "category": "style",
                            "message": "print() left in library code; use the logging module so output can be configured or silenced.",
                        }
                    )
                dm = _DEF_RE.match("+" + text)
                if dm and not dm.group(2).startswith("_") and not change.is_test_file:
                    findings.append(
                        {
                            **loc,
                            "category": "question",
                            "message": (
                                f"new or changed public function '{dm.group(2)}': is the "
                                "signature compatible with the existing callers shown in the "
                                "retrieved context?"
                            ),
                        }
                    )
            if not change.is_test_file and change.path.endswith(".py") and not any_test_changed:
                note = (
                    "an existing test file for this module appears in the retrieved context; "
                    "extend it to cover the change."
                    if context_has_test_for.get(change.path)
                    else "consider adding tests for this module."
                )
                findings.append(
                    {
                        "file": change.path,
                        "line": None,
                        "category": "missing_test",
                        "message": f"this change modifies {change.path} but the pull request adds or updates no tests; {note}",
                    }
                )

        files = ", ".join(sorted(changed_paths)) or "no files"
        review = {
            "summary": f"mock review of {len(changes)} changed file(s): {files}. "
            f"{len(findings)} finding(s) from deterministic heuristic checks.",
            "findings": findings,
        }
        return json.dumps(review, indent=2)
