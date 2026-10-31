"""Unified diff parsing.

Parses `git diff` output into structured file changes with per-line
kinds and new-file line numbers, so findings can point at exact lines
in the post-change file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass
class DiffLine:
    kind: str  # "context", "add", or "del"
    content: str  # line text without the leading +/-/space marker
    new_lineno: int | None = None  # line number in the new file (None for deletions)
    old_lineno: int | None = None


@dataclass
class Hunk:
    old_start: int
    new_start: int
    lines: list[DiffLine] = field(default_factory=list)


@dataclass
class FileChange:
    old_path: str | None
    new_path: str | None
    hunks: list[Hunk] = field(default_factory=list)

    @property
    def path(self) -> str:
        """Path of the file in the new revision (falls back to old path)."""
        return self.new_path or self.old_path or ""

    @property
    def is_test_file(self) -> bool:
        p = self.path.replace("\\", "/")
        parts = p.split("/")
        return (
            any(part in ("test", "tests") for part in parts)
            or parts[-1].startswith("test_")
            or parts[-1].endswith("_test.py")
        )

    def added_lines(self) -> list[DiffLine]:
        return [ln for h in self.hunks for ln in h.lines if ln.kind == "add"]

    def added_text(self) -> str:
        return "\n".join(ln.content for ln in self.added_lines())


def _strip_prefix(path: str) -> str | None:
    path = path.strip()
    if path == "/dev/null":
        return None
    if path.startswith(("a/", "b/")):
        path = path[2:]
    return path


def parse_diff(diff_text: str) -> list[FileChange]:
    """Parse unified diff text into a list of FileChange objects."""
    changes: list[FileChange] = []
    current: FileChange | None = None
    hunk: Hunk | None = None
    old_no = new_no = 0

    for raw in diff_text.splitlines():
        if raw.startswith("diff --git "):
            current = FileChange(old_path=None, new_path=None)
            changes.append(current)
            hunk = None
            continue
        if current is None:
            continue
        if raw.startswith("--- "):
            current.old_path = _strip_prefix(raw[4:])
            continue
        if raw.startswith("+++ "):
            current.new_path = _strip_prefix(raw[4:])
            continue
        m = _HUNK_RE.match(raw)
        if m:
            old_no = int(m.group(1))
            new_no = int(m.group(3))
            hunk = Hunk(old_start=old_no, new_start=new_no)
            current.hunks.append(hunk)
            continue
        if hunk is None:
            continue
        if raw.startswith("\\"):  # "\ No newline at end of file"
            continue
        marker, content = (raw[:1], raw[1:]) if raw else (" ", "")
        if marker == "+":
            hunk.lines.append(DiffLine("add", content, new_lineno=new_no, old_lineno=None))
            new_no += 1
        elif marker == "-":
            hunk.lines.append(DiffLine("del", content, new_lineno=None, old_lineno=old_no))
            old_no += 1
        else:
            hunk.lines.append(DiffLine("context", content, new_lineno=new_no, old_lineno=old_no))
            old_no += 1
            new_no += 1

    # drop header-only entries (e.g. pure renames with no hunks)
    return [c for c in changes if c.hunks]
