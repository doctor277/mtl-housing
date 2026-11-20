# Data sources

All inputs are free and open. **No listing sites are scraped.**
Raw files live in `data/raw/` (gitignored). Their exact versions are pinned in [`data/manifest.csv`](data/manifest.csv) (download date + SHA-256).

| # | Dataset | Publisher | Used for | Phase | Licence | Status |
|---|---|---|---|---|---|---|
| 1 | Quartiers de référence en habitation (GeoJSON) | Ville de Montréal, [donnees.montreal.ca/dataset/quartiers](https://donnees.montreal.ca/dataset/quartiers) | Neighbourhood polygons (91 quartiers, includes the villes liées) | 1 | CC BY 4.0 | downloaded |
| 2 | Nombre de logements par quartier de référence (CSV) | Ville de Montréal, same page | Dwelling counts per quartier (cross-check) | 1 | CC BY 4.0 | downloaded |
| 3 | STM GTFS *planifiés* | Société de transport de Montréal, [données ouvertes](https://www.stm.info/a-propos/documents-donnees/donnees-ouvertes) | Bus + metro schedules | 1 | CC BY 4.0 + metro condition (below) | downloaded |
| 4 | REM GTFS | Réseau express métropolitain, [gtfs.gpmmom.ca](https://gtfs.gpmmom.ca/gtfs/gtfs.zip) | REM light metro schedules | 1 | CC BY 4.0 | downloaded |
| 5 | exo GTFS, trains | exo, [données ouvertes](https://exo.quebec/fr/a-propos/donnees-ouvertes) | Commuter rail (5 lines) | 1 | CC BY 4.0 | downloaded |
| 6 | OpenStreetMap, Québec extract (`.osm.pbf`) | Geofabrik, download.geofabrik.de | Walking network for r5py | 1 | ODbL 1.0 | downloaded |
| 7 | 2021 Census Geographic Attribute File (92-151-X) | Statistics Canada | Dissemination-block representative points + dwelling counts → residential sample points | 1 | Statistics Canada Open Licence | downloaded |
| 8 | Rental Market Survey, average rent by bedroom type, Oct 2025, **Neighbourhood** level (+ **Zone** level for fallback) | CMHC Housing Market Information Portal | Relative rent level per area | 2 | CMHC terms (see attribution) | to do |
| 9 | Table 46-10-0092-01, Asking rent and paid rent prices, by rental unit type and number of bedrooms (experimental estimates), quarterly | Statistics Canada, [table page](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=4610009201) | Citywide asking rent, Montréal CMA | 2 | Statistics Canada Open Licence | downloaded |

## Attribution text to show on the site

- **OpenStreetMap:** "© OpenStreetMap contributors" (ODbL). Must appear on the map and on the sources page.
- **Ville de Montréal:** "Contains data from the Ville de Montréal open data portal, licensed under CC BY 4.0."
- **Statistics Canada:** "Adapted from Statistics Canada, [product], [date]. This does not constitute an endorsement by Statistics Canada of this product."
- **CMHC:** "Adapted from Canada Mortgage and Housing Corporation, [product], [date]. This does not constitute an endorsement by CMHC." **No CMHC logo.**
- **STM, REM, exo (CC BY 4.0):** "Transit schedules: Société de transport de Montréal, Réseau express métropolitain and exo, licensed under CC BY 4.0. Travel times are derived from these schedules." Name each publisher, link the licence, and say the data was transformed.

## STM metro schedule condition: how we comply

The STM licence states that its **metro schedules are indicative**. They are meant for estimating trip durations and **may not be used to build a metro timetable application**.

This project only computes **door-to-door trip durations** (median and range per neighbourhood), which is the use the STM intends. The site never shows metro departure times, timetables or "next train" information, and the published JSON contains no schedule data, only aggregated minutes. Any future feature that would display metro times must be checked against this condition first.

## Known limits of the sources

- Feeds currently pinned (see `data/manifest.csv`):
  - STM `20261029135439_26N`, valid 2026-08-24 → 2027-01-03.
  - REM `20260520`, valid 2026-05-19 → 2026-12-31.
  - exo trains, valid 2026-10-19 → 2027-01-03.

  The analysis date must be a weekday inside **all three** windows and before the STM change on 2027-01-05. Tue 2026-11-24 / Wed 2026-11-25 / Tue 2026-12-01 / Wed 2026-12-02 all have full weekday service in every feed.
- CMHC average rents include sitting tenants and so understate what a newcomer pays. See `docs/methodology.md` (Phase 2) for how they are adjusted and labelled.
- Schedules are not reliability: GTFS does not capture delays, outages or detours.
