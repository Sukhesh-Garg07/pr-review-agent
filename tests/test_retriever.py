from pathlib import Path

from review_agent.diff_parser import parse_diff
from review_agent.retriever import CodebaseIndex

DIFF = """\
diff --git a/pricing.py b/pricing.py
--- a/pricing.py
+++ b/pricing.py
@@ -10,3 +10,4 @@
 def order_total(lines):
     subtotal = sum(line_total(price, qty) for price, qty in lines)
     return subtotal * (1 + TAX_RATE)
+
+
+def apply_discount(total, percent):
+    return total * (1 - percent / 100)
"""


def _write(root: Path, name: str, text: str) -> None:
    (root / name).write_text(text, encoding="utf-8")


def _make_repo(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "pricing.py",
        '"""Pricing."""\n\nTAX_RATE = 0.2\n\n\n'
        "def line_total(unit_price, quantity):\n    return unit_price * quantity\n\n\n"
        "def order_total(lines):\n"
        "    subtotal = sum(line_total(price, qty) for price, qty in lines)\n"
        "    return subtotal * (1 + TAX_RATE)\n",
    )
    _write(
        tmp_path,
        "test_pricing.py",
        "from pricing import line_total, order_total\n\n\n"
        "def test_line_total():\n    assert line_total(10, 3) == 30\n",
    )
    _write(
        tmp_path,
        "cart.py",
        "from pricing import order_total\n\n\n"
        "class Cart:\n    def total(self, lines):\n        return order_total(lines)\n",
    )
    _write(tmp_path, "unrelated.py", "def greet(name):\n    return f'hello {name}'\n")


def test_index_covers_all_python_files(tmp_path):
    _make_repo(tmp_path)
    index = CodebaseIndex(tmp_path)
    assert {c.path for c in index.chunks} == {
        "pricing.py",
        "test_pricing.py",
        "cart.py",
        "unrelated.py",
    }


def test_retrieval_surfaces_related_files_and_excludes_changed_file(tmp_path):
    _make_repo(tmp_path)
    index = CodebaseIndex(tmp_path)
    changes = parse_diff(DIFF)
    context = index.context_for_changes(changes, top_k_per_file=3)
    paths = {c.path for c in context}
    assert "pricing.py" not in paths  # the diff already shows the changed file
    assert paths & {"test_pricing.py", "cart.py"}  # at least one genuinely related file
    assert "unrelated.py" not in paths


def test_retrieval_on_empty_repo(tmp_path):
    index = CodebaseIndex(tmp_path)
    assert index.retrieve("anything") == []
