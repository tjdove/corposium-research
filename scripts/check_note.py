"""Note guard (Story 4.2): the figures and fitted numbers ``docs/NOTE.md`` cites are the
ones in the repository.

Four checks, one ``ok:`` line each; exit 0 when all pass, exit 1 naming every failure.

- **figures.** Every ``figures/<name>.png`` the note links or embeds (markdown ``](...)``)
  exists beside the note and ``<name>`` is a key of ``manifest.json``.
- **cited.** Every figure in the note's figure-list table outside the record-only rows and
  the rows whose file cell is marked ``†`` (supporting; Story 5.1 review, ruling 4) is
  linked or embedded at least once in the body (the text above the figure list). The four
  record-only figures (``docs/figures/README.md``, "Record only", read beside the manifest)
  are never linked or embedded anywhere in the note.
- **freeze.** The freeze tag on the note's header line (the first line that names a tag
  ``v\\d+\\.\\d+-freeze``; it must name exactly one) resolves to a commit whose
  ``manifest.json`` has the working tree manifest's ``code_hash``. A tag that does not
  resolve, or has no manifest, fails. A ``code_hash`` that differs warns (the freeze is
  lifted during Epic 5; Story 4.2 rulings, second round, ruling 2) and fails only with
  ``--strict-freeze``. Every other tag the note names (an older freeze in the text or the
  Change Log; Story 5.7) must resolve but is not compared. When git is not installed or
  the note is not in a git work tree, this warns and does not fail.
- **numbers.** ``NUMBERS`` maps fit-record results to the strings the note quotes, with a
  rounding rule each; the normalised note must contain each one. The depth fit is quoted
  as the symbol D\\*: the symbol must appear, and the fitted value ``16,666,667`` appearing
  in the note only warns.

Normalisation (note and computed string alike): U+2212 minus → ``-``; thin spaces
U+2009/U+202F removed; any whitespace run (line breaks included) → one space. A number
matches only whole (no digit, comma or point directly before it, no digit after) and the
unit may follow with or without a space.

Like ``check_figures.py``, this reads files and git; it runs no simulation. Warnings are
also ``::warning::`` annotations when ``GITHUB_ACTIONS`` is set.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from fit_record import FITS
from note_tables import FIGURE_LIST, NOTE, note_sets, readme_sets, supporting

MANIFEST = Path("docs/figures/manifest.json")
CODE_HASH = "code_hash"
CITED = re.compile(r"\]\(\s*(?:\./)?figures/([A-Za-z0-9_]+\.png)\s*\)")
FREEZE_TAG = re.compile(r"v\d+\.\d+-freeze")
D_STAR = re.compile(r"D\\?\*")

# Attacker capital, the episode's net USDC burn 10 → 13 March 2023 (00:00 UTC snapshots),
# ≈ $2.71B: docs/calibration/SOURCES.md (Story 2.6, holder row and the attacker sizing).
ATTACKER_USD = 2.71e9


def _half_up(x: float, places: int) -> Decimal:
    """``x`` rounded to ``places`` decimals, ties away from zero (Decimal ROUND_HALF_UP)."""
    return Decimal(repr(x)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def usd_billions(x: float) -> str:
    return f"${_half_up(x / 1e9, 2)}B"


def bps(x: float) -> str:
    return f"{int(_half_up(x, 0)):,} bps"


def ratio(x: float) -> str:
    return f"{_half_up(x, 2)}×"


def hours(x: float) -> str:
    return f"{_half_up(x, 1)} h"


def trough_at_c_star(result: dict) -> float:
    """``max_depeg_bps`` of the run at ``c_star`` (the record's own grid point)."""
    (run,) = [r for r in result["runs"] if r["holder_capital"] == result["c_star"]]
    return run["max_depeg_bps"]


@dataclass(frozen=True)
class Quote:
    fit: str  # file in the fits directory
    what: str
    value: Callable[[dict], float]  # from the record's ``result``
    fmt: Callable[[float], str]  # the rounding rule


NUMBERS: list[Quote] = [
    Quote("holder-single.json", "believers' capital C*", lambda r: r["c_star_usd"], usd_billions),
    Quote("holder-single.json", "trough at C*", trough_at_c_star, bps),
    Quote("holder-single.json", "C* / attacker", lambda r: r["c_star_usd"] / ATTACKER_USD, ratio),
    Quote("holder-ladder-b.json", "ladder B capital C*", lambda r: r["c_star_usd"], usd_billions),
    Quote("holder-ladder-b.json", "ladder B trough at C*", trough_at_c_star, bps),
    Quote(
        "holder-ladder-b.json",
        "ladder B C* / attacker",
        lambda r: r["c_star_usd"] / ATTACKER_USD,
        ratio,
    ),
    Quote("reversion.json", "calm reference half-life", lambda r: r["half_life_h"], hours),
]  # the holder fits' time of trough is not in the record, so it is not checked


def normalise(text: str) -> str:
    text = text.replace("−", "-").replace(" ", "").replace(" ", "")
    return re.sub(r"\s+", " ", text)


def quoted(note: str, expected: str) -> bool:
    """Whether normalised ``note`` holds ``expected`` (``<number>[ ]<unit>``) whole."""
    m = re.fullmatch(r"(\$?-?[\d,.]+)\s?(.*)", normalise(expected))
    number, unit = m.groups()
    pattern = rf"(?<![\d,.]){re.escape(number)}(?!\d)\s?{re.escape(unit)}"
    return re.search(pattern, normalise(note)) is not None


@dataclass
class Report:
    ok: list[str]
    fail: list[str]
    warn: list[str]


def body_of(text: str) -> str:
    """The note above its figure list (the whole note when it has none)."""
    i = text.find(FIGURE_LIST)
    return text if i < 0 else text[:i]


def check_figures(note: Path, text: str, manifest: dict, report: Report) -> None:
    cited = CITED.findall(text)
    bad = []
    for name in dict.fromkeys(cited):
        if not (note.parent / "figures" / name).is_file():
            bad.append(f"figures/{name} is cited but not on disk")
        if Path(name).stem not in manifest:
            bad.append(f"figures/{name} is cited but not a key in the manifest")
    report.fail += [f"figures: {b}" for b in bad]
    if not bad:
        report.ok.append(f"figures: {len(set(cited))} cited figures exist and are in the manifest")


def check_cited(note: Path, text: str, readme: Path, report: Report) -> None:
    listed, _ = note_sets(note)
    exempt = set(supporting(note))
    body = set(CITED.findall(body_of(text)))
    uncited = [f for f in listed if f not in body and f not in exempt]
    _, record = readme_sets(readme)
    record_cited = [f for f in record if f in set(CITED.findall(text))]
    report.fail += [f"cited: {f} is in the figure list but never cited in the body"
                    for f in uncited]  # fmt: skip
    report.fail += [f"cited: {f} is record only ({readme}) but the note cites it"
                    for f in record_cited]  # fmt: skip
    if not uncited and not record_cited:
        report.ok.append(
            f"cited: all {len(listed) - len(exempt & set(listed))} listed figures not marked † "
            f"are cited; none of the {len(record)} record-only figures is"
        )


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                          check=False)  # fmt: skip


def check_freeze(
    text: str, manifest_path: Path, manifest: dict, report: Report, strict: bool = False
) -> None:
    named = [ln for ln in text.splitlines() if FREEZE_TAG.search(ln)]
    if not named:
        report.fail.append("freeze: the note must name a freeze tag, found none")
        return
    header = sorted(set(FREEZE_TAG.findall(named[0])))
    if len(header) != 1:
        report.fail.append(f"freeze: the header line must name one freeze tag, found {header}")
        return
    tag, where = header[0], manifest_path.parent
    others = sorted(set(FREEZE_TAG.findall(text)) - {tag})
    try:
        inside = _git(where, "rev-parse", "--is-inside-work-tree")
    except FileNotFoundError:
        report.warn.append(f"freeze: git is not installed; {tag} not checked")
        return
    if inside.returncode != 0:
        report.warn.append(f"freeze: {where} is not in a git work tree; {tag} not checked")
        return
    commit = _git(where, "rev-parse", "--verify", "--quiet", f"{tag}^{{commit}}")
    if commit.returncode != 0:
        report.fail.append(f"freeze: tag {tag} does not resolve (git fetch --tags?)")
        return
    unresolved = [
        t for t in others
        if _git(where, "rev-parse", "--verify", "--quiet", f"{t}^{{commit}}").returncode != 0
    ]  # fmt: skip
    if unresolved:
        report.fail += [f"freeze: tag {t} named in the note does not resolve" for t in unresolved]
        return
    sha = commit.stdout.strip()
    shown = _git(where, "show", f"{sha}:./{manifest_path.name}")
    if shown.returncode != 0:
        report.fail.append(f"freeze: {tag} ({sha[:12]}) has no {manifest_path.name} there")
        return
    then, now = json.loads(shown.stdout).get(CODE_HASH), manifest.get(CODE_HASH)
    if then != now:
        line = (
            f"freeze: {tag} ({sha[:12]}) manifest has code_hash {then}, "
            f"the working tree's has {now}"
        )
        if strict:
            report.fail.append(line)
            return
        report.warn.append(line)
        report.ok.append(f"freeze: {tag} is {sha[:12]} (code differs, see warning)")
        return
    also = f"; older tags named resolve: {', '.join(others)}" if others else ""
    report.ok.append(f"freeze: {tag} is {sha[:12]}, manifest code_hash {now[:12]} matches{also}")


def check_numbers(text: str, fits: Path, report: Report) -> None:
    records, bad, n = {}, [], 0
    for q in NUMBERS:
        if q.fit not in records:
            path = fits / q.fit
            if not path.is_file():
                bad.append(f"numbers: fit record {path} is missing")
                records[q.fit] = None
                continue
            records[q.fit] = json.loads(path.read_text(encoding="utf-8"))["result"]
        if records[q.fit] is None:
            continue
        expected = q.fmt(q.value(records[q.fit]))
        n += 1
        if not quoted(text, expected):
            bad.append(f"numbers: {q.fit} {q.what} is {expected}; the note does not say so")
    depth = fits / "depth.json"
    if not depth.is_file():
        bad.append(f"numbers: fit record {depth} is missing")
    else:
        d_star = json.loads(depth.read_text(encoding="utf-8"))["result"]["d_star"]
        n += 1
        if not D_STAR.search(text):
            bad.append("numbers: depth.json is quoted as the symbol D*; the note never uses it")
        if f"{d_star:,}" in normalise(text):
            report.warn.append(
                f"numbers: the note prints D* as {d_star:,}; it is meant to use the symbol"
            )
    report.fail += bad
    if not bad:
        report.ok.append(f"numbers: {n} fitted values quoted as their records round them")


def check_note(note: Path, manifest_path: Path, fits: Path, strict_freeze: bool = False) -> Report:
    report = Report([], [], [])
    text = note.read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    check_figures(note, text, manifest, report)
    check_cited(note, text, manifest_path.parent / "README.md", report)
    check_freeze(text, manifest_path, manifest, report, strict_freeze)
    check_numbers(text, fits, report)
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--note", type=Path, default=NOTE)
    p.add_argument("--manifest", type=Path, default=MANIFEST)
    p.add_argument("--fits", type=Path, default=FITS)
    p.add_argument(
        "--strict-freeze",
        action="store_true",
        help="fail, not warn, when the freeze tag's code_hash is not the working tree's",
    )
    args = p.parse_args(argv)
    for path in (args.note, args.manifest):
        if not path.is_file():
            print(f"note-check: {path} not found", file=sys.stderr)
            return 1
    report = check_note(args.note, args.manifest, args.fits, args.strict_freeze)
    for line in report.warn:
        print(f"note-check: WARNING: {line}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::warning title=note-check::{line}")
    for line in report.ok:
        print(f"note-check: ok: {line}")
    if report.fail:
        for line in report.fail:
            print(f"note-check: FAIL: {line}", file=sys.stderr)
        print(f"note-check: FAIL, {len(report.fail)} problem(s) in {args.note}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
