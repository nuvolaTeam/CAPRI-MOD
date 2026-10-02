"""CAPRI's endogenous GHG mitigation technologies.

Replaces a hand-transcribed table of ten EU-wide measures with CAPRI's own
technology data (dat/scen/ghgtech p_ghgMiti, via the public JRC dataset): per
member state, activity and option - 20 options, from anaerobic digestion,
feed additives and vaccines to nitrification inhibitors, precision farming and
rice-paddy management - with initial and maximum adoption shares, emissions
under each technology, and quadratic adoption costs.

ADOPTION RULE. CAPRI's objective charges, per unit of activity,
    (costParLin - revenue + pmpParLin - subsidy) * s + 0.5 (costParSqr + pmpParSqr) * s^2
for adoption share s (supply/supply_model.gms, GHG_Mit_Cost_). At carbon price
t the saving per unit is t * E0 * (1 - Q_tech / Q_noc), so the first-order
condition gives
    s* = (t * saving - a) / b,    bounded to [0, MaxShare].
The pmp terms calibrate CAPRI's observed shares to be optimal at zero price, so
s*(t = 0) should reproduce IniShare - the module's first built-in check.

In CAPRI the shares are variables INSIDE the supply model. Here they follow the
same first-order condition on the activity levels the supply model produces:
the same economics, without the feedback of mitigation costs onto activity
levels.

SAVINGS are relative to CAPRI's no-change technology (Q_tech / Q_noc), applied
to this model's own emissions per unit, so CAPRI's absolute units never enter.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
import numpy as np
import pandas as pd

#: CAPRI activity codes -> this model's activities
ACTIVITY_MAP = {"DCOH": "DCOW", "DCOL": "DCOW", "BULH": "BULL", "BULL": "BULL",
                "HEIH": "HEIF", "HEIL": "HEIF", "HEIR": "HEIF",
                "CAFF": "CALV", "CAFR": "CALV", "CAMF": "CALV", "CAMR": "CALV",
                "SCOW": "SCOW", "SOWS": "SOWS", "PIGF": "PIGS", "POUF": "BROI",
                "HENS": "LAYS", "PARI": "PARI", "cropMiti": "*crops", "OFAR": "OFOD"}
GASES = ("CH4ENT", "CH4MAN", "CH4RIC", "N2OSYN")


@dataclass
class Adoption:
    member_state: str
    activity: str
    option: str
    target: str
    share: float
    initial: float
    maximum: float
    relative_saving: float


class CapriMitigation:
    def __init__(self, table: pd.DataFrame):
        t = table.copy()
        t = t[t["target"].isin(GASES)]
        for c in ("costParLin", "costParSqr", "pmpParLin", "pmpParSqr", "revenue",
                  "subsidy", "IniShare", "MaxShare", "QEmitt"):
            if c not in t.columns:
                t[c] = np.nan
        noc = (t[t["option"] == "NOC"]
               .set_index(["member_state", "activity", "target"])["QEmitt"])
        t = t[t["option"] != "NOC"].copy()
        key = list(zip(t["member_state"], t["activity"], t["target"]))
        t["Q_noc"] = [noc.get(k, np.nan) for k in key]
        t["relative_saving"] = (1.0 - t["QEmitt"] / t["Q_noc"]).clip(lower=0.0)
        f = lambda c: t[c].fillna(0.0)
        t["a"] = f("costParLin") - f("revenue") + f("pmpParLin") - f("subsidy")
        t["b"] = f("costParSqr") + f("pmpParSqr")
        t["IniShare"] = f("IniShare")
        t["MaxShare"] = t["MaxShare"].fillna(1.0)
        self.table = t[t["relative_saving"].notna()].reset_index(drop=True)

    @classmethod
    def from_data_dir(cls, data_dir, base_year: str = "2017"):
        p = Path(data_dir) / base_year / "abatement" / "capri_ghg_mitigation.csv"
        return cls(pd.read_csv(p)) if p.exists() else None

    @staticmethod
    def share(a: float, b: float, value_per_share: float, maximum: float) -> float:
        """Optimal adoption share: marginal cost a + b*s equals the value saved."""
        if b > 1e-12:
            s = (value_per_share - a) / b
        else:                                   # linear cost: all or nothing
            s = maximum if value_per_share > a else 0.0
        return float(min(max(s, 0.0), maximum))

    def adoption(self, price: float,
                 emission_per_unit: Optional[Dict] = None) -> pd.DataFrame:
        """Adoption shares at carbon price `price` (EUR/t CO2e).

        emission_per_unit maps (member_state, activity, target) to tonnes CO2e
        per unit of activity under the current technology; without it the
        value of adoption is zero and the shares are the zero-price calibration.
        """
        rows = []
        for r in self.table.itertuples(index=False):
            e0 = 0.0
            if emission_per_unit is not None:
                e0 = float(emission_per_unit.get((r.member_state, r.activity, r.target), 0.0))
            value = price * e0 * r.relative_saving
            rows.append((r.member_state, r.activity, r.option, r.target,
                         self.share(r.a, r.b, value, r.MaxShare),
                         r.IniShare, r.MaxShare, r.relative_saving))
        return pd.DataFrame(rows, columns=["member_state", "activity", "option", "target",
                                           "share", "initial", "maximum", "relative_saving"])


# ---------------------------------------------------------------------------
# Full-portfolio abatement: CAPRI's technical potential x its price response
# ---------------------------------------------------------------------------
#: Our animal codes -> category keys in capri_mitigation_potential.csv
ANIMAL_CATEGORY = {"DCOW": "DCOW", "BULL": "BULL", "HEIF": "HEIF", "CALV": "CALV",
                   "SCOW": "SCOW", "SHEP": "SHEP", "GOAT": "SHEP", "PIGS": "PIGS",
                   "SOWS": "SOWS"}
#: Emission sources -> the table-option target gas whose price response they follow
SOURCE_GAS = {"CH4_ENT": "CH4ENT", "CH4_MAN": "CH4MAN", "N2O_MAN": "CH4MAN",
              "N2O_SOIL": "N2OSYN"}


class CapriAbatement:
    """Technological abatement from CAPRI's own mitigation portfolio.

    HOW FAR a country can go: capri_mitigation_potential.csv holds, per member
    state and source (enteric CH4 per animal category, manure CH4, manure N2O,
    soil N2O), the share of emissions CAPRI removes at FULL technical potential -
    from CAPRI's res_2_1730greendeal_refpol_endotech_all_max run against its 2030
    reference, at reference herds. It therefore covers CAPRI's whole portfolio -
    feed additives, diet, anaerobic digestion, ammonia measures - not only the
    options with published cost functions.

    HOW FAR at a given carbon price: CAPRI's own adoption rule on the options that
    do have cost functions (CapriMitigation), as a fraction of their potential,
    per gas. That fraction is applied to the full potential. ASSUMPTION, stated:
    the code-defined options (feed additives, diet, ammonia measures) follow the
    same price response as the table options for the same gas; CAPRI's costs for
    them live in its GAMS code, not in data this model holds.

    Soil N2O uses an EU-level potential (fertiliser N2O -16.7% at full potential,
    about a third of soil N2O): CAPRI's country-level aggregates are not usable as
    totals.
    """

    GWP_CH4 = 25.0                  # AR4, as the environmental module
    N2OSYN_T_CO2E_PER_HA = 0.47     # documented estimate, see price_response

    def __init__(self, potential: pd.DataFrame, options: CapriMitigation):
        self.potential = potential
        self.options = options
        self._pot = {(r.member_state, r.source, r.category): float(r.potential)
                     for r in potential.itertuples(index=False)}

    @classmethod
    def from_data_dir(cls, data_dir, base_year: str = "2017"):
        p = Path(data_dir) / base_year / "abatement" / "capri_mitigation_potential.csv"
        opts = CapriMitigation.from_data_dir(data_dir, base_year)
        if not p.exists() or opts is None:
            return None
        return cls(pd.read_csv(p), opts)

    def price_response(self, price: float, e_per_unit: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Fraction of technical potential adopted at `price`, per target gas.

        e_per_unit maps a target gas to typical tonnes CO2e per unit of activity
        (per head, per hectare) used to value a technology's saving.
        """
        e_per_unit = e_per_unit or {}
        t = self.options.table
        out = {}
        for gas in ("CH4ENT", "CH4MAN", "N2OSYN"):
            g = t[t["target"] == gas]
            if g.empty:
                out[gas] = 0.0
                continue
            got = full = got0 = 0.0
            for r in g.itertuples(index=False):
                # Value each option with ITS OWN baseline emission per unit.
                # CAPRI's no-change QEmitt is kg CH4 per head (or ha) per year:
                # dairy enteric 70.6 kg x 25 = 1.76 t CO2e, against this model's
                # own 1.68. For fertiliser N2O the unit is not given in the data,
                # so a documented per-hectare estimate is used (~100 kg N/ha,
                # IPCC 1% EF: 1.57 kg N2O = 0.47 t CO2e). An explicit e_per_unit
                # entry overrides either.
                if gas in e_per_unit:
                    e0 = float(e_per_unit[gas])
                elif gas == "N2OSYN":
                    e0 = self.N2OSYN_T_CO2E_PER_HA
                else:
                    e0 = float(r.Q_noc) * self.GWP_CH4 / 1000.0 if pd.notna(r.Q_noc) else 0.0
                s = self.options.share(r.a, r.b, price * e0 * r.relative_saving, r.MaxShare)
                s0 = self.options.share(r.a, r.b, 0.0, r.MaxShare)
                got += s * r.relative_saving
                got0 += s0 * r.relative_saving
                full += r.MaxShare * r.relative_saving
            # The potential is measured FROM CAPRI's reference, which already
            # contains the zero-price (initial) adoption; count only the increment
            # beyond it, so a zero carbon price abates nothing.
            room = full - got0
            out[gas] = max(0.0, (got - got0) / room) if room > 0 else 0.0
        return out

    def abate(self, emissions_by_source: Dict[str, float], member_state: str,
              price: Optional[float] = None,
              enteric_by_animal: Optional[Dict[str, float]] = None,
              e_per_unit: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Emission reduction per source (same units as the input).

        price=None means full technical potential (CAPRI's max run).
        """
        frac = ({g: 1.0 for g in ("CH4ENT", "CH4MAN", "N2OSYN")} if price is None
                else self.price_response(price, e_per_unit))
        ms = str(member_state)[:2]
        out = {}
        if enteric_by_animal:
            red = 0.0
            for animal, e in enteric_by_animal.items():
                cat = ANIMAL_CATEGORY.get(animal)
                pot = self._pot.get((ms, "CH4_ENT", cat), 0.0) if cat else 0.0
                red += float(e) * pot * frac["CH4ENT"]
            out["CH4_ENT"] = red
        for src in ("CH4_MAN", "N2O_MAN", "N2O_SOIL"):
            e = float(emissions_by_source.get(src, 0.0) or 0.0)
            pot = self._pot.get((ms, src, "*"), 0.0)
            out[src] = e * pot * frac[SOURCE_GAS[src]]
        return out
