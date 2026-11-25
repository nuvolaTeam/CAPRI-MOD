"""The animals' input costs per model head in CAPRI's objective form (register DEP-13, step 3): CAPRI's supply model
charges an animal's directly yield-dependent inputs in its objective's linear part (p_linObjeCont, capmod/
define_objc.gms l. 39-44: the inputs of IobjCont at the member state's UVAP), its feeds through the feeding block
(QUADRF_ and the bulks' market balances) and its young animals through their balances (INPANIE_, SUPBAL_); the model
charged CAPRI's total inputs TOIN (reports/calc_inc_indic.gms l. 34-37: all three), 2017's at 2030
(claude/dep13_step3_plan_2026-11-25.md).

Per model region, model animal and item, CAPRI's regional total (LEVL x the activity's value per unit, over CAPRI's
activities of the model animal) over the model's heads (tools/build/build_livestock_output_coef.per_head, the
territory groups and the member state's remainder as the other per-head coefficients):

  2017 (CAPREG's base year, res_17<MS>.txt at "Y"; CAPRI's aggregates DCOW, BULF, HEIF as the 2017 coefficients):
    each input I of IobjCont   DATA(r, act, I) x the member state's UVAP(I) / 1000 (EUR per head; -p_linObjeCont,
                               the animals' technology T has no input factors in CAPRI's data)
    YOUNG                      the young animals bought, sum over ICAM, ICAF, IHEI, ICOW, IPIG, IBUL, ILAM, ICHI of
                               DATA x the region's UVAG / 1000 (TOIN's part)
    FEED                       the feeds, sum over FEED of DATA x the region's UVAG / 1000 (TOIN's part)
  Check printed: per CAPRI row, the inputs at the region's UVAG + YOUNG + FEED against CAPREG's TOIN.

  2030 (CAPRI's simulation start, sim_ini_21730; its elementary activities DCOL, DCOH, BULL, BULH, HEIL, HEIH, HEIR ...
  as the 2030 coefficients, tools/build/build_livestock_output_2030.MAP; over the model's 2030 base heads,
  build_young_animals_2030.herds_2030):
    each input I of IobjCont   DATA(BAS) x (1 - f + f G) (capmod/define_inputs.gms l. 107-112 before TF_I, which the
                               model applies with the scenario's changes) x the member state's UVAP(I, 2030) (CAPRI's
                               2030 money: UVAP(BAS) x p_infl^(2030 - BAS); the model deflates) / 1000
  Check printed (CAPRI's results, check only): the regional units' inputs x TF_I against the reference's 2030
  coefficients (sim_ini's member-state rows are not their regions' sums: claude/dep13_plan_2026-11-23.md).

Outputs (region, animal, item, eur_head):
  capri_data/2017/supply/livestock_input_cost.csv
  capri_data/baselines/capri_greendeal_ref/1730/supply/livestock_input_cost_2030.csv

    python tools/build/build_livestock_input_cost.py [DIR with res_17<CC>.txt]
"""
from __future__ import annotations

import csv
import gzip
import importlib.util
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib"), str(ROOT / "tools" / "build")]
from paths import BASE_YEAR, REFERENCE, SOURCES  # noqa: E402  (CAPRI's material outside the repository)
from capri_mod.data.definitions import capri_pairs, capri_set  # noqa: E402
from capri_mod.supply.equations.define_inputs import DATA_IY_Y, TF_I, p_yieldGrowth  # noqa: E402
from capri_mod.supply.equations.define_objc import IS_members, IobjCont  # noqa: E402
import _model_regions as _MR  # noqa: E402  (the regional units and their member states)

OUT17 = ROOT / "capri_data" / "2017" / "supply" / "livestock_input_cost.csv"
OUT30 = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply" / "livestock_input_cost_2030.csv"
SIMINI = REFERENCE / "simini" / "simini_21730"
YIELD_IY = ROOT / "capri_data" / "sources" / "raw" / "capri" / "gams" / "inputs" / "yieldIY_p_inputDemandFactor.parquet"
SIM_YEAR = 2030
#: the young animals bought (IS's young animals and the chicks ICHI, sets.gms l. 5051, 3338)
YOUNG = ("ICAM", "ICAF", "IHEI", "ICOW", "IPIG", "IBUL", "ILAM", "ICHI")
_ROW17 = re.compile(r"^'([A-Z0-9]+)'\.'([^']+)'\.'([^']+)'\.'Y'\s+([^,\s]+)")


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / "build" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _num(tok: str) -> float:
    t = tok.strip().rstrip(",").upper()
    return 0.0 if t in ("EPS", "NA", "UNDF", "+INF", "-INF", "INF") else float(t)


def input_sets() -> tuple:
    """(IobjCont, FEED) of CAPRI's sets (sets.gms; IS read from its text, I and FEED from the code lists)."""
    import gams_sets as G_
    gs = G_.read(SOURCES / "gams" / "sets.gms", SOURCES / "gams", {"BaseYear": BASE_YEAR, "BAS": BASE_YEAR[2:]})
    iwat = tuple(x[0] for x in gs.get("IWAT"))
    IS = IS_members((SOURCES / "gams" / "sets.gms").read_text(encoding="latin-1"))
    return IobjCont(capri_set("I"), IS, iwat), tuple(capri_set("FEED"))


def build_2017(dump_dir: Path, IY: tuple, FEED: tuple) -> tuple:
    """({item: {(CAPRI region, model animal): total 1000 EUR}}, check rows) of CAPREG's 2017 data."""
    B = _tool("build_livestock_output_coef")
    p2i = defaultdict(set)
    for a, i in capri_pairs("PACT_TO_I"):
        p2i[a].add(i)
    totals = defaultdict(lambda: defaultdict(float))
    check = []
    for path in sorted(dump_dir.glob("res_17*.txt")):
        data, uvap, uvag = {}, {}, {}
        for line in open(path, errors="ignore"):
            m = _ROW17.match(line)
            if not m:
                continue
            r, c, w, v = m.group(1), m.group(2), m.group(3), _num(m.group(4))
            if c in B.CAPRI_TO_MODEL:
                data[(r, c, w)] = v
            elif c == "UVAP":
                uvap[(r, w)] = v
            elif c == "UVAG":
                uvag[(r, w)] = v
        for (r, c, w), lv in list(data.items()):
            if w != "LEVL" or not lv:
                continue
            if len(r) != 8:                    # the member state's row of Turkey (TUR): its regions' rows are read
                continue
            ms = _MR.national_code(r)
            a = B.CAPRI_TO_MODEL[c]
            ins = p2i.get(c, set())
            iy_g = 0.0
            for i in IY:
                x = data.get((r, c, i), 0.0) if i in ins else 0.0
                if x:
                    totals[i][(r, a)] += lv * x * uvap.get((ms, i), 0.0) / 1000.0
                    iy_g += x * uvag.get((r, i), 0.0) / 1000.0
            yo = sum(data.get((r, c, i), 0.0) * uvag.get((r, i), 0.0) for i in YOUNG if i in ins) / 1000.0
            fe = sum(data.get((r, c, i), 0.0) * uvag.get((r, i), 0.0) for i in FEED if i in ins) / 1000.0
            totals["YOUNG"][(r, a)] += lv * yo
            totals["FEED"][(r, a)] += lv * fe
            toin = data.get((r, c, "TOIN"), 0.0)
            if toin:
                check.append((r, c, iy_g + yo + fe, toin))
    return totals, check


def read_simini(acts: set, IY: tuple) -> tuple:
    """sim_ini_21730's DATA {(region, activity, row, BAS | Y): value} of the activities and {(member state, input):
    UVAP at BAS}."""
    d, uvap = {}, {}
    with gzip.open(SIMINI / "DATA.csv.gz", "rt", newline="", encoding="utf-8") as fh:
        rd = csv.reader(fh)
        head = next(rd)
        assert head[:5] == ["d0", "d1", "d2", "d3", "value"], head
        for d0, d1, d2, d3, v, *_ in rd:
            if d3 not in ("BAS", "Y"):
                continue
            if d1 in acts:
                d[(d0, d1, d2, d3)] = float(v)
            elif d1 == "UVAP" and d3 == "BAS" and d2 in IY:
                uvap[(d0, d2)] = float(v)
    return d, uvap


def build_2030(IY: tuple) -> tuple:
    """({item: {(region, model animal): total 1000 EUR, CAPRI's 2030 money, before TF_I}}, check rows [(region, CAPRI
    activity, input, coefficient x TF_I)]) at CAPRI's simulation start."""
    import gams_sets as G_
    from _sources_io import source_records
    from build_plant_protection_capri_step_2030 import UVAP_Y, p_inflationFactor, read_p_infl
    O = _tool("build_livestock_output_2030")
    gs = G_.read(SOURCES / "gams" / "sets.gms", SOURCES / "gams", {"BaseYear": BASE_YEAR, "BAS": BASE_YEAR[2:]})
    p2y = defaultdict(list)
    for act, o in gs.get("PACT_TO_Y"):
        p2y[act.upper()].append(o.upper())
    p2i = defaultdict(set)
    for a, i in capri_pairs("PACT_TO_I"):
        p2i[a].add(i)
    fac = {(r["activity"], r["input"]): float(r["value"]) for r in source_records(YIELD_IY)}
    D, uvap_bas = read_simini(set(O.MAP), IY)
    infl = p_inflationFactor(read_p_infl(), SIM_YEAR, int(BASE_YEAR))
    tf = TF_I(1.0 - 0.005 * (SIM_YEAR - int(BASE_YEAR)))
    totals = defaultdict(lambda: defaultdict(float))
    check = []
    regs = {k[0] for k in D}
    for r in sorted(regs):
        if len(r) != 8:
            continue
        ms = _MR.national_code(r)
        for c, a in O.MAP.items():
            L, LB = D.get((r, c, "LEVL", "Y"), 0.0), D.get((r, c, "LEVL", "BAS"), 0.0)
            if not (L > 0 and LB):
                continue
            ys = [(D.get((r, c, o, "Y"), 0.0), D.get((r, c, o, "BAS"), 0.0)) for o in p2y.get(c, [])]
            G = p_yieldGrowth([y for y, _ in ys], [b for _, b in ys], LB)
            for i in IY:
                if i not in p2i.get(c, set()):
                    continue
                q = DATA_IY_Y(D.get((r, c, i, "BAS"), 0.0), fac.get((c, i), 1.0), G, 1.0)
                if q and (ms, i) in uvap_bas:
                    totals[i][(r, a)] += L * q * UVAP_Y(uvap_bas[(ms, i)], infl) / 1000.0
                    if _MR.is_unit(r):          # a member state's row of sim_ini is not its regions' sum
                        check.append((r, c, i, q * tf))
    return totals, check


def reference_2030(items: tuple, acts: set) -> dict:
    """CAPRI's 2030 reference coefficients {(region, activity, input): value} (dataOut at 2030), for the check."""
    from _grep import lines
    from paths import BASELINE_REF
    rx = re.compile(r"^'([A-Z0-9_]+)'\.''\.'([A-Za-z0-9_]+)'\.'([A-Z]+)'\.'2030'\s+(\S+)")
    out = {}
    for line in lines(BASELINE_REF):
        if "'2030'" not in line:
            continue
        m = rx.match(line)
        if m and m.group(2) in acts and m.group(3) in items:
            s = m.group(4).strip().rstrip(",")
            out[(m.group(1), m.group(2), m.group(3))] = 0.0 if s.upper() == "EPS" else float(s)
    return out


def write(totals: dict, herds: pd.DataFrame, out: Path) -> pd.DataFrame:
    B = _tool("build_livestock_output_coef")
    rows = []
    for item, tot in totals.items():
        coef = B.per_head(dict(tot), herds)
        for r in coef.index:
            for a in coef.columns:
                v = coef.at[r, a]
                if pd.notna(v) and v != 0.0:
                    rows.append((r, a, item, float(v)))
    t = pd.DataFrame(rows, columns=["region", "animal", "item", "eur_head"]).sort_values(["region", "animal", "item"])
    out.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(out, index=False)
    return t


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCES / "capreg"
    IY, FEED = input_sets()
    from capri_mod.data.loaders import load_regional_animal_numbers
    tot17, check = build_2017(src, IY, FEED)
    t17 = write(tot17, load_regional_animal_numbers(str(ROOT / "capri_data")), OUT17)
    rel = [abs(a / b - 1.0) for _, _, a, b in check if b]
    print(f"{OUT17.name}: {len(t17)} rows; the inputs at UVAG + YOUNG + FEED against CAPREG's TOIN: {len(rel)} rows, "
          f"max relative difference {max(rel):.2e}, {sum(x > 1e-6 for x in rel)} above 1e-6")
    Y = _tool("build_young_animals_2030")
    tot30, check30 = build_2030(IY)
    t30 = write(tot30, Y.herds_2030(), OUT30)
    print(f"{OUT30.name}: {len(t30)} rows, {t30.region.nunique()} regions; items {sorted(t30.item.unique())}")
    ref = reference_2030(tuple(IY), {c for _, c, _, _ in check30})
    dev = [abs(v / ref[(r, c, i)] - 1.0) for r, c, i, v in check30 if ref.get((r, c, i))]
    n_miss = sum(1 for r, c, i, _ in check30 if not ref.get((r, c, i)))
    print(f"check against CAPRI's 2030 reference (x TF_I): {len(dev)} rows, max relative difference {max(dev):.2e}, "
          f"{sum(x > 1e-5 for x in dev)} above 1e-5; {n_miss} without a reference value")


if __name__ == "__main__":
    main()
