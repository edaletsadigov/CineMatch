
from datetime import date
from decimal import Decimal
from math import isfinite
from uuid import UUID

from sqlalchemy import Engine, text


class OpsService:
    """
    Handles PostgreSQL OPS operations for CineMatch.

    Responsibilities:
    - Ingestion run tracking
    - Checkpoint management
    - Error tracking
    - API request logging
    - Ingestion metrics
    """

    def __init__(self, engine: Engine):
        self.engine = engine

    # =================================================
    # 1. INGESTION RUNS
    # =================================================

    def start_run(
        self,
        run_id: UUID | str,
        pipeline_name: str,
    ) -> None:

        if not isinstance(pipeline_name, str) or not pipeline_name.strip():
            raise ValueError("Pipeline name cannot be empty.")

        query = text("""
            INSERT INTO ops.ingestion_runs (
                run_id,
                pipeline_name
            )
            VALUES (
                :run_id,
                :pipeline_name
            )
        """)

        with self.engine.begin() as connection:
            connection.execute(
                query,
                {
                    "run_id": UUID(str(run_id)),
                    "pipeline_name": pipeline_name.strip(),
                },
            )

    def finish_run(
        self,
        run_id: UUID | str,
        status: str,
        records_processed: int,
        records_succeeded: int,
        records_failed: int,
        error_message: str | None = None,
    ) -> None:

        if status not in {"success", "failed"}:
            raise ValueError(
                "Status must be either 'success' or 'failed'."
            )

        counts = {
            "records_processed": records_processed,
            "records_succeeded": records_succeeded,
            "records_failed": records_failed,
        }

        for field, value in counts.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field} must be an integer.")

            if value < 0:
                raise ValueError(f"{field} cannot be negative.")

        if records_processed != records_succeeded + records_failed:
            raise ValueError(
                "records_processed must equal "
                "records_succeeded + records_failed."
            )

        if status == "success" and records_failed > 0:
            raise ValueError(
                "A successful run cannot contain failed records."
            )

        if status == "failed" and not error_message:
            raise ValueError(
                "A failed run must include an error message."
            )

        run_id = UUID(str(run_id))

        query = text("""
            UPDATE ops.ingestion_runs
            SET
                status = :status,
                finished_at = CURRENT_TIMESTAMP,
                records_processed = :records_processed,
                records_succeeded = :records_succeeded,
                records_failed = :records_failed,
                error_message = :error_message
            WHERE run_id = :run_id
              AND status = 'running'
        """)

        with self.engine.begin() as connection:
            result = connection.execute(
                query,
                {
                    "run_id": run_id,
                    "status": status,
                    "records_processed": records_processed,
                    "records_succeeded": records_succeeded,
                    "records_failed": records_failed,
                    "error_message": error_message,
                },
            )

            if result.rowcount != 1:
                raise ValueError(
                    f"Could not finish run {run_id}. "
                    "Run may not exist or may already be completed."
                )

    # =================================================
    # 2. INGESTION CHECKPOINTS
    # =================================================

    def update_checkpoint(
        self,
        source: str,
        media_type: str,
        export_date: date,
        last_processed_id: int,
        records_processed: int,
        run_id: UUID | str,
    ) -> None:

        if not isinstance(source, str) or not source.strip():
            raise ValueError("Source cannot be empty.")

        if media_type not in {"movie", "tv"}:
            raise ValueError("Media type must be 'movie' or 'tv'.")

        if not isinstance(export_date, date):
            raise TypeError("export_date must be a date.")

        if isinstance(last_processed_id, bool) or not isinstance(last_processed_id, int):
            raise TypeError("last_processed_id must be an integer.")

        if isinstance(records_processed, bool) or not isinstance(records_processed, int):
            raise TypeError("records_processed must be an integer.")

        if last_processed_id < 0 or records_processed < 0:
            raise ValueError("Checkpoint values cannot be negative.")

        query = text("""
            INSERT INTO ops.ingestion_checkpoints (
                source,
                media_type,
                export_date,
                last_processed_id,
                records_processed,
                last_processed_at,
                last_run_id
            )
            VALUES (
                :source,
                :media_type,
                :export_date,
                :last_processed_id,
                :records_processed,
                CURRENT_TIMESTAMP,
                :run_id
            )
            ON CONFLICT (
                source,
                media_type,
                export_date
            )
            DO UPDATE SET
                last_processed_id = EXCLUDED.last_processed_id,
                records_processed = EXCLUDED.records_processed,
                last_processed_at = CURRENT_TIMESTAMP,
                last_run_id = EXCLUDED.last_run_id,
                updated_at = CURRENT_TIMESTAMP
            WHERE
                EXCLUDED.last_processed_id >
                ops.ingestion_checkpoints.last_processed_id
        """)

        with self.engine.begin() as connection:
            connection.execute(
                query,
                {
                    "source": source.strip(),
                    "media_type": media_type,
                    "export_date": export_date,
                    "last_processed_id": last_processed_id,
                    "records_processed": records_processed,
                    "run_id": UUID(str(run_id)),
                },
            )

    # =================================================
    # 3. INGESTION ERRORS
    # =================================================

    def record_error(
        self,
        media_type: str,
        tmdb_id: int,
        error_type: str,
        error_message: str,
        run_id: UUID | str | None = None,
        http_status_code: int | None = None,
        retry_count: int = 0,
    ) -> int:

        if media_type not in {"movie", "tv"}:
            raise ValueError("Media type must be 'movie' or 'tv'.")

        if isinstance(tmdb_id, bool) or not isinstance(tmdb_id, int) or tmdb_id <= 0:
            raise ValueError("TMDB ID must be a positive integer.")

        if not error_type or not error_type.strip():
            raise ValueError("Error type cannot be empty.")

        if not error_message or not error_message.strip():
            raise ValueError("Error message cannot be empty.")

        if isinstance(retry_count, bool) or not isinstance(retry_count, int):
            raise TypeError("retry_count must be an integer.")

        if retry_count < 0:
            raise ValueError("retry_count cannot be negative.")

        if http_status_code is not None:
            if isinstance(http_status_code, bool) or not isinstance(http_status_code, int):
                raise TypeError("HTTP status code must be an integer.")

            if not 100 <= http_status_code <= 599:
                raise ValueError("Invalid HTTP status code.")

        query = text("""
            INSERT INTO ops.ingestion_errors (
                run_id,
                media_type,
                tmdb_id,
                error_type,
                error_message,
                http_status_code,
                retry_count
            )
            VALUES (
                :run_id,
                :media_type,
                :tmdb_id,
                :error_type,
                :error_message,
                :http_status_code,
                :retry_count
            )
            RETURNING error_id
        """)

        with self.engine.begin() as connection:
            result = connection.execute(
                query,
                {
                    "run_id": UUID(str(run_id)) if run_id else None,
                    "media_type": media_type,
                    "tmdb_id": tmdb_id,
                    "error_type": error_type.strip(),
                    "error_message": error_message.strip(),
                    "http_status_code": http_status_code,
                    "retry_count": retry_count,
                },
            )

            return result.scalar_one()

    def resolve_error(self, error_id: int) -> None:

        if isinstance(error_id, bool) or not isinstance(error_id, int):
            raise TypeError("error_id must be an integer.")

        if error_id <= 0:
            raise ValueError("error_id must be positive.")

        query = text("""
            UPDATE ops.ingestion_errors
            SET
                is_resolved = TRUE,
                resolved_at = CURRENT_TIMESTAMP
            WHERE error_id = :error_id
              AND is_resolved = FALSE
        """)

        with self.engine.begin() as connection:
            result = connection.execute(
                query,
                {"error_id": error_id},
            )

            if result.rowcount != 1:
                raise ValueError(
                    f"Could not resolve error {error_id}. "
                    "Error may not exist or may already be resolved."
                )

    # =================================================
    # 4. API REQUEST LOGS
    # =================================================

    def log_api_request(
        self,
        endpoint: str,
        is_success: bool,
        run_id: UUID | str | None = None,
        media_type: str | None = None,
        tmdb_id: int | None = None,
        http_status_code: int | None = None,
        response_time_ms: int | None = None,
        error_message: str | None = None,
    ) -> int:

        if not isinstance(endpoint, str) or not endpoint.strip():
            raise ValueError("Endpoint cannot be empty.")

        if not isinstance(is_success, bool):
            raise TypeError("is_success must be a boolean.")

        if media_type is not None and media_type not in {"movie", "tv"}:
            raise ValueError("Media type must be 'movie' or 'tv'.")

        if tmdb_id is not None:
            if isinstance(tmdb_id, bool) or not isinstance(tmdb_id, int) or tmdb_id <= 0:
                raise ValueError("TMDB ID must be a positive integer.")

        if http_status_code is not None:
            if isinstance(http_status_code, bool) or not isinstance(http_status_code, int):
                raise TypeError("HTTP status code must be an integer.")

            if not 100 <= http_status_code <= 599:
                raise ValueError("Invalid HTTP status code.")

        if response_time_ms is not None:
            if isinstance(response_time_ms, bool) or not isinstance(response_time_ms, int):
                raise TypeError("response_time_ms must be an integer.")

            if response_time_ms < 0:
                raise ValueError("response_time_ms cannot be negative.")

        query = text("""
            INSERT INTO ops.api_request_logs (
                run_id,
                endpoint,
                media_type,
                tmdb_id,
                http_method,
                http_status_code,
                response_time_ms,
                is_success,
                error_message
            )
            VALUES (
                :run_id,
                :endpoint,
                :media_type,
                :tmdb_id,
                'GET',
                :http_status_code,
                :response_time_ms,
                :is_success,
                :error_message
            )
            RETURNING request_id
        """)

        with self.engine.begin() as connection:
            result = connection.execute(
                query,
                {
                    "run_id": UUID(str(run_id)) if run_id else None,
                    "endpoint": endpoint.strip(),
                    "media_type": media_type,
                    "tmdb_id": tmdb_id,
                    "http_status_code": http_status_code,
                    "response_time_ms": response_time_ms,
                    "is_success": is_success,
                    "error_message": error_message,
                },
            )

            return result.scalar_one()

    # =================================================
    # 5. INGESTION METRICS
    # =================================================

    def record_metric(
        self,
        run_id: UUID | str,
        media_type: str,
        metric_name: str,
        metric_value: Decimal | int | float,
        metric_unit: str | None = None,
    ) -> int:

        if media_type not in {"movie", "tv", "all"}:
            raise ValueError(
                "Media type must be 'movie', 'tv' or 'all'."
            )

        if not isinstance(metric_name, str) or not metric_name.strip():
            raise ValueError("Metric name cannot be empty.")

        if isinstance(metric_value, bool) or not isinstance(
            metric_value, (Decimal, int, float)
        ):
            raise TypeError("Metric value must be numeric.")

        if not Decimal(str(metric_value)).is_finite():
            raise ValueError("Metric value must be finite.")

        if metric_unit is not None and not isinstance(metric_unit, str):
            raise TypeError("Metric unit must be a string or None.")

        query = text("""
            INSERT INTO ops.ingestion_metrics (
                run_id,
                media_type,
                metric_name,
                metric_value,
                metric_unit
            )
            VALUES (
                :run_id,
                :media_type,
                :metric_name,
                :metric_value,
                :metric_unit
            )
            RETURNING metric_id
        """)

        with self.engine.begin() as connection:
            result = connection.execute(
                query,
                {
                    "run_id": UUID(str(run_id)),
                    "media_type": media_type,
                    "metric_name": metric_name.strip(),
                    "metric_value": metric_value,
                    "metric_unit": metric_unit,
                },
            )

            return result.scalar_one()
