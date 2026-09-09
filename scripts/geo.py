"""Minimal geo helpers. No geo stack dependency by design."""

import math

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def interpolate(lat1: float, lon1: float, lat2: float, lon2: float, frac: float) -> tuple[float, float]:
    return (lat1 + (lat2 - lat1) * frac, lon1 + (lon2 - lon1) * frac)


def bbox_pad_degrees(lat: float, pad_km: float) -> tuple[float, float]:
    """Return (dlat, dlon) degree padding for pad_km at the given latitude."""
    dlat = pad_km / 111.0
    dlon = pad_km / (111.0 * max(math.cos(math.radians(lat)), 0.01))
    return dlat, dlon
