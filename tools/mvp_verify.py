from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
RAG_DIR = BASE_DIR / "rag"

if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

import assistant  # noqa: E402
import databricks_retriever  # noqa: E402


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    details: str


def excerpt(text: str, limit: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def run_check(name: str, func) -> CheckResult:
    try:
        details = func()
        return CheckResult(name=name, passed=True, details=details)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name=name, passed=False, details=str(exc))


def assert_contains(text: str, required_terms: list[str], context: str) -> str:
    normalized = text.lower()
    if not any(term.lower() in normalized for term in required_terms):
        raise AssertionError(f"Expected one of {required_terms} in {context}. Response: {excerpt(text)}")
    return excerpt(text)


def check_databricks_route(question: str, expected_terms: list[str]) -> str:
    retriever = databricks_retriever.DatabricksRetriever.from_env()
    if retriever is None:
        raise RuntimeError("Databricks connection values are missing from .env")

    result = retriever.retrieve(question)
    if result is None:
        raise AssertionError(f"No Databricks SQL route matched question: {question}")

    return assert_contains(result, expected_terms, f"Databricks result for question '{question}'")


def check_assistant_answer(question: str, required_terms: list[str], source_terms: list[str]) -> str:
    response = assistant.answer(question)
    assert_contains(response, required_terms, f"assistant response for question '{question}'")
    return assert_contains(response, source_terms, f"assistant sources for question '{question}'")


def build_checks(include_databricks: bool, include_assistant: bool) -> list[tuple[str, callable]]:
    checks: list[tuple[str, callable]] = []

    if include_databricks:
        checks.extend(
            [
                (
                    "databricks freshness",
                    lambda: check_databricks_route(
                        "What is the latest data freshness?",
                        ["latest_event_timestamp", "delay_minutes"],
                    ),
                ),
                (
                    "databricks quarantine",
                    lambda: check_databricks_route(
                        "How many records are in quarantine?",
                        ["quarantine_count"],
                    ),
                ),
                (
                    "databricks top partners",
                    lambda: check_databricks_route(
                        "Who are the top partners?",
                        ["partner_id", "net_points"],
                    ),
                ),
                (
                    "databricks member balance",
                    lambda: check_databricks_route(
                        "What is the balance for member M000123?",
                        ["member_id", "current_points_balance"],
                    ),
                ),
            ]
        )

    if include_assistant:
        checks.extend(
            [
                (
                    "assistant event schema",
                    lambda: check_assistant_answer(
                        "What is the loyalty event schema?",
                        ["event_id", "event_timestamp", "member_id"],
                        ["event_contract", "event_contract.md"],
                    ),
                ),
                (
                    "assistant support runbook",
                    lambda: check_assistant_answer(
                        "What should I check if streaming stops?",
                        ["api gateway", "kinesis", "lambda", "s3"],
                        ["support_runbook", "support_runbook.md"],
                    ),
                ),
            ]
        )

    return checks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MVP validation checks for Databricks and the assistant.")
    parser.add_argument("--skip-databricks", action="store_true", help="Skip Databricks SQL checks.")
    parser.add_argument("--skip-assistant", action="store_true", help="Skip assistant checks.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    include_databricks = not args.skip_databricks
    include_assistant = not args.skip_assistant

    if not include_databricks and not include_assistant:
        print("No checks selected.")
        return 1

    results = [run_check(name, func) for name, func in build_checks(include_databricks, include_assistant)]

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.details}")

    failures = [result for result in results if not result.passed]
    print(f"Summary: {len(results) - len(failures)} passed, {len(failures)} failed")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())