"""Build CAPRI's land-market data per model region (docs/LAND_USE_FLEXIBILITY.md).

For each model region: base areas (1000 ha) of CAPRI's land types ARAC (arable
crops), GRAS (grassland), FRUN (fruit, nurseries), FORE (forest), OLND (other
land), ARTIF (artificial) from the 2017 regional results (res_17*, LEVL), and
CAPRI's land-market quadratic matrix p_pmpQuadLandTypes (pmppar_17XX.gdx,
regional row, else national). CAPRI's land-type constants (p_pmpCnstLandTypes,
trustee-land variant) are not needed: the model recalibrates constants so the
base land use is optimal, as for every PMP term.

    python tools/build_land_market.py [--dump-dir DIR] [--pmp-dir DIR]
"""
from __future__ import annotations
import argparse, csv, glob, json, re, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
LT = ["ARAC", "GRAS", "FRUN", "FORE", "OLND", "ARTIF"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    ap.add_argument("--pmp-dir", type=Path, default=Path("/home/claude/work/landexp/land_export"))
    args = ap.parse_args()
    import pandas as pd
    areas = pd.read_csv(_ROOT / "capri_data" / "2017" / "supply" / "base_areas.csv", index_col=0)
    corr = json.loads((_ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]
    def to_model(c8):
        for c in corr.get(c8, []):
            if c in areas.index:
                return c
    row = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'(ARAC|GRAS|FRUN|FORE|OLND|ARTIF)'\.'LEVL'\.'Y'\s+(-?\d[\d.Ee+\-]*)")
    lev, r8of = defaultdict(dict), {}
    for f in glob.glob(str(args.dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = row.match(line)
            if m and not m.group(1).endswith("000000"):
                reg = to_model(m.group(1))
                if reg:
                    lev[reg][m.group(2)] = lev[reg].get(m.group(2), 0.0) + float(m.group(3)); r8of[reg] = m.group(1)
    Q = defaultdict(dict)
    for f in glob.glob(str(args.pmp_dir / "pmppar_17*_p_pmpQuadLandTypes.csv")):
        for r in csv.reader(open(f, encoding="utf-8-sig")):
            if len(r) == 4 and r[0] != "RALL" and r[1] in LT and r[2] in LT:
                Q[r[0]][(r[1], r[2])] = float(r[3])
    out, notpd, nodata = {}, [], []
    for reg, d in lev.items():
        r8 = r8of[reg]
        src = r8 if r8 in Q else (r8[:2] + "000000" if r8[:2] + "000000" in Q else None)
        if src is None:
            nodata.append(reg); continue
        M = np.array([[Q[src].get((a, b), Q[src].get((b, a), 0.0)) for b in LT] for a in LT])
        M = 0.5 * (M + M.T)
        ev = np.linalg.eigvalsh(M)
        if ev.min() <= 0:
            notpd.append((reg, float(ev.min())))
        out[reg] = {"base_kha": {a: d.get(a, 0.0) for a in LT}, "quad": M.tolist(), "quad_source": src,
                    "min_eigenvalue": float(ev.min())}
    # ---- SPLIT REGIONS: a CAPRI regional code that maps to no model region but
    # whose agricultural area equals the SUM of unmapped model regions in the
    # same country (within 0.5%) is their parent (e.g. IT310000 Trentino-Alto
    # Adige = ITH1 + ITH2). Each part: ARAC/GRAS/FRUN from the model's own base
    # areas (rows consistent at base); FORE/OLND/ARTIF = parent x the part's
    # share of the parent's agricultural land; matrix = parent's / share, which
    # keeps the relative responsiveness on a smaller area (REGISTERED). Model
    # regions without any parent use the national matrix, scaled likewise.
    from itertools import combinations
    agri = {"ARAC", "GRAS", "FRUN"}
    lev_all = defaultdict(dict)
    for f in glob.glob(str(args.dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = row.match(line)
            if m:
                lev_all[m.group(1)][m.group(2)] = lev_all[m.group(1)].get(m.group(2), 0.0) + float(m.group(3))
    model_area = {r: float(areas.loc[r].sum()) for r in areas.index}
    def own_lt(r):
        a = areas.loc[r]
        perm = sum(float(a.get(c, 0.0)) for c in ("WINE", "OLIV", "APPL", "OFRU", "CITR", "TAGR"))
        gras = float(a.get("GRAS", 0.0))
        return {"ARAC": model_area[r] - perm - gras, "GRAS": gras, "FRUN": perm}
    unmapped = [r for r in areas.index if r not in out and model_area[r] > 0]
    orphans = [c for c in lev_all if not c.endswith("000000") and c[4:] == "0000"
               and not any(x in areas.index for x in corr.get(c, [])) and c in Q]
    parent = {}
    for c in orphans:
        pa = sum(v for k, v in lev_all[c].items() if k in agri)
        cand = [r for r in unmapped if r[:2] == c[:2] and r not in parent]
        hit = None
        for size in (2, 3, 4):
            for grp in combinations(cand, size):
                if pa > 0 and abs(sum(model_area[g] for g in grp) / pa - 1) < 0.005:
                    hit = grp; break
            if hit: break
        if hit:
            for g in hit:
                parent[g] = c
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
        bk = own_lt(r)
        for t in ("FORE", "OLND", "ARTIF"):
            bk[t] = sh * base_src.get(t, 0.0)
        out[r] = {"base_kha": bk, "quad": M.tolist(), "quad_source": src + (" (split parent)" if r in parent else " (national)"),
                  "share_of_source": sh, "min_eigenvalue": float(np.linalg.eigvalsh(M).min())}
        if r in parent: split_n += 1
        else: nat_n += 1
    print(f"split parents: {sorted(set(parent.values()))} -> {sorted(parent)}; filled {split_n} split parts, {nat_n} from national matrices")

    dest = _ROOT / "capri_data" / "2017" / "supply" / "land_market_2017.json"
    dest.write_text(json.dumps({"_source": "CAPRI res_17 LEVL of land types; pmppar_17XX p_pmpQuadLandTypes", "land_types": LT,
                                "regions": out}, indent=1))
    print(f"wrote {dest}: {len(out)} regions | without CAPRI quad: {len(nodata)} | not positive definite: {len(notpd)} {notpd[:5]}")


if __name__ == "__main__":
    main()
