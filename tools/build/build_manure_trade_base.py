"""CAPRI's 2030 manure trade per model region (manureTradeNew; Sprint 9j).

CAPRI's Green Deal reference (star 3.0, `res_2_1730greendeal_refpol_endotech_all_ini`: the 2030 reference with the
endogenous technologies at their calibrated shares, as the model's 2030 baseline) trades manure between regions
through its national pools (supply_model.gms e_netMTrade, e_costMTrade; manuremarket/). Its results carry per
CAPRI region the net manure N trade, MTRADE.NITF (kt N, positive = net export), and the excretion, EXCRET.NITF.

Per group of CAPRI and model regions covering the same territory (tools/lib/_model_regions.capri_groups: one-to-one,
splits, merges, Ireland's several-to-several):
  export_share        = the group's exports / its excretion (CAPRI), applied to each model region's excretion
  import_kg_n_per_ha  = the group's imports / the group's cropland (model base areas), per ha of cropland
so a split region gets its parent's share and rate, and trade between CAPRI regions of one group (Ireland: IR01 to
IR02) stays in the group as gross flows.

Replaces capri_data/2017/environment/manure_trade_2030.csv, which had been written without a builder from
`res_2_1730greendeal_refdefaulta` by CAPRI code: its Romanian and Irish regions (CAPRI's older codes) were missing,
so 155 kt of CAPRI's net trade (Romania 125, Ireland 30) was not in the model's balances.

    python tools/build/build_manure_trade_base.py [--src /mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv]
"""
from __future__ import annotations
import argparse, importlib.util, re, subprocess, sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
KEEP = ROOT / "capri_data" / "sources" / "environment" / "capri_manure_trade_2030.csv"
DEST = ROOT / "capri_data" / "2017" / "environment" / "manure_trade_2030.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path,
                    default=Path("/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv"))
    a = ap.parse_args()
    if a.src.exists():
        txt = subprocess.run(["grep", "-E", r"^'[A-Z0-9]{8}'\.''\.'(MTRADE|EXCRET)'\.'NITF'\.'2030'", str(a.src)],
                             capture_output=True, text=True).stdout
        pat = re.compile(r"^'([A-Z0-9]{8})'\.''\.'(MTRADE|EXCRET)'\.'NITF'\.'2030'\s+([-\d.Ee+]+)")
        rows = [m.groups() for m in map(pat.match, txt.splitlines()) if m]
        KEEP.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows, columns=["capri_region", "item", "kt_n"]).to_csv(KEEP, index=False)
        print(f"extracted {len(rows)} rows -> {KEEP.relative_to(ROOT)}")
    src = pd.read_csv(KEEP)
    v = {(r.capri_region, r.item): float(r.kt_n) for r in src.itertuples()}
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    sys.path.insert(0, str(ROOT))
    from capri_mod.data.loaders import load_all_data
    from capri_mod.data.definitions import CROPS
    d = load_all_data(str(ROOT / "capri_data"))
    A = d["areas"]
    regs = list(A.index)
    code_to_group, groups = mr.capri_groups(regs)
    out = {}
    for g, (codes, mregs) in groups.items():
        ex = sum(max(0.0, v.get((c, "MTRADE"), 0.0)) for c in codes)
        im = sum(max(0.0, -v.get((c, "MTRADE"), 0.0)) for c in codes)
        exc = sum(v.get((c, "EXCRET"), 0.0) for c in codes)
        crop = sum(float(A.loc[r, [c for c in A.columns if c in CROPS]].sum()) for r in mregs if r in A.index)
        sh = ex / exc if exc > 0 else 0.0
        kg = im * 1e6 / (crop * 1000.0) if crop > 0 else 0.0           # kt -> kg over 1000 ha -> kg/ha
        for r in mregs:
            out[r] = (sh, kg, "+".join(sorted(codes)))
    rows = [dict(region=r, export_share=round(out.get(r, (0.0, 0.0, ""))[0], 6),
                 import_kg_n_per_ha=round(out.get(r, (0.0, 0.0, ""))[1], 4),
                 source="CAPRI 2030 reference endotech_all_ini MTRADE/EXCRET " + out.get(r, (0, 0, "none"))[2])
            for r in regs]
    old = pd.read_csv(DEST).set_index("region") if DEST.exists() else None
    new = pd.DataFrame(rows)
    new.to_csv(DEST, index=False)
    if old is not None:
        j = new.set_index("region").join(old, rsuffix="_old")
        dif = j[(abs(j.export_share - j.export_share_old) > 0.01) | (abs(j.import_kg_n_per_ha - j.import_kg_n_per_ha_old) > 2)]
        print(f"wrote {DEST.relative_to(ROOT)}: {len(new)} regions; changed by > 1 point / 2 kg: {len(dif)}")
        print(dif[["export_share", "export_share_old", "import_kg_n_per_ha", "import_kg_n_per_ha_old"]].round(3).to_string())
    print(f"CAPRI EU net trade sum (regional rows): exports {sum(max(0, x) for (c, i), x in v.items() if i == 'MTRADE' and not c.endswith('000000')):.0f} kt")


if __name__ == "__main__":
    main()
