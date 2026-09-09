# vmm-coverage

Approximate cell-tower density along a VMM course GPX (OpenCellID + public sources). Not live coverage.

This private repo is a **seed**. There is no pipeline yet. The build spec lives in [`CLAUDE-PROMPT.md`](CLAUDE-PROMPT.md) — paste that file into Claude (with GitHub access) and have it implement the project **in this repo**.

## After the project exists

```bash
make install
make test
make fetch    # needs OPENCELLID_API_KEY
make run      # or: make run GPX=/path/to/course.gpx
```

Drop an official VMM GPX from [VTS GPS files](https://vietnamtrailseries.com/mountain-marathon/practical-info/vmm-gps-files/) into `gpx/` and set `gpx:` in `config.yaml`.

OpenCellID data is CC BY-SA 4.0. Observed towers near the track ≠ guaranteed signal on race day.
