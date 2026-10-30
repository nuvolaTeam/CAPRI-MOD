"""CAPRI's fertiliser-efficiency options (cropMiti, target N2OSYN) from the mitigation data the
Green Deal runs use.

Source: dat/scen/ghgtech/miti_data_jul15.gdx, symbol p_ghgMiti (miti_data_type = _jul15 in
pol_input/greendeal/refpol_endotech_all_sup.gms), dumped with gdxdump by the project lead ->
capri_data/sources/ghgtech/miti_data_jul15_p_ghgMiti.txt, converted to capri_data/sources/ghgtech/
miti_data_jul15_p_ghgMiti.csv by tools/build/convert_sources_to_csv.py. National entries for the options without
farm-size cost curves; regional (NUTS 2) entries for VRT_SRUC (farm-size dependent, its own QEmitt,
costParSqr and pmpParSqr; envind/ghgMiti.gms l. 52-57 forms its national QEmitt as the mean of the
regional ones).

Output: capri_data/2017/abatement/fert_options_jul15.csv
  region (CAPRI code), option, costParLin, costParSqr, pmpParSqr, revenue, relSubs0, relSubs1,
  IniShare, MaxShare, QEmitt, QEmitt_noc
"""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources" / "ghgtech" / "miti_data_jul15_p_ghgMiti.csv"
OUT = ROOT / "capri_data" / "2017" / "abatement" / "fert_options_jul15.csv"
COLS = ["costParLin", "costParSqr", "pmpParSqr", "revenue", "relSubs0", "relSubs1", "IniShare", "MaxShare", "QEmitt"]


def main():
    v = defaultdict(dict)
    with open(SRC, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["activity"] == "cropMiti" and r["target"] == "N2OSYN":
                v[(r["region"], r["technology"].upper())][r["info"]] = float(r["value"])
    # national QEmitt of VRT_SRUC = mean of its regional values (ghgMiti.gms l. 52-57)
    reg_q = defaultdict(list)
    for (r, o), d in v.items():
        if o == "VRT_SRUC" and not r.endswith("000000") and "QEmitt" in d:
            reg_q[r[:2] + "000000"].append(d["QEmitt"])
    for ms, qs in reg_q.items():
        v[(ms, "VRT_SRUC")].setdefault("QEmitt", sum(qs) / len(qs))
    noc = {r: d.get("QEmitt") for (r, o), d in v.items() if o == "NOC"}
    rows = []
    for (r, o), d in sorted(v.items()):
        if o == "NOC":
            continue
        q0 = noc.get(r) or noc.get(r[:2] + "000000")
        rows.append([r, o] + [d.get(c, "") for c in COLS] + [q0 if q0 is not None else ""])
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["region", "option"] + COLS + ["QEmitt_noc"]); w.writerows(rows)
    print(len(rows), "rows ->", OUT.name, "| options:", sorted({r[1] for r in rows}))


if __name__ == "__main__":
    main()
