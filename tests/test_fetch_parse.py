import csv
import json
import unittest
from pathlib import Path

from scripts.fetch_opencellid import (
    CSV_FIELDS,
    filter_bbox,
    filter_mnc,
    filter_radio,
    operator_name,
    parse_csv_rows,
)
from scripts.fetch_osm import parse_elements

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestOpenCellIdParse(unittest.TestCase):
    def setUp(self):
        with open(FIXTURES / "opencellid_sample.csv", newline="", encoding="utf-8") as f:
            self.rows = list(csv.DictReader(f, fieldnames=CSV_FIELDS))

    def test_parse_skips_malformed_rows(self):
        cells = parse_csv_rows(self.rows)
        # 4 rows in fixture, 1 has a missing lat and must be dropped
        self.assertEqual(len(cells), 3)
        self.assertTrue(all(isinstance(c["lat"], float) for c in cells))

    def test_filter_bbox(self):
        cells = parse_csv_rows(self.rows)
        near = filter_bbox(cells, (22.0, 103.0, 22.001, 103.001))
        self.assertEqual(len(near), 1)
        self.assertEqual(near[0]["mnc"], 1)

    def test_filter_mnc(self):
        cells = parse_csv_rows(self.rows)
        viettel_only = filter_mnc(cells, [4])
        self.assertEqual(len(viettel_only), 1)
        self.assertEqual(operator_name(viettel_only[0]["mnc"]), "Viettel")

        self.assertEqual(len(filter_mnc(cells, [])), len(cells))

    def test_filter_radio(self):
        cells = parse_csv_rows(self.rows)
        gsm_only = filter_radio(cells, ["GSM"])
        self.assertEqual(len(gsm_only), 1)
        self.assertEqual(gsm_only[0]["radio"], "GSM")

    def test_unknown_mnc_labeled(self):
        self.assertIn("unknown", operator_name(99))


class TestOsmParse(unittest.TestCase):
    def test_parse_elements_keeps_only_nodes(self):
        data = json.loads((FIXTURES / "overpass_sample.json").read_text())
        masts = parse_elements(data)
        self.assertEqual(len(masts), 2)
        self.assertEqual(masts[0]["tags"]["man_made"], "mast")


if __name__ == "__main__":
    unittest.main()
