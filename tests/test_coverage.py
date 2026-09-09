import unittest

from scripts.coverage import (
    SampleCoverage,
    cells_near,
    find_dense_clusters,
    find_gaps,
    score_for,
    score_samples,
)
from scripts.gpx import Sample

SCORING = {"none_max": 0, "sparse_max": 2, "moderate_max": 8}


def make_coverage(km, cell_count, score=None):
    return SampleCoverage(
        km=km, lat=0.0, lon=0.0, ele=None, cell_count=cell_count,
        score=score if score is not None else score_for(cell_count, SCORING),
    )


class TestScoring(unittest.TestCase):
    def test_score_for_thresholds(self):
        self.assertEqual(score_for(0, SCORING), "none")
        self.assertEqual(score_for(1, SCORING), "sparse")
        self.assertEqual(score_for(2, SCORING), "sparse")
        self.assertEqual(score_for(3, SCORING), "moderate")
        self.assertEqual(score_for(8, SCORING), "moderate")
        self.assertEqual(score_for(9, SCORING), "dense")


class TestCellsNear(unittest.TestCase):
    def test_uses_configured_radius(self):
        sample = Sample(km=0, lat=22.0, lon=103.0, ele=None)
        cells = [{"lat": 22.001, "lon": 103.0, "mnc": 1, "radio": "GSM", "samples": 5, "range": None}]
        # ~111m away: found at 200m radius, not at 50m radius
        self.assertEqual(len(cells_near(sample, cells, 200)), 1)
        self.assertEqual(len(cells_near(sample, cells, 50)), 0)

    def test_cell_range_extends_effective_radius(self):
        sample = Sample(km=0, lat=22.0, lon=103.0, ele=None)
        far_cell = [{"lat": 22.02, "lon": 103.0, "mnc": 1, "radio": "LTE", "samples": 5, "range": 3000}]
        # ~2.2km away: missed by a 500m search radius alone, caught by the cell's own range
        self.assertEqual(len(cells_near(sample, far_cell, 500)), 1)


class TestScoreSamples(unittest.TestCase):
    def test_operators_and_radios_aggregate(self):
        samples = [Sample(km=0, lat=22.0, lon=103.0, ele=100)]
        cells = [
            {"lat": 22.0005, "lon": 103.0, "mnc": 4, "radio": "LTE", "samples": 10, "range": None},
            {"lat": 22.0006, "lon": 103.0, "mnc": 1, "radio": "GSM", "samples": 20, "range": None},
        ]
        result = score_samples(samples, cells, [], 3000, SCORING)
        self.assertEqual(len(result), 1)
        cov = result[0]
        self.assertEqual(cov.cell_count, 2)
        self.assertEqual(cov.operators, sorted(["Vinaphone", "Viettel"]))
        self.assertEqual(cov.radios, sorted(["GSM", "LTE"]))
        self.assertEqual(cov.median_samples, 15)
        self.assertEqual(cov.score, "sparse")


class TestFindGaps(unittest.TestCase):
    def test_merges_runs_and_drops_short_ones(self):
        coverage = [
            make_coverage(0, 0), make_coverage(1, 0), make_coverage(2, 0),  # 2km gap
            make_coverage(3, 5),  # covered
            make_coverage(4, 0),  # 0km run, too short alone
        ]
        gaps = find_gaps(coverage, gap_min_km=2.0)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].start_km, 0)
        self.assertEqual(gaps[0].end_km, 2)
        self.assertEqual(gaps[0].length_km, 2.0)

    def test_no_gaps_when_all_covered(self):
        coverage = [make_coverage(i, 5) for i in range(5)]
        self.assertEqual(find_gaps(coverage, gap_min_km=2.0), [])


class TestFindDenseClusters(unittest.TestCase):
    def test_finds_dense_run(self):
        coverage = [
            make_coverage(0, 0, "none"),
            make_coverage(1, 20, "dense"),
            make_coverage(2, 20, "dense"),
            make_coverage(3, 20, "dense"),
            make_coverage(4, 0, "none"),
        ]
        clusters = find_dense_clusters(coverage, min_km=1.0)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].start_km, 1)
        self.assertEqual(clusters[0].end_km, 3)


if __name__ == "__main__":
    unittest.main()
