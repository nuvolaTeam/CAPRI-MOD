"""CAPRI's feed energy balance of the non-EU market regions (audit M3): calorie contents and the feed conversion factors
of arm/feed_conv.gms, at CAPRI's 2030 market calibration point.

CAPRI (arm/market_model.gms l. 1018-1048): outside the regions with supply models, each behavioural region's feed use
follows its normalised-quadratic feed cost function FeedNQ_, whose prices include the region's feed energy price FEDE
(v_prodPrice(RMS, "FEDE")), and FeedBal_ makes the energy of the feed used equal the energy the region's animal output
needs:

    sum_xx feed_xx * cal_xx  =  sum_anim prod_anim * feedConv_anim          (both over the base energy fed)

The feed conversion factors are estimated once per calibration (arm/feed_conv.gms, model m_fitFeedConv of
feed_conv_decl.gms), per behavioural region r, over its animal products a (XX_ANIM_FEED: BEEF, PORK, SGMT, POUM, EGGS,
MILK) with output:

    min  sum_a  ((c_a - m_a) / s_a)^2 * prod_a * cal_a
    s.t. sum_xx feed_xx * cal_xx = sum_a prod_a * cal_a * c_a                      FedeBal_
         ppri_a * share  >=  cal_a * c_a * aveFeedCost                            FeedCost_
         0.001 m_a <= c_a <= 20 m_a
    aveFeedCost = sum_xx feed_xx * (arm1P_xx - FSEi_xx) / sum_xx feed_xx * cal_xx   (EUR per kcal fed)

m_a the expected "kg of maize per kg of product" in energy terms (3.5 SGMT, 3.0 BEEF, 2.5 PORK, 2.2 POUM, 2.0 EGGS, 0.8
MILK, times cal_MAIZ / cal_a; for SGMT CAPRI divides by BEEF's calories), s_a its standard deviation (0.6, 0.6, 0.1,
0.1, 0.1, 0.5 times m_a), share = 0.7, raised by 0.1 while the fit is infeasible (at most 100 solves). The fitted factor
is fixed as c_a * cal_a (kcal fed per t of product), the value FeedBal_ uses.

The problem separates by region (FedeBal_ and FeedCost_ are per region; the objective is a sum), and its solution is
exact: with the multiplier mu of FedeBal_, c_a = clip(m_a + mu s_a^2, lo_a, up_a), up_a the smaller of 20 m_a and
FeedCost_'s bound; mu by bisection on FedeBal_. CAPRI raises the share of every region whose FeedCost_ has a marginal
while the joint model is infeasible; at an infeasible solve GAMS's marginals are those of the infeasibility, which
involve the infeasible regions' constraints, so here the share is raised for an infeasible region (REGISTERED as this
port's reading).

FEDE at the calibration point (arm/market1.gms l. 402-408): quantity = sum_xx feed_xx * cal_xx, price = sum_xx feed_xx *
arm1P_xx / quantity (EUR per kcal, the region's market region's Arm1 prices).

Calorie contents (arm/market_model.gms l. 300-313): p_calContent(XX1) = p_nutrientCont(xx, "Energ_cal") of CAPRI's
dat/arm/nutrient_cont_usda.gdx (kcal per kg; capri_data/sources/capri_star/nutrient_cont_usda_export.xlsx, the GDX's
export); a product without one counts no energy (p_noCal).

Data: CAPRI's 2030 market calibration, Data_CAL of data_market_1730defaulta.csv (FEED, PROD, PPRI of each behavioural
region, ARM1P of its market region; FSEi, the feed subsidy, is not in the file: 0).

Outputs (capri_data/2017/market):
  feed_cal_content.csv      product, kcal_per_kg
  noneu_feed_energy.csv     rms, rm, fede_kcal (1000 t x kcal/kg), fede_price (EUR/t per kcal/kg), ave_feed_cost,
                            feed_cost_share, solves
  noneu_feed_conv.csv       rms, product, prod_kt, conv (the fitted c_a), feed_conv (c_a * cal_a), expected (m_a),
                            upper (FeedCost_'s bound on c_a), binding (FeedCost_ binding)
for the behavioural regions outside the EU without supply models (FeedBal_'s domain), with feed and animal output.

    python tools/build/build_feed_energy.py [--data FILE] [--cal XLSX]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from build_noneu_market_supply_nq import EU_RM, UNITS, num, read_param  # noqa: E402

UP = Path("/mnt/user-data/uploads")
DATA = UP / "data_market_1730defaulta.csv"
CAL = ROOT / "capri_data" / "sources" / "capri_star" / "nutrient_cont_usda_export.xlsx"
OUT = ROOT / "capri_data" / "2017" / "market"
#: arm/arm_sets.gms XX_ANIM_FEED (MEAT_DEF + EGGS + MILK)
ANIM = ("BEEF", "PORK", "SGMT", "POUM", "EGGS", "MILK")
#: arm/feed_conv.gms: expected kg of maize per kg of product, the calories it is divided by, the relative std. deviation
EXPECTED = {"SGMT": (3.5, "BEEF", 0.6), "BEEF": (3.0, "BEEF", 0.6), "PORK": (2.5, "PORK", 0.1),
            "POUM": (2.2, "POUM", 0.1), "EGGS": (2.0, "EGGS", 0.1), "MILK": (0.8, "MILK", 0.5)}
LO, UPF, MAXSOLVES = 0.001, 20.0, 100
#: FeedCost_'s share of the producer price: 0.7, raised by 0.1 at each infeasible solve (in tenths)
SHARE0_TENTHS, STEP_TENTHS = 7, 1
SHARE0 = SHARE0_TENTHS / 10.0


def calories(path: Path) -> dict:
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True)["p_nutrientCont"]
    return {str(r[0]): float(r[2]) for r in ws.iter_rows(values_only=True) if r[1] == "Energ_cal" and r[2]}


def fit_region(feed_e: float, prod: dict, cal: dict, ppri: dict, ave: float, share: float, m: dict, s: dict):
    """(conv, upper, feasible) of one region at the share; conv per product with output."""
    acts = [a for a in ANIM if prod.get(a, 0.0) > 0 and cal.get(a)]
    lo = {a: LO * m[a] for a in acts}
    up = {a: UPF * m[a] for a in acts}
    for a in acts:
        if ave > 0:
            up[a] = min(up[a], ppri.get(a, 0.0) * share / (cal[a] * ave))
    w = {a: prod[a] * cal[a] for a in acts}
    if any(up[a] < lo[a] for a in acts):
        return None, up, False

    def bal(mu):
        return sum(w[a] * min(max(m[a] + mu * s[a] ** 2, lo[a]), up[a]) for a in acts) - feed_e

    if not acts or bal(-1e30) > 1e-9 * feed_e or bal(1e30) < -1e-9 * feed_e:
        return None, up, False
    a_, b_ = -1.0, 1.0
    while bal(a_) > 0:
        a_ *= 2
    while bal(b_) < 0:
        b_ *= 2
    for _ in range(200):
        mid = 0.5 * (a_ + b_)
        if bal(mid) > 0:
            b_ = mid
        else:
            a_ = mid
    mu = 0.5 * (a_ + b_)
    return {a: min(max(m[a] + mu * s[a] ** 2, lo[a]), up[a]) for a in acts}, up, True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--cal", type=Path, default=CAL)
    a = ap.parse_args()
    cal_all = calories(a.cal)
    with open(ROOT / "capri_data" / "schema" / "codes" / "capri" / "XX.csv", newline="") as f:
        xx = {r["code"] for r in csv.DictReader(f)}
    cal = {k: v for k, v in cal_all.items() if k in xx}
    with open(ROOT / "capri_data" / "shared" / "rms_to_rm.csv", newline="") as f:
        rm_of = {r["rms"]: r["rm"] for r in csv.DictReader(f)}
    with open(UNITS, newline="") as f:
        ctry = {r["region"][:2] for r in csv.DictReader(f)}
    noneu = {r for r, m in rm_of.items() if m not in EU_RM}
    rmssup = {r for r in noneu if (r.endswith("000000") and r[:2] in ctry) or (r == "TUR" and "TR" in ctry)}
    regs = sorted(noneu - rmssup)
    keep_r = set(regs) | {rm_of[r] for r in regs}
    pat = re.compile(r"^'([^']*)'\.'(FEED|PROD|PPRI|ARM1P|FSEI)'\.'([^']*)'\.'CAL'\s+(\S+)")
    data = defaultdict(dict)
    for r, it, p, v in read_param(a.data, "Data_CAL", pat, lambda m: m.group(1) in keep_r and m.group(3) in xx):
        data[(r, it)][p] = num(v)
    m_ = {k: f * cal["MAIZ"] / cal[d] for k, (f, d, _) in EXPECTED.items()}
    s_ = {k: EXPECTED[k][2] * m_[k] for k in EXPECTED}
    reg_rows, conv_rows = [], []
    for r in regs:
        rm = rm_of[r]
        feed = data.get((r, "FEED"), {})
        prod = {k: data.get((r, "PROD"), {}).get(k, 0.0) for k in ANIM}
        ppri = data.get((r, "PPRI"), {})
        arm = data.get((rm, "ARM1P"), {})
        fsei = data.get((rm, "FSEI"), {})
        feed_e = sum(q * cal.get(p, 0.0) for p, q in feed.items())
        if feed_e <= 0 or not any(prod[k] > 0 and k in cal for k in ANIM):
            continue
        ave = sum(q * (arm.get(p, 0.0) - fsei.get(p, 0.0)) for p, q in feed.items()) / feed_e
        # the share in tenths (CAPRI adds 0.1 per solve; counted here in whole tenths so the written share is the
        # decimal value, not an accumulated sum such as 0.7999999999999999)
        n = 1
        share = SHARE0
        conv, up, ok = fit_region(feed_e, prod, cal, ppri, ave, share, m_, s_)
        while not ok and n < MAXSOLVES:
            n += 1
            share = (SHARE0_TENTHS + (n - 1) * STEP_TENTHS) / 10.0
            conv, up, ok = fit_region(feed_e, prod, cal, ppri, ave, share, m_, s_)
        if not ok:
            raise SystemExit(f"{r}: feed needs not balanced after {n} solves (CAPRI aborts here too)")
        fede_q = feed_e
        fede_p = sum(q * arm.get(p, 0.0) for p, q in feed.items()) / fede_q
        reg_rows.append((r, rm, repr(fede_q), repr(fede_p), repr(ave), repr(share), n))
        for k, c in conv.items():
            conv_rows.append((r, k, repr(prod[k]), repr(c), repr(c * cal[k]), repr(m_[k]), repr(up[k]),
                              int(abs(c - up[k]) <= 1e-12 * max(1.0, up[k]))))
    with open(OUT / "feed_cal_content.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["product", "kcal_per_kg"])
        w.writerows((k, repr(v)) for k, v in sorted(cal.items()))
    with open(OUT / "noneu_feed_energy.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["rms", "rm", "fede_kcal", "fede_price", "ave_feed_cost", "feed_cost_share", "solves"])
        w.writerows(reg_rows)
    with open(OUT / "noneu_feed_conv.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["rms", "product", "prod_kt", "conv", "feed_conv", "expected", "upper", "binding"])
        w.writerows(conv_rows)
    raised = [r[0] for r in reg_rows if r[6] > 1]
    print(f"feed_cal_content.csv: {len(cal)} products; noneu_feed_energy.csv: {len(reg_rows)} regions "
          f"(share raised in {len(raised)}: {raised}); noneu_feed_conv.csv: {len(conv_rows)} factors")


if __name__ == "__main__":
    main()
