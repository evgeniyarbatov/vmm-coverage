# Claude Prompt — create `vmm-coverage` from scratch

Work in the existing **private** repo `evgeniyarbatov/vmm-coverage`. Do not create another repository. Do not stop at a design. Write the files, lock dependencies, commit, and leave a working project.

## Goal

Personal recon tool for **Vietnam Mountain Marathon (VMM)** so I know, *before race day*, where along a course GPX I should expect cellphone / data coverage vs radio silence.

Approximate only. Community tower databases are sparse in the Hoàng Liên Sơn. Never claim this is live carrier coverage, signal bars, or guaranteed 4G/5G. Output must say **observed towers near the track**, not “you will have signal here.”

Primary source: **OpenCellID**. Secondary public sources only if they stay free, key-optional or env-keyed, and do not require scraping.

## Repo already exists

- Owner: `evgeniyarbatov`
- Name: `vmm-coverage`
- **Private**
- Description: `Approximate cell-tower density along a VMM course GPX (OpenCellID + public sources). Not live coverage.`
- Do not add a license file unless asked.
- Do not enable GitHub Pages.
- Keep this file (`CLAUDE-PROMPT.md`). You may replace the short seed `README.md` with the real project README specified below.
- Commit on `main` and push.

## Match my existing VMM repo style

Mirror conventions from `evgeniyarbatov/vmm-stargazing` (public, same event). This repo is smaller and data-focused. No GitHub Pages site unless a tiny static report in `docs/` is cheap to generate from JSON.

Stack:

- Python ≥ 3.11
- **uv** (`pyproject.toml` + `uv.lock`)
- **Makefile** as the only user interface
- `config.yaml` for race + pipeline knobs
- Course GPX in `gpx/`
- Scripts in `scripts/`
- Tests in `tests/` (`unittest`, `test_*.py`)
- Cache **outside git**: `DATA_DIR ?= $(HOME)/Documents/data/vmm-coverage`
- Override course with `make run GPX=/path/to/course.gpx`
- `.env` for secrets, never committed
- `CLAUDE.md` for agent rules
- Short `README.md`, `usage.md`, `architecture.md`, `ROADMAP.md`

Makefile targets that must exist:

```
make install    # uv sync --group dev
make lock       # uv lock
make test       # unittest, no network, no API keys
make lint       # ruff
make fetch      # download / refresh cell data into $DATA_DIR
make run        # gpx → sample → join towers → report
make clean      # derived JSON only, keep downloaded tower DB
make help
```

Typical flow:

```
make install
make test
make fetch    # needs OPENCELLID_API_KEY for download token / area API
make run
make run GPX=gpx/other.gpx
```

## What “coverage along the course” means

1. Read a GPX track (VMM 100 miles by default; any distance works).
2. Densify / sample points every N meters (default 250 m, configurable).
3. For each sample, find OpenCellID cells whose reported position is within a search radius (default 3 km; also consider each cell’s `range` when present).
4. Aggregate per sample and per course km:
   - cell count
   - unique operators (MCC/MNC)
   - radio mix: GSM / UMTS / LTE / NR / other
   - max / median samples (observation quality)
   - nearest cell distance
   - crude score: `none | sparse | moderate | dense`
5. Flag likely **dead zones**: consecutive samples with 0 cells inside radius, stretches longer than e.g. 2 km.
6. Write:
   - `$DATA_DIR/samples.json` — along-track samples + scores
   - `$DATA_DIR/cells.json` — cells kept after bbox/radius filter
   - `$DATA_DIR/gaps.json` — dead-zone stretches
   - `docs/coverage.csv` — km, lat, lon, ele, score, operators, radios, nearest_m, cell_count
   - `docs/coverage.gpx` — track + waypoints for gaps and dense clusters
   - `docs/summary.md` — human readout for race morning

Do **not** invent signal dBm or throughput.

## OpenCellID — how to fetch (important)

Live `cell/getInArea` is a bad default:

- 1 000 API credits / day
- each returned cell costs 1 credit
- max ~50 cells per call
- Sapa bbox can burn the quota

Prefer this order:

1. **Country / world CSV download** (best). OpenCellID daily exports (cells observed in last ~18 months). Filter to **MCC 452 (Vietnam)** and a bbox padded around the GPX (default pad 15 km). Cache the filtered parquet/csv under `$DATA_DIR/opencellid/` and never commit it.
2. If the country extract is missing Vietnam or is empty in the mountains, fall back to tiled `getInArea` / `getInAreaSize` with small bboxes along the track, pagination, and a hard daily budget from config.
3. Always cache. `make fetch` is the only network step. `make run` must work offline from cache.

API details to implement correctly:

- Key via `OPENCELLID_API_KEY` (also used as download token on opencellid.org).
- `GET https://opencellid.org/cell/getInArea?key=...&BBOX=latmin,lonmin,latmax,lonmax&mcc=452&format=json&limit=50&offset=...`
- `GET https://opencellid.org/cell/getInAreaSize?...` first when using the live API.
- Radio filter optional: GSM, UMTS, LTE, NR, CDMA.
- License: **CC BY-SA 4.0**. README and `docs/summary.md` must attribute OpenCellID / Unwired Labs.

Vietnam operators to label (MCC 452):

| MNC | Brand        |
|-----|--------------|
| 01  | Vinaphone    |
| 02  | Mobifone     |
| 04  | Viettel      |
| 05  | Vietnamobile |
| 07  | Gmobile      |
| others | unknown (keep raw MNC) |

Viettel is the mountain default in travel lore; still treat that as commentary in the summary, not as data.

## Other public APIs / sources (optional, pluggable)

Add a provider interface so sources can be enabled in `config.yaml` without rewriting the pipeline.

Implement OpenCellID fully. Stub or lightly implement only if cheap and legal:

- **OpenStreetMap Overpass** (no key): `tower=communication`, `man_made=mast`, `man_made=tower` + `communication:*`, `amenity=telephone` in the course bbox. This is infrastructure presence, not coverage. Label it separately (`osm_masts`).
- Do **not** scrape CellMapper, OpenSignal, nPerf, GSMA maps, or Google.
- Do **not** add paid APIs (Ookla Cell Maps, HERE cellular attributes) unless they are behind an explicit config flag and env key, default **off**.
- No Mozilla MLS (retired).

If Overpass is on, cache the JSON in `$DATA_DIR/osm/` and join the same way (distance to nearest mast). Keep OSM and OpenCellID columns distinct in the CSV.

## Repo layout

```
vmm-coverage/
  README.md
  CLAUDE.md
  CLAUDE-PROMPT.md     # keep this seed prompt
  usage.md
  architecture.md
  ROADMAP.md
  Makefile
  pyproject.toml
  uv.lock
  config.yaml
  .env.example
  .gitignore
  gpx/
    README.md          # where official VTS GPX goes; do not invent geometry
  scripts/
    gpx.py             # load, clean, densify, bbox
    fetch_opencellid.py
    fetch_osm.py       # optional
    coverage.py        # join samples ↔ cells, score, gaps
    report.py          # csv / gpx / summary.md
  tests/
    test_gpx.py
    test_coverage.py
    test_fetch_parse.py  # parse fixture JSON/CSV only
  fixtures/            # tiny synthetic GPX + a handful of fake cells
```

Do **not** commit:

- real OpenCellID dumps
- API keys
- full official VMM GPX if redistribution is unclear — put a placeholder `gpx/README.md` that says: drop the official file from https://vietnamtrailseries.com/mountain-marathon/practical-info/vmm-gps-files/ into `gpx/` and set `gpx:` in `config.yaml`. If a GPX already exists in my other repos (`vmm-stargazing/gpx/`) you may copy it only if it is clearly my file. Otherwise ship `fixtures/tiny-loop.gpx` so tests and `make run` work out of the box.

## `config.yaml` sketch

```yaml
race:
  name: VMM 100 Miles 2026
  location: Sa Pa / Hoàng Liên Sơn
  start: 2026-09-18T08:00:00+07:00
  timezone: Asia/Ho_Chi_Minh

gpx: gpx/course.gpx   # overridden by make GPX=...

sample_m: 250
search_radius_m: 3000
bbox_pad_km: 15
gap_min_km: 2.0

opencellid:
  mcc: 452
  mncs: [1, 2, 4, 5, 7]   # empty = all VN
  radios: []              # empty = all
  prefer_download: true
  max_api_credits: 200    # live-API safety cap

osm:
  enabled: true

scoring:
  none_max: 0
  sparse_max: 2
  moderate_max: 8
  # else dense
```

## Python / quality bar

- Typed where it helps; no framework soup. `httpx` or `requests`, `pyyaml`, `gpxpy` (or minimal XML), `pandas` only if it earns its keep.
- Deterministic scoring so tests are stable.
- Haversine in a tiny helper; no geo stack required.
- Ruff-clean.
- Tests use `fixtures/`; never call the network in `make test`.
- Fail loudly if `make fetch` has no key and no cache.
- `.gitignore`: `.env`, `__pycache__`, `.venv`, `uv` cache, `$DATA_DIR` if someone points it inside the repo, `*.csv.gz` tower dumps.

## README tone

Same family as vmm-stargazing: short, concrete, no marketing.

Must include:

- What this is / is not
- `make install && make test && make fetch && make run`
- `OPENCELLID_API_KEY` + link to https://opencellid.org / https://docs.opencellid.org
- GPX drop-in instructions
- Attribution (OpenCellID CC BY-SA 4.0; OSM ODbL if Overpass is used)
- “Viettel often has the widest mountain reach in VN; this tool only counts *observed towers*, not your SIM.”

## CLAUDE.md must forbid

- Committing tower dumps, keys, or `$DATA_DIR`
- Hitting OpenCellID or Overpass inside tests
- Calling this output “coverage guarantee” or “signal map”
- Scraping commercial coverage maps
- Hardcoding Sapa place names when they can come from config / GPX

## ROADMAP (write the file, do not implement all of it)

- Per-operator along-track plots
- Overlay aid-station checkpoints if a CSV is supplied
- Compare two SIMs (Viettel vs Vinaphone) as separate columns
- Optional paid coverage layer behind a flag
- Night vs day is irrelevant here; do not port stargazing code

## Implementation order

1. Confirm you are writing into `evgeniyarbatov/vmm-coverage` (already private)
2. `pyproject.toml`, Makefile, config, gitignore, env example
3. Fixture GPX + scoring unit tests
4. GPX loader + sampler
5. OpenCellID fetch (download-first, API fallback) + cache
6. Join + gaps + reports
7. Optional Overpass
8. `uv lock`, `make test` green
9. README / usage / architecture / CLAUDE.md (keep `CLAUDE-PROMPT.md`)
10. Commit and push to `main`

When done, print:

- repo URL
- tree
- exact commands I run on my machine
- which files need the official VMM GPX and the API key

Do not write a blog post. Do not add CI that needs secrets. Ship the project.
