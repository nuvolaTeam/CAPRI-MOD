"""Where a region's nitrogen-surplus cut comes from, in a saved 2030 Farm-to-Fork run.

For each region: the nitrogen price, area in use, herds, and the change of each balance item
between baseline and scenario (kt N): mineral, organic (manure net of trade), fixation, deposition,
crop uptake (removal), surplus. A cut met by idling land shows as falling uptake and deposition
alongside falling inputs; a cut met on held land keeps uptake.

    python tools/diag_region_balance.py RUN.pkl [FRH0,DE94,...] [RUN2.pkl]
"""
import pickle
import sys

import pandas as pd

ITEMS = ["n_mineral_input", "n_organic_input", "n_fixation", "n_deposition", "n_crop_uptake", "n_surplus"]
SHORT = ["mineral", "manure", "fixation", "deposition", "uptake", "surplus"]
ANIMALS = ["DCOW", "BCOW", "BULL", "PIGS", "PIGF", "LAYS", "BROI", "SHGP"]


def rows(path, regions):
    r = pickle.load(open(path, "rb"))
    eb, es = r["environmental"]
    ab, as_ = r["act_regional"]
    lam = {k: v.get("lam") for k, v in r["regional"].items()}
    out = []
    for reg in regions:
        if reg not in eb.index:
            continue
        d = {"region": reg, "lambda": lam.get(reg)}
        d["uaa"] = f"{eb.at[reg, 'uaa_total']:.0f}->{es.at[reg, 'uaa_total']:.0f}"
        for it, sh in zip(ITEMS, SHORT):
            d[sh] = round((es.at[reg, it] - eb.at[reg, it]) / 1000.0, 1)
        d["surplus base"] = round(eb.at[reg, "n_surplus"] / 1000.0, 1)
        for a in ANIMALS:
            b0, b1 = ab.get(reg, {}).get(a, 0.0), as_.get(reg, {}).get(a, 0.0)
            if b0 > 1e-6:
                d[a] = f"{100 * (b1 / b0 - 1):+.0f}%"
        out.append(d)
    return pd.DataFrame(out).set_index("region")


if __name__ == "__main__":
    regs = (sys.argv[2] if len(sys.argv) > 2 else "FRH0,DE94,DEA3,ITC4,DK03,NL41,BE25").split(",")
    pd.set_option("display.width", 250)
    for p in [sys.argv[1]] + sys.argv[3:]:
        print(p)
        print(rows(p, regs).to_string())
