"""Results on CAPRI's regional units reported on the current NUTS-2 regions (NUTS 2024).

The model runs on CAPRI's 221 regional units (capri_data/shared/regional_units.csv). For reporting on current NUTS,
capri_data/shared/capri_units_nuts2024.csv (tools/build/build_nuts2024_reporting.py) links each unit to the NUTS-2024
regions covering its territory; linked units and regions form groups, and each region of a group carries a weight, its
share of the group's utilised agricultural area (Eurostat ef_lus_main). 202 of the 217 groups are one unit to one region,
where the report is the unit's own value.

Where a group has several regions (a member state without regional detail such as DK000000 or SI000000, a CAPRI unit
that NUTS later split such as DED00000 or PL120000, or a boundary change such as NL31/NL33 -> NL35/NL36), the regional
values are an area-weighted distribution of the group's result, not model results of their own: every region of the
group gets the group's yields, prices and intensities.

    to_nuts2024(levels)                        extensive values (ha, heads, t, EUR, kt CO2-eq): split by the weights
    to_nuts2024(yields, basis=areas)           intensive values (per ha, per head, prices): basis-weighted means
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from capri_mod.csvio import read_csv

_MAP = Path(__file__).resolve().parents[1] / "capri_data" / "shared" / "capri_units_nuts2024.csv"


def load_mapping(path: str | Path | None = None) -> pd.DataFrame:
    """The unit -> NUTS-2024 table: capri_unit, nuts2024, group, uaa_ha, weight."""
    return read_csv(path or _MAP)


def _groups(m: pd.DataFrame):
    units = m.groupby("group").capri_unit.apply(lambda s: sorted(set(s)))
    regions = m.drop_duplicates(["group", "nuts2024"]).set_index("nuts2024")[["group", "weight"]]
    return units, regions


def _extensive(frame: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    units, regions = _groups(m)
    unknown = sorted(set(frame.index) - set(m.capri_unit))
    if unknown:
        raise KeyError(f"not CAPRI regional units of the mapping: {unknown[:5]}")
    by_group = pd.DataFrame({g: frame.reindex(us).sum(min_count=1) for g, us in units.items()}).T
    out = by_group.reindex(regions.group.to_numpy()).mul(regions.weight.to_numpy(), axis=0)
    out.index = regions.index
    present = set(frame.index)
    keep = [any(u in present for u in units[g]) for g in regions.group]      # groups none of whose units is in frame
    return out[keep].sort_index()


def to_nuts2024(values: pd.DataFrame | pd.Series, basis: pd.DataFrame | pd.Series | None = None,
                mapping: pd.DataFrame | None = None) -> pd.DataFrame | pd.Series:
    """Unit-indexed values -> NUTS-2024-indexed values.

    values: rows are CAPRI units (DE110000, DK000000, ...), columns are variables (a Series is one variable).
    basis: None for extensive values (summed over the group's units, then split by the regions' UAA shares, so totals
        are kept). For intensive values the quantity they are per (the area for a yield, the herd for a yield per head,
        the production for a price), with the same rows and the same columns or a single column: each region gets the
        group's basis-weighted mean, sum(values * basis) / sum(basis), i.e. the ratio recomputed from mapped totals.
    Units missing from values contribute nothing; NaN stays NaN unless another unit of the group has a value.
    """
    m = load_mapping() if mapping is None else mapping
    series = isinstance(values, pd.Series)
    v = values.to_frame() if series else values
    if basis is None:
        out = _extensive(v, m)
    else:
        b = basis.to_frame() if isinstance(basis, pd.Series) else basis
        if b.shape[1] == 1 and v.shape[1] > 1:
            b = pd.DataFrame({c: b.iloc[:, 0] for c in v.columns})
        else:
            b = b.set_axis(v.columns, axis=1) if b.shape[1] == v.shape[1] and series else b
        b = b.reindex(index=v.index, columns=v.columns)
        num = _extensive(v * b.where(v.notna()), m)
        den = _extensive(b.where(v.notna()), m)
        out = num / den.where(den != 0)
    return out.iloc[:, 0].rename(values.name) if series else out
