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
- `docs/coverage.geojson`, `docs/gaps.json`, `docs/index.html` — a Leaflet map of the
  above; commit these after `make run` and enable GitHub Pages (serve from `docs/` on
  `main`) to view it online

See [usage.md](usage.md) for all Makefile targets and config knobs, and
[architecture.md](architecture.md) for the pipeline.

## Attribution

Cell data: [OpenCellID](https://opencellid.org), CC BY-SA 4.0. Infrastructure presence
(optional, OSM Overpass): OpenStreetMap contributors, ODbL.

Viettel often has the widest mountain reach in Vietnam; this tool only counts *observed
towers*, not your SIM.
