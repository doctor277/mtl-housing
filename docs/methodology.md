# Methodology and limitations

This file is filled in as each phase lands. It becomes the site's "Sources & limitations" page in Phase 4.

## Geography
- Unit of analysis: the Ville de Montréal **quartiers de référence en habitation** (91 areas). The layer also covers the villes liées (Westmount, Mont-Royal, Côte-Saint-Luc, …), so the whole island is included.
- 91 quartiers across 15 municipalities, with 1,011,945 dwellings in total (city CSV). **L'Île-Dorval**, a tiny seasonal island municipality with no transit, is not in the city's layer and is not covered.
- Six source polygons have small self-intersections. They are repaired automatically, and the area of each changes by less than 30 m². Neighbouring polygons overlap by up to a few hundred m² from how the borders were drawn, which is negligible.

## Commute (Phase 1)

### Campus destinations
Each campus is a single point taken from OpenStreetMap (2026-11-19). Where one is tagged, it is the building's `entrance=main` node:

| Campus | Point | OSM |
|---|---|---|
| Université de Montréal | Pavillon Roger-Gaudry main entrance (L-4), 2900 boul. Édouard-Montpetit | node/2573744215 |
| McGill (downtown) | Roddick Gates, Sherbrooke O. at McGill College | way/143798969 |
| Concordia SGW | Henry F. Hall Building main entrance, 1455 boul. De Maisonneuve O. | node/4035248248 |

Limitation: these are large campuses. If your classes are in another building, your trip can differ by 5–10 minutes, especially at UdeM, which is spread over a hillside.

_Still to be written: sample points, r5py settings, departure window, validation results._

## Rent (Phase 2)
_To be written: CMHC neighbourhood level with zone fallback, ratio × StatCan asking rent, reliability rules._
