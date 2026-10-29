"""CAPRI's leaching of the soil N surplus (supply/supply_model.gms LEACHN_, e_nitrBal_) and the indirect N2O of leached
and run-off N (supply_model.gms GWPN2OLEA_; envind/gases.gms l. 696-745), per CAPRI region.

CAPRI (capmod: ghgAbatement on, endoLeach on, leachIpcc off) solves the share of the soil surplus lost by leaching as

  v_nitrBalance(Leach) = p_Nemidat(NITF, N, Leach, Surf)
      x (1 - 0.35 x WinterCov - nminSh x sum_fert (shares + AECM) x NO3SLEA - nmanSh x sum_fert (...) x NO3MLEA
           + v_ammoAppLeaAgg)                                         (B1: options capri-mod has)
      x (1 - nminSh x tillage NO3SLEA - nmanSh x tillage NO3MLEA - buffer strips - biodiversity - biochar)   (B2)

p_Nemidat Leach = rLFrest LFsoil (endoLeach on; ammo.gms l. 673-677: tools/build/build_n_cascade.py, n_cascade_region.csv
leach); accumulation and mineralisation are 0 since MITERRA 120407 (ammo.gms l. 664-669), so p_nitrBalance(Leach) is
p_Nemidat itself. CAPRI reports LEACHI = SURSOI x v_nitrBalance.l (reports/calc_nbalance.gms l. 290), so its
realised share is LEACHI / SURSOI.

capri-mod has no tillage, buffer strips, biodiversity or biochar options: B2 is held at the level of CAPRI's Green
Deal reference with endogenous technologies (the 'ini' run): R = leach_ini / (leach_base x B1 at CAPRI's initial
shares), computed in capri_mod/supply/n_leaching.py from this file's leach_ini (REGISTERED).

Data read: capri_data/sources/capri_res/gd2030_endotech_ini_nbalance.csv, CAPRI's regional N balance of the run
(tools/build/extract_gd2030_nbalance.py; this builder extracted it until 29 October 2026)

Data written
  capri_data/2017/abatement/ammonia/n_leaching_region.csv  region, leach_base, leach_ini, exp_imp
      leach_base  p_Nemidat(NITF, N, Leach, Surf) (n_cascade_region.csv leach)
      leach_ini   LEACHI / SURSOI of the run (CAPRI's v_nitrBalance(Leach) there)
      exp_imp     EXPPRD / IMPORT of CAPRI's 2030 reference (capri_gnb_components_2030.csv; the supply model's %data%)

    python tools/build/build_n_leaching.py
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "capri_res" / "gd2030_endotech_ini_nbalance.csv"
OUT = ROOT / "capri_data" / "2017" / "abatement" / "ammonia" / "n_leaching_region.csv"


def build():
    d = {}
    for r in csv.DictReader(open(SRC)):
        d.setdefault(r["region"], {})[r["item"]] = float(r["value"])
    base = {}
    for r in csv.DictReader(open(ROOT / "capri_data" / "2017" / "abatement" / "ammonia" / "n_cascade_region.csv")):
        if r["factor"] == "leach":
            base[r["region"]] = float(r["value"])
    gnb = {}
    for r in csv.DictReader(open(ROOT / "capri_data" / "2017" / "environment" / "capri_gnb_components_2030.csv")):
        gnb.setdefault(r["capri_region"], {})[r["item"]] = float(r["kg_n_per_ha"])
    rows = []
    for reg in sorted(set(base) | set(d)):
        x = d.get(reg, {})
        s, l_ = x.get("SURSOI", 0.0), x.get("LEACHI", 0.0)
        ini = l_ / s if s > 0 else None
        g = gnb.get(reg, {})
        e = g["EXPPRD"] / g["IMPORT"] if g.get("IMPORT", 0.0) > 0 and "EXPPRD" in g else None
        if reg not in base and ini is None:
            continue
        rows.append([reg, base.get(reg, ""), "" if ini is None else ini, "" if e is None else e])
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["region", "leach_base", "leach_ini", "exp_imp"])
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    rows = build()
    print(len(rows), "regions ->", OUT)
    for r in rows:
        if r[0] in ("DE110000", "NL220000", "PL220000", "DK000000", "FRH00000"):
            print(r)
