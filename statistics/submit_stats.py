import argparse
import csv
import io
import json
import subprocess
from pathlib import Path
from typing import Any

from build_stats import MAX_INPUT_BYTES, parse_snapshot

REPOSITORY = "Nienawisc/Schody-WebGL"
MAX_EXPORT_BYTES = 65536


def read_export(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        raw = stream.read(MAX_EXPORT_BYTES + 1)
    if len(raw) > MAX_EXPORT_BYTES:
        raise ValueError("Export is too large. Use the aggregate report, not raw events.")
    if path.suffix.lower() == ".csv":
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig")), strict=True))
        if len(rows) != 2 or rows[0] != ["PUBLIC_STATS_JSON"] or len(rows[1]) != 1:
            raise ValueError("Expected one PUBLIC_STATS_JSON column and exactly one data row.")
        raw = rows[1][0].encode("utf-8")
    elif path.suffix.lower() != ".json":
        raise ValueError("Use the .json report or the single-cell .csv export from Unity.")
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Aggregate JSON is too large.")
    snapshot = parse_snapshot(raw)
    if snapshot["updatedAt"] is None:
        raise ValueError("An exported report must have real data and its SQL timestamp.")
    return snapshot


def submit(path: Path) -> None:
    snapshot = read_export(path)
    payload = json.dumps({"snapshot_json": json.dumps(snapshot, separators=(",", ":"))})
    subprocess.run(
        ["gh", "workflow", "run", "update-statistics.yml", "--repo", REPOSITORY, "--ref", "master", "--json"],
        input=payload, text=True, check=True, capture_output=True, timeout=60,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and send a Unity aggregate JSON/CSV report to GitHub Actions.")
    parser.add_argument("report", type=Path)
    arguments = parser.parse_args()
    try:
        submit(arguments.report)
    except FileNotFoundError:
        parser.exit(1, "Report file or GitHub CLI not found. Install gh, sign in with gh auth login and check the file path.\n")
    except (OSError, ValueError, UnicodeError, RecursionError, csv.Error, subprocess.SubprocessError):
        parser.exit(1, "Could not submit the aggregate report. Check its schema, gh login and Actions access. No raw response is printed.\n")
    print("Report submitted. Check Update public statistics in GitHub Actions; submission is not confirmation of publication.")


if __name__ == "__main__":
    main()
