"""The base year is a parameter of the run (KNOWN_ISSUES K52f, 2 November 2026): no reader of the model fixes 2017. A
base year without a data folder stops with an error naming the folder and the years that have one; a data folder of
another year, laid out as the 2017 one, loads the same data."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "capri_data"


def test_a_base_year_without_data_stops_naming_the_years_with_data():
    from capri_mod.model import CAPRIModel
    with pytest.raises(FileNotFoundError, match=r"base year 2019: no data folder .*2019.*base years with data.*2017"):
        CAPRIModel(data_dir=str(DATA), base_year="2019", verbose=False)


def _mirror(tmp: Path, year: str) -> Path:
    """A data directory whose <year> folder holds the 2017 files, the base year in their names written as <year>
    (links, not copies); shared, codes and sources linked as they are."""
    for d in DATA.iterdir():
        if d.is_dir() and d.name != "2017":
            os.symlink(d, tmp / d.name)
    for p in (DATA / "2017").rglob("*"):
        if p.is_file():
            q = tmp / year / p.relative_to(DATA / "2017")
            q = q.with_name(q.name.replace("_2017", f"_{year}"))
            q.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(p, q)
    return tmp


def test_another_base_year_loads_its_own_folder(tmp_path):
    """The 2017 data under the name 2018 (folder and file names) load as the 2017 data do: every reader of
    load_all_data follows the base year, none reads capri_data/2017 or a _2017 name."""
    from capri_mod.data import inputs as I
    from capri_mod.data.loaders import load_all_data
    root = _mirror(tmp_path, "2018")
    old = I.current()
    try:
        I.use(I.RunInputs(DATA, "2017"))
        a = load_all_data(DATA, base_year="2017")
        I.use(I.RunInputs(root, "2018"))
        b = load_all_data(root, base_year="2018")
    finally:
        I.use(old)
    # the tables keyed by year carry the base year's key
    assert set(a["land_rents"]) == {2017, 2030} and set(b["land_rents"]) == {2018, 2030}
    assert a["land_rents"][2017] == b["land_rents"][2018]
    assert set(a["pmp_recipe"]) == {2017, 2030} and set(b["pmp_recipe"]) == {2018, 2030}
    assert set(a) == set(b)
    for k in a:
        if k in ("land_rents", "pmp_recipe"):
            continue
        x, y = a[k], b[k]
        if isinstance(x, (pd.DataFrame, pd.Series)):
            assert x.equals(y), k
        elif x is None or isinstance(x, (int, float, str, bool)):
            assert x == y, k
        else:
            assert type(x) is type(y), k


def test_the_market_and_supply_tables_follow_the_base_year(tmp_path):
    """The market's yearly files and the supply's young-animal table are read under the base year's name."""
    from capri_mod.data import inputs as I
    from capri_mod.market.inputs import MarketInputs
    root = _mirror(tmp_path, "2018")
    m = MarketInputs(root, "2018")
    assert m.base_year == "2018" and m.exists("bilateral_flows_2018.csv") and not m.exists("bilateral_flows_2017.csv")
    old = I.current()
    try:
        I.use(I.RunInputs(root, "2018"))
        assert I.base_year() == "2018" and I.market_year({}) == 2018 and I.market_year({"market_year": 2030}) == 2030
        from capri_mod.supply.supply_module import young_animal_table
        assert young_animal_table()
    finally:
        I.use(old)
