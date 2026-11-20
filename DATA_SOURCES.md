# Data sources

All inputs are free and open. **No listing sites are scraped.**
Raw files live in `data/raw/` (gitignored). Their exact versions are pinned in [`data/manifest.csv`](data/manifest.csv) (download date + SHA-256).

Rows marked **TODO** still need the exact download URL or licence text confirmed before the site goes public (Phase 4 at the latest).

| # | Dataset | Publisher | Used for | Phase | Licence | Status |
|---|---|---|---|---|---|---|
| 1 | Quartiers de référence en habitation (GeoJSON) | Ville de Montréal, donnees.montreal.ca | Neighbourhood polygons (91 quartiers, includes the villes liées) | 1 | CC BY 4.0 | downloaded |
| 2 | Nombre de logements par quartier de référence (CSV) | Ville de Montréal, donnees.montreal.ca | Dwelling counts per quartier (checks / weighting) | 1 | CC BY 4.0 | downloaded |
| 3 | STM GTFS, *planifiés* (`gtfs_stm.zip`) | Société de transport de Montréal, stm.info developers page | Bus + metro schedules | 1 | TODO: confirm STM open-data terms | downloaded |
| 4 | REM GTFS | ARTM / REM open data | REM light metro schedules | 1 | TODO | **not yet downloaded** |
| 5 | exo GTFS (train sectors serving the island) | exo / ARTM open data | Commuter rail | 1 | TODO | **not yet downloaded** |
| 6 | OpenStreetMap, Québec extract (`.osm.pbf`) | Geofabrik, download.geofabrik.de | Walking network for r5py | 1 | ODbL 1.0 | downloaded |
| 7 | 2021 Census Geographic Attribute File (92-151-X) | Statistics Canada | Dissemination-block representative points + dwelling counts → residential sample points | 1 | Statistics Canada Open Licence | downloaded |
| 8 | Rental Market Survey, average rent by bedroom type, Oct 2025, **Neighbourhood** level (+ **Zone** level for fallback) | CMHC Housing Market Information Portal | Relative rent level per area | 2 | CMHC terms (see attribution) | to do |
| 9 | Table 46-10-0092-01, Quarterly rent statistics | Statistics Canada | Citywide asking rent, Montréal CMA | 2 | Statistics Canada Open Licence | to do |

## Attribution text to show on the site

- **OpenStreetMap:** "© OpenStreetMap contributors" (ODbL). Must appear on the map and on the sources page.
- **Ville de Montréal:** "Contains data from the Ville de Montréal open data portal, licensed under CC BY 4.0."
- **Statistics Canada:** "Adapted from Statistics Canada, [product], [date]. This does not constitute an endorsement by Statistics Canada of this product."
- **CMHC:** "Adapted from Canada Mortgage and Housing Corporation, [product], [date]. This does not constitute an endorsement by CMHC." **No CMHC logo.**
- **STM / ARTM / exo:** TODO, copy the required wording from each publisher's open-data terms.

## Known limits of the sources

- STM feed currently pinned: `feed_version 20261029135439_26N`, valid 2026-08-24 → 2027-01-03. The next STM schedule change is 2027-01-05, so the analysis date must be a weekday **before** that.
- CMHC average rents include sitting tenants and so understate what a newcomer pays. See `docs/methodology.md` (Phase 2) for how they are adjusted and labelled.
- Schedules are not reliability: GTFS does not capture delays, outages or detours.
