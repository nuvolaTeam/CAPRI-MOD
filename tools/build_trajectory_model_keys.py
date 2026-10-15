"""Key CAPRI's trend projection (captrd_2030.json) by the model's own activity and region names.

The trajectory carries CAPRI's codes: activities as CAPRI names them (MAIZ, TWIN, SCOW, BULF, SOWS, HENS, POUF,
SHGT, OFAR ...) and regions as the first four characters of CAPRI's region code (DE11, FR24, BL00 ...). The
projection looks factors up by the MODEL's names (CORN, WINE, BCOW, BULL, PIGS, LAYS, BROI, SHGP, OFOD) and
model regions (NUTS 2021: FRB0, IE04 ...), so every name that differs fell back to the activity default
(maize yield +3.6% instead of CAPRI's +1.8%, bulls' herd 1.0 instead of 0.93) and every recoded region to the
EU median. This adds model-keyed entries next to CAPRI's (which are kept): activity aliases below, regions
through tools/_model_regions.region_to_capri() (the NUTS correspondence with its splits and merges).

    python tools/build_trajectory_model_keys.py [capri_data/trajectories/captrd_2030.json]
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
#: model name -> CAPRI key, per block
ALIASES = {
    "yields": {"CORN": "MAIZ", "WINE": "TWIN", "BCOW": "SCOW", "HFRS": "HEIF", "CALV": "CACR",
               "PIGS": "SOWS", "LAYS": "HENS", "BROI": "POUF", "OFOD": "OFAR", "BULL": "BULF", "COTT": "TEXT",
               "OFIB": "TEXT"},
    # the herds block carries CAPRI's activity levels (LEVL), crops included: model crop names too
    "herds": {"BULL": "BULF", "PIGS": "SOWS", "POUL": "POUF", "SHGO": "SHGM", "SCOW": "SCOW", "HEIF": "HEIF",
              "CORN": "MAIZ", "WINE": "TWIN", "OFOD": "OFAR", "COTT": "TEXT", "OFIB": "TEXT",
              # the model's own animal names (animal_numbers columns) had no herd factor: suckler cows, heifers,
              # laying hens, broilers, calves, sheep and goats stayed at 2017 in the projected data (K12)
              "BCOW": "SCOW", "HFRS": "HEIF", "LAYS": "HENS", "BROI": "POUF", "CALV": "CACR", "SHGP": "SHGT"},
}


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "capri_data" / "trajectories" / "captrd_2030.json"
    t = json.loads(path.read_text())
    sys.path.insert(0, str(ROOT / "tools"))
    import _model_regions as mr
    to_c8 = mr.region_to_capri()
    regions = mr.model_regions()
    added = {"growth": 0, "regional": 0, "regions": 0}
    for block, al in ALIASES.items():
        g = t["growth"].get(block, {})
        for m, c in al.items():
            if c in g and (m not in g or m in ("BULL",)):
                g[m] = dict(g[c]); added["growth"] += 1
    for block in list(t.get("regional", {})):
        reg = t["regional"][block]
        al = ALIASES.get(block, {})
        for r in regions:
            key = to_c8.get(r, mr.national_code(r))[:4]
            src = reg.get(key) or reg.get(mr.national_code(r)[:4])
            if src is None:
                continue
            entry = dict(src)
            for m, c in al.items():
                if c in src:
                    entry[m] = dict(src[c])
            if r not in reg:
                added["regions"] += 1
            reg[r] = entry
            added["regional"] += 1
    t.setdefault("_provenance", {})["model_keys"] = (
        "model activity aliases and model regions added by tools/build_trajectory_model_keys.py "
        "(CAPRI-keyed entries kept)")
    path.write_text(json.dumps(t, indent=1))
    print(f"{path.relative_to(ROOT)}: {added}")


if __name__ == "__main__":
    main()
