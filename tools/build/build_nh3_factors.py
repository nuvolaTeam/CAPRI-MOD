"""Build CAPRI's ammonia emission factors per model region (replaces the proxy).

From CAPRI's 2030 reference run (dataOut, res_2_1730greendeal_refdefaulta):
  * per animal: GNH3 (kg NH3-N per head: housing + storage + application +
    grazing) over MANN (kg N excreted per head), aggregated to model animals
    weighted by excreted N (LEVL x MANN) -> share of excreted N lost as NH3-N;
  * per region: NH3MIN / MINFER -> share of mineral N lost as NH3-N.
Regions without regional rows use the national (CC000000) factors.

    python tools/build/build_nh3_factors.py --rows nh3_rows.txt
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from build_livestock_output_coef import CAPRI_TO_MODEL  # noqa: E402


def _read_csv(*a, **k):
    """pandas.read_csv with floats parsed to the last digit (KNOWN_ISSUES K82)."""
    import pandas as pd
    k.setdefault("float_precision", "round_trip")
    return pd.read_csv(*a, **k)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=Path, default=Path("/home/claude/work/nh3/nh3_rows.txt"))
    args = ap.parse_args()
    import pandas as pd
    areas = _read_csv(_ROOT / "capri_data" / "2017" / "supply" / "base_areas.csv", index_col=0)
    corr = json.loads((_ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]
    pat = re.compile(r"^'([A-Z]{2}[0-9A-Z]{6})'\.''\.'([A-Z0-9]+)'\.'([A-Za-z0-9]+)'\.'2030'\s+(-?\d[\d.Ee+\-]*)")
    v = defaultdict(dict)
    for line in open(args.rows, errors="ignore"):
        m = pat.match(line)
        if m:
            v[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))

    def factors(codes):
        """factors over one CAPRI region or a group of them (splits and merges), N-weighted"""
        codes = [codes] if isinstance(codes, str) else list(codes)
        num, den = defaultdict(float), defaultdict(float)
        mf = mn = 0.0; tot = None
        for code in codes:
            d = v.get(code, {})
            for (act, item), val in d.items():
                if item == "GNH3" and act in CAPRI_TO_MODEL:
                    lev, mann = d.get((act, "LEVL"), 0.0), d.get((act, "MANN"), 0.0)
                    if lev > 0 and mann > 0:
                        num[CAPRI_TO_MODEL[act]] += lev * val
                        den[CAPRI_TO_MODEL[act]] += lev * mann
            mf += d.get(("MINFER", "NITF"), 0.0); mn += d.get(("NH3MIN", "NITF"), 0.0)
            if d.get(("NH3TOT", "NITF")) is not None:
                tot = (tot or 0.0) + d.get(("NH3TOT", "NITF"))
        man = {a: num[a] / den[a] for a in num if den[a] > 0}
        return man, (mn / mf if mf > 0 else None), tot

    # CAPRI regions per model region through the shared groups (splits, merges, renamed regions)
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location("_mr", _ROOT / "tools" / "lib" / "_model_regions.py")
    _mr = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_mr)
    c2g, groups = _mr.capri_groups(list(areas.index))
    reg_codes = {r: sorted(c for c in cs if c in v) for cs, rs in groups.values() for r in rs}
    out, src = {}, defaultdict(int)
    for reg in areas.index:
        c8 = reg_codes.get(reg) or None
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
