"""CAPRI's per-crop nitrogen coefficients per region, 2030 reference (for the gross N balance).

Source: res_2_1730greendeal_refdefaulta (dataOut), supplied by the project lead. Per CAPRI region
and crop: LEVL (1000 ha), YILD (kg/ha), NITF (kg N/ha removed, CAPRI e_EXPPRD coefficient),
NCRD (kg N/ha in crop residues), nutNed_biofix (1000 t N fixed); per region the balance items
EXPPRD and CRESID (1000 t) to scale residues to CAPRI's CRESID (e_CRESID).

Output: capri_data/2017/environment/capri_crop_n_coefs_2030.csv
  capri_region, crop, levl, yild, nitf, ncrd, biofix_t
Usage: python tools/build_capri_crop_n_coefs.py <zip>
"""
import csv
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "capri_data" / "2017" / "environment" / "capri_crop_n_coefs_2030.csv"
P1 = re.compile(r"'([^']+)'\.''\.'([^']+)'\.'(LEVL|YILD|NITF|NCRD)'\.'2030'\s+([-0-9.eE+]+)")
P2 = re.compile(r"'([^']+)'\.'nutNed_biofix'\.'([^']+)'\.'NITF'\.'2030'\s+([-0-9.eE+]+)")
AGG = {"ARAB", "CERE", "PERM", "FODD", "SETF", "OILS", "OAR1", "AGGT", "UAAR", "GROF", "INTF", "NETF"}


def main(src):
    v = defaultdict(dict)
    with zipfile.ZipFile(src) as z, z.open(z.namelist()[0]) as fh:
        for raw in fh:
            line = raw.decode("latin-1")
            m = P1.match(line)
            if m:
                v[(m.group(1), m.group(2))][m.group(3)] = float(m.group(4)); continue
            m = P2.match(line)
            if m:
                v[(m.group(1), m.group(2))]["BIOFIX"] = float(m.group(3))
    rows = []
    for (r, c), d in sorted(v.items()):
        if c in AGG or not d.get("LEVL") or "NITF" not in d:
            continue
        rows.append([r, c, d.get("LEVL"), d.get("YILD", ""), d.get("NITF"), d.get("NCRD", ""), d.get("BIOFIX", "")])
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["capri_region", "crop", "levl", "yild", "nitf", "ncrd", "biofix_t"]); w.writerows(rows)
    print(len(rows), "rows,", len({r[0] for r in rows}), "regions ->", OUT.name)


if __name__ == "__main__":
    main(sys.argv[1])
