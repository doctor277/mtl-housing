# Methodology and limitations

This file is filled in as each phase lands. It becomes the site's "Sources & limitations" page in Phase 4.

## Geography
- Unit of analysis: the Ville de Montréal **quartiers de référence en habitation** (91 areas). The layer also covers the villes liées (Westmount, Mont-Royal, Côte-Saint-Luc, …), so the whole island is included.
- 91 quartiers across 15 municipalities, with 1,011,945 dwellings in total (city CSV). **L'Île-Dorval**, a tiny seasonal island municipality with no transit, is not in the city's layer and is not covered.
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

_Still to be written: sample points, r5py settings, departure window, validation results._

## Rent (Phase 2)
_To be written: CMHC neighbourhood level with zone fallback, ratio × StatCan asking rent, reliability rules._
