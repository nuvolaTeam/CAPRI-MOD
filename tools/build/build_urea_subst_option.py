"""CAPRI's urea substitution (UreaSubst; envind/ammo_tech.gms) per member state, for the regional model's urea column
(capri_mod/supply/abatement.py _urea_spec).

CAPRI's Green Deal settings (pol_input/greendeal/refpol_endotech_all_sup.gms: ghgAbatement on, UreaSubst in the active
list l. 213-222, premCapMitTech off) give the option in every region: the share v of the mineral N bought that is
switched from urea to other fertilisers (v_Miti(RU, cropMiti, UreaSubst, NH3SYN)), 0 <= v <= MaxShare = the member
state's urea share; its NH3 of mineral N, GASTOTNETF_'s (1 - v x othImpact) with othImpact the NH3 emission factor of
urea less the others' (l. 2358-2361); its cost per t of N bought (l. 2372-2375); its calibration as the ammonia options
(l. 2840-2977, 3041-3047, 3100-3107), case 3 where the cost is positive (IniShare 0). The model's equations of these
statements: capri_mod/supply/equations/ammo_tech.py.

Money: CAPRI's cost is in the base year's money and not inflated to the simulation year (ammo_tech.gms l. 3355-3358
inflates the animals' options only; ghgMiti.gms's inflation, l. 155-158, runs before ammo_tech.gms, capmod.gms l. 779
and 1113), so in CAPRI's 2030 objective it is a base-year figure next to 2030 prices. The table keeps CAPRI's numbers in
the model's money: the 2030 objective's term over the model's deflator(2030) (tools/lib/_money.py), as every CAPRI 2030
term the builders hand over.

Sources: capri_data/2017/abatement/ammonia/FracUseFert.csv and EmFracFert.csv (CAPRI's p_fracUseFert, p_emFracFert),
capri_data/2017/supply/mineral_n_price.csv (CAPRI's 2017 UVAG of NITF per member state), sim_ini_21730's p_infl
(capri_sources/reference/simini/simini_21730/p_infl.csv.gz).

Output: capri_data/2017/abatement/mitigation/urea_subst_option.csv
    ms, frac_urea, max_share, nh3_othimpact, cost_lin_eur_t, relsubs0, relsubs1, subs0, subs1, pmp_sqr, pmp_lin, case

    python tools/build/build_urea_subst_option.py [--check]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools" / "lib"))
from _money import deflator                                             # noqa: E402
from paths import REFERENCE  # noqa: E402  (CAPRI's material outside the repository)
from capri_mod.supply.equations.ammo_tech import (                     # noqa: E402
    MaxShare_UreaSubst, othImpact_NH3SYN_UreaSubst, costParLin_UreaSubst, relSubs_ammTech, Subs_ammTech,
    pmpParsqr_UreaSubst, pmpParlin_UreaSubst)

AMM = ROOT / "capri_data" / "2017" / "abatement" / "ammonia"
PRICE = ROOT / "capri_data" / "2017" / "supply" / "mineral_n_price.csv"
PINFL = REFERENCE / "simini" / "simini_21730" / "p_infl.csv.gz"
OUT = ROOT / "capri_data" / "2017" / "abatement" / "mitigation" / "urea_subst_option.csv"
BAS, YEAR_2007 = 2017, 2007


def main(check: bool = False):
    fu = pd.read_csv(AMM / "FracUseFert.csv", float_precision="round_trip").pivot_table(
        index="region", columns="fertiliser", values="value")
    ef = pd.read_csv(AMM / "EmFracFert.csv", float_precision="round_trip")
    ef = ef[ef["gas"] == "NH3"].pivot_table(index="region", columns="fertiliser", values="value")
    pr = pd.read_csv(PRICE, float_precision="round_trip").drop_duplicates("capri_code").set_index("capri_code")["eur_per_t_n"]
    p_infl = float(pd.read_csv(PINFL, float_precision="round_trip")["value"].iloc[0])
    defl = deflator(2030)
    rows = []
    for ms in sorted(fu.index):
        cc = ms[:2]
        if cc not in pr.index or ms not in ef.index:
            continue
        u, o = float(fu.at[ms, "Ureum"]), float(fu.at[ms, "Other"])
        m1 = MaxShare_UreaSubst(u)
        if not m1 > 0:
            continue
        k = costParLin_UreaSubst(float(pr[cc]), u, o, p_infl, BAS - YEAR_2007) / defl
        r0, r1, case = relSubs_ammTech(k, 0.0, 0.0, 1.0)
        s0, s1 = Subs_ammTech(r0, k), Subs_ammTech(r1, k)
        g = pmpParsqr_UreaSubst(s0, s1, m1, 0.0)
        rows.append({"ms": ms, "frac_urea": u, "max_share": m1,
                     "nh3_othimpact": othImpact_NH3SYN_UreaSubst(ef.at[ms, "Ureum"], ef.at[ms, "Other"]),
                     "cost_lin_eur_t": k, "relsubs0": r0, "relsubs1": r1, "subs0": s0, "subs1": s1, "pmp_sqr": g,
                     "pmp_lin": pmpParlin_UreaSubst(0.0, k, s0, g, 0.0), "case": case})
    out = pd.DataFrame(rows)
    print(f"urea substitution: {len(out)} member states; cost per t N switched, model money: median "
          f"{out['cost_lin_eur_t'].median():.1f} (min {out['cost_lin_eur_t'].min():.1f}); cases {out['case'].value_counts().to_dict()}")
    if check:
        old = pd.read_csv(OUT, float_precision="round_trip")
        pd.testing.assert_frame_equal(old, out.astype(old.dtypes.to_dict()), check_exact=False, rtol=1e-12)
        print("unchanged:", OUT.relative_to(ROOT))
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print("wrote", OUT.relative_to(ROOT), len(out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    main(ap.parse_args().check)
