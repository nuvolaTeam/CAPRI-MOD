"""Reporting on NUTS 2024 (capri_mod/nuts_reporting.py, capri_data/shared/capri_units_nuts2024.csv)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from capri_mod.csvio import read_csv
from capri_mod.nuts_reporting import load_mapping, to_nuts2024

ROOT = Path(__file__).resolve().parents[2]
SUPPLY = ROOT / "capri_data" / "2017" / "supply"
#: NUTS-2024 regions CAPRI has no unit for (build_general_set_structure.gms leaves them out)
NO_UNIT = {"BE10", "DE30", "DE50", "DE60", "ES63", "ES64", "FRY1", "FRY2", "FRY3", "FRY4", "FRY5", "NO0B"}


@pytest.fixture(scope="module")
def m():
    return load_mapping()


@pytest.fixture(scope="module")
def areas():
    return read_csv(SUPPLY / "base_areas.csv", index_col=0)


def test_mapping_covers_units_and_current_nuts(m):
    units = read_csv(ROOT / "capri_data" / "shared" / "regional_units.csv").region
    assert set(m.capri_unit) == set(units)
    n24 = read_csv(ROOT / "capri_data" / "sources" / "nuts" / "nuts2024.csv", dtype=str)
    countries = set(read_csv(ROOT / "capri_data" / "shared" / "regional_units.csv").country)
    eu = {c for c, lv in zip(n24.code, n24.level) if str(lv) == "2" and c[:2] in countries and not c.endswith("ZZ")}
    eu |= {n for n in m.nuts2024 if n.startswith("NO")}                    # Norway: 2021 statistical regions
    assert eu - set(m.nuts2024) == NO_UNIT - {"NO0B"}
    assert set(m.nuts2024) <= eu
    w = m.drop_duplicates(["group", "nuts2024"]).groupby("group").weight.sum()
    assert np.allclose(w, 1.0, rtol=0, atol=1e-12)


def test_known_correspondences(m):
    links = m.groupby("capri_unit").nuts2024.apply(frozenset)
    assert links["DE110000"] == {"DE11"}
    assert links["DED00000"] == {"DED2", "DED4", "DED5"}               # Saxony, split in NUTS 2013
    assert links["IT310000"] == {"ITH1", "ITH2"}                       # Bolzano, Trento
    assert links["PL120000"] == {"PL91", "PL92"}
    assert links["PL110000"] == {"PL71"}                               # renamed 2016
    assert links["FR210000"] == {"FRF2"}                               # Champagne-Ardenne, recoded 2016
    assert links["EL110000"] == {"EL51"}
    assert links["NL310000"] == links["NL330000"] == {"NL35", "NL36"}  # NUTS 2024 boundary change
    assert links["PT170000"] == {"PT1A", "PT1B"}
    assert links["DK000000"] == {"DK01", "DK02", "DK03", "DK04", "DK05"}
    assert links["HR000000"] == {"HR02", "HR03", "HR05", "HR06"}
    assert links["BL400000"] == {"LU00"}
    assert links["NO080000"] == {"NO08"}


def test_extensive_totals_kept_and_one_to_one_equal(m, areas):
    out = to_nuts2024(areas)
    assert np.allclose(out.sum(), areas.sum(), rtol=1e-12, atol=0)
    for c in ("DE", "FR", "PL", "IT", "NL", "PT", "DK"):           # national totals as well
        units = m[m.nuts2024.str[:2] == c].capri_unit.unique()
        assert np.isclose(out[out.index.str[:2] == c].sum().sum(), areas.loc[units].sum().sum(), rtol=1e-12)
    one = m.groupby("group").filter(lambda d: len(d) == 1)
    assert len(one) == 202
    for u, n in zip(one.capri_unit, one.nuts2024):
        pd.testing.assert_series_equal(out.loc[n], areas.loc[u], check_names=False)
    dk = out.loc[["DK01", "DK02", "DK03", "DK04", "DK05"], "SWHE"]
    w = m.set_index("nuts2024").loc[dk.index, "weight"]
    assert np.allclose(dk, areas.loc["DK000000", "SWHE"] * w, rtol=1e-14)


def test_intensive_is_the_mapped_ratio(m, areas):
    yields = read_csv(SUPPLY / "yields.csv", index_col=0)
    cols = [c for c in ("SWHE", "BARL", "CORN", "RAPE") if c in yields.columns and c in areas.columns]
    y, a = yields[cols].reindex(areas.index), areas[cols]
    out = to_nuts2024(y, basis=a)
    prod = to_nuts2024(y * a)
    area = to_nuts2024(a)
    ok = area > 0
    assert np.allclose(out[ok], (prod / area)[ok], rtol=1e-12, equal_nan=True)
    assert (out.notna() == ok).all().all()                         # a value where the group has area, else NaN
    nl = out.loc[["NL35", "NL36"], "SWHE"]                            # a group: both get its area-weighted yield
    u = ["NL310000", "NL330000"]
    assert np.allclose(nl, (y.loc[u, "SWHE"] * a.loc[u, "SWHE"]).sum() / a.loc[u, "SWHE"].sum(), rtol=1e-12)
    s = to_nuts2024(y["SWHE"], basis=a["SWHE"])                       # Series in, Series out
    assert isinstance(s, pd.Series) and np.allclose(s[ok.SWHE], out.SWHE[ok.SWHE], rtol=1e-14)


def test_unknown_code_refused(areas):
    with pytest.raises(KeyError):
        to_nuts2024(areas.rename(index={"DE110000": "DE11"}))
