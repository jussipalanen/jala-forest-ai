"""WFS paging and completeness checks against a fake server (no network)."""

import pytest

from jalaforest.config import METSAKESKUS_STANDS, STUDY_AREA
from jalaforest.wfs import WfsError, fetch_layer

CRS = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::3067"}}


class FakeResponse:
    def __init__(self, url, payload=None, text=""):
        self.url, self._payload, self.text = url, payload, text

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    """Serves ``total`` features; ``drop`` ids are silently skipped, ``crs`` overrides the CRS."""

    def __init__(self, total, hits=None, drop=(), crs=CRS, unstable_order=False):
        self.ids = [i for i in range(total) if i not in drop]
        self.hits = total if hits is None else hits
        self.crs = crs
        self.unstable_order = unstable_order
        self.calls = []

    def get(self, url, params, timeout, headers):
        self.calls.append(params)
        if params.get("resultType") == "hits":
            return FakeResponse(url, text=f'<wfs:FeatureCollection numberMatched="{self.hits}" />')
        start = params["startIndex"]
        if self.unstable_order and start > 0:
            start -= 1  # server order shifted between requests: one feature repeats
        page = self.ids[start:start + params["count"]]
        feats = [{"type": "Feature", "id": f"stand.{i}", "properties": {}, "geometry": None} for i in page]
        payload = {"type": "FeatureCollection", "features": feats}
        if feats and self.crs:
            payload["crs"] = self.crs
        return FakeResponse(url, payload)


def test_fetches_all_pages_in_stable_order():
    session = FakeSession(total=250)
    result = fetch_layer(METSAKESKUS_STANDS, STUDY_AREA, 100, session=session)
    assert len(result.features) == 250
    pages = [c for c in session.calls if "startIndex" in c]
    assert [c["startIndex"] for c in pages] == [0, 100, 200]
    assert all(c["sortBy"] == "standid" and c["srsName"].endswith("3067") for c in pages)


def test_incomplete_result_is_an_error():
    with pytest.raises(WfsError, match="incomplete"):
        fetch_layer(METSAKESKUS_STANDS, STUDY_AREA, 100, session=FakeSession(total=250, drop={42}))


def test_duplicate_ids_across_pages_is_an_error():
    with pytest.raises(WfsError, match="duplicate"):
        fetch_layer(METSAKESKUS_STANDS, STUDY_AREA, 100,
                    session=FakeSession(total=250, unstable_order=True))


def test_wrong_crs_is_an_error():
    wrong = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}}
    with pytest.raises(WfsError, match="CRS"):
        fetch_layer(METSAKESKUS_STANDS, STUDY_AREA, 100, session=FakeSession(total=5, crs=wrong))


def test_zero_hits_is_success():
    result = fetch_layer(METSAKESKUS_STANDS, STUDY_AREA, 100, session=FakeSession(total=0))
    assert result.features == [] and result.expected_count == 0
