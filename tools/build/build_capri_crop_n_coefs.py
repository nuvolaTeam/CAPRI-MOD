"""CAPRI's per-crop nitrogen coefficients per region, 2030 reference (for the gross N balance).

Source: res_2_1730greendeal_refdefaulta (dataOut), supplied by the project lead. Per CAPRI region
and crop: LEVL (1000 ha), YILD (kg/ha), NITF (kg N/ha removed, CAPRI e_EXPPRD coefficient),
NCRD (kg N/ha from crop residues and atmospheric deposition, global/fromimpact/sets.gms), MANN (the crop's own N output
to the soil, kg N/ha: CAPRI's e_CRESID coefficient, supply_model.gms: (v_Cresid + v_atmosd) x UAA = sum levl x
DATA(crop, MANN) x (techFact + 1), MANN being FOUT_T_N's output for NITF), nutNed_biofix (1000 t N fixed).
The region's level-weighted NCRD and MANN are the same total (CRESID + ATMOSD), spread differently over the crops;
the balance's crop coefficient is MANN (KNOWN_ISSUES K163).

Use (capri_mod/environmental/nitrogen.py, _capri_crop_n): per ha x the run's yield / the data's yield. In a 2030 run
the data are the projected ones (ProjectionModule.project_data scales data["yields"] to 2030), so the factor is about
1 at the 2030 baseline and CAPRI's 2030 coefficients enter once (checked 4 November 2026 on gate 16's baseline:
removal per region / CAPRI's EXPPRD median 0.999, EU 0.999; BIOFIX EU 0.987).

Output: capri_data/baselines/capri_greendeal_ref/1730/environment/capri_crop_n_coefs_2030.csv
  capri_region, crop, levl, yild, nitf, ncrd, mann, biofix_t
Usage: python tools/build/build_capri_crop_n_coefs.py <zip>
"""
import csv
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "environment" / "capri_crop_n_coefs_2030.csv"
P1 = re.compile(r"'([^']+)'\.''\.'([^']+)'\.'(LEVL|YILD|NITF|NCRD|MANN)'\.'2030'\s+([-0-9.eE+]+)")
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
        rows.append([r, c, d.get("LEVL"), d.get("YILD", ""), d.get("NITF"), d.get("NCRD", ""), d.get("MANN", ""), d.get("BIOFIX", "")])
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["capri_region", "crop", "levl", "yild", "nitf", "ncrd", "mann", "biofix_t"]); w.writerows(rows)
    print(len(rows), "rows,", len({r[0] for r in rows}), "regions ->", OUT.name)


if __name__ == "__main__":
    main(sys.argv[1])
