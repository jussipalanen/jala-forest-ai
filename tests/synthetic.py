"""Small synthetic GeoParquet export shared by the app and end-to-end tests."""

from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

# stand_id, area_ha, natura_overlap_ha
ROWS = [
    (1, 3.0, 1.5),    # large, on Natura: the only hit for "> 2 ha and on Natura"
    (2, 2.5, 0.0),    # large, outside Natura
    (3, 1.0, 1.0),    # small, fully on Natura
    (4, 4.0, 0.005),  # boundary sliver below the Natura hit threshold
]


def write_synthetic_stands(path: Path) -> Path:
    gdf = gpd.GeoDataFrame(
        {
            "stand_id": [r[0] for r in ROWS],
            "stand_number": [str(r[0]) for r in ROWS],
            "stand_number_extension": [None] * len(ROWS),
            "mean_age": [50.0] * len(ROWS),
            "volume_m3_per_ha": [200.0] * len(ROWS),
            "stand_area_ha": [r[1] for r in ROWS],
            "natura_overlap_ha": [r[2] for r in ROWS],
            "natura_overlap_pct": [100 * r[2] / r[1] for r in ROWS],
            "natura_site_codes": ["FI0000001" if r[2] else "" for r in ROWS],
            "natura_site_names": ["Testialue" if r[2] else "" for r in ROWS],
        },
        geometry=[box(29.70 + i * 0.01, 62.60, 29.705 + i * 0.01, 62.605) for i in range(len(ROWS))],
        crs="EPSG:4326",
    )
    gdf.to_parquet(path)
    return path
