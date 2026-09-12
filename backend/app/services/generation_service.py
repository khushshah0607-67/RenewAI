import csv
from datetime import datetime, timedelta, timezone
from io import StringIO

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError

from app.core.generation_validation import GenerationDataContract
from app.core.time_utils import normalize_datetime_to_utc
from app.db.models.historical_generation import HistoricalGeneration
from app.db.models.plant import Plant
from app.db.repositories.historical_generation_repository import HistoricalGenerationRepository


class GenerationService:
    def __init__(self, db):
        self.repository = HistoricalGenerationRepository(db)
        self.db = db

    def list_generation(
        self,
        plant_id: int,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[HistoricalGeneration]:
        return self.repository.get_for_plant(plant_id, start=start, end=end, limit=limit, offset=offset)

    @staticmethod
    def _normalize_upload_file(file: UploadFile) -> None:
        if file.content_type is None:
            file.content_type = "text/csv"

    def _calculate_gap_count(self, timestamps: list[datetime], resolution: str) -> int:
        if len(timestamps) < 2:
            return 0

        if resolution in {"15min", "60min"}:
            step_minutes = 15 if resolution == "15min" else 60
            min_ts = min(timestamps)
            max_ts = max(timestamps)
            expected_count = int((max_ts - min_ts).total_seconds() // 60 // step_minutes) + 1
            return max(expected_count - len(timestamps), 0)

        return sum(
            1
            for previous, current in zip(timestamps, timestamps[1:])
            if (current - previous) > timedelta(minutes=15)
        )

    def upload_generation_csv(self, plant_id: int, file: UploadFile) -> dict:
        self._normalize_upload_file(file)
        content_type = (file.content_type or "").lower()
        if content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain"} and not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Uploaded file must be a CSV file")

        file.file.seek(0)
        contents = file.file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        if len(contents) > 2_000_000:
            raise HTTPException(status_code=400, detail="CSV file is too large")
        file.file.seek(0)

        plant = self.db.get(Plant, plant_id)
        if plant is None:
            raise HTTPException(status_code=404, detail="Plant not found")

        contract = GenerationDataContract(float(plant.installed_capacity_mw))

        text = contents.decode("utf-8-sig")
        stream = StringIO(text)
        reader = csv.DictReader(stream)

        if reader.fieldnames is None:
            raise HTTPException(status_code=400, detail="CSV is missing a header row")

        required_columns = {"timestamp", "generation_mw"}
        missing = sorted(required_columns - set(reader.fieldnames))
        if missing:
            raise HTTPException(status_code=400, detail=f"CSV missing required columns: {', '.join(missing)}")

        rows_received = 0
        rows_inserted = 0
        rows_rejected = 0
        duplicate_count = 0
        valid_row_count = 0
        errors: list[str] = []
        valid_records: list[HistoricalGeneration] = []
        existing_timestamps = self.repository.get_existing_timestamps(plant_id)
        seen_this_upload: set[datetime] = set()
        normalized_rows: list[tuple[datetime, float]] = []
        min_timestamp: datetime | None = None
        max_timestamp: datetime | None = None

        for row_index, row in enumerate(reader, start=2):
            rows_received += 1
            timestamp_raw = (row.get("timestamp") or "").strip()
            generation_raw = (row.get("generation_mw") or "").strip()

            if not timestamp_raw or not generation_raw:
                rows_rejected += 1
                errors.append(f"Row {row_index}: missing timestamp or generation_mw")
                continue

            try:
                timestamp_local = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
            except ValueError:
                rows_rejected += 1
                errors.append(f"Row {row_index}: invalid timestamp '{timestamp_raw}'")
                continue

            try:
                timestamp_utc = normalize_datetime_to_utc(timestamp_local, plant.timezone)
            except ValueError as exc:
                rows_rejected += 1
                errors.append(f"Row {row_index}: {exc}")
                continue

            try:
                generation_mw = float(generation_raw)
            except ValueError:
                rows_rejected += 1
                errors.append(f"Row {row_index}: generation_mw must be numeric")
                continue

            try:
                generation_mw = contract.validate_generation_row(timestamp_utc, generation_mw)
            except ValueError as exc:
                rows_rejected += 1
                errors.append(f"Row {row_index}: {exc}")
                continue

            if timestamp_utc in existing_timestamps or timestamp_utc in seen_this_upload:
                duplicate_count += 1
                rows_rejected += 1
                errors.append(f"Row {row_index}: duplicate timestamp '{timestamp_utc.isoformat()}'")
                continue

            normalized_rows.append((timestamp_utc, generation_mw))
            seen_this_upload.add(timestamp_utc)
            existing_timestamps.add(timestamp_utc)
            valid_row_count += 1

            if min_timestamp is None or timestamp_utc < min_timestamp:
                min_timestamp = timestamp_utc
            if max_timestamp is None or timestamp_utc > max_timestamp:
                max_timestamp = timestamp_utc

        sorted_rows = contract.sort_records(normalized_rows)
        valid_records = [
            HistoricalGeneration(
                plant_id=plant_id,
                timestamp=timestamp,
                generation_mw=generation_mw,
            )
            for timestamp, generation_mw in sorted_rows
        ]

        resolution = GenerationDataContract.detect_resolution([timestamp for timestamp, _ in sorted_rows])
        gap_count = self._calculate_gap_count([timestamp for timestamp, _ in sorted_rows], resolution)

        if valid_records:
            try:
                self.repository.create_many(valid_records)
                rows_inserted = len(valid_records)
            except IntegrityError:
                self.db.rollback()
                duplicate_count += len(valid_records)
                rows_rejected += len(valid_records)
                valid_records = []
                errors.append("Database rejected duplicate rows during commit; no invalid records were persisted.")
                rows_inserted = 0

        return {
            "plant_id": plant_id,
            "rows_received": rows_received,
            "rows_inserted": rows_inserted,
            "rows_rejected": rows_rejected,
            "duplicate_count": duplicate_count,
            "gap_count": gap_count,
            "detected_resolution": resolution if resolution != "unknown" else None,
            "min_timestamp": min_timestamp,
            "max_timestamp": max_timestamp,
            "valid_row_count": valid_row_count,
            "ml_ready_15min": resolution == "15min" and gap_count == 0,
            "errors": errors[:20],
        }
