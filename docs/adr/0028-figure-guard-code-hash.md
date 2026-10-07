# ADR-0028: The figure guard warns on a code-hash mismatch and fails on a source-hash mismatch

**Status:** Accepted (review 2026-10-06)
**Date:** 2026-10-06
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 3.5 AC 3 (3.1 review ruling 4)

## Context

`make figures-check` (Story 2.9, `scripts/check_figures.py`) compares each committed
figure's recorded source hash with the current one: `content_hash()` for a scenario,
`sweep_spec_hash()` for a sweep. It cannot see a change to the code that draws or
simulates, so a chart could be committed from one version of the model and quoted
against another with CI green. Re-running `make figures` on every push is not an option
(about 10 minutes on 12 cores; more on CI's 4), and most code changes (a docstring, a
test, a refactor) do not move a number. The story fixes the semantics (warn on code,
fail on source); it leaves open what exactly is hashed, what a manifest without a code
hash means, and where the warning appears.

## Decision

1. **What is hashed.** `check_figures.code_hash()` is sha256 over every `*.py` under
   `src/depeg_sim/`, in sorted order of relative POSIX path; each file contributes its
   relative path, a NUL byte, its raw bytes and a NUL byte. Including the path means a
   rename, or code moved between files, changes the hash; hashing raw bytes means any
   edit, including whitespace and docstrings, changes it. Not hashed: `scripts/`, `data/`,
   `pyproject.toml`, installed library versions. Scenario and sweep inputs are already
   covered by the source hashes (a replay series enters `content_hash()` as its sha256).
2. **Where it lives.** One top-level key, `code_hash`, in `docs/figures/manifest.json`,
   beside the per-figure entries; every other key is a figure. `make figures` writes it
   at drawing time (`scripts/make_figures.py`).
3. **Guard semantics.**
   - Source hash differs, a figure file or source is missing: **fail**, exit 1, one line
     per problem (unchanged from 2.9).
   - Code hash differs, or the manifest has no `code_hash`: **warn** and exit 0. The
     warning goes to stderr and names the recorded value (or "no code_hash") and the
     current hash in full, and points at the freeze checklist. When `GITHUB_ACTIONS` is
     set it is repeated on stdout as a `::warning title=figures-check::` annotation, so
     it shows on the run summary page and not only in the log. The `ok` line says
     `(code differs, see warning)` instead of `(code_hash matches)`.
   - Both: fail, with the warning printed as well.
4. **The hard gate for code is the freeze.** `docs/REPRODUCIBILITY.md` "Before the
   freeze": `make figures`, commit the figures and manifest, then `make figures-check`
   must print `code_hash matches` with no warning. A reviewer who sees the warning on a
   story that changed model or chart code asks for `make figures` in that story.

## Consequences

- Every push after this story that touches `src/depeg_sim/` shows the warning until the
  next `make figures`. That is the intent: it is loud, and cheap to clear.
- The code hash is sensitive to line endings: a checkout that converts LF to CRLF
  (Windows with `core.autocrlf=true`) hashes differently and warns, though nothing has
  changed. CI and Seoul are Linux; a stranger on Windows sees a warning, not a failure.
- The guard still never compares PNG bytes (matplotlib output is not byte-stable across
  versions) and never runs a scenario.
- A change to `scripts/make_figures.py` alone (for example a new registered figure) does
  not warn; the source hash of a new figure's sweep is absent from the manifest, so the
  figure simply is not checked until `make figures` adds it.

## Alternatives considered

- **Fail on code hash.** Rejected by the story: it would block CI on every docstring edit
  until a 10-minute regeneration.
- **Hash only the modules a figure depends on** (its chart function, the simulation
  packages). More precise, but the dependency set is the whole simulator for every sweep
  figure, so it saves little and adds an import-graph walk that can itself go stale.
- **Hash concatenated contents without paths.** Simpler, but a rename or a block of code
  moved between two files would not change the hash.
- **Hash the git tree of `src/`.** Ties the guard to git being present and to committed
  state; the guard must work on an unpacked tarball.

## Related judgment calls in Story 3.5 (recorded in its Completion Notes)

- `summarize` gains `arbitrageur_redeemed`: reference paid by the redemption channel to
  the first arbitrageur, from its `redeem_fulfilled` events; 0.0 if it never redeemed,
  `None` without an arbitrageur or a redemption module. `scripts/policy_table.py` derives
  the holder's share as `redemption_paid_total - arbitrageur_redeemed`; that holds while
  the arbitrageur and the holder are the only agents that redeem, which
  `tests/test_summary.py` asserts on the calibrated baseline.
- `make test` asserts coverage with `--cov-fail-under=85` over `protocol/` and `agents/`
  together (pytest-cov has no per-package threshold); both are at 96–100% per file.
