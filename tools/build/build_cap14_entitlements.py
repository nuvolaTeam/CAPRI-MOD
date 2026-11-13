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
      the voluntary coupled support (scen/Premiums/Coupling/vcs_2015_2020.gms, through CAP_2013_2020_vcs.gms), the
      crop-specific cotton payment (CropSpecificPremium_2015_2020.gms, through CAP_2013_2020_cscs.gms) and the
      complementary national direct payments (CNDP_2015_2020.gms, through CAP_2013_2020_CNDP.gms), each scheme's
      ceiling per year in million EUR (the files' values divided as each wrapper divides them: EUR / 1e6, thousand
      EUR / 1000)
  cap14_coupled_rates.csv      region, year, scheme, group, rate
      the same files' premium rates per premium group (pgvcsDCOW, pgvcsPULS, ... ; EUR per unit of the group's
      activities, policy.gms's PRMR), as written
  cap14_settings.csv           item, key, value, source
      the greening share of the national ceiling (p_dpGreeningShareCAP14, CAP_2014_2020.gms), the area schemes'
      rates per premium group (area_rate_PGSAPS: DPGREEN, DPYOUNG, DPFIRHA, DPNATCO, DPBPS_SAPS 1000), the BPS years
      (BPSYEARS, policy/policy_sets.gms), the member states under the single area payment scheme (DPCAP14_SAPS) and
      the payment schemes cut endogenously (dpEndCut, def_endCut.gms) and the simulation year whose trend levels
      the levels file holds (SIMY), the last three from sim_ini_21730's sets
  cndp_decoupled_groups.csv    scheme, group, source
      the decoupled complementary national payments' premium groups (psdpay_to_psgroup of CAP_2013_2020_CNDP.gms):
      their rate per unit is the scheme's ceiling over the member state's levels of the group's activities, at run time
  premium_group_edits.csv      group, from_group, domain, source
      the premium groups CAPRI's chain redefines at run time (pol_input/mtr_until2013.gms, included by
      CAP_2014_2020.gms: PSG_TO_A("PGFRM", MCACT) = PSG_TO_A("PGARAB", MCACT) + PSG_TO_A("PGGRAS", MCACT)): the group's
      crops become those of the groups on the right (sim_ini's PSG_TO_A is policy_sets.gms's, before the edit)
  cap14_entitlement_levels.csv region, activity, trd_kha
      DATA(ru, mpact, "LEVL", "TRD") of sim_ini_21730 for CAPRI's regional units (RU) and production activities
      (MPACT; 1000 ha or heads): the crops' (MCACT) sum is each region's entitlement limit (def_endCut.gms,
      p_entlLimit "Limit"), all the levels scale the rural development rates (rd_logic.gms, DATA "Y" at the chain's
      call)

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
#: the coupled-support files of CAP_2014_2020.gms: each wrapper includes its data file and divides its ceilings
#: (VCS and cotton from EUR, the complementary national payments from thousand EUR, to million EUR)
COUPLED = (Path("scen") / "Premiums" / "Coupling" / "CAP_2013_2020_vcs.gms",
           Path("scen") / "Premiums" / "Coupling" / "CAP_2013_2020_cscs.gms",
           Path("scen") / "Premiums" / "Coupling" / "CAP_2013_2020_CNDP.gms")
POLICY_SETS = Path("policy") / "policy_sets.gms"
MTR_UNTIL2013 = Path("pol_input") / "mtr_until2013.gms"
#: the share tables of CAP_2014_2020.gms and the payment each one takes out of the national ceiling
SHARE_TABLES = {"p_BPSYF": "DPYOUNG", "p_BPSRED": "DPFIRHA", "p_BPSNATCO": "DPNATCO"}


def gams_table(text: str, name: str, eps=0.0) -> dict:
    """{(row, column): value} of the GAMS table `name` in text: each cell is assigned to the column header it
    overlaps, or, written just beside one (CAP_2014_2020.gms's left-aligned zeros), to the header whose start or end
    is nearest; two cells of a row under one column stop the build. A line starting with "+" opens a block with its
    own headers; a row label written in parts ("DPGRCU     .2006") is joined. EPS is kept as the value eps (0.0 by
    default: a present cell; GAMS stores no cell written 0, so a caller that needs the difference passes a marker),
    comment lines skipped."""
    m = re.search(rf"^\s*table\s+{name}\s*\([^)]*\)[^\n]*\n(.*?)^\s*;", text, re.S | re.I | re.M)
    if m is None:
        raise SystemExit(f"table {name} not found")
    lines = [l.expandtabs(8) for l in m.group(1).splitlines() if l.strip() and not l.lstrip().startswith("*")]
    head = [(t.start(), t.end(), t.group()) for t in re.finditer(r"\S+", lines[0])]
    out = {}
    for l in lines[1:]:
        if l.lstrip().startswith("+"):
            # a continuation block: its own column headers (the "+" itself is not one)
            head = [(t.start(), t.end(), t.group()) for t in re.finditer(r"\S+", l) if t.group() != "+"]
            continue
        toks = list(re.finditer(r"\S+", l))
        # a row label written in parts ("DPGRCU     .2006"): the parts starting with "." left of the first header
        first = min(s_ for s_, _, _ in head)
        n_lab = 1
        while n_lab < len(toks) and toks[n_lab].group().startswith(".") and toks[n_lab].start() < first:
            n_lab += 1
        row = "".join(t.group() for t in toks[:n_lab])
        taken = set()
        for t in toks[n_lab:]:
            cols = [c for s, e, c in head if t.start() < e and s < t.end()]
            if not cols:
                gap = min(min(abs(t.start() - s), abs(t.end() - e)) for s, e, _ in head)
                cols = [c for s, e, c in head if min(abs(t.start() - s), abs(t.end() - e)) == gap]
            if len(cols) != 1 or cols[0] in taken:
                raise SystemExit(f"table {name} row {row}: cell {t.group()!r} at {t.start()} under {cols} columns")
            taken.add(cols[0])
            v = t.group()
            out[(row, cols[0])] = eps if v.lower() == "eps" else float(v)
    return out


def scalar_assignment(text: str, name: str) -> float:
    """The value of a one-line assignment name(MS) = value; in text (the only one)."""
    hits = re.findall(rf"^\s*{name}\s*\(\s*MS\s*\)\s*=\s*([-\d.Ee+]+)\s*;", text, re.M | re.I)
    if len(hits) != 1:
        raise SystemExit(f"{name}: {len(hits)} assignments of the form {name}(MS) = value")
    return float(hits[0])


def _case_path(root: Path, rel: Path) -> Path:
    """rel under root, each part matched without case (CAPRI's include paths are written for Windows)."""
    p = root
    for part in rel.parts:
        hit = [c for c in p.iterdir() if c.name.lower() == part.lower()] if p.is_dir() else []
        if not hit:
            raise SystemExit(f"{root / rel}: not found")
        p = hit[0]
    return p


def coupled_wrapper(gams: Path, wrapper: Path) -> tuple:
    """A coupled-support wrapper's data file (its $include) and the number it divides the ceilings by (its
    p_premDataE(..., "ceilval") = p_premDataE(..., "ceilval") / N lines, one N)."""
    text = (gams / wrapper).read_text(errors="ignore")
    inc = re.findall(r"^\s*\$include\s+'([^']+)'", text, re.I | re.M)
    div = {float(v) for v in re.findall(r'"ceilval"\)\s*=\s*p_premDataE\([^)]*"ceilval"\)\s*/\s*([\d.Ee+]+)\s*;',
                                         text, re.I)}
    if len(inc) != 1 or len(div) != 1:
        raise SystemExit(f"{wrapper}: includes {inc}, ceiling divisors {div}: one of each expected")
    return Path(*inc[0].replace("\\", "/").split("/")), div.pop(), text


def coupled_items(text: str, divisor: float) -> tuple:
    """The lines p_premDataE("R","Y","scheme","item")=value; of a coupled-support file: (ceilings (region, year,
    scheme, million EUR: the file's value / divisor), rates (region, year, scheme, premium group, EUR per unit)). A
    scheme's label as GAMS reads it, trailing blanks dropped ("vcs-203-Italy-Protein crops " is CAPRI's
    vcs-203-Italy-Protein crops). An item the file assigns twice keeps the later value."""
    rx = re.compile(r'^\s*p_premDataE\("(\w+)","(\d{4})","([^"]+)","(\w+)"\)\s*=\s*([-\d.Ee+]+)\s*;', re.I | re.M)
    ceil, rates = {}, {}
    for r, y, s, item, v in rx.findall(text):
        # an item assigned twice keeps the later value, as GAMS executes the file (24 in CNDP_2015_2020.gms)
        if item.lower() == "ceilval":
            ceil[(r, int(y), s.rstrip())] = float(v) / divisor
        else:
            rates[(r, int(y), s.rstrip(), item.upper())] = float(v)
    return [(*k, v) for k, v in ceil.items()], [(*k, v) for k, v in rates.items()]


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

    cp, cr, dgroups = [], [], []
    for w in COUPLED:
        f, div, wtext = coupled_wrapper(a.gams, w)
        c_, r_ = coupled_items(_case_path(a.gams, f).read_text(errors="ignore"), div)
        cp += c_
        cr += r_
        # the decoupled complementary payments' groups (their rate the ceiling over the member state's levels)
        dgroups += [(sch, g.upper(), f"star 3.0 {w.as_posix()}")
                    for sch, g in re.findall(r'psdpay_to_psgroup\("(\w+)","(\w+)"\)\s*=\s*yes\s*;', wtext, re.I)]
    coupled = pd.DataFrame(cp, columns=["region", "year", "scheme", "ceiling_meur"])
    rates = pd.DataFrame(cr, columns=["region", "year", "scheme", "group", "rate"])
    if rates.duplicated(["region", "year", "scheme", "group"]).any():
        raise SystemExit("a coupled-support rate assigned twice")
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
    # the area schemes' rate per premium group (CAP_2014_2020.gms l. 309-357: PGSAPS = 1000, EUR per ha, cut down to
    # the ceiling by prmcut.gms; set where the scheme has a ceiling, with its application type)
    rx = re.compile(r'^\s*p_premDataE\(MS,BPSYEARS,"(\w+)","(PG\w+)"\)[^=\n]*=\s*([-\d.Ee+]+)\s*;', re.I | re.M)
    # a GAMS label keeps the case of its first declaration: the schemes as sim_ini's PSDPAY writes them (the
    # gms file writes dpbps_SAPS, the set and the results DPBPS_SAPS)
    label = {str(s).lower(): str(s) for s in read_csv(a.sets / "PSDPAY.csv", keep_default_na=False).d0}
    area = [(f"area_rate_{g.upper()}", label.get(sch.lower(), sch), float(v), src_cap) for sch, g, v in rx.findall(cap)]
    if not area:
        raise SystemExit("CAP_2014_2020.gms: no area scheme rates found")
    if any(sch.lower() not in label for sch, _, _ in rx.findall(cap)):
        raise SystemExit("CAP_2014_2020.gms: an area scheme not in PSDPAY")
    settings += area
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
    mpact = set(read_csv(a.sets / "MPACT.csv", keep_default_na=False).d0)
    D = read_csv(a.simini / "DATA.csv.gz", keep_default_na=False, usecols=["d0", "d1", "d2", "d3", "value"])
    D = D[(D.d2 == "LEVL") & (D.d3 == "TRD") & D.d0.isin(ru) & D.d1.isin(mpact)]
    levels = (D.rename(columns={"d0": "region", "d1": "activity", "value": "trd_kha"})
              [["region", "activity", "trd_kha"]].sort_values(["region", "activity"]))

    mtr = (a.gams / MTR_UNTIL2013).read_text(errors="ignore")
    edits = []
    for g, rhs in re.findall(r'^\s*PSG_TO_A\("(\w+)",\s*MCACT\)\s*=\s*([^;]+);', mtr, re.I | re.M):
        parts = re.findall(r'PSG_TO_A\("(\w+)",\s*MCACT\)', rhs, re.I)
        if not parts or re.sub(r'PSG_TO_A\("\w+",\s*MCACT\)|[+\s]', "", rhs, flags=re.I):
            raise SystemExit(f"mtr_until2013.gms: PSG_TO_A({g}) = {rhs}: only a union of groups is read")
        edits += [(g.upper(), f.upper(), "MCACT", f"star 3.0 {MTR_UNTIL2013.as_posix()}") for f in parts]
    if not edits:
        raise SystemExit("mtr_until2013.gms: no redefinition of a premium group found")
    edits = pd.DataFrame(edits, columns=["group", "from_group", "domain", "source"])

    OUT.mkdir(parents=True, exist_ok=True)
    for frame, name, keys in ((nat, "cap14_national_ceilings.csv", ["ms", "year"]),
                              (shares, "cap14_ceiling_shares.csv", ["ms", "year", "scheme"]),
                              (transfers, "cap14_pillar_transfers.csv", ["ms", "year"]),
                              (coupled, "cap14_coupled_ceilings.csv", ["region", "year", "scheme"]),
                              (rates, "cap14_coupled_rates.csv", ["region", "year", "scheme", "group"]),
                              (settings, "cap14_settings.csv", ["item", "key"]),
                              (levels, "cap14_entitlement_levels.csv", ["region", "activity"]),
                              (edits, "premium_group_edits.csv", ["group", "from_group"]),
                              (pd.DataFrame(dgroups, columns=["scheme", "group", "source"]),
                               "cndp_decoupled_groups.csv", ["scheme", "group"])):
        to_csv(frame.sort_values(keys).reset_index(drop=True), OUT / name, index=False)
    print(f"cap14: {nat.ms.nunique()} national ceilings, {len(shares)} share cells, {len(transfers)} transfer cells, "
          f"{coupled.scheme.nunique()} coupled schemes, {levels.region.nunique()} regions' trend levels")


if __name__ == "__main__":
    main()
