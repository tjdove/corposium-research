"""Figure tables in ``docs/NOTE.md`` and ``docs/figures/README.md`` (Story 4.1 AC 4).

One parser, shared by ``tests/test_note_figures.py`` (the two lists match one-to-one) and
``scripts/check_note.py`` (the note cites what it lists, and nothing record-only).
"""

from __future__ import annotations

import re
from pathlib import Path

NOTE = Path("docs/NOTE.md")
FIGURES_README = Path("docs/figures/README.md")
FIGURE_LIST = "## Figure list (committed, `docs/figures/`)"
PNG = re.compile(r"`([A-Za-z0-9_]+\.png)`")


def section(text: str, heading: str) -> str:
    """The text from ``heading`` (a whole ``## `` line) to the next ``## `` heading."""
    lines = text.splitlines()
    start = lines.index(heading) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def table_files(section_text: str) -> list[str]:
    """The first ``*.png`` in each table row's file column (rows start with ``|``)."""
    files = []
    for row in section_text.splitlines():
        if row.startswith("|") and not row.startswith("|---"):
            found = PNG.findall(row)
            if found:
                files.append(found[0])
    return files


def note_sets(note: Path = NOTE) -> tuple[list[str], list[str]]:
    """``(in the note, record only)`` from NOTE.md's figure list."""
    rows = section(Path(note).read_text(encoding="utf-8"), FIGURE_LIST)
    in_note, record = [], []
    for row in rows.splitlines():
        if not row.startswith("|") or row.startswith("|---"):
            continue
        cells = [c.strip() for c in row.strip("|").split("|")]
        found = PNG.findall(cells[1]) if len(cells) > 2 else []
        if found:
            (record if cells[2] == "record only" else in_note).append(found[0])
    return in_note, record


def readme_sets(readme: Path = FIGURES_README) -> tuple[list[str], list[str]]:
    """``(figures in the note, record only)`` from docs/figures/README.md."""
    text = Path(readme).read_text(encoding="utf-8")
    return (
        table_files(section(text, "## Figures in the note")),
        table_files(section(text, "## Record only")),
    )
