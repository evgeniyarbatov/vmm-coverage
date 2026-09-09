"""Fetch OpenCellID cells for the course bbox: download-first, tiled API fallback.

Network only happens here. `make run` reads the cache this writes.
"""

import csv
import gzip
import json
import os
import sys
import time
from pathlib import Path

import httpx

from scripts.config import get_data_dir, load_config, load_env
from scripts.gpx import bbox, load_track

DOWNLOAD_URL = "https://opencellid.org/ocid/downloads?token={token}&type=mcc&file={mcc}.csv.gz"
AREA_URL = "https://opencellid.org/cell/getInArea"
AREA_SIZE_URL = "https://opencellid.org/cell/getInAreaSize"

CSV_FIELDS = [
    "radio", "mcc", "net", "area", "cell", "unit",
    "lon", "lat", "range", "samples", "changeable", "created", "updated", "averageSignal",
]

VN_OPERATORS = {
    1: "Vinaphone",
    2: "Mobifone",
    4: "Viettel",
    5: "Vietnamobile",
    7: "Gmobile",
}


def operator_name(mnc: int) -> str:
    return VN_OPERATORS.get(mnc, f"unknown (mnc {mnc})")


def parse_csv_rows(rows: list[dict]) -> list[dict]:
    """Convert raw OpenCellID CSV dict-rows into typed cell records."""
    cells = []
    for row in rows:
        try:
            cells.append({
                "radio": row["radio"],
                "mcc": int(row["mcc"]),
                "mnc": int(row["net"]),
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "range": float(row["range"]) if row.get("range") else None,
                "samples": int(row["samples"]) if row.get("samples") else 0,
            })
        except (KeyError, ValueError):
            continue
    return cells


def filter_bbox(cells: list[dict], box: tuple[float, float, float, float]) -> list[dict]:
    latmin, lonmin, latmax, lonmax = box
    return [c for c in cells if latmin <= c["lat"] <= latmax and lonmin <= c["lon"] <= lonmax]


def filter_mnc(cells: list[dict], mncs: list[int]) -> list[dict]:
    if not mncs:
        return cells
    return [c for c in cells if c["mnc"] in mncs]


def filter_radio(cells: list[dict], radios: list[str]) -> list[dict]:
    if not radios:
        return cells
    wanted = {r.upper() for r in radios}
    return [c for c in cells if c["radio"].upper() in wanted]


def download_country_csv(mcc: int, token: str, dest_gz: Path) -> bool:
    """Download the per-MCC CSV export. Returns False on any non-2xx response."""
    url = DOWNLOAD_URL.format(token=token, mcc=mcc)
    dest_gz.parent.mkdir(parents=True, exist_ok=True)
    try:
        with httpx.stream("GET", url, timeout=120, follow_redirects=True) as resp:
            if resp.status_code != 200:
                return False
            with open(dest_gz, "wb") as f:
                f.writelines(resp.iter_bytes())
        return dest_gz.stat().st_size > 0
    except httpx.HTTPError:
        return False


def load_country_csv(dest_gz: Path) -> list[dict]:
    with gzip.open(dest_gz, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, fieldnames=CSV_FIELDS)
        return list(reader)


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


def split_tiles(box: tuple[float, float, float, float], tile_deg: float = 0.2):
    latmin, lonmin, latmax, lonmax = box
    lat = latmin
    while lat < latmax:
        lon = lonmin
        lat_hi = min(lat + tile_deg, latmax)
        while lon < lonmax:
            lon_hi = min(lon + tile_deg, lonmax)
            yield (lat, lon, lat_hi, lon_hi)
            lon = lon_hi
        lat = lat_hi


def fetch_via_tiled_api(box: tuple[float, float, float, float], key: str, mcc: int,
                         budget: int, cache_dir: Path) -> list[dict]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cells: list[dict] = []
    spent = 0
    for tile in split_tiles(box):
        if spent >= budget:
            break
        size = get_in_area_size(tile, key, mcc)
        if size == 0:
            continue
        offset = 0
        while offset < size and spent < budget:
            raw = get_in_area(tile, key, mcc, offset=offset)
            if not raw:
                break
            spent += len(raw)
            for c in raw:
                cells.append({
                    "radio": c.get("radio", "?"),
                    "mcc": int(c.get("mcc", mcc)),
                    "mnc": int(c.get("mnc", -1)),
                    "lat": float(c["lat"]),
                    "lon": float(c["lon"]),
                    "range": float(c["range"]) if c.get("range") else None,
                    "samples": int(c.get("samples", 0)),
                })
            offset += len(raw)
            time.sleep(0.2)
    tile_path = cache_dir / f"tiles_{mcc}.json"
    tile_path.write_text(json.dumps(cells, indent=2))
    return cells


def main() -> int:
    load_env()
    config = load_config()
    data_dir = get_data_dir()
    ocid_dir = data_dir / "opencellid"

    points = load_track(config["gpx"])
    box = bbox(points, config["bbox_pad_km"])
    mcc = config["opencellid"]["mcc"]

    key = os.environ.get("OPENCELLID_API_KEY")
    raw_gz = ocid_dir / "raw" / f"{mcc}.csv.gz"
    cells: list[dict] = []

    if config["opencellid"].get("prefer_download", True):
        if raw_gz.exists():
            cells = parse_csv_rows(load_country_csv(raw_gz))
        elif key:
            print(f"downloading OpenCellID CSV export for mcc={mcc}...")
            if download_country_csv(mcc, key, raw_gz):
                cells = parse_csv_rows(load_country_csv(raw_gz))

    cells = filter_bbox(cells, box)

    if not cells:
        if not key:
            if not raw_gz.exists():
                print("no cache and no OPENCELLID_API_KEY set; cannot fetch", file=sys.stderr)
                return 1
        else:
            print("country export empty in bbox; falling back to tiled getInArea...")
            cells = fetch_via_tiled_api(
                box, key, mcc, config["opencellid"]["max_api_credits"], ocid_dir / "tiles"
            )

    cells = filter_mnc(cells, config["opencellid"]["mncs"])
    cells = filter_radio(cells, config["opencellid"]["radios"])

    ocid_dir.mkdir(parents=True, exist_ok=True)
    out_path = ocid_dir / "cells.json"
    out_path.write_text(json.dumps(cells, indent=2))
    print(f"wrote {len(cells)} cells to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
