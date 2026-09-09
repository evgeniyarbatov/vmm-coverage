# Agent rules for vmm-coverage

## Never do

- Commit OpenCellID/OSM raw dumps, API keys, or anything under `$DATA_DIR`.
- Call OpenCellID or Overpass from `tests/`. Tests use `fixtures/` only.
- Describe this tool's output as a "coverage guarantee", "signal map", or anything implying
  live carrier data. It is observed-tower density from a community database.
- Scrape CellMapper, OpenSignal, nPerf, GSMA maps, or Google for coverage data.
- Hardcode Sapa/VMM place names in pipeline code; they belong in `config.yaml` or the GPX.

## Pipeline invariants

- `make fetch` is the only network step. `make run` must work fully offline from cache.
- New sources go behind a provider interface, enabled in `config.yaml`, default off unless
  free and key-optional (OpenCellID, OSM Overpass). Paid APIs stay behind an explicit flag.
- Keep OSM and OpenCellID columns distinct in reports; OSM is infrastructure presence, not
  coverage.
