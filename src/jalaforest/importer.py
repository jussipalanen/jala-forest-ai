"""Import WFS layers into PostGIS with GeoPandas.

Each source is replaced atomically: the fetched features are written to a
staging table and swapped into the target table in the same transaction as
the import_runs row. If fetching or loading fails, the previous successful
version stays in place and a 'failed' run is recorded.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import geopandas as gpd
from shapely.geometry import shape
from sqlalchemy import Engine, text

from .config import CRS_EPSG, METSAKESKUS_STANDS, PAGE_SIZE, STUDY_AREA, SYKE_NATURA_LAYERS, StudyArea, WfsLayer
from .wfs import FetchResult, fetch_layer

Fetcher = Callable[[WfsLayer, StudyArea, int], FetchResult]


@dataclass(frozen=True)
class ImportOutcome:
    source: str
    ok: bool
    feature_count: int = 0
    content_sha256: str | None = None
    changed: bool = False
    error: str | None = None


def content_hash(features: list[dict]) -> str:
    """Order-independent hash of feature ids, properties and geometries."""
    canonical = sorted(
        json.dumps({"id": f["id"], "properties": f.get("properties"), "geometry": f.get("geometry")},
                    sort_keys=True, separators=(",", ":"))
         for f in features
    )
    return hashlib.sha256("\n".join(canonical).encode()).hexdigest()


def to_geodataframe(features: list[dict]) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "feature_id": [f["id"] for f in features],
            "attributes": [json.dumps(f.get("properties") or {}, sort_keys=True) for f in features],
        },
        geometry=[shape(f["geometry"]) for f in features],
        crs=f"EPSG:{CRS_EPSG}",
    ).rename_geometry("geom")


_GEOM_SQL = "ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))"

# psycopg cannot run several parameterised statements in one call, so each
# replacement is a (delete, insert) pair.
_REPLACE_SQL = {
    "stands": (
        "DELETE FROM forest_stands",
        f"""
        INSERT INTO forest_stands (stand_id, feature_id, source, source_area_ha, attributes, geom)
        SELECT (attributes::jsonb->>'standid')::bigint, feature_id, %(source)s,
               (attributes::jsonb->>'area')::double precision, attributes::jsonb, {_GEOM_SQL}
        FROM staging_features
        """,
    ),
    "natura": (
        "DELETE FROM natura_sites WHERE source = %(source)s",
        f"""
        INSERT INTO natura_sites (feature_id, source, site_code, site_name, site_type, attributes, geom)
        SELECT feature_id, %(source)s, attributes::jsonb->>'naturatunnus',
               attributes::jsonb->>'nimisuomi', attributes::jsonb->>'aluetyyppi',
               attributes::jsonb, {_GEOM_SQL}
        FROM staging_features
        """,
    ),
}


def _record_failure(engine: Engine, source: str, area: StudyArea, started_at: datetime, error: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO import_runs (source, bbox, started_at, status, error)
                    VALUES (:source, :bbox, :started_at, 'failed', :error)"""),
            {"source": source, "bbox": area.wfs_bbox(), "started_at": started_at, "error": error},
        )


def import_source(
    engine: Engine,
    layer: WfsLayer,
    kind: str,
    area: StudyArea = STUDY_AREA,
    page_size: int = PAGE_SIZE,
    fetch: Fetcher = fetch_layer,
) -> ImportOutcome:
    started_at = datetime.now(UTC)
    try:
        result = fetch(layer, area, page_size)
        gdf = to_geodataframe(result.features) if result.features else None
        digest = content_hash(result.features)
        with engine.begin() as conn:
            previous = conn.execute(
                text("SELECT content_sha256 FROM current_source_versions WHERE source = :s"),
                {"s": layer.source},
            ).scalar()
            conn.exec_driver_sql("DROP TABLE IF EXISTS staging_features")
            if gdf is not None:
                gdf.to_postgis("staging_features", conn, if_exists="replace", index=False)
            else:
                conn.exec_driver_sql(
                    "CREATE TABLE staging_features (feature_id text, attributes text, geom geometry)"
                )
            for statement in _REPLACE_SQL[kind]:
                conn.exec_driver_sql(statement, {"source": layer.source})
            conn.exec_driver_sql("DROP TABLE staging_features")
            conn.execute(
                text("""INSERT INTO import_runs (source, request_url, bbox, started_at, fetched_at, status,
                                                 expected_count, feature_count, content_sha256)
                        VALUES (:source, :url, :bbox, :started_at, :fetched_at, 'success',
                                :expected, :count, :sha)"""),
                {
                    "source": layer.source,
                    "url": result.request_url,
                    "bbox": area.wfs_bbox(),
                    "started_at": started_at,
                    "fetched_at": result.fetched_at,
                    "expected": result.expected_count,
                    "count": len(result.features),
                    "sha": digest,
                },
            )
        return ImportOutcome(layer.source, True, len(result.features), digest, changed=previous != digest)
    except Exception as exc:  # noqa: BLE001 - any failure must keep the previous version
        error = f"{type(exc).__name__}: {exc}"
        _record_failure(engine, layer.source, area, started_at, error)
        return ImportOutcome(layer.source, False, error=error)


def import_all(engine: Engine, area: StudyArea = STUDY_AREA, page_size: int = PAGE_SIZE,
               fetch: Fetcher = fetch_layer) -> list[ImportOutcome]:
    jobs = [(METSAKESKUS_STANDS, "stands")] + [(layer, "natura") for layer in SYKE_NATURA_LAYERS]
    return [import_source(engine, layer, kind, area, page_size, fetch) for layer, kind in jobs]
