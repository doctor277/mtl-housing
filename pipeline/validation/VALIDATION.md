# Validation: R5 vs Google Maps, UdeM (step 1.9)

> **Update (2026-11-20): this page describes the first run, at 4.8 km/h.** Google's route 5 details time the REM → blue line transfer at Édouard-Montpetit at about 1 min (REM arrives 8:03, "about 1 min" walk, blue line at 8:10, 1 stop, walk 6 min / 280 m, arrive 8:18). So the deep-transfer hypothesis in finding 1 is dropped: in route 4, Google skipped the blue line because of the blue-line wait, not the transfer. The systematic bias is walking speed. Walking speed is now **4.0 km/h** and the Roger-Gaudry penalty **1.2 min** (`config.py`); the re-run and re-validation are pending, and this page will be rewritten with their results.

**Result: 7 of 8 comparisons pass. Route 4 passes only against Google's like-for-like trip (green + REM, 52 min), at the limit of the tolerance; it fails against Google's first suggestion (60 min).** Its leg-by-leg comparison shows two R5 biases: deep-station transfers and walking speed (finding 1). Phase 1 stays open until we decide what to do about them.

- Inputs: [`udem_routes.csv`](udem_routes.csv)
- Outputs: [`udem_results.csv`](udem_results.csv)
- Re-run: `python -m mtlhousing validate --campus udem`

## Method

**Google side.** The author collected the Google numbers on 2026-11-20:
- "Arrive by 8:30", Tuesday 2026-12-01, first suggested trip;
- for routes 3 and 4, the fastest trip listed is also recorded.

Google's time starts when you leave home for a well-timed trip, so it has no initial wait.

**R5 side.** The same settings as the published numbers (`travel_times.routing_kwargs`):
- departures every minute from 7:30 to 8:30, median over the window;
- transit + walk at 4.8 km/h, origins snapped to the street network;
- the calibrated access penalty added for Roger-Gaudry (+2.2 min).

R5's median includes waiting at the first stop. The R5 **p10** is shown as a reference for a well-timed departure.

**Pass rule** (from the plan): |R5 median − Google| ≤ max(5 min, 15% of Google).

**Origins.**

| Routes | Source |
|---|---|
| 1, 3, 4, 7 | Author's Google Maps pins (route 4 was first routed from OSM way/224941530, 20 m away: 43.2 min) |
| 2 | OSM address node/4907803398 |
| 5 | REM GTFS parent station `ST_PTC_1` |
| 6 | STM platform stops 53877 / 53878, where R5's metro trips end |

## Results

| # | From (quartier) | To | Google | R5 median | R5 p10 | Diff | Tol. | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | 4500 Saint-Denis (Mile End) | Roger-Gaudry | 31 | 32.2 | 30.2 | +1.2 | 5.0 | pass |
| 2 | 4000 Wellington (Verdun-Centre) | Roger-Gaudry | 39 | 36.2 | 34.2 | −2.8 | 5.8 | pass |
| 3 | 1500 Fleury Est (Sault-au-Récollet) | Roger-Gaudry | 50 (fastest listed: 42) | 46.2 | 41.2 | −3.8 (+4.2) | 7.5 (6.3) | pass (pass) |
| 4 | 3800 Ontario Est (Hochelaga) | Roger-Gaudry | 60 (green + REM: 52) | 44.2 | 41.2 | −15.8 (−7.8) | 9.0 (7.8) | **fail** (pass, at the limit) |
| 5 | Fairview–Pointe-Claire REM station | Roger-Gaudry | 41 | 44.2 | 38.2 | +3.2 | 6.1 | pass |
| 6 | UdeM metro platform, walk only | Roger-Gaudry | 7 | 7.0 | — | 0.0 | 5.0 | pass (by construction) |
| 7 | 5800 Sherbrooke Ouest (Upper Lachine) | Jean-Brillant | 36 | 32.0 | 29.0 | −4.0 | 5.4 | pass |
| 7 | same | Roger-Gaudry | 35 | 32.2 | 30.2 | −2.8 | 5.2 | pass |

All times are in minutes. Roger-Gaudry times include the +2.2 min penalty; raw values are in the CSV.

**R5's route at 7:45** (one sample departure):
1. Walk 3 → orange line Mont-Royal → Jean-Talon → blue line → Université-de-Montréal → walk 4. This is the same pattern as Google (orange → blue).
2. Green line De l'Église → Lionel-Groulx → orange line → Snowdon → blue line → Université-de-Montréal. Same pattern as Google.
3. Bus 140 → Sauvé → orange line → Jean-Talon → blue line.
4. Walk 11 → green line Joliette → McGill → walk to REM McGill → REM → Édouard-Montpetit → blue line, 1 stop → walk 4. This is the same pattern as Google's 52-min "green + REM" trip.
5. REM Fairview → Édouard-Montpetit → blue line, 1 stop → walk 4. Same pattern as Google (REM → blue).
6. Walk only. R5 walks 4.6 min / 357 m from stop 53877 and 5.1 min / 395 m from stop 53878.
7. Bus 105 → Vendôme → orange line → Snowdon → blue line → Côte-des-Neiges → walk 8 for Jean-Brillant; Université-de-Montréal → walk 4 for Roger-Gaudry.

## Findings

### 1. Route 4: same pattern as Google, but R5 is faster on walks and at Édouard-Montpetit

Google's 52-min trip and R5 leaving at the same minute (7:36) from Google's pin. R5 times are raw; the +2.2 Roger-Gaudry penalty is added at the end.

| Leg | Google | R5 | Google − R5 |
|---|---|---|---|
| Walk to Joliette | 14 min, 900 m | 11.7 min, 902 m | +2.3 |
| Wait + green line Joliette → McGill | 0 + 11 | 1.1 + 10.0 | −0.1 |
| Walk to REM McGill | ~3 | 2.5, 199 m | +0.5 |
| Wait for REM | 5 (arrives 8:04, train 8:09) | 2.5 | +2.5 |
| REM McGill → Édouard-Montpetit | 3 ("Elevator out") | 2.8 | +0.2 |
| Édouard-Montpetit → Roger-Gaudry | **walk 16 min, 1.0 km on the surface** | **transfer 0.4 + wait 4.8 + blue line 2.0 + walk 4.3 + penalty 2.2 = 13.7** | +2.3 |
| **Total** | **52 (arrive 8:28)** | **44.3 (arrive 8:20)** | **+7.7** |

**What the legs show:**
- **Walking speed.** On the same 900 m, Google walks 14 min, about 3.9 km/h. R5 walks 11.7 min at the configured 4.8 km/h. Google's 1.0 km out of Édouard-Montpetit takes 16 min (3.75 km/h, including the elevator); R5's own surface walk on that route is 13.4 min for 1,045 m. Being slower, Google also reaches McGill later and misses a REM, which explains the extra REM wait. **About 5 of the 7.7 min trace back to walking speed.**
- **The Édouard-Montpetit transfer.** Google does not take the blue line at Édouard-Montpetit; it prefers a 16-min surface walk. R5 times that transfer at 0.4 min / 36 m, because the REM platforms are about 20 m from the metro stop on a flat map. Neither feed has `pathways.txt`, `levels.txt` or `transfers.txt`. For Google to prefer the walk, the transfer path must cost more: transfer + blue-line wait + 1 stop (~2 min) + its 7-min platform → Roger-Gaudry walk ≥ 16, so **transfer + wait ≥ ~7 min**.
- **The McGill transfer is fine:** Google ~3 min, R5 2.5 min.

**Verdict.** Against Google's like-for-like trip (52), R5's median is 44.2 (−7.8, tolerance 7.8), so it passes, but only just. The 60-min first suggestion was a different, slower trip.

**Why it matters beyond one route.** Many homes' best R5 trips use REM → Édouard-Montpetit → blue line. In the itinerary samples from step 1.9 this included Mercier–Hochelaga, Milton-Parc, the West Island and Cartierville. Their medians are optimistic by roughly the missing transfer time. How much each quartier would change still needs to be measured.

### 2. R5 is optimistic overall, not pessimistic

We expected R5 medians to come out above Google, because Google leaves out the initial wait. Instead:
- **The median is below Google in 5 of 7 transit comparisons.** Mean difference: −1.5 min without route 4, −3.5 min with it (against its first suggestion).
- **R5's well-timed departure (p10) is faster than Google in every comparison:** −0.8, −4.8, −8.8 (−0.8 against the fastest listed), −10.8 against the 52-min trip, −2.8, −7.0 and −4.8 min.

**Likely contributors** (from route 4's leg breakdown):
- **Walking speed.** Google walks at about 3.8–3.9 km/h; we configured 4.8.
- **Flat transfers at deep stations** such as Édouard-Montpetit.
- **Station entrances not modelled.** R5 walks to the platform coordinate at street level.

**Consequence for the site.** The published medians are closer to "Google trip time" than to "Google + wait". The methodology page must say so and must not describe them as conservative.

### 3. Building split (route 7): a near-tie in both tools

- Google: Roger-Gaudry 35, Jean-Brillant 36, so Roger-Gaudry is faster by 1 min.
- R5: Jean-Brillant 32.0, Roger-Gaudry 32.2, so Jean-Brillant is faster by 0.2 min.

Both pass. The two tools disagree on which building is faster, but by 1 min or less. The "fastest building" value is robust because it's the minimum of two near-equal times. The per-home building choice in NDG is not meaningful at the ±1 min level, and the site should not present it as a clear-cut result.

### 4. Route 6 is a consistency check, not independent evidence

The penalty was calibrated from this same 7-min walk: 7 − 4.8 = 2.2. R5's walk is the mean of 4.6 and 5.1 = 4.85 min, + 2.2 = 7.05 min. This only confirms the penalty is wired in correctly. Routes 1–5 and 7 are the independent tests of the Roger-Gaudry times, and all except route 4 pass.

## Status

**Open: deep-station transfers and walking speed.** Both are decisions for the author:
1. Choose a correction for the Édouard-Montpetit transfer, measure which quartiers change, apply it, re-run and re-validate.
2. Decide whether to keep a walking speed of 4.8 km/h (and document it as optimistic) or move closer to Google's ~3.9 km/h.
3. Write the systematic optimism (finding 2) into `docs/methodology.md` and the site's limitations.
