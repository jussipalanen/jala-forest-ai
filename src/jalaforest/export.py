"""Export overlap results as a single WGS84 GeoParquet file for the map app."""

from __future__ import annotations

import json
import os
from pathlib import Path

import geopandas as gpd
from sqlalchemy import Engine, text

from .config import STUDY_AREA

EXPORT_SQL = """
SELECT o.stand_id,
       s.attributes->>'standnumber'          AS stand_number,
       s.attributes->>'standnumberextension' AS stand_number_extension,
       s.attributes->>'municipalitynumber'   AS municipality_number,
       s.attributes->>'maintreespecies'      AS main_tree_species,
       s.attributes->>'developmentclass'     AS development_class,
       s.attributes->>'fertilityclass'       AS fertility_class,
       (s.attributes->>'meanage')::double precision AS mean_age,
       (s.attributes->>'volume')::double precision  AS volume_m3_per_ha,
       s.source_area_ha,
       round(o.stand_area_ha::numeric, 4)::double precision      AS stand_area_ha,
       round(o.natura_overlap_ha::numeric, 4)::double precision  AS natura_overlap_ha,
       round(o.natura_overlap_pct::numeric, 2)::double precision AS natura_overlap_pct,
       array_to_string(o.natura_site_codes, ', ') AS natura_site_codes,
       array_to_string(o.natura_site_names, ', ') AS natura_site_names,
       s.source     AS stand_source,
       v.fetched_at AS stand_fetched_at,
       ST_Transform(o.geom, 4326) AS geometry
FROM stand_natura_overlap o
JOIN forest_stands s USING (stand_id)
JOIN current_source_versions v ON v.source = s.source
ORDER BY o.stand_id
"""


def export_geoparquet(engine: Engine, path: str | os.PathLike) -> gpd.GeoDataFrame:
    with engine.connect() as conn:
        gdf = gpd.read_postgis(text(EXPORT_SQL), conn, geom_col="geometry", crs="EPSG:4326")
        versions = [
            dict(row._mapping)
            for row in conn.execute(text(
                "SELECT source, run_id, fetched_at, feature_count, content_sha256, request_url "
                "FROM current_source_versions ORDER BY source"
            ))
        ]
    for v in versions:
        v["fetched_at"] = v["fetched_at"].isoformat()

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    # Provenance travels with the file as Parquet key/value metadata.
    gdf.to_parquet(tmp, index=False, schema_version="1.1.0")
    _add_metadata(tmp, {
        "jalaforest:study_area": json.dumps({"name": STUDY_AREA.name, "bbox_epsg3067": STUDY_AREA.bbox}),
        "jalaforest:sources": json.dumps(versions, ensure_ascii=False),
    })
    os.replace(tmp, out)
    return gdf


def _add_metadata(path: Path, extra: dict[str, str]) -> None:
    import pyarrow.parquet as pq

    table = pq.read_table(path)
    meta = dict(table.schema.metadata or {})
    meta.update({k.encode(): v.encode() for k, v in extra.items()})
    pq.write_table(table.replace_schema_metadata(meta), path)
