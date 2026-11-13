"""CAPRI's Nordic aid (policy/nordicaid.gms, included by pol_input/mtr_RD.gms in CAP_2014_2020.gms's chain): the
national aid to northern Finland and Sweden granted on their accession, regulation 142 (the premium module, P2c).

  capri_data/<base year>/policy/nordic_aid_rates.csv    scheme, group, nordic_region, basis, rate
        p_nordicAid_2_5_perLU (basis per_lu: EUR per livestock unit, or per ton of milk) and p_nordicAid_2_9_PerHa
        (per_ha: EUR per ha) by premium group and Nordic aid region
  capri_data/<base year>/policy/nordic_aid_ceilings.csv  scheme, ms, ceiling_meur
        p_nordicAid_2_6_ceilingsAnimals + p_nordicAid_2_10_ceilingsCrops (million EUR a year, the 2005 amounts)
  capri_data/<base year>/policy/nordic_aid_region_shares.csv region, nordic_region, share
        p_nordicAidRegionShare: the share of a CAPRI region in each Nordic aid region
  capri_data/<base year>/policy/nordic_aid_schemes.csv  scheme, apptype, year, source
        each scheme's application type as the file sets it (psdpay_noaCrop per level, psdpay_noaAnim per livestock
        unit, dpNoaMilk per yield, the last assignment winning as in GAMS) and the year it declares (1995)

Scheme labels as sim_ini's PSDPAY writes them (the tables write dpNoaShgm, the set dpNoaSHGM).

    python tools/build/build_nordic_aid.py [--gams DIR] [--sets DIR]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT / "tools" / "build"))
sys.path.insert(0, str(ROOT))
from paths import REFERENCE, SOURCES  # noqa: E402
from build_cap14_entitlements import gams_table  # noqa: E402
from capri_mod.csvio import read_csv, to_csv  # noqa: E402

NORDIC = Path("policy") / "nordicaid.gms"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gams", type=Path, default=SOURCES / "gams")
    ap.add_argument("--sets", type=Path, default=REFERENCE / "sets" / "simini_21730")
    ap.add_argument("--base-year", default="2017")
    a = ap.parse_args()
    out = ROOT / "capri_data" / a.base_year / "policy"
    text = (a.gams / NORDIC).read_text(encoding="latin-1")
    src = f"star 3.0 {NORDIC.as_posix()}"

    def labels(name):
        return [str(x) for x in read_csv(a.sets / f"{name}.csv", keep_default_na=False).d0]

    canon = {s.lower(): s for s in labels("PSDPAY")}

    def scheme(s):
        if s.lower() not in canon:
            raise SystemExit(f"nordicaid.gms: scheme {s} not in PSDPAY")
        return canon[s.lower()]

    rates = []
    for tab, basis in (("p_nordicAid_2_5_perLU", "per_lu"), ("p_nordicAid_2_9_PerHa", "per_ha")):
        for (row, rnoa), v in gams_table(text, tab).items():
            s, g = row.split(".")
            if v:
                rates.append((scheme(s), g.upper(), rnoa, basis, v))
    ceilings = {}
    for tab in ("p_nordicAid_2_6_ceilingsAnimals", "p_nordicAid_2_10_ceilingsCrops"):
        for (s, ms), v in gams_table(text, tab).items():
            ceilings[(scheme(s), ms)] = ceilings.get((scheme(s), ms), 0.0) + v
    shares = [(r, n, v) for (r, n), v in gams_table(text, "p_nordicAidRegionShare").items() if v]

    # the application types: the file's assignments in order, the last one a scheme gets winning
    year = re.findall(r'p_premDataE\(rs,"(\d{4})",psdpay_noa,psGroup\)', text)
    if len(set(year)) != 1:
        raise SystemExit(f"nordicaid.gms: the declared year {year}")
    apptype = {}
    for target, t in re.findall(r'p_premDataE\(rs,"\d{4}",("?\w+"?),"appType"\)[^=]*=\s*(\w+)\s*;', text, re.S):
        members = [target.strip('"')] if target.startswith('"') else labels(target)
        for s in members:
            apptype[scheme(s)] = t
    # GAMS sets the type where the scheme has a ceiling or a rate in the region (l. 133-145)
    used = {s for s, *_ in rates} | {s for s, _ in ceilings}
    if used - set(apptype):
        raise SystemExit(f"nordicaid.gms: schemes with rates and no application type: {sorted(used - set(apptype))}")
    schemes = [(s, apptype[s], int(year[0]), src) for s in sorted(used)]

    for frame, name, keys in (
            (pd.DataFrame(rates, columns=["scheme", "group", "nordic_region", "basis", "rate"]), "nordic_aid_rates.csv",
             ["scheme", "group", "nordic_region"]),
            (pd.DataFrame([(s, m, v) for (s, m), v in ceilings.items()], columns=["scheme", "ms", "ceiling_meur"]),
             "nordic_aid_ceilings.csv", ["scheme", "ms"]),
            (pd.DataFrame(shares, columns=["region", "nordic_region", "share"]), "nordic_aid_region_shares.csv",
             ["region", "nordic_region"]),
            (pd.DataFrame(schemes, columns=["scheme", "apptype", "year", "source"]), "nordic_aid_schemes.csv",
             ["scheme"])):
        if frame.duplicated(keys).any():
            raise SystemExit(f"{name}: a key written twice")
        to_csv(frame.sort_values(keys).reset_index(drop=True), out / name, index=False)
    print(f"nordic aid: {len(rates)} rates, {len(ceilings)} ceilings, {len(shares)} region shares, "
          f"application types {sorted(set(apptype.values()))}, year {year[0]}")


if __name__ == "__main__":
    main()
