"""Story 4.1 AC 4: the note's figure list and docs/figures/README.md match one-to-one."""

import json
import re
from pathlib import Path

NOTE = Path("docs/NOTE.md")
FIGURES_README = Path("docs/figures/README.md")
MANIFEST = Path("docs/figures/manifest.json")
PNG = re.compile(r"`([A-Za-z0-9_]+\.png)`")


def _section(text: str, heading: str) -> str:
    """The text from ``heading`` (a whole ``## `` line) to the next ``## `` heading."""
    lines = text.splitlines()
    start = lines.index(heading) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def _table_files(section: str) -> list[str]:
    """The first ``*.png`` in each table row's file column (rows start with ``|``)."""
    files = []
    for row in section.splitlines():
        if row.startswith("|") and not row.startswith("|---"):
            found = PNG.findall(row)
            if found:
                files.append(found[0])
    return files


def note_sets() -> tuple[list[str], list[str]]:
    """``(in the note, record only)`` from NOTE.md's figure list."""
    section = _section(
        NOTE.read_text(encoding="utf-8"), "## Figure list (committed, `docs/figures/`)"
    )
    note, record = [], []
    for row in section.splitlines():
        if not row.startswith("|") or row.startswith("|---"):
            continue
        cells = [c.strip() for c in row.strip("|").split("|")]
        found = PNG.findall(cells[1]) if len(cells) > 2 else []
        if found:
            (record if cells[2] == "record only" else note).append(found[0])
    return note, record


def readme_sets() -> tuple[list[str], list[str]]:
    text = FIGURES_README.read_text(encoding="utf-8")
    return (
        _table_files(_section(text, "## Figures in the note")),
        _table_files(_section(text, "## Record only")),
    )


def test_note_and_readme_note_sets_match_one_to_one():
    note, _ = note_sets()
    readme, _ = readme_sets()
    assert len(note) == len(set(note)) and len(readme) == len(set(readme))
    assert sorted(note) == sorted(readme)


def test_note_and_readme_record_sets_match():
    _, note = note_sets()
    _, readme = readme_sets()
    assert sorted(note) == sorted(readme) == sorted(
        ["threshold_surface_par.png", "threshold_surface.png", "time_to_parity.png",
         "holder_exit.png"]
    )  # fmt: skip


def test_every_committed_figure_is_in_exactly_one_set():
    note, record = readme_sets()
    manifest = json.loads(MANIFEST.read_text())
    figures = {e["file"] for k, e in manifest.items() if k != "code_hash"}
    assert not set(note) & set(record)
    assert sorted(note + record) == sorted(figures)


def test_every_figure_has_one_caption_in_its_section():
    text = FIGURES_README.read_text(encoding="utf-8")
    note, record = readme_sets()
    for heading, files in (("## Captions: figures in the note", note),
                           ("## Captions: record only", record)):  # fmt: skip
        captions = re.findall(r"^\*\*`([A-Za-z0-9_]+\.png)`\.\*\*", _section(text, heading), re.M)
        assert captions == files  # same order as the table, one each


def test_captions_carry_no_story_or_adr_numbers():
    text = FIGURES_README.read_text(encoding="utf-8")
    captions = text[text.index("## Captions: figures in the note") :]
    assert not re.search(r"\bStory \d|\bADR-?\d", captions)


def test_parser_reads_a_changed_list(tmp_path, monkeypatch):
    """A figure dropped from one side breaks the match (the test is not vacuous)."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs" / "figures").mkdir(parents=True)
    (tmp_path / "docs" / "NOTE.md").write_text(
        "## Figure list (committed, `docs/figures/`)\n\n| # | file | section | f | s |\n"
        "|---|---|---|---|---|\n| 1 | `a.png` | 3 | F | ok |\n"
        "| — | `b.png` | record only | F | x |\n"
        "\n## Word budget\n"
    )
    (tmp_path / "docs" / "figures" / "README.md").write_text(
        "## Figures in the note\n\n| Figure | § |\n|---|---|\n| [`a.png`](a.png) | 3 |\n"
        "| [`c.png`](c.png) | 4 |\n\n## Record only\n\n| Figure |\n|---|\n| [`b.png`](b.png) |\n"
    )
    assert note_sets() == (["a.png"], ["b.png"])
    assert readme_sets() == (["a.png", "c.png"], ["b.png"])
