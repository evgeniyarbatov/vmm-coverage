# Architecture

```
gpx/course.gpx
      │
      ▼
scripts/gpx.py        load_track → densify(sample_m) → bbox(pad_km)
      │                                          │
      │                                          ▼
      │                          scripts/fetch_opencellid.py (network, cached)
      │                          scripts/fetch_osm.py        (network, cached, optional)
      │                                          │
      │                          $DATA_DIR/opencellid/cells.json
      │                          $DATA_DIR/osm/masts.json
      │                                          │
      └──────────────► scripts/coverage.py ◄─────┘
                        cells_near / masts_near (haversine, per-cell range)
                        score_for (config thresholds)
                        find_gaps / find_dense_clusters
                                │
                                ▼
                        scripts/report.py
                                │
              ┌─────────────────┼──────────────────────┐
              ▼                 ▼                       ▼
   $DATA_DIR/samples.json  docs/coverage.csv    docs/coverage.geojson
   $DATA_DIR/cells.json    docs/coverage.gpx     docs/gaps.json
   $DATA_DIR/gaps.json     docs/summary.md       docs/index.html (Leaflet, reads the two above)
```

`scripts/run.py` is the `make run` entrypoint: it wires `gpx.py` → `coverage.py` →
`report.py` and never touches the network — everything it reads comes from the cache
`make fetch` populated.

`$DATA_DIR` is the durable cache (outside git). `docs/` is the publishable surface: CSV
and GPX for personal use, GeoJSON/JSON/HTML for the GitHub Pages map.

OpenCellID fetch order: country CSV export (cheap, one file per MCC) first; only falls
back to tiled `getInArea` calls, under a daily credit budget, if the export is empty in
the padded bbox.
