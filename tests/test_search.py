import geopandas as gpd
import pytest
from pydantic import ValidationError
from synthetic import write_synthetic_stands

from jalaforest.search import SearchFilters, apply_filters, fmt_num, summarize, summary_text_fi


@pytest.fixture
def stands(tmp_path):
    return gpd.read_parquet(write_synthetic_stands(tmp_path / "s.parquet"))


def ids(gdf):
    return sorted(gdf["stand_id"])


def test_filters_reject_inverted_ranges():
    with pytest.raises(ValidationError):
        SearchFilters(min_area_ha=3, max_area_ha=2)
    with pytest.raises(ValidationError):
        SearchFilters(min_natura_pct=60, max_natura_pct=10)
    with pytest.raises(ValidationError):
        SearchFilters(min_natura_pct=120)
    with pytest.raises(ValidationError):
        SearchFilters(unknown=1)


def test_area_and_natura_filters(stands):
    assert ids(apply_filters(stands, SearchFilters())) == [1, 2, 3, 4]
    assert ids(apply_filters(stands, SearchFilters(min_area_ha=2, natura="overlaps"))) == [1]
    # Stand 4 has only a 0.005 ha sliver, so it counts as outside Natura.
    assert ids(apply_filters(stands, SearchFilters(natura="outside"))) == [2, 4]
    assert ids(apply_filters(stands, SearchFilters(min_natura_pct=100))) == [3]
    assert ids(apply_filters(stands, SearchFilters(max_area_ha=1))) == [3]


def test_summary_uses_result_numbers(stands):
    s = summarize(apply_filters(stands, SearchFilters(natura="overlaps")))
    assert (s.count, s.area_ha, s.natura_overlap_ha, s.natura_stand_count) == (2, 4.0, 2.5, 2)
    assert summary_text_fi(s) == (
        "Löytyi 2 kuviota, yhteensä 4 ha. Niistä 2 osuu Natura 2000 -alueelle; "
        "Natura-alueella on 2,5 ha (62,5 % kuvioiden pinta-alasta)."
    )


def test_zero_result_text(stands):
    s = summarize(apply_filters(stands, SearchFilters(min_area_ha=100)))
    assert s.count == 0
    assert summary_text_fi(s) == "Hakuehdoilla ei löytynyt yhtään kuviota."


def test_describe_and_number_format():
    assert SearchFilters().describe_fi() == "ei rajauksia"
    assert SearchFilters(min_area_ha=2, natura="overlaps").describe_fi() == (
        "pinta-ala vähintään 2 ha, osuu Natura 2000 -alueelle"
    )
    assert fmt_num(1234.5) == "1 234,5"
    assert fmt_num(0.01) == "0,01"
    # Regression: integer zeros were trimmed when decimals=0 (400 -> "4").
    assert fmt_num(400, 0) == "400"
    assert fmt_num(30000, 0) == "30\u00a0000"
    assert fmt_num(2.0) == "2"
