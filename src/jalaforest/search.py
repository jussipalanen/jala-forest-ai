"""Search filters over the exported stands, and summaries built from the results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import geopandas as gpd
from pydantic import BaseModel, ConfigDict, Field, model_validator

# A stand counts as "on a Natura 2000 site" from this overlap upwards. Smaller
# overlaps are boundary-digitising slivers (smallest real one: 1.18 m²).
NATURA_HIT_MIN_HA = 0.01

NaturaRule = Literal["any", "overlaps", "outside"]


class SearchFilters(BaseModel):
    """Validated search criteria. Unset bounds mean no limit; bounds are inclusive."""

    model_config = ConfigDict(extra="forbid")

    min_area_ha: float | None = Field(None, ge=0, description="Stand area at least this many hectares.")
    max_area_ha: float | None = Field(None, ge=0, description="Stand area at most this many hectares.")
    natura: NaturaRule = Field(
        "any",
        description="'overlaps': stand overlaps a Natura 2000 site; 'outside': it does not; 'any': no condition.",
    )
    min_natura_pct: float | None = Field(
        None, ge=0, le=100, description="Natura 2000 share of the stand area at least this percent."
    )
    max_natura_pct: float | None = Field(
        None, ge=0, le=100, description="Natura 2000 share of the stand area at most this percent."
    )

    @model_validator(mode="after")
    def _check_ranges(self) -> SearchFilters:
        if self.min_area_ha is not None and self.max_area_ha is not None and self.min_area_ha > self.max_area_ha:
            raise ValueError("min_area_ha must not exceed max_area_ha")
        if (self.min_natura_pct is not None and self.max_natura_pct is not None
                and self.min_natura_pct > self.max_natura_pct):
            raise ValueError("min_natura_pct must not exceed max_natura_pct")
        return self

    def is_empty(self) -> bool:
        return self == SearchFilters()

    def describe_fi(self) -> str:
        parts = []
        if self.min_area_ha is not None and self.max_area_ha is not None:
            parts.append(f"pinta-ala {fmt_num(self.min_area_ha)}–{fmt_num(self.max_area_ha)} ha")
        elif self.min_area_ha is not None:
            parts.append(f"pinta-ala vähintään {fmt_num(self.min_area_ha)} ha")
        elif self.max_area_ha is not None:
            parts.append(f"pinta-ala enintään {fmt_num(self.max_area_ha)} ha")
        if self.natura == "overlaps":
            parts.append("osuu Natura 2000 -alueelle")
        elif self.natura == "outside":
            parts.append("ei osu Natura 2000 -alueelle")
        if self.min_natura_pct is not None and self.max_natura_pct is not None:
            parts.append(f"Natura-osuus {fmt_num(self.min_natura_pct)}–{fmt_num(self.max_natura_pct)} %")
        elif self.min_natura_pct is not None:
            parts.append(f"Natura-osuus vähintään {fmt_num(self.min_natura_pct)} %")
        elif self.max_natura_pct is not None:
            parts.append(f"Natura-osuus enintään {fmt_num(self.max_natura_pct)} %")
        return ", ".join(parts) if parts else "ei rajauksia"


def apply_filters(stands: gpd.GeoDataFrame, f: SearchFilters) -> gpd.GeoDataFrame:
    mask = stands["stand_area_ha"].notna()
    if f.min_area_ha is not None:
        mask &= stands["stand_area_ha"] >= f.min_area_ha
    if f.max_area_ha is not None:
        mask &= stands["stand_area_ha"] <= f.max_area_ha
    on_natura = stands["natura_overlap_ha"] >= NATURA_HIT_MIN_HA
    if f.natura == "overlaps":
        mask &= on_natura
    elif f.natura == "outside":
        mask &= ~on_natura
    if f.min_natura_pct is not None:
        mask &= stands["natura_overlap_pct"] >= f.min_natura_pct
    if f.max_natura_pct is not None:
        mask &= stands["natura_overlap_pct"] <= f.max_natura_pct
    return stands[mask]


@dataclass(frozen=True)
class SearchSummary:
    count: int
    area_ha: float
    natura_overlap_ha: float
    natura_stand_count: int


def summarize(result: gpd.GeoDataFrame) -> SearchSummary:
    return SearchSummary(
        count=len(result),
        area_ha=float(result["stand_area_ha"].sum()),
        natura_overlap_ha=float(result["natura_overlap_ha"].sum()),
        natura_stand_count=int((result["natura_overlap_ha"] >= NATURA_HIT_MIN_HA).sum()),
    )


def summary_text_fi(s: SearchSummary) -> str:
    """Finnish summary built only from the search's own numbers."""
    if s.count == 0:
        return "Hakuehdoilla ei löytynyt yhtään kuviota."
    noun = "kuvio" if s.count == 1 else "kuviota"
    text = f"Löytyi {s.count} {noun}, yhteensä {fmt_num(s.area_ha)} ha."
    if s.natura_stand_count:
        pct = 100.0 * s.natura_overlap_ha / s.area_ha if s.area_ha else 0.0
        text += (f" Niistä {s.natura_stand_count} osuu Natura 2000 -alueelle; Natura-alueella on "
                 f"{fmt_num(s.natura_overlap_ha)} ha ({fmt_num(pct)} % kuvioiden pinta-alasta).")
    else:
        text += " Yksikään niistä ei osu Natura 2000 -alueelle."
    return text


def fmt_num(value: float, decimals: int = 2) -> str:
    """Finnish number format: decimal comma, trailing zeros trimmed."""
    text = f"{value:,.{decimals}f}"
    if "." in text:  # trim decimals only: 400 must not become "4"
        text = text.rstrip("0").rstrip(".")
    return text.replace(",", " ").replace(".", ",")
