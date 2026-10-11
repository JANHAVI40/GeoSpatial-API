# Geospatial File Measurement API

FastAPI service for uploading a KML file or a ZIP archive containing one
Shapefile and returning feature metadata plus CRS-aware measurements.

## Setup

Python 3.11+ is recommended.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Deploy with Docker

Build and run the service locally:

```powershell
docker build -t geospatial-api .
docker run --rm -p 8000:8000 geospatial-api
```

Check that it is running at `http://127.0.0.1:8000/health`, then open
`http://127.0.0.1:8000/docs`.

The container uses the `PORT` environment variable when provided, which is
required by some hosting platforms:

```powershell
docker run --rm -e PORT=8000 -p 8000:8000 geospatial-api
```

## Deploy to Render

1. Push this repository to GitHub.
2. In Render, choose **New > Blueprint** and select the repository.
3. Render detects `render.yaml`, builds the Docker image, and deploys the
   `geospatial-api` web service.
4. Open the deployed URL followed by `/health` to verify the service.
5. Open the deployed URL followed by `/docs` to upload a KML file or ZIP
   archive interactively.

The free Render service may sleep when idle. Records are held in memory, so
uploads are lost whenever the service restarts or is redeployed.

## API

### Upload

`POST /api/files/` with multipart field `file`. Accepted files are `.kml` and
`.zip` archives containing exactly one `.shp` file and its sidecar files.

```powershell
curl.exe -X POST -F "file=@survey.kml" http://127.0.0.1:8000/api/files/
```

Response:

```json
{
  "id": "8a3...",
  "filename": "survey.kml",
  "feature_count": 12,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "created_at": "2026-10-11T07:15:00Z",
  "error": null
}
```

### File information

`GET /api/files/{id}/` returns the upload summary.

### Measurements

`GET /api/files/{id}/measurements/` returns every feature with `id`,
`geometry_type`, GeoJSON-compatible `geometry`, `crs`, `properties`, and a
`measurement`. Polygon and multipolygon measurements contain `area` in square
metres; line and multiline measurements contain `length` in metres; points and
other geometries have `measurement: null`.

## Architecture

- `app/routes.py` defines the three HTTP endpoints and the in-memory record
  repository used for this assessment service.
- `app/processing.py` validates uploads, safely extracts Shapefile archives,
  reads files with GeoPandas, serializes feature metadata, and calculates
  measurements.
- Geographic CRS geometries are transformed to a UTM CRS estimated from the
  dataset before area or length is calculated. Projected CRS geometries are
  measured directly. Files without a CRS are rejected instead of producing
  misleading degree-based measurements.

## Design decisions

FastAPI was chosen for its typed request handling and generated OpenAPI
documentation. GeoPandas delegates format parsing to GDAL/Fiona and provides
consistent CRS transformations for both formats. The service intentionally
keeps records in memory and deletes temporary uploads after processing to keep
the example easy to run; production deployment should use durable metadata and
object storage, a background job queue, authentication, quotas, and structured
logging.

## Learning and future scope

This project demonstrates multipart upload validation, geospatial parsing,
GeoJSON serialization, and projected-coordinate measurement. Future work could
add persistent storage, asynchronous processing and progress states, streaming
downloads, configurable measurement units, more geometry types, and automated
deployment.
