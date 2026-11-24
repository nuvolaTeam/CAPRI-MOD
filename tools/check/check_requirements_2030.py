"""Check the port of CAPRI's requirement functions (capri_mod/feed/equations/req_or_man_fnc_req.py, feed/
req_or_man_fnc.gms with %1 = req) against CAPRI's 2030 Green Deal reference run's start: the port on sim_ini_21730's
DATA at "Y" (the herds, yields, days and daily gains; the base year's fodder at "BAS"), its technologies' shares
p_technFact and MITERRA's housing days p_rcEmissions, with the literal tables of capri_data/2017/feed/
req_or_man_params.csv, against sim_ini_21730's literature requirements p_animReqLit (def_requirements.gms l. 33: the
requirement call's p_animReq), its production days p_animProdDays, energy components p_animReqSubEne, crude protein
p_crprReq and the rations' nutrient densities p_NutContFeed. CAPRI's results serve as the check only.

sim_ini_21730's symbols are read from its extract capri_sources/reference/simini/simini_21730
(tools/build/build_simini_reference.py with the symbols of tools/build/simini_reference_symbols.csv).

Prints, per symbol and item, the cells compared and the largest relative difference; --show lists the worst cells.
Exit status 1 if a cell differs by more than --rtol.

    python tools/check/check_requirements_2030.py [--rtol 1e-6] [--show 5]
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib"), str(ROOT / "tools" / "check")]
from paths import REFERENCE  # noqa: E402  (CAPRI's material outside the repository)

import check_manure_output_2030 as man  # noqa: E402  (the sets and the literal tables)
from capri_mod.feed.equations import req_or_man_fnc_req as rq  # noqa: E402

SIMINI = REFERENCE / "simini" / "simini_21730"
#: DATA columns the functions read besides the animals
OTHER_COLS = ("GRAE", "GRAI", "IHISGR", "FallGr", "OFAR", "MAIF", "INDM", "FEDM", "SHEP", "GOAT", "DRMA", "ENNE", "GROF")


def _csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, float_precision="round_trip", keep_default_na=False,
                       dtype={f"d{k}": str for k in range(7)})


def state_2030(extra: dict | None = None) -> rq.ReqState:
    """CAPRI's inputs of the requirement call at "Y" from sim_ini_21730. extra, if given, receives DATA at "TRD" of the
    animals' herds and of the feed use (extra["TRD"], {(region, column, row): value}) and the member states' days at "Y"
    that the call replaces by CAPTRD's (extra["Y_DAYS_MS"])."""
    mcact = tuple(man._set("MCACT"))
    aact = tuple(man._set("AACT"))
    cols = set(aact) | set(OTHER_COLS) | set(mcact)
    data, bas = {}, {}
    MS = frozenset(man._set("MS"))
    trd_days = {}
    for ch in pd.read_csv(SIMINI / "DATA.csv.gz", chunksize=400_000, float_precision="round_trip",
                          dtype={"d0": str, "d1": str, "d2": str, "d3": str}):
        ch = ch[ch.d1.isin(cols) & ch.d3.isin(["Y", "BAS", "TRD"])]
        for r, c, i, y, v in zip(ch.d0, ch.d1, ch.d2, ch.d3, ch.value):
            if y == "TRD":
                if i == "DAYS" and r in MS:
                    trd_days[(r, c, i)] = float(v)
                if extra is not None and (i == "LEVL" or c == "GROF"):
                    extra.setdefault("TRD", {})[(r, c, i)] = float(v)
                continue
            (data if y == "Y" else bas)[(r, c, i)] = float(v)
    # the member states' days at the requirement call are CAPTRD's: sim_ini's at "Y" are the regions' calibrated days
    # aggregated afterwards (baseline/fedtrm_prep.gms l. 50-75, supply/aggreg.gms)
    if extra is not None:
        extra["Y_DAYS_MS"] = {k: data[k] for k in trd_days if k in data}
    data.update(trd_days)
    tf = _csv(SIMINI / "p_technFact.csv.gz")
    tf = tf[tf.d1.isin(aact)]
    p_technFact = {(r, c, i, a): float(v) for r, c, i, a, v in zip(tf.d0, tf.d1, tf.d2, tf.d3, tf.value)}
    rc = _csv(SIMINI / "p_rcEmissions.csv.gz")
    p_rc = {(r, a, p): float(v) for r, a, p, v in zip(rc.d0, rc.d1, rc.d2, rc.value)}
    rr = pd.read_csv(man.SETS / "R_RAGG.csv", dtype=str, keep_default_na=False)
    r_ms = {a: b for a, b in zip(rr.d0, rr.d1) if b in MS}
    feed_q = {(m, f): v for (m, c, f), v in bas.items() if c == "GROF" and m in MS and f in rq.FEED}
    fo = pd.read_csv(man.SETS / "FEED_TO_O.csv", dtype=str, keep_default_na=False)
    po = pd.read_csv(man.SETS / "PACT_TO_O.csv", dtype=str, keep_default_na=False)
    P = man.params()
    return rq.ReqState(DATA=data, RS=tuple(man._set("RS")), MS=MS, R_RAGG_MS=r_ms, GRSACT=tuple(man._set("GRSACT")),
                       RUMI=tuple(man._set("RUMI")), AACT=aact, p_LUUnits=P["p_LUUnits"], p_technFact=p_technFact,
                       p_rcEmissions=p_rc, p_feedQuant=feed_q, p_carcassShare=P["p_carcassShare"],
                       p_startWgt=P["p_startWgt"], p_reqfcnlim=P["p_reqfcnlim"],
                       p_coeffEnergyForGrowth=P["p_coeffEnergyForGrowth"],
                       p_convFactEnergyUnitsToEnne=P["p_convFactEnergyUnitsToEnne"],
                       p_NutContFeedRef=P["p_NutContFeedRef"], p_pigsReqLowWgt=P["p_pigsReqLowWgt"],
                       p_pigsReqHighWgt=P["p_pigsReqHighWgt"], DATA_BAS=bas, MAACT=tuple(man._set("MAACT")),
                       MCACT=mcact, FEED_TO_O=frozenset(zip(fo.d0, fo.d1)), PACT_TO_O=frozenset(zip(po.d0, po.d1)))


#: the units of CAPRI's requirement call compared: its RU, the NUTS 2 regions and the member states without regions
#: (the member states' and NUTS 1 rows with regions are aggregates in CAPRI's results: def_requirements.gms works on RU)
SKIP: set = set()


def _compare(name, mine: dict, ref: dict, stats, key_item=-1):
    mine = {k: v for k, v in mine.items() if k[0] not in SKIP}
    ref = {k: v for k, v in ref.items() if k[0] not in SKIP}
    for k, v in ref.items():
        m = float(mine.get(k, 0.0) or 0.0)
        rel = abs(m - v) / max(abs(v), 1e-9) if (abs(v) > 1e-9 or abs(m) > 1e-9) else 0.0
        stats[(name, k[key_item] if key_item is not None else "")].append((rel, k, m, v))
    for k, m in mine.items():
        if k not in ref and abs(m) > 1e-9:
            stats[(name, (k[key_item] if key_item is not None else "") + " (port only)")].append((1.0, k, m, 0.0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtol", type=float, default=1e-6)
    ap.add_argument("--show", type=int, default=0)
    o = ap.parse_args()
    st = rq.req_or_man_fnc_req(state_2030())
    rr = pd.read_csv(man.SETS / "R_RAGG.csv", dtype=str, keep_default_na=False)
    SKIP.update({b for a, b in zip(rr.d0, rr.d1) if a != b})
    animals = set(man.ANIMALS)
    stats = defaultdict(list)
    lit = _csv(SIMINI / "p_animReqLit.csv.gz")
    ref = {(r, a, t, i): float(v) for r, a, t, i, v in zip(lit.d0, lit.d1, lit.d2, lit.d3, lit.value) if a in animals}
    mine = {k: v for k, v in st.p_animReq.items() if k[1] in animals and k[3] in rq.REQSC}
    _compare("p_animReqLit", mine, ref, stats)
    for sym, attr, item in (("p_animProdDays", "p_animProdDays", None), ("p_animReqSubEne", "p_animReqSubEne", -1),
                            ("p_NutContFeed", "p_NutContFeed", 3)):
        t = _csv(SIMINI / f"{sym}.csv.gz")
        dims = [c for c in t.columns if c.startswith("d")]
        ref = {}
        for row in t.itertuples(index=False):
            key = tuple(getattr(row, d) for d in dims)
            if key[1] in animals:
                key = tuple("MEAN" if x == "mean" else x for x in key)
                ref[key] = float(row.value)
        mine = {k: v for k, v in getattr(st, attr).items() if k[1] in animals}
        _compare(sym, mine, ref, stats, item)
    t = _csv(SIMINI / "p_crprReq.csv.gz")
    ref = {(r, a, tt): float(v) for r, a, tt, y, v in zip(t.d0, t.d1, t.d2, t.d3, t.value) if a in animals and y == "Y"}
    _compare("p_crprReq", {k: v for k, v in st.p_crprReq.items() if k[1] in animals}, ref, stats, None)
    bad = 0
    for (sym, item), xs in sorted(stats.items()):
        xs.sort(key=lambda x: -x[0])
        n_bad = sum(1 for x in xs if x[0] > o.rtol)
        bad += n_bad
        print(f"{sym:16s} {str(item):22s} cells {len(xs):6d}  above rtol {n_bad:6d}  max rel {xs[0][0]:.2e} {xs[0][1]}")
        for rel, k, m, v in xs[:o.show]:
            if rel > o.rtol:
                print(f"      {k} port {m:.8g} CAPRI {v:.8g} rel {rel:.2e}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
