## What changed

<!-- Milestone: Mx. One or two lines per change. Call out any removed files. -->

## How to test

<!-- Exact commands, from the repo root. Say which steps need local data or a long run. -->

```
conda run -n mtlhousing --cwd pipeline ruff check .
conda run -n mtlhousing --cwd pipeline ruff format --check .
conda run -n mtlhousing --cwd pipeline pytest
npm --prefix web run build
```

## Guesses I made

<!-- Every assumption the owner hasn't confirmed: data interpretation, thresholds, naming, scope. "None" if none. -->

## Checklist

- [ ] All tests pass locally (including `java` tests)
- [ ] `pr-reviewer` agent ran; blocking findings fixed
- [ ] No fake data; every new number has a source in DATA_SOURCES.md
- [ ] No `data/raw/`, `data/interim/` or secrets committed
