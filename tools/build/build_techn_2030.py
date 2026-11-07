"""CAPRI's per-technology terms of its 2030 simulation start, as CSV: the linear PMP terms per technology and the
technology factors (S1, CAPRI's T1/T2 technologies; docs/design/S1_S2_DESIGN.md, steps 0a and 0b of the
implementation plan, 7 November 2026).

CAPRI gives each crop activity but grassland and set-aside two technologies (intens/techf.gms l. 64-75): T1, the
high-yield variant, and T2, the low-yield one, split 50-50 at the calibration point. Their I/O coefficients differ from
the mean by the technology factors p_technFact (outputs +-20%, inputs +-25%, plant protection +-40%, irrigation water 0,
techf.gms l. 77-108; nutrient removal fert/fertned.gms; sugar beet sugar/techf.gms; the rural-development premiums per
technology policy/rd_logic.gms l. 237-244 and 392-393), and each has its own linear PMP term p_pmpCnst (supply_model.gms QUADRA_
l. 5284).

Source: the sim_ini_21730 restart file's p_pmpCnst and p_technFact (capri_sources/reference/simini/simini_21730,
tools/build/build_simini_reference.py). sim_ini loads p_pmpCnst from the 2030 baseline calibration's
pmppar_21730<CC> files (capmod/create_sim_ini_gdx.gms l. 491-492), the files pmp_quad_techn_2030.csv was exported from
(tools/build/build_pmp_2030.py); sim_ini's p_pmpQuadTechn equals that export (28,169 records, largest relative
difference 2e-14; checked 7 November 2026), so both sets of terms are of the same calibration. The pmppar text dumps
themselves were lost with the workspace on 7 November 2026.

Writes (CAPRI region, activity, row and technology codes; values as CAPRI stores them, nothing mapped or changed):
  capri_data/sources/intermediate/baseline_pmp/pmp_cnst_techn_2030.csv   region, activity, tech, value
      p_pmpCnst, in CAPRI's 2030 money (the deflation to the model's 2017 money, KNOWN_ISSUES K108, is the model
      input's builder's, as for pmp_capri_2030.csv)
  capri_data/sources/intermediate/technology/techn_fact_2030.csv         region, activity, row, tech, value
      p_technFact (LEVL the technology's share at the calibration point; the other rows the relative change of the
      coefficient, +0.2 = 20% above the mean)
GAMS Eps is written as 0 (as CAPRI reads it).

Checks (the build stops otherwise): the (region, activity) pairs with T1/T2 linear terms are exactly those with T1/T2
quadratic terms in pmp_quad_techn_2030.csv (11,041 in sim_ini_21730), and each has its T1 and T2 levels in
p_technFact. For the single technology T the linear and quadratic terms differ as in CAPRI's data: linear terms also
on LABT, EAAP and LandRent (not activities), and activities with a quadratic term but no linear one (p_pmpCnst absent,
i.e. 0: NURS, OCRO, FLOW, OANI, OIND, OOIL, NECR).

    python tools/build/build_techn_2030.py [--ref DIR with p_pmpCnst.csv.gz and p_technFact.csv.gz]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))  # tools/lib/paths.py
from paths import REFERENCE  # noqa: E402  (CAPRI's material outside the repository)

SRC = ROOT / "capri_data" / "sources" / "intermediate" / "baseline_pmp"
QUAD = SRC / "pmp_quad_techn_2030.csv"
OUT_CNST = SRC / "pmp_cnst_techn_2030.csv"
OUT_FACT = ROOT / "capri_data" / "sources" / "intermediate" / "technology" / "techn_fact_2030.csv"
TECHS = ("T1", "T2")


def _ref_rows(path: Path, ndim: int):
    """(keys, value) of a sim_ini reference parameter (d0 ... dn, value, eps; Eps as value 0, eps 1)."""
    assert path.is_file(), (f"{path} missing: python tools/build/build_simini_reference.py --src sim_ini_21730.gdx "
                            f"--tag simini_21730")
    with gzip.open(path, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            yield tuple(r[f"d{i}"] for i in range(ndim)), float(r["value"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", type=Path, default=REFERENCE / "simini" / "simini_21730")
    a = ap.parse_args()
    cnst = sorted(_ref_rows(a.ref / "p_pmpCnst.csv.gz", 3))
    fact = sorted(_ref_rows(a.ref / "p_technFact.csv.gz", 4))

    with open(QUAD, newline="") as fh:
        quad = {(r["region"], r["activity"], r["tech1"]) for r in csv.DictReader(fh) if r["tech1"] in TECHS}
    lin = {k for k, _ in cnst if k[2] in TECHS}
    assert lin == quad, (f"p_pmpCnst and p_pmpQuadTechn cover different T1/T2 pairs: {sorted(lin - quad)[:5]} linear "
                         f"only, {sorted(quad - lin)[:5]} quadratic only")
    levl = {(k[0], k[1], k[3]) for k, v in fact if k[2] == "LEVL" and k[3] in TECHS}
    assert lin <= levl, f"T1/T2 linear terms without a level share in p_technFact: {sorted(lin - levl)[:5]}"

    OUT_CNST.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CNST, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["region", "activity", "tech", "value"])
        for k, v in cnst:
            w.writerow([*k, repr(v)])
    OUT_FACT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FACT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["region", "activity", "row", "tech", "value"])
        for k, v in fact:
            w.writerow([*k, repr(v)])
    print(f"{OUT_CNST.name}: {len(cnst)} records ({len(lin)} T1/T2); {OUT_FACT.name}: {len(fact)} records")


if __name__ == "__main__":
    main()
