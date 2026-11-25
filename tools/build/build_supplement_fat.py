"""The fat of the feed bulks per model region and cattle animal with linseed (LINE_Tot), the data of CAPRI's ration fat
limit SupplementPerc_ (supply/supply_model.gms l. 608-633; KNOWN_ISSUES K93).

CAPRI's Green Deal settings switch the feed supplements on (pol_input/greendeal/refpol_endotech_all_sup.gms:
ghgTechLineNitr 1, envind/line_nitr.gms). SupplementPerc_ limits the fat of the ration, its feed bulks' and the linseed's,
to 5% of the dry-matter intake with a heavily penalised slack above; the feed bulks' fat per kg as fed is
p_emisFeed(RU, CATACT, T, FEED, TotFAT) = EE x p_DryMatterContent / 100 (envind/line_nitr.gms l. 175-176), EE the bulk's
ether extract (% of dry matter) as envind/digestibility.gms computes it (l. 31-60 and 200-232: CAPRI's table
p_digestPar("EU", "DCOL", ...), grass by the grazing share and the member state's grass fixation rate, other fodder
with the unit's fodder legume share, the bulks as the member state's feed-use weighted means of their products).
The statements: capri_mod/supply/equations/digestibility.py and line_nitr.py; the steps: tools/lib/_capri_digest.py
feed_ee (shared with 3-NOP's ration fibre and fat).

The data year is CAPRI's simulation's: capmod.gms runs digestibility.gms with "Y" (l. 1106) before line_nitr.gms
(l. 1108), and the simulation's DATA at "Y" is its 2030 calibration point (sim_ini_21730: the baseline's TRD). So the
feed use weights are the member state's FEDM at Y (INTF has no Y entry there: 0, as in CAPRI), the dry-matter contents
the unit's or the member state's DRMA at Y, the legume share the unit's FLEG at Y. (3-NOP's effect takes CAPRI's 2017
regional results instead: tools/build/build_supplement_effects.py.)

Per model region (a CAPRI regional unit) and model animal with a linseed row in supplement_effects.csv, for each feed of
the model's ration (feed_ration_2017.csv): ee, dm_content (p_DryMatterContent) and tot_fat. CAPRI's bulks differ between
activities only through the grazing share GRAZ (GRAS, and OFAR through it), and GRAZ only by the activity's MITERRA
type (envind/ammo.gms l. 604-613; build_ammonia_technologies.graz_share): the activities of each model animal share
theirs (DCOL and DCOH the dairy cows', the other cattle the other cows'), checked here, so the model animal's bulks are its
activities'.

Sources: capri_sources/reference/simini/simini_21730/DATA.csv.gz (CAPRI's simulation data: FEDM, DRMA, FLEG at Y),
capri_data/sources/intermediate/envind/capri_digestpar.parquet and capri_digest_default_prd.parquet (CAPRI's table and
DEF_PRD), fert/fertpar.gms (p_nfixRate_gras), the MITERRA grazing data of build_ammonia_technologies,
capri_data/codes/capri/FEED_TO_O.csv, supplement_effects.csv, feed_ration_2017.csv.

Output: capri_data/2017/abatement/mitigation/supplement_fat.csv
    region, animal, feed, ee, dm_content, tot_fat

    python tools/build/build_supplement_fat.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools" / "lib")); sys.path.insert(0, str(ROOT / "tools" / "build"))
from paths import REFERENCE                                             # noqa: E402  (CAPRI's material outside the repository)
import _capri_digest as G                                               # noqa: E402
import _model_codes as _MC                                              # noqa: E402
from build_ammonia_technologies import graz_share, MITT                 # noqa: E402
from build_capri_crop_n_coefs import simini                             # noqa: E402  (sim_ini_21730's DATA at Y)
from capri_mod.supply.equations.line_nitr import p_emisFeed_TotFAT_FEED  # noqa: E402

M = ROOT / "capri_data" / "2017" / "abatement" / "mitigation"
SUPP = M / "supplement_effects.csv"
RATION = ROOT / "capri_data" / "2017" / "feed" / "feed_ration_2017.csv"
F2O = ROOT / "capri_data" / "codes" / "capri" / "FEED_TO_O.csv"
SIMINI = REFERENCE / "simini" / "simini_21730" / "DATA.csv.gz"
OUT = M / "supplement_fat.csv"


def main(check: bool = False):
    s = pd.read_csv(SUPP)
    pairs = sorted({(r.region, r.animal) for r in s[s.option == "LINE_Tot"].itertuples()})
    from capri_mod.data.nested_tables import read_feed_rations
    rations = read_feed_rations(RATION)
    f2o = [(r["feed"], r["row"]) for r in csv.DictReader(open(F2O))]
    by_ms = defaultdict(list)
    for reg, an in pairs:
        by_ms[reg[:2] + "000000"].append((reg, an))
    D, _ = simini(SIMINI)
    rows = []
    for ms, prs in sorted(by_ms.items()):
        graz_of = {}
        for an in sorted({a for _, a in prs}):
            mem = _MC.ANIMALS[an]
            kinds = {MITT[x][1] for x in mem}
            if len(kinds) != 1:
                raise ValueError(f"{an}: its activities {mem} have different MITERRA types {kinds}")
            graz_of[an] = graz_share(ms, mem[0])
        rus = sorted({reg for reg, _ in prs})
        ee = G.feed_ee(D, ms, rus, f2o, graz_of)
        for reg, an in prs:
            ra = (rations.get(reg) or {}).get(an)
            if not ra:
                continue
            for feed in ra["ration"]:
                e_, dm_ = ee[(reg, an)].get(feed, (0.0, 0.0))
                rows.append({"region": reg, "animal": an, "feed": feed, "ee": e_, "dm_content": dm_,
                             "tot_fat": p_emisFeed_TotFAT_FEED(e_, dm_)})
    out = pd.DataFrame(rows)
    print(f"supplement_fat: {len(out)} rows, {out[['region', 'animal']].drop_duplicates().shape[0]} region-animals")
    print(out.groupby("feed")["ee"].median().round(2).to_string())
    if check:
        old = pd.read_csv(OUT, float_precision="round_trip")
        pd.testing.assert_frame_equal(old, out.astype(old.dtypes.to_dict()), check_exact=False, rtol=1e-12)
        print("unchanged:", OUT.relative_to(ROOT))
        return
    out.to_csv(OUT, index=False)
    print("wrote", OUT.relative_to(ROOT), len(out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    main(ap.parse_args().check)
