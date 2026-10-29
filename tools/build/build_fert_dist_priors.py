"""CAPRI's priors for the inner fertiliser distribution model (supply/set_fert_priors.gms, simulation mode).

In a simulation CAPRI reads the priors from its fertiliser calibration with sourceStat = postMode (supply/
prep_sim.gms): for every region, crop group NGRP and source distPos (MINE mineral, EXCR manure, CRES crop
residues and deposition) the prior mode is the posterior mode PER HECTARE of the baseline times the group's area,
and the accuracy (mode / standard deviation) is the calibration's. The gamma density then has
  var = (mode / accuracy)^2,  beta = (mode + sqrt(mode^2 + 4 var)) / (2 var),  alpha = beta^2 var.

Source: CAPRI's 2030 Green Deal reference results (res_2_1730greendeal_refdefaulta, dataOut): per CAPRI region the
flows to each crop, fertDist_mine / fertDist_excr / fertDist_cres (1000 t N; summed to the groups - the dump's rows
named CERE, PERM, GRAS are reporting aggregates over a different crop set, not the NGRP groups), the crop areas
(LEVL) and the region's mineral losses and manure N not available (AGGT, kg/ha) - the baseline's posterior; kept
as capri_data/sources/environment/fert_dist_dataout_2030.csv.xz. Per hectare these ARE CAPRI's posterior modes:
the priFertDist results at hand (DE, FR, NL, BL, DK, IT; priFertDist_<MS>1730defaulta) carry the same values
(postModePerHa, 2030) and accuracy 1 for every region, group and source; this builder checks both.

Crop groups (supply/define_ngrp_sets.gms, NMINREST off): WHEA (SWHE, DWHE), BARL, MAIZ, CERE (RYEM, OATS, OCER),
RAPN (RAPE, NONF), SUNF, SOYA, PULS, POTA, SUGB, MAIF, ROOF, OFAR, GRAS (GRAE, GRAI; permanent), VEGE (TOMA, OVEG,
FLOW, OCRO, OFRU), PERM (OLIV, TABO, TAGR, TWIN, CITR, APPL; permanent), OAFC (every other crop). Permanent groups
take no crop residues from the arable pool (fertDistCres_).

Outputs (capri_data/2017/environment/)
  fert_dist_priors_2030.csv       capri_region (CAPRI code), level (ru: CAPRI's region; nuts0: the country, for
                                  model regions without a CAPRI region), ngrp, perm, area_kha, mine_kg_ha, excr_kg_ha,
                                  cres_kg_ha, accuracy, mine_eff, excr_avail
  fert_dist_crop_groups_2030.csv  capri_region, model_crop, ngrp, share   (model crop -> CAPRI group, area shares;
                                  OFOD = OFAR + ROOF)

    python tools/build/build_fert_dist_priors.py [--dump /mnt/user-data/uploads/res_2_1730greendeal_refdefaulta.zip]
                                           [--prifertdist /mnt/user-data/uploads/priFertDist_1730defaulta.zip]
"""
from __future__ import annotations
import argparse, io, re, zipfile
from pathlib import Path

import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / "capri_data" / "2017" / "environment"
GROUP = {"SWHE": "WHEA", "DWHE": "WHEA", "BARL": "BARL", "MAIZ": "MAIZ", "RYEM": "CERE", "OATS": "CERE",
         "OCER": "CERE", "RAPE": "RAPN", "NONF": "RAPN", "SUNF": "SUNF", "SOYA": "SOYA", "PULS": "PULS",
         "POTA": "POTA", "SUGB": "SUGB", "MAIF": "MAIF", "ROOF": "ROOF", "OFAR": "OFAR", "GRAE": "GRAS",
         "GRAI": "GRAS", "TOMA": "VEGE", "OVEG": "VEGE", "FLOW": "VEGE", "OCRO": "VEGE", "OFRU": "VEGE",
         "OLIV": "PERM", "TABO": "PERM", "TAGR": "PERM", "TWIN": "PERM", "CITR": "PERM", "APPL": "PERM"}
PERM_NGRP = {"GRAS", "PERM"}
#: aggregates in the extract (not activities)
AGGREGATES = {"AGGT", "ARAB", "CERE", "FODD", "OAR1", "OILS", "PERM", "SETF", "UAAR", "GRAS"}
#: model crop -> CAPRI crops (environmental_module._CAPRI_CROP and the model's names)
MODEL = {"CORN": ("MAIZ",), "WINE": ("TWIN",), "GRAS": ("GRAE", "GRAI"),
         "OFOD": ("OFAR", "ROOF"), "SETA": ("SETA", "FALL", "VSET")}


def ngrp(c: str) -> str:
    return GROUP.get(c, "OAFC")


def check_dumps(zpath: Path, pri: pd.DataFrame):
    """Compare with CAPRI's priFertDist results (postModePerHa and accuracy, NITF, 2030)."""
    if not zpath.exists():
        print("priFertDist results not at hand: no check")
        return
    pat = re.compile(r"^'([A-Z0-9]+)'\.'(postModePerHa|accuracy)'\.'(MINE|EXCR|CRES)'\.'NITF'\.'([A-Z]+)'\.'2030'\s+([-\d.Ee+]+)")
    got = {}
    with zipfile.ZipFile(zpath) as z:
        for name in z.namelist():
            with z.open(name) as fh:
                for raw in io.TextIOWrapper(fh, errors="ignore"):
                    if raw.startswith("Parameter p_priNutAvailFact"):
                        break
                    m = pat.match(raw)
                    if m:
                        got[(m.group(1), m.group(2), m.group(3), m.group(4))] = float(m.group(5))
    acc = [v for (r, s, d, g), v in got.items() if s == "accuracy"]
    print(f"priFertDist results: {len(got)} values; accuracy 2030 min {min(acc):.3g} max {max(acc):.3g}")
    col = {"MINE": "mine_kg_ha", "EXCR": "excr_kg_ha", "CRES": "cres_kg_ha"}
    p = pri.set_index(["capri_region", "ngrp"])
    worst, n = 0.0, 0
    for (r, s, d, g), v in got.items():
        if s != "postModePerHa":
            continue
        if (r, g) not in p.index:
            continue
        x = float(p.at[(r, g), col[d]])
        worst = max(worst, abs(x - v) / max(1.0, abs(v)))
        n += 1
    print(f"postModePerHa against the extract: {n} values, worst relative difference {worst:.2e}")


SRC = ROOT / "capri_data" / "sources" / "environment" / "fert_dist_dataout_2030.csv.xz"
NGRPS = ("WHEA", "BARL", "MAIZ", "CERE", "RAPN", "SUNF", "SOYA", "PULS", "POTA", "SUGB", "MAIF", "ROOF", "OFAR",
         "GRAS", "OAFC", "VEGE", "PERM")
#: CAPRI crops (MCACT) whose LEVL make up the group areas; GRAS = GRAE + GRAI
CROPS = tuple(sorted(set(GROUP) | {"OIND", "NURS", "TEXT", "TOBA", "FALL", "NECR", "OOIL", "SETA", "VSET", "ISET",
                                   "PARI", "OFRU", "TOMA", "OVEG", "FLOW", "OCRO", "NONF", "ROOF", "OFAR", "MAIF"}))


def extract(dump: Path) -> pd.DataFrame:
    import subprocess
    pat = (r"^'[A-Z0-9]+'\.'(fertDist_mine|fertDist_excr|fertDist_cres)'\.'(" + "|".join(CROPS) + r")'\.'NITF'\.'2030'"
           r"|^'[A-Z0-9]+'\.''\.'(" + "|".join(CROPS) + r")'\.'LEVL'\.'2030'"
           r"|^'[A-Z0-9]+'\.'(nutNed_mine_loss_gasRunTot_perha|fertDist_mine_perha|nutNed_excr_unavailable_perha|"
           r"fertDist_excr_perha)'\.'AGGT'\.'NITF'\.'2030'")
    p1 = subprocess.Popen(["unzip", "-p", str(dump)], stdout=subprocess.PIPE)
    out = subprocess.run(["grep", "-E", pat], stdin=p1.stdout, capture_output=True, text=True).stdout
    rx = re.compile(r"^'([A-Z0-9]+)'\.'([^']*)'\.'([A-Z]+)'\.'([A-Z]+)'\.'2030'\s+([-\d.Ee+]+)")
    rows = []
    for line in out.splitlines():
        m = rx.match(line)
        if m:
            r, item, prod, col, v = m.groups()
            rows.append(dict(region=r, item=item if item else "LEVL", product=prod, value=float(v)))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, default=Path("/mnt/user-data/uploads/res_2_1730greendeal_refdefaulta.zip"))
    ap.add_argument("--prifertdist", type=Path, default=Path("/mnt/user-data/uploads/priFertDist_1730defaulta.zip"))
    a = ap.parse_args()
    if a.dump.exists():
        src = extract(a.dump)
        SRC.parent.mkdir(parents=True, exist_ok=True)
        src.to_csv(SRC, index=False)
        print(f"extracted {len(src)} rows -> {SRC.relative_to(ROOT)}")
    src = _read_csv(SRC)
    v = {(r.region, r.item, r.product): r.value for r in src.itertuples(index=False)}
    # CAPRI's regions (RU: NUTS2, or the country where it has one region) and, for the model regions without a
    # CAPRI region of their own (Berlin, Hamburg, Bremen, ...), the country (NUTS0 code; level "nuts0")
    regions = sorted({r for r in src.region if len(r) == 8})
    nuts0 = {r for r in regions if r.endswith("000000") and
             any(x.startswith(r[:2]) and not x.endswith("000000") for x in src.region)}
    rows, mrows = [], []
    for r in regions:
        area = {}
        for c in CROPS:
            x = v.get((r, "LEVL", c), 0.0)
            if x > 0:
                area[c] = x
        garea = {}
        for c, x in area.items():
            garea[ngrp(c)] = garea.get(ngrp(c), 0.0) + x
        ml, mp = v.get((r, "nutNed_mine_loss_gasRunTot_perha", "AGGT")), v.get((r, "fertDist_mine_perha", "AGGT"))
        eu, ep = v.get((r, "nutNed_excr_unavailable_perha", "AGGT")), v.get((r, "fertDist_excr_perha", "AGGT"))
        meff = 1.0 + ml / mp if (ml is not None and mp) else float("nan")
        eav = 1.0 + eu / ep if (eu is not None and ep) else float("nan")
        for g in NGRPS:
            A = garea.get(g, 0.0)
            if A <= 0:
                continue
            cs = [c for c in area if ngrp(c) == g]
            # group flow = sum over the group's crops (the dump's group-named rows CERE, PERM, GRAS are CAPRI's
            # reporting aggregates, not the NGRP groups)
            f = lambda s: sum(v.get((r, f"fertDist_{s}", c), 0.0) for c in cs) * 1000.0 / A   # 1000 t/1000 ha -> kg/ha
            mine, excr, cres = f("mine"), f("excr"), (0.0 if g in PERM_NGRP else f("cres"))
            if mine + excr + cres <= 0:
                continue
            rows.append(dict(capri_region=r, level="nuts0" if r in nuts0 else "ru", ngrp=g, perm=int(g in PERM_NGRP),
                             area_kha=A, mine_kg_ha=mine,
                             excr_kg_ha=excr, cres_kg_ha=cres, accuracy=1.0, mine_eff=meff, excr_avail=eav))
        # model crop -> group shares
        rev = {}
        for mc, cs in MODEL.items():
            for c in cs:
                rev[c] = mc
        for c, x in area.items():
            mrows.append(dict(capri_region=r, model_crop=rev.get(c, c), ngrp=ngrp(c), area=x))
    pri = pd.DataFrame(rows).sort_values(["capri_region", "ngrp"])
    pri.to_csv(ENV / "fert_dist_priors_2030.csv", index=False)
    mg = pd.DataFrame(mrows).groupby(["capri_region", "model_crop", "ngrp"], as_index=False).area.sum()
    mg["share"] = mg.area / mg.groupby(["capri_region", "model_crop"]).area.transform("sum")
    mg.drop(columns="area").to_csv(ENV / "fert_dist_crop_groups_2030.csv", index=False)
    print(f"fert_dist_priors_2030.csv: {len(pri)} rows, {pri[pri.level == 'ru'].capri_region.nunique()} CAPRI regions in "
          f"{pri.capri_region.str[:2].nunique()} countries")
    print(f"mineral efficiency: median {pri.mine_eff.median():.3f}; manure availability median {pri.excr_avail.median():.3f}")
    check_dumps(a.prifertdist, pri)


if __name__ == "__main__":
    main()
