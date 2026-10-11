from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models import FileRecord
from app.processing import create_record

router = APIRouter()
records: dict[str, FileRecord] = {}


def _summary(record: FileRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "filename": record.filename,
        "feature_count": record.feature_count,
        "crs": record.crs,
        "status": record.status,
        "created_at": record.created_at,
        "error": record.error,
    }


@router.post("/files/", status_code=201)
def upload_file(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        record = create_record(file)
    except (OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    records[record.id] = record
    return _summary(record)


@router.get("/files/{file_id}/")
def file_information(file_id: str) -> dict[str, Any]:
    record = records.get(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    return _summary(record)


@router.get("/files/{file_id}/measurements/")
def file_measurements(file_id: str) -> dict[str, Any]:
    record = records.get(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "id": record.id,
        "filename": record.filename,
        "crs": record.crs,
        "measurements": record.features,
    }
