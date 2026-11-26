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
| **M5** Languages, sources, sharing | French/English, sources & limitations page (must include: the old-lease bias, i.e. CMHC averages include long-time tenants, so old-stock areas look cheaper and new-build areas pricier than new listings; R5 itinerary vs matrix mismatch for Concordia east trips (Peel exit); McGill route 5: R5 counts waiting time, Google doesn't), shareable URL holding the search settings; decide whether to restyle `/map` (the old explorer, no longer linked since M4.3) or delete it | |
| **M5.5** Auto-refresh | See below | |
| **M6** Launch | Out-of-sample validation (3–4 new Google routes, collected *before* running R5; settings frozen; failures reported, not tuned); refresh before launch (GTFS: `refresh-feeds`, then `refresh --date` with a winter-term Tuesday or Wednesday after the STM change of 2027-01-05, about 50 min of routing; and check for a newer StatCan quarter); the transit credit wording in `commute.json` ("licensed under CC BY 4.0") is fixed (M5.3a bilingual export, M5 decision 5); `/sources` links `pipeline/validation/VALIDATION.md` on GitHub (owner, 2026-11-26: the repo goes public before M5.5); deploy to Vercel; after deploy, send one results link in WhatsApp, Messenger, iMessage, Discord and Telegram and check the preview. **Needs owner:** the site's name (the site has no name yet; every "[NAME]" placeholder must be replaced before launch; link previews show it from og:site_name, not in the title, so its length is free, owner M5.3b); the contact email on `/sources` (the "[EMAIL]" placeholder); the site's domain, so the pages' language alternates (hreflang) and canonical links become absolute (`metadataBase`, M5.3b); OK to deploy | |

## M5.5 Auto-refresh

Goal (owner): make the January STM/REM refresh in M6 one command instead of a manual afternoon.

1. **`refresh-feeds` step.** Downloads the STM, REM and exo GTFS from their fixed URLs
   (`config.GTFS_URLS`; the STM's fixed URL was checked against its open-data page on
   2026-11-25), checks each file (a zip, the files routing needs, version and service
   period), and only if all three pass archives the previous files to
   `data/raw/gtfs/archive/` (gitignored; the manifest records versions), puts the new ones in
   place and updates `data/manifest.csv`. Any failure stops before anything is replaced. It
   never reuses old data silently. `--check` only reports whether a feed changed or ends
   within 30 days.
2. **Weekly GitHub Actions workflow** (`.github/workflows/feeds.yml`, owner). Runs only
   `refresh-feeds --check` (no routing) and opens an Issue, or updates the open one, when a
   feed changed or ends within 30 days. No automatic PR (owner).
3. **One `refresh --date YYYY-MM-DD` command.** Checks the date in every feed (gtfs-check)
   before writing it to `pipeline/analysis.json`, then runs travel-times and aggregate for
   every campus, export, and validate (reference only: the Google times are for their own
   day, so the copy goes to `data/interim/refresh/`), and writes a change report (per campus,
   how the medians moved; neighbourhoods that moved 5 min or more; unreachable shares that
   moved 5 points or more) to paste in the PR. `--no-download` uses the feeds already in
   `data/raw/gtfs`. Rents are out of scope (a newer StatCan quarter stays a manual check in M6).

**Proof run** (owner, 2026-11-26): `refresh --date 2026-12-01 --no-download` on the pinned
feeds reproduced every published number ("No commute number changed"; `commute.json` differed
only in its timestamps) and the three validation results byte for byte (UdeM 8 of 9, McGill
5 of 6, Concordia 6 of 6, walks included). Routing took 1,222 s (UdeM) + 894 s (McGill) + 904 s
(Concordia), about 50 min.

Heavy routing stays a local run the owner triggers at home; CI never routes. The analysis
date for January is chosen in M6.

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

Added by the owner (2026-11-24), starting M4.3:

18. **Budget field:** any whole dollar (no $25 steps). It is still compared with the rounded
    rent the user sees (decision 2).
19. **Rent detail:** "adjusted to current Montréal asking rents" is said once, in the line under
    every estimate, not again in the CMHC detail line.

## M5 decisions

Decided by the owner (2026-11-24), on top of the M5 row above:

1. **Three PRs, in this order:** M5.1 the `/map` decision and the shareable URL; M5.2 the
   sources & limitations page (English); M5.3 French for everything and the FR/EN switch.
2. **Process:** `/qa` at phone size before every M5 PR, Impeccable on every screen, and
   `/design-review` once at the end of M5 (report only).
3. **`/map` is deleted** (the results map covers it). The M5.1 PR lists every removed file.
4. **Shareable URL:** a "Copy link" button on the results; clean links (no empty `budget=`, no
   `open=`; `view` and `sort` kept); link previews with text only (title and description, no
   image); the language in the link (with M5.3). No link shortener, no analytics.
5. **Data-file texts in two languages:** the pipeline exports both languages (grade words,
   credits, campus names), with a test proving the re-export changes only text fields, never a
   number. This also fixes the transit credit wording ("licensed under CC BY 4.0").
6. **Official French wording** for credits and CMHC's grade labels comes from the publishers'
   own French pages, each cited.
7. **Languages in the URL:** French is the default at `/`, English at `/en/…`. No automatic
   redirect by browser language. The FR/EN switch keeps the current search.
8. **French formats:** Québec style: "1 500 $", "≈ 1 475 $", "7 h 30", "mardi 1er décembre
   2026"; "3½" and "4½" unchanged.
9. **French review:** Claude drafts; the owner reviews the French before each PR.
10. **CMHC area names** stay as CMHC publishes them, in both languages.
11. **`/sources` contents:** the three required limitations (old-lease bias, Concordia Peel-exit
    mismatch, McGill route 5), every source with link, licence and date, the validation summary,
    the commute and rent limits, and an **About** block: "Not affiliated with UdeM, McGill,
    Concordia, STM, REM, exo, CMHC or Statistics Canada", plus a contact line with a placeholder
    email the owner fills in before launch.
12. **Validation numbers** on `/sources` are dated facts citing `pipeline/validation/VALIDATION.md`.
13. **`/sources`** is where the footer's "Sources" link points; How it works keeps one line linking
    there instead of its own credits list.
14. **M2.7** (old-lease correction) stays parked; `/sources` says the effect isn't measured yet.
