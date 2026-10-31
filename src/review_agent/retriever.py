"""TF-IDF retrieval over a codebase.

The repository's Python sources are split into overlapping line-window
chunks and indexed with scikit-learn's TfidfVectorizer. For a changed
file, the query is built from the file's module name plus the lines the
diff adds, and the top matching chunks from *other* files (callers,
related modules, tests) are returned as review context.

Why TF-IDF and not embeddings: it needs no model downloads, no API key
and no GPU, it is fully deterministic, and for code -- where shared
identifiers matter more than paraphrase -- lexical overlap is a strong
signal. See the README for the trade-offs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".tox"}
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Python keywords appear in nearly every chunk, so as TF-IDF terms they
# match everything and drown out the identifiers that actually signal
# relatedness. They are dropped from the index (stop words).
_PYTHON_KEYWORDS = [
    "def", "return", "import", "from", "class", "if", "else", "elif",
    "for", "while", "try", "except", "finally", "with", "as", "pass",
    "lambda", "yield", "raise", "assert", "del", "global", "nonlocal",
    "and", "or", "not", "in", "is", "none", "true", "false", "self",
]


@dataclass
class Chunk:
    path: str  # repo-relative path
    start_line: int  # 1-based, inclusive
    end_line: int  # 1-based, inclusive
    text: str


def chunk_file(path: str, text: str, window: int = 50, overlap: int = 10) -> list[Chunk]:
    lines = text.splitlines()
    if not lines:
        return []
    step = max(1, window - overlap)
    chunks = []
    for start in range(0, len(lines), step):
        end = min(len(lines), start + window)
        chunks.append(
            Chunk(
                path=path,
                start_line=start + 1,
                end_line=end,
                text="\n".join(lines[start:end]),
            )
        )
        if end == len(lines):
            break
    return chunks


class CodebaseIndex:
    """A TF-IDF index over all Python files under a repository root."""

    def __init__(self, repo_root: str | Path):
        self.root = Path(repo_root)
        self.chunks: list[Chunk] = []
        for file_path in sorted(self.root.rglob("*.py")):
            rel = file_path.relative_to(self.root)
            if any(part in _SKIP_DIRS for part in rel.parts):
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            self.chunks.extend(chunk_file(rel.as_posix(), text))
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        if self.chunks:
            self._vectorizer = TfidfVectorizer(
                token_pattern=r"[A-Za-z_][A-Za-z0-9_]*",
                lowercase=True,
                sublinear_tf=True,
                stop_words=_PYTHON_KEYWORDS,
            )
            self._matrix = self._vectorizer.fit_transform(c.text for c in self.chunks)

    def __len__(self) -> int:
        return len(self.chunks)

    def query_for_change(self, change) -> str:
        """Build a retrieval query from a parsed FileChange."""
        module_tokens = _TOKEN_RE.findall(Path(change.path).stem)
        return " ".join(module_tokens) + "\n" + change.added_text()

    def retrieve(
        self, query: str, exclude_paths: set[str] | None = None, top_k: int = 4
    ) -> list[Chunk]:
        """Return the top_k chunks most similar to the query.

        Chunks from files in exclude_paths (typically the changed file
        itself, whose content the diff already shows) are skipped.
        """
        if not self.chunks or self._vectorizer is None:
            return []
        exclude = exclude_paths or set()
        q = self._vectorizer.transform([query])
        scores = cosine_similarity(q, self._matrix)[0]
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])
        out: list[Chunk] = []
        for i in ranked:
            if scores[i] <= 0:
                break
            chunk = self.chunks[i]
            if chunk.path in exclude:
                continue
            out.append(chunk)
            if len(out) >= top_k:
                break
        return out

    def context_for_changes(self, changes, top_k_per_file: int = 3) -> list[Chunk]:
        """Retrieve context chunks for every changed file, de-duplicated."""
        seen: set[tuple[str, int]] = set()
        context: list[Chunk] = []
        for change in changes:
            query = self.query_for_change(change)
            for chunk in self.retrieve(query, exclude_paths={change.path}, top_k=top_k_per_file):
                key = (chunk.path, chunk.start_line)
                if key not in seen:
                    seen.add(key)
                    context.append(chunk)
        return context
