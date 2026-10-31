"""Evaluation harness for the review pipeline (mock mode).

For each case in cases.json there is a tiny repository and a diff with
one deliberately planted issue. The harness runs the full pipeline
(diff parsing -> TF-IDF retrieval -> prompt assembly -> mock provider)
and checks two things per case:

  retrieval hit -- did retrieval surface at least one of the context
                   files a human reviewer would want to see?
  issue surfaced -- does the mock review contain a finding in the
                    expected category whose message names the planted
                    pattern?

What this measures, honestly: the coverage of the retrieval and
prompt-assembly stages plus the mock provider's deterministic checks.
It does NOT measure language-model review quality; that would need a
labelled set of real pull requests and a real provider. Run:

    python eval/run_eval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from review_agent.providers import MockProvider  # noqa: E402
from review_agent.review import run_review  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent


def main() -> int:
    spec = json.loads((EVAL_DIR / "cases.json").read_text(encoding="utf-8"))
    provider = MockProvider()
    rows = []
    for case in spec["cases"]:
        case_dir = EVAL_DIR / "cases" / case["name"]
        diff_text = (case_dir / "change.diff").read_text(encoding="utf-8")
        review = run_review(diff_text, str(case_dir / "repo"), provider)

        retrieved = {c.path for c in review.context_chunks}
        retrieval_hit = bool(retrieved & set(case["expected_context_files"]))
        surfaced = any(
            f.category == case["expected_category"]
            and f.file == case["changed_file"]
            and case["expected_keyword"].lower() in f.message.lower()
            for f in review.findings
        )
        rows.append((case["name"], retrieval_hit, surfaced, sorted(retrieved)))

    print(f"{'case':<18} {'retrieval':<10} {'issue surfaced':<15} retrieved context")
    for name, hit, surfaced, retrieved in rows:
        print(f"{name:<18} {'HIT' if hit else 'miss':<10} {'yes' if surfaced else 'NO':<15} {', '.join(retrieved)}")
    n = len(rows)
    hits = sum(1 for r in rows if r[1])
    surfaced = sum(1 for r in rows if r[2])
    print()
    print(f"retrieval hit rate: {hits}/{n}")
    print(f"planted issues surfaced by the mock pipeline: {surfaced}/{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
