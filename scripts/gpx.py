"""Load, clean, densify a GPX track and compute its padded bbox."""

from dataclasses import dataclass
from itertools import pairwise

import gpxpy

from scripts.geo import bbox_pad_degrees, haversine_m, interpolate


@dataclass
class TrackPoint:
    lat: float
    lon: float
    ele: float | None


@dataclass
class Sample:
    km: float
    lat: float
    lon: float
    ele: float | None


def load_track(path: str) -> list[TrackPoint]:
    with open(path, encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    points: list[TrackPoint] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for pt in segment.points:
                points.append(TrackPoint(lat=pt.latitude, lon=pt.longitude, ele=pt.elevation))

    if not points:
        raise ValueError(f"no track points found in {path}")

    # Drop consecutive duplicate points (zero-distance segments break interpolation).
    cleaned = [points[0]]
    for pt in points[1:]:
        prev = cleaned[-1]
        if haversine_m(prev.lat, prev.lon, pt.lat, pt.lon) > 0:
            cleaned.append(pt)
    return cleaned


def densify(points: list[TrackPoint], sample_m: float) -> list[Sample]:
    """Resample the polyline every sample_m meters, interpolating lat/lon/ele."""
    if len(points) < 2:
        raise ValueError("need at least 2 track points to densify")
    if sample_m <= 0:
        raise ValueError("sample_m must be positive")

    samples = [Sample(km=0.0, lat=points[0].lat, lon=points[0].lon, ele=points[0].ele)]
    cum_m = 0.0
    next_target_m = sample_m

    for prev, cur in pairwise(points):
        seg_len = haversine_m(prev.lat, prev.lon, cur.lat, cur.lon)
        if seg_len == 0:
            continue
        seg_start_m = cum_m
        seg_end_m = cum_m + seg_len

        while next_target_m <= seg_end_m:
            frac = (next_target_m - seg_start_m) / seg_len
            lat, lon = interpolate(prev.lat, prev.lon, cur.lat, cur.lon, frac)
            ele = None
            if prev.ele is not None and cur.ele is not None:
                ele = prev.ele + (cur.ele - prev.ele) * frac
            samples.append(Sample(km=next_target_m / 1000.0, lat=lat, lon=lon, ele=ele))
            next_target_m += sample_m

        cum_m = seg_end_m

    last = points[-1]
    if samples[-1].lat != last.lat or samples[-1].lon != last.lon:
        samples.append(Sample(km=cum_m / 1000.0, lat=last.lat, lon=last.lon, ele=last.ele))

    return samples


def bbox(points: list[TrackPoint], pad_km: float) -> tuple[float, float, float, float]:
    """Return (latmin, lonmin, latmax, lonmax) padded by pad_km."""
    lats = [p.lat for p in points]
    lons = [p.lon for p in points]
    latmin, latmax = min(lats), max(lats)
    lonmin, lonmax = min(lons), max(lons)

    mid_lat = (latmin + latmax) / 2
    dlat, dlon = bbox_pad_degrees(mid_lat, pad_km)

    return (latmin - dlat, lonmin - dlon, latmax + dlat, lonmax + dlon)
