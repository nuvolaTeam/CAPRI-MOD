"""The methane per head of a country's activities in 2017, as CAPREG computes it at "Y" (capreg.gms l. 2299 digestibility,
l. 2314 gases), from the port (capri_mod/environmental/methane_per_head.py) against CAPREG's own results: CH4ENT and
CH4MAN of DATA2 at "Y" (capri_sources/reference/capreg_base/17/<CC>.csv.gz).

The inputs are CAPRI's: CAPREG's 2017 data at "Y" (the products' DRMA, FIDI, CRPR, the member state's FEDM and INTF,
FLEG, the rations), its technologies' shares and housing days (capreg_tseries/<CC>_17: p_technFact, p_rcEmissions) and
MITERRA's shares (p_NemiDAT); the requirement call (feed/req_or_man_fnc.gms 'req', capri_mod/feed/equations/
req_or_man_fnc_req.py) on that data, the year being its own base and trend; CAPRI's raw methane tables
(tools/build/build_gascoeff_tables.py), its digestibility table (capri_digestpar) and its grass N fixation
(fert/fertpar.gms). CAPREG's results are for the check only.

    python tools/check/check_methane_2017.py [CC ...]       (default DK)
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib")]

from capri_mod.data.definitions import capri_pairs, capri_set  # noqa: E402
from capri_mod.environmental import methane_per_head as mph  # noqa: E402
from capri_mod.feed import chain  # noqa: E402
from capri_mod.feed.equations import req_or_man_fnc_req as rq  # noqa: E402
from capri_mod.projection.equations import load_base_data_and_trends as ly  # noqa: E402

ENV = ROOT / "capri_data" / "sources" / "intermediate" / "envind"


def _src(name: str, keys: tuple) -> dict:
    from _sources_io import source_records
    return {tuple(r[k] for k in keys): float(r["value"]) for r in source_records(ENV / f"{name}.parquet")}


def raw_tables() -> dict:
    """CAPRI's raw methane tables as gascoeff.gms loads them."""
    return {"EMISCALC0": _src("capri_emiscalc0", ("region", "act", "tech", "item")),
            "p_tier1EmFactManMgt0": _src("capri_tier1_manure_ef", ("region", "act", "tech", "clim")),
            "p_shareClimZone0": _src("capri_share_clim_zone", ("region", "clim")),
            "p_manureMgtShare0": _src("capri_manure_mgt_share", ("region", "act", "tech", "par", "clim", "mansys"))}


def year_2017(cc: str):
    """CAPREG's 2017 data of the country at "Y" (also as its "BAS" and "TRD"), the requirement call's state on it."""
    import feed_chain_inputs as fci
    ci = fci.chain_inputs(cc)
    S = ly.YearSets.from_codes()
    ms, mine = chain.regions_of(cc, S)
    D = ly.Data()
    for (t, c, w), dd in ci.capreg.c.items():
        if t != "Y":
            continue
        for r, v in dd.items():
            for tt in ("Y", "BAS", "TRD"):
                D.set(r, c, w, tt, v)
    tf = {k: v for k, v in ci.p_technFact.items() if k[0] in mine}
    st, _trd = chain.req_state(D, ci, mine, chain.req_or_man_params(), tf)
    rq.req_or_man_fnc_req(st)
    return ci, ms, mine, D, tf, st


def inputs(cc: str) -> tuple:
    """(MethaneInputs, CAPREG's DATA2 at "Y") of the country."""
    import _capri_digest as cd
    import pandas as pd
    ci, ms, mine, D, tf, st = year_2017(cc)
    DATA = {}
    for (t, c, w), dd in D.c.items():
        if t == "Y":
            for r, v in dd.items():
                DATA[(r, c, w)] = v
    RU = tuple(sorted(r for r in mine if r in set(capri_set("RU"))))
    mr = set(capri_pairs("MAP_RR"))
    MS_of = {r: ms for r in RU if r == ms or (ms, r) in mr}
    nemi = pd.read_parquet(fci_folder(cc) / "p_NemiDAT.parquet")
    p_nemi = mph.normalise_nemidat(zip(nemi.d1, nemi.d2, nemi.d3, nemi.d4, nemi.d5, nemi.value))
    rates, biofix = cd.nfix_rates()
    T = raw_tables()
    m = mph.MethaneInputs(
        RU=RU, MS_of=MS_of, MAACT=tuple(capri_set("MAACT")), CATACT=tuple(capri_set("CATACT")),
        A=tuple(capri_set("A")), DATA=DATA,
        p_technFact={(r, a, t): v for (r, a, i, t), v in tf.items() if i == "LEVL"},
        p_animReq=dict(st.p_animReq), p_animReqSubEne=dict(st.p_animReqSubEne), p_animProdDays=dict(st.p_animProdDays),
        p_Nemidat=p_nemi, p_nfixRate_gras=rates, nfix_default=biofix, digestpar=cd.table(),
        FEED_TO_O=tuple(capri_pairs("FEED_TO_O")), RS=tuple(capri_set("RS")), CLIMALL=tuple(capri_set("CLIMALL")),
        CLIM=tuple(capri_set("CLIM")), CLIMCELS=tuple(capri_set("CLIMCELS")), CLIMCOOL=tuple(capri_set("CLIMCOOL")),
        CLIMTEMP=tuple(capri_set("CLIMTEMP")), CLIMWARM=tuple(capri_set("CLIMWARM")), EUGR=tuple(capri_set("EUGR")),
        ManSys=tuple(capri_set("ManSys")), EUGR_TO_MS=tuple(capri_pairs("EUGR_TO_MS")),
        SUBENE=tuple(capri_set("SUBENE")), **T)
    return m, DATA


def fci_folder(cc: str) -> Path:
    import feed_chain_inputs as fci
    return fci.capreg_folder(cc)


def compare(cc: str) -> list:
    """[(region, activity, item, port, CAPREG)] of CH4ENT and CH4MAN per head (the technology "T")."""
    m, DATA = inputs(cc)
    res = mph.methane_per_head(copy.deepcopy(m))
    rows = []
    for (ru, act, t), v in sorted(res.items()):
        if t != "T":
            continue
        for item in ("CH4ENT", "CH4MAN"):
            ref = DATA.get((ru, act, item), 0.0)
            if v[item] or ref:
                rows.append((ru, act, item, v[item], ref, v))
    return rows


def main() -> None:
    for cc in sys.argv[1:] or ["DK"]:
        rows = compare(cc)
        print(f"{cc}: {len(rows)} rows (CH4ENT, CH4MAN per head, kg; port against CAPREG 2017)")
        for ru, act, item, mine, ref, v in rows:
            rel = (mine - ref) / ref if ref else float("nan")
            extra = f"DE {v['DE']:.2f} GE {v['GE']:.3f} ASH {v['ASH']:.2f} GENE_req {v['GENE_req']:.1f} " \
                    f"VSER {v['VSER']:.3f} MCFMS {v['MCFMS']:.4f}"
            print(f"  {ru} {act:5s} {item:6s} {mine:10.3f} {ref:10.3f} {rel:+8.4f}  {extra}")


if __name__ == "__main__":
    main()
