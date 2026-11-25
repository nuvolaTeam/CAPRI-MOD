"""The inputs of the methane per head (capri_mod/environmental/methane_per_head.py) from CAPRI's files, for a year's
data and its requirement call:

- CAPRI's raw methane tables (capri_data/sources/intermediate/envind: tools/build/build_gascoeff_tables.py), its
  digestibility table with the DEF_PRD fill and its grass N fixation (tools/lib/_capri_digest.py);
- MITERRA's tables (capri_data/2017/abatement/ammonia: RCEmissions, bNumAniRAINS, ControlStrategies, reducEmHouse,
  reducEmStorage) for the shares and CH4 losses of a MITERRA scenario year (envind/ammo.gms with %storgrazInv% off:
  capmod/create_sim_ini_gdx.gms l. 176-186 gives 2020 for a simulation year after 2010, envind/Miterra/
  scenario_settings.gms l. 90 gives 2000 in CAPREG);
- CAPRI's sets (capri_data/codes/capri).

    from methane_inputs import methane_inputs
    m = methane_inputs(DATA, regions, ms, p_technFact, st, scen_year=2020)
"""
from __future__ import annotations

import csv
from pathlib import Path

from capri_mod.data.definitions import capri_pairs, capri_set
from capri_mod.environmental import methane_per_head as mph

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / "capri_data" / "sources" / "intermediate" / "envind"
AMMO = ROOT / "capri_data" / "2017" / "abatement" / "ammonia"


def _src(name: str, keys: tuple) -> dict:
    from _sources_io import source_records
    return {tuple(r[k] for k in keys): float(r["value"]) for r in source_records(ENV / f"{name}.parquet")}


def raw_tables() -> dict:
    """CAPRI's raw methane tables as gascoeff.gms loads them."""
    return {"EMISCALC0": _src("capri_emiscalc0", ("region", "act", "tech", "item")),
            "p_tier1EmFactManMgt0": _src("capri_tier1_manure_ef", ("region", "act", "tech", "clim")),
            "p_shareClimZone0": _src("capri_share_clim_zone", ("region", "clim")),
            "p_manureMgtShare0": _src("capri_manure_mgt_share", ("region", "act", "tech", "par", "clim", "mansys"))}


def miterra_tables() -> dict:
    """MITERRA's tables (capri_data/2017/abatement/ammonia), keyed as CAPRI's parameters."""
    spec = {"RCEmissions": ("region", "animal_mitt", "item"), "bNumAniRAINS": ("region", "animal_mitt", "year"),
            "ControlStrategies": ("region", "animal_mitt", "strategy", "item"),
            "reducEmHouse": ("region", "animal_mitt", "gas", "tech_class"),
            "reducEmStorage": ("region", "animal_mitt", "gas", "tech_class")}
    out = {}
    for name, keys in spec.items():
        with open(AMMO / f"{name}.csv", newline="") as f:
            out[name] = {tuple(r[k] for k in keys): float(r["value"]) for r in csv.DictReader(f)}
    return out


def miterra_sets() -> dict:
    """CAPRI's sets of MITERRA's types (capri_data/codes/capri)."""
    one = ("atGrazingExtra", "ani_Liq", "POULTRY", "MDACT", "ManuType", "MACT")
    two = ("ms_to_country", "pact_to_atModel", "atModel_to_PACT", "manuType_to_atModel", "DACT_TO_PACT")
    return {**{s: tuple(capri_set(s)) for s in one}, **{s: tuple(capri_pairs(s)) for s in two}}


def methane_inputs(DATA: dict, regions: set, ms: str, p_technFact: dict, st, scen_year: int,
                   p_Nemidat: dict | None = None, ghgAbatement: bool = False) -> mph.MethaneInputs:
    """MethaneInputs of a member state's regional units: DATA {(region, col, row): value} at "Y"; p_technFact
    {(region, activity, item, A): share} (the LEVL ones are taken); st the requirement call's state (its p_animReq,
    p_animReqSubEne, p_animProdDays); MITERRA's shares and CH4 losses of scen_year, or p_Nemidat as given."""
    import _capri_digest as cd
    RU = tuple(sorted(r for r in regions if r in set(capri_set("RU"))))
    mr = set(capri_pairs("MAP_RR"))
    MS_of = {r: ms for r in RU if r == ms or (ms, r) in mr}
    if p_Nemidat is None:
        p_Nemidat = mph.miterra_nemidat(scen_year, (ms,), tuple(capri_set("AACT")), miterra_tables(), miterra_sets())
    rates, biofix = cd.nfix_rates()
    return mph.MethaneInputs(
        RU=RU, MS_of=MS_of, MAACT=tuple(capri_set("MAACT")), CATACT=tuple(capri_set("CATACT")),
        A=tuple(capri_set("A")), DATA=DATA,
        p_technFact={(r, a, t): v for (r, a, i, t), v in p_technFact.items() if i == "LEVL"},
        p_animReq=dict(st.p_animReq), p_animReqSubEne=dict(st.p_animReqSubEne), p_animProdDays=dict(st.p_animProdDays),
        p_Nemidat=p_Nemidat, p_nfixRate_gras=rates, nfix_default=biofix, digestpar=cd.table(),
        FEED_TO_O=tuple(capri_pairs("FEED_TO_O")), RS=tuple(capri_set("RS")), CLIMALL=tuple(capri_set("CLIMALL")),
        CLIM=tuple(capri_set("CLIM")), CLIMCELS=tuple(capri_set("CLIMCELS")), CLIMCOOL=tuple(capri_set("CLIMCOOL")),
        CLIMTEMP=tuple(capri_set("CLIMTEMP")), CLIMWARM=tuple(capri_set("CLIMWARM")), EUGR=tuple(capri_set("EUGR")),
        ManSys=tuple(capri_set("ManSys")), EUGR_TO_MS=tuple(capri_pairs("EUGR_TO_MS")),
        SUBENE=tuple(capri_set("SUBENE")), ghgAbatement=ghgAbatement, **raw_tables())


def data_at(D, regions: set, t: str = "Y") -> dict:
    """{(region, col, row): value} of a year's data (load_base_data_and_trends.Data) at t for the regions."""
    out = {}
    for (tt, c, w), dd in D.c.items():
        if tt == t:
            for r, v in dd.items():
                if r in regions:
                    out[(r, c, w)] = v
    return out
