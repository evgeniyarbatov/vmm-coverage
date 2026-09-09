"""Fetch OSM communication infrastructure (masts/towers) in the course bbox via Overpass.

Presence only, not coverage. Kept in its own cache and its own output columns.
"""

import json

import httpx

from scripts.config import get_data_dir, load_config
from scripts.gpx import bbox, load_track

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

QUERY_TEMPLATE = """
[out:json][timeout:60];
(
  node["man_made"="mast"]({latmin},{lonmin},{latmax},{lonmax});
  node["man_made"="tower"]["tower:type"~"communication"]({latmin},{lonmin},{latmax},{lonmax});
  node["tower"="communication"]({latmin},{lonmin},{latmax},{lonmax});
  node["amenity"="telephone"]({latmin},{lonmin},{latmax},{lonmax});
);
out body;
"""


def build_query(box: tuple[float, float, float, float]) -> str:
    latmin, lonmin, latmax, lonmax = box
    return QUERY_TEMPLATE.format(latmin=latmin, lonmin=lonmin, latmax=latmax, lonmax=lonmax)


def parse_elements(data: dict) -> list[dict]:
    masts = []
    for el in data.get("elements", []):
        if el.get("type") != "node":
            continue
        masts.append({
            "lat": el["lat"],
            "lon": el["lon"],
            "tags": el.get("tags", {}),
        })
    return masts


def fetch_overpass(query: str) -> dict:
    resp = httpx.post(OVERPASS_URL, data={"data": query}, timeout=90)
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    config = load_config()
    if not config.get("osm", {}).get("enabled", False):
        print("osm disabled in config.yaml; skipping")
        return 0

    data_dir = get_data_dir()
    osm_dir = data_dir / "osm"
    osm_dir.mkdir(parents=True, exist_ok=True)

    points = load_track(config["gpx"])
    box = bbox(points, config["bbox_pad_km"])

    print("querying Overpass for masts/towers in bbox...")
    data = fetch_overpass(build_query(box))
    masts = parse_elements(data)

    out_path = osm_dir / "masts.json"
    out_path.write_text(json.dumps(masts, indent=2))
    print(f"wrote {len(masts)} masts to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
