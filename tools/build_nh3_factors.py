"""Build CAPRI's ammonia emission factors per model region (replaces the proxy).

From CAPRI's 2030 reference run (dataOut, res_2_1730greendeal_refdefaulta):
  * per animal: GNH3 (kg NH3-N per head: housing + storage + application +
    grazing) over MANN (kg N excreted per head), aggregated to model animals
    weighted by excreted N (LEVL x MANN) -> share of excreted N lost as NH3-N;
  * per region: NH3MIN / MINFER -> share of mineral N lost as NH3-N.
Regions without regional rows use the national (CC000000) factors.

    python tools/build_nh3_factors.py --rows nh3_rows.txt
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "tools"))
from build_livestock_output_coef import CAPRI_TO_MODEL  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=Path, default=Path("/home/claude/work/nh3/nh3_rows.txt"))
    args = ap.parse_args()
    import pandas as pd
    areas = pd.read_csv(_ROOT / "capri_data" / "2017" / "supply" / "base_areas.csv", index_col=0)
    corr = json.loads((_ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]
    pat = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'([A-Z0-9]+)'\.'([A-Za-z0-9]+)'\.'2030'\s+(-?\d[\d.Ee+\-]*)")
    v = defaultdict(dict)
    for line in open(args.rows, errors="ignore"):
        m = pat.match(line)
        if m:
            v[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))

    def factors(code):
        d = v.get(code, {})
        num, den = defaultdict(float), defaultdict(float)
        for (act, item), val in d.items():
            if item == "GNH3" and act in CAPRI_TO_MODEL:
                lev, mann = d.get((act, "LEVL"), 0.0), d.get((act, "MANN"), 0.0)
                if lev > 0 and mann > 0:
                    num[CAPRI_TO_MODEL[act]] += lev * val
                    den[CAPRI_TO_MODEL[act]] += lev * mann
        man = {a: num[a] / den[a] for a in num if den[a] > 0}
        mf, mn = d.get(("MINFER", "NITF"), 0.0), d.get(("NH3MIN", "NITF"), 0.0)
        return man, (mn / mf if mf > 0 else None), d.get(("NH3TOT", "NITF"))

    out, src = {}, defaultdict(int)
    for reg in areas.index:
        c8 = next((c for c, lst in corr.items() if reg in lst and not c.endswith("000000") and c in v), None)
        man, mi, tot = factors(c8) if c8 else ({}, None, None)
        nat = factors(reg[:2] + "000000")
        if not man and not nat[0]:
            continue
        rec = {"manure_share": {**nat[0], **man}, "mineral_share": mi if mi is not None else nat[1],
               "source": "regional" if c8 and man else "national", "capri_nh3_total_ktN": tot}
        out[reg] = rec
        src[rec["source"]] += 1
    dest = _ROOT / "capri_data" / "2017" / "environment" / "nh3_factors_capri.json"
    dest.write_text(json.dumps({"_source": "CAPRI res_2_1730greendeal_refdefaulta dataOut: GNH3/MANN per animal (weighted by excreted N), "
                                "NH3MIN/MINFER per region; national rows where regional are missing",
                                "_units": "kg NH3-N per kg N excreted (manure_share) or applied as mineral fertiliser (mineral_share)",
                                "regions": out}, indent=1))
    print(f"wrote {dest}: {len(out)} regions ({dict(src)})")


if __name__ == "__main__":
    main()
