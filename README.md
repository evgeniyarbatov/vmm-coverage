# vmm-coverage

Approximate cell-tower density along a VMM course GPX (OpenCellID + public sources).

**What this is:** a personal recon tool — before race day, see where along the track
OpenCellID has *observed* cell towers nearby, and where it hasn't.

**What this is not:** a signal map, a coverage guarantee, or a live carrier feed. Community
tower data is sparse in the Hoàng Liên Sơn. A "none" score means no towers have been
*observed* near that point — it does not mean you will have no signal there, and a
"dense" score does not mean you will.

```bash
make install
make test
make fetch    # needs OPENCELLID_API_KEY, see below
make run
make run GPX=/path/to/other-course.gpx
```

`make fetch` is the only step that touches the network; `make run` works entirely from
the cache under `DATA_DIR` (default `~/Documents/data/vmm-coverage`).

## API key

Get a free key at [opencellid.org](https://opencellid.org) (docs:
[docs.opencellid.org](https://docs.opencellid.org)). Copy `.env.example` to `.env` and
set `OPENCELLID_API_KEY`.

## Course GPX

The default course, `gpx/vmm-100-miles-2024.gpx`, is already in the repo. To use a
different year or distance, drop the official file from
[VTS GPS files](https://vietnamtrailseries.com/mountain-marathon/practical-info/vmm-gps-files/)
into `gpx/` and either set `gpx:` in `config.yaml` or pass `make run GPX=...`.

## Output

- `docs/coverage.csv` — per-sample km, position, score, operators, radios, nearest tower
- `docs/coverage.gpx` — track with waypoints at dead zones and dense clusters
- `docs/summary.md` — human-readable readout for race morning
- `site/index.html`, `site/coverage.geojson`, `site/gaps.json` — a Leaflet map of the
  above; commit these after `make run` and GitHub Pages deploys `site/` via
  `.github/workflows/pages.yml`

See [architecture.md](architecture.md) for the pipeline.

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
| `bbox_pad_km` | padding around the track bbox for the OSM Overpass query |
| `gap_min_km` | minimum length of a zero-cell stretch to report as a dead zone |
| `opencellid.mcc` | country code filter (452 = Vietnam) |
| `opencellid.mncs` | operator filter; empty = all |
| `opencellid.radios` | radio filter (GSM/UMTS/LTE/NR); empty = all |
| `opencellid.max_api_credits` | daily credit budget for the live `getInArea` sweep |
| `osm.enabled` | also query Overpass for masts/towers |
| `scoring.*` | cell-count thresholds for none/sparse/moderate/dense |

## Publishing the map

`make run` writes `site/coverage.geojson` and `site/gaps.json`, which `site/index.html`
(Leaflet, OSM basemap) reads. `make serve` serves `site/` locally at
`http://localhost:8000` (browsers block `fetch` of local files opened directly, so don't
just double-click `index.html`). Commit `site/` after a real `make fetch && make run`;
`.github/workflows/pages.yml` deploys it on push to `main`. GitHub Pages needs to be
enabled once (Settings → Pages → source: GitHub Actions) — note that Pages on a
**private** repo requires GitHub Pro/Team/Enterprise; the free plan only supports it on
public repos.

## Attribution

Cell data: [OpenCellID](https://opencellid.org), CC BY-SA 4.0. Infrastructure presence
(optional, OSM Overpass): OpenStreetMap contributors, ODbL.

Viettel often has the widest mountain reach in Vietnam; this tool only counts *observed
towers*, not your SIM.
