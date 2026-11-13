"""CAPRI's rural development (pillar 2) inputs of the 2030 premium chain (the premium module, P2c: policy/
extend_rd_baseline.gms and policy/rd_logic.gms, called from scen/Premiums/rd/define_second_pillar_baseline.gms):

  capri_data/<base year>/policy/rd_budget.csv          region, year, measure, plan_spend, meur, eps
        p_rdBudget of results/policy/rd_budget.gdx, the total public money (rdSpendPublic, million EUR) planned or
        spent per region, year and RDP measure, for the measures CAPRI's RD payments are made of and the measures
        sharing their policy shock (the weights of extend_rd_baseline.gms rule 3); eps = 1 where the file writes EPS
        (a spend recorded as nothing: it keeps a region out of the weights' fallbacks and its plan out of the
        ceiling)
  capri_data/<base year>/policy/rd_programme_years.csv rdp, year (rdp_simyy of rd_budget.gdx)
  capri_data/<base year>/policy/rd_scheme_measures.csv scheme, rdp, measure (psDpay_RDP_rdMeasure,
        define_second_pillar_baseline.gms)
  capri_data/<base year>/policy/rd_shock_measures.csv  shock, rdp, measure (rdShocks_RDP_rdMeasure,
        load_rdp_spend_and_budget.gms), the shocks of the measures above
  capri_data/<base year>/policy/rd_new_measure_keys.csv region, shock, share (p_rdNewMeasuresRegDist of
        dat/policy/rdNewMeasuresRegDist.gdx, rule 4), those shocks
  capri_data/<base year>/policy/rd_land_partition.csv  region, land_cover, area_type, kha (p_clueLandPart of
        dat/baseline/clueLandPartition.gdx: the agricultural land covers' areas, total and in LFA, Natura 2000, HNV,
        NVZ)
  capri_data/<base year>/policy/rd_fadn_ae.csv          ms, farm_type, lfa, ae, unit, value (p_fes of
        dat/baseline/ae_lfa_fes.gdx: FADN 2005 hectares and agri-environment euros by farm type, in or out of LFA)
  capri_data/<base year>/policy/rd_sweden_expert.csv    region, year, scheme, ceiling_meur (p_seLbuData of
        dat/policy/rd_spend_2007_2013_se.gdx, rd_logic.gms's Swedish expert data)
  capri_data/<base year>/policy/rd_sets.csv             set, a, b (rd_static.gms: psgroup_tf8, dpae_tf8, tf8_lc)
  capri_data/<base year>/policy/rd_settings.csv         item, key, value, source (p_rdMax of
        define_second_pillar_baseline.gms)

    python tools/build/build_rd_inputs.py [--gams DIR] [--dat DIR] [--budget FILE]
"""
from __future__ import annotations

import argparse
import itertools
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT))
from paths import SOURCES  # noqa: E402
from capri_mod.csvio import to_csv  # noqa: E402

RD_STATIC = Path("policy") / "rd_static.gms"
LOAD_RDP = Path("policy") / "load_rdp_spend_and_budget.gms"
SECOND_PILLAR = Path("scen") / "Premiums" / "rd" / "define_second_pillar_baseline.gms"


def read_gdx(path: Path, symbol: str, eps=0.0) -> list:
    """The records of a GDX symbol (tools/lib/_gdx.py), EPS as eps."""
    from _gdx import read_symbol
    return read_symbol(path, symbol, eps=eps)


def _text(p: Path) -> str:
    return p.read_text(encoding="latin-1")


def _tokens(part: str) -> list:
    """The elements of one position of a GAMS set literal: a label, a quoted label or a parenthesised list."""
    part = part.strip()
    if part.startswith("("):
        inner = part[1:-1]
        return [t.strip().strip('"').strip("'") for t in re.findall(r'"[^"]*"|\'[^\']*\'|[^,\s]+', inner)]
    return [part.strip('"').strip("'")]


def set_literal(text: str, name: str) -> list:
    """The tuples of a multi-dimensional GAMS set given as a literal ("SET name(...) "..." / a.b.(c,d) ... /"),
    comment lines (*) skipped; each line one product of its positions."""
    m = re.search(r"SET\s+" + re.escape(name) + r"\b[^/]*/(.*?)/\s*;", text, re.I | re.S)
    if m is None:
        raise SystemExit(f"set {name} not found")
    out = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        parts = re.findall(r'\([^)]*\)|"[^"]*"|[^.\s"()]+', line)
        out += [tuple(p) for p in itertools.product(*(_tokens(p) for p in parts))]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gams", type=Path, default=SOURCES / "gams")
    ap.add_argument("--dat", type=Path, default=SOURCES / "course_capri_git" / "dat")
    ap.add_argument("--budget", type=Path, default=SOURCES / "results" / "policy" / "rd_budget.gdx")
    ap.add_argument("--base-year", default="2017")
    a = ap.parse_args()
    out = ROOT / "capri_data" / a.base_year / "policy"
    out.mkdir(parents=True, exist_ok=True)

    scheme_measures = set_literal(_text(a.gams / SECOND_PILLAR), "psDpay_RDP_rdMeasure")
    shock_measures = set_literal(_text(a.gams / LOAD_RDP), "rdShocks_RDP_rdMeasure")
    measures = {m for _, _, m in scheme_measures}
    shocks = {s for s, _, m in shock_measures if m in measures and s.lower() != "none"}
    shock_rows = [(s, r, m) for s, r, m in shock_measures if s in shocks]
    keep = measures | {m for _, _, m in shock_rows}

    budget = [(r, int(y), str(m), ps, 0.0 if v == "EPS" else v, int(v == "EPS"))
              for r, y, m, sp, ps, v in read_gdx(a.budget, "p_rdBudget", eps="EPS")
              if sp == "rdSpendPublic" and str(m) in keep]
    budget = pd.DataFrame(budget, columns=["region", "year", "measure", "plan_spend", "meur", "eps"])
    years = pd.DataFrame([(row[0], int(row[1])) for row in read_gdx(a.budget, "rdp_simyy")], columns=["rdp", "year"])

    keys = pd.DataFrame([(r, s, v) for r, s, v in read_gdx(a.dat / "policy" / "rdNewMeasuresRegDist.gdx",
                                                          "p_rdNewMeasuresRegDist") if s in shocks],
                        columns=["region", "shock", "share"])
    land = pd.DataFrame(read_gdx(a.dat / "baseline" / "clueLandPartition.gdx", "p_clueLandPart"),
                        columns=["region", "land_cover", "area_type", "kha"])
    fadn = pd.DataFrame(read_gdx(a.dat / "baseline" / "ae_lfa_fes.gdx", "p_fes"),
                        columns=["ms", "farm_type", "lfa", "ae", "unit", "value"])
    se = pd.DataFrame([(r, int(y), s, v) for r, y, s, i, v in read_gdx(a.dat / "policy" / "rd_spend_2007_2013_se.gdx",
                                                                      "p_seLbuData") if i.lower() == "ceilval"],
                      columns=["region", "year", "scheme", "ceiling_meur"])

    static = _text(a.gams / RD_STATIC)
    sets = [(n, x, y) for n in ("psgroup_tf8", "dpae_tf8", "tf8_lc") for x, y in set_literal(static, n)]
    sets = [(n, x.upper() if n != "tf8_lc" else x, y.upper() if n == "tf8_lc" else y) for n, x, y in sets]
    second = _text(a.gams / SECOND_PILLAR)
    rdmax = re.findall(r'p_rdMax\("(\w+)"\)\s*=\s*([-\d.Ee+]+)\s*;', second)
    if len(rdmax) != 2:
        raise SystemExit(f"p_rdMax: {rdmax}, two amounts expected (LFA, N2K)")
    src = f"star 3.0 {SECOND_PILLAR.as_posix()}"
    settings = pd.DataFrame([("rd_max", k, float(v), src) for k, v in rdmax], columns=["item", "key", "value", "source"])

    for frame, name, keys_ in (
            (budget, "rd_budget.csv", ["region", "year", "measure", "plan_spend"]),
            (years, "rd_programme_years.csv", ["rdp", "year"]),
            (pd.DataFrame(scheme_measures, columns=["scheme", "rdp", "measure"]), "rd_scheme_measures.csv",
             ["scheme", "rdp", "measure"]),
            (pd.DataFrame(shock_rows, columns=["shock", "rdp", "measure"]), "rd_shock_measures.csv",
             ["shock", "rdp", "measure"]),
            (keys, "rd_new_measure_keys.csv", ["region", "shock"]),
            (land, "rd_land_partition.csv", ["region", "land_cover", "area_type"]),
            (fadn, "rd_fadn_ae.csv", ["ms", "farm_type", "lfa", "ae", "unit"]),
            (se, "rd_sweden_expert.csv", ["region", "year", "scheme"]),
            (pd.DataFrame(sets, columns=["set", "a", "b"]), "rd_sets.csv", ["set", "a", "b"]),
            (settings, "rd_settings.csv", ["item", "key"])):
        if frame.duplicated(keys_).any():
            raise SystemExit(f"{name}: a key written twice")
        to_csv(frame.sort_values(keys_).reset_index(drop=True), out / name, index=False)
    print(f"rd inputs: {len(budget)} budget cells ({budget.measure.nunique()} measures), {len(scheme_measures)} scheme "
          f"measures, shocks {sorted(shocks)}, {len(land)} land partition cells, {len(fadn)} FADN cells, {len(se)} "
          f"Swedish cells, p_rdMax {dict(rdmax)}")


if __name__ == "__main__":
    main()
