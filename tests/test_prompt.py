from review_agent.prompt import build_prompt
from review_agent.retriever import Chunk

DIFF = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,1 +1,2 @@\n x = 1\n+y = 2\n"


def test_prompt_contains_diff_and_schema():
    prompt = build_prompt(DIFF, [])
    assert "```diff" in prompt
    assert "+y = 2" in prompt
    assert '"findings"' in prompt
    assert '"missing_test"' in prompt
    assert "(no relevant context retrieved)" in prompt


def test_prompt_includes_context_with_locations():
    chunk = Chunk(path="tests/test_a.py", start_line=3, end_line=9, text="def test_a():\n    pass")
    prompt = build_prompt(DIFF, [chunk])
    assert "### tests/test_a.py (lines 3-9)" in prompt
    assert "def test_a():" in prompt
