import argparse
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
FIELDS = frozenset({"schemaVersion", "updatedAt", "windowStart", "windowEnd", "runs", "deaths", "completedRuns"})
COUNT_FIELDS = ("runs", "deaths", "completedRuns")
MAX_COUNT = 9_007_199_254_740_991
MAX_INPUT_BYTES = 8192
WIDTH, HEIGHT = 1040, 900
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
BACKGROUND = "#101114"
PANEL = "#191B20"
BORDER = "#35373E"
INK = "#F3EEE5"
MUTED = "#B8B5B0"
ACCENT = "#E8A260"
RED = "#E78577"


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys are not allowed.")
        result[key] = value
    return result


def normalize_snapshot(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or set(data) != FIELDS:
        raise ValueError("Use only the exact aggregate fields documented in the snapshot schema.")
    if type(data["schemaVersion"]) is not int or data["schemaVersion"] != 1:
        raise ValueError("Unsupported schemaVersion.")
    pending = all(data[field] is None for field in COUNT_FIELDS)
    if pending:
        if any(data[field] is not None for field in ("updatedAt", "windowStart", "windowEnd")):
            raise ValueError("An unpublished snapshot must have null dates and counters.")
        return dict(data)
    for field in COUNT_FIELDS:
        if type(data[field]) is not int or not 0 <= data[field] <= MAX_COUNT:
            raise ValueError(f"{field} must be a non-negative, safe integer.")
    if data["deaths"] + data["completedRuns"] > data["runs"]:
        raise ValueError("Deaths plus completed runs cannot exceed recorded runs.")
    timestamp = data["updatedAt"]
    if not isinstance(timestamp, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp):
        raise ValueError("updatedAt must be a UTC timestamp like 2026-11-14T20:00:00Z.")
    datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    parsed_dates = []
    for field in ("windowStart", "windowEnd"):
        value = data[field]
        if value is None and data["runs"] == 0:
            parsed_dates.append(None)
            continue
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError(f"{field} must be a date in YYYY-MM-DD format.")
        parsed_dates.append(date.fromisoformat(value))
    if (parsed_dates[0] is None) != (parsed_dates[1] is None):
        raise ValueError("Reporting window dates must both be present or both be null.")
    if parsed_dates[0] is not None and parsed_dates[0] > parsed_dates[1]:
        raise ValueError("windowStart must not be later than windowEnd.")
    return dict(data)


def parse_snapshot(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Snapshot is too large. Never upload raw events or player data.")
    return normalize_snapshot(json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object))


def read_snapshot(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return parse_snapshot(stream.read(MAX_INPUT_BYTES + 1))


def check_replacement(previous: dict[str, Any], incoming: dict[str, Any]) -> None:
    previous = normalize_snapshot(previous)
    incoming = normalize_snapshot(incoming)
    if incoming["updatedAt"] is None:
        raise ValueError("A submitted report must contain real aggregate data and its report timestamp.")
    if previous["updatedAt"] is None:
        return
    if incoming["updatedAt"] < previous["updatedAt"]:
        raise ValueError("A submitted report must not be older than the published snapshot.")
    if incoming["updatedAt"] == previous["updatedAt"] and incoming != previous:
        raise ValueError("Different data requires a new SQL report timestamp.")


def public_stats(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = normalize_snapshot(snapshot)
    pending = result["runs"] is None
    finished = 0 if pending else result["deaths"] + result["completedRuns"]
    result["status"] = "awaiting-data" if pending else "published"
    result["escapeRatePercent"] = None if finished == 0 else round(100 * result["completedRuns"] / finished, 2)
    result["scope"] = "available_analytics_data"
    return result


def render_card(stats: dict[str, Any]) -> bytes:
    stats = public_stats({field: stats[field] for field in FIELDS})
    ET.register_namespace("", SVG_NAMESPACE)
    root = ET.Element(f"{{{SVG_NAMESPACE}}}svg", {
        "width": str(WIDTH), "height": str(HEIGHT), "viewBox": f"0 0 {WIDTH} {HEIGHT}",
        "role": "img", "aria-labelledby": "card-title card-description",
        "font-family": "Arial, Helvetica, sans-serif",
    })

    def element(tag: str, attributes: dict[str, Any], text: str | None = None) -> ET.Element:
        node = ET.SubElement(root, f"{{{SVG_NAMESPACE}}}{tag}", {key: str(value) for key, value in attributes.items()})
        node.text = text
        return node

    def text(x: int, y: int, value: str, size: int, color: str, bold: bool = False) -> None:
        element("text", {"x": x, "y": y, "fill": color, "font-size": size,
                         "font-weight": "700" if bold else "400"}, value)

    element("title", {"id": "card-title"}, "Lucky Roomber community statistics")
    pending = stats["status"] == "awaiting-data"
    description = "Awaiting first report. No statistics have been published yet."
    if not pending:
        description = (f"{stats['deaths']} recorded deaths; {stats['completedRuns']} completed runs; "
                       f"{stats['runs']} recorded runs. Report updated {stats['updatedAt']}.")
    element("desc", {"id": "card-description"}, description)
    element("rect", {"width": WIDTH, "height": HEIGHT, "fill": BACKGROUND})
    element("rect", {"width": WIDTH, "height": 7, "fill": ACCENT})
    text(58, 69, "LUCKY ROOMBER  /  COMMUNITY RECORDS", 23, ACCENT)
    text(58, 145, "THE BUILDING REMEMBERS.", 54, INK, True)
    text(58, 195, "Not everyone finds their lucky room.", 29, MUTED)
    count = lambda value: "-" if value is None else f"{value:,}"
    rate = stats["escapeRatePercent"]
    entries = (
        ("RECORDED DEATHS", count(stats["deaths"]), "Runs ending in death", RED),
        ("COMPLETED RUNS", count(stats["completedRuns"]), "Confirmed completions", INK),
        ("ESCAPE RATE", "-" if rate is None else f"{rate:.1f}%", "Among death/completion outcomes", ACCENT),
        ("RECORDED RUNS", count(stats["runs"]), "Not unique players", INK),
    )
    for index, (label, value, caption, color) in enumerate(entries):
        x = 58 + (index % 2) * 474
        y = 232 + (index // 2) * 222
        element("rect", {"x": x, "y": y, "width": 450, "height": 200, "rx": 14,
                         "fill": PANEL, "stroke": BORDER, "stroke-width": 2})
        text(x + 25, y + 43, label, 26, MUTED)
        text(x + 23, y + 137, value, min(90, int(390 / (0.68 * max(len(value), 1)))), color, True)
        text(x + 25, y + 180, caption, 23, MUTED)
    element("line", {"x1": 58, "y1": 688, "x2": 982, "y2": 688, "stroke": BORDER, "stroke-width": 2})
    if pending:
        text(58, 742, "AWAITING FIRST REPORT", 29, ACCENT, True)
        text(58, 784, "No statistics have been published yet.", 26, MUTED)
    else:
        updated = stats["updatedAt"].replace("T", " ").replace("Z", " UTC")
        text(58, 742, f"REPORT UPDATED  {updated}", 25, ACCENT)
        window = "No recorded runs in this report."
        if stats["windowStart"] is not None:
            window = f"Available data: {stats['windowStart']} to {stats['windowEnd']}"
        text(58, 784, window, 26, MUTED)
    text(58, 841, "Analytics-enabled runs only. Not a live counter.", 26, MUTED)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".stats-")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def serialize(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def build(source: Path, output: Path, submitted_json: str = "") -> dict[str, Any]:
    snapshot = read_snapshot(source)
    if submitted_json.strip():
        incoming = parse_snapshot(submitted_json.encode("utf-8"))
        check_replacement(snapshot, incoming)
        snapshot = incoming
    stats = public_stats(snapshot)
    svg = render_card(stats)
    atomic_write(output / "stats.svg", svg)
    atomic_write(output / "stats.json", serialize(stats))
    if submitted_json.strip():
        atomic_write(source, serialize(snapshot))
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the public Lucky Roomber SVG from aggregate counters only.")
    parser.add_argument("--input", type=Path, default=ROOT / "snapshot.json")
    parser.add_argument("--output", type=Path, default=ROOT / "public")
    parser.add_argument("--input-env", help="Name of an environment variable containing an optional replacement JSON report.")
    arguments = parser.parse_args()
    try:
        submitted = "" if arguments.input_env is None else os.environ.get(arguments.input_env, "")
        result = build(arguments.input, arguments.output, submitted)
    except (OSError, ValueError, UnicodeError, RecursionError):
        parser.exit(1, "Invalid, stale or unavailable aggregate report. Check the schema and timestamp; never submit raw events or secrets.\n")
    print(f"Statistics SVG built successfully ({result['status']}).")


if __name__ == "__main__":
    main()
