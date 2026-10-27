"""Build CAPRI's young-animal balances per model region (herd links).

CAPRI (supply_model.gms INPANI_): young animals used as inputs (ICAM, ICAF,
IBUL, IHEI, ICOW per 1000 head of the using activity) equal young animals
available, produced as outputs of other activities (YCAM, YCAF, YBUL, YHEI,
YCOW). Aggregated to the model's cattle activities with CAPRI's 2017 herd
weights (LEVL), three balances per region:
  calves_m, calves_f   produced by DCOW, BCOW (YCAM, YCAF)  used by CALV (ICAM, ICAF)
  young_m, young_f     produced by CALV (YBUL, YHEI)        used by BULL (IBUL), HFRS (IHEI)
  cows                 produced by HFRS (YCOW)              used by DCOW, BCOW (ICOW)
(per sex since 22 October 2026, as CAPRI; calves and young cattle were pooled before)
Coefficients are per MODEL head: CAPRI's regional flow of the young animal (LEVL x
coefficient over its activities) divided by the model's head count of the activity, as
for livestock outputs (build_livestock_output_coef.py). The model's cattle head counts
differ from CAPRI's activity levels (DE11 fattening bulls: 5.2 model, 13.1 CAPRI), so
per-CAPRI-head coefficients gave base balances far from CAPRI's (EU: young cattle
produced 17.4 m against 5.5 m used); per model head, each region's base flows are CAPRI's
own. Spain has no res_17 dump in the project: its per-CAPRI-head coefficients (earlier
build) are scaled with CAPRI's 2030 activity levels (capri_mann_days_2030.csv)
(REGISTERED). Base value per head = CAPRI unit value (UVAG) of the young animal, national.

    python tools/build/build_young_animals.py [--dump-dir DIR]
"""
from __future__ import annotations
import argparse, glob, json, re, sys
from collections import defaultdict
from pathlib import Path


def _read_csv(*a, **k):
    """pandas.read_csv with floats parsed to the last digit (KNOWN_ISSUES K82)."""
    import pandas as pd
    k.setdefault("float_precision", "round_trip")
    return pd.read_csv(*a, **k)

_ROOT = Path(__file__).resolve().parents[2]
MAP = {"DCOW": "DCOW", "SCOW": "BCOW", "BULF": "BULL", "HEIF": "HFRS", "HEIR": "HFRS",
       "CAMF": "CALV", "CAFF": "CALV", "CAMR": "CALV", "CAFR": "CALV",
       "SOWS": "PIGS", "PIGF": "PIGF", "SHGM": "SHGM", "SHGF": "SHGF"}
#: two groupings, two files:
#: - BAL_BY_SEX (young_animals_by_sex_2017.json), CAPRI's balances (INPANI_ per young animal): male and female calves
#:   (YCAM / ICAM, YCAF / ICAF), young bulls and young heifers (YBUL / IBUL, YHEI / IHEI); read with the model's cattle
#:   member splits (RegionalSupplyModel.use_cattle_member_splits);
#: - BAL_POOLED (young_animals_2017.json, the model's default): calves and young cattle pooled across the sexes (the
#:   per-sex markets did not converge yet, KNOWN_ISSUES K65)
BAL_BY_SEX = {"calves_m": ({"YCAM"}, {"ICAM"}, ("YCAM",)),
       "calves_f": ({"YCAF"}, {"ICAF"}, ("YCAF",)),
       "young_m": ({"YBUL"}, {"IBUL"}, ("YBUL",)),
       "young_f": ({"YHEI"}, {"IHEI"}, ("YHEI",)),
       "cows": ({"YCOW"}, {"ICOW"}, ("YCOW",)),
       # piglets: sows produce YPIG, fattening pigs (one piglet each) and sows (replacement gilts) use IPIG
       "piglets": ({"YPIG"}, {"IPIG"}, ("YPIG",)),
       # lambs: sheep and goats for milk (breeding ewes and goats) produce YLAM, fattening (one lamb each) and
       # replacement in SHGM use ILAM (CAPRI sets.gms YLAM.ILAM), since the sheep and goat split (October 2026)
       "lambs": ({"YLAM"}, {"ILAM"}, ("YLAM",))}


BAL_POOLED = {"calves": ({"YCAM", "YCAF"}, {"ICAM", "ICAF"}, ("YCAM", "YCAF")),
              "young": ({"YBUL", "YHEI"}, {"IBUL", "IHEI"}, ("YBUL", "YHEI")),
              **{k: v for k, v in BAL_BY_SEX.items() if k not in ("calves_m", "calves_f", "young_m", "young_f")}}
BAL = BAL_POOLED
VARIANTS = (("young_animals_2017.json", BAL_POOLED), ("young_animals_by_sex_2017.json", BAL_BY_SEX))


def main() -> None:
    global BAL
    for name, bal in VARIANTS:
        BAL = bal
        build(name)


def build(dest_name: str) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    ap.add_argument("--old-json", default=None, help="earlier build (per CAPRI head) for Spain")
    args = ap.parse_args()
    import pandas as pd
    herds = _read_csv(_ROOT / "capri_data" / "2017" / "supply" / "animal_numbers.csv", index_col=0)
    corr = json.loads((_ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]
    items = {i for b in BAL.values() for i in b[0] | b[1]}
    row = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.'([A-Z0-9]{4})'\.'([A-Z0-9]{4})'\.'Y'\s+(-?\d[\d.Ee+\-]*)")
    v = defaultdict(dict)
    for f in glob.glob(str(args.dump_dir / "res_17*.txt")):
        for line in open(f, errors="ignore"):
            m = row.match(line)
            if not m:
                continue
            r8, a, it, val = m.group(1), m.group(2), m.group(3), float(m.group(4))
            if (a in MAP and (it in items or it == "LEVL")) or (a == "UVAG" and r8.endswith("000000")):
                v[r8][(a, it)] = val

    def to_model(c8):
        for c in corr.get(c8, []):
            if c in herds.index:
                return c

    import importlib.util as _iu
    _sp = _iu.spec_from_file_location("_mr", _ROOT / "tools" / "lib" / "_model_regions.py")
    _mr = _iu.module_from_spec(_sp); _sp.loader.exec_module(_mr)
    HCOL = {"DCOW": "DCOW", "BCOW": "SCOW", "BULL": "BULL", "HFRS": "HEIF", "CALV": "CALV", "PIGS": "PIGS", "PIGF": "PIGF",
            "SHGM": "SHGM", "SHGF": "SHGF"}

    # CAPRI regions per model region through the shared groups (splits, merges, renamed regions):
    # a group's flows over the group's model heads
    _c2g, _groups = _mr.capri_groups(list(herds.index))
    grp_of = {r: (sorted(c for c in cs if c in v), sorted(rs)) for cs, rs in _groups.values() for r in rs}

    def coefs(r8, reg):
        codes = [r8] if isinstance(r8, str) else list(r8)
        num, lev = defaultdict(float), defaultdict(float)
        for code in codes:
            d = v.get(code, {})
            for (a, it), val in d.items():
                if a in MAP and it == "LEVL":
                    lev[MAP[a]] += val
            for (a, it), val in d.items():
                if a in MAP and it in items:
                    num[(MAP[a], it)] += d.get((a, "LEVL"), 0.0) * val / 1000.0
        out = {}
        if isinstance(r8, str) and r8.endswith("000000"):     # national flows over the country's model heads
            regs = [r for r in herds.index if _mr.national_code(r) == r8]
            hd = {m: float(herds.loc[regs, HCOL[m]].sum()) if HCOL[m] in herds.columns else 0.0 for m in lev}
        else:
            regs = grp_of.get(reg, ([], [reg]))[1]
            hd = {m: float(herds.loc[regs, HCOL[m]].sum()) if HCOL[m] in herds.columns else 0.0 for m in lev}
        for b, (prod, use, _) in BAL.items():
            pc = {m: sum(num[(m, i)] for i in prod) / hd[m] for m in lev if hd[m] > 0 and sum(num[(m, i)] for i in prod) > 0}
            uc = {m: sum(num[(m, i)] for i in use) / hd[m] for m in lev if hd[m] > 0 and sum(num[(m, i)] for i in use) > 0}
            if pc and uc:
                out[b] = {"produce": pc, "use": uc}
        return out

    # Spain (no res_17 dump): earlier per-CAPRI-head coefficients x CAPRI 2030 levels / model heads
    old_es = {}
    _old = Path(args.old_json) if args.old_json else None
    if _old and _old.exists():
        md = _read_csv(_ROOT / "capri_data" / "2017" / "abatement" / "ammonia" / "capri_mann_days_2030.csv")
        L30 = defaultdict(float)
        SUB = {"DCOL": "DCOW", "DCOH": "DCOW", "BULL": "BULL", "BULH": "BULL", "HEIL": "HFRS", "HEIH": "HFRS", "HEIR": "HFRS",
               "SCOW": "BCOW", "CAMR": "CALV", "CAFR": "CALV", "CAMF": "CALV", "CAFF": "CALV"}
        for r in md[md["item"] == "LEVL"].itertuples():
            if r.activity in SUB:
                for n2 in corr.get(r.region, []):
                    L30[(n2, SUB[r.activity])] += float(r.value)
        for reg, rec in json.loads(_old.read_text())["regions"].items():
            if not reg.startswith("ES") or reg not in herds.index:
                continue
            out = {}
            for b, d in rec.items():
                sc = lambda m: L30.get((reg, m), 0.0) / max(float(herds.loc[reg].get(HCOL[m], 0.0) or 0.0), 1e-9)
                out[b] = {"produce": {m: c * sc(m) for m, c in d["produce"].items() if sc(m) > 0},
                          "use": {m: c * sc(m) for m, c in d["use"].items() if sc(m) > 0}}
            old_es[reg] = out

    nat_uvag = {}
    for r8, d in v.items():
        if r8.endswith("000000"):
            nat_uvag[r8[:2]] = {b: (sum(d.get(("UVAG", i), 0.0) for i in BAL[b][2]) / len(BAL[b][2])) for b in BAL}
    res, nat_used = {}, 0
    for reg in herds.index:
        c8 = grp_of.get(reg, ([], []))[0] or None
        cf = coefs(c8, reg) if c8 else {}
        if not cf:
            _nc = _mr.national_code(reg)
            cf = coefs(_nc, reg) if _nc in v else {}
            nat_used += bool(cf)
            if cf:            # national flows: the region's share by model heads
                pass
        if not cf and reg in old_es:
            cf = old_es[reg]
        if not cf:
            continue
        rec = {}
        for b, d in cf.items():
            x = herds.loc[reg]
            prod0 = sum(c * float(x.get(m, 0.0)) for m, c in d["produce"].items())
            use0 = sum(c * float(x.get(m, 0.0)) for m, c in d["use"].items())
            if prod0 <= 0 and use0 <= 0:
                continue
            rec[b] = {**d, "base_net_export": prod0 - use0,
                      "value_eur_head": float(nat_uvag.get(_mr.national_code(reg)[:2], {}).get(b, 0.0))}
        if rec:
            res[reg] = rec
    # countries without a national UVAG in the dumps (Spain): median of the other countries (REGISTERED)
    import statistics as _st
    med = {b: _st.median([r[b]["value_eur_head"] for r in res.values() if b in r and r[b]["value_eur_head"] > 0])
           for b in BAL}
    for r in res.values():
        for b, x in r.items():
            if not x["value_eur_head"]:
                x["value_eur_head"] = med[b]
    dest = _ROOT / "capri_data" / "2017" / "supply" / dest_name
    dest.write_text(json.dumps({"_source": "CAPRI 2017 regional results (res_17*): YCAM/YCAF/YBUL/YHEI/YCOW/YPIG outputs and ICAM/ICAF/IBUL/IHEI/ICOW/IPIG "
                                "inputs per 1000 head, LEVL weights; national UVAG; supply_model.gms INPANI_",
                                "_units": "head per head; 1000 head (base_net_export); EUR per head (value)", "regions": res}, indent=1))
    print(f"wrote {dest}: {len(res)} regions ({nat_used} from national rows)")


if __name__ == "__main__":
    main()
