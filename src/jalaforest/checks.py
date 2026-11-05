"""Verification helpers: state fingerprint and an independent area cross-check."""

from __future__ import annotations

import hashlib

import geopandas as gpd
from shapely import STRtree, relate_pattern, union_all
from sqlalchemy import Engine, text

# Data tables that make up the end state of an import + analysis run.
# import_runs is excluded on purpose: it is an append-only log.
FINGERPRINT_QUERIES = {
    "forest_stands": "SELECT stand_id, feature_id, source, source_area_ha, attributes::text, "
                     "ST_AsEWKB(geom) FROM forest_stands ORDER BY stand_id",
    "natura_sites": "SELECT feature_id, source, site_code, site_name, site_type, attributes::text, "
                    "ST_AsEWKB(geom) FROM natura_sites ORDER BY feature_id",
    "stand_natura_overlap": "SELECT stand_id, stand_area_ha, natura_overlap_ha, natura_overlap_pct, "
                            "natura_site_codes, natura_site_names, ST_AsEWKB(geom) "
                            "FROM stand_natura_overlap ORDER BY stand_id",
}


def fingerprint(engine: Engine) -> dict[str, str]:
    """SHA-256 of each data table's full ordered content."""
    out = {}
    with engine.connect() as conn:
        for name, sql in FINGERPRINT_QUERIES.items():
            h = hashlib.sha256()
            count = 0
            for row in conn.exec_driver_sql(sql):
                h.update(repr(tuple(bytes(v) if isinstance(v, memoryview) else v for v in row)).encode())
                count += 1
            out[name] = f"{count} rows sha256={h.hexdigest()[:16]}"
    return out


def crosscheck_overlap(engine: Engine, tolerance_ha: float = 1e-6) -> dict:
    """Recompute the overlap with Shapely from the same DB inputs and compare to PostGIS."""
    with engine.connect() as conn:
        stands = gpd.read_postgis(text("SELECT stand_id, geom FROM forest_stands"), conn, geom_col="geom")
        natura = gpd.read_postgis(text("SELECT site_code, geom FROM natura_sites"), conn, geom_col="geom")
        pg = {r.stand_id: r.natura_overlap_ha for r in conn.execute(
            text("SELECT stand_id, natura_overlap_ha FROM stand_natura_overlap"))}

    tree = STRtree(natura.geometry.values)
    max_diff = 0.0
    mismatches = []
    for stand_id, geom in zip(stands.stand_id, stands.geom):
        idx = tree.query(geom)
        hits = [natura.geometry.values[i] for i in idx
                if relate_pattern(geom, natura.geometry.values[i], "2********")]
        overlap_ha = geom.intersection(union_all(hits)).area / 10000.0 if hits else 0.0
        diff = abs(overlap_ha - pg[stand_id])
        max_diff = max(max_diff, diff)
        if diff > tolerance_ha:
            mismatches.append((stand_id, overlap_ha, pg[stand_id]))
    return {"stands": len(stands), "max_abs_diff_ha": max_diff, "mismatches": mismatches}
