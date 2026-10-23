"""CAPRI's manure N lost in housing and storage, per model region and animal (fertDistExcr_ input).

CAPRI distributes over its crop groups (supply_model.gms fertDistExcr_, v_ManureNPK) the manure N left after the
losses in housing and storage and after net trade: in its 2030 reference, in every one of 268 regions,

    fertDist_excr = EXCRET - MTRADE - GASANI - RUNANI          (1000 t N; checked below)

GASANI (gaseous losses: NH3, N2O, NOx, N2 from housing and storage) and RUNANI (runoff) are reported per animal
(kg N per head) beside MANN (kg N excreted per head). Per CAPRI animal the loss share is (GASANI + RUNANI) / MANN,
aggregated to the model animals weighted by excreted N (LEVL x MANN), as tools/build/build_nh3_factors.py does; model
regions without regional rows take the national (CC000000) shares.

Source: CAPRI's 2030 Green Deal reference results, res_2_1730greendeal_refdefaulta (dataOut).
Output: capri_data/2017/environment/manure_housing_losses_2030.csv
        region, animal, loss_share (kg N lost per kg N excreted), source (regional / national)

    python tools/build/build_manure_losses.py [--zip /mnt/user-data/uploads/res_2_1730greendeal_refdefaulta.zip]
"""
from __future__ import annotations
import argparse, importlib.util, re, subprocess, sys, zipfile
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
_sys.path[:0] = [str(_ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check", "check/nlp_check")]
from _model_regions import CTRY as MS_CODE  # noqa: E402  CAPRI member-state codes (capri_member_state_codes.csv)
sys.path[:0] = [str(_ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check", "check/nlp_check")]

#: CAPRI star 3.0 animals -> model animals. The 2030 results report the split activities (dairy cows DCOL / DCOH,
#: bulls BULL / BULH, heifers HEIL / HEIH, supply/define_activities); the former aggregates (DCOW, BULF, HEIF)
#: carry no loss rows. Only rows with a loss item count (losses / excretion of the same animals).
CAPRI_TO_MODEL = {"DCOL": "DCOW", "DCOH": "DCOW", "SCOW": "BCOW", "BULL": "BULL", "BULH": "BULL",
                  "HEIL": "HFRS", "HEIH": "HFRS", "HEIR": "HFRS",
                  "CAMF": "CALV", "CAFF": "CALV", "CAMR": "CALV", "CAFR": "CALV",
                  "SOWS": "PIGS", "PIGF": "PIGF", "HENS": "LAYS", "POUF": "BROI", "SHGM": "SHGM", "SHGF": "SHGF"}

PAT = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([^']*)'\.'([A-Za-z0-9_]+)'\.'([A-Za-z0-9]+)'\.'2030'\s+(-?\d[\d.Ee+\-]*)")
ANIM_ITEMS = {"LEVL", "MANN", "GASANI", "RUNANI"}
REG_ITEMS = {"EXCRET", "MTRADE", "GASANI", "RUNANI"}


def read(zpath: Path):
    v = defaultdict(dict)
    with zipfile.ZipFile(zpath) as z:
        name = z.namelist()[0]
        with z.open(name) as f:
            for raw in f:
                line = raw.decode("latin-1")
                if "GASANI" not in line and "RUNANI" not in line and "'MANN'" not in line and "'LEVL'" not in line \
                        and "EXCRET" not in line and "MTRADE" not in line and "fertDist_excr" not in line:
                    continue
                m = PAT.match(line)
                if not m:
                    continue
                code, dim, a, b, val = m.groups()
                if dim == "" and b in ANIM_ITEMS and a in CAPRI_TO_MODEL:
                    v[code][(a, b)] = float(val)
                elif dim == "" and a in REG_ITEMS and b == "NITF":
                    v[code][(a, "REG")] = float(val)
                elif dim == "fertDist_excr" and a == "AGGT" and b == "NITF":
                    v[code][("fertDist_excr", "REG")] = float(val)
    return v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, default=Path("/mnt/user-data/uploads/res_2_1730greendeal_refdefaulta.zip"))
    args = ap.parse_args()
    import pandas as pd
    v = read(args.zip)
    # CAPRI's identity, and the per-animal losses adding up to the regional ones
    bad = []
    for code, d in v.items():
        if ("EXCRET", "REG") in d and ("fertDist_excr", "REG") in d and d[("EXCRET", "REG")] > 1:
            net = d[("EXCRET", "REG")] - d.get(("MTRADE", "REG"), 0) - d.get(("GASANI", "REG"), 0) - d.get(("RUNANI", "REG"), 0)
            if abs(net - d[("fertDist_excr", "REG")]) > 1e-6 * max(1.0, d[("EXCRET", "REG")]):
                bad.append(code)
            la = sum(d.get((a, "LEVL"), 0) * (d.get((a, "GASANI"), 0) + d.get((a, "RUNANI"), 0)) for a in CAPRI_TO_MODEL) / 1000
            lr = d.get(("GASANI", "REG"), 0) + d.get(("RUNANI", "REG"), 0)
            if lr > 0.1 and code[2:] != "000000" and abs(la / lr - 1) > 0.02:
                bad.append(code + " (animals)")
    print("identity checked:", "all hold" if not bad else f"fails in {bad[:10]}")

    def shares(codes):
        num, den = defaultdict(float), defaultdict(float)
        for code in codes:
            d = v.get(code, {})
            for a, m in CAPRI_TO_MODEL.items():
                lev, mann = d.get((a, "LEVL"), 0.0), d.get((a, "MANN"), 0.0)
                if lev > 0 and mann > 0 and ((a, "GASANI") in d or (a, "RUNANI") in d):
                    num[m] += lev * (d.get((a, "GASANI"), 0.0) + d.get((a, "RUNANI"), 0.0))
                    den[m] += lev * mann
        return {m: num[m] / den[m] for m in num if den[m] > 0}

    areas = pd.read_csv(_ROOT / "capri_data" / "2017" / "supply" / "base_areas.csv", index_col=0)
    sp = importlib.util.spec_from_file_location("_mr", _ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(sp); sp.loader.exec_module(mr)
    _c2g, groups = mr.capri_groups(list(areas.index))
    reg_codes = {r: sorted(c for c in cs if c in v) for cs, rs in groups.values() for r in rs}
    rows, src = [], defaultdict(int)
    for reg in areas.index:
        own = shares(reg_codes.get(reg) or [])
        # CAPRI's national rows carry no animal detail: the country's regions pooled (CAPRI codes BL / IR for BE+LU / IE)
        cc = MS_CODE.get(reg[:2], reg[:2])
        nat = shares([c for c in v if c.startswith(cc) and c[2:] != "000000"]) or shares([cc + "000000"])
        for a in sorted(set(nat) | set(own)):
            s = own.get(a, nat.get(a))
            kind = "regional" if a in own else "national"
            rows.append(dict(region=reg, animal=a, loss_share=round(s, 10), source=kind))
            src[kind] += 1
    dest = _ROOT / "capri_data" / "2017" / "environment" / "manure_housing_losses_2030.csv"
    pd.DataFrame(rows).to_csv(dest, index=False)
    print(f"wrote {dest}: {len(rows)} rows, {len({r['region'] for r in rows})} regions ({dict(src)})")


if __name__ == "__main__":
    main()
