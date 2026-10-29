"""Mini-EU regression run: the 2030 Farm-to-Fork run (tools/run/run_f2f_2030.py) on 20 CAPRI units that cover the
model's structures, as a fast check between full reference runs (task 239, agreed 27 October 2026).

A subset run is its own small market: the EU's supply is these units' (K83), so its prices are not the full run's.
The check is therefore against an earlier mini-EU run of the same code path, not against the full run: the same
code and data must give the same result (to the regional solver's tolerance), and a change shows where it acts.

    python tools/run/run_mini_eu.py OUT.pkl [--scenario f2f|greendeal2030] [--reference REF.pkl]

With --reference, the indicators of tools/check/compare_runs.py are printed for both runs, with the largest
regional activity differences.
"""
from __future__ import annotations

import argparse
import os
import pickle
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: unit: what it covers
UNITS = {
    "DE110000": "the default test unit (Stuttgart): mixed farming",
    "FR240000": "arable (Centre)",
    "ES610000": "Mediterranean, olives, irrigation (Andalucia)",
    "IT400000": "intensive arable and livestock, CAPRI's 2006 code (Emilia-Romagna, ITH5)",
    "EL140000": "cotton and durum wheat (Thessaly)",
    "PT180000": "extensive grazing, permanent crops (Alentejo; NUTS 2024 boundary change)",
    "NL220000": "intensive livestock (Gelderland)",
    "NL320000": "the tiered N target falls back to JRC121368's relaxed one (K22)",
    "BL210000": "pigs and dairy (Antwerpen; Belgium and Luxembourg are one CAPRI member state)",
    "IR010000": "grassland cattle (Ireland: two CAPRI units over three NUTS-2016 regions)",
    "DK000000": "a member state without regional detail",
    "HR000000": "the same, mineral fertiliser cap relaxed (ROOF)",
    "PL120000": "eastern arable, rye and oats (Mazowieckie: CAPRI unit of PL91 + PL92)",
    "DED00000": "a CAPRI unit NUTS later split (Saxony)",
    "BG020000": "mineral fertiliser cap relaxed (PERM)",
    "HU220000": "duals relaxed",
    "RO040000": "small-scale eastern mixed (Sud-Vest Oltenia, CAPRI's 2006 code)",
    "AT330000": "mountain grassland (Tyrol)",
    "FI190000": "northern arable and dairy (Laensi-Suomi)",
    "NO080000": "Norway's own market (NOR)",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--scenario", default="f2f")
    ap.add_argument("--reference", default="")
    a = ap.parse_args()
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    cmd = [sys.executable, str(ROOT / "tools" / "run" / "run_f2f_2030.py"), a.out, "--scenario", a.scenario,
           "--regions", ",".join(UNITS)]
    r = subprocess.run(cmd, cwd=ROOT, env=env)
    if r.returncode:
        sys.exit(r.returncode)
    if a.reference:
        subprocess.run([sys.executable, str(ROOT / "tools" / "check" / "compare_runs.py"), a.reference, a.out],
                       cwd=ROOT, env=env)
        ref, new = (pickle.load(open(f, "rb")) for f in (a.reference, a.out))
        diffs = []
        for i, key in enumerate(("baseline", "scenario")):
            for reg, acts in new["act_regional"][i].items():
                for act, v in acts.items():
                    v0 = ref["act_regional"][i].get(reg, {}).get(act)
                    if v0 is not None and abs(v - v0) > 1e-9 * max(1.0, abs(v0)):
                        diffs.append((abs(v - v0) / max(1e-9, abs(v0)), key, reg, act, v0, v))
        diffs.sort(reverse=True)
        print(f"regional activity levels differing (rel > 1e-9): {len(diffs)}")
        for d in diffs[:15]:
            print(f"  {d[1]} {d[2]} {d[3]}: {d[4]:.6g} -> {d[5]:.6g} ({d[0]:.2e})")


if __name__ == "__main__":
    main()
