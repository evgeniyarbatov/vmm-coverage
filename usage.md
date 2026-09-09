# Usage

## Makefile targets

| target | does |
|---|---|
| `make install` | `uv sync --group dev` |
| `make lock` | `uv lock` |
| `make test` | run `tests/` (unittest, no network, no API key) |
| `make lint` | `ruff check .` |
| `make fetch` | download/refresh OpenCellID + OSM data into `DATA_DIR` |
| `make run` | gpx → sample → join towers → report, offline from cache |
| `make clean` | remove derived JSON/CSV/GPX/summary; keeps the downloaded tower DB |
| `make help` | list targets |

`DATA_DIR` (default `~/Documents/data/vmm-coverage`) and `GPX` (default from
`config.yaml`) are overridable: `make run GPX=gpx/other.gpx`.

## config.yaml

| key | meaning |
|---|---|
| `race.*` | name/location/start time, used in `docs/summary.md` |
| `gpx` | default course file |
| `sample_m` | along-track sample spacing (meters) |
| `search_radius_m` | max distance from a sample to count a cell |
| `bbox_pad_km` | padding around the track bbox when fetching |
| `gap_min_km` | minimum length of a zero-cell stretch to report as a dead zone |
| `opencellid.mcc` | country code filter (452 = Vietnam) |
| `opencellid.mncs` | operator filter; empty = all |
| `opencellid.radios` | radio filter (GSM/UMTS/LTE/NR); empty = all |
| `opencellid.prefer_download` | try the country CSV export before the live API |
| `opencellid.max_api_credits` | daily credit cap for the `getInArea` fallback |
| `osm.enabled` | also query Overpass for masts/towers |
| `scoring.*` | cell-count thresholds for none/sparse/moderate/dense |

## Publishing the map

`make run` also writes `docs/coverage.geojson`, `docs/gaps.json`, and reads them from
`docs/index.html` (Leaflet, OSM basemap). Commit those three plus `docs/coverage.csv`,
`docs/coverage.gpx`, `docs/summary.md` after a real `make fetch && make run`, then enable
GitHub Pages on the repo (Settings → Pages → deploy from `main` / `docs`).
