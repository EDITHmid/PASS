"""
PASS Data Ingestion Module
============================
Implements FR-01, FR-02, FR-03, FR-04 from the PRD.

Handles:
  - CSV file parsing and validation
  - Timestamp normalization to UTC UNIX format
  - Error logging for malformed/incomplete records
  - Δt computation on ingestion
"""

import uuid
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Tuple, List, Optional
from io import StringIO

from engine.metrics import MetricComputer


class DataIngestor:
    """
    Handles data ingestion from CSV files and validates submission records.
    """

    REQUIRED_COLUMNS = {
        "student_id",
        "assignment_id",
        "submission_timestamp",
        "deadline_timestamp",
    }

    OPTIONAL_COLUMNS = {
        "student_name",
        "course_id",
        "submission_status",
        "attendance_pct",
        "mid1_score",
        "mid2_score",
        "mid3_score",
    }

    def __init__(self):
        self.metric_computer = MetricComputer()
        self.errors = []

    def ingest_csv(
        self, file_content: str, filename: str = "upload.csv"
    ) -> Dict:
        """
        Parse and validate a CSV file for ingestion (FR-01).

        Expected columns: student_id, assignment_id, submission_timestamp,
                         deadline_timestamp.

        Args:
            file_content: Raw CSV string content.
            filename: Original filename for logging.

        Returns:
            Ingestion result dictionary with valid records and error log.
        """
        self.errors = []

        try:
            df = pd.read_csv(StringIO(file_content))
        except Exception as e:
            return {
                "success": False,
                "filename": filename,
                "total_records": 0,
                "valid_records": 0,
                "invalid_records": 0,
                "records": [],
                "errors": [f"Failed to parse CSV: {str(e)}"],
            }

        # Normalize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        # Validate required columns
        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            return {
                "success": False,
                "filename": filename,
                "total_records": len(df),
                "valid_records": 0,
                "invalid_records": len(df),
                "records": [],
                "errors": [f"Missing required columns: {', '.join(missing)}"],
            }

        total = len(df)
        valid_records = []
        invalid_count = 0

        for idx, row in df.iterrows():
            record, is_valid = self._process_row(row, idx)
            if is_valid:
                valid_records.append(record)
            else:
                invalid_count += 1

        return {
            "success": True,
            "filename": filename,
            "total_records": total,
            "valid_records": len(valid_records),
            "invalid_records": invalid_count,
            "records": valid_records,
            "errors": self.errors,
        }

    def _process_row(
        self, row: pd.Series, row_index: int
    ) -> Tuple[Optional[Dict], bool]:
        """
        Process and validate a single CSV row.

        Args:
            row: Pandas Series representing one CSV row.
            row_index: Row number for error reporting.

        Returns:
            Tuple of (processed record dict or None, is_valid bool).
        """
        # Check for required fields
        for col in self.REQUIRED_COLUMNS:
            if pd.isna(row.get(col)):
                self.errors.append(
                    f"Row {row_index + 1}: Missing required field '{col}'"
                )
                return None, False

        # Parse timestamps (FR-03: normalize to UTC)
        try:
            submission_ts = self._parse_timestamp(row["submission_timestamp"])
            deadline_ts = self._parse_timestamp(row["deadline_timestamp"])
        except (ValueError, TypeError) as e:
            self.errors.append(
                f"Row {row_index + 1}: Invalid timestamp format — {str(e)}"
            )
            return None, False

        # Compute Δt (FR-05)
        delta_t = self.metric_computer.compute_delta_t(
            submission_ts.timestamp(), deadline_ts.timestamp()
        )
        delta_t_hours = self.metric_computer.delta_t_to_hours(delta_t)
        status = self.metric_computer.classify_submission(delta_t)

        # Override status if provided in CSV
        if "submission_status" in row and not pd.isna(row.get("submission_status")):
            csv_status = str(row["submission_status"]).strip().lower()
            if csv_status in ("on-time", "late", "missing"):
                status = csv_status

        # Build validated record
        record = {
            "submission_id": f"SUB-{uuid.uuid4().hex[:10].upper()}",
            "student_id": str(row["student_id"]).strip(),
            "student_name": str(row.get("student_name", "")).strip() or None,
            "assignment_id": str(row["assignment_id"]).strip(),
            "course_id": str(row.get("course_id", "")).strip() or None,
            "submitted_at": submission_ts,
            "deadline": deadline_ts,
            "delta_t": delta_t,
            "delta_t_hours": delta_t_hours,
            "submission_status": status,
            "attendance_pct": self._safe_float(row.get("attendance_pct")),
            "mid1_score": self._safe_float(row.get("mid1_score")),
            "mid2_score": self._safe_float(row.get("mid2_score")),
            "mid3_score": self._safe_float(row.get("mid3_score")),
        }

        return record, True

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """Safely convert a value to float, returning None on failure."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        try:
            v = float(value)
            return v if not np.isnan(v) else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_timestamp(value) -> datetime:
        """
        Parse a timestamp value to a timezone-aware datetime (FR-03).

        Supports ISO 8601 strings and UNIX timestamps.

        Args:
            value: Timestamp as string, int, or float.

        Returns:
            Timezone-aware datetime in UTC.
        """
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)

        value = str(value).strip()

        if not value:
            raise ValueError("Empty timestamp value")

        # Try common formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%d/%m/%Y %H:%M:%S",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        # Try pandas parser as fallback
        try:
            dt = pd.to_datetime(value, utc=True)
            return dt.to_pydatetime()
        except Exception:
            pass

        raise ValueError(f"Cannot parse timestamp: '{value}'")

    def validate_csv_structure(self, file_content: str) -> Dict:
        """
        Pre-validate CSV structure before full ingestion.

        Args:
            file_content: Raw CSV string content.

        Returns:
            Validation result with column info and sample data.
        """
        try:
            df = pd.read_csv(StringIO(file_content), nrows=5)
            df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

            missing = self.REQUIRED_COLUMNS - set(df.columns)
            extra = set(df.columns) - self.REQUIRED_COLUMNS - self.OPTIONAL_COLUMNS

            return {
                "valid": len(missing) == 0,
                "columns_found": list(df.columns),
                "columns_missing": list(missing),
                "columns_extra": list(extra),
                "sample_rows": df.head(3).to_dict(orient="records"),
                "total_rows_preview": len(df),
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
            }
