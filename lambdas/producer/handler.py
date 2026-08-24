import base64
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3

REQUIRED_FIELDS = {
    "event_type",
    "member_id",
    "points",
    "partner_id",
}


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _kinesis_client():
    return boto3.client("kinesis")


def _load_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body", event)
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    if isinstance(body, str):
        body = json.loads(body)
    if not isinstance(body, dict):
        raise TypeError("Request body must decode to a JSON object")
    return body


def _enrich_event(body: dict[str, Any]) -> dict[str, Any]:
    body = dict(body)
    body.setdefault("event_id", str(uuid.uuid4()))
    body.setdefault("transaction_id", f"T-{uuid.uuid4().hex[:12]}")
    body.setdefault("trace_id", str(uuid.uuid4()))
    body.setdefault("event_version", "1.0")
    body.setdefault(
        "event_timestamp",
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    body.setdefault("source_system", "LOYALTY_SIMULATOR")
    body.setdefault("attributes", {})
    return body


def lambda_handler(event, context):
    try:
        body = _load_body(event)
        missing = sorted(REQUIRED_FIELDS - body.keys())
        if missing:
            return _response(400, {"error": "Missing fields", "fields": missing})

        payload = _enrich_event(body)
        stream_name = os.environ["STREAM_NAME"]
        result = _kinesis_client().put_record(
            StreamName=stream_name,
            Data=(json.dumps(payload) + "\n").encode("utf-8"),
            PartitionKey=str(payload["member_id"]),
        )

        return _response(
            202,
            {
                "accepted": True,
                "event_id": payload["event_id"],
                "shard_id": result["ShardId"],
                "sequence_number": result["SequenceNumber"],
            },
        )
    except json.JSONDecodeError:
        return _response(400, {"error": "Request body is not valid JSON"})
    except (TypeError, ValueError) as exc:
        return _response(400, {"error": str(exc)})
    except Exception as exc:
        print(json.dumps({"level": "ERROR", "message": str(exc)}))
        return _response(500, {"error": "Internal processing error"})
