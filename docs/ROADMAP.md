# Roadmap

One milestone = one branch + one PR (see [CLAUDE.md](../CLAUDE.md)). Before each milestone,
Claude lists what it needs from the owner. **Needs owner** marks work that can't happen without
them: heavy local runs, approvals, deploys.

| Milestone | Scope | Status |
|---|---|---|
| **M2.3** Crosswalk | Quartier → CMHC neighbourhood → zone, verified from CMHC unit counts | done (PR #3) |
| **M2.4** Rent estimate per quartier | Ratio (CMHC neighbourhood ÷ CMA) × StatCan citywide level; split quartiers with the ≥ 80% re-weighting rule; fallbacks; grade labels | done (PR #5) |
| **M2.5** Rent export | `rent.json` for the site + the Rent section of `docs/methodology.md` | done |
| **M2.6** Rent on the map | A rent layer on the map | next |
| **M3** McGill + Concordia commutes | Travel times for the other two campuses. **Needs owner:** heavy local run, at home | |
| **M4** Real site | Form (campus, apartment size, budget, max commute), ranked shortlist, detail panel; mobile-first. Before starting, review garrytan/gstack's /design-review and /qa skills; copy useful parts into .claude/, don't install the whole toolkit. | |
| **M5** Languages, sources, sharing | French/English, sources & limitations page, shareable URL holding the search settings | |
| **M5.5** Auto-refresh | See below | |
| **M6** Launch | Out-of-sample validation (3–4 new Google routes, collected *before* running R5; settings frozen; failures reported, not tuned); refresh before launch (GTFS, and check for a newer StatCan quarter); deploy to Vercel. **Needs owner:** OK to deploy | |

## M5.5 Auto-refresh

1. **`refresh-feeds` step.** Downloads the STM, REM and exo GTFS from their fixed URLs (check
   the current official URLs first), validates them, and updates `data/manifest.csv`. If a
   download fails or a file looks wrong, it stops and reports. It never reuses old data
   silently.
2. **Weekly GitHub Actions workflow.** Light, no routing. Checks whether any feed changed or
   expires within 30 days, and opens an Issue if so.
3. **One `refresh` command.** Runs the full rebuild end to end (new analysis date,
   travel-times, aggregate, export, validate) and opens a PR summarising how the commute
   numbers changed.

Heavy routing stays a local run the owner triggers at home; CI never routes.
