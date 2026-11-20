# [NAME]

A Montréal "where should I live?" tool for students and renters without a car.

Pick your campus (UdeM, McGill, Concordia SGW), apartment size (studio / 3½ / 4½),
maximum budget and maximum transit commute. The site shows:

- a map of Montréal neighbourhoods coloured by transit commute time,
- a ranked shortlist of 3–5 neighbourhoods that fit,
- a detail panel per neighbourhood: commute estimate, rent estimate, data source, date and reliability.

**Data honesty is rule #1.** Every number shows where it comes from, when, and how reliable it is.
When the data is too thin, the site says "not enough data" instead of guessing.
See [DATA_SOURCES.md](DATA_SOURCES.md) and [docs/methodology.md](docs/methodology.md).

## How it works

```
open data (manual downloads)          offline Python pipeline              static website
data/raw/  ───────────────────────►   pipeline/  (r5py, geopandas)  ──►   web/public/data/*.json
                                                                          web/  (Next.js + MapLibre)
```

Everything is precomputed. There is no routing server, database or account system in production.

## Repository layout

| Path | What |
|---|---|
| `data/` | Downloaded and intermediate data (gitignored) + `manifest.csv` (committed). See [data/README.md](data/README.md). |
| `pipeline/` | Python pipeline: boundaries, sample points, travel times, rent estimates, export. |
| `web/` | Next.js site (from Phase 1.5). Reads static JSON from `web/public/data/`. |
| `docs/` | Methodology and limitations. |

## Run

### Pipeline (Windows)

Prerequisite: [Miniforge](https://github.com/conda-forge/miniforge) (provides `mamba`/`conda`).
The environment brings its own Python 3.12 and OpenJDK 21, so it does not touch your system Java or Python.

Open **Miniforge Prompt** in the repo folder:

```bat
mamba env create -f pipeline\environment.yml
mamba activate mtlhousing
pip install -e pipeline --no-deps
pytest pipeline
```

To update the environment after `environment.yml` changes:

```bat
mamba env update -f pipeline\environment.yml --prune
```

Pipeline steps (`python -m mtlhousing <step>`) are added in Phase 1.

### Web

Added in Phase 1.5.

## Status

- [x] Phase 0: repo skeleton
- [ ] Phase 1: UdeM commute pipeline + manual validation
- [ ] Phase 1.5: ugly map
- [ ] Phase 2: other campuses, rent data, crosswalk, estimates
- [ ] Phase 3: web UI (form, map, shortlist, detail panel)
- [ ] Phase 4: FR/EN, sources page, shareable URLs, deploy

## Credits

Data sources and required attributions are listed in [DATA_SOURCES.md](DATA_SOURCES.md).
