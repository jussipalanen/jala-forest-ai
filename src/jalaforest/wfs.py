"""Paged WFS 2.0 GetFeature client with completeness checks."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import requests

from .config import CRS_URN, StudyArea, WfsLayer

USER_AGENT = "jalaforest-demo/0.1"
TIMEOUT_S = 120


class WfsError(RuntimeError):
    """The WFS request failed or returned an incomplete or unexpected result."""


@dataclass(frozen=True)
class FetchResult:
    layer: WfsLayer
    features: list[dict[str, Any]]
    expected_count: int
    fetched_at: datetime
    request_url: str


def _get(session: requests.Session, url: str, params: dict[str, Any], retries: int = 3) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = session.get(url, params=params, timeout=TIMEOUT_S, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(2**attempt)
    raise WfsError(f"WFS request to {url} failed after {retries} attempts: {last_exc}") from last_exc


def _base_params(layer: WfsLayer, area: StudyArea) -> dict[str, Any]:
    return {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": layer.type_name,
        "srsName": CRS_URN,
        "bbox": area.wfs_bbox(),
    }


def count_features(session: requests.Session, layer: WfsLayer, area: StudyArea) -> int:
    params = _base_params(layer, area) | {"resultType": "hits"}
    text = _get(session, layer.url, params).text
    match = re.search(r'numberMatched="(\d+)"', text)
    if not match:
        raise WfsError(f"{layer.type_name}: hit count missing from response: {text[:300]!r}")
    return int(match.group(1))


def fetch_layer(
    layer: WfsLayer,
    area: StudyArea,
    page_size: int,
    session: requests.Session | None = None,
) -> FetchResult:
    """Fetch every feature of ``layer`` that intersects ``area``.

    Pages with ``startIndex``/``count`` in a stable ``sortBy`` order and fails
    if the total differs from the server's hit count, if a feature id repeats
    or if the response CRS is not EPSG:3067.
    """
    session = session or requests.Session()
    fetched_at = datetime.now(UTC)
    expected = count_features(session, layer, area)

    features: list[dict[str, Any]] = []
    start = 0
    request_url = ""
    while True:
        params = _base_params(layer, area) | {
            "outputFormat": "application/json",
            "sortBy": layer.sort_by,
            "count": page_size,
            "startIndex": start,
        }
        resp = _get(session, layer.url, params)
        if not request_url:
            request_url = resp.url
        try:
            data = resp.json()
        except ValueError as exc:
            raise WfsError(f"{layer.type_name}: response is not GeoJSON: {resp.text[:300]!r}") from exc

        page = data.get("features") or []
        # GeoServer omits "crs" when a page has no features; a zero result is
        # still a successful query.
        crs_name = ((data.get("crs") or {}).get("properties") or {}).get("name", "")
        if page and not crs_name.endswith("3067"):
            raise WfsError(f"{layer.type_name}: unexpected response CRS {crs_name!r}, expected EPSG:3067")

        features.extend(page)
        if len(page) < page_size:
            break
        start += page_size
        if start > expected + page_size:
            raise WfsError(f"{layer.type_name}: paging did not terminate (expected {expected} features)")

    ids = [f.get("id") for f in features]
    if None in ids or len(set(ids)) != len(ids):
        raise WfsError(f"{layer.type_name}: missing or duplicate feature ids across pages")
    if len(features) != expected:
        raise WfsError(
            f"{layer.type_name}: incomplete result, received {len(features)} of {expected} features"
        )
    return FetchResult(layer, features, expected, fetched_at, request_url)
