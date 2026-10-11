from fastapi import FastAPI

from app.routes import router

app = FastAPI(
    title="Geospatial File Measurement API",
    description="Upload Shapefiles and KML files and calculate feature measurements.",
    version="1.0.0",
)
app.include_router(router, prefix="/api")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
