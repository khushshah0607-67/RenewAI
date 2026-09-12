import csv
from datetime import datetime
from io import StringIO

from fastapi import HTTPException, UploadFile

from app.db.models.historical_generation import HistoricalGeneration
from app.db.repositories.historical_generation_repository import HistoricalGenerationRepository


class GenerationService:
    def __init__(self, db):
        self.repository = HistoricalGenerationRepository(db)
        self.db = db

    def list_generation(self, plant_id: int, start: datetime | None = None, end: datetime | None = None, limit: int | None = None) -> list[HistoricalGeneration]:
        return self.repository.get_for_plant(plant_id, start=start, end=end, limit=limit)

    def upload_generation_csv(self, plant_id: int, file: UploadFile) -> dict:
        if file.content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain"} and not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Uploaded file must be a CSV file")

        contents = file.file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        if len(contents) > 2_000_000:
            raise HTTPException(status_code=400, detail="CSV file is too large")

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
        errors: list[str] = []
        valid_records: list[HistoricalGeneration] = []
        existing_timestamps = self.repository.get_existing_timestamps(plant_id)
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
                timestamp = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
            except ValueError:
                rows_rejected += 1
                errors.append(f"Row {row_index}: invalid timestamp '{timestamp_raw}'")
                continue

            try:
                generation_mw = float(generation_raw)
            except ValueError:
                rows_rejected += 1
                errors.append(f"Row {row_index}: generation_mw must be numeric")
                continue

            if generation_mw < 0:
                rows_rejected += 1
                errors.append(f"Row {row_index}: generation_mw must be >= 0")
                continue

            if timestamp in existing_timestamps:
                duplicate_count += 1
                rows_rejected += 1
                errors.append(f"Row {row_index}: duplicate timestamp '{timestamp.isoformat()}'")
                continue

            valid_records.append(
                HistoricalGeneration(
                    plant_id=plant_id,
                    timestamp=timestamp,
                    generation_mw=generation_mw,
                )
            )
            existing_timestamps.add(timestamp)
            rows_inserted += 1

            if min_timestamp is None or timestamp < min_timestamp:
                min_timestamp = timestamp
            if max_timestamp is None or timestamp > max_timestamp:
                max_timestamp = timestamp

        if valid_records:
            self.repository.create_many(valid_records)

        return {
            "plant_id": plant_id,
            "rows_received": rows_received,
            "rows_inserted": rows_inserted,
            "rows_rejected": rows_rejected,
            "duplicate_count": duplicate_count,
            "min_timestamp": min_timestamp,
            "max_timestamp": max_timestamp,
            "errors": errors[:20],
        }
