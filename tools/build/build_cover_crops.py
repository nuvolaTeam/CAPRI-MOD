"""CAPRI's winter cover (catch) crops, CATC, per model region: 2030 level, cost, N fixation, winter cover shares.

CAPRI (envind/cover_crops.gms, supply/supply_model.gms, pol_input/greendeal/*_io.gms):
  * CATC is an activity on top of the arable land: a catch crop sown after the main crop. Its level is
    limited by the land not already under winter cover, UAAR - sum_c crop_c x p_winterCoverShare(c)
    (+ fallow floor), and costs its inputs per ha (capmod/define_objc.gms p_linObjeCont, the cost of the
    winter-cover option in envind/cover_crops.gms l. 410).
  * Its inputs (policy/define_greening_limits.gms l. 70-84): CAPRI has no CATC data; for each of its inputs
    (PACT_TO_I: SEED, REPM, REPB, EFUL, ELUB, IRRO, INPO) the coefficient is 25% (SEED: 50%) of the average of the
    cheapest cereal's (the lowest non-zero coefficient over CERE: SWHE, DWHE, RYEM, BARL, OATS, MAIZ, OCER) and OFAR's
    base-year coefficient, projected to 2030 as a crop without yield growth (capmod/define_inputs.gms: x TF_I, the
    input-saving progress 1 - 0.005 x (2030 - 2017)), valued at the member state's 2030 unit value (UVAG = UVAP,
    define_objc.gms). The rule reproduces CAPRI's 2030 CATC coefficients exactly in the 90 regions whose catch crops
    CAPRI reports (17 November 2026) and its TOIN (DE000000: 172.78 EUR per ha either way).
  * Its N: biological fixation and residues p_ghgMiti(CATC, WinterCov, othImpact, BioFix)
    = p_cInput(winterCov) / 24 x 0.75 x 0.5 (t N per ha; reports/calc_cbalance.gms l. 672, carbon input
    from the Century table p_cInput in reports/def_cbalance.gms). It is N supplied to the crops
    (nutrient need, l. 1076), an input of the gross balance (e_BIOFIX) and a source of crop-residue N2O.
  * Farm-to-Fork: a minimum catch-crop area (e_minCoverCrops) from the organic and pesticide targets:
      organic_io.gms      coverCrop = 50 (%), x organic area target
      conventional_io.gms coverCrop = pesticide cut / 2 = 25 (%), x (1 - organic) x remaining / cut
    each times (UAAR - sum_c crop_c x p_winterCoverShare0(c)), plus the baseline catch-crop area.
    The requirement uses p_winterCoverShare0, the shares as given in wintercovershare.gms (NUTS2 entries
    for Austria and a few German regions only); the potential-area row uses p_winterCoverShare, filled
    NUTS2 <- member state <- EU (policy/define_greening_limits.gms). Both are written.

Sources: capri_data/validation/greendeal_2030/capri_marginal_terms_ref_2030.csv (CATC LEVL, UAAR LEVL, crop LEVL;
CAPRI's 2030 Green Deal baseline, the model's 2030 base), CAPRI's 2017 results res_17<MS>.txt (the cereals' and OFAR's
input coefficients; capri_sources/capreg), capri_data/validation/greendeal_2030/capri_unit_values_ref_2030.csv (the
member states' 2030 unit values of the inputs), capri_data/sources/raw/capri/dat/policy/
wintercovershare_p_winterCoverShare0.parquet (dat/policy/wintercovershare.gms, converted to CSV by
tools/build/convert_sources.py), the GAMS source reports/def_cbalance.gms (p_cInput).

Written (capri_data/2017/supply/):
  cover_crops.csv          region, capri_region, catc_share_2030 (CATC / UAAR), catc_cost_eur_ha (CAPRI's rule above,
                           over CAPRI's inflation to 2030: the model's 2017 money, K108), cost_source ("rule": CAPRI's
                           rule for every region since 17 November 2026, K130; until then its reported TOIN, from its
                           calibration run where its baseline had no catch crop), biofix_t_n_ha
  winter_cover_share.csv   region, crop, share (filled), share0 (as given; 0 where not given)

Model crops that sum several CAPRI activities take their shares weighted by CAPRI's 2030 levels in the
region (GRAS: GRAE, GRAI; olives OLIV and table olives TABO separate).

    python tools/build/build_cover_crops.py [--gams-dir capri_sources/gams]
"""
from __future__ import annotations
import argparse, csv, importlib.util, json, re
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
import sys  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from paths import SOURCES  # noqa: E402  (CAPRI's material outside the repository)
from _sources_io import read_source, source_records, write_source  # noqa: E402  (capri_data/sources: Parquet)
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
_sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from _model_regions import CTRY as MS_CODE  # noqa: E402  CAPRI member-state codes (capri_member_state_codes.csv)
CTRY_CAPRI = MS_CODE
#: CAPRI's p_winterCoverShare0 (dat/policy/wintercovershare.gms as CSV)
WCS = ROOT / "capri_data" / "sources" / "raw" / "capri" / "dat" / "policy" / "wintercovershare_p_winterCoverShare0.parquet"


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def read_wcs(path: Path = WCS) -> dict:
    """{(capri_region, capri_act): share} from p_winterCoverShare0 of wintercovershare.gms, converted to CSV by
    tools/build/convert_sources.py (eps -> 0)."""
    return {(r["region"], r["act"].upper()): 0.0 if r["value"].lower() == "eps" else float(r["value"])
            for r in source_records(path)}


def read_cinput(path: Path) -> dict:
    """{capri_region: winterCov carbon input, t C per ha} from the p_cInput table."""
    txt = open(path, errors="ignore").read()
    i = txt.index("table p_cInput(")
    out = {}
    for line in txt[i:].splitlines()[2:]:
        if line.strip().startswith(";"):
            break
        if line.startswith("*") or not line.strip():
            continue
        p = line.split()
        if len(p) >= 2 and re.match(r"^[A-Z]{2}[0-9A-Z]{6}$", p[0]):
            out[p[0]] = float(p[1])
    return out


#: policy/define_greening_limits.gms l. 77-84: CATC's inputs (PACT_TO_I) and the shares of the cheapest cereal's and
#: OFAR's average base coefficient they take
CATC_INPUTS = {"SEED": 0.50, "REPM": 0.25, "REPB": 0.25, "EFUL": 0.25, "ELUB": 0.25, "IRRO": 0.25, "INPO": 0.25}
#: global/fromimpact/sets.gms CERE
CERE = ("SWHE", "DWHE", "RYEM", "BARL", "OATS", "MAIZ", "OCER")
#: capmod/define_inputs.gms l. 66: TF_I = 1 - 0.005 x (simulation year - base year), 2030 from 2017
TF_I_2030 = 1.0 - 0.005 * (2030 - 2017)
ROW17 = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Z0-9]+)'\.'([A-Z0-9]+)'\.'Y'\s+([-\d.Ee+]+)")


def catc_coefficients(dump_dir: Path) -> dict:
    """{capri region: {input: CAPRI's 2030 CATC coefficient}} by CAPRI's rule (define_greening_limits.gms l. 77-84,
    define_inputs.gms): share x (the lowest non-zero cereal coefficient + OFAR's) / 2 x TF_I, from the 2017 results."""
    import glob
    v = defaultdict(dict)
    for f in glob.glob(str(dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = ROW17.match(line)
            if m and m.group(3) in CATC_INPUTS and (m.group(2) in CERE or m.group(2) == "OFAR"):
                v[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    if not v:
        raise SystemExit(f"no CAPRI 2017 results under {dump_dir}")
    out = {}
    for r, d in v.items():
        co = {}
        for i, f_ in CATC_INPUTS.items():
            cer = [d[(c, i)] for c in CERE if d.get((c, i))]
            co[i] = f_ * ((min(cer) if cer else 0.0) + d.get(("OFAR", i), 0.0)) / 2.0 * TF_I_2030
        out[r] = co
    return out


def catc_costs(dump_dir: Path, deflator: float) -> dict:
    """{capri region: CATC's input cost per ha in the model's 2017 money}: CAPRI's coefficients (catc_coefficients)
    x the member state's 2030 unit values / 1000 (define_objc.gms), over CAPRI's inflation to 2030 (K108)."""
    uv = _read_csv(ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_unit_values_ref_2030.csv")
    uv = {(r, p): float(x) for r, p, x in zip(uv.region, uv["product"], uv.uvag)}
    out = {}
    for r, co in catc_coefficients(dump_dir).items():
        # the member state's row in CAPRI's results (Turkey's regions TR..., its row TUR)
        ms = "TUR" if r[:2] == "TR" else CTRY_CAPRI.get(r[:2], r[:2]) + "000000"
        miss = [i for i, x in co.items() if x and (ms, i) not in uv]
        # None where a unit value is missing (CAPRI's units outside the model: Turkey's regions); an error where the
        # model needs the region (main)
        out[r] = None if miss else sum(x * uv[(ms, i)] for i, x in co.items() if x) / 1000.0 / deflator
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gams-dir", type=Path, default=SOURCES / "gams")
    ap.add_argument("--dump-dir", type=Path, default=SOURCES / "capreg")
    a = ap.parse_args()
    terms = _read_csv(ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_marginal_terms_ref_2030.csv",
                        header=None, names=["region", "act", "item", "value"], dtype=str)
    terms["value"] = pd.to_numeric(terms["value"], errors="coerce")
    lev = terms[terms["item"] == "LEVL"].pivot_table(index="region", columns="act", values="value")
    # CATC's input cost in the model's 2017 money: CAPRI's 2030 TOIN over its inflation to 2030 (tools/lib/_money;
    # KNOWN_ISSUES K108, 31 October 2026: before, CAPRI's 2030 money); the winter-cover option's cost curve
    # (build_winter_cover_option.py) scales with it
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "tools" / "lib"))
    import _money
    cost_rule = catc_costs(a.dump_dir, _money.deflator(2030))
    wcs0 = read_wcs(WCS)
    cin = read_cinput(a.gams_dir / "reports" / "def_cbalance.gms")

    mr = _load(ROOT / "tools" / "lib" / "_model_regions.py")
    base = _load(ROOT / "tools" / "build" / "build_capri_base.py")
    crop_map = dict(base.CROP_MAP)
    crop_map["GRAS"] = ("GRAE", "GRAI")
    import importlib.util as _ilu_
    _sp_ = _ilu_.spec_from_file_location("_mr_", ROOT / "tools" / "lib" / "_model_regions.py")
    _mr_ = _ilu_.module_from_spec(_sp_); _sp_.loader.exec_module(_mr_)
    to_c8 = _mr_.region_to_capri()          # correspondence + NUTS splits and merges (tools/lib/_model_regions.py)

    def share(c8, act, filled):
        """CAPRI's p_winterCoverShare (filled NUTS2 <- MS <- EU) or p_winterCoverShare0 (as given)."""
        if (c8, act) in wcs0:
            return wcs0[(c8, act)]
        if not filled:
            return 0.0
        ms = CTRY_CAPRI.get(c8[:2], c8[:2]) + "000000"
        return wcs0.get((ms, act), wcs0.get(("EU027000", act), 0.0))

    rows, srows = [], []
    for reg in mr.model_regions():
        c8 = to_c8.get(reg)
        ms = mr.national_code(reg)
        # the region's own entry where CAPRI reports the region (its UAAR): a CATC level it does not list is 0 (GAMS
        # stores no zero; until 9 November 2026 the member state's share was taken there); else the member state's
        reported = c8 in lev.index and "UAAR" in lev.columns and lev.at[c8, "UAAR"] > 0
        src = c8 if reported else ms
        if src not in lev.index or "UAAR" not in lev.columns or not (lev.at[src, "UAAR"] > 0):
            continue
        catc = float(lev.at[src, "CATC"]) if "CATC" in lev.columns and pd.notna(lev.at[src, "CATC"]) else 0.0
        # the cost per ha: CAPRI's rule for the region (the CAPRI region the model region maps to, else the member
        # state), as CAPRI computes it for every unit
        rsrc = c8 if c8 in cost_rule else ms
        if cost_rule.get(rsrc) is None:
            raise SystemExit(f"{reg}: no CAPRI 2017 coefficients or 2030 unit values for the catch crops' cost "
                             f"({c8}, {ms})")
        cost, csrc = cost_rule[rsrc], "rule"
        bf = cin.get(c8 or "", cin.get(ms))
        rows.append({"region": reg, "capri_region": src, "catc_share_2030": catc / float(lev.at[src, "UAAR"]),
                     "catc_cost_eur_ha": cost, "cost_source": csrc,
                     "biofix_t_n_ha": (bf / 24.0 * 0.75 * 0.5) if bf is not None else float("nan")})
        wr = c8 if c8 in lev.index else ms
        for crop, acts in crop_map.items():
            lv = [(x, float(lev.at[wr, x]) if x in lev.columns and pd.notna(lev.at[wr, x]) else 0.0) for x in acts]
            tot = sum(v for _, v in lv)
            w = [(x, v / tot) for x, v in lv] if tot > 0 else [(x, 1.0 / len(acts)) for x, _ in lv]
            srows.append({"region": reg, "crop": crop,
                          "share": sum(f * share(c8 or ms, x, True) for x, f in w),
                          "share0": sum(f * share(c8 or ms, x, False) for x, f in w)})
    out = pd.DataFrame(rows)
    dest = ROOT / "capri_data" / "2017" / "supply"
    out.to_csv(dest / "cover_crops.csv", index=False)
    s = pd.DataFrame(srows)
    s[(s["share"] > 0) | (s["share0"] > 0)].to_csv(dest / "winter_cover_share.csv", index=False)
    print(f"cover_crops.csv: {len(out)} regions, CATC share median {out.catc_share_2030.median():.3f}, "
          f"cost median {out.catc_cost_eur_ha.median():.0f} EUR/ha, biofix median {1000 * out.biofix_t_n_ha.median():.0f} kg N/ha "
          f"({int(out.biofix_t_n_ha.isna().sum())} without); winter_cover_share.csv: {len(s)} region-crop rows, "
          f"{int((s.share0 > 0).sum())} with a share as given")


if __name__ == "__main__":
    main()
