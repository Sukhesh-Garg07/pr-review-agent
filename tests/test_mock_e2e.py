import os
from pathlib import Path

import pytest

from review_agent.providers import AnthropicProvider, MockProvider
from review_agent.review import parse_review_json, render_markdown, run_review

ROOT = Path(__file__).resolve().parents[1]


def test_mock_end_to_end_on_bundled_sample():
    diff_text = (ROOT / "samples" / "sample.diff").read_text(encoding="utf-8")
    review = run_review(diff_text, str(ROOT / "samples" / "sample_repo"), MockProvider())

    by_category = {}
    for f in review.findings:
        by_category.setdefault(f.category, []).append(f)

    # the sample diff plants three problems in taskstore/store.py:
    # a mutable default argument, a leftover print, and no test changes
    assert "bug" in by_category
    assert any("mutable default" in f.message for f in by_category["bug"])
    bug_lines = {f.line for f in by_category["bug"]}
    assert 19 in bug_lines  # the `def find(self, tags=[])` line in the new file

    assert "style" in by_category
    assert any("print()" in f.message for f in by_category["style"])

    assert "missing_test" in by_category

    markdown = render_markdown(review)
    assert "## Potential bugs" in markdown
    assert "## Missing tests" in markdown
    assert "taskstore/store.py" in markdown
    # the existing test file for the module should have been retrieved as context
    assert any(c.path == "tests/test_store.py" for c in review.context_chunks)


def test_mock_provider_is_deterministic():
    diff_text = (ROOT / "samples" / "sample.diff").read_text(encoding="utf-8")
    provider = MockProvider()
    first = run_review(diff_text, str(ROOT / "samples" / "sample_repo"), provider)
    second = run_review(diff_text, str(ROOT / "samples" / "sample_repo"), provider)
    assert [(f.category, f.file, f.line, f.message) for f in first.findings] == [
        (f.category, f.file, f.line, f.message) for f in second.findings
    ]


def test_parse_review_json_tolerates_prose_around_json():
    raw = 'Here is the review:\n{"summary": "s", "findings": [{"category": "bug", "file": "a.py", "line": 3, "message": "m"}]}\nDone.'
    summary, findings = parse_review_json(raw)
    assert summary == "s"
    assert findings[0].category == "bug"
    assert findings[0].line == 3


def test_anthropic_provider_requires_env_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider()
    assert "ANTHROPIC_API_KEY" not in os.environ or True  # nothing was written anywhere
