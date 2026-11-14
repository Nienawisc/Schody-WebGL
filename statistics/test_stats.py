import copy
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from build_stats import HEIGHT, MAX_COUNT, WIDTH, build, normalize_snapshot, public_stats, read_snapshot


class StatisticsTests(unittest.TestCase):
    def setUp(self):
        self.ready = {
            "schemaVersion": 1,
            "updatedAt": "2026-11-14T20:00:00Z",
            "windowStart": "2026-11-13",
            "windowEnd": "2026-11-14",
            "runs": 50,
            "deaths": 20,
            "completedRuns": 5,
        }
        self.pending = {key: None for key in self.ready}
        self.pending["schemaVersion"] = 1

    def test_rate_uses_only_known_outcomes(self):
        self.assertEqual(public_stats(self.ready)["escapeRatePercent"], 20)

    def test_pending_is_not_zero(self):
        result = public_stats(self.pending)
        self.assertEqual(result["status"], "awaiting-data")
        self.assertIsNone(result["deaths"])
        self.assertIsNone(result["escapeRatePercent"])

    def test_empty_published_report(self):
        self.ready.update(runs=0, deaths=0, completedRuns=0, windowStart=None, windowEnd=None)
        result = public_stats(self.ready)
        self.assertEqual(result["status"], "published")
        self.assertIsNone(result["escapeRatePercent"])

    def test_unresolved_runs_do_not_create_a_zero_rate(self):
        self.ready.update(deaths=0, completedRuns=0)
        self.assertIsNone(public_stats(self.ready)["escapeRatePercent"])

    def test_only_deaths_gives_zero_rate(self):
        self.ready["completedRuns"] = 0
        self.assertEqual(public_stats(self.ready)["escapeRatePercent"], 0)

    def test_only_completions_gives_full_rate(self):
        self.ready["deaths"] = 0
        self.assertEqual(public_stats(self.ready)["escapeRatePercent"], 100)

    def test_raw_data_and_unknown_fields_rejected(self):
        for key in ("USER_ID", "sc_run_id", "token", "events", "extra"):
            candidate = dict(self.ready, **{key: "do not publish"})
            with self.subTest(key=key), self.assertRaises(ValueError):
                normalize_snapshot(candidate)

    def test_invalid_counts_rejected(self):
        for value in (True, False, 1.5, -1, "12", float("nan"), float("inf"), MAX_COUNT + 1, None):
            candidate = dict(self.ready, deaths=value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_snapshot(candidate)

    def test_outcomes_cannot_exceed_runs(self):
        self.ready["runs"] = 24
        with self.assertRaises(ValueError):
            normalize_snapshot(self.ready)

    def test_missing_field_rejected(self):
        del self.ready["windowEnd"]
        with self.assertRaises(ValueError):
            normalize_snapshot(self.ready)

    def test_invalid_timestamp_rejected(self):
        for value in (None, "today", "2026-11-14T20:00:00", "2026-02-30T20:00:00Z", "<script>"):
            candidate = dict(self.ready, updatedAt=value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_snapshot(candidate)

    def test_reversed_dates_rejected(self):
        self.ready["windowStart"] = "2026-11-15"
        with self.assertRaises(ValueError):
            normalize_snapshot(self.ready)

    def test_mixed_pending_rejected(self):
        self.pending["updatedAt"] = self.ready["updatedAt"]
        with self.assertRaises(ValueError):
            normalize_snapshot(self.pending)

    def test_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text('{"schemaVersion":1,"schemaVersion":1}', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_snapshot(path)

    def test_oversized_input_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text(" " * 8193, encoding="utf-8")
            with self.assertRaises(ValueError):
                read_snapshot(path)

    def test_schema_version_boolean_rejected(self):
        self.ready["schemaVersion"] = True
        with self.assertRaises(ValueError):
            normalize_snapshot(self.ready)

    def test_deterministic_render_does_not_refresh_report_date(self):
        original = copy.deepcopy(self.ready)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "snapshot.json"
            source.write_text(json.dumps(self.ready), encoding="utf-8")
            build(source, root / "first")
            build(source, root / "second")
            for filename in ("stats.json", "stats.png"):
                self.assertEqual((root / "first" / filename).read_bytes(), (root / "second" / filename).read_bytes())
            exported = json.loads((root / "first" / "stats.json").read_text())
            self.assertEqual(exported["updatedAt"], original["updatedAt"])
            with Image.open(root / "first" / "stats.png") as image:
                self.assertEqual(image.size, (WIDTH, HEIGHT))
        self.assertEqual(self.ready, original)

    def test_failed_build_does_not_overwrite_last_card(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "snapshot.json"
            source.write_text(json.dumps(self.ready), encoding="utf-8")
            build(source, root / "public")
            previous = (root / "public" / "stats.png").read_bytes()
            source.write_text('{"USER_ID":"private"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                build(source, root / "public")
            self.assertEqual((root / "public" / "stats.png").read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
