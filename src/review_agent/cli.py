"""Command line interface.

Usage:
    review-agent --diff change.diff --repo path/to/repo [--mock]
    review-agent --demo [--mock]        # bundled sample diff + sample repo

Without --mock the Anthropic provider is used and ANTHROPIC_API_KEY
must be set in the environment. With --mock the deterministic offline
provider is used, which is what the tests and the demo run.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .providers import AnthropicProvider, MockProvider
from .review import render_markdown, run_review

_SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def _load_demo() -> tuple[str, str]:
    diff = (_SAMPLES / "sample.diff").read_text(encoding="utf-8")
    return diff, str(_SAMPLES / "sample_repo")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="review-agent", description=__doc__)
    parser.add_argument("--diff", help="path to a unified diff file")
    parser.add_argument("--repo", help="path to the repository the diff applies to")
    parser.add_argument("--demo", action="store_true", help="use the bundled sample diff and repo")
    parser.add_argument("--mock", action="store_true", help="use the deterministic offline provider")
    parser.add_argument("--model", default="claude-sonnet-4-5", help="Anthropic model (ignored with --mock)")
    parser.add_argument("--out-prefix", help="write <prefix>.md and <prefix>.json next to the printed review")
    args = parser.parse_args(argv)

    if args.demo:
        diff_text, repo_path = _load_demo()
    elif args.diff and args.repo:
        diff_text = Path(args.diff).read_text(encoding="utf-8")
        repo_path = args.repo
    else:
        parser.error("either --demo or both --diff and --repo are required")

    provider = MockProvider() if args.mock else AnthropicProvider(model=args.model)
    review = run_review(diff_text, repo_path, provider)

    markdown = render_markdown(review)
    print(markdown)
    if args.out_prefix:
        Path(args.out_prefix + ".md").write_text(markdown, encoding="utf-8")
        payload = {
            "summary": review.summary,
            "findings": [asdict(f) for f in review.findings],
            "context": [
                {"path": c.path, "start_line": c.start_line, "end_line": c.end_line}
                for c in review.context_chunks
            ],
        }
        Path(args.out_prefix + ".json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
