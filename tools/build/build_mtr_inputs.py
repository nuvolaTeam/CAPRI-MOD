"""The inputs of CAPRI's 2004-2013 premium regime as its CAP 2014-2020 chain evaluates it for the BPS's historical key
(scen/base_scenarios/CAP_2014_2020.gms l. 44-77: pol_input/mtr_RD.gms -> pol_input/mtr_until2013.gms, then
policy/calc_mtr_top.gms with policy/calc_mtr.gms; the premium module, P2c, port A).

sim_ini_21730 is written at the simulation start: it holds the premium declarations of the time series (Agenda 2000,
1993-2003, and the other files' edits) but not mtr_until2013.gms's, which the 2030 run executes on top of them (its
tables merge into the data, $ONMULTI in util/global_settings.gms; its assignments then run in order). So:

  capri_data/<base year>/policy/mtr_declarations.csv   line, region, year, scheme, item, value, special
        line 0: sim_ini_21730's p_premDataE of the schemes the key needs (PSDPAY_MTR_EL with mtr_until2013.gms's
        additions, DPMTR, DPSAPS); line n: mtr_until2013.gms's assignment of one value at line n (p_premDataE("R",
        "Y","S","I") = number, EPS or an application type). special: EPS, NA (sim_ini's NA, policy.gms's "missing")
        or the application type's name in value. The file's other assignments (sets, conditions, loops) are
        capri_mod/policy/mtr.py's rules, each at its line; this builder stops when mtr_until2013.gms has one more
  capri_data/<base year>/policy/mtr_ceiling_tables.csv table, region, year, value
        P_1782_2003_ANNEX_VIII, P_1782_2003_ANNEX_VIIIa, p_73_2009_ANNEX_IV (million EUR) and P_SAPS_AREAS (1000 ha,
        year 0) of mtr_until2013.gms
  capri_data/<base year>/policy/mtr_coupling.csv       scheme, year, ms, pct, eps    TABLE p_couplPercent_E
  capri_data/<base year>/policy/mtr_dd_targets.csv     region, year, scheme, target, pct, eps    TABLE p_premToDDTarget_E
  capri_data/<base year>/policy/mtr_dd_target_rules.csv line, region, scheme, target, pct, from_year
        the assignments after the table (l. 1566-1581), in their order; scheme or target ALL: all of PSDPAY_MTR_EL or
        DDTarget
  capri_data/<base year>/policy/mtr_dd_nuts.csv        line, region, level
        p_premToDDTargetNuts: the parameter's data (line of the declaration) and the assignments of one region
  capri_data/<base year>/policy/mtr_modulation.csv     group, class, region, pct     TABLE p_percAffByModulation
  capri_data/<base year>/policy/mtr_modulation_classes.csv class, share    Prem_Mod (the modulation of each class)
  capri_data/<base year>/policy/mtr_sets.csv           set, member, source
        PSDPAY_MTR_EL (sim_ini's with mtr_until2013.gms's additions), DPAgEu10 (calc_mtr_top.gms), PSGG_TO_P
        (group|scheme), TRDWHE_REG, PSDPAY_MTR (the key's schemes), PSGROUP (the premium groups), DDTarget
  capri_data/<base year>/policy/mtr_base_data.csv      region, activity, item, column, value
        DATA of sim_ini_21730 for the units and member states: LEVL at BAS and TRD, UAAR at BAS, the main outputs'
        yields (PACT_TO_Y, item YILD summed) and the young animals' inputs (PACT_TO_I, item SLGT summed) at BAS, HSTY
        (the activities' and CERE's) and the milk quota (QUTS COMI) in every column
  capri_data/<base year>/policy/mtr_rules.csv          line, rule, labels, rhs, numbers, statement
        each rule line of mtr_until2013.gms with the rule of mtr.py that executes it and the statement's quoted
        labels (| separated), right-hand side and unquoted numbers
  capri_data/<base year>/policy/mtr_settings.csv       item, value, source
        CAPRI's year set (SIMYY), %endofMTR% (CAP_2014_2020.gms), the coupling's and targets' first years
        (mtr_until2013.gms), the years EU025000's and EU027000's declarations reach the member states (calc_mtr_top)
  capri_data/<base year>/policy/mtr_lu_units.csv       activity, value    p_LUUnits of sim_ini_21730 (per livestock unit)
  capri_data/<base year>/policy/mtr_modif.csv          region, activity, scheme, value
        p_premModifFact of the simulation year (2030) above EPS (policy.gms l. 27): the Agenda 2000 premiums' shares

    python tools/build/build_mtr_inputs.py [--gams DIR] [--sets DIR] [--simini DIR]
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

MTR = Path("pol_input") / "mtr_until2013.gms"
TOP = Path("policy") / "calc_mtr_top.gms"
CAP = Path("scen") / "base_scenarios" / "CAP_2014_2020.gms"
#: a GDX stores a value written as an acronym as its number x 1e301 (sim_ini's _acronyms.csv)
ACRONYM_BASE = 1e301
#: the lines of mtr_until2013.gms whose p_premDataE assignment is not of one literal value, and the rule of
#: capri_mod/policy/mtr.py that executes each (the DPCN, DPENERCRP, DPADDSHGM, DPIRSCOW and DPNONCAP ones touch no
#: scheme of the key and are not ported); mtr_rules.csv gives each its labels, right-hand side and numbers
RULES = {214: "ceiling_from_viii_eu_west", 215: "ceiling_from_viii", 216: "ceiling_from_viiia",
         217: "ceiling_from_viiia", 222: "net_ceiling", 237: "saps_ceiling", 238: "saps_net_ceiling",
         264: "fill_ceiling", 267: "fill_ceiling", 275: "saps_level", 277: "saps_level_from_uaar", 279: "saps_rate",
         282: "saps_type", 309: "set_where_ceiling", 310: "set_where_ceiling", 325: "set_where_ceiling",
         326: "set_where_ceiling", 544: "eps_where_no_level", 589: "eps_in_year", 590: "eps_in_year",
         594: "delete_year", 599: "set_in_regions", 601: "set_in_regions", 635: "eps_in_year", 636: "eps_in_year",
         677: "eps_in_year", 678: "eps_in_year", 697: "set_from_year", 700: "set_from_year",
         704: "dcow_ceiling", 705: "dcow_ceiling", 710: "scale_year", 711: "scale_year", 712: "scale_year",
         717: "add_to_item", 718: "item_from_other", 721: "eps_where_saps", 722: "eps_where_saps", 741: "rdel"}
RULE_LINES = set(RULES)
#: the application types' names (policy_sets.gms) as GAMS identifiers: case-insensitive
APPTYPES = {"perlevl", "perslgthd", "peryield", "perhisty", "perlivestockunit"}


def statements(text: str):
    """(first line, statement) of a GAMS file: comment lines and $ontext blocks dropped, statements ending with ";"."""
    out, cur, start, skip = [], [], None, False
    for i, line in enumerate(text.splitlines(), 1):
        if re.match(r"^\$ontext", line, re.I):
            skip = True
        if re.match(r"^\$offtext", line, re.I):
            skip = False
            continue
        if skip or line.startswith("*"):
            continue
        if start is None and line.strip():
            start = i
        cur.append(line.strip())
        if ";" in line:
            out.append((start, " ".join(x for x in cur if x)))
            cur, start = [], None
    return out


def literal(expr: str):
    """(value, special) of a literal right-hand side: a number or arithmetic of numbers, EPS, an application type."""
    e = expr.strip()
    if e.lower() == "eps":
        return 0.0, "EPS"
    if e.lower() in APPTYPES:
        return e, "APPTYPE"
    if re.fullmatch(r"[\d.eE+\-*/() ]+", e):
        return float(eval(e, {"__builtins__": {}})), ""     # numbers and + - * / only (checked above)
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gams", type=Path, default=SOURCES / "gams")
    ap.add_argument("--sets", type=Path, default=REFERENCE / "sets" / "simini_21730")
    ap.add_argument("--simini", type=Path, default=REFERENCE / "simini" / "simini_21730")
    ap.add_argument("--base-year", default="2017")
    a = ap.parse_args()
    out = ROOT / "capri_data" / a.base_year / "policy"
    text = (a.gams / MTR).read_text(encoding="latin-1")

    def labels(name):
        return [str(x) for x in read_csv(a.sets / f"{name}.csv", keep_default_na=False).d0]

    def pairs(name):
        t = read_csv(a.sets / f"{name}.csv", keep_default_na=False)
        return list(zip(t.d0.astype(str), t.d1.astype(str)))

    canon_s = {s.lower(): s for s in labels("PSDPAY_T")}
    canon_i = {s.lower(): s for s in labels("PSPOS_GRP")}
    acr = {int(n): str(m) for n, m in zip(*(lambda t: (t.number, t.name))(
        read_csv(a.simini / "_acronyms.csv", keep_default_na=False)))}

    def scheme(s):
        if s.lower() not in canon_s:
            raise SystemExit(f"{MTR}: scheme {s} not in PSDPAY_T")
        return canon_s[s.lower()]

    def label(s):
        """a label of a table over * (the coupling table also lists schemes of no set): the set's case if a scheme"""
        return canon_s.get(s.lower(), s)

    def item(i):
        if i.lower() not in canon_i:
            raise SystemExit(f"{MTR}: item {i} not in PSPOS_GRP")
        return canon_i[i.lower()]

    st = statements(text)

    # the sets: PSDPAY_MTR_EL with the file's additions (l. 1010-1018), DPAgEu10 of calc_mtr_top.gms
    added = [scheme(s) for _, s in ((ln, m.group(1)) for ln, t in st for m in [re.match(
        r'^PSDPAY_MTR_EL\("(\w+)"\)\s*=\s*YES\s*;$', t, re.I)] if m)]
    mtr_el = list(dict.fromkeys(labels("PSDPAY_MTR_EL") + added))
    m = re.search(r"SET\s+DPAgEu10\(PSDPAY\)[^/]*/(.*?)/", (a.gams / TOP).read_text(encoding="latin-1"), re.I | re.S)
    if m is None:
        raise SystemExit(f"{TOP}: DPAgEu10 not found")
    ageu10 = [scheme(s.strip()) for s in m.group(1).split(",") if s.strip()]
    keyset = set(mtr_el) | {scheme("DPMTR"), scheme("DPSAPS")}
    sets = ([("PSDPAY_MTR_EL", s, "sim_ini" if s not in added else f"star 3.0 {MTR.as_posix()}") for s in mtr_el]
            + [("DPAgEu10", s, f"star 3.0 {TOP.as_posix()}") for s in ageu10]
            + [("PSGG_TO_P", f"{g}|{p}", "sim_ini") for g, p in pairs("PSGG_TO_P")]
            + [("TRDWHE_REG", r, "sim_ini") for r in labels("TRDWHE_REG")]
            + [("PSDPAY_MTR", s, "sim_ini") for s in labels("PSDPAY_MTR")]
            + [("PSGROUP", g, "sim_ini") for g in labels("PSGROUP")]
            + [("DDTarget", g, "sim_ini") for g in labels("DDTarget")])
    if not set(ageu10) <= set(mtr_el):
        raise SystemExit("DPAgEu10 has schemes outside PSDPAY_MTR_EL")

    # sim_ini's declarations of the key's schemes
    d = read_csv(a.simini / "p_premDataE.csv.gz", keep_default_na=False)
    d = d[d.d2.str.lower().isin({s.lower() for s in keyset})]
    rows = []
    for r, y, s, i, v, e in zip(d.d0, d.d1, d.d2, d.d3, d.value, d.eps):
        s, i = scheme(s), item(i)
        if i == "APPTYPE" and int(e) == 0 and v not in ("nan", "0.0"):
            n = int(round(float(v) / ACRONYM_BASE))
            if n not in acr:
                raise SystemExit(f"p_premDataE: application type {v} of {r} {y} {s} not an acronym of the file")
            rows.append((0, r, int(y), s, i, acr[n], "APPTYPE"))
        elif v == "nan":
            rows.append((0, r, int(y), s, i, "", "NA"))
        else:
            rows.append((0, r, int(y), s, i, repr(float(v)), "EPS" if int(e) else ""))

    # mtr_until2013.gms's assignments: literals as data, the others must be ported rules (mtr.py)
    low_key = {s.lower() for s in keyset}
    spans_all = {"psdpay", "psdpay_t", "psdpay_mtr_el", "dpageu10"}      # set indices covering the key's schemes
    unported = []
    for ln, t in st:
        if not re.match(r"^p_premDataE\(", t, re.I):
            continue
        mm = re.match(r'^p_premDataE\("(\w+)","(\d{4})","(\w+)","(\w+)"\)\s*=\s*(.*);$', t, re.I)
        lit = literal(mm.group(5)) if mm else None
        if mm and lit is not None:
            if mm.group(3).lower() in low_key:
                v, sp = lit
                rows.append((ln, mm.group(1), int(mm.group(2)), scheme(mm.group(3)), item(mm.group(4)),
                             v if sp == "APPTYPE" else repr(v), sp))
            continue
        args = re.match(r"^p_premDataE\(([^,]+),([^,]+),([^,]+),", t, re.I)
        sch = args.group(3).strip().strip('"').lower() if args else ""
        if (sch in low_key or sch in spans_all) and ln not in RULE_LINES:
            unported.append((ln, t[:120]))
    decl = pd.DataFrame(rows, columns=["line", "region", "year", "scheme", "item", "value", "special"])

    # the rules' parameters: the statement's quoted labels, right-hand side and unquoted numbers, in their order
    by_line = dict(st)
    rl = []
    for ln, name in sorted(RULES.items()):
        if ln not in by_line:
            raise SystemExit(f"mtr_until2013.gms: no statement starts at l. {ln} (the file changed: check mtr.py)")
        s = by_line[ln]
        s = s[s.lower().index("p_premdatae("):] if "p_premdatae(" in s.lower() else s   # l. 264: after the LOOP's head
        lhs, rhs = s.split("=", 1) if "=" in s else (s, "")
        labs = [canon_s.get(x.lower(), canon_i.get(x.lower(), x)) for x in re.findall(r'"([^"]*)"', s)]
        nums = re.findall(r"(?<![\w.\"])(\d+\.?\d*)(?![\w\"])", re.sub(r'"[^"]*"', '""', rhs))
        rl.append((ln, name, "|".join(labs), rhs.strip().rstrip(";").strip(), " ".join(nums), s[:150]))
    rules_t = pd.DataFrame(rl, columns=["line", "rule", "labels", "rhs", "numbers", "statement"])

    # the settings the port needs, read from the statements that set them
    top = (a.gams / TOP).read_text(encoding="latin-1")
    cap = (a.gams / CAP).read_text(encoding="latin-1")

    def find(pattern, txt, what):
        m = re.search(pattern, txt, re.I | re.S)
        if m is None:
            raise SystemExit(f"{what} not found")
        return float(m.group(1))

    simyy = [int(y) for y in labels("SIMYY")]
    settings = pd.DataFrame([
        ("first_year", min(simyy), "sim_ini SIMYY"), ("last_year", max(simyy), "sim_ini SIMYY"),
        ("end_of_mtr", find(r"\$setglobal\s+endofMTR\s+(\d{4})", cap, "endofMTR"), f"star 3.0 {CAP.as_posix()}"),
        ("coupled_until", find(r'p_couplPercent\(PSDPAY,SIMY,MSALL\)\s*\$\s*\(CALYEA\(SIMY\)\s*LE\s*CALYEA\("(\d{4})"\)\)',
                               text, "the coupling's last full year"), f"star 3.0 {MTR.as_posix()}"),
        ("coupling_from", find(r'p_couplPercent\(PSDPAY,"(\d{4})",MSALL\)', text, "the coupling table's year"),
         f"star 3.0 {MTR.as_posix()}"),
        ("targets_from", find(r'LOOP\(\s*SIMYY\s*\$\s*\(\(CALYEA\(SIMYY\)\s*GE\s*CALYEA\("(\d{4})"\)\)\s*\$\s*\(CALYEA\(SIMYY\)\s*'
                              r'LE\s*max\{', text, "the decoupling targets' loop"), f"star 3.0 {MTR.as_posix()}"),
        ("eu25_from", find(r'CALYEA\("(\d{4})"\)\)\s*and\s*MAP_RR\("EU025000",MS\)', top, "EU025000's year"),
         f"star 3.0 {TOP.as_posix()}"),
        ("eu27_from", find(r'CALYEA\("(\d{4})"\)\)\s*and\s*MAP_RR\("EU027000",MS\)', top, "EU027000's year"),
         f"star 3.0 {TOP.as_posix()}")], columns=["item", "value", "source"])

    # the tables
    tab = []
    for (r, y), v in gams_table(text, "P_1782_2003_ANNEX_VIII").items():
        tab.append(("ANNEX_VIII", r, int(y), v))
    for (y, r), v in gams_table(text, "P_1782_2003_ANNEX_VIIIa").items():
        if v:
            tab.append(("ANNEX_VIIIa", r, int(y), v))
    for (r, y), v in gams_table(text, "p_73_2009_ANNEX_IV").items():
        tab.append(("ANNEX_IV", r, int(y), v))
    m = re.search(r"PARAMETER\s+P_SAPS_AREAS\(RALL\)[^/]*/(.*?)/\s*;", text, re.I | re.S)
    if m is None:
        raise SystemExit(f"{MTR}: P_SAPS_AREAS not found")
    body = "\n".join(x for x in m.group(1).splitlines() if not x.lstrip().startswith("*"))
    tab += [("SAPS_AREAS", r, 0, float(v)) for r, v in re.findall(r"(\w+)\s+([-\d.]+)", body)]
    tables = pd.DataFrame(tab, columns=["table", "region", "year", "value"])
    tables = tables[tables.value != 0]

    EPSM = -1e300
    cp = []
    for (row, ms), v in gams_table(text, "p_couplPercent_E", eps=EPSM).items():
        s, y = row.split(".")
        cp.append((label(s), int(y), ms, 0.0 if v == EPSM else v, int(v == EPSM)))
    coupling = pd.DataFrame(cp, columns=["scheme", "year", "ms", "pct", "eps"])
    coupling = coupling[(coupling.pct != 0) | (coupling.eps == 1)]

    tg = []
    for (row, target), v in gams_table(text, "p_premToDDTarget_E", eps=EPSM).items():
        r, y, s = row.split(".")
        tg.append((r, int(y), label(s), target, 0.0 if v == EPSM else v, int(v == EPSM)))
    targets = pd.DataFrame(tg, columns=["region", "year", "scheme", "target", "pct", "eps"])
    targets = targets[(targets.pct != 0) | (targets.eps == 1)]

    rx = re.compile(r'^p_premToDDTarget\("(\w+)",SIMY,("?\w+"?),("?\w+"?)\)\s*\$\s*\(CALYEA\(SIMY\)\s*GE\s*'
                    r'CALYEA\("(\d{4})"\)\)\s*=\s*([-\d.]+)\s*;$', re.I)
    rules = []
    for ln, t in st:
        g = rx.match(t)
        if g:
            r, s, tgt, y, v = g.groups()
            rules.append((ln, r, scheme(s.strip('"')) if s.startswith('"') else "ALL",
                          tgt.strip('"') if tgt.startswith('"') else "ALL", float(v), int(y)))
        elif re.match(r'^p_premToDDTarget\("', t, re.I):
            raise SystemExit(f"mtr_until2013.gms l. {ln}: a decoupling target rule not of the expected form: {t}")
    rules = pd.DataFrame(rules, columns=["line", "region", "scheme", "target", "pct", "from_year"])

    nuts = []
    for ln, t in st:
        g = re.match(r"^Parameter\s+p_premToDDTargetNuts\(\*\)\s*/(.*)/\s*;$", t, re.I)
        if g:
            nuts += [(ln, r, float(v)) for r, v in re.findall(r"(\w+)\s+([-\d.]+)", g.group(1))]
        g = re.match(r'^p_premToDDTargetNuts\("(\w+)"\)\s*=\s*([-\d.]+)\s*;$', t, re.I)
        if g:
            nuts.append((ln, g.group(1), float(g.group(2))))
    if not nuts:
        raise SystemExit(f"{MTR}: p_premToDDTargetNuts not found")
    nuts = pd.DataFrame(nuts, columns=["line", "region", "level"])

    mod = []
    for (row, r), v in gams_table(text, "p_percAffByModulation").items():
        g, c = row.split(".")
        if v:
            mod.append((g, c.lower(), r, v))
    modulation = pd.DataFrame(mod, columns=["group", "class", "region", "pct"])
    pm = [(c.lower(), float(v)) for ln, t in st
          for c, v in re.findall(r'^Prem_Mod\("(\w+)"\)\s*=\s*([-\d.]+)\s*;$', t, re.I)]
    if not pm:
        raise SystemExit(f"{MTR}: Prem_Mod not found")
    classes = pd.DataFrame(pm, columns=["class", "share"])

    # the base year's data
    ru, ms = set(labels("RU")), set(labels("MS"))
    regions = ru | ms
    mpact = set(labels("MPACT"))
    p2y = pd.DataFrame(pairs("PACT_TO_Y"), columns=["a", "o"])
    p2i = pd.DataFrame(pairs("PACT_TO_I"), columns=["a", "i"])
    iyani = set(labels("IYANI"))
    p2i = p2i[p2i.i.isin(iyani)]
    D = read_csv(a.simini / "DATA.csv.gz", keep_default_na=False, usecols=["d0", "d1", "d2", "d3", "value"])
    D = D[D.d0.isin(regions)]
    D["value"] = D.value.astype(float)
    parts = []
    lv = D[D.d1.isin(mpact) & (D.d2 == "LEVL") & D.d3.isin(["BAS", "TRD"])]
    parts.append(pd.DataFrame({"region": lv.d0, "activity": lv.d1, "item": "LEVL", "column": lv.d3,
                               "value": lv.value}))
    ua = D[(D.d1 == "UAAR") & (D.d2 == "LEVL") & (D.d3 == "BAS")]
    parts.append(pd.DataFrame({"region": ua.d0, "activity": "UAAR", "item": "LEVL", "column": "BAS",
                               "value": ua.value}))
    for pp, name, col in ((p2y.rename(columns={"o": "x"}), "YILD", "BAS"), (p2i.rename(columns={"i": "x"}), "SLGT",
                                                                            "BAS")):
        x = D[D.d3 == col].merge(pp, left_on=["d1", "d2"], right_on=["a", "x"])
        x = x.groupby(["d0", "d1"], as_index=False).value.sum()
        parts.append(pd.DataFrame({"region": x.d0, "activity": x.d1, "item": name, "column": col, "value": x.value}))
    hs = D[D.d2 == "HSTY"]
    parts.append(pd.DataFrame({"region": hs.d0, "activity": hs.d1, "item": "HSTY", "column": hs.d3, "value": hs.value}))
    qu = D[(D.d1 == "QUTS") & (D.d2 == "COMI")]
    parts.append(pd.DataFrame({"region": qu.d0, "activity": "QUTS", "item": "COMI", "column": qu.d3,
                               "value": qu.value}))
    base = pd.concat(parts, ignore_index=True)
    base = base[base.value != 0]

    lu = read_csv(a.simini / "p_LUUnits.csv.gz", keep_default_na=False)
    lu = pd.DataFrame({"activity": lu.d0, "value": lu.value.astype(float)})

    mf = read_csv(a.simini / "p_premModifFact.csv.gz", keep_default_na=False)
    mf = mf[(mf.d1.astype(str) == "2030") & (mf.eps.astype(int) == 0) & (mf.value.astype(float) > 0)]
    modif = pd.DataFrame({"region": mf.d0, "activity": mf.d2, "scheme": [scheme(s) for s in mf.d3],
                          "value": mf.value.astype(float)})
    modif = modif[modif.scheme.isin(keyset)]

    for frame, name, keys in (
            (decl, "mtr_declarations.csv", None),
            (tables, "mtr_ceiling_tables.csv", ["table", "region", "year"]),
            (coupling, "mtr_coupling.csv", ["scheme", "year", "ms"]),
            (targets, "mtr_dd_targets.csv", ["region", "year", "scheme", "target"]),
            (rules, "mtr_dd_target_rules.csv", ["line"]),
            (nuts, "mtr_dd_nuts.csv", ["line", "region"]),
            (modulation, "mtr_modulation.csv", ["group", "class", "region"]),
            (classes, "mtr_modulation_classes.csv", ["class"]),
            (pd.DataFrame(sets, columns=["set", "member", "source"]), "mtr_sets.csv", ["set", "member"]),
            (base, "mtr_base_data.csv", ["region", "activity", "item", "column"]),
            (modif, "mtr_modif.csv", ["region", "activity", "scheme"]),
            (rules_t, "mtr_rules.csv", ["line"]),
            (settings, "mtr_settings.csv", ["item"]),
            (lu, "mtr_lu_units.csv", ["activity"])):
        if keys and frame.duplicated(keys).any():
            raise SystemExit(f"{name}: a key written twice")
        frame = frame.reset_index(drop=True) if keys is None else frame.sort_values(keys).reset_index(drop=True)
        to_csv(frame, out / name, index=False)
    print(f"mtr inputs: {len(decl)} declarations ({int((decl.line == 0).sum())} sim_ini, "
          f"{int((decl.line > 0).sum())} mtr_until2013.gms literals), {len(tables)} ceiling cells, {len(coupling)} "
          f"coupling cells, {len(targets)} targets, {len(rules)} target rules, {len(nuts)} NUTS levels, "
          f"{len(modulation)} modulation cells, {len(base)} base data, {len(modif)} modification factors; "
          f"PSDPAY_MTR_EL {len(mtr_el)} ({', '.join(added)} added)")


if __name__ == "__main__":
    main()
