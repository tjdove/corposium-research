# ADR-0002: BMAD-style epics and stories; Claude writes, Claude Code builds

**Status:** Accepted · **Date:** 2026-10-02 · **Deciders:** Tim Dove, Claude · **Origin:** charter

## Context
The DEX rebuild succeeded with BMAD (PRD → epics → stories with context XML → dev → senior review → retro). Tim is the only human; Muse handles ops.

## Decision
`docs/epics.md` is the master plan. Claude (chat) occupies the SM/PM/Architect seats: drafts each story and context file, assigns it, reviews independently (re-running every AC on a separate machine), rules on builder flags, marks `done`, drafts the next story via PR. Claude Code on Seoul builds exactly one story per session and stops. Muse never directs builders.

## Consequences
Story files are the contract and win over any kickoff prompt. Builder flags are expected and ruled on in the review. Every ruling becomes an ADR when it constrains future work.

## Alternatives considered
Muse also directing coding agents (rejected: two dev managers); ad-hoc prompting without stories (rejected: lost the review gate that caught real defects in 1.3 and 1.4).
