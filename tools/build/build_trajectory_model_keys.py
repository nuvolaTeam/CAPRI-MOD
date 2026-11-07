"""Key CAPRI's trend projection (capri_data/scenarios/captrd_2030) by the model's own activity and region names.

The trajectory carries CAPRI's codes: activities as CAPRI names them (MAIZ, TWIN, SCOW, BULF, SOWS, HENS, POUF,
SHGT, OFAR ...) and regions as the first four characters of CAPRI's region code (DE11, FR24, BL00 ...). The
projection looks factors up by the MODEL's names (CORN, WINE, BCOW, BULL, PIGS, LAYS, BROI, SHGP, OFOD) and
model regions (NUTS 2021: FRB0, IE04 ...), so every name that differs fell back to the activity default
(maize yield +3.6% instead of CAPRI's +1.8%, bulls' herd 1.0 instead of 0.93) and every recoded region to the
EU median. This adds model-keyed entries next to CAPRI's (which are kept): activity aliases below, regions
through tools/lib/_model_regions.region_to_capri() (the NUTS correspondence with its splits and merges).

Since 29 October 2026 the file is built from blank by tools/build/build_captrd_trajectory.py, which calls
add_model_keys; the command line below edits a file in place (as before) and is not part of the data pipeline.

    python tools/build/build_trajectory_model_keys.py [capri_data/scenarios/captrd_2030]
(a scenario folder, capri_mod/projection/scenario_io.py; a JSON file until 31 October 2026)
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
#: model name -> CAPRI key, per block
ALIASES = {
    "yields": {"CORN": "MAIZ", "WINE": "TWIN", "BCOW": "SCOW", "HFRS": "HEIF", "CALV": "CACR",
               "PIGS": "SOWS", "LAYS": "HENS", "BROI": "POUF", "OFOD": "OFAR", "BULL": "BULF"},
    # the herds block carries CAPRI's activity levels (LEVL), crops included: model crop names too
    "herds": {"BULL": "BULF", "PIGS": "SOWS", "POUL": "POUF", "SCOW": "SCOW", "HEIF": "HEIF",
              "CORN": "MAIZ", "WINE": "TWIN", "OFOD": "OFAR",
              # the model's own animal names (animal_numbers columns) had no herd factor: suckler cows, heifers,
              # laying hens, broilers, calves, sheep and goats stayed at 2017 in the projected data (K12)
              "BCOW": "SCOW", "HFRS": "HEIF", "LAYS": "HENS", "BROI": "POUF", "CALV": "CACR"},
}


#: model names that are CAPRI's names for another item: the alias replaces them, and where the alias has no factor the
#: model name gets none either (the region falls back to the EU factor, itself the alias's), never the other item's.
#: BULL: CAPRI's bulls' raising, the model's bull fattening is BULF. PIGS (KNOWN_ISSUES K119, the project lead's
#: decision of 6 November 2026): CAPRI's "Pigs total" aggregate (PIGF + SOWS + piglets; reports/aggreg_sets.gms l. 101,
#: 132; CAPTRD's aggreg_and_report.gms l. 262-283, a yield mixing tonnes of pork and heads of piglets), the model's
#: PIGS is CAPRI's SOWS (codes/model_activities.csv)
CAPRI_OTHER = ("BULL", "PIGS")


def add_model_keys(t: dict) -> dict:
    """The model's activity and region keys added to a CAPRI-keyed trajectory (in place; returns the counts)."""
    sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
    import _model_regions as mr
    to_c8 = mr.region_to_capri()
    regions = mr.model_regions()
    added = {"growth": 0, "regional": 0, "regions": 0}
    # model names retired since: their keys would otherwise be carried on (CAPRI's own keys, e.g. TEXT, stay)
    RETIRED = {"COTT", "OFIB", "SHGP", "SHGO"}
    dropped = 0
    for block in ("growth", "regional"):
        for k, v in t.get(block, {}).items():
            entries = [v] if block == "growth" else list(v.values())
            for e in entries:
                for m in RETIRED & set(e):
                    del e[m]; dropped += 1
    for block, al in ALIASES.items():
        g = t["growth"].get(block, {})
        for m, c in al.items():
            if c in g and (m not in g or m in CAPRI_OTHER):
                g[m] = dict(g[c]); added["growth"] += 1
            elif m in CAPRI_OTHER and m in g and c not in g:
                del g[m]
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
                # a factor under the model's own name (OFOD = OFAR + ROOF, build_trajectory_capri_ref.py) is kept;
                # a model name that is CAPRI's name for another item (CAPRI_OTHER) takes the alias or nothing
                if c in src and (m not in src or m in CAPRI_OTHER):
                    entry[m] = dict(src[c])
                elif m in CAPRI_OTHER and m in entry and c not in src:
                    del entry[m]
            if r not in reg:
                added["regions"] += 1
            reg[r] = entry
            added["regional"] += 1
    t.setdefault("_provenance", {})["model_keys"] = (
        "model activity aliases and model regions added by tools/build/build_trajectory_model_keys.py "
        "(CAPRI-keyed entries kept)")
    added["retired_dropped"] = dropped
    return added


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "capri_data" / "scenarios" / "captrd_2030"
    sys.path.insert(0, str(ROOT))
    from capri_mod.projection import scenario_io
    t = scenario_io.read(path)
    added = add_model_keys(t)
    scenario_io.write(path, t)
    print(f"{path.resolve().relative_to(ROOT)}: {added}")

if __name__ == "__main__":
    main()
