# gpx/

Drop the official VMM course file from
[VTS GPS files](https://vietnamtrailseries.com/mountain-marathon/practical-info/vmm-gps-files/)
into this directory and point `gpx:` in `config.yaml` at it (or use `make run GPX=...`).

`vmm-100-miles-2024.gpx` is the current default course, already committed here.

If no course file is present, tests and `make run` fall back to `fixtures/tiny-loop.gpx`.
