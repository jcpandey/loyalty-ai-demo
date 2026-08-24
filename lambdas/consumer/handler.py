import base64
import gzip
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3


def _s3_client():
    return boto3.client("s3")


def _bucket_name() -> str:
    return os.environ["BUCKET_NAME"]


def _landing_prefix() -> str:
    return os.getenv("LANDING_PREFIX", "landing/events")


def _decode_record(record: dict[str, Any]) -> dict[str, Any]:
    raw = base64.b64decode(record["kinesis"]["data"]).decode("utf-8")
    payload = json.loads(raw)
    payload["_kinesis_sequence_number"] = record["kinesis"]["sequenceNumber"]
    payload["_kinesis_partition_key"] = record["kinesis"]["partitionKey"]
    payload["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    return payload


def _batch_key(request_id: str, now: datetime) -> str:
    return (
        f"{_landing_prefix()}/year={now:%Y}/month={now:%m}/day={now:%d}/"
        f"hour={now:%H}/batch-{request_id}-{uuid.uuid4().hex}.jsonl.gz"
    )


def lambda_handler(event, context):
    valid_records: list[dict[str, Any]] = []
    failed_identifiers: list[str] = []

    for record in event.get("Records", []):
        try:
            valid_records.append(_decode_record(record))
        except Exception as exc:
            sequence_number = record.get("kinesis", {}).get("sequenceNumber", "unknown")
            failed_identifiers.append(sequence_number)
            print(
                json.dumps(
                    {
                        "level": "ERROR",
                        "item_identifier": sequence_number,
                        "message": str(exc),
                    }
                )
            )

    if valid_records:
        now = datetime.now(timezone.utc)
        key = _batch_key(context.aws_request_id, now)
        json_lines = "\n".join(json.dumps(item) for item in valid_records) + "\n"

        _s3_client().put_object(
            Bucket=_bucket_name(),
            Key=key,
            Body=gzip.compress(json_lines.encode("utf-8")),
            ContentType="application/x-ndjson",
            ContentEncoding="gzip",
            ServerSideEncryption="AES256",
            Metadata={"record-count": str(len(valid_records))},
        )

        print(
            json.dumps(
                {
                    "level": "INFO",
                    "s3_key": key,
                    "record_count": len(valid_records),
                }
            )
        )

    return {
        "batchItemFailures": [
            {"itemIdentifier": item_identifier}
            for item_identifier in failed_identifiers
        ]
    }
