# Methodology and limitations

This file is filled in as each phase lands. It becomes the site's "Sources & limitations" page in Phase 4.

## Geography
- Unit of analysis: the Ville de Montréal **quartiers de référence en habitation** (91 areas). The layer also covers the villes liées (Westmount, Mont-Royal, Côte-Saint-Luc, …), so the whole island is included.
- 91 quartiers across 15 municipalities, with 1,011,945 dwellings in total (city CSV). **L'Île-Dorval**, a tiny island municipality with no bridge and only a seasonal ferry, is not a separate quartier. Its single census point (25 occupied dwellings) falls inside the Dorval polygon. It is **out of scope**: kept in the sample with `in_scope = false` and a reason, but not routed and **excluded from Dorval's commute statistics** (`config.OUT_OF_SCOPE_CSDS`).
- **Parc Jean-Drapeau has no quartier of its own.** Île Sainte-Hélène and Île Notre-Dame are two separate polygon parts of the **Vieux-Montréal** quartier (about 1.3 km² each, against 2.8 km² for the mainland part). None of Vieux-Montréal's 13 census points lies on them; they are park islands with no permanent residents. Without a fix, the map would paint them with Vieux-Montréal's commute time. The export cuts them out as a separate **"no residents"** area (`config.NO_RESIDENT_AREAS`): grey on the map, no commute time, and its popup says it belongs to Vieux-Montréal in the city's data. Vieux-Montréal's statistics are unchanged, because they only ever came from its homes. The export refuses to run if a census home ever falls inside a no-residents area.
- Six source polygons have small self-intersections. They are repaired automatically, and the area of each changes by less than 30 m². Neighbouring polygons overlap by up to a few hundred m² from how the borders were drawn, which is negligible.

## Commute (Phase 1)

### Campus destinations
Each campus has one or more **destination buildings**. Trips are routed to the building's entrance, and r5py chooses the metro or bus stop itself. Points come from OpenStreetMap (2026-11-19). Where one is tagged, we use the `entrance=main` node.

| Campus | Destination | OSM |
|---|---|---|
| Université de Montréal | Pavillon Roger-Gaudry, main entrance L-4, 2900 boul. Édouard-Montpetit (nearest metro: Université-de-Montréal) | node/2573744215 |
| Université de Montréal | Pavillon Jean-Brillant, 3200 rue Jean-Brillant, the only entrance mapped (nearest metro: Côte-des-Neiges) | node/6783857247 |
| McGill (downtown) | Roddick Gates, Sherbrooke O. at McGill College | way/143798969 |
| Concordia SGW | Henry F. Hall Building main entrance, 1455 boul. De Maisonneuve O. | node/4035248248 |

**UdeM = "fastest UdeM building".** For each home, the UdeM commute is the faster of the two trips: to Roger-Gaudry or to Jean-Brillant. That per-home minimum is then summarised per quartier. The time to each building is also stored and shown in the detail panel.
- This is **optimistic** for students whose classes are in the other building. From some homes the "fastest" building can be 5–10 minutes closer than the other one.
- UdeM students choose their station by building: Université-de-Montréal metro for Roger-Gaudry and André-Aisenstadt (about 7 min uphill on foot through the tunnel), Côte-des-Neiges metro for Jean-Brillant (about 7 min). Routing to buildings rather than stations captures this choice.

**Pedestrian tunnel.** OSM maps the Université-de-Montréal metro → Roger-Gaudry tunnel ("Tunnel de la Montagne", way/723260098, an escalator, plus tunnel corridors). Part of it is tagged `highway=corridor`, which R5 may not treat as walkable. In that case the modelled walk would go outside and could come out slightly longer than reality. This is checked in validation (route "UdeM metro → Roger-Gaudry").

Limitation: campuses are large. A class in a building other than the modelled ones can change the trip by 5–10 minutes.

**McGill and Concordia: one point each** (M3). McGill is measured to the Roddick Gates (Sherbrooke at McGill College) and Concordia to the Hall Building's main entrance. There is no "fastest building" rule for them as there is for UdeM. A student whose classes are elsewhere on these downtown campuses may walk a few more minutes.

**Out of scope for now:** McGill's **Macdonald campus** (Sainte-Anne-de-Bellevue) and Concordia's **Loyola campus** (NDG). The site's McGill and Concordia commutes are to the downtown campuses only.

### Where trips start: residential sample points
A quartier's commute is not measured from its centre. It is measured from many points where people actually live, and the results are then summarised.

- **Source:** Statistics Canada, 2021 Census Geographic Attribute File (92-151-X), census division 2466 (island of Montréal).
- **One point per dissemination area (DA).** A DA is a small census area of about 400–700 residents. The point is StatCan's representative point for that DA. The file has no coordinates at the smaller block level, which is why DAs are used.
- **Weight = dwellings occupied by usual residents** in the DA, from the 2021 census. A DA with no residents is not used.
- This gives **3,220 points**: a median of 34 per quartier, minimum 2 and maximum 91. Every point falls inside a quartier.
- **Reliability flag:** a quartier with fewer than 3 points is flagged `low_sample`. Today that is only **Senneville** (2 points). A quartier with no point at all would be routed from a point inside its polygon and flagged. None needs that today.
- **Cross-check:** StatCan 2021 dwellings per quartier compared with the city's counts. The median ratio is 0.99, ranging 0.76–1.09. The lowest are René-Lévesque (0.76) and Vieux-Montréal (0.77), which is consistent with downtown condo construction since 2021. This confirms the points land in the right quartiers, and that 2021 census weights slightly under-represent the fastest-growing downtown areas.

### Street network
- OpenStreetMap, Geofabrik Québec extract, data as of **2026-11-19 21:22 UTC**. It is clipped with osmium to the island of Montréal plus a buffer, lon −74.10 to −73.35 and lat 45.35 to 45.80, so routes through Laval and the South Shore stay possible. The clip keeps every path that crosses the edge in full (`complete_ways`). The result is 77 MB, down from 1,168 MB.

### Transit schedules and analysis date
- Feeds: STM `20261029135439_26N` (bus + metro), REM `20260520`, and exo trains (5 lines). Versions and hashes are in `data/manifest.csv`.
- **Analysis date: Tuesday 2026-12-01**, during the fall class term and before the STM schedule change of 2027-01-05.
- `python -m mtlhousing gtfs-check` checks that the date falls inside every feed's service period and has a **typical** number of trips for that weekday, at least 95% of the median. That day has 19,141 STM trips, 443 REM and 103 exo. The same check flags the REM holiday schedule on Dec 29–30 (323 trips), so a holiday can't be picked by accident.
- Validating against Google Maps: any regular Tue/Wed between 2026-11-24 and 2026-12-16 runs the same schedule in all three feeds, so the manual checks can use whichever of those dates is still upcoming.

### Routing (r5py 1.1.7 / R5)
- **Network:** clipped OSM streets plus the STM, REM and exo GTFS feeds, merged into one R5 transport network.
- **Search:** R5's RAPTOR router. It walks to nearby stops, waits for the next departure, rides, transfers (up to 8 vehicles) and walks to the building entrance. Modes are transit plus walk. Walking speed is **4.0 km/h** and the maximum trip is 2 h. Origins and destinations are snapped to the nearest walkable street.
- **Why 4.0 km/h.** The first run used 4.8 km/h, to match Google Maps. Validation (step 1.9) showed Google walks slower than that: its walk legs on the test routes imply 3.75–4.3 km/h (900 m in 14 min, 1.0 km in 16 min, 500–650 m in 7–9 min). At 4.8 km/h R5 came out faster than Google on 5 of 7 routes. The analysis date is also in winter, when sidewalks are slower. 4.0 km/h sits in Google's range and applies to every walk: to the first stop, between stops, and to the building.
- **Departure window:** R5 computes one trip per departure minute from 7:30 to 8:30 on Tuesday 2026-12-01, and we keep the **median (50th percentile)** of those 60 trips. This includes a realistic wait at the first stop, and it isn't skewed by one lucky or unlucky connection. r5py has no "arrive by" option, so this window is how we approximate "arrive around 8:30".
- **Scheduled, not frequency-based.** None of the three feeds has a `frequencies.txt`. Every metro trip has exact times in `stop_times.txt`: on 2026-12-01 there are 476 green-line, 478 orange, 314 yellow and 386 blue trips. R5 only uses random Monte Carlo draws for frequency-based routes, where departure times aren't known. r5py fixes that at 60 draws internally and doesn't expose the setting. With fully scheduled feeds there is nothing to draw, so the results are **deterministic** and need no draw setting. If a future feed switches to frequencies (some agencies publish the metro that way), the results would gain a random component, and this note must be revisited.
- **STM licence:** the metro schedules are used only to compute trip durations, never displayed. See DATA_SOURCES.md.

### Tunnel check (UdeM)
A walk-only route from the Université-de-Montréal metro entrance (2810 Édouard-Montpetit) to the Roger-Gaudry main entrance **does use the Tunnel de la Montagne escalator**. R5 gives **3.5 min for 271 m**. Students' experience (Google Maps) is about **7 min for about 400 m**. R5 ignores the climb, because no elevation model is loaded, walks the escalator at flat speed, and may take a shorter door-to-door path. **Commutes to Roger-Gaudry are therefore likely about 3 min optimistic.** This is corrected by the access adjustments below.

### UdeM runs (2026-11-20)
- **Current run (walking at 4.0 km/h):** 3,219 homes × 2 buildings, 29 min of routing. Raw R5 times, before access adjustments and pooled over both buildings, have a median of 48 min and range from 5 to 117 min.
- **First run (walking at 4.8 km/h, superseded):** 3,220 homes, 22 min of routing, raw median 45 min. In it, **Jean-Brillant was the faster building for only about 2% of homes** before any adjustment; the diagnosis below explains why.
- **Homes stuck on private paths.** A census point inside a private complex (for example condo grounds on Île-des-Soeurs mapped with `access=private` footways) gets snapped onto the private path, and R5 then cannot walk out. **Only for homes that reach no building at all**, the start is moved to the nearest public walkable OSM way within 300 m and re-routed. The distance moved is stored (`origin_moved_m`). This fixed the Île-des-Soeurs DA (897 homes, moved 92 m, now 35 min).
- **Excluded, not unreachable:** L'Île-Dorval (see Geography). It is not routed and not counted.
- **Still unreachable, correctly:** the western tip of Île-Bizard, beyond R5's 2-hour limit. At 4.0 km/h this is 4 census points (1,045 dwellings, 15% of the quartier), so L'Île-Bizard–Sainte-Geneviève is flagged `many_unreachable` and its p90 is "more than 2 h". Moving these starts to the nearest public path (see above) doesn't help: they are simply too far.
- Unreachable means **"more than 2 h"**. It is never treated as missing data or as 0 when quartiers are summarised.

### Why Jean-Brillant rarely came out faster (diagnosis of the first run, 4.8 km/h, 2026-11-20)
This diagnosis led to the access adjustments below. Its numbers are from the first run.

Without any adjustment, Jean-Brillant is the faster building for only **2.2% of homes**. That contradicts how students actually get there: anyone coming from the west on the blue line (Snowdon) reaches Côte-des-Neiges station first.

- **The Jean-Brillant side is modelled correctly.** R5 walks Côte-des-Neiges metro → Jean-Brillant entrance in **6.8–7.3 min (533–576 m)**, matching Google (about 7 min / 500 m). The entrance used is node/6783857247, about 430 m in a straight line from both CDN entrances.
- **The Roger-Gaudry side is too fast.** R5 walks Université-de-Montréal metro → Roger-Gaudry in **3.5 min (271 m)** through the tunnel, against about 7 min / 400 m in reality. The climb isn't modelled.
- **Both trips are identical until the last station.** They differ only in the stop where you get off and the walk to the door. At the median home, Roger-Gaudry minus Jean-Brillant is exactly −4 min, and the gap never goes beyond −5 min. Sample homes, median over 7:30–8:30:

| Home (DA) | Roger-Gaudry | Jean-Brillant | Route at 08:00 |
|---|---|---|---|
| Snowdon (da:24663199) | 14 | 16 | blue line from Snowdon. RG: ride to Université-de-Montréal + 4-min walk. JB: get off at Côte-des-Neiges + 8-min walk. |
| Édouard-Montpetit / Côte-des-Neiges (da:24660699) | 12 | 4 | JB: walk 5 min. RG: one metro stop + 4-min walk. |
| NDG east, Côte-Saint-Antoine (da:24660761) | 26 | 28 | 103 bus → orange → blue, same split at Côte-des-Neiges / Université-de-Montréal |
| NDG west, Loyola (da:24660865) | 33 | 34 | 51 bus → blue, same split |

- With a realistic walk to Roger-Gaudry (about 3.5 min more), the Snowdon and NDG homes flip to Jean-Brillant. Homes reached from the east (blue line from Saint-Michel or Jean-Talon) still favour Roger-Gaudry by about 1–2 min.
- **The "fastest building" share is very sensitive** to this one walk. It is 2% at +0 min, 16% at +2, 31% at +3, 46% at +3.5 to +4, and 100% at +5. R5 reports whole minutes, so the shares jump in steps. Both buildings' times are therefore always published alongside the minimum.

**Correction applied: calibrated access adjustments for both buildings.**

Both UdeM buildings are calibrated the same way, so neither side of the building split is favoured. The **target** is the real walk from the metro platform where R5's blue-line trips end to the building's door. The **adjustment** is the target minus R5's walk-only time from that platform stop, at the configured 4.0 km/h. It can be negative.

| Building | Platform (STM GTFS stop) | Target, source | R5 walk at 4.0 km/h | Adjustment |
|---|---|---|---|---|
| Roger-Gaudry | Université-de-Montréal (`56`) | 7 min: the author (a UdeM student) and Google Maps (~7 min / 400 m) | 5.08 min / 332 m | **+1.9 min** |
| Jean-Brillant | Côte-des-Neiges (`55`) | 7 min: Google Maps (~7 min / 500 m) | 9.40 min / 613 m | **−2.4 min** |

- **Why the adjustments differ in sign.** R5 walks at flat speed with no elevation model. On the Roger-Gaudry side it misses the climb through the Tunnel de la Montagne. On the Jean-Brillant side R5's path is longer than Google's: it starts at the platform coordinate and walks 613 m for a door 459 m away in a straight line, while Google gives ~500 m.
- **How it's applied.** The adjustment is added to **every** trip ending at that building (`config.ACCESS_ADJUSTMENT_MIN`), after routing, on the saved results; times never go below 0. This is exact for a fixed per-destination adjustment: every route to that door shifts by the same minutes, so R5's route choice and the median over departure minutes shift by exactly that amount. The router's own value is kept as `travel_time_raw_min`.
- **Reproducible.** `python -m mtlhousing access-check` routes the platform walks (validation routes 6 and 6b) and prints the R5 walk, the target and the implied adjustment. The adjustments depend on the walking speed and must be re-derived after any speed change; the pipeline refuses saved travel times routed at a different speed.
- **Correction (2026-11-20).** The first calibration, at 4.8 km/h, used STM stops 53877 / 53878. These are **bus stops** named "Station Université-de-Montréal" (lines 51, 155, 368), not the metro platform. Metro trips end at stop `56`. That first run had only a Roger-Gaudry penalty (+2.2 min) and no Jean-Brillant adjustment.
- **Caveats.**
  - The adjustment also applies to trips that reach a building without the metro, for example walking from a nearby home or arriving by bus. For a walk from a home near Jean-Brillant, the −2.4 min can overstate the saving.
  - Trips just over 120 min before the adjustment were never computed.
  - Routes 6 and 6b in validation check the adjustments by construction; they are not independent evidence.
- **Effect on the building split.** Jean-Brillant is the faster building for **66% of dwellings** (32% in the first run, which had no Jean-Brillant adjustment). The two buildings are close for most homes: the median Roger-Gaudry − Jean-Brillant gap is +0.3 min, and for **58% of dwellings they are within 1 min**. The fastest-building time is robust; which building wins for a given home is not, so the site must not present it as clear-cut.

**Future work (Option B): elevation model.** r5py supports `TransportNetwork(elevation_model=<DEM GeoTIFF>, elevation_cost_function=TOBLER or MINETTI)`. It slows every uphill walk citywide (Mont-Royal, Westmount), which is more realistic than fixed per-building adjustments. It needs:
- a DEM download (an elevation file for Montréal);
- a network rebuild and a full re-run (about 25 min);
- a check of how R5 treats tunnels and escalators, which would get surface elevations.

Not done for v1.

### Per-quartier commute statistics (step 1.7)
For each home (in-scope census point) and each campus:
1. Apply the access adjustments above.
2. **Campus time = fastest of the campus's buildings for that home** ("fastest UdeM building"). Both buildings' times are always kept and published next to it.
3. Per quartier, for the fastest time and for each building's time:
   - **Dwelling-weighted median, p10 and p90.** Quantiles use the weighted inverse CDF without interpolation: the smallest time *t* such that at least that share of the quartier's occupied dwellings has a time ≤ *t*.
   - `n_points`, `n_unreachable` and `unreachable_share` (dwelling-weighted).
   - For each building, `fastest_share`: the share of dwellings for which it is the faster building.
4. **Unreachable = more than 120 min.** It ranks above every real time, so it pushes the median and percentiles up. If a quantile lands on it, the value is reported as "more than 2 h". It is never dropped and never counted as 0.
5. **Flags:** `low_sample` (fewer than 3 points) and `many_unreachable` (more than 10% of dwellings unreachable).

UdeM result (4.0 km/h, adjustments +1.9 / −2.4):
- The median of quartier medians is **44.6 min**.
- Nearest: Édouard-Montpetit (10.9), Snowdon (21.6), Outremont (21.9), Parc-Kent (22.6), Savane (24.6).
- Farthest: Senneville (106.6, `low_sample`), Rivière-des-Prairies (91.6), L'Île-Bizard–Sainte-Geneviève (87.6, `many_unreachable`, p90 > 2 h), Baie-D'Urfé (86.6), Marc-Aurèle-Fortin (81.6).
- **Against the first run (4.8 km/h):**
  - Quartier medians rose by 1.9 min on average, ranging from −0.4 to +5.4.
  - The largest rises are far from campus, where walks to and between stops are long: Senneville +5.4, Dollard-Des Ormeaux and L'Île-Bizard +4.4, Baie-D'Urfé +3.6, Maisonneuve and Nouveau-Bordeaux +3.4.
  - Near Côte-des-Neiges, the Jean-Brillant adjustment offsets the slower walk: Loyola and Côte-Saint-Luc −0.4, Édouard-Montpetit −0.1.

### Web export (step 1.8)
`python -m mtlhousing export --campus udem` writes two files to `web/public/data/` (committed, so the site never runs Python):

- **`neighbourhoods.geojson`** (~290 kB): one feature per quartier with `id`, `name`, `borough`, `municipality` and `dwellings`.
  - Boundaries are simplified as a coverage (5 m tolerance in MTM 8), so neighbouring quartiers still share their edges with no gaps or overlaps.
  - Coordinates are rounded to 5 decimals (about 1 m).
- **`commute.json`** (~60 kB): `meta` records how, when and from what the numbers were made:
  - analysis date and departure window;
  - walk speed and the 120-min limit;
  - GTFS feed versions and OSM date;
  - each campus's buildings with their access adjustments (`access_adjustment_min`);
  - out-of-scope areas, relocated origins and source credits.

  `results[quartier_id][campus_id]` holds:
  - the fastest-building `median`, `p10` and `p90`;
  - `n_points`, `n_unreachable`, `unreachable_share` and `flags`;
  - `rule: "fastest_destination"`;
  - `by_destination`: each building's own `median`, `p10` and `p90`, `n_unreachable` and `fastest_share`.
- **Missing values are JSON `null`, never `NaN`.** The writer refuses NaN/Infinity.
  - A time over 120 min is `null` **and** its name is listed in `over_max`, so the site shows "more than 2 h".
  - A `null` not listed in `over_max` means no data.
  - For UdeM, only L'Île-Bizard–Sainte-Geneviève has a stat over the limit (its p90).
- **No-residents areas** (Parc Jean-Drapeau, see Geography) are separate features with `no_residents: true`, `part_of` and `dwellings: 0`. They have no entry in `commute.json`.
- A folium check map (`data/interim/commute_udem_map.html`) is written next to the interim data. It is not used by the site.

### Validation against Google Maps (step 1.9)
Seven hand-picked routes plus two platform walks were routed with the published settings and compared with Google "Arrive by 8:30" (pass rule |R5 − Google| ≤ max(5 min, 15%)). Details, R5 itineraries and the first run are in [`pipeline/validation/VALIDATION.md`](../pipeline/validation/VALIDATION.md).

- **8 of 9 comparisons pass.** Route 4 (Hochelaga → Roger-Gaudry) fails against Google's first suggestion (60 min), a slower trip. Against Google's like-for-like green line + REM trip (52 min), R5 gives 46.9 and passes.
- **Walking speed was the systematic bias.** At 4.8 km/h, R5's medians (which include waiting) were 1.5 min below Google's well-timed trip on average, excluding route 4. At 4.0 km/h they are +0.0 min on average. That is why walking speed is 4.0 km/h.
- **Transfers.** The feeds have no pathway or transfer times, so R5 treats a transfer as a flat street walk between stop coordinates. At Édouard-Montpetit (REM → blue line) that gives about 1 min, which agrees with Google's route 5 trip ("about 1 min").
- **The building split is a near-tie.** Google and R5 disagree on the faster building for route 7 by about 1 min.
- Routes 6 and 6b (platform → building walks) are the calibration of the access adjustments, not independent evidence.
- **These results are in-sample.** The walking speed was chosen from routes 1–5 and 7, and the adjustments from routes 6 and 6b, so the agreement is a fit, not a prediction. Before launch, 3–4 out-of-sample routes will be checked with the settings frozen, and the result reported whether it passes or not.

## Rent (Phase 2)
Computed by `python -m mtlhousing rent` (`data/interim/rent_by_quartier.csv`, unrounded) and exported for the site by `python -m mtlhousing rent-export` (`web/public/data/rent.json`, rounded). The export re-checks the crosswalk against CMHC's unit counts first, and refuses to write if anything is off.

### Two sources, two jobs
- **Where rents are higher or lower: CMHC, October 2025.** CMHC's Rental Market Survey gives the average rent by neighbourhood and bedroom count. We only use its ratios: a neighbourhood's average divided by the Montréal average for the same bedroom count. Every ratio comes from that one survey, so they are consistent with each other.
- **How high rents are now: Statistics Canada, 2026 Q2.** Table 46-10-0092-01 gives the average *asking* rent for the Montréal CMA by bedroom count. It sets the citywide level that the ratios scale.

Estimate = (CMHC neighbourhood average ÷ CMHC Montréal average) × StatCan Montréal asking rent.

**Why two different dates.** StatCan's latest quarter is used because the site should show today's asking level. Asking rents fell 4–5% between 2025 Q4 and 2026 Q2 (1 bedroom: $1,550 → $1,480). This assumes the neighbourhood pattern of October 2025 still holds. The site shows both dates in the rent legend, and says there that the StatCan figures are experimental estimates. The quarter is one config value (`STATCAN_RENT_QUARTER`).

**Known limitation: old leases.** CMHC's averages include long-time tenants, whose rents likely sit below what a new tenant would pay. So the neighbourhood pattern reflects existing leases, not only new ones:
- **Old-stock areas likely look cheaper than new listings** (e.g. Plateau-Mont-Royal, Rosemont).
- **New-build areas, with more recent leases, likely look pricier** (e.g. the West Island).

This hasn't been measured yet, so how large the effect is in each area is unknown. Scaling to StatCan's asking rents fixes the citywide level, not this pattern. The site will say so on its sources & limitations page (M5). A possible correction, using CMHC rents of vacant units, is the optional M2.7 in `docs/ROADMAP.md`.

Montréal CMA average asking rent, 2026 Q2: studio $1,250, 1 bedroom (3½) $1,480, 2 bedrooms (4½) $1,820, 3+ bedrooms $2,260.

### From quartiers to CMHC areas: the crosswalk
CMHC publishes rents for its own areas: **neighbourhoods** (groups of census tracts) and **zones** (groups of neighbourhoods). Their edges don't follow the city's quartiers, and CMHC's exports carry names only, with no codes and no map of which tract belongs where. So the link is a hand-made crosswalk in `pipeline/crosswalk/`, three files:

| File | Links | Rows |
|---|---|---|
| `census_tract_to_cmhc_neighbourhood.csv` | census tract → CMHC neighbourhood | 520 tracts (every island tract with rental units) |
| `quartier_to_cmhc_neighbourhood.csv` | quartier → CMHC neighbourhood(s), with each one's share | 95 rows for 91 quartiers |
| `cmhc_neighbourhood_to_zone.csv` | CMHC neighbourhood → zone | 37 neighbourhoods in 18 zones |

**How it is checked.** CMHC also publishes how many rental units each zone, neighbourhood and census tract has, by bedroom type (rental universe, October 2025, same survey). Those counts must add up, so `python -m mtlhousing crosswalk-check` (and a test) checks the hand-made links against them:
- **Tracts → neighbourhoods.** For each neighbourhood and bedroom type, its tracts' units must add up to its published count. A count CMHC suppressed (`**`) can't be added up, so that cell is "unchecked". Even then, the published tracts must not add up to *more* than the neighbourhood. Result: **all 37 neighbourhoods match on their total.** 153 cells match, 32 are unchecked because of a suppressed tract, and none contradicts.
- **Neighbourhoods → zones.** The same test one level up. **All 18 zones match on their total** (89 cells match, 1 unchecked, none contradicts). As a second check, every zone's average rent lies between its neighbourhoods' rents (54 of 54 comparisons).
- **Quartiers → neighbourhoods.** A quartier's tracts come from the census: each dissemination-area point (see "Where trips start") carries its census tract. A tract on a quartier edge is divided between the quartiers by their homes in it (2021 occupied dwellings). That gives each quartier's rental units in each neighbourhood, and its **share** of them. The committed shares must equal these to 3 decimals.

A row is marked **verified** only when this check confirms it. 94 of the 95 rows are verified. The other one is **Baie-D'Urfé**: its only census tract has no CMHC rental units, so the counts can't confirm anything. It is matched by name to *Sainte-Anne-de-Bellevue/Baie-d'Urfé* (confidence "high", reviewed by the owner).

**Small slivers are folded in.** When less than 5% of a quartier's rental units fall in a second neighbourhood, that part is folded into the main one instead of kept as a split (`config.CROSSWALK_FOLD_BELOW`). This happens twice: Bois-Francs (0.6% of its rental units in Senneville/Roxboro-Pierrefonds) and Grande-Prairie (1.8% in Mercier).

**Four quartiers are split** between two neighbourhoods, by rental units:

| Quartier | Neighbourhoods (share of the quartier's rental units) |
|---|---|
| Nouveau-Bordeaux | Ahuntsic 0.619, Cartierville 0.381 |
| Gabriel-Sagard | Villeray 0.530, Saint-Michel 0.470 |
| Parc-Jarry | Villeray 0.893, Parc-Extension 0.107 |
| Côte-Saint-Luc | Côte-Saint-Luc/Montreal West 0.866, Hampstead/Côte-Saint-Luc 0.134 |

**Limits.**
- How the tract → neighbourhood file was first built wasn't recorded. Its evidence is that the counts add up exactly. A tract that adds nothing to a sum (a suppressed count) can't be confirmed by it. No tract in the export has a suppressed **total**, and the check refuses to share out a tract that has one.
- CMHC's tract export lists no tract with 0 units, so a census tract missing from it is taken to have **no purpose-built rental units**. That covers 1.7% of the homes in the quartiers. Every tract in the crosswalk exists in the census file under the same name, which the check enforces.
- Three mapped tracts (0014.02, 0091.00, 0189.00) had no occupied home in the 2021 census, probably because they were built since. Their 89 rental units (0.02% of the island's) can't be given to any quartier. The check fails if such units ever exceed 0.1% (`config.CROSSWALK_MAX_UNALLOCATED`).
- Rental units are spread over a tract's homes evenly. A tract on a quartier edge whose rental buildings sit on one side will be divided slightly wrong. This only affects the 4 split quartiers and the 2 folded slivers.
- The tract units are CMHC's October 2025 counts, and the homes are from the 2021 census.

### Which CMHC value is used, and how it is labelled
CMHC grades each average rent by reliability: a excellent, b very good, c good, d poor ("use with caution"). `**` means suppressed or not statistically reliable. A zone is a group of neighbourhoods.

For each quartier and bedroom type, the first available value in this order is used (`rent.choose_source`):

| Order | Value used | Label on the site |
|---|---|---|
| 1 | Neighbourhood, grade a, b or c | estimate (CMHC neighbourhood) |
| 2 | Zone, grade a, b or c | zone estimate (CMHC zone) |
| 3 | Neighbourhood, grade d | low reliability (CMHC grade d) |
| 4 | Zone, grade d | low reliability (CMHC grade d), zone level |
| 5 | none | not enough data |

- A grade d value is used only when no a, b or c value exists at either level. For a split quartier, that means no a/b/c values covering at least 80% of its rental units (see below). That's why a zone graded c comes before a neighbourhood graded d: it's less local, but more reliable.
- Between two grade d values, the neighbourhood comes first, because it's more local.
- `**` is never used, at either level.

### Quartiers split between neighbourhoods
Applied by `rent.estimate_quartier`; the threshold is `config.RENT_MIN_COVERAGE`.

For a quartier split between neighbourhoods (see the crosswalk), the rule above is applied once for the whole quartier, at one level at a time:
- **Every part has a usable value at the same level:** the quartier's ratio is the share-weighted average of the parts' ratios (share = the part's share of the quartier's rental units). It is labelled with the **worst grade** among the parts.
- **The parts with a usable value cover at least 80% of the quartier's rental units:** the average is re-weighted over those parts only, and labelled "covers X% of rental units", with X the share they cover, **rounded down** to a whole percent (86.6% → "86%").
- **Below 80%:** fall back to the next step of the order above, as for any quartier.

The rule applies at **every step**, grade d included, and the labels combine: for example "low reliability (CMHC grade d), covers 90% of rental units". "Usable" means a value that qualifies for that step: grade a, b or c at steps 1–2, and grade **d or better** (a, b, c or d) at steps 3–4. A c value is never ignored at a step that accepts d. For a quartier with one neighbourhood this changes nothing, since an a/b/c value is already used at step 1 or 2. For a split quartier, a part graded c and a part graded d can together reach the coverage a step needs. The label is then grade d, the worst grade used. In practice:
- **Côte-Saint-Luc:** Hampstead/Côte-Saint-Luc is suppressed for every size. Côte-Saint-Luc/Montreal West covers 86.6%, so every size is labelled "covers 86% of rental units".
- **Gabriel-Sagard, studio:** Villeray has a grade c value but covers only 53%, so the quartier uses the zone, which covers both halves.
- **Nouveau-Bordeaux, 3+ bedrooms:** Ahuntsic (grade c) covers only 61.9%, so step 1 fails, and the zone has no a/b/c value, so step 2 fails. At step 3, Ahuntsic (c) and Cartierville (d) both count and cover 100%. The quartier gets a neighbourhood-level estimate labelled "low reliability (CMHC grade d)".
- All four split quartiers have both parts in the same zone, so the zone steps give a single value.

### What is computed
Every quartier gets a row for each of the four bedroom types CMHC and StatCan share: studio, 1 bedroom (3½), 2 bedrooms (4½) and 3+ bedrooms. The row holds either an estimate or "not enough data". The site shows the first three types. With October 2025 data, "not enough data" covers 0 quartiers for studios, 6 for 1 bedroom, 6 for 2 bedrooms and 33 for 3+ bedrooms. The estimate is kept unrounded until the export. If the StatCan Montréal value for a bedroom type is missing, unusable, or flagged E ("use with caution") or worse, the step stops: how to label such a value isn't decided yet. 2026 Q2 has no flag on any apartment value.

### Rooms
StatCan gives a citywide average asking rent for a room ($720, 2026 Q2). CMHC has no room data, so there is no estimate per neighbourhood. The site shows the room figure once, rounded like the rest (≈ $725). The wording is under "What the site shows".

### What the site shows
**Rounding.** Every rent is rounded **half up to the nearest $25** in the export, rooms included ($1,612.50 → $1,625, $1,604 → $1,600), and shown with "≈": "≈ $1,600". The site, its budget filter and the shortlist all use the rounded value, so a rent shown as ≈ $1,475 is never excluded at a $1,475 budget. "Not enough data" is `null` in `rent.json`, never a number.

**Words.** The city's quartiers are "neighbourhoods" on the site. CMHC's areas are always "CMHC area" and "CMHC zone", so the two are never confused. CMHC's grade is shown in words, never as a letter: a "excellent", b "very good", c "good", d "use with caution".

**Labels.** `rent.json` carries a key; the site holds the text. English is below; French comes in M5.

| Key | Badge (map, shortlist) | Detail panel line |
|---|---|---|
| `neighbourhood` | Estimate | Based on CMHC's average rent in {CMHC area} (October 2025, rated {excellent / very good / good} by CMHC), adjusted to current Montréal asking rents. |
| `zone` | Wider-area estimate | CMHC has no reliable figure for this area, so this uses the wider CMHC zone {zone} (rated {excellent / very good / good} by CMHC). |
| `neighbourhood_low` | Low reliability | Based on CMHC's average rent in {CMHC area}, which CMHC rates "use with caution". |
| `zone_low` | Low reliability | Based on the wider CMHC zone {zone}, which CMHC rates "use with caution". |
| `none` | Not enough data | CMHC doesn't publish a reliable rent for this size here or nearby. |

These lines are added to the detail line when they apply:
- **Split neighbourhood:** "Weighted average of CMHC areas {A} (62%) and {B} (38%), by rental units."
- **Coverage under 100%:** "Covers {X}% of this neighbourhood's rental units; CMHC has no reliable figure for the rest." X is rounded down.
- **Under every estimate** (owner's wording, M3): "Estimate based on average rents, adjusted to current Montréal asking rents. Not a listing, and possibly low in areas with many long-time tenants." It replaces the earlier line, which also gave the dates.
- **Data dates, once in the rent legend:** "Data: CMHC (October 2025) and Statistics Canada's experimental asking rents (2026 Q2)."
- **Room:** "≈ $725 a month: Montréal-wide average asking rent for a room, not specific to this neighbourhood (Statistics Canada, 2026 Q2)."

**Shares shown.** The per-area shares are shown **raw**, as in `rent.json`: each CMHC area's share of the neighbourhood's rental units, with no re-weighting for display. When coverage is under 100%, they add up to the coverage, not to 100%.
- In a split, each share carries that area's own rating: "Weighted average of CMHC areas Villeray (89%, rated very good) and Parc-Extension (11%, rated good), by rental units." A grade d area reads `rated "use with caution"`, quoted as everywhere else. Shares are whole percents, or one decimal when coverage is under 100% (no current split is).
- Next to "covers X%", the share has one decimal, so it doesn't look like a contradiction: "Covers 86% of this neighbourhood's rental units (Côte-Saint-Luc/Montreal West: 86.6%)".
- For a split, the detail line names every area but leaves the rating out, because the label's worst grade isn't every area's rating: "Based on CMHC's average rents in CMHC areas Villeray and Parc-Extension (October 2025), adjusted to current Montréal asking rents." If the label is low reliability, it ends "CMHC rates at least one of them "use with caution"".

The unrounded Montréal figures in `meta.montreal` (CMHC average, StatCan asking rent) are published source values. They can be shown as they are.

**On the map** (rent layer, M2.6). One size at a time: studio, 3½ (the default) or 4½. Each neighbourhood is coloured by its rounded rent compared with the Montréal asking rent for that size:
- **Six classes:** < 85%, 85–95%, 95–105%, 105–115%, 115–130%, > 130%.
- **Class edges** are those percentages of the Montréal level, **rounded up** to the next $25. Rents are multiples of $25, so "rent ≥ edge" means exactly "rent ≥ that %", and no neighbourhood is coloured in a class whose % it doesn't meet. Rounding to the nearest $25 would break that: for 3½, the 85% edge would become $1,250, which is 84.5%. A rent equal to an edge goes in the class above. The legend shows each class in dollars for the chosen size (for 3½: under $1,275 … $1,925 or more). It also shows the Montréal level as published ($1,480, no "≈"), and its swatches use the map's opacity.
- **Palette:** a diverging scale centred on a neutral, near-white 95–105%. Blue is cheaper, orange-brown is pricier: `#2166ac`, `#6aaed6`, `#f3f2ee`, `#eb9236`, `#b85208`, `#6a2d05`. It is colour-blind-safe. It was checked with a palette validator: each arm steps light to dark in one hue, and every pair of neighbouring classes stays distinguishable for colour-blind and full-vision readers (worst ΔE 16.4). It is deliberately not the green-to-red commute scale.
- **Low reliability** (grade d) keeps its class colour, with a diagonal hatch of dark and light lines, so it shows on pale and dark classes alike.
- **Not enough data** is a dark grey (`#6e6e6e`). "No residents" keeps the commute map's light grey (`#d4d4d4`) and gets a dashed outline, in both modes. Its grey is close to the near-white neutral, so the outline tells them apart.
- **Spread with 2026 Q2 data**, neighbourhoods per class (< 85% … > 130%):
  - studio: 37, 22, 16, 8, 8, **0**. No studio is above 130%: the highest is 128% of the Montréal level;
  - 3½: 14, 27, 21, 15, 4, 4;
  - 4½: 9, 13, 48, 7, 3, 5.

**Crosswalk notes.** Notes on the crosswalk are shown only on the sources & limitations page, not in the main interface. `rent.json` carries them in `meta.crosswalk_notes`:
- Baie-D'Urfé's link to Sainte-Anne-de-Bellevue/Baie-d'Urfé is by name and can't be confirmed from the counts.
- Two slivers are folded in: Bois-Francs and Grande-Prairie.
- Two island-wide facts: homes in tracts with no CMHC units, and units in tracts with no 2021 home.

**Attribution** (in `meta.sources`, shown on the sources page):
- "Adapted from Canada Mortgage and Housing Corporation, Rental Market Survey, October 2025. This does not constitute an endorsement by CMHC."
- "Adapted from Statistics Canada, Table 46-10-0092-01 Asking rent and paid rent prices, by rental unit type and number of bedrooms (experimental estimates), 2026 Q2. This does not constitute an endorsement by Statistics Canada of this product."
- Statistics Canada 2021 Census Geographic Attribute File and Ville de Montréal open data, as for the commute.
