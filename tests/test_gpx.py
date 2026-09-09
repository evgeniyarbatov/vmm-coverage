import unittest
from itertools import pairwise
from pathlib import Path

from scripts.gpx import bbox, densify, load_track

FIXTURE = str(Path(__file__).parent.parent / "fixtures" / "tiny-loop.gpx")


class TestGpx(unittest.TestCase):
    def test_load_track(self):
        points = load_track(FIXTURE)
        self.assertEqual(len(points), 5)
        self.assertAlmostEqual(points[0].lat, 22.0000)
        self.assertAlmostEqual(points[0].lon, 103.0000)

    def test_densify_spacing(self):
        points = load_track(FIXTURE)
        samples = densify(points, sample_m=100)
        self.assertGreater(len(samples), 4)
        self.assertEqual(samples[0].km, 0.0)
        # cumulative distance along the path advances in fixed 100m steps; the straight-line
        # (haversine) gap between two such points can be shorter only at a corner in between.
        for a, b in pairwise(samples[:-1]):
            self.assertAlmostEqual((b.km - a.km) * 1000, 100, delta=0.01)

    def test_densify_rejects_bad_input(self):
        points = load_track(FIXTURE)
        with self.assertRaises(ValueError):
            densify(points, sample_m=0)
        with self.assertRaises(ValueError):
            densify([points[0]], sample_m=100)

    def test_bbox_padding_grows_with_pad_km(self):
        points = load_track(FIXTURE)
        tight = bbox(points, pad_km=0)
        padded = bbox(points, pad_km=15)
        self.assertLess(padded[0], tight[0])
        self.assertLess(padded[1], tight[1])
        self.assertGreater(padded[2], tight[2])
        self.assertGreater(padded[3], tight[3])


if __name__ == "__main__":
    unittest.main()
