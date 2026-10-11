import zipfile

import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon

from app.processing import _safe_extract_shapefile, process_file


def test_processes_geographic_features_with_projected_measurements(tmp_path):
    frame = gpd.GeoDataFrame(
        {"name": ["square", "road", "marker"]},
        geometry=[
            Polygon([(0, 0), (0, 0.01), (0.01, 0.01), (0.01, 0)]),
            LineString([(0, 0), (0.01, 0)]),
            Point(0, 0),
        ],
        crs="EPSG:4326",
    )
    source = tmp_path / "features.geojson"
    frame.to_file(source, driver="GeoJSON")

    result = process_file(source, "features.geojson", "test-id")

    assert result.status == "COMPLETED"
    assert result.crs == "EPSG:4326"
    assert result.feature_count == 3
    assert result.features[0]["measurement"]["area"] > 1_000_000
    assert result.features[1]["measurement"]["length"] > 1_000
    assert result.features[2]["measurement"] is None


def test_safe_extract_shapefile_accepts_uppercase_extensions(tmp_path):
    frame = gpd.GeoDataFrame(
        {"name": ["square"]},
        geometry=[Polygon([(0, 0), (0, 0.01), (0.01, 0.01), (0.01, 0)])],
        crs="EPSG:4326",
    )
    shapefile_directory = tmp_path / "features"
    frame.to_file(shapefile_directory, driver="ESRI Shapefile")

    archive_path = tmp_path / "features.zip"
    with zipfile.ZipFile(archive_path, "w") as zip_file:
        for file_path in shapefile_directory.iterdir():
            zip_file.write(file_path, arcname=file_path.name.upper())

    extracted = _safe_extract_shapefile(archive_path, tmp_path / "unpacked")

    assert extracted.name.upper().endswith(".SHP")
    assert extracted.exists()


def test_safe_extract_shapefile_rejects_parent_directory_traversal(tmp_path):
    archive_path = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive_path, "w") as zip_file:
        zip_file.writestr("../evil.shp", b"raw")

    try:
        _safe_extract_shapefile(archive_path, tmp_path / "safe")
    except ValueError as exc:
        assert "unsafe path" in str(exc)
    else:
        raise AssertionError("Traversal archive should have been rejected")
