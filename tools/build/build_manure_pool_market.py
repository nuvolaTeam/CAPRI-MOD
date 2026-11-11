"""The terms of CAPRI's manure pool market (manuremarket/m_mPoolMarket) per region and nutrient, from CAPRI's fertiliser
distribution results of its 2030 Green Deal baseline (priFertDist_<MS>1730defaulta.gdx, results/fert; the raw dataset
nuvolaTeam/capri-mod-raw, capri/results/fert/priFertDist_<MS>1730defaulta/, as Parquet).

Per CAPRI region r and FOUT (MANN, MANP, MANK; sets.gms FOUT_T_N: NITF, PHOF, POTF), as CAPRI computes them
(manuremarket/declare_manure_market.gms l. 466-505):
  supply_t        sum over the fertiliser groups of p_priFertDist(r, "postMode", "EXCR", FNUT, NGRP, 2030): the manure
                  nutrient distributed to the crops, t (v_fertDist is in t, supply_model.gms fertDistExcr_)
  dual_cal_eur_t  p_dualValueManureCal(r, FOUT): ManureNPK_.M at the calibration point, EUR (CAPRI's 2030 money) per t
  slope_capri     p_mPoolSupSlope = p_manPointSupElas x supply_t / dual_cal_eur_t, p_manPointSupElas = 0.01 (l. 496):
                  CAPRI's number, used by CAPRI with the excess supply in kt (v_netPutQuant, v_manureExports: 1000 t,
                  supply_model.gms e_netMTrade) and prices in EUR per t - so its excess supply responds 1000 times more
                  than the elasticity 0.01 written (supply in t, quantities in kt; docs/design/MANURE_POOL_PORT.md)
  es_slope        slope_capri in the model's units: excess supply in t per EUR 1000 (the model's 2017 money) per t,
                  slope_capri x 1000 (kt to t) x 1000 (EUR to EUR 1000) x deflator(2030) (tools/lib/_money.py, K108)
  dual_cal        dual_cal_eur_t in the model's units, EUR 1000 (2017 money) per t: the market model's fall-back value
CAPRI's trade cost terms (p_manureSellCost*, p_manureBuyCost*) are the supply model's (the regional NLP's own here,
capri_mod/supply/land.py) and are not taken from these files; nor are the fixed exports to third countries
(p_manureExportsToThirdCountries, l. 142): the model clears the deviations from CAPRI's base trade, which holds them
(and the files give none by region, only EU totals of 2010-2018).

The rows the builder needs are kept in capri_data/sources/raw/capri/results/fert/manure_pool_inputs_2030.parquet, so
it rebuilds without the raw files.

    python tools/build/build_manure_pool_market.py [--parquet DIR | --download]
        DIR: a copy of the raw dataset's capri/ folder; --download: from the raw dataset (Hugging Face);
        neither: from the kept extract
Output: capri_data/baselines/capri_greendeal_ref/1730/environment/manure_pool_market_2030.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import BASELINE_DATA  # noqa: E402
from _sources_io import read_source, write_source  # noqa: E402  (capri_data/sources: Parquet)
import _money  # noqa: E402

OUT = BASELINE_DATA / "environment" / "manure_pool_market_2030.csv"
KEEP = ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "fert" / "manure_pool_inputs_2030.parquet"
#: manuremarket/declare_manure_market.gms l. 496
POINT_SUP_ELAS = 0.01
#: kt to t and EUR to EUR 1000: CAPRI's pool quantities in kt, prices in EUR per t; the model's in t and EUR 1000 per t
KT_TO_T = 1000.0
EUR_TO_KEUR = 1000.0
#: sets.gms FOUT_T_N
FOUT_T_N = {"MANN": "NITF", "MANP": "PHOF", "MANK": "POTF"}
SIMY = "2030"
SYMBOLS = ["p_priFertDist", "p_dualValueManureCal"]
REPO = "nuvolaTeam/capri-mod-raw"


def _folders(parquet: Path | None, download: bool):
    if parquet is not None:
        return sorted((parquet / "results" / "fert").glob("priFertDist_*1730defaulta"))
    if not download:
        return []
    from huggingface_hub import snapshot_download
    p = snapshot_download(REPO, repo_type="dataset",
                          allow_patterns=[f"capri/results/fert/priFertDist_*1730defaulta/{s}.parquet" for s in SYMBOLS])
    return sorted((Path(p) / "capri" / "results" / "fert").glob("priFertDist_*1730defaulta"))


def _extract(folders) -> pd.DataFrame:
    """CAPRI's records the builder uses, one row per region, FOUT and item (supply_t, dual_cal_eur_t)."""
    rows = []
    for f in folders:
        pf = pd.read_parquet(f / "p_priFertDist.parquet")
        pf = pf[(pf.d2.str.lower() == "postmode") & (pf.d3.str.upper() == "EXCR") & (pf.d6 == SIMY)]
        sup = pf.groupby(["d1", "d4"]).value.sum()
        du = pd.read_parquet(f / "p_dualValueManureCal.parquet")
        for r, fo, v in zip(du.d1, du.d2, du.value):
            rows.append([r, fo, "dual_cal_eur_t", float(v)])
            rows.append([r, fo, "supply_t", float(sup.get((r, FOUT_T_N[fo]), 0.0))])
    return pd.DataFrame(rows, columns=["capri_region", "fout", "item", "value"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", type=Path, default=None)
    ap.add_argument("--download", action="store_true")
    a = ap.parse_args()
    folders = _folders(a.parquet, a.download)
    if folders:
        ex = _extract(folders)
        KEEP.parent.mkdir(parents=True, exist_ok=True)
        write_source(ex, KEEP, index=False)
        print(f"extracted {len(ex)} rows from {len(folders)} files -> {KEEP.relative_to(ROOT)}")
    src = read_source(KEEP)
    v = {(r, fo, it): float(x) for r, fo, it, x in zip(src.capri_region, src.fout, src["item"], src.value)}
    money = _money.deflator(int(SIMY))
    rows = []
    for (r, fo, it) in sorted(k for k in v if k[2] == "dual_cal_eur_t"):
        d_ = v[(r, fo, it)]
        if not d_:
            # CAPRI aborts on a zero calibration dual (declare_manure_market.gms l. 501-505)
            raise SystemExit(f"{r} {fo}: zero calibration dual, CAPRI's slope undefined")
        s_ = v.get((r, fo, "supply_t"), 0.0)
        b = POINT_SUP_ELAS * s_ / d_
        rows.append([r, fo, s_, d_, b, b * KT_TO_T * EUR_TO_KEUR * money, d_ / EUR_TO_KEUR / money])
    if not rows:
        raise SystemExit("no records")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["region", "fout", "supply_t", "dual_cal_eur_t", "slope_capri", "es_slope", "dual_cal"])
        w.writerows(rows)
    print(f"{OUT.relative_to(ROOT)}: {len(rows)} records (deflator {money:.6f})")


if __name__ == "__main__":
    main()
