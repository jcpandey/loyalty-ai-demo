import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from databricks import sql
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


class DatabricksQueryError(RuntimeError):
    pass


@dataclass(frozen=True)
class QuerySpec:
    statement: str
    parameters: tuple[str, ...] = ()
    description: str = ""


class DatabricksRetriever:
    def __init__(
        self,
        server_hostname: str,
        http_path: str,
        access_token: str,
        socket_timeout: float = 30.0,
        retry_attempts: int = 1,
        tls_no_verify: bool = False,
        tls_trusted_ca_file: str | None = None,
    ):
        self.server_hostname = server_hostname
        self.http_path = http_path
        self.access_token = access_token
        self.socket_timeout = socket_timeout
        self.retry_attempts = retry_attempts
        self.tls_no_verify = tls_no_verify
        self.tls_trusted_ca_file = tls_trusted_ca_file

    @classmethod
    def from_env(cls) -> "DatabricksRetriever | None":
        server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        http_path = os.getenv("DATABRICKS_HTTP_PATH")
        access_token = os.getenv("DATABRICKS_TOKEN")
        socket_timeout = float(os.getenv("DATABRICKS_SQL_SOCKET_TIMEOUT", "30"))
        retry_attempts = int(os.getenv("DATABRICKS_SQL_RETRY_ATTEMPTS", "1"))
        tls_no_verify = os.getenv("DATABRICKS_SQL_TLS_NO_VERIFY", "false").lower() in {
            "1",
            "true",
            "yes",
        }
        tls_trusted_ca_file = os.getenv("DATABRICKS_SQL_TRUSTED_CA_FILE") or None
        if not server_hostname or not http_path or not access_token:
            return None
        if "replace_me" in {server_hostname, http_path, access_token}:
            return None
        return cls(
            server_hostname=server_hostname,
            http_path=http_path,
            access_token=access_token,
            socket_timeout=socket_timeout,
            retry_attempts=retry_attempts,
            tls_no_verify=tls_no_verify,
            tls_trusted_ca_file=tls_trusted_ca_file,
        )

    def retrieve(self, question: str) -> str | None:
        query = self._build_query(question)
        if query is None:
            return None
        rows = self._run_query(query)
        return self._format_result(query.description, rows)

    def _build_query(self, question: str) -> QuerySpec | None:
        normalized = question.lower()
        member_match = re.search(r"\bM\d{3,}\b", question, re.IGNORECASE)
        partner_match = re.search(r"\b[A-Z]{3,}\b", question)
        date_range = self._parse_date_range(question)
        day_filter = self._parse_relative_day_filter(normalized)

        if any(term in normalized for term in ("top partner", "top partners", "highest partner", "highest points")):
            return self._build_top_partners_query(date_range, day_filter)

        if member_match and "balance" in normalized:
            return QuerySpec(
                statement=(
                    "SELECT member_id, current_points_balance, last_activity_timestamp "
                    "FROM loyalty_demo.gold.member_balance "
                    "WHERE member_id = ?"
                ),
                parameters=(member_match.group(0).upper(),),
                description="member balance",
            )

        if member_match and any(
            term in normalized for term in ("history", "transactions", "activity", "events")
        ):
            return QuerySpec(
                statement=(
                    "SELECT event_ts, event_type, partner_id, transaction_id, points, amount_aud, channel "
                    "FROM loyalty_demo.silver.loyalty_events "
                    "WHERE member_id = ? "
                    "ORDER BY event_ts DESC "
                    "LIMIT 10"
                ),
                parameters=(member_match.group(0).upper(),),
                description="member transaction history",
            )

        if any(term in normalized for term in ("quarantine", "invalid", "failed validation")):
            return QuerySpec(
                statement=(
                    "SELECT COUNT(*) AS quarantine_count "
                    "FROM loyalty_demo.silver.loyalty_events_quarantine"
                ),
                description="quarantine count",
            )

        if any(term in normalized for term in ("latest", "recent", "freshness", "delay")):
            return QuerySpec(
                statement=(
                    "SELECT MAX(event_ts) AS latest_event_timestamp, "
                    "timestampdiff(MINUTE, MAX(event_ts), current_timestamp()) AS delay_minutes "
                    "FROM loyalty_demo.silver.loyalty_events"
                ),
                description="event freshness",
            )

        if any(term in normalized for term in ("hourly", "per hour", "by hour")):
            return self._build_hourly_metrics_query(partner_match, normalized)

        if date_range and any(
            term in normalized for term in ("summary", "summarise", "summarize", "between", "from")
        ):
            return QuerySpec(
                statement=(
                    "SELECT MIN(event_date) AS start_date, MAX(event_date) AS end_date, "
                    "COUNT(*) AS event_count, COUNT(DISTINCT member_id) AS distinct_members, "
                    "SUM(points) AS net_points, SUM(amount_aud) AS total_amount_aud "
                    "FROM loyalty_demo.silver.loyalty_events "
                    "WHERE event_date BETWEEN ? AND ?"
                ),
                parameters=date_range,
                description=f"date-range summary from {date_range[0]} to {date_range[1]}",
            )

        if partner_match and any(term in normalized for term in ("partner", "points", "transactions")):
            return self._build_partner_summary_query(partner_match.group(0).upper(), date_range, day_filter)

        return None

    def _build_top_partners_query(
        self, date_range: tuple[str, str] | None, day_filter: str | None
    ) -> QuerySpec:
        if date_range:
            return QuerySpec(
                statement=(
                    "SELECT partner_id, SUM(net_points) AS net_points, SUM(transaction_count) AS transaction_count, "
                    "SUM(transaction_value_aud) AS transaction_value_aud "
                    "FROM loyalty_demo.gold.daily_partner_points "
                    "WHERE event_date BETWEEN ? AND ? "
                    "GROUP BY partner_id "
                    "ORDER BY net_points DESC "
                    "LIMIT 10"
                ),
                parameters=date_range,
                description=f"top partners from {date_range[0]} to {date_range[1]}",
            )
        if day_filter:
            return QuerySpec(
                statement=(
                    "SELECT partner_id, net_points, transaction_count, transaction_value_aud "
                    "FROM loyalty_demo.gold.daily_partner_points "
                    f"WHERE event_date = {day_filter} "
                    "ORDER BY net_points DESC "
                    "LIMIT 10"
                ),
                description="top partners for relative day",
            )
        return QuerySpec(
            statement=(
                "WITH latest_day AS (SELECT MAX(event_date) AS event_date FROM loyalty_demo.gold.daily_partner_points) "
                "SELECT d.partner_id, d.net_points, d.transaction_count, d.transaction_value_aud "
                "FROM loyalty_demo.gold.daily_partner_points d "
                "INNER JOIN latest_day l ON d.event_date = l.event_date "
                "ORDER BY d.net_points DESC "
                "LIMIT 10"
            ),
            description="top partners for latest available date",
        )

    def _build_partner_summary_query(
        self,
        partner_id: str,
        date_range: tuple[str, str] | None,
        day_filter: str | None,
    ) -> QuerySpec:
        if date_range:
            return QuerySpec(
                statement=(
                    "SELECT event_date, partner_id, points_earned, points_redeemed, net_points, "
                    "transaction_count, active_members, transaction_value_aud "
                    "FROM loyalty_demo.gold.daily_partner_points "
                    "WHERE partner_id = ? AND event_date BETWEEN ? AND ? "
                    "ORDER BY event_date DESC "
                    "LIMIT 31"
                ),
                parameters=(partner_id, date_range[0], date_range[1]),
                description=f"daily partner points for {partner_id} from {date_range[0]} to {date_range[1]}",
            )
        if day_filter:
            return QuerySpec(
                statement=(
                    "SELECT event_date, partner_id, points_earned, points_redeemed, net_points, "
                    "transaction_count, active_members, transaction_value_aud "
                    "FROM loyalty_demo.gold.daily_partner_points "
                    f"WHERE partner_id = ? AND event_date = {day_filter} "
                    "ORDER BY event_date DESC "
                    "LIMIT 7"
                ),
                parameters=(partner_id,),
                description=f"daily partner points for {partner_id} on relative day",
            )
        return QuerySpec(
            statement=(
                "SELECT event_date, partner_id, points_earned, points_redeemed, net_points, "
                "transaction_count, active_members, transaction_value_aud "
                "FROM loyalty_demo.gold.daily_partner_points "
                "WHERE partner_id = ? "
                "ORDER BY event_date DESC "
                "LIMIT 7"
            ),
            parameters=(partner_id,),
            description="daily partner points",
        )

    def _build_hourly_metrics_query(
        self, partner_match: re.Match[str] | None, normalized: str
    ) -> QuerySpec:
        if partner_match:
            return QuerySpec(
                statement=(
                    "SELECT event_hour, event_type, partner_id, event_count, total_points, average_value_aud "
                    "FROM loyalty_demo.gold.hourly_event_metrics "
                    "WHERE partner_id = ? "
                    "ORDER BY event_hour DESC "
                    "LIMIT 24"
                ),
                parameters=(partner_match.group(0).upper(),),
                description="hourly event metrics for partner",
            )

        event_type = self._parse_event_type(normalized)
        if event_type:
            return QuerySpec(
                statement=(
                    "SELECT event_hour, event_type, partner_id, event_count, total_points, average_value_aud "
                    "FROM loyalty_demo.gold.hourly_event_metrics "
                    "WHERE event_type = ? "
                    "ORDER BY event_hour DESC "
                    "LIMIT 24"
                ),
                parameters=(event_type,),
                description=f"hourly event metrics for {event_type}",
            )

        return QuerySpec(
            statement=(
                "SELECT event_hour, event_type, partner_id, event_count, total_points, average_value_aud "
                "FROM loyalty_demo.gold.hourly_event_metrics "
                "ORDER BY event_hour DESC "
                "LIMIT 24"
            ),
            description="latest hourly event metrics",
        )

    def _parse_date_range(self, question: str) -> tuple[str, str] | None:
        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", question)
        if len(dates) >= 2:
            return dates[0], dates[1]
        return None

    def _parse_relative_day_filter(self, normalized: str) -> str | None:
        if "today" in normalized:
            return "current_date()"
        if "yesterday" in normalized:
            return "date_sub(current_date(), 1)"
        return None

    def _parse_event_type(self, normalized: str) -> str | None:
        if "earned" in normalized or "earn" in normalized:
            return "POINTS_EARNED"
        if "redeemed" in normalized or "redeem" in normalized:
            return "POINTS_REDEEMED"
        if "adjusted" in normalized or "adjust" in normalized:
            return "POINTS_ADJUSTED"
        return None

    def _run_query(self, query: QuerySpec) -> list[dict[str, object]]:
        try:
            with sql.connect(
                server_hostname=self.server_hostname,
                http_path=self.http_path,
                access_token=self.access_token,
                _socket_timeout=self.socket_timeout,
                _retry_stop_after_attempts_count=self.retry_attempts,
                _tls_no_verify=self.tls_no_verify,
                _tls_trusted_ca_file=self.tls_trusted_ca_file,
                use_cloud_fetch=False,
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query.statement, query.parameters)
                    columns = [column[0] for column in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as exc:
            message = str(exc)
            if "CERTIFICATE_VERIFY_FAILED" in message or "CA cert" in message:
                message = (
                    f"{message}. Configure DATABRICKS_SQL_TRUSTED_CA_FILE with your corporate CA bundle, "
                    "or temporarily set DATABRICKS_SQL_TLS_NO_VERIFY=true for connectivity testing."
                )
            raise DatabricksQueryError(message) from exc

    def _format_result(self, description: str, rows: list[dict[str, object]]) -> str:
        if not rows:
            return f"Databricks SQL returned no rows for {description}."

        lines = [f"Databricks SQL result for {description}:"]
        for row in rows[:10]:
            formatted = ", ".join(f"{key}={value}" for key, value in row.items())
            lines.append(f"- {formatted}")
        return "\n".join(lines)


def main() -> None:
    question = " ".join(sys.argv[1:]).strip() or "What is the latest data freshness?"
    retriever = DatabricksRetriever.from_env()
    if retriever is None:
        raise SystemExit("Databricks connection values are missing from .env")

    print(
        (
            f"Connecting to Databricks SQL at {retriever.server_hostname} "
            f"with socket timeout {retriever.socket_timeout}s, retries {retriever.retry_attempts}, "
            f"tls_no_verify={retriever.tls_no_verify}..."
        ),
        flush=True,
    )
    result = retriever.retrieve(question)
    if result is None:
        print("No Databricks SQL route matched that question.")
        return
    print(result)


if __name__ == "__main__":
    main()