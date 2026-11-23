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

Pipeline steps (run in order, from the repo root, inside the env). Each step caches its output in `data/interim/` and is safe to re-run:

```bat
python -m mtlhousing boundaries      :: quartiers -> data/interim/quartiers.parquet
python -m mtlhousing sample-points   :: StatCan DAs -> residential sample points (first run ~10 s)
python -m mtlhousing osm-clip        :: Québec PBF -> Montréal PBF (~45 s, skipped if unchanged)
python -m mtlhousing gtfs-check      :: feed periods + validates config.ANALYSIS_DATE (exit 1 if not OK)
python -m mtlhousing tunnel-check    :: walk-only check: UdeM metro -> Roger-Gaudry through the tunnel
python -m mtlhousing travel-times --campus udem   :: r5py, ~25 min; JVM capped at 6 GB
python -m mtlhousing travel-times --campus udem --repair-only   :: re-route only homes that reached nothing
python -m mtlhousing aggregate --campus udem      :: per-quartier median/p10/p90, access adjustments, flags
python -m mtlhousing export                       :: web/public/data/*.json(geojson) for every campus with results + check maps
python -m mtlhousing validate --campus udem       :: R5 vs Google routes -> pipeline/validation/udem_results.csv
python -m mtlhousing access-check --campus udem   :: R5 platform -> building walks and the access adjustments they imply
python -m mtlhousing crosswalk-check  :: quartier -> CMHC neighbourhood -> zone, checked against CMHC unit counts (exit 1 on a problem)
python -m mtlhousing rent             :: rent estimate per quartier and bedroom type -> data/interim/rent_by_quartier.csv
python -m mtlhousing rent-export      :: re-checks the crosswalk, rounds to $25 -> web/public/data/rent.json (committed)
```

### Web

Requires Node 22.12+ (Vitest 5; CI uses Node 22). From the repo root:

```bat
cd web
npm ci
npm run dev        :: http://localhost:3000
npm test           :: Vitest: rent classes, labels and texts (web/lib/*.test.ts)
```

The page reads `web/public/data/neighbourhoods.geojson`, `commute.json` and `rent.json`
(written by the pipeline's `export` and `rent-export` steps and committed). It is still a bare
map: a Commute / Rent toggle; quartiers coloured by median UdeM commute (fastest building) or by
the estimated rent for a studio, 3½ or 4½; click for details. Basemap: OpenFreeMap (no API key).

## Status

See [docs/ROADMAP.md](docs/ROADMAP.md).

## Credits

Data sources and required attributions are listed in [DATA_SOURCES.md](DATA_SOURCES.md).
