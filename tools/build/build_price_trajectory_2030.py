"""CAPRI's 2030 prices and premiums for the model's 2030 baseline, in 2017 money.

CAPRI's 2030 reference is in current prices. Every non-agricultural input (fuel, electricity,
fertilisers, seed, plant protection, repairs, services) moves by one index, the same in every
member state (2030/2017 = 1.28 in res_2_1730greendeal_refpol_endotech_all_ini); agricultural
outputs move by their own projected prices. The model works in 2017 money with 2017 input costs,
so a product's 2030 price in 2017 money is its CAPRI unit value ratio over that input index:

    real ratio(ms, product) = [UVAG 2030 / UVAG 2017](ms, product) / deflator(ms)
    deflator(ms)            = median over the inputs of UVAG 2030 / UVAG 2017

Premiums the same way: CAPRI's 2030 PRME per activity unit over the deflator (CAP payments are
nominal and fall in 2030 in CAPRI's reference: soft wheat in Brittany EUR 288 -> 226 per ha).

Oilcakes (no UVAG in CAPRI's 2017 results): producer prices PPRI at the market baseline's base (2017)
and 2030 calibration points, capri_data/sources/capri_baseline/capri_market_prices_1730.csv.
The reference run's 2030 output prices equal CAPRI's own calibrated 2030 baseline (p_uvagStore,
results/baseline/data_uvag1730defaulta; capri_uvag_store_1730.csv): ratio 1.000 for every traded product.

Sources: capri_data/validation/greendeal_2030/capri_unit_values_ini_2030.csv and
capri_marginal_terms_ini_2030.csv.xz (tools/build/extract_capri_marginal_terms.py); CAPRI 2017 results
res_17<MS>.txt (national UVAG, regional PRME and LEVL).

Written (capri_data/trajectories/):
  capri_price_ratios_2030.csv          ms, product, uvag_2017, uvag_2030, deflator, real_ratio
  capri_cap_premium_2030.csv           model region x CAPRI activity: PRME 2030 in 2017 money (per unit)
  capri_livestock_premium_ratio_2030.csv  model region x model animal: 2030/2017 premium ratio (real,
                                       2017 CAPRI activity levels as weights)

    python tools/build/build_price_trajectory_2030.py [--dump-dir /home/claude/work/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, json, re, statistics
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
CAKES = ("SOYC", "RAPC", "SUNC")
INPUTS = ("EFUL", "ELEC", "EGAS", "ELUB", "NITF", "PHOF", "POTF", "SEED", "PLAP", "REPM", "REPB", "INPO", "IPHA")
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Za-z0-9_]+)'\.'([A-Za-z0-9_]+)'\.'Y'\s+(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    args = ap.parse_args()
    val = ROOT / "capri_data" / "validation" / "greendeal_2030"
    out = ROOT / "capri_data" / "trajectories"
    uv30 = _read_csv(val / "capri_unit_values_ini_2030.csv")
    terms = _read_csv(val / "capri_marginal_terms_ini_2030.csv.xz")
    products = set(uv30["product"])

    # --- CAPRI 2017: national UVAG, regional PRME and LEVL
    uv17, prme17, levl17 = {}, defaultdict(dict), defaultdict(dict)
    for f in glob.glob(str(args.dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = ROW.match(line)
            if not m:
                continue
            reg, a, it, v = m.group(1), m.group(2), m.group(3), float(m.group(4))
            if a == "UVAG" and reg.endswith("000000") and it in products:
                uv17[(reg, it)] = v
            elif it == "PRME":
                prme17[reg][a] = v
            elif it == "LEVL":
                levl17[reg][a] = v

    # --- price ratios per member state
    rows, defl = [], {}
    nat = uv30[uv30["region"].str.endswith("000000")]
    for reg, g in nat.groupby("region"):
        r_in = [float(x.uvag) / uv17[(reg, x.product)] for x in g.itertuples()
                if x.product in INPUTS and uv17.get((reg, x.product), 0) > 0 and x.uvag > 0]
        if len(r_in) < 3:
            continue
        defl[reg] = statistics.median(r_in)
        for x in g.itertuples():
            u17 = uv17.get((reg, x.product), 0.0)
            if u17 > 0 and x.uvag > 0:
                rows.append((reg[:2], x.product, u17, float(x.uvag), defl[reg], float(x.uvag) / u17 / defl[reg]))
    # oilcakes: CAPRI's 2017 results carry no oilcake UVAG; the market baseline
    # (results/baseline/data_market_1730defaulta: PPRI at the base point BAS = 2017 and at the 2030
    # calibration point CAL) gives the same producer-price concept at both points
    mk = _read_csv(ROOT / "capri_data" / "sources" / "capri_baseline" / "capri_market_prices_1730.csv")
    mk = mk[(mk["item"] == "PPRI") & mk["product"].isin(CAKES)].pivot_table(
        index=["region", "product"], columns="point", values="value")
    for (reg, prod), v in mk.iterrows():
        if reg in defl and v.get("BAS", 0) > 0 and v.get("CAL", 0) > 0:
            rows.append((reg[:2], prod, float(v["BAS"]), float(v["CAL"]), defl[reg],
                         float(v["CAL"]) / float(v["BAS"]) / defl[reg]))
    pr = pd.DataFrame(rows, columns=["ms", "product", "uvag_2017", "uvag_2030", "deflator", "real_ratio"])
    pr.to_csv(out / "capri_price_ratios_2030.csv", index=False)

    # --- premiums: 2030 PRME per unit (CAPRI regions and national rows) in 2017 money
    p30 = terms[terms["item"] == "PRME"].pivot_table(index="region", columns="activity", values="value")
    sys_path = str(ROOT)
    import sys; sys.path.insert(0, sys_path)
    from capri_mod.data.loaders import load_cap_premium, load_regional_animal_numbers  # the tables needed (load_all_data read every model input, a dependency cycle in the data pipeline; 29 Oct 2026)
    cap = load_cap_premium(str(ROOT / "capri_data")); herds = load_regional_animal_numbers(str(ROOT / "capri_data"))
    mr = _load(ROOT / "tools" / "lib" / "_model_regions.py")
    loc = _load(ROOT / "tools" / "build" / "build_livestock_output_coef.py")
    c2m = loc.CAPRI_TO_MODEL
    import importlib.util as _ilu_
    _sp_ = _ilu_.spec_from_file_location("_mr_", ROOT / "tools" / "lib" / "_model_regions.py")
    _mr_ = _ilu_.module_from_spec(_sp_); _sp_.loader.exec_module(_mr_)
    to_c8 = _mr_.region_to_capri()          # correspondence + NUTS splits and merges (tools/lib/_model_regions.py)
    COLMAP = {"CORN": "MAIZ"}                         # cap_premium columns that use the model's code

    def source(reg):
        """CAPRI region with 2030 premiums for a model region, else its national row."""
        c8 = to_c8.get(reg)
        if c8 in p30.index:
            return c8
        n = mr.national_code(reg)
        return n if n in p30.index else None

    capn = pd.DataFrame(index=cap.index, columns=cap.columns, dtype=float)
    for reg in cap.index:
        src = source(reg)
        if src is None or (src[:2] + "000000") not in defl and mr.national_code(reg) not in defl:
            continue
        df_ = defl.get(mr.national_code(reg), defl.get(src[:2] + "000000"))
        for col in cap.columns:
            a = COLMAP.get(col, col)
            v = p30.at[src, a] if a in p30.columns else float("nan")
            if pd.notna(v):
                capn.at[reg, col] = float(v) / df_
    capn.to_csv(out / "capri_cap_premium_2030.csv")

    lsk = pd.DataFrame(index=herds.index, columns=sorted(set(c2m.values())), dtype=float)
    for reg in herds.index:
        src = source(reg)
        df_ = defl.get(mr.national_code(reg))
        if src is None or df_ is None:
            continue
        lv = levl17.get(src, {}); p7 = prme17.get(src, {})
        num, den = defaultdict(float), defaultdict(float)
        for ca, ma in c2m.items():
            L = lv.get(ca, 0.0); a17 = p7.get(ca, 0.0)
            a30 = float(p30.at[src, ca]) if ca in p30.columns and pd.notna(p30.at[src, ca]) else None
            if L > 0 and a30 is not None:
                num[ma] += L * a30 / df_; den[ma] += L * a17
        for ma in num:
            if den[ma] > 1e-9:
                lsk.at[reg, ma] = num[ma] / den[ma]
    lsk.to_csv(out / "capri_livestock_premium_ratio_2030.csv")
    print(f"price ratios: {len(pr)} rows, deflator median {statistics.median(defl.values()):.4f} "
          f"(range {min(defl.values()):.4f}-{max(defl.values()):.4f}); cap premiums {int(capn.notna().sum().sum())} cells; "
          f"livestock premium ratios {int(lsk.notna().sum().sum())} cells")


if __name__ == "__main__":
    main()
