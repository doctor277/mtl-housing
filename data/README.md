# data/

`raw/` and `interim/` are **gitignored**. Only this README and `manifest.csv` are committed.

```
data/
├─ manifest.csv          one row per raw file: source, URL, download date, SHA-256
├─ raw/                  files exactly as downloaded, never edited by hand
│  ├─ boundaries/        quartierreferencehabitation.geojson, nombrelogementsquartiersreference.csv
│  ├─ gtfs/              stm.zip, rem.zip, exo_<sector>.zip
│  ├─ osm/               quebec-YYMMDD.osm.pbf (Geofabrik)
│  ├─ statcan/           2021_92-151_X.zip (Geographic Attribute File), 46100092-eng.zip (rent table 46-10-0092-01)
│  └─ cmhc/              HMIP exports, renamed: cmhc_rms_2025-10_avg_rent_by_neighbourhood.csv, cmhc_rms_2025-10_avg_rent_by_zone.csv
└─ interim/              produced by the pipeline (clipped PBF, sample points, raw travel times)
```

## Rules

1. Keep the downloaded file name or use the name above. The pipeline reads paths from `pipeline/src/mtlhousing/config.py`.
2. After adding or replacing a raw file, add or update its row in `manifest.csv` (download date + SHA-256).
   PowerShell: `Get-FileHash <file> -Algorithm SHA256`.
3. When a source is refreshed (new GTFS season, new CMHC survey), replace the file, update the manifest, re-run the pipeline, and commit the regenerated `web/public/data/` together with the manifest change.
