r"""The year data's containers and sets (Data, OSet, YearSets) (capmod/load_base_data_and_trends.gms; moved from
capri_mod/projection/equations/load_base_data_and_trends.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass

from capri_mod.data.definitions import capri_pairs, capri_set




class Data:
    """CAPRI's DATA(region, column, row, position) as {(position, column, row): {region: value}}. A zero value is an
    absent cell, as in GAMS."""

    def __init__(self):
        self.c = {}

    def get(self, r, c, w, t):
        d = self.c.get((t, c, w))
        return d.get(r, 0.0) if d else 0.0

    def set(self, r, c, w, t, v):
        if v == 0 or v is None:
            d = self.c.get((t, c, w))
            if d is not None:
                d.pop(r, None)
                if not d:
                    del self.c[(t, c, w)]
        else:
            self.c.setdefault((t, c, w), {})[r] = float(v)

    def at(self, c, w, t):
        """{region: value} of one column and row at one position."""
        return self.c.get((t, c, w), {})

    def keys(self, t):
        """The (column, row) pairs with a cell at position t."""
        return [(c, w) for (tt, c, w) in self.c if tt == t]


class OSet(tuple):
    """A CAPRI set: its elements in CAPRI's order, so that the loops and sums over it run in GAMS's order (a sum's last
    digits depend on it), with a set's membership test, intersection, union and difference."""

    def __new__(cls, items=()):
        t = super().__new__(cls, dict.fromkeys(items))
        t._m = frozenset(t)
        return t

    def __contains__(self, x):
        return x in self._m

    def __and__(self, other):
        return OSet(x for x in self if x in other)

    def __or__(self, other):
        return OSet(list(self) + [x for x in other if x not in self._m])

    def __sub__(self, other):
        return OSet(x for x in self if x not in other)


@dataclass
class YearSets:
    """CAPRI's sets the statements use (sim_ini_21730's sets, capri_data/codes/capri), in CAPRI's order (OSet)."""
    RS: OSet
    RU: OSet
    MS: OSet
    MSALL: OSet
    MAP_RR: OSet          # {(member state, region)}
    R_RAGG: OSet          # {(region, member state)}
    PACT: OSet
    MPACT: OSet
    MAACT: OSet
    AACT: OSet
    CACT: OSet
    DACT: OSet
    SplitActs: OSet
    DACT_TO_PACT: OSet    # {(DACT, split activity)}
    FEED: OSet
    FEED_TRD: OSet
    FODDI: OSet
    FODDO: OSet
    FODDIO: OSet
    FEED_TO_O: OSet       # {(feed, output)}
    RESIMP: OSet
    PACT_TO_IO: OSet      # {(activity, row)}
    PACT_TO_I: OSet
    PACT_TO_O: OSet
    FIX_YAI: OSet
    FIX_YAO: OSet
    IYANI: OSet
    OYANI: OSet
    OIYANI: OSet
    IO: OSet
    IOP: OSet
    O: OSet
    FOUT: OSet
    ROWS: OSet
    COLS: OSet
    ColsRead: OSet
    RowsRead: OSet
    losfItem: OSet
    REQSR_M: OSet
    REQSC: OSet
    OSECO: OSet
    RSET: OSet
    GASAGG: OSet
    GAS_EMIS: OSet
    GHGSDEL_ROWS: OSet
    MAPP: OSet
    SCEN: OSet
    ILAB: OSet
    setfPact: OSet
    arbact: OSet
    FNUT: OSet
    RMS: OSet
    XX: OSet
    Seco_BioF: OSet
    XXBIOF: OSet
    Stock_to_fuel: OSet        # {(feedstock, biofuel)}
    Stock_to_by: OSet          # {(feedstock, by-product)}
    CAK: OSet
    SED: OSet
    SED_TO_CAK: OSet           # {(oilseed, cake)}
    MLK: OSet
    FATSPROT: OSet
    PACT_TO_Y: OSet            # {(activity, its main output)}

    @classmethod
    def from_codes(cls):
        def s(n):
            return OSet(capri_set(n))

        def p(n):
            return OSet(tuple(x[:2]) for x in capri_pairs(n))
        names = {f: f for f in cls.__dataclass_fields__}
        names.update(arbact="arbAct", Seco_BioF="SECO_BIOF", XXBIOF="XXBiof", Stock_to_fuel="STOCK_TO_FUEL",
                     Stock_to_by="STOCK_TO_BY")
        pairs = {"MAP_RR", "R_RAGG", "DACT_TO_PACT", "FEED_TO_O", "PACT_TO_IO", "PACT_TO_I", "PACT_TO_O",
                 "Stock_to_fuel", "Stock_to_by", "SED_TO_CAK", "PACT_TO_Y"}
        return cls(**{f: (p(n) if f in pairs else s(n)) for f, n in names.items()})
