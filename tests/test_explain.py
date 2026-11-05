import geopandas as gpd
import pytest
from synthetic import write_synthetic_stands

from jalaforest.explain import COLUMNS, calculation_steps_fi, stand_label, stand_table


@pytest.fixture
def stands(tmp_path):
    return gpd.read_parquet(write_synthetic_stands(tmp_path / "s.parquet"))


def test_table_lists_all_stands_largest_first(stands):
    table = stand_table(stands, hit_ids={1})
    assert len(table) == 4
    assert table[COLUMNS["area"]].tolist() == [4.0, 3.0, 2.5, 1.0]
    assert table.loc[table[COLUMNS["hit"]], COLUMNS["stand_id"]].tolist() == [1]
    assert table.loc[table[COLUMNS["stand_id"]] == 2, COLUMNS["site"]].item() == "–"


def test_calculation_steps_for_a_natura_stand(stands):
    row = stand_table(stands, hit_ids=set()).set_index(COLUMNS["stand_id"], drop=False).loc[1]
    steps = calculation_steps_fi(row)
    assert [s.result for s in steps] == ["3 ha", "1,5 ha", "50 %", "kyllä", "ero 0,001 ha"]
    assert steps[0].formula == "ST_Area(kuvio) = 30 000 m² → 30 000 / 10 000"
    assert steps[2].formula == "1,5 ha / 3 ha × 100"


def test_sliver_is_not_a_natura_hit(stands):
    row = stand_table(stands, hit_ids=set()).set_index(COLUMNS["stand_id"], drop=False).loc[4]
    steps = calculation_steps_fi(row)
    assert steps[1].result == "0,005 ha"
    assert steps[3].formula == "0,005 ha < 0,01 ha" and steps[3].result == "ei"


def test_stand_label():
    assert stand_label("12", "3") == "12.3"
    assert stand_label("12", None) == "12"
    assert stand_label(None, None) == "–"
