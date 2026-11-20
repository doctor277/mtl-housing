# Validation: R5 vs Google Maps, UdeM (step 1.9)

**Result: 7 of 8 comparisons pass. Route 4 fails and is not explained yet, so Phase 1 stays open until it is.**

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
| 1, 3, 7 | Author's Google Maps pins |
| 2 | OSM address node/4907803398 |
| 4 | OSM address way/224941530 |
| 5 | REM GTFS parent station `ST_PTC_1` |
| 6 | STM platform stops 53877 / 53878, where R5's metro trips end |

## Results

| # | From (quartier) | To | Google | R5 median | R5 p10 | Diff | Tol. | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | 4500 Saint-Denis (Mile End) | Roger-Gaudry | 31 | 32.2 | 30.2 | +1.2 | 5.0 | pass |
| 2 | 4000 Wellington (Verdun-Centre) | Roger-Gaudry | 39 | 36.2 | 34.2 | −2.8 | 5.8 | pass |
| 3 | 1500 Fleury Est (Sault-au-Récollet) | Roger-Gaudry | 50 (fastest listed: 42) | 46.2 | 41.2 | −3.8 (+4.2) | 7.5 (6.3) | pass (pass) |
| 4 | 3800 Ontario Est (Hochelaga) | Roger-Gaudry | 60 (green + REM: 52) | 43.2 | 40.2 | −16.8 (−8.8) | 9.0 (7.8) | **fail (fail)** |
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

### 1. Route 4 fails: R5 is 9–17 min faster than Google on the same pattern

Even against Google's fastest listed trip (52 min, green + REM), R5's median is 8.8 min lower. R5's well-timed departure is 11.8 min lower.

R5's legs at a 7:40 departure (raw, no penalty, 41.0 min):

| Leg | R5 |
|---|---|
| Walk to Joliette | 10.5 min, 814 m |
| Green line Joliette → McGill | 10.0 min + 1.1 wait |
| **Transfer McGill metro → REM McGill** | **2.5 min, 199 m, flat** (+1.0 wait) |
| REM McGill → Édouard-Montpetit | 2.8 min + 1.5 wait |
| **Transfer REM → blue line at Édouard-Montpetit** | **0.4 min, 36 m, flat** (+1.1 wait) |
| Blue line, 1 stop | 2.0 min + 3.7 wait |
| Walk to Roger-Gaudry | 4.3 min (+2.2 penalty) |

**Most likely cause: R5 does not see how deep the REM stations are.**
- Neither the REM nor the STM feed has `pathways.txt`, `levels.txt` or `transfers.txt`.
- R5 times a transfer as a street-network walk between the two stop coordinates.
- At Édouard-Montpetit, the REM platforms are about 20 m from the metro stop on a flat map. The real station is very deep, so the transfer is by long escalators or elevators. R5 counts 0.4 min.
- The McGill transfer between the green line and the REM's deep platforms is also timed as a flat 199 m walk.

**Other possible causes** (I can't confirm either without Google's trip details):
- Google may place "3800 Rue Ontario Est" somewhere other than the OSM address. This is the only failing route whose origin came from OSM rather than from an author pin.
- Google may add its own transfer buffers.

**Needed to close this:** Google's leg-by-leg times for the 52-min trip (start walk, transfer minutes at McGill and at Édouard-Montpetit, final walk) and Google's pin coordinates for the origin.

**Why it matters beyond one route.** Many homes' best R5 trips use REM → Édouard-Montpetit → blue line. In the itinerary samples from step 1.9 this included Mercier–Hochelaga, Milton-Parc, the West Island and Cartierville. If the REM transfers are underestimated, those quartiers' commutes are optimistic. Route 5 passes with the same 0.4-min Édouard-Montpetit transfer (R5 p10 38.2 vs Google 41). So the gap there is a few minutes, not 10.

### 2. R5 is optimistic overall, not pessimistic

We expected R5 medians to come out above Google, because Google leaves out the initial wait. Instead:
- **The median is below Google in 5 of 7 transit comparisons.** Mean difference: −1.5 min without route 4, −3.7 min with it.
- **R5's well-timed departure (p10) is faster than Google in every comparison:** −0.8, −4.8, −8.8 (−0.8 against the fastest listed), −11.8 against the 52-min trip, −2.8, −7.0 and −4.8 min.

**Likely contributors**, in this order: flat transfers and no time for going down to deep platforms (finding 1); entrances not modelled, since R5 walks to the platform coordinate at street level; Google's own buffers.

**Consequence for the site.** The published medians are closer to "Google trip time" than to "Google + wait". The methodology page must say so and must not describe them as conservative.

### 3. Building split (route 7): a near-tie in both tools

- Google: Roger-Gaudry 35, Jean-Brillant 36, so Roger-Gaudry is faster by 1 min.
- R5: Jean-Brillant 32.0, Roger-Gaudry 32.2, so Jean-Brillant is faster by 0.2 min.

Both pass. The two tools disagree on which building is faster, but by 1 min or less. The "fastest building" value is robust because it's the minimum of two near-equal times. The per-home building choice in NDG is not meaningful at the ±1 min level, and the site should not present it as a clear-cut result.

### 4. Route 6 is a consistency check, not independent evidence

The penalty was calibrated from this same 7-min walk: 7 − 4.8 = 2.2. R5's walk is the mean of 4.6 and 5.1 = 4.85 min, + 2.2 = 7.05 min. This only confirms the penalty is wired in correctly. Routes 1–5 and 7 are the independent tests of the Roger-Gaudry times, and all except route 4 pass.

## Status

**Open: route 4.** To resolve:
1. Get Google's leg breakdown and origin pin.
2. If the REM transfer is confirmed as the cause, decide on a documented correction. Options include a fixed transfer time for deep REM stations, or a patched REM feed with pathway times. Either way it gets re-run and re-validated.
3. Write the systematic optimism (finding 2) into `docs/methodology.md` and the site's limitations.
