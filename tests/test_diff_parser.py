from review_agent.diff_parser import parse_diff

DIFF = """\
diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -2,3 +2,4 @@
 import os
 
-def main():
+def main(verbose=False):
+    print("start")
     pass
diff --git a/tests/test_app.py b/tests/test_app.py
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -1,1 +1,3 @@
 def test_main():
+    assert True
+    assert True
"""


def test_parse_two_files():
    changes = parse_diff(DIFF)
    assert [c.path for c in changes] == ["src/app.py", "tests/test_app.py"]


def test_added_line_numbers_are_in_new_file_terms():
    changes = parse_diff(DIFF)
    added = changes[0].added_lines()
    assert [(ln.content, ln.new_lineno) for ln in added] == [
        ("def main(verbose=False):", 4),
        ('    print("start")', 5),
    ]


def test_deleted_lines_have_no_new_lineno():
    changes = parse_diff(DIFF)
    deleted = [ln for h in changes[0].hunks for ln in h.lines if ln.kind == "del"]
    assert len(deleted) == 1
    assert deleted[0].new_lineno is None
    assert deleted[0].old_lineno == 4


def test_is_test_file_detection():
    changes = parse_diff(DIFF)
    assert not changes[0].is_test_file
    assert changes[1].is_test_file


def test_header_only_entries_are_dropped():
    rename_only = (
        "diff --git a/old.py b/new.py\n"
        "similarity index 100%\n"
        "rename from old.py\n"
        "rename to new.py\n"
    )
    assert parse_diff(rename_only) == []
