# Roadmap

One milestone = one branch + one PR (see [CLAUDE.md](../CLAUDE.md)). Before each milestone,
Claude lists what it needs from the owner. **Needs owner** marks work that can't happen without
them: heavy local runs, approvals, deploys.

| Milestone | Scope | Status |
|---|---|---|
| **M2.3** Crosswalk | Quartier → CMHC neighbourhood → zone, verified from CMHC unit counts | done (PR #3) |
| **M2.4** Rent estimate per quartier | Ratio (CMHC neighbourhood ÷ CMA) × StatCan citywide level; split quartiers with the ≥ 80% re-weighting rule; fallbacks; grade labels | done (PR #5) |
| **M2.5** Rent export | `rent.json` for the site + the Rent section of `docs/methodology.md` | done (PR #6) |
| **M2.6** Rent on the map | A rent layer on the map | done (PR #8) |
| **M2.7** (optional) Old-lease bias | Investigate CMHC vacant-unit rents by zone to correct the old-lease bias (see `docs/methodology.md`, Rent, "Known limitation: old leases") | optional, parked until after M4 |
| **M3** McGill + Concordia commutes | Travel times for the other two campuses (downtown campuses only: Roddick Gates, Hall Building; Macdonald and Loyola out of scope for now). **Needs owner:** Google times for validation, heavy local run, at home | done (PR #10) |
| **M4** Real site | Form (campus, apartment size, budget, max commute), ranked shortlist, detail panel; mobile-first. Before starting, review garrytan/gstack's /design-review and /qa skills; copy useful parts into .claude/, don't install the whole toolkit. Impeccable wins over gstack: take from gstack only what Impeccable doesn't do (likely browser QA). First screen: one-line explanation ('Find where to live in Montréal without a car') + the search form (campus, size, budget, max commute) + 'Show me neighbourhoods' button, no sign-up. Results: ranked shortlist cards first (name, commute, rent, reliability badge), map second. An 'example search' link. Short 'How it works' + honest data line + link to sources. The map is the results view, not the homepage. Decisions: see "M4 decisions" below. | |
| **M5** Languages, sources, sharing | French/English, sources & limitations page (must include: the old-lease bias, i.e. CMHC averages include long-time tenants, so old-stock areas look cheaper and new-build areas pricier than new listings; R5 itinerary vs matrix mismatch for Concordia east trips (Peel exit); McGill route 5: R5 counts waiting time, Google doesn't), shareable URL holding the search settings | |
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

## M4 decisions

Decided by the owner (2026-11-23), on top of the M4 row above:

1. **Shortlist order:** fastest commute first by default, with a "sort by cheapest" toggle.
   Sorting happens **within each group** (fits / slightly over budget / not enough data): the
   groups are the budget answer, and sorting keeps them intact.
2. **Budget:** compare the **rounded rent the user sees** with the budget. A rent shown as
   ≈ $1,400 with a $1,400 budget is within budget (rounded rent ≤ budget). "Slightly over
   budget" means up to 10% above the budget (budget < rounded rent ≤ budget × 1.10); those
   are shown under that heading, below the ones that fit. Above that, hidden.
3. **No rent data:** still shown, at the bottom, marked **"Not enough data"**, the same label
   as on the map (one name for one thing). Unknown rent only means the budget can't be
   checked.
4. **Max commute:** buttons 20 / 30 / 45 / 60 min (no slider). It is a **hard filter** for
   every neighbourhood, including those with no rent data. Neighbourhoods with **missing
   commute data** are hidden by it too, with one line under the results saying how many were
   hidden and why.
5. **Rooms:** there is one citywide figure, so neighbourhoods can't be compared on room rent.
   Show a single note ("Room rent: ≈ $725 citywide, same estimate everywhere") and sort by
   commute only. Don't pretend the figure varies by neighbourhood.
   - **The budget does not filter rooms:** show all neighbourhoods, sorted by commute. If the
     budget is under the citywide room figure, show a warning that typical room rent is
     above their budget and we can't tell where cheaper rooms are.
   - **Wording:** the short note in the results; the methodology's room line in "How it
     works" and on the sources page. The number always comes from the data file
     (`rent.json`), never typed into the text.
6. **Language:** English and French both at launch, with an FR/EN switch. M4 keeps every UI
   string in one place (no hard-coded text in components) so M5 only adds the French file.

Added by the owner (2026-11-23), when M4 started:

7. **Sizes:** Room / Studio / 3½ / 4½. The site name stays a placeholder until M6.
8. **Budget is optional.** With no budget: sort by commute, no budget groups.
9. **The map is never the default results view.** Shortlist cards come first; the map is a
   second view the user switches to. The map-first page must not be the first thing people
   see (since M4.1 it lives at `/map`).
10. **M4.2 tests:** unit tests for the grouping and sorting logic: exactly at budget,
    rounding to $25, just under and just over 10%, rent "Not enough data", rooms (no budget
    filter + warning), missing commute hidden with the count line, sort within groups.
11. **M4 in three PRs:** M4.1 design system, strings file, layout, first screen; M4.2 search,
    grouped and sorted shortlist, detail panel; M4.3 map as the results' second view,
    example-search link ("UdeM, 3½, $1,500, 45 min"), How it works, data line, then
    `/design-review` once.

Added by the owner (2026-11-24), reviewing M4.2:

12. **Commute filter on the minutes shown:** a 45.4-min median shows as 45 and passes a
    45-min max; 45.6 shows as 46 and doesn't (same rule as the budget's rounded rent).
13. **No budget:** one list in commute order, no groups and no "cheapest" order. A
    neighbourhood with no rent data keeps its "Not enough data" badge in its commute place
    (decision 3's bottom group is for searches with a budget).
14. **First 5 per group,** then "Show N more", for every group.
15. **Over budget by more than 10%:** hidden, with a count line ("N more neighbourhoods are
    more than 10% over your budget."). If nothing is left, name the cheapest one.
16. **Reliability on cards:** one line above the list ("All rents are estimates."); badges
    only for real caveats (wider-area estimate, low reliability, not enough data). Plain
    "Estimate" is not repeated on every card.
17. **Commute detail:** door-to-door time, the range for most homes and, for UdeM, each
    building's time. The schedule date and the access adjustments are explained in How it
    works (M4.3), not in the panel.
