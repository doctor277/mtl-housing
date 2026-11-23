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

CI (`.github/workflows/ci.yml`, job `ci`) runs ruff, `pytest -m "not java"` and the web build
on every PR. Tests that start the JVM carry `@pytest.mark.java`; mark any new ones the same way.

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
