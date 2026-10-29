"""CAPRI's 2030 CAP budgets and the per-activity premium split by scheme (Pillar I, LFA, Natura 2000, agri-environment).

Source: CAPRI's 2030 reference results, dataOut of res_2_1730greendeal_refpol_endotech_all_inidefaulta (the run the
model's 2030 calibration uses):
  - dataOut(R, '', 'CEILVAL', scheme, '2030'): the budget of each premium scheme, Mio EUR (p_premDataE(...,'ceilval'),
    policy/rd_logic.gms l. 160-170 for the RD schemes, policy/calc_mtr_top.gms for Pillar I), per member state and
    CAPRI NUTS2 region;
  - dataOut(R, 'PRME', activity, scheme, '2030'): the premium per unit of activity paid under each scheme, with
    DPTOTAL the total over schemes;
  - dataOut(R, '', activity, 'LEVL', '2030'): activity levels, to weight CAPRI activities into model activities.

Outputs
  capri_data/2017/policy/cap_ceilings_2030.csv     CAPRI region x scheme budget (Mio EUR): DPPIL1, DPPIL2, DPRD_LFA,
                                                    DPRD_N2K, DPAE, DPNAT (national payments: complementary
                                                    national direct payments, Norway's schemes), DPTOTAL (Eps -> 0)
  capri_data/2017/policy/premium_scheme_shares_2030.csv
                                                    model region x activity: the share of the activity's premium per
                                                    unit paid under DPPIL1, DPRD_LFA, DPRD_N2K, DPAE and DPNAT
                                                    (each over DPTOTAL), level-weighted over the activity's CAPRI members; region
                                                    as tools/lib/_model_regions.region_to_capri, else its member state

They replace, in the payments engine (capri_mod/policy/policy_module.py), the participation shares 30% (ANC),
20% (agri-environment) and 8% (organic) and the "approximate 2023-2027" national envelopes (PROXY_AUDIT S289, S292).

    python tools/build/build_cap_ceilings_2030.py [--src CSV]
"""
from __future__ import annotations

import argparse
import importlib.util
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = Path("/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv")
OUT_CEIL = ROOT / "capri_data" / "2017" / "policy" / "cap_ceilings_2030.csv"
OUT_SHARE = ROOT / "capri_data" / "2017" / "policy" / "premium_scheme_shares_2030.csv"
SCHEMES = ("DPPIL1", "DPPIL2", "DPRD_LFA", "DPRD_N2K", "DPAE", "DPNAT", "DPTOTAL")
SHARES = ("DPPIL1", "DPRD_LFA", "DPRD_N2K", "DPAE", "DPNAT")
# model activity -> CAPRI activities (crops: tools/build/build_capri_base.CROP_MAP; animals: tools/build/build_livestock_units.ANIMALS)
CROPS = {"SWHE": ("SWHE",), "DWHE": ("DWHE",), "RYEM": ("RYEM",), "BARL": ("BARL",), "OATS": ("OATS",),
         "CORN": ("MAIZ",), "OCER": ("OCER",), "PARI": ("PARI",), "PULS": ("PULS",), "OCRO": ("OCRO",),
         "OIND": ("OIND",), "NURS": ("NURS",), "FLOW": ("FLOW",), "SUGB": ("SUGB",), "POTA": ("POTA",),
         "TOMA": ("TOMA",), "OVEG": ("OVEG",), "APPL": ("APPL",), "OFRU": ("OFRU",), "CITR": ("CITR",),
         "TAGR": ("TAGR",), "WINE": ("TWIN",), "OLIV": ("OLIV",), "TABO": ("TABO",), "GRAS": ("GRAS",),
         "TOBA": ("TOBA",), "MAIF": ("MAIF",), "RAPE": ("RAPE",), "SUNF": ("SUNF",), "SOYA": ("SOYA",),
         "OOIL": ("OOIL",), "TEXT": ("TEXT",), "OFOD": ("OFAR", "ROOF"), "SETA": ("SETA", "FALL")}
ANIMALS = {"DCOW": ("DCOL", "DCOH"), "BCOW": ("SCOW",), "BULL": ("BULL", "BULH"), "HFRS": ("HEIL", "HEIH", "HEIR"),
           "CALV": ("CAMF", "CAFF", "CAMR", "CAFR"), "PIGS": ("SOWS",), "PIGF": ("PIGF",), "LAYS": ("HENS",),
           "BROI": ("POUF",), "SHGM": ("SHGM",), "SHGF": ("SHGF",), "OANI": ("OANI",)}
MEMBERS = {**CROPS, **ANIMALS}
CAPRI_ACTS = {c for v in MEMBERS.values() for c in v}


def num(s: str) -> float:
    s = s.strip().rstrip(",").strip()
    return 0.0 if s.upper() == "EPS" else float(s)


def read(src: Path):
    ceil = defaultdict(dict)
    prme = defaultdict(dict)
    levl = defaultdict(dict)
    rx_c = re.compile(r"^'([A-Z0-9_]{8})'\.''\.'CEILVAL'\.'([^']+)'\.'2030'\s+(\S+)")
    rx_p = re.compile(r"^'([A-Z0-9_]{8})'\.'PRME'\.'([A-Z0-9]+)'\.'([^']+)'\.'2030'\s+(\S+)")
    rx_l = re.compile(r"^'([A-Z0-9_]{8})'\.''\.'([A-Z0-9]+)'\.'LEVL'\.'2030'\s+(\S+)")
    with open(src, errors="ignore") as f:
        for line in f:
            if "'2030'" not in line:
                continue
            m = rx_c.match(line)
            if m and m.group(2) in SCHEMES:
                ceil[m.group(1)][m.group(2)] = num(m.group(3)); continue
            m = rx_p.match(line)
            if m and m.group(2) in CAPRI_ACTS and m.group(3) in SHARES + ("DPTOTAL",):
                prme[m.group(1)][(m.group(2), m.group(3))] = num(m.group(4)); continue
            m = rx_l.match(line)
            if m and m.group(2) in CAPRI_ACTS:
                levl[m.group(1)][m.group(2)] = num(m.group(3))
    return ceil, prme, levl


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=SRC)
    a = ap.parse_args()
    ceil, prme, levl = read(a.src)
    # member states and their NUTS regions (not the EU aggregates EU, EU27yr19, EU_EAST, A_EU_WEST, ...)
    eu = sorted(r for r in ceil if re.fullmatch(r"[A-Z]{2}[0-9A-Z]{6}", r) and not r.startswith("EU"))
    c = pd.DataFrame({r: {s: ceil[r].get(s, 0.0) for s in SCHEMES} for r in eu}).T[list(SCHEMES)]
    c.index.name = "capri_region"
    c.to_csv(OUT_CEIL)

    sp = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(sp); sp.loader.exec_module(mr)
    to_c8 = mr.region_to_capri()
    rows = []
    for reg in mr.model_regions():
        for act, mem in MEMBERS.items():
            for src in (to_c8.get(reg), mr.national_code(reg)):
                if not src or src not in prme:
                    continue
                w = {x: levl.get(src, {}).get(x, 0.0) for x in mem}
                tot = sum(w[x] * prme[src].get((x, "DPTOTAL"), 0.0) for x in mem)
                if tot <= 0:
                    continue
                row = dict(region=reg, activity=act, capri_region=src)
                for s in SHARES:
                    row[s] = sum(w[x] * prme[src].get((x, s), 0.0) for x in mem) / tot
                rows.append(row)
                break
    sh = pd.DataFrame(rows)
    sh.to_csv(OUT_SHARE, index=False)
    nat = int((sh.capri_region.str[2:] == "000000").sum())
    chk = (sh[list(SHARES)].sum(axis=1) - 1.0).abs()
    print(f"cap_ceilings_2030.csv: {len(c)} CAPRI regions; premium_scheme_shares_2030.csv: {len(sh)} region x activity "
          f"rows ({nat} from the member-state row); max |sum of shares - 1| = {chk.max():.2e} "
          f"(rows not summing to 1: {int((chk > 1e-6).sum())})")


if __name__ == "__main__":
    main()
