"""CAPRI's 2030 market of its Green Deal step and of its reference, for the market-only check
(tools/check/check_market_gd.py): the market regions' balances and prices, and the member states' production and feed
bulks the market takes from the supply models.

The same two capmod result files as tools/build/extract_capri_gd_pair.py (docs/EXTERNAL_SOURCES.md):
res_2_1730greendeal_refdefaulta.gdx (the reference) and
res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00defaultA.gdx (the project lead's Green Deal run).

Kept, year 2030, dataOut(region, "", item, product), under the model's commodity codes (build_bilateral_market.MODEL:
SWHE <- WHEA, CORN <- MAIZ, POUL <- POUM, SUGR <- SUGA, BUTR <- BUTT, SKIM <- SMIP, WHEY <- WHEP, PARI <- RICE,
OLIV <- OLIO, WINE <- TWIN, the rest by name; raw milk MILK):
  - the model's 45 market regions (bilateral_regions_2030.csv; CAPRI's A_EU_WEST and A_EU_EAST under the model's
    EU_WEST and EU_EAST): PROD, PMRK, HCON, FEDM, IMPT, EXPT, DOMM, PRCM, INDM, BIOF, LOSM, SEDM;
  - the member states and other countries with supply models (codes ending in 000000): PROD (raw milk delivered under
    MILK) and FEDM of the feed bulks FCER, FPRO, FENE, FOTH, FMIL;
  - raw milk's producer price PPRI (market regions and countries): CAPRI's PMRK of MILK is a constant of its market
    data (unchanged in the scenario; raw milk is not traded), its milk price is PPRI.

Output: capri_data/validation/greendeal_2030/capri_gd_market_2030.csv.xz (region, item, commodity, ref, scen)

    python tools/build/extract_capri_gd_market.py [REF.gdx SCEN.gdx] [--lib-dir DIR]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(ROOT / "tools" / "build"))
from paths import EXPORTS, SOURCES  # noqa: E402
from build_bilateral_market import MODEL  # noqa: E402

REF = EXPORTS / "res_2_1730greendeal_refdefaulta.gdx"
SCEN = EXPORTS / "res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00defaultA.gdx"
OUT = ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_gd_market_2030.csv.xz"
REGIONS = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "market" / "bilateral_regions_2030.csv"
EU_BLOCKS = {"A_EU_WEST": "EU_WEST", "A_EU_EAST": "EU_EAST"}
MARKET_ITEMS = ("PROD", "PMRK", "HCON", "FEDM", "IMPT", "EXPT", "DOMM", "PRCM", "INDM", "BIOF", "LOSM", "SEDM")
BULKS = ("FCER", "FPRO", "FENE", "FOTH", "FMIL")


def read_gdx(path, lib, regions, to_model):
    from gams.core import gdx
    h = gdx.new_gdxHandle_tp()
    ok, msg = gdx.gdxCreateD(h, lib, gdx.GMS_SSSIZE)
    if not ok:
        raise SystemExit(msg)
    gdx.gdxOpenRead(h, str(path))
    _, idx = gdx.gdxFindSymbol(h, "dataOut")
    _, nrec = gdx.gdxDataReadStrStart(h, idx)
    out = {}
    for _ in range(nrec):
        ok, k, v, _ = gdx.gdxDataReadStr(h)
        if not ok:
            break
        if k[4] != "2030" or k[1] != "":
            continue
        val = float(v[gdx.GMS_VAL_LEVEL])
        ms = k[0].endswith("000000") and len(k[0]) == 8
        if ms and k[2] == "FEDM" and k[3] in BULKS:
            out[(k[0], "FEDM", k[3])] = val
        if ms and k[2] == "PROD" and k[3] in to_model:
            out[(k[0], "PROD", to_model[k[3]])] = val
        r = EU_BLOCKS.get(k[0], k[0])
        if k[3] == "MILK" and k[2] == "PPRI" and (k[0] in EU_BLOCKS or r in regions or ms):
            out[(r, "PPRI", "MILK")] = val
        if (k[0] in EU_BLOCKS or (r in regions and r not in EU_BLOCKS.values())) and k[2] in MARKET_ITEMS \
                and k[3] in to_model:
            out[(r, k[2], to_model[k[3]])] = val
    gdx.gdxDataReadDone(h); gdx.gdxClose(h)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref_gdx", type=Path, nargs="?", default=REF)
    ap.add_argument("scen_gdx", type=Path, nargs="?", default=SCEN)
    ap.add_argument("--lib-dir", default=os.environ.get("CAPRI_GDXLIB", str(SOURCES / "gdxlib")))
    a = ap.parse_args()
    regions = set(pd.read_csv(REGIONS, float_precision="round_trip")["region"])
    to_model = {capri[0]: m for m, capri in MODEL.items() if len(capri) == 1}
    to_model["MILK"] = "MILK"
    ref = read_gdx(a.ref_gdx, a.lib_dir, regions, to_model)
    scen = read_gdx(a.scen_gdx, a.lib_dir, regions, to_model)
    keys = sorted(set(ref) | set(scen))
    df = pd.DataFrame([(r, it, c, ref.get((r, it, c)), scen.get((r, it, c))) for (r, it, c) in keys],
                      columns=["region", "item", "commodity", "ref", "scen"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(df)} rows; items {df['item'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
