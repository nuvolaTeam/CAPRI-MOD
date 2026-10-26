"""CAPRI's input costs that the Green Deal organic and pesticide targets shock, per model region and activity (2017).

CAPRI's organic and pesticide targets (pol_input/greendeal/organic_io.gms, conventional_io.gms; applied to the input
coefficients by capmod/define_inputs.gms) change three input rows:
  PLAP  plant protection: a regional percentage change of every activity's coefficient (DATA GROF.PLAP)
  INPO  other inputs: a regional percentage change of every activity's coefficient, animals included (GROF.INPO),
        plus, per organic crop, a top-up by its EFUL coefficient x 2 x the crop's organic target (organic_io.gms)
  (fertiliser: through the fertilisation constraints, not a cost row)
The model applies these changes in EUR per ha (crops) or as a share of the cost per head (animals).

CAPRI values an input coefficient at its regional unit value: cost (EUR per ha or head) = DATA(act, I) x UVAG(I) / 1000
(checked: the inputs of BL000000 soft wheat sum to its TOIN, 1139 against 1140 EUR/ha). Columns:

  crops
  plap_eur_ha       PLAP x UVAG.PLAP / 1000
  inpo_eur_ha       INPO x UVAG.INPO / 1000 (until 24 October 2026 the bare INPO coefficient, without its unit value:
                    about 20% too low)
  fert_eur_ha       FERT (CAPRI's fertiliser cost in EUR, NITF + PHOF + POTF valued)
  eful_eur_ha       EFUL x UVAG.EFUL / 1000: the fuel cost, the basis of the organic top-up the code's comment
                    describes ("costs for EFUL+SERI would double")
  eful_inpo_eur_ha  EFUL x UVAG.INPO / 1000: the top-up as organic_io.gms codes it (the EFUL coefficient added to the
                    INPO coefficient, so valued at INPO's unit value; for the parity switch)
  yd_rest_eur_ha    the yield-dependent part of the other directly yield-dependent inputs (sets.gms IY: CAOF, SEED,
                    REPM, REPB, ELEC, EGAS, EFUL, ELUB, IRRO, SERI): sum_i f_i x cost_i x G, with f_i CAPRI's
                    p_inputDemandFactor (inputs/yieldIY.gms, vendored) and G CAPRI's yield growth 2017 -> 2030 (2030
                    reference YILD / 2017 YILD). capmod/define_inputs.gms sets a coefficient to
                    BAS x (1 - f + f x G) x TF_I, so the cost moves by yd x TF_I x (rho - 1) for a yield ratio rho
                    against the 2030 reference (supply/endog_yields.gms re-runs define_inputs after the price-driven
                    yield update; capmod/shift_yields.gms precedes it for the scenario's yield shifts)
  yd_plap_eur_ha, yd_inpo_eur_ha   the same for PLAP and INPO (their TF_I carries the Green Deal changes)
  yield_growth      G of the model crop (LEVL x YILD weighted, each activity's G within CAPRI's bounds 0.5-1.5); an
                    activity at a bound contributes nothing to the yd columns
  animals (activity = model animal; CAPRI members as in build_animal_yields.py)
  inpo_toin_share   sum LEVL x INPO x UVAG.INPO / 1000 over sum LEVL x TOIN: other inputs as a share of CAPRI's total
                    input cost per head, applied to the model's cost per head (livestock_cost_coef.csv, which is
                    CAPRI's LEVL x TOIN per model head)
SERI (services), which organic_io.gms also tops up where present, has no activity rows in CAPRI's 2017 data.

Mapping: model regions take their CAPRI region (NUTS correspondence), else the national row; model crops sum CAPRI
activities as in tools/build/build_capri_base.py (CROP_MAP), weighted by CAPRI's 2017 levels.

Source: CAPRI 2017 results res_17<MS>.txt (PLAP, INPO, FERT, EFUL, TOIN, LEVL, YILD and the IY inputs per activity;
their UVAG); CAPRI's 2030 reference yields (res_2_1730greendeal_refdefaulta, --dump-2030, extracted to
capri_data/sources/capri_res/yild_2030_ref.csv.xz).
Output: capri_data/2017/supply/plant_protection_cost.csv
    (region, activity, plap_eur_ha, inpo_eur_ha, fert_eur_ha, eful_eur_ha, eful_inpo_eur_ha, inpo_toin_share,
     capri_region)

    python tools/build/build_plant_protection_cost.py [--dump-dir /home/claude/work/capreg] [--out FILE]
"""
from __future__ import annotations
import argparse, glob, importlib.util, re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
#: CAPRI's directly yield-dependent inputs of crops present in the 2017 data (sets.gms IY = I not IS, without ICHI,
#: water and mitiI: CIREST and IGEN)
IY_CROP = ("CAOF", "SEED", "PLAP", "REPM", "REPB", "ELEC", "EGAS", "EFUL", "ELUB", "IRRO", "INPO", "SERI")
ROW = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Za-z0-9_]+)'\.'(PLAP|INPO|FERT|EFUL|TOIN|LEVL|YILD|CAOF|SEED|REPM|"
                 r"REPB|ELEC|EGAS|ELUB|IRRO|SERI)'\.'Y'\s+"
                 r"(-?\d[\d.]*(?:[Ee][+\-]?\d+)?)")
#: model animal -> CAPRI activities (as tools/build/build_animal_yields.py)
ANIMALS = {"DCOW": ("DCOL", "DCOH"), "BCOW": ("SCOW",), "BULL": ("BULL", "BULH"), "HFRS": ("HEIL", "HEIH", "HEIR"),
           "CALV": ("CAMF", "CAFF", "CAMR", "CAFR"), "PIGS": ("SOWS",), "PIGF": ("PIGF",), "LAYS": ("HENS",),
           "BROI": ("POUF",), "SHGM": ("SHGM",), "SHGF": ("SHGF",), "OANI": ("OANI",)}
COLS = ["region", "activity", "plap_eur_ha", "inpo_eur_ha", "fert_eur_ha", "eful_eur_ha", "eful_inpo_eur_ha",
        "yd_rest_eur_ha", "yd_plap_eur_ha", "yd_inpo_eur_ha", "yield_growth", "inpo_toin_share", "capri_region"]
YIELD_IY = ROOT / "capri_data" / "sources" / "capri_gams" / "inputs" / "yieldIY.gms"
YILD30 = ROOT / "capri_data" / "sources" / "capri_res" / "yild_2030_ref.csv.xz"


def yields_2030(dump: Path) -> dict:
    """CAPRI's 2030 reference yields per CAPRI region and activity (kg/ha, YILD of res_2_1730greendeal_refdefaulta),
    extracted from the dump when given, else read from the extract (capri_data/sources/capri_res/yild_2030_ref.csv.xz)."""
    if dump is not None and dump.exists():
        import subprocess
        p1 = subprocess.Popen(["unzip", "-p", str(dump)], stdout=subprocess.PIPE)
        out = subprocess.run(["grep", "-E", r"^'[A-Z0-9]{8}'\.''\.'[A-Z]+'\.'YILD'\.'2030'"], stdin=p1.stdout,
                             capture_output=True, text=True).stdout
        rx = re.compile(r"^'([A-Z0-9]{8})'\.''\.'([A-Z]+)'\.'YILD'\.'2030'\s+([-\d.Ee+]+)")
        rows = [m.groups() for m in map(rx.match, out.splitlines()) if m]
        df = pd.DataFrame(rows, columns=["capri_region", "activity", "yild_kg_ha"]).astype({"yild_kg_ha": float})
        YILD30.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(YILD30, index=False, float_format="%.10g")
        print(f"extracted {len(df)} 2030 yields -> {YILD30.relative_to(ROOT)}")
    df = pd.read_csv(YILD30)
    return {(r.capri_region, r.activity): float(r.yild_kg_ha) for r in df.itertuples(index=False)}


def input_demand_factors() -> dict:
    """CAPRI's p_inputDemandFactor(act, input), the yield-dependent part of an input coefficient
    (inputs/yieldIY.gms; vendored): the table, and 1 for a yield-dependent input the table leaves blank
    (l. 103: p_inputDemandFactor(PACT,IY) $ (NOT p_inputDemandFactor(PACT,IY)) = 1)."""
    lines = YIELD_IY.read_text(errors="replace").splitlines()
    i0 = next(i for i, l in enumerate(lines) if l.startswith("TABLE p_inputDemandFactor"))
    head, f = None, {}
    for l in lines[i0 + 1:]:
        if l.strip() == ";" or l.strip().startswith(";"):
            break
        if not l.strip() or l.lstrip().startswith("*"):
            continue
        if head is None:
            head = [(m.start(), m.group()) for m in re.finditer(r"[A-Z]+", l)]
            continue
        act = l.split()[0]
        for m in re.finditer(r"\d+\.?\d*", l[len(act):]):
            pos = m.start() + len(act)
            col = min(head, key=lambda h: abs(h[0] - pos))[1]      # the column header nearest the number
            f[(act, col)] = float(m.group())
    return f


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    ap.add_argument("--out", type=Path, default=ROOT / "capri_data" / "2017" / "supply" / "plant_protection_cost.csv")
    ap.add_argument("--dump-2030", type=Path, default=Path("/mnt/user-data/uploads/res_2_1730greendeal_refdefaulta.zip"))
    a = ap.parse_args()
    y30 = yields_2030(a.dump_2030)
    v = defaultdict(dict)            # region -> {(act, item): value}
    for f in glob.glob(str(a.dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = ROW.match(line)
            if m:
                v[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    mr = _load(ROOT / "tools" / "lib" / "_model_regions.py")
    base = _load(ROOT / "tools" / "build" / "build_capri_base.py")
    crop_map = dict(base.CROP_MAP)
    fac = input_demand_factors()
    to_c8 = mr.region_to_capri()          # correspondence + NUTS splits and merges (tools/lib/_model_regions.py)

    def crop_cost(src, acts):
        d = v.get(src, {})
        uv = {i: d.get(("UVAG", i)) for i in ("PLAP", "INPO", "EFUL")}
        if not (uv["PLAP"] and uv["INPO"]):
            return None
        uvi = {i: d.get(("UVAG", i)) or 0.0 for i in IY_CROP}
        s = defaultdict(float)
        den = 0.0
        for act in acts:
            L = d.get((act, "LEVL"), 0.0)
            if L <= 0:
                continue
            p, i = d.get((act, "PLAP")), d.get((act, "INPO"))
            if p is None and i is None:
                continue
            den += L
            e = d.get((act, "EFUL")) or 0.0
            s["plap"] += L * (p or 0.0) * uv["PLAP"] / 1000.0
            s["inpo"] += L * (i or 0.0) * uv["INPO"] / 1000.0
            s["fert"] += L * (d.get((act, "FERT")) or 0.0)
            s["eful"] += L * e * (uv["EFUL"] or 0.0) / 1000.0
            s["eful_inpo"] += L * e * uv["INPO"] / 1000.0
            # the yield-dependent parts (capmod/define_inputs.gms: coefficient = BAS x (1 - f + f x yield growth)
            # x TF_I): f x cost per ha, PLAP and INPO apart (the Green Deal changes their TF_I)
            # x yield growth G = CAPRI's 2030 reference yield / 2017 yield: the cost's derivative in the yield ratio
            # against the 2030 reference (before TF_I)
            y = d.get((act, "YILD"))
            g = y30.get((src, act), 0.0) / y if y else 0.0
            # define_inputs.gms bounds the yield growth to 0.5-1.5 (l. 101-102): an activity at a bound does not move
            # with the yield (its derivative is 0; REGISTERED: the asymmetric move off the bound is not held)
            g_in = 0.5 < g < 1.5
            for i in IY_CROP:
                q = d.get((act, i))
                if q and g_in:
                    k = "yd_plap" if i == "PLAP" else "yd_inpo" if i == "INPO" else "yd_rest"
                    s[k] += L * q * uvi[i] / 1000.0 * fac.get((act, i), 1.0) * g
            if y and g > 0:
                s["yld"] += L * y
                s["yld30"] += L * y * min(1.5, max(0.5, g))
        if den <= 0:
            return None
        yld = s["yld30"] / s["yld"] if s["yld"] > 0 else float("nan")       # G of the model crop (2030 / 2017)
        return [s[k] / den for k in ("plap", "inpo", "fert", "eful", "eful_inpo", "yd_rest", "yd_plap", "yd_inpo")] \
            + [yld, float("nan")]

    def animal_cost(src, acts):
        d = v.get(src, {})
        uv = d.get(("UVAG", "INPO"))
        if not uv:
            return None
        num = den = 0.0
        for act in acts:
            L = d.get((act, "LEVL"), 0.0)
            t = d.get((act, "TOIN"))
            if L <= 0 or not t:
                continue
            num += L * (d.get((act, "INPO")) or 0.0) * uv / 1000.0
            den += L * t
        return [float("nan")] * 9 + [num / den] if den > 0 else None

    rows, n_reg, n_nat = [], 0, 0
    for reg in mr.model_regions():
        if reg[:2] == "NO":
            continue                               # EU instrument (region_plap: EU27yr19)
        for kind_map, fn in ((crop_map, crop_cost), (ANIMALS, animal_cost)):
            for col, acts in kind_map.items():
                for src, kind in ((to_c8.get(reg), "regional"), (mr.national_code(reg), "national")):
                    if src and src in v:
                        c = fn(src, acts)
                        if c is not None:
                            rows.append([reg, col] + c + [src])
                            n_reg += kind == "regional"; n_nat += kind == "national"
                            break
    out = pd.DataFrame(rows, columns=COLS)
    out.to_csv(a.out, index=False, float_format="%.6g")
    crops = out[out.inpo_toin_share.isna()]
    med = crops.groupby("activity")[COLS[2:10]].median().round(0)
    print(f"wrote {a.out}: {len(out)} rows ({len(crops)} crop, {len(out) - len(crops)} animal), "
          f"{out.region.nunique()} regions ({n_reg} regional, {n_nat} national cells)")
    print(med.loc[[c for c in ("SWHE", "CORN", "RAPE", "SUGB", "POTA", "APPL", "WINE", "OLIV", "GRAS") if c in med.index]].to_string())
    print(out[out.inpo_toin_share.notna()].groupby("activity").inpo_toin_share.median().round(3).to_string())


if __name__ == "__main__":
    main()
