"""Story 4.2: scripts/check_note.py, the note's figures, freeze tag and fitted numbers."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("scripts").resolve()))

import check_note  # noqa: E402

NOTE = """# A note

Code frozen at `v0.9-freeze`.

![Figure 1](figures/a.png)

The trough is
−1,138 bps. The buyer's capital, $2.15B, is 0.79× the attack. A ladder gives
$2.54B (0.94×) and −1,323 bps. Half-life 1.4 h. Pool depth D\\*.
See the [budget figure](figures/b.png).

## Figure list (committed, `docs/figures/`)

| # | file | section | finding(s) | status |
|---|---|---|---|---|
| 1 | `a.png` | 3 | F-1 | final |
| — | `b.png` | 4 | F-2 | final |
| — | `r.png` | record only | F-3 | not in the note |

## Change Log
"""

README = """# Figures

## Figures in the note

| Figure | Note § |
|---|---|
| [`a.png`](a.png) | 3 |
| [`b.png`](b.png) | 4 |

## Record only

| Figure | Why kept |
|---|---|
| [`r.png`](r.png) | superseded |
"""

FITS = {
    "holder-single.json": {
        "c_star": 9, "c_star_usd": 2150500078,
        "runs": [{"holder_capital": 8, "max_depeg_bps": -1608.6},
                 {"holder_capital": 9, "max_depeg_bps": -1137.8173865104236}],
    },
    "holder-ladder-b.json": {
        "c_star": 10, "c_star_usd": 2541499922,
        "runs": [{"holder_capital": 10, "max_depeg_bps": -1323.270334147425}],
    },
    "reversion.json": {"half_life_h": 1.4128396007529505},
    "depth.json": {"d_star": 16666667},
}  # fmt: skip


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True, capture_output=True,
    )  # fmt: skip


def make_repo(tmp_path: Path, note: str = NOTE, git: bool = True) -> list[str]:
    """A note, figures, manifest, README and fits under ``tmp_path``, committed and tagged
    ``v0.9-freeze`` when ``git``; returns the check's arguments."""
    docs = tmp_path / "docs"
    (docs / "figures").mkdir(parents=True)
    (docs / "NOTE.md").write_text(note, encoding="utf-8")
    for name in ("a", "b", "r"):
        (docs / "figures" / f"{name}.png").write_bytes(b"png")
    manifest = {"code_hash": "c0de"} | {n: {"file": f"{n}.png"} for n in ("a", "b", "r")}
    (docs / "figures" / "manifest.json").write_text(json.dumps(manifest))
    (docs / "figures" / "README.md").write_text(README)
    fits = tmp_path / "fits"
    fits.mkdir()
    for name, result in FITS.items():
        (fits / name).write_text(json.dumps({"result": result}))
    if git:
        _git(tmp_path, "init", "-q")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-q", "-m", "freeze")
        _git(tmp_path, "tag", "-a", "v0.9-freeze", "-m", "freeze")
    return ["--note", str(docs / "NOTE.md"), "--manifest",
            str(docs / "figures" / "manifest.json"), "--fits", str(fits)]  # fmt: skip


def run(args, capsys):
    code = check_note.main(args)
    out = capsys.readouterr()
    return code, out.out, out.err


def test_synthetic_note_passes_with_one_ok_line_per_check(tmp_path, capsys):
    code, out, err = run(make_repo(tmp_path), capsys)
    assert code == 0, err
    lines = out.splitlines()
    assert [ln.split(":")[2].strip() for ln in lines] == ["figures", "cited", "freeze", "numbers"]
    assert all(ln.startswith("note-check: ok: ") for ln in lines)
    assert "numbers: 8 fitted values" in out and err == ""


def test_missing_figure_fails(tmp_path, capsys):
    args = make_repo(tmp_path, NOTE.replace("figures/a.png", "figures/gone.png"))
    code, _, err = run(args, capsys)
    assert code == 1
    assert "figures/gone.png is cited but not on disk" in err
    assert "figures/gone.png is cited but not a key in the manifest" in err


def test_figure_on_disk_but_not_in_manifest_fails(tmp_path, capsys):
    args = make_repo(tmp_path)
    (tmp_path / "docs" / "figures" / "extra.png").write_bytes(b"png")
    note = Path(args[1])
    note.write_text(note.read_text() + "\n![x](figures/extra.png)\n")
    code, _, err = run(args, capsys)
    assert code == 1 and "figures/extra.png is cited but not a key in the manifest" in err
    assert "not on disk" not in err


def test_listed_but_uncited_figure_fails(tmp_path, capsys):
    args = make_repo(tmp_path, NOTE.replace("See the [budget figure](figures/b.png).", ""))
    code, _, err = run(args, capsys)
    assert code == 1
    assert "cited: b.png is in the figure list but never cited in the body" in err


def test_a_citation_only_in_the_figure_list_does_not_count(tmp_path, capsys):
    note = NOTE.replace("See the [budget figure](figures/b.png).", "").replace(
        "| — | `b.png` |", "| — | [`b.png`](figures/b.png) |"
    )
    code, _, err = run(make_repo(tmp_path, note), capsys)
    assert code == 1 and "b.png is in the figure list but never cited" in err


def test_record_only_cited_fails(tmp_path, capsys):
    args = make_repo(tmp_path, NOTE.replace("Pool depth", "See [r](figures/r.png). Pool depth"))
    code, _, err = run(args, capsys)
    assert code == 1 and "cited: r.png is record only" in err


def test_wrong_number_fails(tmp_path, capsys):
    args = make_repo(tmp_path, NOTE.replace("$2.15B", "$2.16B"))
    code, out, err = run(args, capsys)
    assert code == 1
    assert "numbers: holder-single.json believers' capital C* is $2.15B" in err
    assert "ok: figures" in out and "ok: numbers" not in out


def test_wrong_trough_and_half_life_fail(tmp_path, capsys):
    note = NOTE.replace("−1,323", "−1,324").replace("1.4 h", "1.5 h")
    code, _, err = run(make_repo(tmp_path, note), capsys)
    assert code == 1
    assert "ladder B trough at C* is -1,323 bps" in err
    assert "calm reference half-life is 1.4 h" in err


def test_missing_fit_record_fails(tmp_path, capsys):
    args = make_repo(tmp_path)
    (Path(args[5]) / "reversion.json").unlink()
    code, _, err = run(args, capsys)
    assert code == 1 and "reversion.json is missing" in err


def test_depth_symbol_missing_fails_and_value_printed_warns(tmp_path, capsys):
    code, _, err = run(make_repo(tmp_path, NOTE.replace("D\\*", "the depth")), capsys)
    assert code == 1 and "quoted as the symbol D*" in err

    code, out, err = run(make_repo(tmp_path / "w", NOTE + "\nD* is 16,666,667.\n"), capsys)
    assert code == 0 and "WARNING: numbers: the note prints D* as 16,666,667" in err


def test_freeze_tag_on_other_code_fails(tmp_path, capsys):
    args = make_repo(tmp_path)
    manifest = Path(args[3])
    manifest.write_text(manifest.read_text().replace("c0de", "beef"))
    code, _, err = run(args, capsys)
    assert code == 1
    assert "freeze: v0.9-freeze" in err and "code_hash c0de, the working tree's has beef" in err


def test_freeze_tag_missing_fails(tmp_path, capsys):
    code, _, err = run(make_repo(tmp_path, NOTE.replace("v0.9-freeze", "v0.8-freeze")), capsys)
    assert code == 1 and "tag v0.8-freeze does not resolve" in err


def test_note_naming_no_tag_fails(tmp_path, capsys):
    code, _, err = run(make_repo(tmp_path, NOTE.replace("`v0.9-freeze`", "the tag")), capsys)
    assert code == 1 and "must name one freeze tag, found none" in err


def test_freeze_without_git_warns(tmp_path, capsys, monkeypatch):
    args = make_repo(tmp_path, git=False)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    code, out, err = run(args, capsys)
    assert code == 0 and "WARNING: freeze:" in err and "not in a git work tree" in err
    assert "ok: freeze" not in out

    def no_git(*a, **k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(check_note.subprocess, "run", no_git)
    code, _, err = run(args, capsys)
    assert code == 0 and "git is not installed" in err


@pytest.mark.parametrize(
    ("fmt", "x", "expected"),
    [(check_note.bps, -1137.8173865104236, "-1,138 bps"), (check_note.bps, -1137.5, "-1,138 bps"),
     (check_note.bps, -1323.270334147425, "-1,323 bps"),
     (check_note.usd_billions, 2150500078, "$2.15B"), (check_note.usd_billions, 2545e6, "$2.55B"),
     (check_note.ratio, 2150500078 / 2.71e9, "0.79×"),
     (check_note.ratio, 2541499922 / 2.71e9, "0.94×"),
     (check_note.hours, 1.4128396007529505, "1.4 h"), (check_note.hours, 1.45, "1.5 h")],
)  # fmt: skip
def test_rounding_rules(fmt, x, expected):
    assert fmt(x) == expected


def test_quoted_is_minus_space_and_whole_number_aware():
    assert check_note.quoted("trough\n−1,138 bps", "-1,138 bps")
    assert check_note.quoted("trough −1,138bps", "-1,138 bps")
    assert not check_note.quoted("trough −11,138 bps", "-1,138 bps")
    assert not check_note.quoted("trough −1,1385 bps", "-1,138 bps")
    assert not check_note.quoted("trough 1,138 bps", "-1,138 bps")
    assert not check_note.quoted("$2.150B", "$2.15B")
    assert not check_note.quoted("$12.15B", "$2.15B")
    assert check_note.quoted("0.79× the attack", "0.79×")


@pytest.mark.xfail(
    strict=True,
    reason="Story 4.2 blocked: docs/NOTE.md lists 9 figures its body never cites "
    "(see the story's Blockers); remove this mark when the note or its list is fixed",
)
def test_the_committed_note_passes():
    run = subprocess.run(
        [sys.executable, "scripts/check_note.py"], capture_output=True, text=True, check=False
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.count("note-check: ok: ") == 4
