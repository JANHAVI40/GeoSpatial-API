from __future__ import annotations

import json
import shutil
import tempfile
import uuid
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from zipfile import BadZipFile, ZipFile

import geopandas as gpd
from fastapi import UploadFile
from shapely.geometry.base import BaseGeometry

from app.models import FileRecord

ALLOWED_EXTENSIONS = {".zip", ".kml"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _crs_name(crs: Any) -> str | None:
    if crs is None:
        return None
    return crs.to_string()


def _is_unsafe_member_path(member_name: str) -> bool:
    normalized_name = member_name.replace("\\", "/")
    path_obj = PurePosixPath(normalized_name)
    windows_path = PureWindowsPath(member_name)

    if path_obj.is_absolute() or windows_path.is_absolute():
        return True
    if normalized_name in {".", ".."}:
        return True
    if normalized_name.startswith("../") or normalized_name.startswith("./"):
        return True
    if normalized_name.endswith("/..") or "/../" in normalized_name or normalized_name == "..":
        return True
    return False


def _safe_extract_shapefile(archive: Path, target: Path) -> Path:
    try:
        with ZipFile(archive) as zip_file:
            members = zip_file.infolist()
            target_root = target.resolve()
            for member in members:
                if _is_unsafe_member_path(member.filename):
                    raise ValueError("Archive contains an unsafe path")
                destination = (target / member.filename).resolve()
                try:
                    destination.relative_to(target_root)
                except ValueError as exc:
                    raise ValueError("Archive contains an unsafe path") from exc
            zip_file.extractall(target)
    except BadZipFile as exc:
        raise ValueError("The uploaded ZIP file is invalid") from exc

    shapefiles = [
        path for path in target.rglob("*") if path.is_file() and path.suffix.lower() == ".shp"
    ]
    if len(shapefiles) != 1:
        raise ValueError("ZIP must contain exactly one .shp file")
    return shapefiles[0]


def _projected_geometry(geometry: BaseGeometry, source_crs: Any, frame: gpd.GeoDataFrame) -> BaseGeometry:
    if source_crs is None:
        raise ValueError("The file does not define a CRS; measurements cannot be calculated safely")
    if source_crs.is_geographic:
        projected_crs = frame.estimate_utm_crs()
        if projected_crs is None:
            raise ValueError("Unable to determine a projected CRS for the file")
        return gpd.GeoSeries([geometry], crs=source_crs).to_crs(projected_crs).iloc[0]
    return geometry


def _serialize_properties(properties: Any) -> dict[str, Any]:
    if properties is None:
        return {}
    return json.loads(json.dumps(dict(properties), default=str))


def process_file(path: Path, filename: str, record_id: str) -> FileRecord:
    record = FileRecord(id=record_id, filename=filename)
    with tempfile.TemporaryDirectory() as temporary_directory:
        working_directory = Path(temporary_directory)
        source = path
        if path.suffix.lower() == ".zip":
            source = _safe_extract_shapefile(path, working_directory)
        frame = gpd.read_file(source)
        source_crs = frame.crs
        record.crs = _crs_name(source_crs)
        record.feature_count = len(frame)

        for index, row in frame.iterrows():
            geometry = row.geometry
            feature: dict[str, Any] = {
                "id": index,
                "geometry_type": geometry.geom_type if geometry is not None else None,
                "geometry": geometry.__geo_interface__ if geometry is not None else None,
                "crs": record.crs,
                "properties": _serialize_properties(row.drop(labels="geometry")),
                "measurement": None,
            }
            if geometry is not None and not geometry.is_empty:
                if geometry.geom_type in {"Polygon", "MultiPolygon", "LineString", "MultiLineString"}:
                    measured = _projected_geometry(geometry, source_crs, frame)
                    if geometry.geom_type in {"Polygon", "MultiPolygon"}:
                        feature["measurement"] = {"area": measured.area, "unit": "square metres"}
                    else:
                        feature["measurement"] = {"length": measured.length, "unit": "metres"}
            record.features.append(feature)
    record.status = "COMPLETED"
    return record


def save_upload(upload: UploadFile) -> tuple[Path, str]:
    filename = Path(upload.filename or "").name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Only .kml and .zip files are supported")

    temporary_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    total = 0
    try:
        while chunk := upload.file.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise ValueError("Uploaded file exceeds the 50 MB limit")
            temporary_file.write(chunk)
    finally:
        temporary_file.close()
    return Path(temporary_file.name), filename


def create_record(upload: UploadFile) -> FileRecord:
    path, filename = save_upload(upload)
    record_id = uuid.uuid4().hex
    try:
        return process_file(path, filename, record_id)
    finally:
        path.unlink(missing_ok=True)
