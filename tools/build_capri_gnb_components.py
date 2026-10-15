"""CAPRI's regional gross nitrogen balance components, 2030 reference (kg N per ha).

Source: CAPRI 2030 Green Deal reference results, res_2_1730greendeal_refdefaulta (dataOut, rows
'perHa'.<item>.'NITF'.'2030'), supplied by the project lead (uploads, zipped csv dump). Items:
MINFER (mineral fertiliser), EXCRET (excretion), BIOFIX, ATMOSD, CRESID (crop residues, input),
EXPPRD (removal with products incl. residues), MTRADE (manure net export), IMPORT, GASTOT, SURTOT,
nutNed_cres_unavailable_perha and nutNed_cres_loss_gasRunTot_perha (residue and deposition N not
available to crops, NUTNED_); fertDist_excr_perha, nutNed_excr_unavailable_perha, fertDist_mine_perha and
nutNed_mine_loss_gasRunTot_perha (manure and mineral N delivered to crops and the parts not available,
NUTNED_: manure availability, mineral efficiency and manure applied per ha for CAPRI's endogenous
availability factor, fert/endoManAvail.gms)
(= MINFER + EXCRET + BIOFIX + ATMOSD + CRESID - EXPPRD - MTRADE; supply_model.gms e_SURTOTHa).

Output: capri_data/2017/environment/capri_gnb_components_2030.csv (capri_region, item, kg_n_per_ha)
Usage: python tools/build_capri_gnb_components.py <zip of res_2_1730greendeal_refdefaulta>
"""
import csv
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "capri_data" / "2017" / "environment" / "capri_gnb_components_2030.csv"
ITEMS = {"MINFER", "EXCRET", "BIOFIX", "ATMOSD", "CRESID", "EXPPRD", "MTRADE", "IMPORT", "GASTOT", "SURTOT"}
PAT = re.compile(r"'([^']+)'\.'perHa'\.'([^']+)'\.'NITF'\.'2030'\s+([-0-9.eE+]+)")
# residue (and deposition) N not available to crops, NUTNED_ (kg/ha of UAA)
PAT2 = re.compile(r"'([^']+)'\.'(nutNed_cres_unavailable_perha|nutNed_cres_loss_gasRunTot_perha|fertDist_excr_perha|"
                  r"nutNed_excr_unavailable_perha|fertDist_mine_perha|nutNed_mine_loss_gasRunTot_perha)'\.'AGGT'\.'NITF'\.'2030'\s+([-0-9.eE+]+)")


def main(src):
    rows = []
    with zipfile.ZipFile(src) as z:
        with z.open(z.namelist()[0]) as fh:
            for raw in fh:
                line = raw.decode("latin-1")
                if "nutNed_" in line or "fertDist_" in line:
                    m = PAT2.match(line)
                    if m:
                        rows.append([m.group(1), m.group(2), float(m.group(3))])
                    continue
                if "'perHa'" not in line:
                    continue
                m = PAT.match(line)
                if m and m.group(2) in ITEMS:
                    rows.append([m.group(1), m.group(2), float(m.group(3))])
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["capri_region", "item", "kg_n_per_ha"]); w.writerows(rows)
    print(len(rows), "rows ->", OUT.name)


if __name__ == "__main__":
    main(sys.argv[1])
