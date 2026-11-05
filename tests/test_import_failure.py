"""A failed or incomplete import must keep the last successful version."""

from datetime import UTC, datetime

from sqlalchemy import text

from jalaforest.config import METSAKESKUS_STANDS, STUDY_AREA
from jalaforest.importer import import_source
from jalaforest.wfs import FetchResult, WfsError


def _stand(stand_id: int, x: float) -> dict:
    ring = [[x, 7000000], [x + 100, 7000000], [x + 100, 7000100], [x, 7000100], [x, 7000000]]
    return {"type": "Feature", "id": f"stand.{stand_id}",
            "properties": {"standid": stand_id, "area": 1.0},
            "geometry": {"type": "Polygon", "coordinates": [ring]}}


def _ok(features):
    def fetch(layer, area, page_size):
        return FetchResult(layer, features, len(features), datetime.now(UTC), "synthetic://")
    return fetch


def _fail(layer, area, page_size):
    raise WfsError("v2:stand: incomplete result, received 99 of 100 features")


def _state(engine):
    with engine.connect() as conn:
        stands = conn.execute(text("SELECT stand_id FROM forest_stands ORDER BY 1")).scalars().all()
        runs = conn.execute(text("SELECT status FROM import_runs ORDER BY run_id")).scalars().all()
    return stands, runs


def test_failed_import_keeps_previous_version(engine):
    first = import_source(engine, METSAKESKUS_STANDS, "stands", STUDY_AREA, 100,
                          fetch=_ok([_stand(1, 500000), _stand(2, 500200)]))
    assert first.ok

    failed = import_source(engine, METSAKESKUS_STANDS, "stands", STUDY_AREA, 100, fetch=_fail)
    assert not failed.ok
    assert "incomplete" in failed.error

    stands, runs = _state(engine)
    assert stands == [1, 2]
    assert runs == ["success", "failed"]


def test_reimport_of_same_data_is_unchanged(engine):
    features = [_stand(1, 500000), _stand(2, 500200)]
    a = import_source(engine, METSAKESKUS_STANDS, "stands", STUDY_AREA, 100, fetch=_ok(features))
    b = import_source(engine, METSAKESKUS_STANDS, "stands", STUDY_AREA, 100,
                      fetch=_ok(list(reversed(features))))
    assert a.changed and not b.changed
    assert a.content_sha256 == b.content_sha256
    assert _state(engine)[0] == [1, 2]


def test_zero_features_is_a_successful_empty_import(engine):
    import_source(engine, METSAKESKUS_STANDS, "stands", STUDY_AREA, 100, fetch=_ok([_stand(1, 500000)]))
    empty = import_source(engine, METSAKESKUS_STANDS, "stands", STUDY_AREA, 100, fetch=_ok([]))
    assert empty.ok and empty.feature_count == 0
    stands, runs = _state(engine)
    assert stands == []
    assert runs == ["success", "success"]
