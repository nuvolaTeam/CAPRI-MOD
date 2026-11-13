"""CAPRI's CAP 2014-2020 ceilings and the endogenous entitlement limit of its 2030 simulation (KNOWN_ISSUES K136):
the inputs of scen/base_scenarios/CAP_2014_2020.gms and policy/def_endCut.gms, as CAPRI writes them, for the
supply model's sumEntl_ / overShotEntl_ (supply_model.gms l. 1885-1892, objective l. 4768). The model computes the
ceilings from them (capri_mod/supply/entitlements.py), as CAPRI's chain does at run time.

Outputs (capri_data/2017/policy/):
  cap14_national_ceilings.csv  ms, year, ceiling_meur
      p_2013_1307_AnnexII (CAP_2014_2020.gms l. 103-131): the national ceilings of Regulation 1307/2013 Annex II,
      million EUR, the years as written (2015-2019, Croatia to 2022)
  cap14_ceiling_shares.csv     ms, year, scheme, pct
      the payments CAPRI takes out of the national ceiling in percent of it: p_BPSYF (DPYOUNG, young farmers),
      p_BPSRED (DPFIRHA, redistributive payment), p_BPSNATCO (DPNATCO, areas with natural constraints)
      (l. 186-282); the tables' nonzero cells (GAMS keeps no zero)
  cap14_pillar_transfers.csv   ms, year, pct
      p_cap_2013_2020_transfers_dp_rd("rel", ms, year) (scen/Premiums/cap_2013_2020_transfers.gms): the transfer
      from pillar 1 to pillar 2 in percent of the national ceiling. A cell written EPS (Romania 2019-2020) is a row
      with pct 0: it holds the year at zero (GAMS does not fill it from the year before). The transfer from pillar 2
      to pillar 1 (p_cap_2013_2020_transfers_rd_dp) is not written: it is a percentage of the member state's pillar-2
      ceilings of the years before the simulation year, which policy/del_policy.gms has set to zero before the file
      runs (CAP_2014_2020.gms l. 52, before l. 147), so CAPRI's transfer is zero (checked: the 2030 BPS ceilings of
      HR, HU, MT, PL and SK in CAPRI's reference dataOut have none)
  cap14_coupled_ceilings.csv   region, year, scheme, ceiling_meur
      the voluntary coupled support (scen/Premiums/Coupling/vcs_2015_2020.gms, through CAP_2013_2020_vcs.gms) and
      the crop-specific cotton payment (CropSpecificPremium_2015_2020.gms, through CAP_2013_2020_cscs.gms), each
      scheme's ceiling per year in million EUR (the files' EUR / 1e6, as CAPRI divides them)
  cap14_settings.csv           item, key, value, source
      the greening share of the national ceiling (p_dpGreeningShareCAP14, CAP_2014_2020.gms), the BPS years
      (BPSYEARS, policy/policy_sets.gms), the member states under the single area payment scheme (DPCAP14_SAPS) and
      the payment schemes cut endogenously (dpEndCut, def_endCut.gms) and the simulation year whose trend levels
      the levels file holds (SIMY), the last three from sim_ini_21730's sets
  cap14_entitlement_levels.csv region, activity, trd_kha
      DATA(ru, mcact, "LEVL", "TRD") of sim_ini_21730 for CAPRI's regional units (RU) and crop activities (MCACT):
      the trend levels whose sum is each region's entitlement limit (def_endCut.gms, p_entlLimit "Limit")

    python tools/build/build_cap14_entitlements.py [--gams DIR] [--sets DIR] [--simini DIR]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib")]
from paths import REFERENCE, SOURCES  # noqa: E402  (CAPRI's material outside the repository)
from capri_mod.csvio import read_csv, to_csv  # noqa: E402

OUT = ROOT / "capri_data" / "2017" / "policy"
CAP14 = Path("scen") / "base_scenarios" / "CAP_2014_2020.gms"
TRANSFERS = Path("scen") / "Premiums" / "cap_2013_2020_transfers.gms"
COUPLED = (Path("scen") / "Premiums" / "Coupling" / "vcs_2015_2020.gms",
           Path("scen") / "Premiums" / "Coupling" / "CropSpecificPremium_2015_2020.gms")
POLICY_SETS = Path("policy") / "policy_sets.gms"
#: the share tables of CAP_2014_2020.gms and the payment each one takes out of the national ceiling
SHARE_TABLES = {"p_BPSYF": "DPYOUNG", "p_BPSRED": "DPFIRHA", "p_BPSNATCO": "DPNATCO"}


def gams_table(text: str, name: str) -> dict:
    """{(row, column): value} of the GAMS table `name` in text: each cell is assigned to the column header it
    overlaps, or, written just beside one (CAP_2014_2020.gms's left-aligned zeros), to the header whose start or end
    is nearest; two cells of a row under one column stop the build. EPS is kept as 0.0 (a present cell), comment
    lines skipped."""
    m = re.search(rf"^\s*table\s+{name}\s*\([^)]*\)[^\n]*\n(.*?)^\s*;", text, re.S | re.I | re.M)
    if m is None:
        raise SystemExit(f"table {name} not found")
    lines = [l.expandtabs(8) for l in m.group(1).splitlines() if l.strip() and not l.lstrip().startswith("*")]
    head = [(t.start(), t.end(), t.group()) for t in re.finditer(r"\S+", lines[0])]
    out = {}
    for l in lines[1:]:
        toks = list(re.finditer(r"\S+", l))
        row = toks[0].group()
        taken = set()
        for t in toks[1:]:
            cols = [c for s, e, c in head if t.start() < e and s < t.end()]
            if not cols:
                gap = min(min(abs(t.start() - s), abs(t.end() - e)) for s, e, _ in head)
                cols = [c for s, e, c in head if min(abs(t.start() - s), abs(t.end() - e)) == gap]
            if len(cols) != 1 or cols[0] in taken:
                raise SystemExit(f"table {name} row {row}: cell {t.group()!r} at {t.start()} under {cols} columns")
            taken.add(cols[0])
            v = t.group()
            out[(row, cols[0])] = 0.0 if v.lower() == "eps" else float(v)
    return out


def scalar_assignment(text: str, name: str) -> float:
    """The value of a one-line assignment name(MS) = value; in text (the only one)."""
    hits = re.findall(rf"^\s*{name}\s*\(\s*MS\s*\)\s*=\s*([-\d.Ee+]+)\s*;", text, re.M | re.I)
    if len(hits) != 1:
        raise SystemExit(f"{name}: {len(hits)} assignments of the form {name}(MS) = value")
    return float(hits[0])


def coupled_ceilings(text: str) -> list:
    """(region, year, scheme, ceiling in million EUR) of the lines p_premDataE("R","Y","scheme","ceilval")=EUR;"""
    rx = re.compile(r'^\s*p_premDataE\("(\w+)","(\d{4})","([^"]+)","ceilval"\)\s*=\s*([-\d.Ee+]+)\s*;', re.I | re.M)
    return [(r, int(y), s, float(v) / 1e6) for r, y, s, v in rx.findall(text)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gams", type=Path, default=SOURCES / "gams", help="CAPRI's gams folder (star 3.0)")
    ap.add_argument("--sets", type=Path, default=REFERENCE / "sets" / "simini_21730")
    ap.add_argument("--simini", type=Path, default=REFERENCE / "simini" / "simini_21730")
    a = ap.parse_args()

    cap = (a.gams / CAP14).read_text(errors="ignore")
    ann = gams_table(cap, "p_2013_1307_AnnexII")
    nat = pd.DataFrame([(r, int(y), v) for (r, y), v in ann.items()], columns=["ms", "year", "ceiling_meur"])

    sh = []
    for tab, scheme in SHARE_TABLES.items():
        sh += [(r, int(y), scheme, v) for (r, y), v in gams_table(cap, tab).items() if v != 0.0]
    shares = pd.DataFrame(sh, columns=["ms", "year", "scheme", "pct"])

    tr = gams_table((a.gams / TRANSFERS).read_text(errors="ignore"), "p_cap_2013_2020_transfers_dp_rd")
    if any(not r.startswith("rel.") for r, _ in tr):
        raise SystemExit("p_cap_2013_2020_transfers_dp_rd: a row that is not 'rel.MS'")
    transfers = pd.DataFrame([(r[4:], int(y), v) for (r, y), v in tr.items()], columns=["ms", "year", "pct"])

    cp = []
    for f in COUPLED:
        cp += coupled_ceilings((a.gams / f).read_text(errors="ignore"))
    coupled = pd.DataFrame(cp, columns=["region", "year", "scheme", "ceiling_meur"])
    if coupled.duplicated(["region", "year", "scheme"]).any():
        raise SystemExit("a coupled-support ceiling assigned twice")

    bps = re.search(r"SET\s+BPSYEARS\s*\([^)]*\)\s*/\s*(\d{4})\s*\*\s*(\d{4})\s*/", (a.gams / POLICY_SETS).read_text(
        errors="ignore"), re.I)
    if bps is None:
        raise SystemExit("set BPSYEARS not found in policy_sets.gms")
    src_cap = f"star 3.0 {CAP14.as_posix()}"
    settings = [("greening_share", "MS", scalar_assignment(cap, "p_dpGreeningShareCAP14"), src_cap),
                ("bps_years", "first", float(bps.group(1)), f"star 3.0 {POLICY_SETS.as_posix()}"),
                ("bps_years", "last", float(bps.group(2)), f"star 3.0 {POLICY_SETS.as_posix()}")]
    settings += [("saps", ms, 1.0, "sim_ini_21730 set DPCAP14_SAPS")
                 for ms in read_csv(a.sets / "DPCAP14_SAPS.csv", keep_default_na=False).d0]
    settings += [("cut_scheme", dp, 1.0, "sim_ini_21730 set dpEndCut (policy/def_endCut.gms)")
                 for dp in read_csv(a.sets / "dpEndCut.csv", keep_default_na=False).d0]
    simy = list(read_csv(a.sets / "SIMY.csv", keep_default_na=False).d0)
    if len(simy) != 1:
        raise SystemExit(f"SIMY: {simy}, one simulation year expected")
    settings += [("trend_year", "TRD", float(simy[0]), "sim_ini_21730 set SIMY (the year of DATA's TRD levels)")]
    settings = pd.DataFrame(settings, columns=["item", "key", "value", "source"])

    ru = set(read_csv(a.sets / "RU.csv", keep_default_na=False).d0)
    mcact = set(read_csv(a.sets / "MCACT.csv", keep_default_na=False).d0)
    D = read_csv(a.simini / "DATA.csv.gz", keep_default_na=False, usecols=["d0", "d1", "d2", "d3", "value"])
    D = D[(D.d2 == "LEVL") & (D.d3 == "TRD") & D.d0.isin(ru) & D.d1.isin(mcact)]
    levels = (D.rename(columns={"d0": "region", "d1": "activity", "value": "trd_kha"})
              [["region", "activity", "trd_kha"]].sort_values(["region", "activity"]))

    OUT.mkdir(parents=True, exist_ok=True)
    for frame, name, keys in ((nat, "cap14_national_ceilings.csv", ["ms", "year"]),
                              (shares, "cap14_ceiling_shares.csv", ["ms", "year", "scheme"]),
                              (transfers, "cap14_pillar_transfers.csv", ["ms", "year"]),
                              (coupled, "cap14_coupled_ceilings.csv", ["region", "year", "scheme"]),
                              (settings, "cap14_settings.csv", ["item", "key"]),
                              (levels, "cap14_entitlement_levels.csv", ["region", "activity"])):
        to_csv(frame.sort_values(keys).reset_index(drop=True), OUT / name, index=False)
    print(f"cap14: {nat.ms.nunique()} national ceilings, {len(shares)} share cells, {len(transfers)} transfer cells, "
          f"{coupled.scheme.nunique()} coupled schemes, {levels.region.nunique()} regions' trend levels")


if __name__ == "__main__":
    main()
