import base64
import gzip
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
CONSUMER_PATH = ROOT / "lambdas" / "consumer" / "handler.py"


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_record(payload: dict, sequence_number: str = "seq-1") -> dict:
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    return {
        "eventID": f"event-{sequence_number}",
        "kinesis": {
            "data": encoded,
            "sequenceNumber": sequence_number,
            "partitionKey": payload.get("member_id", "M000001"),
        },
    }


def test_consumer_writes_gzipped_json_lines_and_reports_failures():
    os.environ["BUCKET_NAME"] = "demo-bucket"
    consumer = load_module("consumer_handler", CONSUMER_PATH)
    s3_client = Mock()

    good_payload = {
        "event_id": "evt-1",
        "event_type": "POINTS_EARNED",
        "member_id": "M000001",
        "partner_id": "ACCOR",
        "points": 100,
    }
    bad_record = {
        "eventID": "event-bad",
        "kinesis": {
            "data": "not-base64",
            "sequenceNumber": "seq-bad",
            "partitionKey": "M000999",
        },
    }
    event = {"Records": [make_record(good_payload), bad_record]}
    context = SimpleNamespace(aws_request_id="req-123")

    with patch.object(consumer, "_s3_client", return_value=s3_client):
        response = consumer.lambda_handler(event, context)

    assert response == {"batchItemFailures": [{"itemIdentifier": "seq-bad"}]}
    s3_client.put_object.assert_called_once()

    put_kwargs = s3_client.put_object.call_args.kwargs
    assert put_kwargs["Bucket"] == "demo-bucket"
    assert put_kwargs["ContentEncoding"] == "gzip"

    decoded_body = gzip.decompress(put_kwargs["Body"]).decode("utf-8")
    written_record = json.loads(decoded_body.strip())
    assert written_record["event_id"] == "evt-1"
    assert written_record["_kinesis_sequence_number"] == "seq-1"
