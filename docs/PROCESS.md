# PROCESS.md — how the dev-manager role runs this project

This is the operating manual for whoever holds the dev-manager seat (today: Claude, in
chat, outside this repo). It exists so that a fresh session with no memory of the
conversation can pick up the project from the repo alone. The charter says *what* and
*why*; this file says *how*, and records the process lessons that were learned the hard
way. Model-level findings do **not** go here — they go in `FINDINGS.md` and the ADRs.

Read order for a cold start: `CHARTER.md` → `epics.md` → this file → `adr/README.md` →
`FINDINGS.md` → the last two story files (their Senior Developer Review sections) →
`retrospectives/`.

---

## 1. Where everything lives

| Thing | Location | Owner |
|---|---|---|
| Mission, scope, roles, timeline, decision log | `docs/CHARTER.md` | dev manager, Tim decides |
| Epic and story plan, status per story | `docs/epics.md` | dev manager |
| The contract for one unit of work | `docs/stories/N-M-slug.md` + `.context.xml` | dev manager writes, builder fills Dev Agent Record, dev manager appends review |
| Design decisions and rulings on builder flags | `docs/adr/NNNN-*.md`, index in `adr/README.md` | builder proposes, dev manager accepts/amends/rejects |
| What the model has shown (narrative for the note) | `docs/FINDINGS.md` | dev manager, append-only |
| Tim's 1992 research and the analogy map | `docs/BACKGROUND.md` | Tim |
| Calibration provenance and validation result | `docs/calibration/SOURCES.md`, `VALIDATION.md`, `data/` | builder, reviewed |
| Per-epic retro | `docs/retrospectives/epic-N-retro.md` | dev manager |
| Builder's standing rules | `CLAUDE.md` (repo root) | dev manager |
| Business ops, time logs, comms | Open Brain (`[muse-ops]` tag), email | Muse |
| Build reports for ops | Open Brain (`[claude]` tag) | dev manager |
| Mirrors for the Claude project (chat-side memory) | `claude/*.md` in the "Corposium Research Lab" project | dev manager, refreshed at each review |

Rule: if a fact matters to a later story or to the note, it is in one of these files.
Chat is not storage.

---

## 2. The story loop

One story per builder session, strictly sequential. The loop:

1. **Draft.** Dev manager writes `N-M-slug.md` (template in `stories/README.md`) and
   `N-M-slug.context.xml`. ACs are numbered; every Task maps to ACs; Dev Notes carry
   "Learnings from previous story" lifted from the last review. Set `Status: ready-for-dev`.
   Update `epics.md`. Open a PR; **Tim merges**.
2. **Kickoff.** Only after Tim says "merged" (see lesson L-4), dev manager gives Tim the
   kickoff prompt (template §4). Tim runs it in a fresh Claude Code session on Seoul.
3. **Build.** Builder follows `CLAUDE.md`: in-progress → tasks in order → tests alongside
   → Dev Agent Record with real command output → `Status: review` → push to `main`.
   Builder stops. If the spec contradicts itself, builder writes `## Blockers`, sets
   `Status: blocked`, stops.
4. **Report.** Tim pastes the builder's report into chat.
5. **Review.** Dev manager pulls `main`, reproduces independently (§3), appends
   `## Senior Developer Review` to the story file, rules on every builder flag, accepts or
   amends each Proposed ADR (edits the ADR file and the index), appends findings to
   `FINDINGS.md`, sets `Status: done`, updates `epics.md`, drafts the next story in the
   same PR. Refreshes the project mirrors. Opens the PR; Tim merges.
6. Repeat. At the end of an epic: retro file, then draft the next epic's stories in detail.

The story file wins over the kickoff prompt, over chat, over anything. This has been
tested (1.2) and it holds.

---

## 3. Review procedure

The review is independent: a different machine, a different Python (review box runs the
CI version, 3.12; Seoul runs 3.12 under uv), nothing taken from the report on trust.

Checklist, in order:

- [ ] `git pull`; fresh venv; `pip install -e ".[dev]"`; `pytest -q`; `ruff check .`;
      `ruff format --check .`. Paste counts into the review. Compare to the builder's.
- [ ] Every AC: find the code, find the test, run the command the AC implies. Tick or fail
      each one explicitly in the review.
- [ ] Determinism: re-run the story's headline scenario; compare `summary.json` hash and
      the run-dir hash8 to the builder's. They must match byte-for-byte.
- [ ] Every numeric claim in the report: reproduce it or mark it "not reproduced".
      Large sweeps: run a slice (L-6) and check the slice cells match the committed CSV.
- [ ] Every builder flag / "I decided X": rule on it. Ratify, amend, or reverse. Write
      the ruling in the review and, if it will bind later stories, in the ADR.
- [ ] Each Proposed ADR: read against the code. Accept / amend / reject; edit the file's
      status line and add it to `adr/README.md`. Supersede earlier ADR sections by name.
- [ ] Findings: is there a model behaviour here that the note will cite? If yes, add
      `F-NN` to `FINDINGS.md` with the exact run that shows it, and re-rank the headline
      candidates. If it refines an earlier finding, add a dated refinement under that
      finding rather than rewriting it.
- [ ] Spec defects the builder caught: list them in the review and in the next story's
      "Learnings". They are the dev manager's errors and get recorded as such.
- [ ] CI: confirm the run on `main` is green by looking, not by assuming (L-5).
- [ ] Look at every chart the story produced. Describe it in the review in words.
- [ ] Scope check against `CHARTER.md` §4 Out list. Nothing in the Out list gets built
      even if it would be easy.

Review verdict is one of: **APPROVED, done** · **APPROVED with amendments** (list them,
they go into the next story) · **RETURNED** (specific ACs failed; story goes back to
`in-progress` with a `## Review Notes` section the builder must address).

---

## 4. Kickoff prompt template

Issue this, filled in, only after the story file is on `main`.

```
You are Claude Code on Seoul, implementing one story for the Corposium Research depeg simulator.

Setup:
- cd into the corposium-research repo, `git checkout main && git pull`.
- Activate the uv venv (Python 3.12). Confirm `python --version` prints 3.12.x.
- Read CLAUDE.md, then docs/adr/README.md (index), then docs/FINDINGS.md in full.

Your story: docs/stories/N-M-slug.md and its context file docs/stories/N-M-slug.context.xml.
Read both fully, including Dev Notes. The story file is the contract; if this prompt
and the story disagree, the story wins.

Work it per CLAUDE.md:
1. Set Status: in-progress.
2. Tasks in order. [Any commit-split instruction, e.g. "config is a separate first commit".]
3. [Story-specific normative reminders — fit rules, what is NOT to be re-fitted, etc.]
4. pytest, ruff check ., ruff format --check . — paste output.
5. Fill the Dev Agent Record, Change Log, set Status: review. Final commit:
   `story N.M: <slug>`. Push to main.

Hard constraints: [the story's constraints block, verbatim].

If anything in the story contradicts itself or the code, stop, write it under
## Blockers with Status: blocked, and report back. Do not guess.

When done, report: [the specific numbers the review needs], the ADR number, and the test count.
```

The report request at the end matters: it tells the builder what the review will check,
so the Debug Log contains it.

---

## 5. Conventions the stories rely on

These are decided (see the ADRs) and every new story is written to respect them:

- Construction validates and raises; execution rejects via `ExecutionResult(ok=False)`
  plus a `*_rejected` event (ADR-0005).
- Emitting methods take `ctx` first (ADR-0008).
- Floats, not Decimal (ADR-0003). Files plus manifest, not SQL (ADR-0004).
- Manifest embeds the resolved config and the sha256 of any input series (ADR-0014).
- Run dir `output/<name>-<seed>-<hash8>/`; sweep cells `<sweep>/<index>-<seed>-<hash8>/`
  (ADR-0015).
- One parameter, one observation, log grid then 5-point refinement, closest wins, no
  hand-picking — the fit discipline (ADR-0019, 0020).
- Schema additions must leave every existing scenario's `content_hash()` unchanged, with
  a test that pins the hashes.
- Chart conventions: 10×6 in at 150 dpi, time axis in minutes or hours, deviation in bps,
  dashed zero line, shaded tolerance band, footer with scenario / seed / hash8.
- CLI entrypoints flush stdout/stderr then `os._exit(rc)` (PR #15; see L-5).
- Commit messages `story N.M: <what changed>`.

---

## 6. Process lessons (L-NN)

Numbered so reviews and retros can cite them. Add to the list; do not delete.

- **L-1 — Story file is the contract.** A reused or stale kickoff prompt (1.2) did no harm
  because the builder followed the story file. Keep it that way: never put an instruction
  only in the prompt.
- **L-2 — Check Dev Notes against ACs before issuing a story.** Six of the first thirteen
  stories had a contradiction between the two (1.3 queue-clear phase, 1.3 view-protocol
  location, 1.4 mixed-unit fees, 1.5 threshold-0, 1.6 `set_spread_bps` signature, 2.1 cell
  layout, 2.2 manifest key, 2.3 Curve fee and Chainlink heartbeat, 2.4 grid extension).
  The builder caught every one, but each cost a round trip. Read the story once more as
  the builder before setting `ready-for-dev`.
- **L-3 — A wrong calibration input propagates into every downstream number.** ADR-0018's
  attacker ratio of 1.0 produced D\* = $430B/side and was not caught until 2.4's result
  looked absurd. Sanity-check every anchor against a real-world magnitude in the SOURCES
  row itself (e.g. "this is 1.2× the episode net burn") before it feeds a fit.
- **L-4 — Wait for "merged" before issuing a kickoff.** Story 2.4's file was not on
  `main` when the prompt went out; the builder merged the branch itself. Harmless once,
  but it puts the builder in the dev manager's seat. The prompt goes out after Tim
  confirms the merge, never before.
- **L-5 — A CI flake is a bug.** `test_mc_module_cli_and_rerun_bytes` SIGABRT'd on one of
  two runs of the same SHA. The cause was interpreter teardown in a spawned-pool CLI, fixed
  with flush + `os._exit`. The suggested try/except would not have caught a C++ abort.
  Never close a story on a CI run that was re-run to green without a diagnosis.
- **L-6 — Verify big sweeps with slices.** The review box (2 cores) cannot re-run a 2,016-
  cell sweep. Run a 48-cell slice and check those cells match the committed CSV
  byte-for-byte; that is sufficient evidence of reproducibility.
- **L-7 — Append with care.** A `cat >>` to a mistyped filename created a duplicate
  ADR-0019 that had to be merged in PR #17. Use the Edit tool against the existing file,
  and `ls docs/adr` before creating a new one.
- **L-8 — Reviews are where findings get named.** F-02 through F-08 were all noticed in
  review by asking "what does this number mean for the note?", not by the builder. Keep
  the findings question on the review checklist.
- **L-9 — Validation failing is a result.** The 2.5 replay missing the trough by 4× was
  the most informative run of the project because it localised a missing agent (F-08) and
  changed the scope. Do not soften a failed validation; write what failed, why, and what
  it implies for the next story.
- **L-10 — Scope changes are decisions, not drift.** Inserting Story 2.6 moved Epic 2's end
  date by two days. It was written into `epics.md`, `CHARTER.md`'s decision log and the
  ADR amendment before the story was drafted, and marked "for Tim's confirmation" until
  Tim confirmed. Any change to dates or deliverables goes through the decision log.
- **L-11 — The builder needs the narrative, not just the spec.** Since Epic 2 the kickoff
  reads `FINDINGS.md` in full. Builders who know what the model has shown recognise a new
  finding when they produce one (2.5's diagnosis of the missing counterparty came from the
  builder).
- **L-12 — Refresh the project mirrors at every review.** The chat-side project docs are
  what survives a context reset on the dev-manager side. Charter, epics, findings and this
  file are mirrored; a mirror older than the last review is stale.
- **L-13 — Never scale a behavioural threshold to the agent's own size.** Story 2.6's
  redeem rule (`capacity ≥ 0.1 × stable`) made a large holder unable to redeem at all and
  turned a config flag into dead code. Thresholds on an agent's willingness to act should
  be in market units (capacity, price, time), never in multiples of its own balance. When
  drafting a rule, evaluate it once at the size the fit is expected to produce.
- **L-14 — Push before Tim is told "ready to merge".** PROCESS.md was pushed to the PR #17
  branch after Tim had already merged it, and missed main. Anything added to a PR after the
  "merge when ready" message needs its own PR or an explicit "one more commit, hold".

---

## 7. Environment notes

- **Seoul** (builder): uv-managed venv on Python 3.12 (system is 3.14). `bash time` is
  fine; `/usr/bin/time` is absent and not needed.
- **Review box**: 2 cores; CI version of Python; `gh api` works, GraphQL is blocked; use
  REST (`gh api repos/tjdove/corposium-research/...`).
- **CI**: GitHub Actions on push to `main` and on PRs; Python 3.12; `pytest` + `ruff`.
- **Open Brain**: Supabase MCP, append-only by convention; `[claude]` for build reports,
  `[muse-ops]` for ops. Muse never deletes, never writes under `[claude]`.
- **Comms to Muse**: email. Muse has no repo access and no dev credentials.

---

## 8. Roadmap beyond the current epic (pointer)

The detailed plan is `epics.md`. The intent behind Epics 3 and 4, so it is not lost if
`epics.md` is edited down:

- **Epic 3** — defender policies as the comparison axis for chart (5): `restore_threshold_pct`,
  spread-first vs buy-first ordering, a `peg_recovered.reference` termination option so
  series-driven scenarios can terminate on the reference not the AMM. Stretch: LP
  withdrawal agent (one panic threshold), Anvil fork validation of the AMM math.
- **Epic 4** — the note (2,000–3,500 words, built from `FINDINGS.md` headline ranking),
  the site Research page, the one-pager, the launch thread. Committed figures from 2.8
  are the only charts the note may use.
- **Freeze** Oct 21; **publish** Nov 1. See `CHARTER.md` §6.

---

## Change Log

- 2026-10-04: Created by dev manager after Story 2.5 review, during the 2.6 build, to
  guard against dev-manager context loss. L-1 to L-12 lifted from the Epic 1 retro and
  the Epic 2 reviews to date.
