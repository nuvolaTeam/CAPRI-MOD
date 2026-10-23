"""CAPRI's minimum shares of ammonia options under the Nitrates Directive (p_envConst, envind/ammo_tech.gms
l. 2398-2670): covered storage (CovStorLow) and low- and high-efficiency manure application (AmmAppLE, AmmAppHE), per
CAPRI region and animal activity.

Data:
  the obligations (sets StorCover, applLe, applHe, ammo_tech.gms l. 2398-2575: region, inside/outside NVZ, manure
    system, slope class, land use), read from CAPRI's code into nitrates_directive_obligations.csv;
  NVZ share of the region (p_nvzShare_lu.csv), areas by NVZ and land use and slope shares (dat/envind/nvz.gdx:
    p_nvzArea, p_slopeTypes; nvz_p_nvzArea.csv, nvz_p_slopeTypes.csv);
  applicability by manure system (costs/p_applic.csv) and the liquid share (n_cascade_factors.csv tsl).

Formulas (l. 2587-2670):
  p_slopePerc(RU, nvz, LU, slope) = p_slopeTypes(RU, nvz, LU, slope) x p_nvzArea(RU, nvz, LU) / sum_LU p_nvzArea(RU, nvz, LU)
  CovStorLow = sum over nvz in/out of (share nvz) x (L x applic_liquid $ obliged(liquid) + (1 - L) x applic_solid
               $ obliged(solid)), the obligation of the region, else of its NUTS1, else of its member state
  AmmAppLE/HE = sum over slope and land use of (share nvz x p_slopePerc) x (L x applic_liquid $ obliged + (1 - L) x
               applic_solid $ obliged), same fallback; Malta's sheep and goats: liquid only (l. 2620)

Output: capri_data/2017/abatement/ammonia/nitrates_directive_min_shares.csv (region, activity, technology, value).
CAPRI raises the initial shares to these minima (l. 2676-2725; p_helpManStor) and uses them in the premium logic
(supply/bounds_miti_adapt.gms) and as lower bounds (ND_ManStor_, ND_ManCov_, ND_AmmAppLE_, ND_AmmAppHE_), all only with
%NDtech% on; CAPRI's settings for its Green Deal runs set NDtech off (pol_input/cap_after_2023/refpol_endotech_all_sup.gms
l. 401), so capri-mod, following those runs, does not apply them (docs/KNOWN_ISSUES.md K51).
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "capri_data" / "2017" / "abatement" / "ammonia"
GAMS = Path("/home/claude/work/allgms/gams/envind/ammo_tech.gms")
APPLIC_CAT = {"DCOL": "dcow", "DCOH": "dcow", "PIGF": "pigs", "SOWS": "pigs", "HENS": "hens", "POUF": "pouf",
              "SHGF": "shgt", "SHGM": "shgt"}


def parse_obligations():
    """The three sets from CAPRI's code -> nitrates_directive_obligations.csv (kept with the data)."""
    out = D / "nitrates_directive_obligations.csv"
    if GAMS.exists():
        txt = GAMS.read_text(errors="replace").split("\n")
        rows = []
        for name in ("StorCover", "applLe", "applHe"):
            i = next(k for k, l in enumerate(txt) if re.match(rf"\s*set\s+{name}\s*\(", l, re.I))
            j = i + 1
            while txt[j].strip() != "/":
                j += 1
            j += 1
            while txt[j].strip() != "/":
                l = txt[j].strip()
                if l and not l.startswith("*"):
                    parts = l.split(".")
                    rows.append([name, parts[0], parts[1].replace("InNVZ", "inNVZ").replace("OutNVZ", "outNVZ"),
                                 parts[2].lower()] + (parts[3:5] if len(parts) >= 5 else ["", ""]))
                j += 1
        with open(out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["set", "region", "nvz", "mansys", "slope", "landuse"])
            w.writerows(rows)
    return [r for r in csv.DictReader(open(out))]


def build():
    obl = parse_obligations()
    ST = {(r["region"], r["nvz"], r["mansys"]) for r in obl if r["set"] == "StorCover"}
    LE = {(r["region"], r["nvz"], r["mansys"], r["slope"], r["landuse"]) for r in obl if r["set"] == "applLe"}
    HE = {(r["region"], r["nvz"], r["mansys"], r["slope"], r["landuse"]) for r in obl if r["set"] == "applHe"}
    nvz = {r["region"]: float(r["value"]) for r in csv.DictReader(open(D / "p_nvzShare_lu.csv"))}
    area = defaultdict(dict)
    for r in csv.DictReader(open(D / "nvz_p_nvzArea.csv")):
        area[(r["dim1"], r["dim2"])][r["dim3"]] = float(r["level"])
    slope = defaultdict(dict)
    for r in csv.DictReader(open(D / "nvz_p_slopeTypes.csv")):
        slope[(r["dim1"], r["dim2"])][(r["dim3"], r["dim4"])] = float(r["level"])
    AP = {(r["country"], r["animal_cat"].lower(), r["manure_system"].lower(), r["technology"]): float(r["value"]) / 100.0
          for r in csv.DictReader(open(D / "costs" / "p_applic.csv"))}
    tsl = {(r["region"], r["activity"]): float(r["value"]) for r in csv.DictReader(open(D / "n_cascade_factors.csv"))
           if r["factor"] == "tsl"}

    def sperc(ru, z):
        a = area.get((ru, z), {})
        tot = sum(a.values())
        if tot <= 0:
            return {}
        return {(lu, sl): v * a.get(lu, 0.0) / tot for (lu, sl), v in slope.get((ru, z), {}).items()}

    rows = []
    for (ru, act), L in sorted(tsl.items()):
        if ru.endswith("000000") and ru not in ("DK000000", "EE000000", "CY000000", "MT000000", "LU000000",
                                                  "LV000000", "LT000000", "SI000000"):
            continue
        ms, n1 = ru[:2] + "000000", ru[:3] + "00000"
        cat = APPLIC_CAT.get(act, "ocat")
        sh = nvz.get(ru, 0.0)
        aS = lambda t: AP.get((ms, cat, "solid", t), 0.0)
        aL = lambda t: AP.get((ms, cat, "liquid", t), 0.0)
        # covered storage
        v = 0.0
        for key in (ru, n1, ms):
            v = sum(w * ((L * aL("CovStorLow") if (key, z, "liquid") in ST else 0.0)
                         + ((1 - L) * aS("CovStorLow") if (key, z, "solid") in ST else 0.0))
                    for z, w in (("inNVZ", sh), ("outNVZ", 1 - sh)))
            if v:
                break
        if ms == "MT000000" and act in ("SHGM", "SHGF"):
            v = L * aL("CovStorLow")
        if v:
            rows.append([ru, act, "CovStorLow", round(v, 9)])
        for tech, S in (("AmmAppLE", LE), ("AmmAppHE", HE)):
            v = 0.0
            for key in (ru, n1, ms):
                v = 0.0
                for z, w in (("inNVZ", sh), ("outNVZ", 1 - sh)):
                    for (lu, sl), p in sperc(ru, z).items():
                        v += w * p * ((L * aL(tech) if (key, z, "liquid", sl, lu) in S else 0.0)
                                      + ((1 - L) * aS(tech) if (key, z, "solid", sl, lu) in S else 0.0))
                if v:
                    break
            if v:
                rows.append([ru, act, tech, round(v, 9)])
    with open(D / "nitrates_directive_min_shares.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["region", "activity", "technology", "value"])
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    rows = build()
    print(len(rows), "minimum shares;", len({r[0] for r in rows}), "regions")
    for r in rows:
        if r[0] in ("DE110000", "DK000000", "NL220000", "PL220000") and r[1] in ("DCOL", "PIGF"):
            print(r)
