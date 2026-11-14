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
and 2030 calibration points, capri_data/sources/raw/capri/capri_baseline/capri_market_prices_1730.parquet.
The reference run's 2030 output prices equal CAPRI's own calibrated 2030 baseline (p_uvagStore,
results/baseline/data_uvag1730defaulta; capri_uvag_store_1730.parquet): ratio 1.000 for every traded product.

P2 step 2 (13 November 2026): the 2030 PRME of the regions the premium ports cover (capri_mod/policy/premiums.py,
the EU's units and member states at CAPRI's trend levels; norway.py) replace the reference's rows; an activity the
ports give no premium has none (CAPRI's reference has none either: Greece's dairy cows, LEVL > 0 and no PRME). The
data base activities DCOW, BULF and HEIF take their members' total premium on CAPREG's 2017 level (T30 H17 /
(H30 L17), _ported_premiums_2030). The reference's rows remain for the regions the ports do not cover. The ports'
open points against the reference: docs/KNOWN_ISSUES.md K140, K142.

Sources: capri_data/validation/greendeal_2030/capri_unit_values_ref_2030.csv and
capri_marginal_terms_ref_2030.csv (tools/build/extract_capri_marginal_terms.py); CAPRI 2017 results
res_17<MS>.txt (national UVAG, regional PRME and LEVL).

Written (capri_data/baselines/capri_greendeal_ref/1730/trajectories/):
  capri_price_ratios_2030.csv          ms, product, uvag_2017, uvag_2030, deflator, real_ratio
  capri_cap_premium_2030.csv           model region x CAPRI activity: PRME 2030 in 2017 money (per unit)
  capri_livestock_premium_ratio_2030.csv  model region x model animal: 2030/2017 premium ratio (real,
                                       2017 CAPRI activity levels as weights)

    python tools/build/build_price_trajectory_2030.py [--dump-dir capri_sources/capreg]
"""
from __future__ import annotations
import argparse, glob, importlib.util, json, re, statistics
from collections import defaultdict
from pathlib import Path

import pandas as pd

import functools as _ft
import sys  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from paths import SOURCES  # noqa: E402  (CAPRI's material outside the repository)
from _sources_io import read_source, source_records, write_source  # noqa: E402  (capri_data/sources: Parquet)
import sys as _sys_nc  # noqa: E402
_sys_nc.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "tools" / "lib"))
from _model_regions import national_code as _national_code  # noqa: E402  (TUR for Turkey's units, 4 November 2026)
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
CAKES = ("SOYC", "RAPC", "SUNC")
INPUTS = ("EFUL", "ELEC", "EGAS", "ELUB", "NITF", "PHOF", "POTF", "SEED", "PLAP", "REPM", "REPB", "INPO", "IPHA")
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6}|TUR)'\.'([A-Za-z0-9_]+)'\.'([A-Za-z0-9_]+)'\.'Y'\s+(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def _ported_premiums_2030(p30: pd.DataFrame):
    """CAPRI's 2030 premiums per activity unit from the ported premium module (capri_mod/policy/premiums.py at CAPRI's
    trend levels: the EU's units and member states, level-weighted as aggreg_ppepay.gms; norway.py: Norway's units),
    in place of the reference's rows for the regions they cover; and, for the data base activities (DCOW, BULF, HEIF,
    codes/capri/DACT_TO_PACT.csv) of those regions, (T30, H30, H17): the members' total premium at the trend levels,
    their herd at the trend levels and at the base (LEVL x DAYS / 365, sim_ini_21730's DATA "TRD"/"Y" and "BAS")."""
    import csv as _csv
    import gzip as _gz
    sys.path.insert(0, str(ROOT))
    from capri_mod.external_paths import REFERENCE
    from capri_mod.policy import norway as _nw
    from capri_mod.policy import premiums as _pm
    trend = _pm.trend_levels()
    prme = _pm.prme_table(2030, 2017)
    for (u, a, _s), v in _nw.norway_premiums(2030).items():
        prme[(u, a)] = prme.get((u, a), 0.0) + v
    ported = sorted({r for r, _ in prme} & set(p30.index))
    mpact = set(_read_csv(ROOT / "capri_data" / "codes" / "capri" / "MPACT.csv").code)
    out = p30.copy()
    for r in ported:
        for a in out.columns:
            if a in mpact:
                v = prme.get((r, a))
                out.at[r, a] = float(v) if v else float("nan")
    # the data base activities' members and their days
    d2p = _read_csv(ROOT / "capri_data" / "codes" / "capri" / "DACT_TO_PACT.csv")
    members = defaultdict(list)
    for a, m in zip(d2p.dact, d2p.pact):
        members[str(a)].append(str(m))
    aggs = [a for a in ("DCOW", "BULF", "HEIF") if a in members]
    want = {m for a in aggs for m in members[a]}
    units = {u for u, _ in trend}
    D = {}
    with _gz.open(REFERENCE / "simini" / "simini_21730" / "DATA.csv.gz", "rt") as f:
        for r in _csv.DictReader(f):
            if r["d0"] in units and r["d1"] in want and r["d2"] in ("LEVL", "DAYS", "PRME") and r["d3"] in ("BAS", "Y"):
                D[(r["d0"], r["d1"], r["d2"], r["d3"])] = float(r["value"])
    from capri_mod.data.definitions import capri_ms
    herd = {}
    for a in aggs:
        acc = defaultdict(lambda: [0.0, 0.0, 0.0])
        for u in sorted(units):
            t30 = h30 = h17 = 0.0
            for m in members[a]:
                L30 = trend.get((u, m), 0.0)
                t30 += float(prme.get((u, m), 0.0) or 0.0) * L30
                h30 += L30 * D.get((u, m, "DAYS", "Y"), 0.0) / 365.0
                h17 += D.get((u, m, "LEVL", "BAS"), 0.0) * D.get((u, m, "DAYS", "BAS"), 0.0) / 365.0
            if h30 or h17:
                for k in {u, capri_ms(u)}:              # a member state of one unit counted once
                    x = acc[k]
                    x[0] += t30; x[1] += h30; x[2] += h17
        for k, (t30, h30, h17) in acc.items():
            if k in ported:
                herd[(k, a)] = (t30, h30, h17)
    return out, herd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=SOURCES / "capreg")
    args = ap.parse_args()
    val = ROOT / "capri_data" / "validation" / "greendeal_2030"
    out = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "trajectories"
    uv30 = _read_csv(val / "capri_unit_values_ref_2030.csv")
    terms = _read_csv(val / "capri_marginal_terms_ref_2030.csv")
    products = set(uv30["product"])

    # --- CAPRI 2017: national UVAG, regional PRME and LEVL
    uv17, prme17, levl17 = {}, defaultdict(dict), defaultdict(dict)
    for f in glob.glob(str(args.dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = ROW.match(line)
            if not m:
                continue
            reg, a, it, v = m.group(1), m.group(2), m.group(3), float(m.group(4))
            if a == "UVAG" and (reg.endswith("000000") or reg == "TUR") and it in products:   # TUR: Turkey's row
                uv17[(reg, it)] = v
            elif it == "PRME":
                prme17[reg][a] = v
            elif it == "LEVL":
                levl17[reg][a] = v

    # --- price ratios per member state
    rows, defl = [], {}
    # the national rows: '<MS>000000' and Turkey's 'TUR' (left out until 4 November 2026); keyed by the two letters (TU)
    nat = uv30[uv30["region"].str.endswith("000000") | (uv30["region"] == "TUR")]
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
    mk = read_source(ROOT / "capri_data" / "sources" / "raw" / "capri" / "capri_baseline" / "capri_market_prices_1730.parquet")
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
    # P2 step 2: the EU's and Norway's from the ported premium module at CAPRI's trend levels; the regions the ports
    # do not cover (the UK, the Western Balkans, Turkey) keep CAPRI's reference
    p30, herd = _ported_premiums_2030(p30)
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
    # cap_premium columns that use the model's code: CAPRI's code from codes/model_activities.csv, crops mapped to one
    # CAPRI activity (CORN -> MAIZ, WINE -> TWIN; K145: until 13 November 2026 only CORN, so WINE's 2030 premium was
    # left empty and the model kept the 2017 premium)
    _ma = _read_csv(ROOT / "capri_data" / "codes" / "model_activities.csv")
    COLMAP = {str(c): str(k) for c, k, kind in zip(_ma.code, _ma.capri_codes, _ma.kind)
              if kind == "crop" and ";" not in str(k) and str(k) != str(c)}

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
        if src is None or (_national_code(src)) not in defl and mr.national_code(reg) not in defl:
            continue
        df_ = defl.get(mr.national_code(reg), defl.get(_national_code(src)))
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
            if (src, ca) in herd:
                # a data base activity of the ports' regions (DCOW, BULF, HEIF): its members' premium per head of
                # their herd, on CAPREG's 2017 level of the activity (CAPRI's level of BULF moves with the members'
                # herd, LEVL x DAYS / 365; claude/p2_integration_design.md): T30 H17 / (H30 L17)
                t30, h30, h17 = herd[(src, ca)]
                a30 = t30 * h17 / (h30 * L) if (h30 > 0 and L > 0) else None
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
