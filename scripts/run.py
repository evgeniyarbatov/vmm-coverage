"""Pipeline entrypoint: gpx -> sample -> join towers -> report. Offline; reads only the cache."""

import argparse
import json
from pathlib import Path

from scripts.config import get_data_dir, load_config
from scripts.coverage import find_gaps, score_samples
from scripts.gpx import bbox, densify, load_track
from scripts.report import write_csv, write_data_json, write_geojson, write_gpx, write_summary


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpx", default=None, help="override config.yaml's gpx path")
    args = parser.parse_args()

    config = load_config()
    if args.gpx:
        config["gpx"] = args.gpx

    data_dir = get_data_dir()
    docs_dir = Path("docs")

    points = load_track(config["gpx"])
    samples = densify(points, config["sample_m"])
    box = bbox(points, config["bbox_pad_km"])

    cells = load_json(data_dir / "opencellid" / "cells.json", [])
    masts = load_json(data_dir / "osm" / "masts.json", [])

    if not cells:
        print("no cached OpenCellID cells found; run `make fetch` first")

    coverage = score_samples(samples, cells, masts, config["search_radius_m"], config["scoring"])
    gaps = find_gaps(coverage, config["gap_min_km"])

    write_data_json(data_dir, coverage, cells, gaps)
    write_csv(docs_dir, coverage)
    write_gpx(docs_dir, coverage, gaps)
    write_geojson(docs_dir, coverage, gaps)
    write_summary(docs_dir, config, coverage, gaps)

    print(f"bbox: {box}")
    print(f"{len(samples)} samples, {len(cells)} cells, {len(masts)} masts, {len(gaps)} gaps")
    print("wrote docs/coverage.csv, docs/coverage.gpx, docs/summary.md, docs/coverage.geojson")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
