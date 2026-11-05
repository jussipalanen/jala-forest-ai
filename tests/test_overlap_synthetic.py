"""Synthetic check data for the PostGIS overlap calculation (EPSG:3067 metres)."""

import pytest
from sqlalchemy import text

from jalaforest.db import compute_overlap

X0, Y0 = 500000, 7000000


def box(x1, y1, x2, y2) -> str:
    return (f"SRID=3067;MULTIPOLYGON((({X0 + x1} {Y0 + y1},{X0 + x2} {Y0 + y1},"
            f"{X0 + x2} {Y0 + y2},{X0 + x1} {Y0 + y2},{X0 + x1} {Y0 + y1})))")


# Every stand is 100 m x 100 m = 1 ha.
STANDS = {
    1: box(0, 0, 100, 100),        # two overlapping Natura sites cover x 25..100
    2: box(200, 0, 300, 100),      # touches Natura along an edge only
    3: box(500, 0, 600, 100),      # touches Natura at a single corner only
    4: box(1000, 0, 1100, 100),    # inside a site that is listed as both SAC and SPA
    5: box(2000, 0, 2100, 100),    # no Natura nearby
}

NATURA = [
    ("A", "sac", box(50, 0, 150, 100)),      # covers stand 1 x 50..100 (0.5 ha)
    ("B", "sac", box(25, -10, 75, 110)),     # covers stand 1 x 25..75 (0.5 ha), overlaps A
    ("C", "sac", box(300, 0, 400, 100)),     # shares stand 2's east edge
    ("D", "sac", box(600, 100, 700, 200)),   # shares stand 3's NE corner
    ("E", "sac", box(900, -100, 1200, 200)),
    ("E", "spa", box(900, -100, 1200, 200)), # same site again in the SPA layer
]


@pytest.fixture
def results(engine):
    with engine.begin() as conn:
        for stand_id, wkt in STANDS.items():
            conn.execute(
                text("INSERT INTO forest_stands (stand_id, feature_id, source, attributes, geom) "
                     "VALUES (:id, :fid, 'synthetic', '{}', ST_GeomFromEWKT(:g))"),
                {"id": stand_id, "fid": f"stand.{stand_id}", "g": wkt},
            )
        for i, (code, layer, wkt) in enumerate(NATURA):
            conn.execute(
                text("INSERT INTO natura_sites (feature_id, source, site_code, attributes, geom) "
                     "VALUES (:fid, :src, :code, '{}', ST_GeomFromEWKT(:g))"),
                {"fid": f"natura.{i}", "src": f"synthetic:{layer}", "code": code, "g": wkt},
            )
        compute_overlap(conn)
        rows = conn.execute(text("SELECT * FROM stand_natura_overlap")).mappings().all()
    return {r["stand_id"]: r for r in rows}


def test_every_stand_has_a_result(results):
    assert set(results) == set(STANDS)
    for r in results.values():
        assert r["stand_area_ha"] == pytest.approx(1.0)


def test_overlapping_natura_sites_are_counted_once(results):
    r = results[1]
    # A alone 0.5 ha, B alone 0.5 ha, union inside the stand is x 25..100.
    assert r["natura_overlap_ha"] == pytest.approx(0.75)
    assert r["natura_overlap_pct"] == pytest.approx(75.0)
    assert r["natura_site_codes"] == ["A", "B"]


def test_edge_touch_is_not_an_overlap(results):
    r = results[2]
    assert r["natura_overlap_ha"] == 0
    assert r["natura_overlap_pct"] == 0
    assert r["natura_site_codes"] == []


def test_corner_touch_is_not_an_overlap(results):
    r = results[3]
    assert r["natura_overlap_ha"] == 0
    assert r["natura_site_codes"] == []


def test_site_in_two_layers_does_not_exceed_stand_area(results):
    r = results[4]
    assert r["natura_overlap_ha"] == pytest.approx(1.0)
    assert r["natura_overlap_pct"] == pytest.approx(100.0)
    assert r["natura_site_codes"] == ["E"]


def test_stand_without_natura_is_zero(results):
    r = results[5]
    assert r["natura_overlap_ha"] == 0
    assert r["natura_site_codes"] == []
