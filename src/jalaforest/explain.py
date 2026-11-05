"""Stand table and step-by-step area calculation shown in the app's data view."""

from __future__ import annotations

import math
from dataclasses import dataclass

import geopandas as gpd
import pandas as pd

from .search import NATURA_HIT_MIN_HA, fmt_num

METHOD_FI = f"""\
**Miten pinta-alat lasketaan** (PostGIS, `src/jalaforest/sql/overlap.sql`)

1. **Kuvion pinta-ala**: `ST_Area(kuvio)` EPSG:3067-koordinaatistossa, jonka yksikkö on metri.
   Tulos on neliömetreinä; hehtaarit = m² / 10 000.
2. **Natura-päällekkäisyys**: kuviota leikkaavat Natura 2000 -alueet yhdistetään (`ST_Union`),
   leikataan kuviolla (`ST_Intersection`) ja yhteisen osan pinta-ala lasketaan. Päällekkäiset
   Natura-alueet lasketaan vain kerran, eikä pelkkä rajan kosketus kerrytä pinta-alaa.
3. **Natura-osuus** = päällekkäisyys / kuvion pinta-ala × 100 %.
4. **Natura-osuma**, kun päällekkäisyys on vähintään {fmt_num(NATURA_HIT_MIN_HA)} ha. Pienemmät osuudet
   ovat rajojen digitointieroista syntyviä suikaleita.
"""

COLUMNS = {
    "kuvio": "Kuvio",
    "stand_id": "Kuvion ID",
    "area": "Pinta-ala (ha)",
    "source_area": "Metsäkeskuksen pinta-ala (ha)",
    "natura_ha": "Natura (ha)",
    "natura_pct": "Natura-osuus (%)",
    "site": "Natura-alue",
    "hit": "Hakuun osuva",
}


def stand_label(number, extension) -> str:
    number = "–" if number is None or (isinstance(number, float) and math.isnan(number)) else str(number)
    return f"{number}.{extension}" if isinstance(extension, str) and extension else number


def stand_table(stands: gpd.GeoDataFrame, hit_ids: set) -> pd.DataFrame:
    """All stands with their computed areas, largest first."""
    source_area = stands["source_area_ha"] if "source_area_ha" in stands else pd.Series(float("nan"), stands.index)
    table = pd.DataFrame({
        COLUMNS["kuvio"]: [stand_label(n, e) for n, e in
                           zip(stands["stand_number"], stands["stand_number_extension"], strict=True)],
        COLUMNS["stand_id"]: stands["stand_id"].astype("int64"),
        COLUMNS["area"]: stands["stand_area_ha"],
        COLUMNS["source_area"]: source_area,
        COLUMNS["natura_ha"]: stands["natura_overlap_ha"],
        COLUMNS["natura_pct"]: stands["natura_overlap_pct"],
        COLUMNS["site"]: stands["natura_site_names"].where(stands["natura_site_names"] != "", "–"),
        COLUMNS["hit"]: stands["stand_id"].isin(hit_ids),
    })
    return table.sort_values(COLUMNS["area"], ascending=False).reset_index(drop=True)


@dataclass(frozen=True)
class Step:
    title: str
    formula: str
    result: str


def calculation_steps_fi(row: pd.Series) -> list[Step]:
    """The calculation for one stand, using the numbers stored in the export."""
    area_ha = float(row[COLUMNS["area"]])
    natura_ha = float(row[COLUMNS["natura_ha"]])
    pct = float(row[COLUMNS["natura_pct"]])
    area_m2 = round(area_ha * 10_000)
    natura_m2 = round(natura_ha * 10_000)
    hit = natura_ha >= NATURA_HIT_MIN_HA

    steps = [
        Step("1. Kuvion pinta-ala", f"ST_Area(kuvio) = {fmt_num(area_m2, 0)} m² → {fmt_num(area_m2, 0)} / 10 000",
             f"{fmt_num(area_ha, 4)} ha"),
        Step("2. Natura-päällekkäisyys",
             f"ST_Area(kuvio ∩ ∪ Natura-alueet) = {fmt_num(natura_m2, 0)} m² → {fmt_num(natura_m2, 0)} / 10 000",
             f"{fmt_num(natura_ha, 4)} ha"),
        Step("3. Natura-osuus", f"{fmt_num(natura_ha, 4)} ha / {fmt_num(area_ha, 4)} ha × 100", f"{fmt_num(pct)} %"),
        Step("4. Natura-osuma",
             f"{fmt_num(natura_ha, 4)} ha {'≥' if hit else '<'} {fmt_num(NATURA_HIT_MIN_HA)} ha",
             "kyllä" if hit else "ei"),
    ]
    source = row.get(COLUMNS["source_area"])
    if source is not None and not (isinstance(source, float) and math.isnan(source)):
        diff = abs(area_ha - float(source))
        steps.append(Step("Vertailu lähteeseen",
                          f"Metsäkeskuksen ilmoittama pinta-ala {fmt_num(float(source), 4)} ha",
                          f"ero {fmt_num(diff, 4)} ha"))
    return steps
