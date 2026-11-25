"""The 2030 methane per head of a country's activities, from the port (capri_mod/environmental/methane_per_head.py) on
the ported feed chain (capri_mod/feed/chain.py: CAPREG's base year and CAPRI's trends), as CAPRI's report at the
solution computes it, against CAPRI's 2030 reference results (tools/lib/paths.BASELINE_REF), as a check only.

CAPRI's report (reports/sol_simy.gms l. 254-257 and 1627 on) runs gascoeff, digestibility and gases on the solution's
rations, the feed input coefficients over the technologies' levels; the calibrated reference reproduces the start's
coefficients (tools/build/build_ration_trajectory_2030.py), so the check takes them (tools/lib/methane_inputs.
with_report_rations). The year's data at "Y" carry the trend rations instead (create_sim_ini_gdx.gms l. 311: in
Alentejo's dairy cows 9.3 t of grass per head against the coefficients' 27.1 t), which CAPRI's supply model's methane
rests on with %ghgAbatement% on (envind/gases.gms l. 400-403). The rest at "Y" of the start: the requirements and days
(the requirement call after def_requirements and adjust), the technologies' shares, MITERRA's shares and CH4 losses of
its 2020 scenario year (create_sim_ini_gdx.gms l. 176-178), %ghgAbatement% off (the reference run's: the ammonia
techniques' factor on CH4MAN) and %CH4ENTfromFEED% on. The products' mix within each feed bulk stays the start's (the
report's comes from the solution's feed use).

Result (25 November 2026): the tier 1 values (pigs, poultry, sheep and goats) equal CAPRI's; Denmark's 50 values within
1.7% (40 within 1%), Portugal's 347 within 9.3% (329 within 5%; the largest the cattle's CH4MAN in PT16, -8 to -9%),
Norway's 299 within 0.05%. Norway's poultry with CAPRI's Norwegian MITERRA data of the project lead's installation
(tools/build/extract_capri_dat.py): the dat mirror's had no low-emission housing share of 2020 for hens and other
poultry (no CH4 loss: 18 times CAPRI's CH4MAN for the other poultry).

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
    from capri_mod.environmental.equations import ammo_ch4
    ci = fci.chain_inputs(cc, raw=raw)
    res = chain.feed_chain(ci)
    ms = next(r for r in res.regions if r in res.S.MS)
    DATA = mi.with_report_rations(mi.data_at(res.D, res.regions), res.a.v_feedInpCoeff_L, res.st.p_maxFeedShare,
                                  res.st.p_technFact)
    m = mi.methane_inputs(DATA, res.regions, ms, res.st.p_technFact, res.st, scen_year=ammo_ch4.ScenYear(ci.SIMY))
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
