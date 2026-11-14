import argparse
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FIELDS = frozenset({"schemaVersion", "updatedAt", "windowStart", "windowEnd", "runs", "deaths", "completedRuns"})
COUNT_FIELDS = ("runs", "deaths", "completedRuns")
MAX_COUNT = 9_007_199_254_740_991
MAX_INPUT_BYTES = 8192
WIDTH, HEIGHT = 1040, 900
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
        raise ValueError("Use only the exact aggregate fields produced by export-public-stats.sql.")
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


def read_snapshot(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Snapshot is too large. Never upload raw events or player data.")
    return normalize_snapshot(json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object))


def public_stats(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = normalize_snapshot(snapshot)
    pending = result["runs"] is None
    finished = 0 if pending else result["deaths"] + result["completedRuns"]
    result["status"] = "awaiting-data" if pending else "published"
    result["escapeRatePercent"] = None if finished == 0 else round(100 * result["completedRuns"] / finished, 2)
    result["scope"] = "available_analytics_data"
    return result


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=size)


def fit_font(draw: ImageDraw.ImageDraw, text: str, size: int, max_width: int) -> ImageFont.FreeTypeFont:
    selected = font(size)
    while draw.textlength(text, font=selected) > max_width and size > 12:
        size -= 1
        selected = font(size)
    return selected


def render_card(stats: dict[str, Any]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 7), fill=ACCENT)
    draw.text((58, 43), "LUCKY ROOMBER  /  COMMUNITY RECORDS", fill=ACCENT, font=font(23))
    heading = "THE BUILDING REMEMBERS."
    draw.text((58, 96), heading, fill=INK, font=fit_font(draw, heading, 57, 924))
    draw.text((58, 168), "Not everyone finds their lucky room.", fill=MUTED, font=font(29))
    pending = stats["status"] == "awaiting-data"
    count = lambda value: "-" if value is None else f"{value:,}"
    rate = stats["escapeRatePercent"]
    rate_text = "-" if rate is None else f"{rate:.1f}%"
    entries = (
        ("RECORDED DEATHS", count(stats["deaths"]), "Runs ending in death", RED),
        ("COMPLETED RUNS", count(stats["completedRuns"]), "Confirmed completions", INK),
        ("ESCAPE RATE", rate_text, "Among death/completion outcomes", ACCENT),
        ("RECORDED RUNS", count(stats["runs"]), "Not unique players", INK),
    )
    for index, (label, value, caption, color) in enumerate(entries):
        x = 58 + (index % 2) * 474
        y = 232 + (index // 2) * 222
        draw.rounded_rectangle((x, y, x + 450, y + 200), radius=14, fill=PANEL, outline=BORDER, width=2)
        draw.text((x + 25, y + 20), label, fill=MUTED, font=fit_font(draw, label, 28, 400))
        draw.text((x + 23, y + 53), value, fill=color, font=fit_font(draw, value, 96, 402))
        draw.text((x + 25, y + 162), caption, fill=MUTED, font=fit_font(draw, caption, 24, 400))
    draw.line((58, 688, 982, 688), fill=BORDER, width=2)
    if pending:
        draw.text((58, 714), "AWAITING FIRST REPORT", fill=ACCENT, font=font(29))
        draw.text((58, 757), "No statistics have been published yet.", fill=MUTED, font=font(26))
    else:
        updated = stats["updatedAt"].replace("T", " ").replace("Z", " UTC")
        draw.text((58, 714), f"REPORT UPDATED  {updated}", fill=ACCENT, font=font(25))
        window = "No recorded runs in this report."
        if stats["windowStart"] is not None:
            window = f"Available data: {stats['windowStart']} to {stats['windowEnd']}"
        draw.text((58, 757), window, fill=MUTED, font=font(26))
    draw.text((58, 811), "Analytics-enabled runs only. Not a live counter.", fill=MUTED, font=font(26))
    return image


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


def build(source: Path, output: Path) -> dict[str, Any]:
    from io import BytesIO

    stats = public_stats(read_snapshot(source))
    serialized = (json.dumps(stats, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    buffer = BytesIO()
    render_card(stats).save(buffer, format="PNG", optimize=True)
    atomic_write(output / "stats.json", serialized)
    atomic_write(output / "stats.png", buffer.getvalue())
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the public Lucky Roomber card from aggregate counters only.")
    parser.add_argument("--input", type=Path, default=ROOT / "snapshot.json")
    parser.add_argument("--output", type=Path, default=ROOT / "public")
    arguments = parser.parse_args()
    try:
        result = build(arguments.input, arguments.output)
    except (OSError, ValueError, UnicodeError):
        parser.exit(1, "Invalid aggregate snapshot or unavailable input/output. Check the documented schema; do not paste raw events.\n")
    print(f"Statistics card built successfully ({result['status']}).")


if __name__ == "__main__":
    main()
