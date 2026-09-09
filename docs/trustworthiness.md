# How trustworthy is the reported coverage?

Assessment of the current pipeline and the data behind `docs/summary.md` /
`docs/coverage.csv` / `site/`, based on the code in `scripts/` and the live cache
under `$DATA_DIR` as of the last `make fetch && make run`.

## Bottom line

Treat scores as *relative* signal — "this stretch has more observed towers nearby
than that one" — not as an estimate of signal strength or probability of a bar on
your phone. The labeling throughout the repo (README, summary, site) already says
this correctly. The methodology has three structural weaknesses that make even the
relative signal noisier than it looks.

## What the data actually is

- 296 OpenCellID cells along the course corridor, fetched live via `getInArea`
  (`fetch_opencellid.py`), not the bulk export — the bulk export returned effectively
  nothing for this area (1 cell vs. 13+ from the live API in a single tile).
- **Every single one of the 296 cells has `samples: 1`** — OpenCellID has exactly one
  crowdsourced observation for each tower in this corridor. There is no cell in this
  dataset backed by repeated, cross-validated measurements.
- No 5G/NR towers in the dataset (GSM/UMTS/LTE only) — plausible for rural
  Hoàng Liên Sơn, not itself a red flag.

## Structural weaknesses

### 1. Single-sample towers mean unverified position and unverified existence

OpenCellID computes a tower's recorded lat/lon by triangulating across contributor
reports. With `samples: 1`, the coordinate is essentially wherever one phone happened
to be when it logged that cell ID — there was never a second observation to
cross-check it against. In flat, dense urban areas this is usually within tens to
low-hundreds of meters. In mountainous terrain with few contributors, a single
GPS fix can plausibly be off by more, and there's no way to tell which of the 296
cells that applies to from the data alone.

### 2. Straight-line distance ignores terrain

`cells_near()` (`scripts/coverage.py`) scores a sample point as "covered" if a tower
is within `search_radius_m` (3000 m) haversine distance — a flat-earth straight line,
with no line-of-sight or elevation check. The Hoàng Liên Sơn course crosses ridgelines
and valleys; a tower 2 km away by straight line can be on the far side of a mountain
with no realistic RF path to the trail. This will systematically overstate "dense"/
"moderate" coverage in exactly the terrain where the tool matters most — deep valleys
and ridge sections.

### 3. `range` mostly defaults to a flat 1000 m, and gets overridden by the wider search radius

`cells_near()` takes `effective_radius = max(search_radius_m, cell.range)`. Across the
296 cells, `range` is 770–6079 m with a median of exactly **1000 m** — i.e. for the
large majority of cells OpenCellID isn't reporting a meaningfully estimated coverage
radius (unsurprising with `samples: 1`, since range is itself derived from spread
across multiple observations). Because `search_radius_m` (3000 m) is larger than that
default for nearly every cell, the per-cell `range` field ends up contributing almost
nothing — practically every scoring decision reduces to "is there a tower within
3000 m in a straight line," regardless of radio type (a 3000 m nominal reach is
generous for GSM/UMTS in mountainous terrain and conservative for LTE).

## What's *not* a problem

- **Fetch completeness**: the corridor sweep used 47 tiles and pulled 395 raw cells
  (296 after de-dup/filtering) — well under the 900-credit daily budget, so this run
  wasn't truncated by the API cap.
- **Attribution and disclaimers**: README, `site/index.html`, and
  `docs/summary.md` all consistently call this "observed-tower density," not a
  signal map or guarantee — matches this repo's own ground rules.
- **OSM masts are kept separate**: `osm_count`/`osm_nearest_m` are reported as
  distinct columns and never folded into the OpenCellID-derived score, so
  infrastructure presence isn't laundered into a coverage number.
- **No test-vs-prod data leakage**: `tests/` runs against `fixtures/` only, no network
  calls, so the reported numbers in `docs/` come only from the real API responses
  cached under `$DATA_DIR`.

## If you wanted tighter numbers

- Weight or flag cells by `samples` count (a `samples: 1` cell is weaker evidence
  than one with many); currently the join treats all cells identically regardless of
  confidence.
- Use `range` as the *only* radius when it's present and non-default, falling back to
  `search_radius_m` only when a cell has no real range estimate — right now the wider
  of the two always wins, which mostly discards `range`.
- Add an elevation-aware check (e.g. drop a tower if a ridge separates it from the
  sample point) — meaningfully harder given "no geo stack dependency" is a stated
  design constraint (`scripts/geo.py`), but that's the assumption most likely to be
  wrong on this specific course.
