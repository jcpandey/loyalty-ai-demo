import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SIMULATOR_PATH = ROOT / "simulator" / "generate_events.py"


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_event_contains_required_fields():
    simulator = load_module("generate_events", SIMULATOR_PATH)
    event = simulator.build_event()

    required_fields = {
        "event_id",
        "event_type",
        "event_version",
        "event_timestamp",
        "member_id",
        "partner_id",
        "transaction_id",
        "points",
        "amount_aud",
        "channel",
        "source_system",
        "trace_id",
        "attributes",
    }

    assert required_fields.issubset(event.keys())
    assert event["event_timestamp"].endswith("Z")
    assert event["member_id"].startswith("M")


def test_points_redeemed_events_are_negative():
    simulator = load_module("generate_events_redeemed", SIMULATOR_PATH)

    with patch.object(simulator.random, "choices", return_value=["POINTS_REDEEMED"]):
        event = simulator.build_event()

    assert event["event_type"] == "POINTS_REDEEMED"
    assert event["points"] < 0


def test_ssl_verification_can_be_disabled_by_flag_or_env():
    simulator = load_module("generate_events_ssl", SIMULATOR_PATH)

    args = simulator.parse_args.__globals__["argparse"].Namespace(no_verify_ssl=True)
    assert simulator.ssl_verification_enabled(args) is False

    args = simulator.parse_args.__globals__["argparse"].Namespace(no_verify_ssl=False)
    with patch.dict(os.environ, {"AWS_VERIFY_SSL": "false"}, clear=False):
        assert simulator.ssl_verification_enabled(args) is False

    with patch.dict(os.environ, {"AWS_VERIFY_SSL": "true"}, clear=False):
        assert simulator.ssl_verification_enabled(args) is True
