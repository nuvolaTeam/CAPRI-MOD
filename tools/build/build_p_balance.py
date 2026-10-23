"""CAPRI's gross phosphate (P2O5) balance (reports/calc_nbalance.gms, FNUT = PHOF), the coefficients the environmental
accounts need that capri-mod did not have yet, and CAPRI's own balance items for the comparison.

CAPRI's P balance, per region, in 1000 t P2O5 (dataOut '' . item . PHOF; 'perha' the same per ha of UAAR):
  EXCRET  = sum_MAACT LEVL x MANP x 0.001                                      (calc_nbalance.gms l. 144-146)
  MTRADE  = manure P2O5 net exports (v_manureExports - v_manureImports, ManureTradeNEW on)            (l. 175)
  MINFER  = NETF = -v_netPutQuant(PHOF), the mineral P2O5 bought                                      (l. 115)
  CRESID  = sum_MCACT LEVL x MANP(crop) x 0.001   (crop residues; for P nothing is netted out)          (l. 197-207)
  EXPPRD  = sum_MCACT LEVL x DATA(MCACT, PHOF) x 0.001, DATA(MCACT, PHOF) at that point still the retention
            (the crop's PRET in the results; the reported PHOF is the managed need, l. 45-46)                     (l. 55-59)
  RUNANI  = sum_MAACT LEVL x MANP x RunTot(N) x 0.001 (l. 71, 103-106: the N runoff share of the manure applied to its P;
            "202102al - RUNANI should happen also for P and K with the same loss factor?", l. 70)
  IMPORT  = EXCRET - MTRADE + MINFER + CRESID                                                          (l. 237-243)
  SURTOT  = IMPORT - EXPPRD                                                                             (l. 305-313)
  SURSOI  = SURTOT - RUNANI                                                                             (l. 247-262)
(the supply model's own e_SURSOIHa for PHOF has no runoff term: v_gasrunani is MANN-only; supply_model.gms l. 1322)

Sources
  --ref  res_2_1730greendeal_refdefaulta (zip; CAPRI's Green Deal 2030 reference, the run every other 2030 coefficient
         of capri-mod comes from: tools/build/build_npk_balance_2030.py, build_capri_crop_n_coefs.py)
  --ini  res_2_1730greendeal_refpol_endotech_all_inidefaulta (csv; the same reference with endogenous technologies at
         their initial shares, the run the N cascade and leaching checks use: tools/build/build_n_leaching.py)

Data written
  capri_data/sources/capri_res/gd2030_ref_pbalance.csv          region, col, row, value: the extract of --ref (the
      regional items above for PHOF, UAAR LEVL, and per elementary crop LEVL, PRET, PCRD); the input of this builder
  capri_data/sources/capri_res/gd2030_endotech_ini_pbalance.csv  the same for --ini, plus per elementary animal activity
      LEVL, MANP, MANN, RUNANI (kg per head, RUNANI/MANN = CAPRI's v_emiLoss(N, RunTot)); validation only
      (capri_mod/tests/test_p_balance.py)
  capri_data/2017/environment/p_balance_crop_coefs_2030.csv  capri_region, model_crop, levl_kha, pret_kg_ha, pcrd_kg_ha:
      CAPRI's P2O5 retention (removal, EXPPRD) and crop residue output (CRESID) per ha of the model's crops (CAPRI crops
      pooled into model crops by area as tools/build/build_npk_balance_2030.py does: CORN = MAIZ, WINE = TWIN,
      GRAS = GRAE + GRAI, OFOD = OFAR + ROOF, SETA = FALL + VSET + ISET + GSET + TSET), and GRAE and GRAI on their own
      (the model's grassland split column)

The builder checks the identities above on both runs (every region with a UAAR): the sums of the crop and animal
coefficients against CAPRI's regional items, and the balance identities.

    python tools/build/build_p_balance.py [--ref res_2_1730greendeal_refdefaulta.zip] [--ini res_..._inidefaulta.csv]
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "capri_data" / "sources" / "capri_res"
SRC_REF = SRC_DIR / "gd2030_ref_pbalance.csv"
SRC_INI = SRC_DIR / "gd2030_endotech_ini_pbalance.csv"
OUT = ROOT / "capri_data" / "2017" / "environment" / "p_balance_crop_coefs_2030.csv"
UP = Path("/mnt/user-data/uploads")

ITEMS = ("EXCRET", "MTRADE", "MINFER", "NETF", "CRESID", "EXPPRD", "RUNANI", "IMPORT", "SURTOT", "SURSOI")
#: CAPRI's elementary crop activities (sets.gms MCACT), as tools/build/build_npk_balance_2030.py
CROPS = ("SWHE", "DWHE", "RYEM", "BARL", "OATS", "MAIZ", "OCER", "PARI", "RAPE", "SUNF", "SOYA", "OOIL", "OIND", "NURS",
         "FLOW", "OCRO", "NECR", "MAIF", "ROOF", "OFAR", "GRAE", "GRAI", "PULS", "POTA", "SUGB", "TEXT", "TOBA", "TOMA",
         "OVEG", "APPL", "OFRU", "CITR", "TAGR", "TABO", "TWIN", "OLIV", "FALL", "ISET", "GSET", "TSET", "VSET", "NONF")
#: CAPRI's elementary animal activities (sets.gms MAACT; BULL and BULH are the low- and high-intensity bulls, DCOW,
#: BULF, HEIF, CALV, PIGS, ... aggregates)
ANIMALS = ("DCOL", "DCOH", "BULL", "BULH", "HEIL", "HEIH", "HEIR", "CAFF", "CAFR", "CAMF", "CAMR", "SCOW", "SHGM", "SHGF",
           "PIGF", "SOWS", "HENS", "POUF")
#: model crop <- CAPRI crops (tools/build/build_npk_balance_2030.py MODEL)
MODEL = {"CORN": ("MAIZ",), "WINE": ("TWIN",), "GRAS": ("GRAE", "GRAI"), "OFOD": ("OFAR", "ROOF"),
         "SETA": ("FALL", "VSET", "ISET", "GSET", "TSET")}

RX = re.compile(r"^'([A-Z0-9]{8})'\.''\.'([A-Za-z0-9_]+)'\.'([A-Za-z0-9_]+)'\.'2030'\s+([-\d.Ee+]+)")


def _wanted(col: str, row: str, animals: bool) -> bool:
    if row == "PHOF" and col in ITEMS:
        return True
    if col == "UAAR" and row == "LEVL":
        return True
    if col in CROPS and row in ("LEVL", "PRET", "PCRD"):
        return True
    return animals and col in ANIMALS and row in ("LEVL", "MANP", "MANN", "RUNANI")


def extract(dump: Path, out: Path, animals: bool) -> int:
    """The P balance rows of a CAPRI result dump (zip with one csv, or the csv) -> out (region, col, row, value)."""
    if dump.suffix == ".zip":
        p = subprocess.Popen(["unzip", "-p", str(dump)], stdout=subprocess.PIPE, text=True)
        lines = p.stdout
    else:
        lines = open(dump)
    rows = []
    for line in lines:
        m = RX.match(line)
        if m and _wanted(m.group(2), m.group(3), animals):
            v = float(m.group(4))
            if v != 0.0:
                rows.append((m.group(1), m.group(2), m.group(3), m.group(4)))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["region", "col", "row", "value"])
        w.writerows(rows)
    return len(rows)


def read(src: Path) -> dict:
    """{region: {(col, row): value}}"""
    d = defaultdict(dict)
    for r in csv.DictReader(open(src)):
        d[r["region"]][(r["col"], r["row"])] = float(r["value"])
    return d


def check(d: dict, name: str, animals: bool) -> None:
    """CAPRI's identities on the run's own data: the items from the coefficients and the balance."""
    worst = defaultdict(float)
    n = nr = 0
    for reg, x in d.items():
        if x.get(("UAAR", "LEVL"), 0.0) <= 0 or ("EXPPRD", "PHOF") not in x:
            continue
        n += 1
        it = lambda k: x.get((k, "PHOF"), 0.0)
        calc = {
            "EXPPRD": sum(x.get((c, "LEVL"), 0.0) * x.get((c, "PRET"), 0.0) for c in CROPS) / 1000.0,
            "CRESID": sum(x.get((c, "LEVL"), 0.0) * x.get((c, "PCRD"), 0.0) for c in CROPS) / 1000.0,
            "IMPORT": it("EXCRET") - it("MTRADE") + it("MINFER") + it("CRESID"),
            "SURTOT": it("EXCRET") - it("MTRADE") + it("MINFER") + it("CRESID") - it("EXPPRD"),
            "SURSOI": it("EXCRET") - it("MTRADE") + it("MINFER") + it("CRESID") - it("EXPPRD") - it("RUNANI"),
            "MINFER": it("NETF"),
        }
        if animals:
            calc["EXCRET"] = sum(x.get((a, "LEVL"), 0.0) * x.get((a, "MANP"), 0.0) for a in ANIMALS) / 1000.0
            # per-activity RUNANI (MANN x RunTot) is reported for the NUTS2 regions, not for the member-state aggregates
            if any((a, "RUNANI") in x for a in ANIMALS):
                nr += 1
                calc["RUNANI"] = sum(x.get((a, "LEVL"), 0.0) * x.get((a, "MANP"), 0.0) * x.get((a, "RUNANI"), 0.0)
                                     / x[(a, "MANN")] for a in ANIMALS if x.get((a, "MANN"), 0.0) > 0) / 1000.0
        for k, v in calc.items():
            worst[k] = max(worst[k], abs(v - it(k)) / max(1.0, abs(it(k))))
    print(f"{name}: {n} regions ({nr} with per-activity RUNANI); largest deviation of CAPRI's formula from its item "
          "(relative, at least 1 kt): " + ", ".join(f"{k} {v:.1e}" for k, v in sorted(worst.items())))


def build(d: dict) -> int:
    rev = {c: mc for mc, cs in MODEL.items() for c in cs}
    rows = []
    for reg in sorted(d):
        x = d[reg]
        lev = {c: x.get((c, "LEVL"), 0.0) for c in CROPS if x.get((c, "LEVL"), 0.0) > 0}
        if not lev:
            continue
        agg = {}
        for c, L in lev.items():
            mc = rev.get(c, c)
            a = agg.setdefault(mc, [0.0, 0.0, 0.0])
            a[0] += L
            a[1] += L * x.get((c, "PRET"), 0.0)
            a[2] += L * x.get((c, "PCRD"), 0.0)
        for gc in ("GRAE", "GRAI"):
            if gc in lev:
                agg["_" + gc] = [lev[gc], lev[gc] * x.get((gc, "PRET"), 0.0), lev[gc] * x.get((gc, "PCRD"), 0.0)]
        for mc, (L, pr, pc) in sorted(agg.items()):
            rows.append([reg, mc.lstrip("_"), f"{L:.10g}", f"{pr / L:.10g}", f"{pc / L:.10g}"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["capri_region", "model_crop", "levl_kha", "pret_kg_ha", "pcrd_kg_ha"])
        w.writerows(rows)
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", type=Path, default=UP / "res_2_1730greendeal_refdefaulta.zip")
    ap.add_argument("--ini", type=Path, default=UP / "res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv")
    a = ap.parse_args()
    if a.ref.exists():
        print(extract(a.ref, SRC_REF, animals=False), "records ->", SRC_REF.relative_to(ROOT))
    if a.ini.exists():
        print(extract(a.ini, SRC_INI, animals=True), "records ->", SRC_INI.relative_to(ROOT))
    ref = read(SRC_REF)
    check(ref, "reference", animals=False)
    if SRC_INI.exists():
        check(read(SRC_INI), "ini", animals=True)
    print(build(ref), "rows ->", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
