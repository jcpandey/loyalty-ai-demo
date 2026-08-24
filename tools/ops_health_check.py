from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning


BASE_DIR = Path(__file__).resolve().parent.parent
RAG_DIR = BASE_DIR / "rag"

if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from databricks_retriever import DatabricksRetriever, QuerySpec  # noqa: E402


@dataclass(frozen=True)
class Thresholds:
    max_silver_delay_minutes: int
    max_quarantine_count: int


def format_row(status: str, label: str, row: dict[str, object], message: str | None = None) -> None:
    formatted = ", ".join(f"{key}={value}" for key, value in row.items())
    suffix = f" | {message}" if message else ""
    print(f"[{status}] {label}: {formatted}{suffix}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run operational health checks for the loyalty POC.")
    parser.add_argument(
        "--max-silver-delay-minutes",
        type=int,
        default=int(os.getenv("OPS_MAX_SILVER_DELAY_MINUTES", "10080")),
        help="Fail when Silver data delay exceeds this many minutes. Default: %(default)s",
    )
    parser.add_argument(
        "--max-quarantine-count",
        type=int,
        default=int(os.getenv("OPS_MAX_QUARANTINE_COUNT", "10")),
        help="Fail when quarantine row count exceeds this value. Default: %(default)s",
    )
    return parser.parse_args()


def parse_timestamp(raw_value: object) -> datetime | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, datetime):
        return raw_value
    text = str(raw_value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def parse_date(raw_value: object) -> date | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, date) and not isinstance(raw_value, datetime):
        return raw_value
    text = str(raw_value).strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def evaluate_silver_freshness(row: dict[str, object], thresholds: Thresholds) -> tuple[str, str]:
    delay_value = row.get("silver_delay_minutes")
    if delay_value is None:
        return "FAIL", "silver delay is missing"
    delay_minutes = int(delay_value)
    if delay_minutes > thresholds.max_silver_delay_minutes:
        return "FAIL", f"delay {delay_minutes}m exceeds threshold {thresholds.max_silver_delay_minutes}m"
    return "OK", f"delay {delay_minutes}m within threshold {thresholds.max_silver_delay_minutes}m"


def evaluate_quarantine(row: dict[str, object], thresholds: Thresholds) -> tuple[str, str]:
    count_value = row.get("quarantine_count")
    if count_value is None:
        return "FAIL", "quarantine count is missing"
    quarantine_count = int(count_value)
    if quarantine_count > thresholds.max_quarantine_count:
        return "FAIL", f"count {quarantine_count} exceeds threshold {thresholds.max_quarantine_count}"
    return "OK", f"count {quarantine_count} within threshold {thresholds.max_quarantine_count}"


def evaluate_latest_data_movement(row: dict[str, object]) -> tuple[str, str]:
    silver_ts = parse_timestamp(row.get("latest_silver_event_ts"))
    gold_hour = parse_timestamp(row.get("latest_gold_event_hour"))
    gold_date = parse_date(row.get("latest_gold_event_date"))

    if silver_ts is None:
        return "FAIL", "latest Silver timestamp is missing"
    if gold_hour is None and gold_date is None:
        return "FAIL", "Gold movement timestamps are missing"

    message_parts: list[str] = ["Silver and Gold timestamps are present"]
    if gold_hour is not None:
        message_parts.append(f"latest gold hour={gold_hour}")
    if gold_date is not None:
        message_parts.append(f"latest gold date={gold_date}")
    return "OK", "; ".join(message_parts)


def main() -> int:
    args = parse_args()
    thresholds = Thresholds(
        max_silver_delay_minutes=args.max_silver_delay_minutes,
        max_quarantine_count=args.max_quarantine_count,
    )

    retriever = DatabricksRetriever.from_env()
    if retriever is None:
        print("[FAIL] Databricks connection values are missing from .env")
        return 1

    if retriever.tls_no_verify:
        disable_warnings(InsecureRequestWarning)

    checks = [
        (
            "silver freshness",
            QuerySpec(
                statement=(
                    "SELECT MAX(event_ts) AS latest_silver_event_ts, "
                    "timestampdiff(MINUTE, MAX(event_ts), current_timestamp()) AS silver_delay_minutes "
                    "FROM loyalty_demo.silver.loyalty_events"
                ),
                description="silver freshness",
            ),
            lambda row: evaluate_silver_freshness(row, thresholds),
        ),
        (
            "quarantine count",
            QuerySpec(
                statement=(
                    "SELECT COUNT(*) AS quarantine_count "
                    "FROM loyalty_demo.silver.loyalty_events_quarantine"
                ),
                description="quarantine count",
            ),
            lambda row: evaluate_quarantine(row, thresholds),
        ),
        (
            "latest data movement",
            QuerySpec(
                statement=(
                    "SELECT "
                    "(SELECT MAX(event_ts) FROM loyalty_demo.silver.loyalty_events) AS latest_silver_event_ts, "
                    "(SELECT MAX(event_hour) FROM loyalty_demo.gold.hourly_event_metrics) AS latest_gold_event_hour, "
                    "(SELECT MAX(event_date) FROM loyalty_demo.gold.daily_partner_points) AS latest_gold_event_date"
                ),
                description="latest data movement",
            ),
            evaluate_latest_data_movement,
        ),
    ]

    failures = 0
    for label, query, evaluator in checks:
        try:
            rows = retriever._run_query(query)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"[FAIL] {label}: {exc}")
            continue

        if not rows:
            failures += 1
            print(f"[FAIL] {label}: no rows returned")
            continue

        status, message = evaluator(rows[0])
        if status == "FAIL":
            failures += 1
        format_row(status, label, rows[0], message)

    if failures:
        print(f"Summary: {len(checks) - failures} passed, {failures} failed")
        return 1

    print("Summary: 3 passed, 0 failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())