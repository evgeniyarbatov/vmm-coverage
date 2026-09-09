import json
import unittest
from pathlib import Path

from scripts.fetch_opencellid import (
    corridor_tiles,
    dedupe_cells,
    filter_mnc,
    filter_radio,
    operator_name,
    parse_live_cell,
)
from scripts.fetch_osm import parse_elements
from scripts.gpx import load_track

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestOpenCellIdParse(unittest.TestCase):
    def setUp(self):
        data = json.loads((FIXTURES / "opencellid_area_sample.json").read_text())
        self.raw_cells = data["cells"]

    def test_parse_live_cell(self):
        c = parse_live_cell(self.raw_cells[0], mcc=452)
        self.assertEqual(c, {
            "radio": "UMTS", "mcc": 452, "mnc": 4,
            "lat": 22.303, "lon": 103.775, "range": 1000.0, "samples": 1,
        })

    def test_dedupe_cells_collapses_repeats(self):
        cells = [parse_live_cell(c, mcc=452) for c in self.raw_cells]
        # fixture's 1st and 4th entries are identical (same lat/lon/mnc/radio)
        self.assertEqual(len(dedupe_cells(cells)), 3)

    def test_filter_mnc(self):
        cells = [parse_live_cell(c, mcc=452) for c in self.raw_cells]
        viettel_only = filter_mnc(cells, [4])
        self.assertTrue(all(c["mnc"] == 4 for c in viettel_only))
        self.assertEqual(len(filter_mnc(cells, [])), len(cells))

    def test_filter_radio(self):
        cells = [parse_live_cell(c, mcc=452) for c in self.raw_cells]
        gsm_only = filter_radio(cells, ["GSM"])
        self.assertEqual(len(gsm_only), 1)
        self.assertEqual(gsm_only[0]["radio"], "GSM")

    def test_unknown_mnc_labeled(self):
        self.assertIn("unknown", operator_name(99))


class TestCorridorTiles(unittest.TestCase):
    def test_no_duplicate_tiles(self):
        points = load_track(str(FIXTURES / "tiny-loop.gpx"))
        tiles = corridor_tiles(points, tile_area_m2=100_000)  # small tiles for a small fixture
        self.assertGreaterEqual(len(tiles), 1)
        self.assertEqual(len(tiles), len(set(tiles)))

    def test_tiles_cover_the_track(self):
        points = load_track(str(FIXTURES / "tiny-loop.gpx"))
        tiles = corridor_tiles(points, tile_area_m2=100_000)
        for p in points:
            covered = any(
                latmin <= p.lat <= latmax and lonmin <= p.lon <= lonmax
                for latmin, lonmin, latmax, lonmax in tiles
            )
            self.assertTrue(covered, f"point {p} not covered by any tile")


class TestOsmParse(unittest.TestCase):
    def test_parse_elements_keeps_only_nodes(self):
        data = json.loads((FIXTURES / "overpass_sample.json").read_text())
        masts = parse_elements(data)
        self.assertEqual(len(masts), 2)
        self.assertEqual(masts[0]["tags"]["man_made"], "mast")


if __name__ == "__main__":
    unittest.main()
