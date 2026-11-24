---
name: qa
description: Browser QA of this repo's web app at phone size, before every M4 PR - test, fix bugs inside the milestone, re-test, and write a report whose summary goes in the PR. Adapted from gstack's /qa (MIT) to use the Playwright MCP tools instead of gstack's own browser.
---

# /qa: Test → Fix → Verify (mtl-housing)

Adapted from gstack's `/qa` (github.com/garrytan/gstack, commit `aab606e`, MIT, © 2026 Garry
Tan; licence in `.claude/skills/LICENSE-gstack.txt`). What was kept: the QA method, issue
taxonomy, health-score rubric and report format. What was removed: gstack's preamble, config,
telemetry, cross-project "learnings", its Aside/`$B` browser and auto-commits. This repo's
`CLAUDE.md` wins over anything here.

## When

Before every M4 PR (owner's rule), **at phone size first** (390 × 844), then desktop
(1280 × 820). Put the summary in the PR's description.

## Setup

1. **Clean tree.** `git status --porcelain` must be empty (commit the milestone's work first),
   so QA fixes are separate commits.
2. **Build and serve the real app:** `npm --prefix web run build`, then
   `npm --prefix web run start -- --port 3100` as a background task. Stop it at the end.
3. **Browser:** the Playwright MCP tools (`mcp__playwright__*`); load them with ToolSearch.
   - size: `browser_resize` (390 × 844 for phone, 1280 × 820 for desktop);
   - open: `browser_navigate`; structure and refs: `browser_snapshot`;
   - act: `browser_click`, `browser_type`, `browser_fill_form`, `browser_select_option`,
     `browser_press_key`;
   - evidence: `browser_take_screenshot` (save under the report dir), then Read the image;
   - errors: `browser_console_messages` (level `warning`), `browser_network_requests`;
   - checks inside the page: `browser_evaluate`.
4. **Report dir:** `data/interim/qa-reports/run-<YYYYMMDDTHHMMSSZ>/` (gitignored), with
   `screenshots/`. Never overwrite an earlier run.
5. **Scope:** diff-aware by default: `git diff origin/main...HEAD --name-only`, map changed
   components/routes to pages, test those pages and their neighbours.

## Phases 1–6: baseline

1. **Orient.** For each page in scope: navigate, snapshot, screenshot (`initial-phone.png`),
   console messages. Confirm the page shows its expected result, not just that it loaded.
2. **Explore** core flows first (for M4: search form → results → detail → map view).
   Per page, use the checklist in **Per-page checklist**. Check empty, invalid and edge
   inputs: no budget, a budget at an exact rent, very low and high budgets, every size,
   every commute button, keyboard only.
3. **Document.** Retry each issue once to confirm it, then save evidence
   (`issue-NNN-step-N.png`, `issue-NNN-result.png`). Never invent an issue; 5–10 evidenced
   issues beat 20 vague ones.
4. **Wrap up.** Health score (rubric below), top 3 things to fix, console health, counts.

Rules: test like a user: use the UI, not source code, while discovering. Check the console after
every interaction. Never type credentials. This app has no accounts.

## Phase 7–9: triage, fix, re-test

- **Fix tier:** standard = critical + high + medium. Low/cosmetic go in the report.
- **Fix only inside the current milestone's scope.** Anything outside it, or any data
  question, goes in the report as "not fixed, needs owner". Never fake data to make a
  page look right.
- Per fix: reproduce → if the logic is testable, add a failing Vitest/pytest test first → fix
  → re-test in the browser at the same size → classify `verified` / `best-effort` /
  `reverted` / `deferred`.
- Commit fixes with this repo's convention (`fix(web): …`, message via a heredoc file,
  `git commit -F`). One logical fix per commit.
- Stop and report if fixes start to cascade (three fixes in a row that break something
  else).
- Final pass: re-run the baseline pages; compute the score again.

## Per-page checklist

1. **Visual:** layout breaks, overlap, clipped text, horizontal scroll, broken images.
2. **Interactive:** every button, link and control does what it says.
3. **Forms:** empty submit, invalid values, edge values; labels visible; errors next to the
   field; correct input types on phone.
4. **Navigation:** back/forward, deep links, a way back from every view.
5. **States:** empty, loading, error, overflow (long names), "not enough data".
6. **Console:** no new errors or failed requests.
7. **Responsive:** phone first; then desktop.
8. **Accessibility:** keyboard reachable, visible focus, labelled inputs, 44 px touch
   targets, contrast (WCAG AA).
9. **Next.js:** hydration errors (`Hydration failed`, `Text content did not match`),
   client-side link navigation (click, not only `goto`), layout shift after load.

## Issue taxonomy

| Severity | Meaning |
|---|---|
| critical | core flow blocked for everyone, data shown wrong, crash |
| high | major feature broken, no workaround |
| medium | works with noticeable problems, workaround exists (e.g. broken on phone only) |
| low | cosmetic, copy, small friction |

Categories (one primary per issue, first that applies): links, accessibility, functional,
performance, visual, content, UX, console.

## Health score rubric

Score each **tested** category 0–100, then a weighted average over tested categories only
(untested = "not scored"; partial = "provisional").
- **Console (15%):** 0 errors 100 · 1–3 → 70 · 4–10 → 40 · 11+ → 10.
- **Links (10%):** 100, −15 per unique broken destination.
- **Visual 10% · Functional 20% · UX 15% · Performance 10% · Content 5% · Accessibility 15%:**
  start at 100; critical −25, high −15, medium −8, low −3; floor 0.
- Final = Σ(score × weight) / Σ(tested weights), rounded at the end only.

## Report (`qa-report.md` in the run dir; summary in the PR)

Header: date, URL, branch, commit, viewports, pages visited, screenshot count.
Then: **Health score** with per-category scores · **Top 3 things to fix** · **Console
health** · **Severity counts** · **Issues** (each: severity, category, page, expected vs
actual, repro steps with screenshots) · **Fixes applied** (issue, status, commit, files) ·
**Not fixed / needs owner** · **Score before → after**.

PR summary line: "QA (phone 390 × 844, then desktop): found N issues, fixed M, health score
X → Y." Commit only the screenshots the PR shows (WebP under `docs/screenshots/<milestone>/`).
