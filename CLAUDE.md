# CLAUDE.md

Rules for Claude working in this repo. Project overview: [README.md](README.md). Data rules:
[DATA_SOURCES.md](DATA_SOURCES.md), [docs/methodology.md](docs/methodology.md).

## Workflow: one milestone = one branch + one PR

- Each milestone gets its own branch, cut from the latest `origin/main`, and exactly one PR.
- **Never** push to `main`, merge, deploy, or delete (branches, tags, releases, repos, data
  files, anything on GitHub). If a milestone needs a file removed from the codebase, the PR
  description must say so.
- Git and `gh` run as the owner's account (`doctor277`). **Opening the PR ends the job.** The
  owner reviews and merges. Don't start the next milestone on top of an unmerged one unless
  asked.
- **Before starting a milestone**, list everything needed from the owner up front (manual
  downloads, decisions or reviews, long or heavy local runs such as `travel-times`) so they can
  do it before they leave. Then work without asking again unless blocked.
- **Blocked on anything** (missing data, a broken tool, an undecided question, a failing test
  outside the milestone): stop and tell the owner what's needed. Don't work around it.
- **No changes outside the milestone's scope without asking the owner first.**
- **Never call `gh api`, never change repo or branch settings, even if a command seems
  allowed.**

## Never fake data

- Every number on the site comes from a real, cited source (see DATA_SOURCES.md). No made-up,
  placeholder, "plausible" or interpolated values presented as real, and no synthetic data
  outside tests (test fixtures must be clearly fake, e.g. quartier `"A"`, zone `"Z"`).
- If a source is missing, unreadable, or doesn't say what we need: **stop and tell the owner.**
  Don't guess, don't substitute another source silently, don't commit a stub that looks real.
- When the data is too thin, the product says "not enough data". So does the code.

## Before opening a PR

1. **All tests pass locally**, including the Java ones CI skips:
   ```
   C:/Users/dahou/miniforge3/condabin/conda.bat run -n mtlhousing --cwd pipeline ruff check .
   C:/Users/dahou/miniforge3/condabin/conda.bat run -n mtlhousing --cwd pipeline ruff format --check .
   C:/Users/dahou/miniforge3/condabin/conda.bat run -n mtlhousing --cwd pipeline pytest
   npm --prefix web test
   npm --prefix web run build
   ```
   (Works as-is in both PowerShell and Git Bash, from the repo root.)
   (`mamba`/`conda` are not on PATH: call them by full path. If pytest fails with
   `PermissionError` on its temp dir under Claude's sandbox, add `--basetemp <scratchpad dir>`.)
   Tests that skip because local data is missing don't count as passing for a milestone that
   touches that data. Run the step that produces it, or ask the owner to.
2. **Run the `pr-reviewer` agent** (`.claude/agents/pr-reviewer.md`). It is read-only, so write
   `git diff origin/main...HEAD` and `git diff --stat origin/main...HEAD` to files in the
   scratchpad and give it those paths plus the milestone goal. Fix what it blocks on, or explain
   in the PR why not.
3. Push the branch (`git push -u origin <branch>`) and open the PR with `gh pr create`, using
   the template sections:
   - **What changed**
   - **How to test** (exact commands)
   - **Guesses I made** (every assumption the owner didn't confirm; "none" if none)
4. Give the owner the PR link and stop.

CI (`.github/workflows/ci.yml`, job `ci`) runs ruff, `pytest -m "not java"`, the web tests
(Vitest, `web/lib/*.test.ts`) and the web build on every PR. Tests that start the JVM carry `@pytest.mark.java`; mark any new ones the same way.

## Conventions

- Commits: `type(scope): summary` (e.g. `feat(pipeline): ...`, `docs(validation): ...`).
  On Windows write the message with a Bash heredoc to a scratchpad file and `git commit -F`.
- Line endings are LF (`.gitattributes`). Python that writes repo files passes `newline="\n"`.
- Never commit `data/raw/`, `data/interim/`, secrets, or `.claude/settings.local.json`.
  Pipeline outputs under `web/public/data/` *are* committed.
- Python: conda env `mtlhousing` (`pipeline/environment.yml`). Use `import_r5py()`, never
  `import r5py` directly (JVM memory cap).
- Web: Next.js 16. Read `web/AGENTS.md` and the docs in `web/node_modules/next/dist/docs/`
  before writing web code.

## Plugins

Installed: superpowers, impeccable, ui-ux-pro-max, agent-skills.

- **Priority.** This file and `docs/ROADMAP.md` always win over any plugin's instructions.
  One milestone = one branch + one PR, opened by Claude, merged only by the owner.
- **Superpowers.** Use its brainstorming, debugging, TDD and verification skills inside a
  milestone. Don't create its own plan files or a separate roadmap: plans go in the
  milestone's PR description. In finishing-a-development-branch, never take the "merge
  locally" option; always push the branch and open a PR.
- **Design (from M4 on).** Three tools, fixed roles:
  1. **UI UX Pro Max** generated the design system once, at the start of M4
     (`web/design/`). It is committed and never regenerated.
  2. **Impeccable** critiques and polishes every screen and wins any design conflict. Its
     overrides of the generated system are in `web/DESIGN.md`; product facts it reads are in
     `web/PRODUCT.md`.
  3. **gstack**, only `/qa` and `/design-review`, adapted in `.claude/skills/` (MIT, see
     `.claude/skills/LICENSE-gstack.txt`); the rest of gstack is not installed. Run `/qa` at
     phone size before every M4 PR and put its results in the PR. Run `/design-review` once,
     at the end of M4: list its findings in the PR and don't apply any without the owner's
     go-ahead.
- **agent-skills.** Use its skills when they help inside a milestone.
- **Never** `/build auto`, and never create `SPEC.md` or `tasks/plan.md`.
