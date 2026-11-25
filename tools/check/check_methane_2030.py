"""The 2030 methane per head of a country's activities at the simulation's start, from the port (capri_mod/environmental/
methane_per_head.py) on the ported feed chain (capri_mod/feed/chain.py: CAPREG's base year and CAPRI's trends), against
CAPRI's 2030 reference results (tools/lib/paths.BASELINE_REF), as a check only.

At "Y" of the start, as capmod's gascoeff, digestibility and gases run there (capmod.gms l. 778, 1106, 1139): the
year's data of create_sim_ini_gdx.gms (the rations DATA(RU, MAACT, FEED, "Y") at "TRD", l. 311), the start's
requirements and days (the requirement call after def_requirements and adjust), the technologies' shares, MITERRA's
shares and CH4 losses of its 2020 scenario year (create_sim_ini_gdx.gms l. 176-178), %ghgAbatement% off (the
reference run's: the ammonia techniques' factor on CH4MAN) and %CH4ENTfromFEED% on. CAPRI's reference reports its
values at the solution (reports/sol_simy.gms l. 1669-1716), with the solution's rations: the two differ by the rations,
the tier 1 values and the per-head factors not at all.

    python tools/check/check_methane_2030.py [CC ...]       (default DK)
"""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "lib")]

from capri_mod.environmental import methane_per_head as mph  # noqa: E402
from capri_mod.feed import chain  # noqa: E402

ITEMS = ("CH4ENT", "CH4ENTstd", "CH4MAN")


def chain_methane(cc: str, raw=None) -> tuple:
    """(the chain's result, {(RU, MAACT): {CH4ENT, CH4ENTstd, CH4MAN}}, {(RU, MAACT, A): per head}) of the country's
    2030 start."""
    import feed_chain_inputs as fci
    import methane_inputs as mi
    res = chain.feed_chain(fci.chain_inputs(cc, raw=raw))
    ms = next(r for r in res.regions if r in res.S.MS)
    DATA = mi.data_at(res.D, res.regions)
    m = mi.methane_inputs(DATA, res.regions, ms, res.st.p_technFact, res.st, scen_year=2020)
    per_head = mph.methane_per_head(copy.deepcopy(m))
    return res, mph.data_per_activity(m, per_head), per_head


def capri_2030(regions: set) -> dict:
    """CAPRI's 2030 reference results {(region, activity): {item: value}} of the methane items."""
    from _grep import grep
    from paths import BASELINE_REF
    alt = "|".join(sorted(regions))
    txt = grep(rf"^'({alt})'\.''\.'[A-Z0-9]+'\.'({'|'.join(ITEMS)})'\.'2030'", str(BASELINE_REF))
    pat = re.compile(r"^'([A-Z0-9]+)'\.''\.'([A-Z0-9]+)'\.'([A-Za-z0-9]+)'\.'2030'\s+(\S+?),?\s*$")
    out = {}
    for line in txt.splitlines():
        mt = pat.match(line.strip())
        if mt:
            v = 0.0 if mt.group(4).lower() == "eps" else float(mt.group(4))
            out.setdefault((mt.group(1), mt.group(2)), {})[mt.group(3)] = v
    return out


def main() -> None:
    for cc in sys.argv[1:] or ["DK"]:
        res, mine, per_head = chain_methane(cc)
        ref = capri_2030(res.regions)
        rows = []
        for (ru, act), rec in sorted(mine.items()):
            for it in ITEMS:
                r = ref.get((ru, act), {}).get(it, 0.0)
                if rec.get(it) or r:
                    rows.append((ru, act, it, rec.get(it, 0.0), r))
        rel = [abs(a - b) / abs(b) for *_, a, b in rows if b]
        print(f"{cc}: {len(rows)} rows (kg CH4 per head, the start against CAPRI's 2030 solution); "
              f"{sum(r < 1e-6 for r in rel)} of {len(rel)} within 1e-6, {sum(r < 0.01 for r in rel)} within 1%, "
              f"{sum(r < 0.05 for r in rel)} within 5%, largest {max(rel):.3f}")
        for ru, act, it, a, b in rows:
            print(f"  {ru} {act:5s} {it:9s} {a:11.4f} {b:11.4f} {((a - b) / b if b else float('nan')):+9.4f}")


if __name__ == "__main__":
    main()
