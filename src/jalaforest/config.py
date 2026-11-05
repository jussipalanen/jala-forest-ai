"""Project configuration: study area, WFS sources and database connection.

Layer names and CRS were verified against the services' GetCapabilities
documents (2026-11-05):

* Metsäkeskus ``v2:stand`` at avoin.metsakeskus.fi/rajapinnat/v2/stand/ows,
  DefaultCRS EPSG:3067, ImplementsResultPaging=TRUE, CountDefault=10000.
* Syke ``inspire_ps:PS.ProtectedSites{SpecialAreaOfConservation,
  SpecialProtectionArea,ProposedSiteOfCommunityImportance}`` at
  paikkatiedot.ymparisto.fi/geoserver/inspire_ps/wfs, DefaultCRS EPSG:3067,
  ImplementsResultPaging=TRUE. Together these three layers form the Natura
  2000 network (SAC, SPA and SCI sites).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

CRS_URN = "urn:ogc:def:crs:EPSG::3067"
CRS_EPSG = 3067


@dataclass(frozen=True)
class StudyArea:
    name: str
    # (min_x, min_y, max_x, max_y) in EPSG:3067 metres.
    bbox: tuple[float, float, float, float]

    def wfs_bbox(self) -> str:
        return ",".join(str(v) for v in self.bbox) + f",{CRS_URN}"


# Noljakka, Joensuu: contains the Natura 2000 site "Noljakanmäen alue"
# (FI0700107) and the surrounding forest stands.
STUDY_AREA = StudyArea(
    name="Joensuu, Noljakka",
    bbox=(636500.0, 6944800.0, 639500.0, 6947200.0),
)


@dataclass(frozen=True)
class WfsLayer:
    source: str  # stable source key stored with each import run
    url: str
    type_name: str
    sort_by: str  # attribute used for stable paging order


METSAKESKUS_STANDS = WfsLayer(
    source="metsakeskus:v2:stand",
    url="https://avoin.metsakeskus.fi/rajapinnat/v2/stand/ows",
    type_name="v2:stand",
    sort_by="standid",
)

_SYKE_URL = "https://paikkatiedot.ymparisto.fi/geoserver/inspire_ps/wfs"
SYKE_NATURA_LAYERS = tuple(
    WfsLayer(
        source=f"syke:inspire_ps:PS.ProtectedSites{name}",
        url=_SYKE_URL,
        type_name=f"inspire_ps:PS.ProtectedSites{name}",
        sort_by="objectid",
    )
    for name in (
        "SpecialAreaOfConservation",
        "SpecialProtectionArea",
        "ProposedSiteOfCommunityImportance",
    )
)

PAGE_SIZE = int(os.environ.get("WFS_PAGE_SIZE", "100"))

LOCAL_DATABASE_URL = (
    "postgresql+psycopg://jalaforest:jalaforest@localhost:"
    f"{os.environ.get('POSTGIS_PORT', '5433')}/jalaforest"
)


def normalize_database_url(url: str) -> str:
    """Accept plain ``postgres://`` / ``postgresql://`` URLs (as Neon shows them) for psycopg 3."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def describe_database_url(url: str) -> str:
    """Host and database for log output, without the password."""
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    return f"{parts.hostname}:{parts.port or 5432}/{parts.path.lstrip('/')}"


def is_local_database_url(url: str) -> bool:
    from urllib.parse import urlsplit

    return urlsplit(url).hostname in {"localhost", "127.0.0.1", "::1", "postgis"}


DATABASE_URL = normalize_database_url(os.environ.get("DATABASE_URL", LOCAL_DATABASE_URL))

EXPORT_PATH = os.environ.get("EXPORT_PATH", "data/export/stand_natura_overlap.parquet")
