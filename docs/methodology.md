# Methodology and limitations

This file is filled in as each phase lands. It becomes the site's "Sources & limitations" page in Phase 4.

## Geography
- Unit of analysis: the Ville de Montréal **quartiers de référence en habitation** (91 areas). The layer also covers the villes liées (Westmount, Mont-Royal, Côte-Saint-Luc, …), so the whole island is included.
- 91 quartiers across 15 municipalities, with 1,011,945 dwellings in total (city CSV). **L'Île-Dorval**, a tiny seasonal island municipality with no transit, is not a separate quartier. Its single census point falls inside the Dorval polygon and is reported as unreachable by transit.
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
- **Search:** R5's RAPTOR router. It walks to nearby stops, waits for the next departure, rides, transfers (up to 8 vehicles) and walks to the building entrance. Modes are transit plus walk. Walking speed is 4.8 km/h and the maximum trip is 2 h. Origins and destinations are snapped to the nearest walkable street.
- **Departure window:** R5 computes one trip per departure minute from 7:30 to 8:30 on Tuesday 2026-12-01, and we keep the **median (50th percentile)** of those 60 trips. This includes a realistic wait at the first stop, and it isn't skewed by one lucky or unlucky connection. r5py has no "arrive by" option, so this window is how we approximate "arrive around 8:30".
- **Scheduled, not frequency-based.** None of the three feeds has a `frequencies.txt`. Every metro trip has exact times in `stop_times.txt`: on 2026-12-01 there are 476 green-line, 478 orange, 314 yellow and 386 blue trips. R5 only uses random Monte Carlo draws for frequency-based routes, where departure times aren't known. r5py fixes that at 60 draws internally and doesn't expose the setting. With fully scheduled feeds there is nothing to draw, so the results are **deterministic** and need no draw setting. If a future feed switches to frequencies (some agencies publish the metro that way), the results would gain a random component, and this note must be revisited.
- **STM licence:** the metro schedules are used only to compute trip durations, never displayed. See DATA_SOURCES.md.

### Tunnel check (UdeM)
A walk-only route from the Université-de-Montréal metro entrance (2810 Édouard-Montpetit) to the Roger-Gaudry main entrance **does use the Tunnel de la Montagne escalator**. R5 gives **3.5 min for 271 m**. Students' experience (Google Maps) is about **7 min for about 400 m**. R5 ignores the climb, because no elevation model is loaded, walks the escalator at flat speed, and may take a shorter door-to-door path. **Commutes to Roger-Gaudry are therefore likely about 3 min optimistic.** This is measured in validation route 6, and the methodology will state the final correction or caveat.

### UdeM run (2026-11-20)
- 3,220 homes × 2 buildings, 22 min of routing. The median trip to the fastest UdeM building is 45 min, with a range of 4 to 117 min.
- **Jean-Brillant is the faster building for only about 2% of homes.** Most of the city reaches Université-de-Montréal station (Roger-Gaudry side) at least as fast as Côte-des-Neiges, and the optimistic 3.5-min tunnel walk adds to that. This is revisited after validation.
- **Homes stuck on private paths.** A census point inside a private complex (for example condo grounds on Île-des-Soeurs mapped with `access=private` footways) gets snapped onto the private path, and R5 then cannot walk out. **Only for homes that reach no building at all**, the start is moved to the nearest public walkable OSM way within 300 m and re-routed. The distance moved is stored (`origin_moved_m`). This fixed the Île-des-Soeurs DA (897 homes, moved 92 m, now 35 min).
- **Still unreachable, correctly:**
  - **L'Île-Dorval** (25 homes): an island with no bridge and only a seasonal ferry. Its census point falls inside the city's Dorval quartier polygon, so it appears there as unreachable.
  - **The western tip of Île-Bizard:** beyond R5's 2-hour limit. Neighbouring homes already take up to 117 min.
- Unreachable means **"more than 2 h"**. It is never treated as missing data or as 0 when quartiers are summarised.

_Still to be written: per-quartier aggregation, validation results._

## Rent (Phase 2)
_To be written: CMHC neighbourhood level with zone fallback, ratio × StatCan asking rent, reliability rules._
