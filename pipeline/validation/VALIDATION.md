# Validation: R5 vs Google Maps, UdeM (step 1.9)

**Result (second run, 2026-11-20, walking at 4.0 km/h): 8 of 9 comparisons pass.**
- **Route 4 fails** against Google's first suggestion (60 min), a different, slower trip. Against Google's like-for-like trip (green line + REM, 52 min) it passes with room to spare: −5.1 min against a 7.8-min tolerance. At 4.8 km/h it passed only at the limit.
- **On average R5 now matches Google:** the mean difference is +0.0 min without route 4, against −1.5 min at 4.8 km/h.
- **This is an in-sample result.** The walking speed and both access adjustments were tuned on these same routes (see [In-sample, not independent](#in-sample-not-independent)). Before launch, 3–4 out-of-sample routes will be added and checked with the settings frozen.

| File | Purpose |
|---|---|
| [`udem_routes.csv`](udem_routes.csv) | Inputs |
| [`udem_results.csv`](udem_results.csv) | Outputs |

Re-run:
- `python -m mtlhousing validate --campus udem` runs the comparisons.
- `python -m mtlhousing access-check --campus udem` re-derives the access adjustments.

## Method

**Google side.** The author collected the Google numbers on 2026-11-20:
- "Arrive by 8:30", Tuesday 2026-12-01, first suggested trip;
- for routes 3 and 4, the fastest trip listed is also recorded.

Google's time starts when you leave home for a well-timed trip, so it has no initial wait.

**R5 side.** The same settings as the published numbers (`travel_times.routing_kwargs`):
- departures every minute from 7:30 to 8:30, median over the window;
- transit + walk at **4.0 km/h**, origins snapped to the street network;
- the calibrated access adjustment for each building (`config.ACCESS_ADJUSTMENT_MIN`): **Roger-Gaudry +1.9 min, Jean-Brillant −2.4 min** (details below).

R5's median includes waiting at the first stop. The R5 **p10** is shown as a reference for a well-timed departure.

**Pass rule** (from the plan): |R5 median − Google| ≤ max(5 min, 15% of Google).

**Origins.**

| Routes | Source |
|---|---|
| 1, 3, 4, 7 | Author's Google Maps pins |
| 2 | OSM address node/4907803398 |
| 5 | REM GTFS parent station `ST_PTC_1` |
| 6 | STM GTFS metro stop `56`, Université-de-Montréal, where R5's blue-line trips end |
| 6b | STM GTFS metro stop `55`, Côte-des-Neiges, where R5's blue-line trips end |

## Why the settings changed after the first run

The first run (walking at 4.8 km/h, Roger-Gaudry penalty +2.2 min) passed 7 of 8 comparisons. Its leg-by-leg comparison of route 4 pointed to two causes.

**1. Walking speed.** Google's walk legs on these routes imply **3.75–4.3 km/h**:

| Walk | Google | Speed |
|---|---|---|
| To Joliette (route 4) | 900 m in 14 min | ~3.9 km/h |
| Édouard-Montpetit → Roger-Gaudry (route 4) | 1.0 km in 16 min | ~3.75 km/h |
| Platform → building (routes 6, 6b) | 500–650 m in 7–9 min | ~4.3 km/h |

R5 walked the same 900 m in 11.7 min. That accounted for about 5 of route 4's 7.7-min gap, including a missed REM. At 4.8 km/h R5 was faster than Google on 5 of 7 routes. The analysis date is also in winter. **Walking speed is now 4.0 km/h.**

**2. Not a cause: the Édouard-Montpetit transfer.** In route 4, Google walked 16 min on the surface instead of taking the blue line one stop. That suggested the deep REM → metro transfer was much slower than R5's 0.4 min. Google's route 5 details settle it:

| Time | Step |
|---|---|
| 8:03 | REM arrives at Édouard-Montpetit |
| | walk to the blue line, "about 1 min" |
| 8:10 | blue line departs (the rest of the gap is waiting) |
| 8:12 | arrives at Université-de-Montréal, 1 stop |
| 8:18 | arrives at Roger-Gaudry after a 6-min / 280 m walk |

So Google times the transfer at about 1 min. In route 4 it skipped the blue line because of the wait for it, not the transfer. **No Édouard-Montpetit correction is applied.**

**Access adjustments, both buildings calibrated the same way.** The target is the real walk from the metro platform where R5's trips end to the door. The adjustment is that target minus R5's walk-only time at 4.0 km/h (`access-check`).

| Building | Platform | Target, source | R5 walk | Adjustment |
|---|---|---|---|---|
| Roger-Gaudry | Université-de-Montréal (stop 56) | 7 min: author + Google (~7 min / 400 m) | 5.08 min / 332 m | **+1.9** |
| Jean-Brillant | Côte-des-Neiges (stop 55) | 7 min: Google (~7 min / 500 m) | 9.40 min / 613 m | **−2.4** |

- **First-run calibration error.** The first run calibrated Roger-Gaudry from STM stops 53877 / 53878. These are **bus stops** (lines 51, 155, 368) named "Station Université-de-Montréal", not the metro platform. It also left Jean-Brillant unadjusted, which biased the building split.
- **Why the signs differ.** R5 misses the climb to Roger-Gaudry (no elevation model). On the Jean-Brillant side, R5's path from the platform coordinate is longer than Google's.

## Results

| # | From (quartier) | To | Google | R5 median | R5 p10 | Diff | Tol. | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | 4500 Saint-Denis (Mile End) | Roger-Gaudry | 31 | 33.9 | 31.9 | +2.9 | 5.0 | pass |
| 2 | 4000 Wellington (Verdun-Centre) | Roger-Gaudry | 39 | 37.9 | 35.9 | −1.1 | 5.8 | pass |
| 3 | 1500 Fleury Est (Sault-au-Récollet) | Roger-Gaudry | 50 (fastest listed: 42) | 48.9 | 41.9 | −1.1 (+6.9) | 7.5 (6.3) | pass (**fail**) |
| 4 | 3800 Ontario Est (Hochelaga) | Roger-Gaudry | 60 (green + REM: 52) | 46.9 | 44.9 | −13.1 (−5.1) | 9.0 (7.8) | **fail** (pass) |
| 5 | Fairview–Pointe-Claire REM station | Roger-Gaudry | 41 | 44.9 | 38.9 | +3.9 | 6.1 | pass |
| 6 | Université-de-Montréal platform, walk only | Roger-Gaudry | 7 | 7.0 | — | 0.0 | 5.0 | pass (by construction) |
| 6b | Côte-des-Neiges platform, walk only | Jean-Brillant | 7 | 7.0 | — | 0.0 | 5.0 | pass (by construction) |
| 7 | 5800 Sherbrooke Ouest (Upper Lachine) | Jean-Brillant | 36 | 32.6 | 29.6 | −3.4 | 5.4 | pass |
| 7 | same | Roger-Gaudry | 35 | 33.9 | 31.9 | −1.1 | 5.2 | pass |

- All times are in minutes and include the access adjustments; raw R5 values are in the CSV.
- Values in brackets compare against Google's alternative trip (routes 3 and 4). The verdict uses the first suggested trip, as the plan specifies.

**Compared with the first run (4.8 km/h):** R5 medians rose by 0.6–2.7 min on the transit routes. Every first-suggestion comparison except route 4 still passes, now closer to Google on average.

**R5's route at 7:45** (one sample departure):
1. Walk 3 → orange line Mont-Royal → Jean-Talon → blue line → Université-de-Montréal → walk 5. This is the same pattern as Google (orange → blue).
2. Walk 5 → green line De l'Église → Peel → walk 5 → REM McGill → Édouard-Montpetit → blue line, 1 stop → walk 5. Google takes green → orange → blue. Both paths are close in time, and R5's choice depends on the departure minute.
3. Bus 41 → Sauvé → orange line → Jean-Talon → blue line. Same pattern as Google (bus + metro).
4. Walk 14 → green line Joliette → Peel → walk 5 → REM McGill → Édouard-Montpetit → blue line, 1 stop → walk 5. This is Google's "green + REM" pattern, except that Google gets off the green line at McGill and walks from Édouard-Montpetit.
5. REM Fairview → Édouard-Montpetit → walk 1 → blue line, 1 stop → walk 5. This is Google's trip. The 1-min transfer matches Google's "about 1 min".
6. Walk only, 5.1 min / 332 m from stop 56.
6b. Walk only, 9.4 min / 613 m from stop 55.
7. Bus 105 → Vendôme → orange line → Snowdon → blue line. For Jean-Brillant: Côte-des-Neiges → walk 9. For Roger-Gaudry: Université-de-Montréal → walk 5.

At 4.0 km/h, R5's walk to Joliette in route 4 (14 min) matches Google's 14 min.

## Findings

### 1. Walking speed was the systematic bias; at 4.0 km/h R5 matches Google on average

| | 4.8 km/h | 4.0 km/h |
|---|---|---|
| Mean R5 median − Google, routes 1–3, 5, 7 (first suggestion) | −1.5 min | **+0.0 min** |
| R5 median below Google (all 7 transit comparisons) | 5 of 7 | 5 of 7, but 4 of them by ≤ 3.4 min |
| Route 4 against its like-for-like trip (52) | −7.8 (limit 7.8) | **−5.1** (limit 7.8) |

R5's well-timed departure (p10) is still at or below Google, except on route 1 (+0.9). That is expected: p10 is a lucky departure, while Google plans a well-timed trip with real-world slack:

| Route | p10 − Google |
|---|---|
| 1 | +0.9 |
| 2 | −3.1 |
| 3 | −8.1 (−0.1 against the fastest listed) |
| 4 | −15.1 (−7.1 against the 52-min trip) |
| 5 | −2.1 |
| 7, Jean-Brillant | −6.4 |
| 7, Roger-Gaudry | −3.1 |

### 2. Route 4: what is left is Google's choice of a slower first trip

- Against Google's like-for-like 52-min trip (green line + REM), R5's median is 46.9 (−5.1), well inside the tolerance.
- The first suggestion (60 min) is a different trip.
- The remaining gap to the 52-min trip has two parts:
  - Google waits 5 min for the REM at McGill;
  - Google walks 16 min from Édouard-Montpetit, where R5 takes the blue line one stop.

  Neither is a modelling error that a setting would fix.

### 3. Route 3: the median matches the first trip; p10 matches the fastest trip

- Against the first suggestion (50), R5's median is 48.9: pass.
- Against the fastest trip listed (42), the median fails by 0.6 min beyond the tolerance (+6.9 against 6.3).
- R5's p10 is 41.9, exactly the fastest listed trip. That trip is a well-timed bus connection. R5's median includes waiting for bus 41 or 140 across the hour, which Google's fastest trip does not.
- This was a pass at 4.8 km/h only because walking was too fast. The verdict uses the first suggestion, as the plan specifies.

### 4. Building split: still a near-tie, now calibrated symmetrically

- **Route 7:** Google has Roger-Gaudry 35, Jean-Brillant 36. R5 has Jean-Brillant 32.6, Roger-Gaudry 33.9. The tools still disagree on the faster building, by about 1 min.
- **Citywide, Jean-Brillant is now the faster building for 66% of dwellings.** It was 32% in the first run, which had no Jean-Brillant adjustment.
- **But the gap is small almost everywhere.** For the median home, Roger-Gaudry minus Jean-Brillant is +0.3 min. For **58% of dwellings the two buildings are within 1 min** of each other.
- Homes arriving from the west on the blue line (Snowdon side) reach Côte-des-Neiges first and favour Jean-Brillant. Roger-Gaudry is faster for 34% of dwellings, mostly by under 1 min (the 10th and 25th percentiles of the gap are both −0.7 min).

The "fastest building" time is robust, because it is the minimum of two near-equal times. **Which building wins for a given home is not**, and the site must not present it as a clear result.

### 5. Routes 6 and 6b are the calibration, not independent evidence

The adjustments are defined so that these two walks come out at exactly 7.0 min. Routes 1–5 and 7 are the independent tests.

## In-sample, not independent

Every setting that changed after the first run was tuned on these routes:
- **Walking speed (4.0 km/h)** was chosen from Google's walk legs on routes 1–5 and 7, and from R5's bias on those same routes at 4.8 km/h.
- **The access adjustments (+1.9 / −2.4)** were set so that routes 6 and 6b come out at exactly 7.0 min.

So the +0.0 min mean difference shows that the settings fit these routes. It does not show how well they predict other trips. The pass count is likely optimistic.

**Before launch:** add 3–4 out-of-sample routes, chosen and collected from Google before R5 is run on them, and check them with the settings frozen (no re-tuning on the result). They should cover areas the current set misses, for example the West Island, the far east (Rivière-des-Prairies / Pointe-aux-Trembles), a REM-only trip and a bus-only trip. If they fail, the failure is reported, not tuned away.

## Status

**Phase 1 validation is closed (2026-11-20), in-sample.** Every first-suggestion comparison passes except route 4. Route 4 passes against Google's like-for-like trip and is explained (finding 2). The out-of-sample check above is still to do before launch.

Known limits, documented in `docs/methodology.md`:
- **Flat walking.** There is no elevation model. Constant per-building adjustments stand in for the climb at UdeM.
- **No station models.** The feeds have no `pathways.txt`, so R5 times transfers as street walks between stop coordinates. At Édouard-Montpetit that gives 1 min, which agrees with Google.
- **Building choice is a near-tie** for most homes (finding 4).

## McGill and Concordia (M3)

Route lists: [`mcgill_routes.csv`](mcgill_routes.csv) and [`concordia_sgw_routes.csv`](concordia_sgw_routes.csv).
- **Five transit origins per campus**, reused from the UdeM list. McGill: routes 1–5. Concordia: routes 1, 2, 3, 7 (as its route 4) and 5. They have the same coordinates as the UdeM rows.
- **One platform → entrance walk per campus:**
  - McGill metro → Roddick Gates (STM stop 32);
  - Guy-Concordia → Hall Building (STM stop 34). Google's walk is outdoors via De Maisonneuve; nothing shows which path R5 takes.

**Google side.** Collected on 2026-11-23 through Google Maps in the owner's browser, by Claude (chat) for the owner. Same method as for UdeM: "Arrive by 8:30", Tuesday 2026-12-01, first suggested trip.

| Route | McGill → Roddick Gates | Concordia → Hall Building |
|---|---|---|
| 1 Saint-Denis | 22 min (orange → green) | 22 min (orange → green) |
| 2 Wellington, Verdun | 21 min (green) | 17 min (green) |
| 3 Fleury Est | 55 min (bus 121 → REM A4-A1) | 53 min (bus 13 → orange → green) |
| 4 | Ontario Est: 30 min (green from Joliette) | 5800 Sherbrooke O (NDG): 34 min (bus 105 → orange → green) |
| 5 Fairview-Pointe-Claire REM | 33 min (REM A3-A1) | 42 min (REM A3-A1, 13 min walking) |
| 6 walk | McGill station → Roddick Gates: 4 min / 250 m, via McGill College | Guy-Concordia → Hall: 3 min / 180 m, outdoors via De Maisonneuve |

**The two walks are a lower bound.** Google starts them at the station's **street entrance** (its geocode), not at the platform, and routes them **outdoors**, not through the tunnel. Platform to street adds about **1–2 min** (owner). When deciding whether a campus needs an access adjustment, compare R5's platform walk with the Google time **plus 1–2 min**, not with the raw number. The routes files carry that target in `walk_target_min`, the midpoint: McGill 5.5 min, Concordia 4.5 min. `access-check` calibrates against it, and falls back to `google_min` for UdeM, whose walks were measured from the platform.

**R5 side.** The settings stay as tuned on UdeM: walking at 4.0 km/h, the same window and the same feeds. These comparisons are therefore not used to re-tune them. The platform walks show whether either campus needs an access adjustment like UdeM's. If one is added, it is calibrated on that walk, which makes the walk route in-sample.

### Results (2026-11-23, settings frozen at 4.0 km/h)

Travel times were routed by the owner in his own terminal on 2026-11-23: 3,219 origins, complete. The unreachable homes are 2 for McGill and 4 for Concordia, all in L'Île-Bizard–Sainte-Geneviève (as for UdeM). Files: [`mcgill_results.csv`](mcgill_results.csv), [`concordia_sgw_results.csv`](concordia_sgw_results.csv).

| Route | McGill: Google / R5 median (p10) | verdict | Concordia: Google / R5 median (p10) | verdict |
|---|---|---|---|---|
| 1 Saint-Denis | 22 / 21.0 (19.0) | pass | 22 / 21.6 (20.6) | pass |
| 2 Wellington | 21 / 24.0 (23.0) | pass | 17 / 20.6 (18.6) | pass |
| 3 Fleury Est | 55 / 47.0 (42.0) | pass | 53 / 48.6 (43.6) | pass |
| 4 | Ontario Est: 30 / 31.0 (30.0) | pass | NDG: 34 / 31.6 (29.6) | pass |
| 5 Fairview REM | 33 / 40.0 (35.0) | **fail** (+7.0, tolerance 5) | 42 / 47.6 (41.6) | pass |
**Transit routes: McGill 4 of 5, Concordia 5 of 5.** Over those five, the mean R5 − Google difference is +0.4 min for both campuses (UdeM: +0.0). Two pass by a thin margin: McGill route 3 (−8.0 against a tolerance of 8.2; R5 takes bus 41 → orange → green, Google 121 → REM) and Concordia route 5 (+5.6 against 6.3).

**The walks are not counted in that tally.** Under the 5-min minimum tolerance, any R5 walk from 0 to 9 min would "pass". Each walk is judged against its range instead:
- McGill: R5 5.4 min, against a range of 5–6.
- Concordia: R5 2.9 min, against a range of 4–5. The +1.6 adjustment brings it to 4.5, but that is the calibration itself, not a check.

**McGill route 5 fails, and is explained, not tuned.** At 7:45, R5 takes Google's trip: REM A3-A1 from Fairview-Pointe-Claire to McGill station, then a 4-minute walk. The gap is most likely the wait at the first stop, as R5's p10 (35 min, 2 min from Google) suggests. R5's median runs over departures from 7:30 to 8:30, so it includes waiting for the REM. Google's "arrive by 8:30" trip leaves at the right moment. The 7:45 itinerary itself shows only a 1-minute wait, so this explanation is inferred, not shown. It is the same R5-vs-Google effect described for UdeM (see Method).

**Concordia trips from the east: the printed itinerary is not the path behind the median.** For routes 1, 3 and 5 (arriving westbound on the green line), the 7:45 itinerary in `concordia_sgw_results.csv` gets off at **Peel and walks 9 min**, not at Guy-Concordia (one stop later, 3 min walk). The STM data is normal: westbound trains stop at Guy-Concordia (stop 34) one minute after Peel, with no drop-off restriction. Two things show the published numbers don't use the Peel path:
- R5 listed all 60 itinerary options for route 1 at 7:45 (2026-11-23). All of them end at Peel, at 24.7–28.7 min.
- R5's travel-time median for that route is 20.0 min before the adjustment, faster than any of those options.

So the travel-time matrix must use a faster exit, most likely Guy-Concordia. The Peel trips appear only in r5py's itinerary listing, which validation prints for reference. Why the itinerary router never ends westbound trips at Guy-Concordia is not known. The +1.6 adjustment assumes the matrix's trips end at Guy-Concordia, which this supports but does not prove.

**Access adjustments** (`config.ACCESS_ADJUSTMENT_MIN`). Each is judged against Google's walk **plus 1–2 min** from platform to street, as the owner noted:
- **McGill: none.** Google gives 4 min from the street entrance, so the real walk is 5–6 min. R5 walks 357 m from the platform (STM stop 32) in 5.43 min, inside that range (`access-check`: +0.1 against 5.5).
- **Concordia: +1.6 min.** Google gives 3 min / 180 m from the street entrance, outdoors, so the real walk is 4–5 min; the midpoint is 4.5. R5 walks 184 m from the platform (STM stop 34) in 2.87 min. 4.5 − 2.87 = +1.6. This walk route is now in-sample: the adjustment was calibrated on it.

Re-run, after the heavy `travel-times` runs:
- `python -m mtlhousing validate --campus mcgill`
- `python -m mtlhousing access-check --campus mcgill`
- the same two commands with `--campus concordia_sgw`.
