"""Build CAPRI's land-market data per model region (docs/LAND_USE_FLEXIBILITY.md).

For each model region: base areas (1000 ha) of CAPRI's land types ARAC (arable
crops), GRAS (grassland), FRUN (fruit, nurseries), FORE (forest), OLND (other
land), ARTIF (artificial) from the 2017 regional results (res_17*, LEVL), and
CAPRI's land-market quadratic matrix p_pmpQuadLandTypes (pmppar_17XX.gdx,
regional row, else national). CAPRI's land-type constants (p_pmpCnstLandTypes,
trustee-land variant) are not needed: the model recalibrates constants so the
base land use is optimal, as for every PMP term.

    python tools/build/build_land_market.py [--dump-dir DIR] [--pmp-dir DIR]
"""
from __future__ import annotations
import argparse, csv, glob, json, re, sys
from collections import defaultdict
from pathlib import Path
import numpy as np


def _read_csv(*a, **k):
    """pandas.read_csv with floats parsed to the last digit (KNOWN_ISSUES K82)."""
    import pandas as pd
    k.setdefault("float_precision", "round_trip")
    return pd.read_csv(*a, **k)

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
sys.path[:0] = [str(_ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
LT = ["ARAC", "GRAS", "FRUN", "FORE", "OLND", "ARTIF"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    ap.add_argument("--pmp-dir", type=Path, default=Path("/home/claude/work/landexp/land_export"))
    ap.add_argument("--year", type=int, choices=(2017, 2030), default=2017,
                    help="2017: CAPRI's base-year calibration (res_17 LEVL, pmppar_17 exports); 2030: its 2030 baseline "
                         "calibration (LEVL of the 2030 reference, pmppar_21730 p_pmpQuadLandTypes, "
                         "capri_data/sources/baseline_pmp/pmp_quad_landtypes_2030.csv)")
    ap.add_argument("--ref", type=Path,
                    default=Path("/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv"))
    args = ap.parse_args()
    import pandas as pd
    areas = _read_csv(_ROOT / "capri_data" / "2017" / "supply" / "base_areas.csv", index_col=0)
    # CAPRI regions -> model regions (tools/lib/_model_regions.py): on CAPRI's units, each region is its own CAPRI region
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location("_mr", _ROOT / "tools" / "lib" / "_model_regions.py")
    _mr = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_mr)
    _c2g, _groups = _mr.capri_groups(list(areas.index))

    def to_model(c8):
        g = _c2g.get(c8)
        if g is None:
            return None
        regs_g = _groups[g][1]
        return next(iter(regs_g)) if len(regs_g) == 1 else None
    # land-type levels (CAPRI code, land type, 1000 ha) of the calibration point
    if args.year == 2030:
        import subprocess as _sp2
        _pat = r"^'[A-Z]{2}[0-9A-Z]{6}'\.''\.'(ARAC|GRAS|FRUN|FORE|OLND|ARTIF)'\.'LEVL'\.'2030'"
        _txt = _sp2.run(["grep", "-E", _pat, str(args.ref)], capture_output=True, text=True).stdout
        _rx = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'(ARAC|GRAS|FRUN|FORE|OLND|ARTIF)'\.'LEVL'\.'2030'\s+(-?\d[\d.Ee+\-]*)")
        LEVROWS = [(m.group(1), m.group(2), float(m.group(3))) for m in map(_rx.match, _txt.splitlines()) if m]
    else:
        _rx = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'(ARAC|GRAS|FRUN|FORE|OLND|ARTIF)'\.'LEVL'\.'Y'\s+(-?\d[\d.Ee+\-]*)")
        LEVROWS = [(m.group(1), m.group(2), float(m.group(3)))
                   for f in glob.glob(str(args.dump_dir / "res_17*.txt"))
                   for m in map(_rx.match, open(f, errors="ignore")) if m]
    lev, r8of = defaultdict(dict), {}
    for c8, t, v in LEVROWS:
        if _mr.regional_row(c8):
            reg = to_model(c8)
            if reg:
                lev[reg][t] = lev[reg].get(t, 0.0) + v
                r8of.setdefault(reg, set()).add(c8)
    Q = defaultdict(dict)
    if args.year == 2030:
        for r in csv.DictReader(open(_ROOT / "capri_data" / "sources" / "baseline_pmp" / "pmp_quad_landtypes_2030.csv")):
            if r["landtype1"] in LT and r["landtype2"] in LT:
                Q[r["region"]][(r["landtype1"], r["landtype2"])] = float(r["value"])
    else:
        for f in glob.glob(str(args.pmp_dir / "pmppar_17*_p_pmpQuadLandTypes.csv")):
            for r in csv.reader(open(f, encoding="utf-8-sig")):
                if len(r) == 4 and r[0] != "RALL" and r[1] in LT and r[2] in LT:
                    Q[r[0]][(r[1], r[2])] = float(r[3])
    # CAPRI DEFAULT PLACEHOLDERS are not data: some codes (e.g. PL300000, not used in
    # CAPRI simulations) carry 100 on the diagonal and -5 off it. Taken as a split
    # parent, PL300000 gave PL81/PL84 curvature 1e5 times their neighbours' (Clarabel
    # declared them unbounded). Treated as missing: those regions use the national
    # matrix scaled by their share (the registered rule for regions without a parent).
    def _placeholder(qq):
        vals = list(qq.values())
        diag = [v for (a, b), v in qq.items() if a == b]
        off = [v for (a, b), v in qq.items() if a != b]
        return bool(diag) and all(abs(v - 100.0) < 1e-9 for v in diag) and all(abs(v + 5.0) < 1e-9 for v in off)
    placeholders = sorted(c for c, qq in Q.items() if _placeholder(qq))
    for c in placeholders:
        del Q[c]
    print(f"CAPRI default placeholder matrices ignored: {placeholders}")

    # merged CAPRI regions (several codes, one model region): a combined matrix, the parents'
    # matrices weighted by their agricultural area (REGISTERED)
    _agri_lev = defaultdict(float)
    for c8, t, v in LEVROWS:
        if t in ("ARAC", "GRAS", "FRUN"):
            _agri_lev[c8] += v

    def _combine(codes):
        codes = sorted(c for c in codes if c in Q)
        if len(codes) == 1:
            return codes[0]
        if not codes:
            return None
        key = "+".join(codes)
        # The land owners of the combined CAPRI regions each respond to the same rents, so the combined land supply
        # is the SUM of their responses, dL = (Q1^-1 + Q2^-1 + ...) dr: the combined curvature is the inverse of the
        # sum of the inverses (Sprint 9t). An area-weighted average of the matrices, used before, treated the
        # combination as if it were one of its parts and overstated its curvature (FI1D: about twice).
        def _mat(c):
            M = np.array([[Q[c].get((a, b), Q[c].get((b, a), 0.0)) for b in LT] for a in LT])
            return 0.5 * (M + M.T)
        Minv = sum(np.linalg.inv(_mat(c)) for c in codes)
        Mc = np.linalg.inv(Minv)
        Mc = 0.5 * (Mc + Mc.T)
        Q[key] = {(a, b): float(Mc[i, j]) for i, a in enumerate(LT) for j, b in enumerate(LT)}
        return key

    out, notpd, nodata = {}, [], []
    for reg, d in lev.items():
        r8s = sorted(r8of[reg])
        r8 = _combine(r8s) or r8s[0]
        src = r8 if r8 in Q else (r8s[0][:2] + "000000" if r8s[0][:2] + "000000" in Q else None)
        if src is None:
            nodata.append(reg); continue
        M = np.array([[Q[src].get((a, b), Q[src].get((b, a), 0.0)) for b in LT] for a in LT])
        M = 0.5 * (M + M.T)
        ev = np.linalg.eigvalsh(M)
        if ev.min() <= 0:
            notpd.append((reg, float(ev.min())))
        out[reg] = {"base_kha": {a: d.get(a, 0.0) for a in LT}, "quad": M.tolist(), "quad_source": src,
                    "min_eigenvalue": float(ev.min())}
    # REGIONS WITHOUT THEIR OWN LAND-TYPE DATA: the national matrix, scaled by the region's share of the country's
    # agricultural land (REGISTERED). On CAPRI's units (27 October 2026) every unit has its own rows; until then the NUTS
    # splits found their parent here (by the NUTS groups, or by area sums within 0.5%), Norway's four 2016 regions shared
    # NO08 + NO09 + NO0A, and Ireland's three 2016 regions took fixed shares of IE01 and IE02.
    agri = {"ARAC", "GRAS", "FRUN"}
    lev_all = defaultdict(dict)
    for c8, t, v in LEVROWS:
        lev_all[c8][t] = lev_all[c8].get(t, 0.0) + v
    model_area = {r: float(areas.loc[r].sum()) for r in areas.index}
    def own_lt(r):
        a = areas.loc[r]
        perm = sum(float(a.get(c, 0.0)) for c in ("WINE", "OLIV", "TABO", "APPL", "OFRU", "CITR", "TAGR"))
        gras = float(a.get("GRAS", 0.0))
        return {"ARAC": model_area[r] - perm - gras, "GRAS": gras, "FRUN": perm}
    unmapped = [r for r in areas.index if r not in out and model_area[r] > 0]
    parent = {}
    split_n = nat_n = 0
    for r in unmapped:
        src = parent.get(r) or (r[:2] + "000000" if r[:2] + "000000" in Q else None)
        if src is None:
            continue
        base_src = lev_all.get(src, {})
        pa = sum(v for k, v in base_src.items() if k in agri)
        if pa <= 0:
            continue
        sh = model_area[r] / pa
        M = np.array([[Q[src].get((a, b), Q[src].get((b, a), 0.0)) for b in LT] for a in LT])
        M = 0.5 * (M + M.T) / max(sh, 1e-6)
        if args.year == 2030:
            # the part's share of its parent's 2030 land types (shares from the 2017 areas, REGISTERED)
            bk = {t: sh * base_src.get(t, 0.0) for t in LT}
        else:
            bk = own_lt(r)
            for t in ("FORE", "OLND", "ARTIF"):
                bk[t] = sh * base_src.get(t, 0.0)
        out[r] = {"base_kha": bk, "quad": M.tolist(), "quad_source": src + (" (split parent)" if r in parent else " (national)"),
                  "share_of_source": sh, "min_eigenvalue": float(np.linalg.eigvalsh(M).min())}
        if r in parent: split_n += 1
        else: nat_n += 1
    print(f"split parents: {sorted(set(parent.values()))} -> {sorted(parent)}; filled {split_n} split parts, {nat_n} from national matrices")
    sys.path.insert(0, str(_ROOT))
    from capri_mod.data import land_market_io as io
    dest = _ROOT / "capri_data" / "2017" / "supply" / f"land_market_{args.year}"
    src_txt = ("CAPRI res_17 LEVL of land types; pmppar_17XX p_pmpQuadLandTypes" if args.year == 2017 else
               "CAPRI 2030 reference LEVL of land types (res_2_1730greendeal_refpol_endotech_all_inidefaulta); "
               "pmppar_21730XX p_pmpQuadLandTypes of the 2030 baseline calibration (tools/build/build_pmp_2030.py)")
    io.write(dest, out, LT)        # CSV (capri_mod/data/land_market_io.py); source: src_txt, recorded in MANIFEST.json
    print(f"wrote {dest}.csv ({src_txt}): {len(out)} regions | without CAPRI quad: {len(nodata)} | not positive definite: {len(notpd)} {notpd[:5]}")


if __name__ == "__main__":
    main()
