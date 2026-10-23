"""Model region -> CAPRI region map, for the model's runtime lookups of CAPRI regional tables.

Written from tools/lib/_model_regions.py (the NUTS correspondence with its fixes, plus NUTS splits
and merges), so the runtime and the data builders use one mapping:

  region         model region (NUTS 2016/2021)
  capri_region   the CAPRI region whose per-unit values the region takes (a split part: its
                 parent; a merged region: the first parent, REGISTERED)
  capri_group    every CAPRI region of the group covering the same territory ('+'-joined)
  relation       one-to-one, split, merge, or none (the region takes national values)

Output: capri_data/shared/region_capri_map.csv
    python tools/build/build_region_map.py
"""
from pathlib import Path
import importlib.util, csv

ROOT = Path(__file__).resolve().parents[2]


def main():
    spec = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
    regs = mr.model_regions()
    one = mr.region_to_capri()
    c2g, groups = mr.capri_groups(regs)
    grp = {r: (sorted(cs), sorted(rs)) for cs, rs in groups.values() for r in rs}
    dest = ROOT / "capri_data" / "shared" / "region_capri_map.csv"
    n = {}
    with open(dest, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["region", "capri_region", "capri_group", "relation"])
        for r in regs:
            cs, rs = grp.get(r, ([], []))
            rel = ("none" if not cs else "one-to-one" if len(cs) == 1 and len(rs) == 1
                   else "merge" if len(rs) == 1 else "split")
            n[rel] = n.get(rel, 0) + 1
            w.writerow([r, one.get(r, "") if cs else "", "+".join(cs), rel])
    print(f"wrote {dest.name}: {len(regs)} regions {n}")


if __name__ == "__main__":
    main()
