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
   $DATA_DIR/samples.json  docs/coverage.csv    site/coverage.geojson
   $DATA_DIR/cells.json    docs/coverage.gpx     site/gaps.json
   $DATA_DIR/gaps.json     docs/summary.md       site/index.html (Leaflet, reads the two above)
                                                          │
                                          .github/workflows/pages.yml
                                                          ▼
                                                    GitHub Pages
```

`scripts/run.py` is the `make run` entrypoint: it wires `gpx.py` → `coverage.py` →
`report.py` and never touches the network — everything it reads comes from the cache
`make fetch` populated.

`$DATA_DIR` is the durable cache (outside git). `docs/` holds personal-use reports (CSV,
GPX, summary). `site/` is the standalone Pages publish surface — nothing under `docs/`
is needed to view the map, only what's committed under `site/`.

OpenCellID fetch: the per-country bulk CSV export is stale/incomplete for Vietnam (one
cell across the whole padded course bbox, vs. 13+ in a single 2km tile from the live
API), so `fetch_opencellid.py` tiles a corridor along the track itself and queries the
live `getInArea` API tile by tile, bounded by `opencellid.max_api_credits` per run.
