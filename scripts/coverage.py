"""Join along-track samples to nearby cells/masts, score, and find dead zones."""

import statistics
from dataclasses import dataclass, field

from scripts.fetch_opencellid import operator_name
from scripts.geo import haversine_m
from scripts.gpx import Sample


@dataclass
class SampleCoverage:
    km: float
    lat: float
    lon: float
    ele: float | None
    cell_count: int
    operators: list[str] = field(default_factory=list)
    radios: list[str] = field(default_factory=list)
    nearest_m: float | None = None
    median_samples: float | None = None
    max_samples: int | None = None
    score: str = "none"
    osm_count: int = 0
    osm_nearest_m: float | None = None


def cells_near(sample: Sample, cells: list[dict], search_radius_m: float) -> list[dict]:
    near = []
    for cell in cells:
        d = haversine_m(sample.lat, sample.lon, cell["lat"], cell["lon"])
        effective_radius = max(search_radius_m, cell.get("range") or 0)
        if d <= effective_radius:
            near.append({**cell, "_distance_m": d})
    return near


def masts_near(sample: Sample, masts: list[dict], search_radius_m: float) -> list[dict]:
    near = []
    for mast in masts:
        d = haversine_m(sample.lat, sample.lon, mast["lat"], mast["lon"])
        if d <= search_radius_m:
            near.append({**mast, "_distance_m": d})
    return near


def score_for(cell_count: int, scoring: dict) -> str:
    if cell_count <= scoring["none_max"]:
        return "none"
    if cell_count <= scoring["sparse_max"]:
        return "sparse"
    if cell_count <= scoring["moderate_max"]:
        return "moderate"
    return "dense"


def score_samples(samples: list[Sample], cells: list[dict], masts: list[dict],
                   search_radius_m: float, scoring: dict) -> list[SampleCoverage]:
    results = []
    for sample in samples:
        near_cells = cells_near(sample, cells, search_radius_m)
        near_masts = masts_near(sample, masts, search_radius_m)

        operators = sorted({operator_name(c["mnc"]) for c in near_cells})
        radios = sorted({c["radio"] for c in near_cells})
        samples_seen = [c["samples"] for c in near_cells if c.get("samples")]

        results.append(SampleCoverage(
            km=sample.km,
            lat=sample.lat,
            lon=sample.lon,
            ele=sample.ele,
            cell_count=len(near_cells),
            operators=operators,
            radios=radios,
            nearest_m=min((c["_distance_m"] for c in near_cells), default=None),
            median_samples=statistics.median(samples_seen) if samples_seen else None,
            max_samples=max(samples_seen) if samples_seen else None,
            score=score_for(len(near_cells), scoring),
            osm_count=len(near_masts),
            osm_nearest_m=min((m["_distance_m"] for m in near_masts), default=None),
        ))
    return results


@dataclass
class Run:
    start_km: float
    end_km: float
    length_km: float
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float


def find_runs(coverage: list[SampleCoverage], predicate, min_km: float) -> list[Run]:
    """Merge consecutive samples matching predicate into runs of at least min_km."""
    runs = []
    run: list[SampleCoverage] = []

    def flush():
        if len(run) < 2:
            return
        length = run[-1].km - run[0].km
        if length >= min_km:
            runs.append(Run(
                start_km=run[0].km, end_km=run[-1].km, length_km=length,
                start_lat=run[0].lat, start_lon=run[0].lon,
                end_lat=run[-1].lat, end_lon=run[-1].lon,
            ))

    for point in coverage:
        if predicate(point):
            run.append(point)
        else:
            flush()
            run = []
    flush()
    return runs


def find_gaps(coverage: list[SampleCoverage], gap_min_km: float) -> list[Run]:
    return find_runs(coverage, lambda p: p.cell_count == 0, gap_min_km)


def find_dense_clusters(coverage: list[SampleCoverage], min_km: float = 1.0) -> list[Run]:
    return find_runs(coverage, lambda p: p.score == "dense", min_km)
