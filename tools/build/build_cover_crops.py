"""CAPRI's winter cover (catch) crops, CATC, per model region: 2030 level, cost, N fixation, winter cover shares.

CAPRI (envind/cover_crops.gms, supply/supply_model.gms, pol_input/greendeal/*_io.gms):
  * CATC is an activity on top of the arable land: a catch crop sown after the main crop. Its level is
    limited by the land not already under winter cover, UAAR - sum_c crop_c x p_winterCoverShare(c)
    (+ fallow floor), and costs its input row (TOIN) per ha.
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

Sources: capri_data/validation/greendeal_2030/capri_marginal_terms_ini_2030.csv.xz (CATC LEVL and TOIN, UAAR
LEVL, crop LEVL; CAPRI's 2030 reference with technologies), capri_data/sources/capri_gams/
wintercovershare.gms (dat/policy), the GAMS source reports/def_cbalance.gms (p_cInput).

Written (capri_data/2017/supply/):
  cover_crops.csv          region, capri_region, catc_share_2030 (CATC / UAAR), catc_cost_eur_ha (TOIN),
                           biofix_t_n_ha
  winter_cover_share.csv   region, crop, share (filled), share0 (as given; 0 where not given)

Model crops that sum several CAPRI activities take their shares weighted by CAPRI's 2030 levels in the
region (OFOD: OFAR, ROOF; SETA: SETA, FALL; GRAS: GRAE, GRAI; olives OLIV and table olives TABO separate).

    python tools/build/build_cover_crops.py [--gams-dir /home/claude/work/allgms/gams]
"""
from __future__ import annotations
import argparse, importlib.util, json, re
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
_sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from _model_regions import CTRY as MS_CODE  # noqa: E402  CAPRI member-state codes (capri_member_state_codes.csv)
CTRY_CAPRI = MS_CODE


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def read_wcs(path: Path) -> dict:
    """{(capri_region, capri_act): share} from wintercovershare.gms (eps -> 0)."""
    out = {}
    pat = re.compile(r"^\s+([A-Z]{2}[0-9A-Z]{6})\.([A-Za-z0-9]+)\s+(eps|-?\d[\d.]*)\s*$")
    for line in open(path, errors="ignore"):
        if line.strip().startswith("p_wintercovershare(rall"):
            break
        m = pat.match(line)
        if m:
            out[(m.group(1), m.group(2).upper())] = 0.0 if m.group(3) == "eps" else float(m.group(3))
    return out


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gams-dir", type=Path, default=Path("/home/claude/work/allgms/gams"))
    a = ap.parse_args()
    terms = _read_csv(ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_marginal_terms_ini_2030.csv.xz",
                        header=None, names=["region", "act", "item", "value"], dtype=str)
    terms["value"] = pd.to_numeric(terms["value"], errors="coerce")
    lev = terms[terms["item"] == "LEVL"].pivot_table(index="region", columns="act", values="value")
    toin = terms[(terms["act"] == "CATC") & (terms["item"] == "TOIN")].set_index("region")["value"]
    wcs0 = read_wcs(ROOT / "capri_data" / "sources" / "capri_gams" / "wintercovershare.gms")
    cin = read_cinput(a.gams_dir / "reports" / "def_cbalance.gms")

    mr = _load(ROOT / "tools" / "lib" / "_model_regions.py")
    base = _load(ROOT / "tools" / "build" / "build_capri_base.py")
    crop_map = dict(base.CROP_MAP)
    crop_map["GRAS"] = ("GRAE", "GRAI")
    corr = json.loads((ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]
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
        src = c8 if (c8 in lev.index and pd.notna(lev.at[c8, "CATC"]) if "CATC" in lev.columns else False) else ms
        if src not in lev.index or "UAAR" not in lev.columns or not (lev.at[src, "UAAR"] > 0):
            continue
        catc = float(lev.at[src, "CATC"]) if pd.notna(lev.at[src, "CATC"]) else 0.0
        bf = cin.get(c8 or "", cin.get(ms))
        rows.append({"region": reg, "capri_region": src, "catc_share_2030": catc / float(lev.at[src, "UAAR"]),
                     "catc_cost_eur_ha": float(toin.get(src, float("nan"))),
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
