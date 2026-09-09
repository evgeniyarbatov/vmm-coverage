"""Fetch OpenCellID cells for a corridor along the course track via the live getInArea API.

Network only happens here. `make run` reads the cache this writes. The per-country bulk
CSV export was tried first in an earlier version but is dramatically stale/incomplete for
Vietnam (1 cell in the whole padded course bbox vs. 13+ in a single 2km tile from the live
API), so this fetches live, tiled along the track, bounded by a daily credit budget.
"""

import json
import math
import os
import sys
import time
from pathlib import Path

import httpx

from scripts.config import get_data_dir, load_config, load_env
from scripts.geo import tile_degrees
from scripts.gpx import densify, load_track

AREA_URL = "https://opencellid.org/cell/getInArea"
AREA_SIZE_URL = "https://opencellid.org/cell/getInAreaSize"
MAX_TILE_AREA_M2 = 4_000_000  # OpenCellID's own getInArea/getInAreaSize hard limit
TILE_SAFETY = 0.9  # margin below the hard limit

VN_OPERATORS = {
    1: "Vinaphone",
    2: "Mobifone",
    4: "Viettel",
    5: "Vietnamobile",
    7: "Gmobile",
}


def operator_name(mnc: int) -> str:
    return VN_OPERATORS.get(mnc, f"unknown (mnc {mnc})")


def parse_live_cell(raw: dict, mcc: int) -> dict:
    return {
        "radio": raw.get("radio", "?"),
        "mcc": int(raw.get("mcc", mcc)),
        "mnc": int(raw.get("mnc", -1)),
        "lat": float(raw["lat"]),
        "lon": float(raw["lon"]),
        "range": float(raw["range"]) if raw.get("range") else None,
        "samples": int(raw.get("samples", 0)),
    }


def dedupe_cells(cells: list[dict]) -> list[dict]:
    """Adjacent tiles can return the same cell twice; key on rounded position + mnc + radio."""
    seen = set()
    out = []
    for c in cells:
        key = (round(c["lat"], 5), round(c["lon"], 5), c["mnc"], c["radio"])
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def filter_mnc(cells: list[dict], mncs: list[int]) -> list[dict]:
    if not mncs:
        return cells
    return [c for c in cells if c["mnc"] in mncs]


def filter_radio(cells: list[dict], radios: list[str]) -> list[dict]:
    if not radios:
        return cells
    wanted = {r.upper() for r in radios}
    return [c for c in cells if c["radio"].upper() in wanted]


def corridor_tiles(points, tile_area_m2: float = MAX_TILE_AREA_M2 * TILE_SAFETY):
    """Tile boxes covering a corridor along the track, deduped on a tile-sized grid."""
    mid_lat = sum(p.lat for p in points) / len(points)
    dlat, dlon = tile_degrees(mid_lat, tile_area_m2)
    tile_side_m = math.sqrt(tile_area_m2)
    samples = densify(points, sample_m=tile_side_m / 2)

    seen = set()
    tiles = []
    for s in samples:
        ix, iy = math.floor(s.lat / dlat), math.floor(s.lon / dlon)
        if (ix, iy) in seen:
            continue
        seen.add((ix, iy))
        latmin, lonmin = ix * dlat, iy * dlon
        tiles.append((latmin, lonmin, latmin + dlat, lonmin + dlon))
    return tiles


def get_in_area_size(box: tuple[float, float, float, float], key: str, mcc: int) -> int:
    latmin, lonmin, latmax, lonmax = box
    params = {"key": key, "BBOX": f"{latmin},{lonmin},{latmax},{lonmax}", "mcc": mcc, "format": "json"}
    resp = httpx.get(AREA_SIZE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return int(resp.json().get("count", 0))


def get_in_area(box: tuple[float, float, float, float], key: str, mcc: int, offset: int = 0) -> list[dict]:
    latmin, lonmin, latmax, lonmax = box
    params = {
        "key": key, "BBOX": f"{latmin},{lonmin},{latmax},{lonmax}",
        "mcc": mcc, "format": "json", "limit": 50, "offset": offset,
    }
    resp = httpx.get(AREA_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("cells", [])


def fetch_corridor(tiles: list[tuple], key: str, mcc: int, budget: int, cache_dir: Path) -> list[dict]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cells: list[dict] = []
    spent = 0
    tiles_done = 0

    for tile in tiles:
        if spent >= budget:
            break
        tiles_done += 1
        size = get_in_area_size(tile, key, mcc)
        if size == 0:
            continue
        offset = 0
        while offset < size and spent < budget:
            raw = get_in_area(tile, key, mcc, offset=offset)
            if not raw:
                break
            spent += len(raw)
            cells.extend(parse_live_cell(c, mcc) for c in raw)
            offset += len(raw)
            time.sleep(0.2)

    if tiles_done < len(tiles):
        print(f"stopped after {tiles_done}/{len(tiles)} tiles: hit max_api_credits budget ({budget})")

    tile_path = cache_dir / f"corridor_{mcc}.json"
    tile_path.write_text(json.dumps(cells, indent=2))
    return dedupe_cells(cells)


def main() -> int:
    load_env()
    config = load_config()
    data_dir = get_data_dir()
    ocid_dir = data_dir / "opencellid"
    out_path = ocid_dir / "cells.json"
    mcc = config["opencellid"]["mcc"]

    key = os.environ.get("OPENCELLID_API_KEY")
    if not key:
        if out_path.exists():
            print(f"no OPENCELLID_API_KEY set; reusing cached {out_path}")
            return 0
        print("no cache and no OPENCELLID_API_KEY set; cannot fetch", file=sys.stderr)
        return 1

    points = load_track(config["gpx"])
    tiles = corridor_tiles(points)
    print(f"sweeping {len(tiles)} tiles along the track (budget {config['opencellid']['max_api_credits']} credits)...")

    cells = fetch_corridor(tiles, key, mcc, config["opencellid"]["max_api_credits"], ocid_dir / "tiles")
    cells = filter_mnc(cells, config["opencellid"]["mncs"])
    cells = filter_radio(cells, config["opencellid"]["radios"])

    ocid_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(cells, indent=2))
    print(f"wrote {len(cells)} cells to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
