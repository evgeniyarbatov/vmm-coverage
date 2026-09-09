"""Write samples/cells/gaps JSON (cache), and the CSV/GPX/summary/geojson reports (docs/)."""

import csv
import json
from dataclasses import asdict
from pathlib import Path

import gpxpy
import gpxpy.gpx

from scripts.coverage import Run, SampleCoverage, find_dense_clusters


def write_data_json(data_dir: Path, coverage: list[SampleCoverage], cells: list[dict],
                     gaps: list[Run]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "samples.json").write_text(json.dumps([asdict(c) for c in coverage], indent=2))
    (data_dir / "cells.json").write_text(json.dumps(cells, indent=2))
    (data_dir / "gaps.json").write_text(json.dumps([asdict(g) for g in gaps], indent=2))


def write_csv(docs_dir: Path, coverage: list[SampleCoverage]) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    path = docs_dir / "coverage.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["km", "lat", "lon", "ele", "score", "operators", "radios",
                          "nearest_m", "cell_count"])
        for c in coverage:
            writer.writerow([
                round(c.km, 3), c.lat, c.lon, c.ele, c.score,
                "|".join(c.operators), "|".join(c.radios),
                round(c.nearest_m) if c.nearest_m is not None else "",
                c.cell_count,
            ])


def write_gpx(docs_dir: Path, coverage: list[SampleCoverage], gaps: list[Run]) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack(name="VMM coverage")
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)
    for c in coverage:
        segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=c.lat, longitude=c.lon, elevation=c.ele))

    for gap in gaps:
        wpt = gpxpy.gpx.GPXWaypoint(
            latitude=gap.start_lat, longitude=gap.start_lon,
            name=f"gap {gap.length_km:.1f}km @ km{gap.start_km:.1f}",
        )
        gpx.waypoints.append(wpt)

    for cluster in find_dense_clusters(coverage):
        wpt = gpxpy.gpx.GPXWaypoint(
            latitude=cluster.start_lat, longitude=cluster.start_lon,
            name=f"dense {cluster.length_km:.1f}km @ km{cluster.start_km:.1f}",
        )
        gpx.waypoints.append(wpt)

    (docs_dir / "coverage.gpx").write_text(gpx.to_xml())


def write_geojson(docs_dir: Path, coverage: list[SampleCoverage], gaps: list[Run]) -> None:
    """Data file for docs/index.html; $DATA_DIR is gitignored so Pages needs its own copy."""
    docs_dir.mkdir(parents=True, exist_ok=True)
    features = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [c.lon, c.lat]},
        "properties": {
            "km": round(c.km, 3), "score": c.score, "cell_count": c.cell_count,
            "operators": c.operators, "nearest_m": c.nearest_m,
        },
    } for c in coverage]
    geojson = {"type": "FeatureCollection", "features": features}
    (docs_dir / "coverage.geojson").write_text(json.dumps(geojson))
    (docs_dir / "gaps.json").write_text(json.dumps([asdict(g) for g in gaps], indent=2))


def write_summary(docs_dir: Path, config: dict, coverage: list[SampleCoverage],
                   gaps: list[Run]) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    race = config["race"]
    total_km = coverage[-1].km if coverage else 0.0
    score_counts = {s: 0 for s in ("none", "sparse", "moderate", "dense")}
    for c in coverage:
        score_counts[c.score] += 1

    lines = [
        f"# {race['name']} — coverage readout",
        "",
        f"Course: {race['location']} · start {race['start']}",
        (f"Track length sampled: {total_km:.1f} km ({len(coverage)} points, "
         f"{config['sample_m']} m spacing)"),
        "",
        ("**This is observed-tower density, not a signal guarantee.** OpenCellID's tower "
         "database is sparse in the Hoàng Liên Sơn; a point with no observed cells nearby "
         "may still have signal, and a point with cells nearby may not."),
        "",
        "## Score distribution",
        "",
        "| score | points | share |",
        "|---|---|---|",
    ]
    for score in ("none", "sparse", "moderate", "dense"):
        n = score_counts[score]
        pct = (n / len(coverage) * 100) if coverage else 0
        lines.append(f"| {score} | {n} | {pct:.0f}% |")

    lines += ["", "## Likely dead zones (no observed cells within radius)", ""]
    if gaps:
        lines.append("| from km | to km | length km |")
        lines.append("|---|---|---|")
        for g in gaps:
            lines.append(f"| {g.start_km:.1f} | {g.end_km:.1f} | {g.length_km:.1f} |")
    else:
        lines.append(f"None found ≥ {config['gap_min_km']} km.")

    lines += [
        "",
        "## Notes",
        "",
        ("- Viettel often has the widest mountain reach in Vietnam; this tool only counts "
         "*observed towers*, not your SIM."),
        "- Cell data: [OpenCellID](https://opencellid.org), CC BY-SA 4.0.",
    ]
    if config.get("osm", {}).get("enabled"):
        lines.append("- Infrastructure presence: OpenStreetMap contributors, ODbL.")

    (docs_dir / "summary.md").write_text("\n".join(lines) + "\n")
