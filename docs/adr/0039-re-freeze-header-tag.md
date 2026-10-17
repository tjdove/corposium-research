# ADR-0039: The note's freeze tag is the one on its header line; older tags must resolve; note-check strict again

**Status:** Accepted (interface; review 2026-10-17, unamended)
**Date:** 2026-10-17
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 5.7 (re-freeze; ADR-0032 ruling 4)

## Context

Story 5.7 re-freezes the code behind the note at a new tag, `v0.95-freeze`, and says that
the builder changes `docs/NOTE.md`'s header line from `v0.9-freeze` to `v0.95-freeze`
"and nothing else in the note". The dev manager rewrites the rest for v2.

`scripts/check_note.py` (Story 4.2) required the note to name exactly one freeze tag.
NOTE.md names `v0.9-freeze` three times: in the header, in §9 ("Code is frozen at
`v0.9-freeze`") and in a Change Log line. With only the header changed, the note names
two tags and the check fails with "the note must name one freeze tag". The story's two
requirements (only the header changes; `make note-check` is clean) could not both hold
under the old check. Tim chose this resolution when asked (2026-10-17).

## Decision

1. **The header line names the freeze.** The note's header line is the first line that
   names a tag `v\d+\.\d+-freeze`, and it must name exactly one. That tag is the one
   compared on `code_hash`, as before: a mismatch warns, and fails with `--strict-freeze`.
2. **Every other tag the note names must resolve, but is not compared.** An older freeze
   named in the text or the Change Log is history. If it does not resolve (a typo, an
   unpushed tag), the check fails. When there are older tags, the `ok` line names them.
3. **A note that names no tag still fails.** The wording is now "must name a freeze tag,
   found none".
4. **Where the change goes.** The checker change is in the freeze commit (`story 5.7:
   re-freeze`). The commit after it, which records the freeze hash, changes nothing under
   `src/`, `scripts/`, `scenarios/` or `sweeps/` (ADR-0032 ruling 4). `scripts/check_note.py`
   is not in `code_hash` and draws no figure, so the figures and hashes are the same with
   it or without it.
5. **note-check is strict again from the hash commit.** The Makefile's `note-check` passes
   `--strict-freeze`. CI runs `make note-check`, so CI is strict too, and so is a local
   run. Story 4.2's second-round ruling 2 relaxed the check because the freeze was lifted
   during Epic 5. With the note citing the new tag, any change to `src/depeg_sim/` after
   `v0.95-freeze` now fails note-check until the next freeze, or until the dev manager
   relaxes it again.

## Consequences

- The v2 rewrite of §9 and the Change Log can name both tags freely. Only the header
  decides which code the note cites.
- Putting a new tag on a later line without changing the header does nothing; the header
  is still compared (tested).
- Any code change merged before the note's v2 release must come with a new freeze, or must
  drop `--strict-freeze` in the Makefile, which is a one-line change.

## Alternatives considered

- **Also change §9 to `v0.95-freeze`.** This edits more of the note than the story allows,
  and the Change Log line still names the old tag, so the checker would need changing
  anyway. Rejected (Tim).
- **Use the newest tag the note names.** This picks the tag by version order, not by what
  the header says. A Change Log line naming a newer tag would silently become the freeze.
  Rejected.
- **Make only CI strict (`ci.yml`), not `make note-check`.** Local runs would then pass
  where CI fails. Rejected in favour of one spelling, used in both places.
