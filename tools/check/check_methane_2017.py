"""The methane per head of a country's activities in 2017, as CAPREG computes it at "Y" (capreg.gms l. 2299 digestibility,
l. 2314 gases), from the port (capri_mod/environmental/methane_per_head.py) against CAPREG's own results: CH4ENT and
CH4MAN of DATA2 at "Y" (capri_sources/reference/capreg_base/17/<CC>.csv.gz).

The inputs are CAPRI's: CAPREG's 2017 data at "Y" (the products' DRMA, FIDI, CRPR, the member state's FEDM and INTF,
FLEG, the rations), its technologies' shares and housing days (capreg_tseries/<CC>_17: p_technFact, p_rcEmissions) and
MITERRA's shares (p_NemiDAT); the requirement call (feed/req_or_man_fnc.gms 'req', capri_mod/feed/equations/
req_or_man_fnc_req.py) on that data, the year being its own base and trend; CAPRI's raw methane tables
(tools/build/build_gascoeff_tables.py), its digestibility table (capri_digestpar) and its grass N fixation
(fert/fertpar.gms); the readers in tools/lib/methane_inputs.py. CAPREG's results are for the check only.

Result (25 November 2026, MITERRA's scenario year 2000 as CAPREG's): the values of all 35 countries with CAPREG's base
year (CH4ENT from the ration, CH4ENTstd, CH4MAN of the activities with a level) within 1.8e-7 of CAPREG's, Denmark's
50 within 1.4e-14, Norway's 300 within 6.3e-12 (with CAPRI's Norwegian MITERRA data of the project lead's
installation: until then its hens' and other poultry's housing shares of 2000 were swapped). With CAPREG's
time-series p_NemiDAT (--scen-year=0; the inventory shares) Denmark's dairy CH4MAN is 39% higher.

    python tools/check/check_methane_2017.py [--scen-year=2000] [CC ...]       (default DK; 0: CAPREG's p_NemiDAT)
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib")]

from capri_mod.environmental import methane_per_head as mph  # noqa: E402
from capri_mod.feed import chain  # noqa: E402
from capri_mod.feed.equations import req_or_man_fnc_req as rq  # noqa: E402
from capri_mod.projection.equations import load_base_data_and_trends as ly  # noqa: E402

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


def inputs(cc: str, scen_year: int = 2000) -> tuple:
    """(MethaneInputs, CAPREG's DATA2 at "Y") of the country; MITERRA's shares and CH4 losses of the scenario
    year (CAPREG's 2000; 0: CAPREG's time-series p_NemiDAT)."""
    import pandas as pd
    import feed_chain_inputs as fci
    import methane_inputs as mi
    ci, ms, mine, D, tf, st = year_2017(cc)
    DATA = mi.data_at(D, mine)
    p_nemi = None
    if not scen_year:                           # CAPREG's time-series run's (inventory shares, storgrazInv on)
        nemi = pd.read_parquet(fci.capreg_folder(cc) / "p_NemiDAT.parquet")
        p_nemi = mph.normalise_nemidat(zip(nemi.d1, nemi.d2, nemi.d3, nemi.d4, nemi.d5, nemi.value))
    return mi.methane_inputs(DATA, mine, ms, tf, st, scen_year, p_Nemidat=p_nemi), DATA


def compare(cc: str, scen_year: int = 2000) -> list:
    """[(region, activity, item, port, CAPREG, per head of "T")] of CH4ENT (the ration's), CH4ENTstd (tier 2, else tier
    1) and CH4MAN per head of the activities with a level, as gases.gms writes them to DATA (methane_per_head.
    data_per_activity), against CAPREG's DATA2 at "Y"."""
    m, DATA = inputs(cc, scen_year)
    per_head = mph.methane_per_head(copy.deepcopy(m))
    res = mph.data_per_activity(m, per_head)
    rows = []
    for (ru, act), rec in sorted(res.items()):
        for item in ("CH4ENT", "CH4ENTstd", "CH4MAN"):
            ref = DATA.get((ru, act, item), 0.0)
            if rec.get(item) or ref:
                rows.append((ru, act, item, rec.get(item, 0.0), ref, per_head.get((ru, act, "T"), {})))
    return rows


def main() -> None:
    args = sys.argv[1:]
    year = 2000
    if args and args[0].startswith("--scen-year="):
        year = int(args.pop(0).split("=")[1])
    for cc in args or ["DK"]:
        rows = compare(cc, year)
        rel = [abs(a - b) / abs(b) for _, _, _, a, b, _ in rows if b]
        print(f"{cc}: {len(rows)} rows (CH4ENT, CH4ENTstd, CH4MAN; kg per head; port against CAPREG 2017)"
              f": largest relative difference {max(rel):.2e}, {sum(r < 1e-6 for r in rel)} of {len(rel)} within 1e-6")
        for ru, act, item, mine, ref, v in rows:
            rel = (mine - ref) / ref if ref else float("nan")
            extra = f"DE {v.get('DE', 0):.2f} GE {v.get('GE', 0):.3f} ASH {v.get('ASH', 0):.2f} " \
                    f"GENE_req {v.get('GENE_req', 0):.1f} VSER {v.get('VSER', 0):.3f} MCFMS {v.get('MCFMS', 0):.4f}"
            print(f"  {ru} {act:5s} {item:6s} {mine:12.5f} {ref:12.5f} {rel:+10.2e}  {extra}")


if __name__ == "__main__":
    main()
