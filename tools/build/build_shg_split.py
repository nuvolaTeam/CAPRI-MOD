"""Split the model's single sheep-and-goat activity into CAPRI's two: SHGM and SHGF (October 2026).

CAPRI (supply/define_activities, sets.gms) has SHGM (sheep and goats for milk: output milk SGMI, meat SGMT from
lambs and culled animals, manure) and SHGF (sheep and goats for fattening: output meat SGMT, manure), each with its
own PMP terms, feed requirements, costs and premiums. The model kept both in SHGP (census stock SHGO). The meat
market, whose model code was SHGM, is now CAPRI's SGMT (the code SHGM is CAPRI's milk activity).

Herds (census stock, 1000 head, animal_numbers.csv): the census SHGO split by CAPRI's LEVL shares of SHGM and SHGF
(res_17 dumps, 2017), per group of CAPRI and model regions covering the same territory (tools/lib/_model_regions.py);
regions without regional CAPRI rows take their member state's share.

Then every per-head table is rebuilt with CAPRI's activities mapped one to one (SHGM -> SHGM, SHGF -> SHGF) by the
existing builders, each checked beforehand to reproduce the current files with the old mapping (--reproduce).

Usage: python tools/build/build_shg_split.py [--dump-dir /home/claude/work/capreg] [--reproduce]
"""
import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

#: builders run after the herd split, in dependency order (pig split order, plus the builders added since)
STEPS = (["tools/build/build_livestock_premium_coef.py", "{dump}"], ["tools/build/build_feed_ration.py", "--dump-dir", "{dump}"],
         ["tools/build/build_nh3_factors.py"], ["tools/build/build_ammonia_tech_model.py"],
         ["tools/build/build_young_animals.py", "--dump-dir", "{dump}"], ["tools/build/build_fodder_balance.py"],
         ["tools/build/build_livestock_products.py", "--dump-dir", "{dump}"], ["tools/build/build_manure_losses.py"],
         ["tools/build/build_genetics_effects.py", "--dump-dir", "{dump}"], ["tools/build/build_lownfeed_effects.py"],
         ["tools/build/build_supplement_effects.py"], ["tools/build/build_manure_n2o.py", "--dump-dir", "{dump}"],
         ["tools/build/build_ghg_coefs_2017.py", "{dump}"])


def coefficient_tables(dump: Path):
    sys.path.insert(0, str(ROOT)); sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check", "check/nlp_check")]
    import build_livestock_output_coef as B
    D = ROOT / "capri_data" / "2017"
    B.build(dump).to_csv(D / "supply" / "livestock_output_coef.csv")
    for item, dest in (("MREV", "supply/livestock_revenue_coef.csv"), ("TOIN", "supply/livestock_cost_coef.csv"),
                       ("TOOU", "supply/livestock_output_value_coef.csv"), ("MANN", "environment/livestock_manure_n_coef.csv")):
        B.build(dump, item).to_csv(D / dest)
    B.build(dump, "FINAL_VALUE").to_csv(D / "supply" / "livestock_product_value_coef.csv")
    B.build_product_values_by_market(dump).to_csv(D / "supply" / "livestock_product_value_by_market_coef.csv")
    feed = []
    for item, suf in (("FCER", "cereals"), ("FPRO", "protein"), ("FENE", "energy")):
        t = B.build(dump, item) / 1000.0
        feed.append(t.rename(columns=lambda c: f"{c}_{suf}"))
    pd.concat(feed, axis=1).to_csv(D / "feed" / "livestock_feed_coef.csv")


def run_steps(dump: Path):
    for cmd in STEPS:
        cmd = [c.format(dump=dump) for c in cmd]
        r = subprocess.run([sys.executable] + cmd, cwd=ROOT, capture_output=True, text=True)
        tail = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
        print(cmd[0], "->", tail[:160], ("FAILED: " + r.stderr.strip()[-400:]) if r.returncode else "")


def per_head_tables(dump: Path):
    """yields.csv, variable_costs.csv (per head, CAPRI's YILD and TOIN of SHGM and SHGF, LEVL-weighted per region
    group, national where the group has no regional rows) and producer_prices.csv (CAPREG's regional producer prices
    of SHGM, SHGF, herd-weighted EU mean, as the other rows of that table): the columns of the old SHGP are replaced.
    YILD of SHGM is milk per head, of SHGF meat per head (CAPRI)."""
    import glob, re
    from collections import defaultdict
    import importlib.util as _ilu
    sp = _ilu.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = _ilu.module_from_spec(sp); sp.loader.exec_module(mr)
    v = defaultdict(dict)
    pat = re.compile(r"^'([A-Z]{2}[A-Z0-9]{6})'\.'(SHGM|SHGF)'\.'(LEVL|YILD|TOIN)'\.'Y'\s+([-\d.Ee+]+)")
    for p in sorted(glob.glob(str(dump / "res_17*.txt"))):
        for line in open(p, errors="ignore"):
            m = pat.match(line)
            if m:
                v[(m.group(1), m.group(2))][m.group(3)] = float(m.group(4))
    S = ROOT / "capri_data" / "2017" / "supply"
    herds = pd.read_csv(S / "animal_numbers.csv", index_col=0)
    _c2g, groups = mr.capri_groups(list(herds.index))

    def weighted(codes, act, item):
        num = den = 0.0
        for c in codes:
            d = v.get((c, act), {})
            if d.get("LEVL", 0) > 0:                     # an absent item is 0 (GAMS): milk sheep without milk
                num += d["LEVL"] * d.get(item, 0.0); den += d["LEVL"]
        return num / den if den > 0 else None

    for fname, item in (("yields.csv", "YILD"), ("variable_costs.csv", "TOIN")):
        t = pd.read_csv(S / fname, index_col=0)
        for act in ("SHGM", "SHGF"):
            col = pd.Series(float("nan"), index=t.index)
            for codes, regs in groups.values():
                x = weighted([c for c in codes if not c.endswith("000000")], act, item)
                if x is not None:
                    for r in regs:
                        if r in col.index:
                            col[r] = round(x, 4)
            for r in col.index[col.isna()]:
                x = weighted([mr.national_code(r)], act, item)
                if x is not None:
                    col[r] = round(x, 4)
            t[act] = col
        if "SHGP" in t.columns:
            i = list(t.columns).index("SHGP")
            cols = [c for c in t.columns if c not in ("SHGP", "SHGM", "SHGF")]
            t = t[cols[:i] + ["SHGM", "SHGF"] + cols[i:]]
        t.to_csv(S / fname)
        print(f"{fname}: SHGM median {t['SHGM'].median():.2f}, SHGF median {t['SHGF'].median():.2f} ({item})")
    pp = pd.read_csv(ROOT / "capri_data" / "2017" / "market" / "producer_prices.csv", index_col=0)
    cp = pd.read_csv(ROOT / "capri_data" / "sources" / "capreg" / "capreg_producer_prices.csv", index_col=0)
    for act in ("SHGM", "SHGF"):
        w = herds[act].reindex(cp.index).fillna(0.0)
        x = cp[act].where(cp[act] > 0)
        ok = x.notna() & (w > 0)
        pp.loc[act, pp.columns[0]] = round(float((x[ok] * w[ok]).sum() / w[ok].sum()), 4)
    pp = pp.drop(index=["SHGP"], errors="ignore")
    pp.to_csv(ROOT / "capri_data" / "2017" / "market" / "producer_prices.csv")
    print("producer_prices.csv:", pp.loc[["SHGM", "SHGF"]].iloc[:, 0].to_dict())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", default="/home/claude/work/capreg")
    ap.add_argument("--reproduce", action="store_true", help="rebuild with the current mapping only (no herd split)")
    a = ap.parse_args()
    dump = Path(a.dump_dir)
    if not a.reproduce:
        split_herds(dump)
        per_head_tables(dump)
    coefficient_tables(dump)
    run_steps(dump)


def split_herds(dump: Path):
    """animal_numbers.csv: SHGO (CAPRI's SHGT HERD) -> SHGM + SHGF at CAPRI's HERD shares of the region's group
    (national shares where the group has no regional CAPRI rows)."""
    import glob, re
    from collections import defaultdict
    f = ROOT / "capri_data" / "2017" / "supply" / "animal_numbers.csv"
    a = pd.read_csv(f, index_col=0)
    if "SHGO" not in a.columns:
        print("animal_numbers.csv already split (no SHGO column)")
        return
    herd = defaultdict(dict)                                  # CAPRI code -> {SHGM, SHGF}
    pat = re.compile(r"^'([A-Z]{2}[A-Z0-9]{6})'\.'(SHGM|SHGF)'\.'HERD'\.'Y'\s+([-\d.Ee+]+)")
    for p in sorted(glob.glob(str(dump / "res_17*.txt"))):
        for line in open(p, errors="ignore"):
            m = pat.match(line)
            if m:
                herd[m.group(1)][m.group(2)] = float(m.group(3))
    import importlib.util as _ilu
    sp = _ilu.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = _ilu.module_from_spec(sp); sp.loader.exec_module(mr)
    _c2g, groups = mr.capri_groups(list(a.index))
    share, src = {}, defaultdict(int)
    for codes, regs in groups.values():
        m_ = sum(herd.get(c, {}).get("SHGM", 0.0) for c in codes if not c.endswith("000000"))
        f_ = sum(herd.get(c, {}).get("SHGF", 0.0) for c in codes if not c.endswith("000000"))
        if m_ + f_ > 0:
            for r in regs:
                share[r] = m_ / (m_ + f_)
    tot = a["SHGO"].fillna(0.0)
    sm = pd.Series(0.0, index=a.index)
    for r in a.index:
        if tot[r] <= 0:
            continue
        if r in share:
            s_ = share[r]; src["regional"] += 1
        else:
            nat = herd.get(mr.national_code(r), {})
            s_ = nat.get("SHGM", 0.0) / (nat.get("SHGM", 0.0) + nat.get("SHGF", 0.0)) \
                if nat.get("SHGM", 0.0) + nat.get("SHGF", 0.0) > 0 else 0.5
            src["national" if nat else "none (0.5)"] += 1
        sm[r] = s_
    a["SHGM"] = (tot * sm).round(6)
    a["SHGF"] = (tot - a["SHGM"]).clip(lower=0.0)
    cols = [c for c in a.columns if c not in ("SHGM", "SHGF")]
    i = cols.index("SHGO")
    a = a[cols[:i] + ["SHGM", "SHGF"] + cols[i + 1:]]
    a.to_csv(f)
    eu = {k: herd.get(k, {}) for k in herd if k.endswith("000000")}
    cm = sum(v.get("SHGM", 0) for v in eu.values()); cf = sum(v.get("SHGF", 0) for v in eu.values())
    print(f"animal_numbers.csv: SHGM {a['SHGM'].sum():.0f}, SHGF {a['SHGF'].sum():.0f} (1000 head; CAPRI national HERD "
          f"sums {cm:.0f}, {cf:.0f}); shares {dict(src)}")


if __name__ == "__main__":
    main()
