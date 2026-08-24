import argparse
import json
import os
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
import requests

PARTNERS = ["ACCOR", "MASTERCARD", "TRAVLR", "RETAIL_CO", "AIRLINE_CO"]
EVENT_TYPES = ["POINTS_EARNED", "POINTS_REDEEMED", "POINTS_ADJUSTED"]
CHANNELS = ["MOBILE_APP", "WEB", "PARTNER_BATCH", "CONTACT_CENTRE"]


def build_event() -> dict:
    event_type = random.choices(EVENT_TYPES, weights=[0.72, 0.23, 0.05], k=1)[0]
    points = random.randint(10, 2500)
    if event_type == "POINTS_REDEEMED":
        points *= -1
    elif event_type == "POINTS_ADJUSTED":
        points *= random.choice([-1, 1])

    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_version": "1.0",
        "event_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "member_id": f"M{random.randint(1, 10000):06d}",
        "partner_id": random.choice(PARTNERS),
        "transaction_id": f"T-{uuid.uuid4().hex[:12]}",
        "points": points,
        "amount_aud": round(random.uniform(2.0, 500.0), 2),
        "channel": random.choice(CHANNELS),
        "source_system": "LOYALTY_SIMULATOR",
        "trace_id": str(uuid.uuid4()),
        "attributes": {
            "campaign_id": random.choice([None, "WELCOME_BONUS", "WINTER_BONUS"]),
        },
    }


def ssl_verification_enabled(args: argparse.Namespace) -> bool:
    if args.no_verify_ssl:
        return False
    env_value = os.getenv("AWS_VERIFY_SSL", "true").strip().lower()
    return env_value not in {"0", "false", "no"}


def send_to_api(event: dict[str, Any], api_url: str, verify: bool) -> None:
    response = requests.post(api_url, json=event, timeout=10, verify=verify)
    response.raise_for_status()
    print(response.status_code, response.json())


def send_to_kinesis(
    event: dict[str, Any],
    stream_name: str,
    region: str,
    verify: bool,
) -> None:
    client = boto3.client("kinesis", region_name=region, verify=verify)
    response = client.put_record(
        StreamName=stream_name,
        Data=(json.dumps(event) + "\n").encode("utf-8"),
        PartitionKey=event["member_id"],
    )
    print(event["event_id"], response["ShardId"], response["SequenceNumber"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic loyalty events.")
    parser.add_argument("--mode", choices=["api", "kinesis"], default="api")
    parser.add_argument("--rate", type=float, default=2.0, help="Events per second")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable TLS certificate verification for local lab use only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.rate <= 0:
        raise ValueError("--rate must be greater than zero")
    if args.count < 0:
        raise ValueError("--count must be zero or greater")

    api_url = os.getenv("LOYALTY_API_URL")
    stream_name = os.getenv("STREAM_NAME")
    region = os.getenv("AWS_REGION", "ap-southeast-2")
    verify = ssl_verification_enabled(args)

    for _ in range(args.count):
        event = build_event()
        if args.mode == "api":
            if not api_url:
                raise RuntimeError("Set LOYALTY_API_URL")
            send_to_api(event, api_url, verify)
        else:
            if not stream_name:
                raise RuntimeError("Set STREAM_NAME")
            send_to_kinesis(event, stream_name, region, verify)
        time.sleep(1 / args.rate)


if __name__ == "__main__":
    main()
