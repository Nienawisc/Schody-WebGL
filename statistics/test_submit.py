import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from submit_stats import read_export, submit


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.ready = {
            "schemaVersion": 1, "updatedAt": "2026-11-14T20:00:00Z", "windowStart": "2026-11-13",
            "windowEnd": "2026-11-14", "runs": 50, "deaths": 20, "completedRuns": 5,
        }
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def file(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def csv_export(self, rows):
        stream = io.StringIO()
        csv.writer(stream).writerows(rows)
        return stream.getvalue()

    def test_json(self):
        self.assertEqual(read_export(self.file("report.json", json.dumps(self.ready))), self.ready)

    def test_unity_csv_with_escaped_json_and_bom(self):
        contents = self.csv_export([["PUBLIC_STATS_JSON"], [json.dumps(self.ready)]])
        self.assertEqual(read_export(self.file("report.csv", "\ufeff" + contents)), self.ready)

    def test_csv_extra_rows_and_columns_rejected(self):
        invalid = (
            [["PUBLIC_STATS_JSON", "USER_ID"], [json.dumps(self.ready), "private"]],
            [["PUBLIC_STATS_JSON"], [json.dumps(self.ready)], [json.dumps(self.ready)]],
            [["PUBLIC_STATS_JSON"]],
            [["PUBLIC_STATS_JSON", "PUBLIC_STATS_JSON"], ["{}", "{}"]],
        )
        for rows in invalid:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                read_export(self.file("report.csv", self.csv_export(rows)))

    def test_raw_events_rejected_before_cli(self):
        path = self.file("report.json", '{"USER_ID":"private"}')
        with patch("submit_stats.subprocess.run") as run, self.assertRaises(ValueError):
            submit(path)
        run.assert_not_called()

    def test_unknown_extension_rejected(self):
        with self.assertRaises(ValueError):
            read_export(self.file("report.txt", json.dumps(self.ready)))

    def test_oversized_export_rejected(self):
        with self.assertRaises(ValueError):
            read_export(self.file("report.csv", "x" * 65537))

    def test_duplicate_json_fields_rejected(self):
        with self.assertRaises(ValueError):
            read_export(self.file("report.json", '{"runs":1,"runs":2}'))

    def test_pending_report_rejected(self):
        pending = {key: None for key in self.ready}
        pending["schemaVersion"] = 1
        with self.assertRaises(ValueError):
            read_export(self.file("report.json", json.dumps(pending)))

    def test_cli_uses_stdin_not_shell_interpolation(self):
        path = self.file("report.json", json.dumps(self.ready))
        with patch("submit_stats.subprocess.run") as run:
            submit(path)
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["gh", "workflow", "run", "update-statistics.yml", "--repo", "Nienawisc/Schody-WebGL", "--ref", "master", "--json"])
        self.assertNotIn("shell", kwargs)
        self.assertEqual(json.loads(json.loads(kwargs["input"])["snapshot_json"]), self.ready)
        self.assertTrue(kwargs["check"])
        self.assertTrue(kwargs["capture_output"])


if __name__ == "__main__":
    unittest.main()
