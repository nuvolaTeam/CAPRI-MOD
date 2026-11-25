"""Check the port of CAPRI's manure output functions (capri_mod/feed/equations/req_or_man_fnc.py) against CAPRI's 2030
Green Deal reference run: the port on the run's start (sim_ini_21730: DATA at "Y", the technologies' shares, the
correction factor p_animExcrProtCorrFact at "Y"; the literal tables, capri_data/2017/feed/req_or_man_params.csv), with CAPRI's N in products at the year from the port of
fert/calc_nexport.gms (tools/build/build_livestock_n_export_2030.calc_nexport_CRPR_EXPT, as CAPRI's PART III runs it
first), against the run's MANN, MANP and MANK at 2030 (dataOut of
res_2_1730greendeal_refdefaulta, tools/lib/paths.BASELINE_REF). CAPRI's results serve as the check only.

Prints, per animal activity and item, the cells compared and the largest relative difference; --show lists the worst
cells. Exit status 1 if a cell differs by more than --rtol or an animal activity could not be computed.

    python tools/check/check_manure_output_2030.py [--rtol 1e-6] [--show 10]
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib")]
from paths import BASELINE_REF, REFERENCE  # noqa: E402  (CAPRI's material outside the repository)
from _grep import grep  # noqa: E402

from capri_mod.feed.equations import req_or_man_fnc as rm  # noqa: E402

SIMINI = REFERENCE / "simini" / "simini_21730"
SETS = REFERENCE / "sets" / "simini_21730"
PARAMS = ROOT / "capri_data" / "2017" / "feed" / "req_or_man_params.csv"
ANIMALS = ("DCOL", "DCOH", "SCOW", "BULL", "BULH", "HEIL", "HEIH", "HEIR", "CAMF", "CAFF", "CAMR", "CAFR", "SOWS", "PIGF",
           "HENS", "POUF", "SHGM", "SHGF")
#: DATA columns the functions read besides the animals (the stocking rate's area, the sheep's and goats' herds)
OTHER_COLS = ("GRAE", "GRAI", "IHISGR", "FallGr", "OFAR", "MAIF", "INDM", "FEDM", "SHEP", "GOAT")


def _nexport():
    spec = importlib.util.spec_from_file_location("bne", ROOT / "tools" / "build" / "build_livestock_n_export_2030.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _set(name: str) -> list[str]:
    return pd.read_csv(SETS / f"{name}.csv", dtype=str, keep_default_na=False).iloc[:, 0].tolist()


def params(path: Path = PARAMS) -> dict:
    """{symbol: {key tuple or key: value}} of capri_data/2017/feed/req_or_man_params.csv."""
    keys = ["key1", "key2", "key3", "key4", "key5"]
    t = pd.read_csv(path, dtype={k: str for k in keys}, keep_default_na=False, float_precision="round_trip")
    out = defaultdict(dict)
    for row in t.itertuples(index=False):
        key = tuple(getattr(row, k) for k in keys if getattr(row, k))
        out[row.symbol][key if len(key) > 1 else key[0]] = float(row.value)
    return out


def state_2030() -> rm.ManState:
    """CAPRI's inputs of the reference run's 'man' call at "Y" (sim_ini_21730), CRPR_EXPT recomputed at the year."""
    cols = set(ANIMALS) | set(OTHER_COLS)
    data = {}
    for ch in pd.read_csv(SIMINI / "DATA.csv.gz", chunksize=400_000, float_precision="round_trip",
                          dtype={"d0": str, "d1": str, "d2": str, "d3": str}):
        ch = ch[(ch.d3 == "Y") & ch.d1.isin(cols)]
        data.update({(r, c, i): float(v) for r, c, i, v in zip(ch.d0, ch.d1, ch.d2, ch.value)})
    bne = _nexport()
    for (r, c, i) in [k for k in data if k[1] in ANIMALS and k[2] == "LEVL"]:
        items = {it: data.get((r, c, it), 0.0) for it in bne.ITEMS}
        data[(r, c, "CRPR_EXPT")] = bne.calc_nexport_CRPR_EXPT(c, items) if data[(r, c, "LEVL")] else 0.0
    tf = pd.read_csv(SIMINI / "p_technFact.csv.gz", dtype=str, keep_default_na=False)
    tf = tf[tf.d1.isin(ANIMALS) & tf.d2.isin(["LEVL", "YPIG"])]
    p_technFact = {(r, c, i, a): float(v) for r, c, i, a, v in zip(tf.d0, tf.d1, tf.d2, tf.d3, tf.value)}
    cf = pd.read_csv(SIMINI / "p_animExcrProtCorrFact.csv.gz", dtype=str, keep_default_na=False)
    cf = cf[cf.d3 == "Y"]
    corr = {(r, c, a): float(v) for r, c, a, v in zip(cf.d0, cf.d1, cf.d2, cf.value)}
    MS = frozenset(_set("MS"))
    rr = pd.read_csv(SETS / "R_RAGG.csv", dtype=str, keep_default_na=False)
    r_ms = {a: b for a, b in zip(rr.d0, rr.d1) if b in MS}
    P = params()
    return rm.ManState(DATA=data, RS=tuple(_set("RS")), MS=MS, R_RAGG_MS=r_ms, GRSACT=tuple(_set("GRSACT")),
                       RUMI=tuple(_set("RUMI")), p_LUUnits=P["p_LUUnits"], p_technFact=p_technFact,
                       p_animExcrProtCorrFact=corr, p_NutContManureKgM3=P["p_NutContManureKgM3"],
                       p_addExcrPerkgMilk=P["p_addExcrPerkgMilk"], p_carcassShare=P["p_carcassShare"],
                       p_startWgt=P["p_startWgt"], p_reqfcnlim=P["p_reqfcnlim"],
                       p_pigsReqLowWgt=P.get("p_pigsReqLowWgt", {}), p_pigsReqHighWgt=P.get("p_pigsReqHighWgt", {}))


def capri_2030(items=("MANN", "MANP", "MANK")) -> dict:
    """{(region, column, item): value} of the reference run's dataOut at 2030."""
    pat = r"^'[A-Z]{2}[A-Z0-9]{6}'\.''\.'(" + "|".join(ANIMALS) + r")'\.'(" + "|".join(items) + r")'\.'2030'"
    row = re.compile(r"^'([A-Z]{2}[A-Z0-9]{6})'\.''\.'([A-Z0-9]+)'\.'([A-Z_]+)'\.'2030'\s+([^,\s]+)")
    out = {}
    for line in grep(pat, str(BASELINE_REF)).splitlines():
        m = row.match(line)
        if m:
            tok = m.group(4).upper()
            out[(m.group(1), m.group(2), m.group(3))] = 0.0 if tok in ("EPS", "NA", "UNDF") else float(m.group(4))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtol", type=float, default=1e-6)
    ap.add_argument("--show", type=int, default=0)
    o = ap.parse_args()
    st = rm.req_or_man_fnc_man(state_2030())
    ref = capri_2030()
    # a member state's row with regions (CAPRI's MSAGG) holds in dataOut the sum of its regions, not its own call's
    msagg = {m for r, m in st.R_RAGG_MS.items() if r != m}
    stats = defaultdict(list)
    for (r, c, i), v in ref.items():
        if c in st.not_computed or r in msagg:
            continue
        if (r, c, "LEVL") not in st.DATA:
            continue
        mine = st.DATA.get((r, c, i), 0.0)
        rel = abs(mine - v) / max(abs(v), 1e-9) if (abs(v) > 1e-9 or abs(mine) > 1e-9) else 0.0
        stats[(c, i)].append((rel, r, mine, v))
    bad = 0
    for (c, i), xs in sorted(stats.items()):
        xs.sort(reverse=True)
        n_bad = sum(1 for x in xs if x[0] > o.rtol)
        bad += n_bad
        print(f"{c:5s} {i:5s} cells {len(xs):4d}  above rtol {n_bad:4d}  max rel {xs[0][0]:.2e} ({xs[0][1]})")
        for rel, r, mine, v in xs[:o.show]:
            if rel > o.rtol:
                print(f"      {r} port {mine:.6g} CAPRI {v:.6g} rel {rel:.2e}")
    if st.not_computed:
        print("not computed (CAPRI's data missing):", ", ".join(sorted(st.not_computed)))
    return 1 if bad or st.not_computed else 0


if __name__ == "__main__":
    sys.exit(main())
