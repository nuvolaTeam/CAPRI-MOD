"""CAPRI's active mitigation technologies for the Green Deal runs (activeTech).

Source: pol_input/greendeal/refpol_endotech_all_sup.gms (the reference that
pol_input/greendeal/greendeal_scenarios.gms includes, refScenMain), the $SETGLOBAL lists
ghgTechActiveAmm, ghgTechActiveFert, ghgTechActiveFeed, ghgTechActiveCarb, ghgTechActiveOther.
envind/ghgMiti.gms removes every option outside activeTech from mitiTech_map after calibration,
so only these can be adopted in the Farm-to-Fork run (JRC121368).

Output: capri_data/2017/abatement/active_technologies.csv (group, technology, source)
Usage:  python tools/build/build_active_technologies.py <path to refpol_endotech_all_sup.gms>
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capri_data" / "2017" / "abatement" / "active_technologies.csv"
PAT = re.compile(r"^\$ifi\s+not\s+SETGLOBAL\s+ghgTechActive(\w+)\s+\$SETGLOBAL\s+ghgTechActive\w+\s+(.+)$", re.I)


def main(src):
    rows = []
    for line in open(src, encoding="latin-1"):
        m = PAT.match(line.strip())
        if m:
            for t in m.group(2).split(","):
                if t.strip():
                    rows.append([m.group(1), t.strip(), Path(src).name])
    if not rows:
        raise SystemExit("no ghgTechActive lists found")
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["group", "technology", "source"]); w.writerows(rows)
    print(len(rows), "active technologies written to", OUT.name)


if __name__ == "__main__":
    main(sys.argv[1])
