"""Digitise the PV-density figure from the supplied ISPRS paper.

This is deliberately a *figure digitisation*, not a reconstruction of the
authors' unpublished PV-module polygons.  It creates:

* a georeferenced copy of Figure 12 (the most faithful representation);
* a 32-bit visual-density raster scaled to the figure legend (0--40.79);
* a 0.01 degree sampling grid as GeoJSON, CSV, and ESRI Shapefile.

The figure's map frame is georeferenced from the two printed longitude labels
(-9.000 and -7.500) and the two printed latitude labels (32.000 and 31.000).
All vector attributes are named to make clear that values come from colour
digitisation of the publication, not the original analysis.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import struct
from datetime import date
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
from PIL import Image
from pypdf import PdfReader


# Pixel coordinates in the 1070 x 646 source figure.  Values were measured
# from its labelled graticule, not guessed from the regional boundary.
MAP_X0, MAP_Y0, MAP_X1, MAP_Y1 = 260, 44, 1031, 602
LON_TICK_1, LON_TICK_1_X = -9.000, 500.0
LON_TICK_2, LON_TICK_2_X = -7.500, 890.0
LAT_TICK_1, LAT_TICK_1_Y = 32.000, 274.5
LAT_TICK_2, LAT_TICK_2_Y = 31.000, 533.0
LEGEND_MAX = 40.79
GRID_STEP_DEGREES = 0.01
WGS84_WKT = (
    'GEOGCS["WGS 84",DATUM["WGS_1984",'
    'SPHEROID["WGS 84",6378137,298.257223563]],'
    'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
)


def lon_at(global_x: float) -> float:
    """Longitude at a source-image pixel centre."""
    return LON_TICK_1 + (global_x - LON_TICK_1_X) * (
        (LON_TICK_2 - LON_TICK_1) / (LON_TICK_2_X - LON_TICK_1_X)
    )


def lat_at(global_y: float) -> float:
    """Latitude at a source-image pixel centre."""
    return LAT_TICK_1 + (global_y - LAT_TICK_1_Y) * (
        (LAT_TICK_2 - LAT_TICK_1) / (LAT_TICK_2_Y - LAT_TICK_1_Y)
    )


LON_STEP = lon_at(LON_TICK_1_X + 1) - lon_at(LON_TICK_1_X)
LAT_STEP = lat_at(LAT_TICK_1_Y + 1) - lat_at(LAT_TICK_1_Y)


def extract_figure(pdf_path: Path) -> Image.Image:
    """Extract the Figure 12 image object from PDF page 10."""
    reader = PdfReader(str(pdf_path))
    page_images = reader.pages[9].images
    candidates = [item.image.convert("RGB") for item in page_images]
    if not candidates:
        raise RuntimeError("No images were found on page 10 of the PDF.")
    # Figure 12 is the wide image at the top of page 10 (1070 x 646).
    figure = max(candidates, key=lambda image: image.width / image.height)
    if figure.size != (1070, 646):
        raise RuntimeError(
            f"Expected the 1070 x 646 heatmap figure, found {figure.size}. "
            "Update the measured crop constants before continuing."
        )
    return figure


def digitise_visual_density(rgb: np.ndarray) -> np.ndarray:
    """Estimate the density-layer value encoded by Figure 12's colour ramp.

    The raster is intentionally termed ``visual_density``: it reads the
    publication's cyan/yellow/red heatmap colours.  It cannot recover the
    authors' original KDE parameters or module centroids.
    """
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0].astype(np.float32)

    # The figure's ramp progresses cyan -> yellow/green -> orange/red.  The
    # saturation and value guards reject most satellite-basemap colours while
    # retaining the clearly visible published heatmap.
    cyan = cv2.inRange(hsv, (80, 130, 130), (105, 255, 255)) > 0
    yellow_green = cv2.inRange(hsv, (30, 155, 150), (79, 255, 255)) > 0
    orange_red = cv2.inRange(hsv, (0, 175, 100), (29, 255, 255)) > 0

    score = np.zeros(hue.shape, dtype=np.float32)
    # Low-density cyan is deliberately kept nonzero so isolated published
    # kernels remain visible in the vector export.
    score[cyan] = 0.04 + (105.0 - hue[cyan]) / 25.0 * 0.08
    # Moving from green/yellow (high hue) to orange (low hue) increases value.
    score[yellow_green] = 0.12 + (79.0 - hue[yellow_green]) / 49.0 * 0.53
    # Dark red corresponds to the legend's upper end.
    score[orange_red] = 0.65 + (29.0 - hue[orange_red]) / 29.0 * 0.35

    # Compression leaves tiny holes in otherwise continuous density patches.
    # A one-pixel Gaussian smooths those artefacts without changing geography.
    score = cv2.GaussianBlur(score, (0, 0), sigmaX=1.0, sigmaY=1.0)
    return np.clip(score, 0.0, 1.0)


def write_world_file(path: Path) -> None:
    """Write a world file for the cropped map; coordinates refer to centres."""
    lines = [
        f"{LON_STEP:.15f}",
        "0.0",
        "0.0",
        f"{LAT_STEP:.15f}",
        f"{lon_at(MAP_X0):.15f}",
        f"{lat_at(MAP_Y0):.15f}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def density_class(density: float) -> str:
    if density >= 25.0:
        return "high"
    if density >= 10.0:
        return "medium"
    return "low"


def sample_grid(density: np.ndarray) -> list[dict[str, object]]:
    """Sample the visual-density raster at approximately one kilometre."""
    lon_min, lon_max = lon_at(MAP_X0), lon_at(MAP_X1 - 1)
    lat_min, lat_max = lat_at(MAP_Y1 - 1), lat_at(MAP_Y0)
    start_lon = math.ceil((lon_min - 1e-10) / GRID_STEP_DEGREES) * GRID_STEP_DEGREES
    start_lat = math.ceil((lat_min - 1e-10) / GRID_STEP_DEGREES) * GRID_STEP_DEGREES
    longitudes = np.arange(start_lon, lon_max + 1e-10, GRID_STEP_DEGREES)
    latitudes = np.arange(start_lat, lat_max + 1e-10, GRID_STEP_DEGREES)

    records: list[dict[str, object]] = []
    for lat in latitudes:
        global_y = LAT_TICK_1_Y + (lat - LAT_TICK_1) / LAT_STEP
        local_y = global_y - MAP_Y0
        if local_y < 0 or local_y >= density.shape[0] - 1:
            continue
        y0 = int(math.floor(local_y))
        wy = local_y - y0
        for lon in longitudes:
            global_x = LON_TICK_1_X + (lon - LON_TICK_1) / LON_STEP
            local_x = global_x - MAP_X0
            if local_x < 0 or local_x >= density.shape[1] - 1:
                continue
            x0 = int(math.floor(local_x))
            wx = local_x - x0
            # Bilinear interpolation makes the grid independent of pixel phase.
            value = (
                density[y0, x0] * (1 - wx) * (1 - wy)
                + density[y0, x0 + 1] * wx * (1 - wy)
                + density[y0 + 1, x0] * (1 - wx) * wy
                + density[y0 + 1, x0 + 1] * wx * wy
            )
            density_value = float(value * LEGEND_MAX)
            # Keep very low published density too, but omit ordinary imagery.
            if density_value < 0.5:
                continue
            records.append(
                {
                    "longitude": round(float(lon), 6),
                    "latitude": round(float(lat), 6),
                    "relative_density": round(float(value), 5),
                    "visual_density_0_40_79": round(density_value, 3),
                    "density_class": density_class(density_value),
                    "source": "Figure 12 digitisation",
                }
            )
    return records


def write_geojson(records: Iterable[dict[str, object]], path: Path) -> None:
    features = []
    for record in records:
        props = dict(record)
        lon = props.pop("longitude")
        lat = props.pop("latitude")
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": props,
            }
        )
    collection = {
        "type": "FeatureCollection",
        "name": "pv_density_visual_digitisation",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": features,
    }
    path.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def write_csv(records: Iterable[dict[str, object]], path: Path) -> None:
    fields = [
        "longitude",
        "latitude",
        "relative_density",
        "visual_density_0_40_79",
        "density_class",
        "source",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def _dbf_field(name: str, field_type: str, length: int, decimals: int = 0) -> bytes:
    encoded = name.encode("ascii")[:11].ljust(11, b"\0")
    return encoded + field_type.encode("ascii") + b"\0\0\0\0" + bytes([length, decimals]) + b"\0" * 14


def write_point_shapefile(records: list[dict[str, object]], stem: Path) -> None:
    """Write a compact, dependency-free WGS84 point Shapefile with a DBF."""
    if not records:
        raise RuntimeError("No density grid records were generated.")
    points = [(float(row["longitude"]), float(row["latitude"])) for row in records]
    xs, ys = zip(*points)
    shp_path = stem.with_suffix(".shp")
    shx_path = stem.with_suffix(".shx")

    # Each POINT record contains 20 bytes = 10 16-bit words; its record header
    # is 8 bytes = 4 words.  The .shx index therefore advances by 14 words.
    shp_length_words = (100 + len(points) * 28) // 2
    shx_length_words = (100 + len(points) * 8) // 2

    def header(length_words: int) -> bytes:
        return (
            struct.pack(">7i", 9994, 0, 0, 0, 0, 0, length_words)
            + struct.pack("<2i4d4d", 1000, 1, min(xs), min(ys), max(xs), max(ys), 0, 0, 0, 0)
        )

    with shp_path.open("wb") as shp, shx_path.open("wb") as shx:
        shp.write(header(shp_length_words))
        shx.write(header(shx_length_words))
        offset_words = 50
        for index, (x, y) in enumerate(points, start=1):
            shp.write(struct.pack(">2i", index, 10))
            shp.write(struct.pack("<idd", 1, x, y))
            shx.write(struct.pack(">2i", offset_words, 10))
            offset_words += 14

    fields = [
        ("SCORE", "N", 9, 5),
        ("DENSITY", "N", 9, 3),
        ("CLASS", "C", 10, 0),
        ("SOURCE", "C", 22, 0),
    ]
    record_length = 1 + sum(field[2] for field in fields)
    header_length = 32 + len(fields) * 32 + 1
    today = date.today()
    with stem.with_suffix(".dbf").open("wb") as dbf:
        dbf.write(
            struct.pack(
                "<BBBBIHH20x",
                3,
                today.year - 1900,
                today.month,
                today.day,
                len(records),
                header_length,
                record_length,
            )
        )
        for field in fields:
            dbf.write(_dbf_field(*field))
        dbf.write(b"\r")
        for row in records:
            values = [
                f"{float(row['relative_density']):9.5f}",
                f"{float(row['visual_density_0_40_79']):9.3f}",
                str(row["density_class"])[:10].ljust(10),
                "Fig12 digitisation".ljust(22),
            ]
            dbf.write(b" " + "".join(values).encode("ascii"))
        dbf.write(b"\x1a")
    stem.with_suffix(".prj").write_text(WGS84_WKT + "\n", encoding="ascii")
    stem.with_suffix(".cpg").write_text("UTF-8\n", encoding="ascii")


def write_readme(path: Path, records: list[dict[str, object]], bounds: dict[str, float]) -> None:
    path.write_text(
        f"""# Marrakech-Safi PV density: digitised Figure 12

## What this package is

This package is a georeferenced **digitisation of Figure 12** from the supplied
paper, *Solar Panel Segmentation in High-Resolution Satellite Imagery: A
YOLOv8-GIS Approach in the Marrakech-Safi Region, Morocco*.  It was made because
the paper does not include its underlying PV polygons, mask tiles, or KDE input
points.

The original paper reports 18,050 PV modules and says it made its final heatmap
after converting segmentation masks to polygons.  Those individual module
geometries cannot be accurately recovered from a printed 1070 x 646-pixel map.
Do **not** use this package as an authoritative PV inventory or for parcel-level
analysis.

## Files

* `pv_density_map_georeferenced.tif` and `.png` - the original published map
  crop, placed geographically.  This is the closest visual match to the paper.
* `pv_density_visual_0_40.tif` - a float raster derived from the displayed
  cyan/yellow/red heatmap colours; values are visually scaled to the legend's
  0--40.79 range and are not the paper's original KDE measurements.
* `pv_density_visual_grid.geojson`, `.csv`, and `.shp` (+ sidecars) - roughly
  1 km WGS84 sample points.  In QGIS, style `DENSITY` / `visual_density_0_40_79`
  with a continuous colour ramp or run a Heatmap renderer.
* `.tfw` and `.prj` sidecars - WGS84 georeferencing for the TIFF files.

## Coordinate reference system and accuracy

All files use WGS 84 (EPSG:4326).  The image frame was fitted to the printed
graticule labels: -9.000 and -7.500 longitude, 32.000 and 31.000 latitude.
The resulting raster frame is approximately:

* longitude: {bounds['west']:.5f} to {bounds['east']:.5f}
* latitude: {bounds['south']:.5f} to {bounds['north']:.5f}

Expect positional uncertainty of a few image pixels (roughly 1--2 km), plus
uncertainty where the heatmap colour blends with the satellite basemap.  The
vector points record the visual pattern, not original PV locations.

## Vector attributes

* `relative_density` / `SCORE`: 0--1 visual colour-ramp strength.
* `visual_density_0_40_79` / `DENSITY`: visual scaling to the figure legend.
* `density_class` / `CLASS`: low (<10), medium (10--<25), high (>=25).

There are {len(records):,} nonzero grid samples.  Use the georeferenced figure
as the primary reference when comparing against the publication.
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("isprs-archives-XLVIII-4-W17-2025-317-2026.pdf"),
        help="Path to the supplied paper PDF.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/pv_density_digitization"),
        help="Directory for GIS deliverables.",
    )
    args = parser.parse_args()
    if not args.pdf.is_file():
        raise FileNotFoundError(f"PDF not found: {args.pdf}")
    args.output.mkdir(parents=True, exist_ok=True)

    figure = extract_figure(args.pdf)
    figure.save(args.output / "figure12_source_image.jpg", quality=95)
    figure_rgb = np.asarray(figure)
    crop = figure_rgb[MAP_Y0:MAP_Y1, MAP_X0:MAP_X1]
    Image.fromarray(crop).save(args.output / "pv_density_map_georeferenced.tif", compression="tiff_lzw")
    Image.fromarray(crop).save(args.output / "pv_density_map_georeferenced.png")

    visual_density = digitise_visual_density(crop)
    density_0_40 = (visual_density * LEGEND_MAX).astype(np.float32)
    Image.fromarray(density_0_40, mode="F").save(args.output / "pv_density_visual_0_40.tif")

    # A concise diagnostic preview makes it easy to see which heatmap colours
    # became the density signal, while preserving the source figure separately.
    preview = cv2.applyColorMap(np.uint8(density_0_40 / LEGEND_MAX * 255), cv2.COLORMAP_JET)
    preview = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
    Image.fromarray(preview).save(args.output / "pv_density_visual_preview.png")

    for stem in ("pv_density_map_georeferenced", "pv_density_visual_0_40"):
        write_world_file(args.output / f"{stem}.tfw")
        (args.output / f"{stem}.prj").write_text(WGS84_WKT + "\n", encoding="ascii")
    write_world_file(args.output / "pv_density_map_georeferenced.pgw")

    records = sample_grid(visual_density)
    write_geojson(records, args.output / "pv_density_visual_grid.geojson")
    write_csv(records, args.output / "pv_density_visual_grid.csv")
    write_point_shapefile(records, args.output / "pv_density_visual_grid")

    bounds = {
        "west": lon_at(MAP_X0 - 0.5),
        "east": lon_at(MAP_X1 - 0.5),
        "south": lat_at(MAP_Y1 - 0.5),
        "north": lat_at(MAP_Y0 - 0.5),
    }
    metadata = {
        "source": "Figure 12, supplied ISPRS paper",
        "method": "Printed-graticule georeferencing and colour-ramp digitisation",
        "crs": "EPSG:4326",
        "legend_maximum": LEGEND_MAX,
        "grid_spacing_degrees": GRID_STEP_DEGREES,
        "map_pixel_bounds_in_source_figure": [MAP_X0, MAP_Y0, MAP_X1, MAP_Y1],
        "geographic_bounds": bounds,
        "grid_record_count": len(records),
        "limitation": "Visual reconstruction; not the authors' original PV polygons or KDE output.",
    }
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    write_readme(args.output / "README.md", records, bounds)
    print(f"Created {len(records):,} vector samples in {args.output}")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
