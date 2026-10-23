"""CAPTRD's sets of estimated series and product groups, as mapping CSVs for CAPTRD-MOD.

CAPTRD defines its own sets in gams/captrd/sets_captrd.gms (CAPRI star 3.0) on top of CAPRI's global sets
(gams/sets.gms). The global ones are taken from CAPRI's own instantiation, exported from a CAPMOD file
(capri_reference/sets/<tag>, tools/build/build_capri_sets_reference.py); the CAPTRD ones are transcribed below with their
line numbers.

Caveat: the global sets come from a CAPMOD run (sim_ini_21730.gdx). sets.gms is shared by CAPTRD and CAPMOD, but
a compile-time switch that differs between the two tasks could change a set; the coverage test against CAPTRD's own
results (capri_mod/pipeline/tests/test_captrd_sets.py) is the check.

Output: capri_data/pipeline/captrd/sets/<name>.csv (one column per dimension: d0, d1).

    python tools/build/build_captrd_sets.py [--ref capri_reference/sets/simini_21730]
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "pipeline" / "captrd" / "sets"

# --- sets_captrd.gms, transcribed -----------------------------------------------------------------------------------
GRPC = ["CERE", "OILS", "INDU", "VEGE", "FRUI", "FARA"]                                    # l. 208-214
CROPC_TO_G = {"CERE": ["SWHE", "DWHE", "RYEM", "BARL", "OATS", "MAIZ", "OCER"],             # l. 216-224
              "OILS": ["RAPE", "SUNF", "SOYA", "OOIL"], "INDU": ["TEXT", "TOBA", "OIND"],
              "VEGE": ["TOMA", "OVEG"], "FRUI": ["APPL", "OFRU"], "FARA": ["MAIF", "ROOF", "OFAR"]}
GRPR = ["CERE", "OILS", "INDU", "VEGE", "FRUI", "FORA", "MEAS"]                             # l. 232-240
ROWS_TO_G = {"CERE": ["SWHE", "DWHE", "RYEM", "BARL", "OATS", "MAIZ", "OCER"],              # l. 242-251
             "OILS": ["RAPE", "SUNF", "SOYA", "OOIL"], "INDU": ["TOBA", "TEXT", "OIND"],
             "VEGE": ["TOMA", "OVEG"], "FRUI": ["APPL", "CITR", "TAGR", "OFRU"],
             "FORA": ["MAIF", "ROOF", "OFAR", "GRAS"], "MEAS": ["BEEF", "PORK", "POUM", "SGMT"]}
REQST = ["ENNE", "CRPR", "FILG", "FICT", "FISM", "FISF"]                                     # l. 456
# S_ColsEst, l. 385-420: literal members, then the global sets MPACT, LandUseARTO, GRPC, MRKBALE; OSET removed
S_COLS_LITERAL = ["UAAR", "ARTO", "GROF", "QUTS", "MAPR", "UVAG", "UVAD", "EAAG", "PRCY", "FATS", "PROT", "CSSP",
                  "EXPE", "INHA", "DOMM", "NTRD", "LU", "LOSF", "NAGR", "SECG", "CTAX", "PRCI", "PRCB", "PRCBY",
                  "N_CAL", "N_PRO", "N_FAT", "foodSh"]
S_COLS_SETS = ["MPACT", "LandUseARTO"]
# CAPTRD's own MrkBalE (sets_captrd.gms l. 292-294), not the CAPMOD one of sets.gms l. 5271 (8 positions)
MRKBALE = ["GROF", "IMPT", "EXPT", "FEDM", "SEDF", "SEDM", "INDM", "PRCM", "BIOF", "HCOM", "LOSF", "LOSM", "MAPR", "INTP"]
# captrd.gms l. 833: S_ColsEst(REQSC) = YES after the data load (the nutrient contents; sets.gms l. 2133 REQSC = REQS_SET)
# S_RowsEst, l. 422-460: the global sets O, SECO, SECO_BIOF, FUEL_ROWS, MLKSECO, IYANI, FEED, then literals and GRPR;
# minus FOUT (l. 454); plus REQST (l. 458); minus the outputs no activity produces (l. 459, PACT_TO_O)
S_ROWS_SETS = ["O", "SECO", "SECO_BIOF", "FUEL_ROWS", "MLKSECO", "IYANI", "FEED"]
S_ROWS_LITERAL = ["FENI", "FPRI", "HFCS", "LEVL", "TOOU", "YDAYS", "DAYS", "HERD", "DAILY", "SLGW",
                  "LABO", "LABN", "LABH", "LABT", "LABF", "LABP", "NONS", "INCE"]
NO_YIELD_DROP_LITERAL = ["PARI", "MAIF", "ROOF", "POTA", "SUGB", "PULS", "TOBA", "TAGR", "TEXT", "DCOL", "DCOH",
                         "SOWS", "HENS", "OOIL", "GRAE", "GRAI"]                              # l. 465-467 (+ CERE, OILS)
FIX_YIELD = ["OCRO", "OOIL", "OANI"]                                                         # l. 472


def _members(ref: Path, name: str, dim: int = 1):
    f = ref / f"{name}.csv"
    if not f.exists():
        idx = {r["set"].lower(): r["file"] for r in csv.DictReader(open(ref / "_index.csv"))}
        if name.lower() not in idx:
            raise KeyError(f"CAPRI set {name} not in {ref}")
        f = ref / f"{idx[name.lower()]}.csv"
    rows = list(csv.reader(open(f, encoding="utf-8")))[1:]
    return [tuple(r[:dim]) if dim > 1 else r[0] for r in rows]


def _write(name: str, rows, dim: int = 1):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"{name}.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow([f"d{k}" for k in range(dim)])
        for r in rows:
            w.writerow(r if dim > 1 else [r])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", default=str(ROOT / "capri_reference" / "sets" / "simini_21730"))
    args = ap.parse_args()
    ref = Path(args.ref)

    cols = list(S_COLS_LITERAL)
    for s in S_COLS_SETS:
        cols += _members(ref, s)
    cols += GRPC + MRKBALE + list(_members(ref, "REQSC"))
    cols = sorted(set(cols) - {"OSET"}, key=str.upper)

    rows = []
    for s in S_ROWS_SETS:
        rows += _members(ref, s)
    rows += S_ROWS_LITERAL + GRPR + REQST
    rows = set(rows) - set(_members(ref, "FOUT"))
    produced = {o for _a, o in _members(ref, "PACT_TO_O", 2)}
    outputs = set(_members(ref, "O"))
    rows = sorted(r for r in rows if not (r in outputs and r not in produced))

    _write("s_colsest", cols)
    _write("s_rowsest", rows)
    _write("grpc", GRPC)
    _write("cropc_to_g", [(c, g) for g, cs in CROPC_TO_G.items() for c in cs], 2)
    _write("grpr", GRPR)
    _write("rows_to_g", [(r, g) for g, rs in ROWS_TO_G.items() for r in rs], 2)
    _write("reqst", REQST)
    _write("mrkbale", MRKBALE)
    _write("noyielddrop", sorted(set(NO_YIELD_DROP_LITERAL) | set(_members(ref, "CERE")) | set(_members(ref, "OILS"))))
    _write("fixyield", FIX_YIELD)
    print(f"S_ColsEst {len(cols)}, S_RowsEst {len(rows)} -> {OUT}")


if __name__ == "__main__":
    main()
