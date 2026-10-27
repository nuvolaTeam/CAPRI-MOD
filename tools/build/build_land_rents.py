"""CAPRI's land rents per model region and land type at the 2030 reference (docs/LAND_RENT_CALIBRATION_PLAN.md).

CAPRI's supply calibration takes the land rents as given (supply/cal_land_nests.gms sets DATA(r, landType, "d_area");
supply/prep_cal.gms l. 125-156 subtracts the "assumed land rent for arable and grass land" from the activities' costs;
supply/pmp_terms/define_const_pmp_param.gms adds it back). At the calibration point CAPRI's simulation reproduces them as
the land balances' duals, which its results report as D_AREA: the land types ARAC and FRUN carry the rent (positive),
the activities minus the rent of their land type (grassland GRAS: -rent of grassland).

Read from CAPRI's 2030 reference (res_2_1730greendeal_refpol_endotech_all_inidefaulta, the file the model's 2030
trajectory is built from):
  rent_ARAC = D_AREA(ARAC), rent_FRUN = D_AREA(FRUN), rent_GRAS = -D_AREA(GRAS), EUR/ha; LEVL of the same rows (1000 ha)
Non-positive rents (grassland in ten regions, every land type of PT20) are not calibration rents: CAPRI's calibration
gives every land type a positive one (supply/cal_land_nests.gms l. 204-226), and so does this file since 23 October 2026
(before, the model kept its own base dual there, recovered with a 1% shadow-price proxy):
  grassland:          min(1, 0.2 x TOOU)                                       (cal_land_nests.gms l. 221-226)
  arable, permanent:  max(p_landRentCoefToou x TOOU + p_landRentCoefPrme x PRME, 1.25 x PRME)   (l. 204-209)
with CAPRI's FADN land-rent regression (intercept 0, 0.084295555 on revenue, 0.700023526 on premiums; the values in
pol_input/ghg/carbcali_fin_endotech_noc.gms l. 259-261) and TOOU, PRME per ha of the land type, level-weighted over its
activities (cal_land_nests.gms l. 176-193; landTypes_to_pact: sets.gms l. 2944-2959) from the same 2030 reference.
Model regions: CAPRI's regions in groups covering the same territory (tools/lib/_model_regions.capri_groups); a group's rent
is its CAPRI regions' rents weighted by their area of that land type; model regions without a CAPRI region take the
member state's (national) rent (REGISTERED, as elsewhere in the model).

    python tools/build/build_land_rents.py [--year 2030|2017] [--ref FILE]
Writes capri_data/2017/supply/land_rents_2030.csv (or land_rents_2017.csv from CAPRI's 2017 results, res_17<MS> dumps:
D_AREA 'Y'; 23 October 2026) with region, capri_source, rent_arac, rent_frun, rent_gras (EUR/ha).
"""
from __future__ import annotations
import argparse, csv, importlib.util, re, subprocess, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF = Path("/mnt/user-data/uploads/res_2_1730greendeal_refpol_endotech_all_inidefaulta.csv")
OUT = ROOT / "capri_data" / "2017" / "supply" / "land_rents_2030.csv"
SRC_OUT = ROOT / "capri_data" / "sources" / "capri_land_rents" / "land_rents_capri_2030.csv"
TYPES = ("ARAC", "FRUN", "GRAS")
#: CAPRI's FADN land-rent regression (pol_input/ghg/carbcali_fin_endotech_noc.gms l. 259-261)
RENT_INTERCEPT, RENT_COEF_TOOU, RENT_COEF_PRME = 0.0, 0.084295555, 0.700023526
#: CAPRI's crop activities by land type (sets.gms: MECACT, MFCACT, GRSACT, cropC_to_landAgg FRUN; arable = the rest)
FRUN_ACTS = ("TWIN", "CITR", "OFRU", "TAGR", "TABO", "OLIV", "APPL", "NURS", "NECR")
GRAS_ACTS = ("GRAE", "GRAI", "IHISGR", "FALLGR")
ARAC_ACTS = ("SWHE", "DWHE", "RYEM", "BARL", "OATS", "MAIZ", "OCER", "PARI", "RAPE", "SUNF", "SOYA", "PULS", "POTA",
             "SUGB", "TEXT", "TOBA", "TOMA", "OVEG", "FALL", "ISET", "GSET", "TSET", "VSET", "MAIF", "ROOF", "OFAR",
             "OOIL", "OIND", "FLOW", "OCRO", "IHISCR")
ACTS_OF = {"ARAC": ARAC_ACTS, "FRUN": FRUN_ACTS, "GRAS": GRAS_ACTS}


DUMPS = Path("/home/claude/work/capreg")


def read_items(year: int, ref: Path) -> dict:
    """{CAPRI region: {(code, item): value}} for the land types and the crop activities: D_AREA, LEVL, TOOU, PRME of
    CAPRI's 2030 reference (dataOut, '2030') or of its 2017 results (res_17<MS> dumps, 'Y')."""
    codes = sorted(set(TYPES) | {x for v_ in ACTS_OF.values() for x in v_})
    alt = "|".join(codes)
    if year == 2030:
        pat = rf"^'[A-Z]{{2}}[0-9A-Z]{{6}}'\.''\.'({alt})'\.'(D_AREA|LEVL|TOOU|PRME)'\.'2030'"
        rx = re.compile(rf"^'([A-Z]{{2}}[0-9A-Z]{{6}})'\.''\.'({alt})'\.'(D_AREA|LEVL|TOOU|PRME)'\.'2030'\s+([-\d.Ee+]+)")
        files = [str(ref)]
    else:
        pat = rf"^'[A-Z]{{2}}[0-9A-Z]{{6}}'\.'({alt})'\.'(D_AREA|LEVL|TOOU|PRME)'\.'Y'"
        rx = re.compile(rf"^'([A-Z]{{2}}[0-9A-Z]{{6}})'\.'({alt})'\.'(D_AREA|LEVL|TOOU|PRME)'\.'Y'\s+([-\d.Ee+]+)")
        files = sorted(str(f) for f in DUMPS.glob("res_17*.txt") if re.fullmatch(r"res_17[A-Z]{2}\.txt", f.name))
    v = defaultdict(dict)
    for f in files:
        txt = subprocess.run(["grep", "-hE", pat, f], capture_output=True, text=True).stdout
        for line in txt.splitlines():
            m = rx.match(line)
            if m:
                v[m.group(1)][(m.group(2), m.group(3))] = float(m.group(4))
    return v


def rents(av: dict) -> dict:
    """{CAPRI region: {land type: (rent EUR/ha, level 1000 ha)}}: the land types' D_AREA (grassland: minus the
    grassland activity's, as CAPRI reports the activities' D_AREA as minus the rent of their land type); where that is
    not positive, CAPRI's calibration rent (cal_land_nests.gms l. 204-226)."""
    def per_ha(r, t, item):
        num = den = 0.0
        for x in ACTS_OF[t]:
            l_ = av[r].get((x, "LEVL"), 0.0)
            if l_ > 0:
                num += av[r].get((x, item), 0.0) * l_
                den += l_
        return num / den if den > 0 else None

    out, fixed = {}, []
    for r, d in av.items():
        rent = {}
        for t in TYPES:
            if t == "GRAS":
                x = next((d[(g, "D_AREA")] for g in ("GRAS",) + GRAS_ACTS if (g, "D_AREA") in d), None)
                rr = -x if x is not None else None
            else:
                x = d.get((t, "D_AREA"))
                rr = x
            if rr is None:
                continue
            lev = d.get((t, "LEVL"))
            if lev is None:
                lev = sum(d.get((a_, "LEVL"), 0.0) for a_ in ACTS_OF[t])
            if not rr > 0:
                # CAPRI's calibration rent where none positive is given (cal_land_nests.gms l. 204-226)
                toou, prme = per_ha(r, t, "TOOU"), per_ha(r, t, "PRME")
                old = rr
                if t == "GRAS" and toou is not None:
                    rr = min(1.0, 0.2 * toou)
                elif t != "GRAS" and toou is not None and prme is not None:
                    rr = max(RENT_INTERCEPT + RENT_COEF_TOOU * toou + RENT_COEF_PRME * prme, 1.25 * prme)
                fixed.append((r, t, old, rr))
                if not rr > 0:
                    continue        # the land type has no level in CAPRI's region (cal_land_nests.gms: $ levl): no rent
            rent[t] = (rr, max(float(lev), 0.0))
        out[r] = rent
    for r, t, old, new in fixed:
        print(f"  {r} {t}: reported {old:.1f} -> CAPRI's calibration rent {new:.2f} EUR/ha")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", type=Path, default=REF)
    ap.add_argument("--year", type=int, default=2030, choices=(2017, 2030))
    a = ap.parse_args()
    data = rents(read_items(a.year, a.ref))
    out = OUT if a.year == 2030 else OUT.with_name("land_rents_2017.csv")
    # per CAPRI region as well (read by tools/build/build_pmp_recipe.py, which works on CAPRI's regions)
    SRC_OUT.parent.mkdir(parents=True, exist_ok=True)
    src_out = SRC_OUT.with_name(f"land_rents_capri_{a.year}.csv")
    with open(src_out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["capri_region", "land_type", "rent_eur_ha", "levl_kha"])
        for c in sorted(data):
            for t, (r_, l_) in sorted(data[c].items()):
                w.writerow([c, t, repr(float(r_)), repr(float(l_))])
    print(f"wrote {src_out}")
    sp = importlib.util.spec_from_file_location("_mr", ROOT / "tools" / "lib" / "_model_regions.py")
    mr = importlib.util.module_from_spec(sp); sp.loader.exec_module(mr)
    regions = mr.model_regions()
    _c2g, groups = mr.capri_groups(regions)
    rows, src = {}, {}
    for _g, (codes, regs) in groups.items():
        rent = {}
        for t in TYPES:
            num = den = 0.0
            for c in codes:
                if t in data.get(c, {}):
                    r_, l_ = data[c][t]
                    num += r_ * l_; den += l_
            if den > 0:
                rent[t] = num / den
            else:
                vals = [data[c][t][0] for c in codes if t in data.get(c, {})]
                if vals:
                    rent[t] = sum(vals) / len(vals)
        for r in regs:
            if rent:
                rows[r] = rent; src[r] = "+".join(sorted(codes))
    for r in regions:
        nat = mr.national_code(r)
        d = data.get(nat, {})
        have = rows.setdefault(r, {})
        miss = [t for t in TYPES if t not in have and t in d]
        for t in miss:
            have[t] = d[t][0]
        if miss:
            src[r] = (src.get(r, "") + ("; " if r in src else "") + f"{nat} ({','.join(miss)})").strip()
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["region", "capri_source", "rent_arac", "rent_frun", "rent_gras"])
        n = 0
        for r in sorted(rows):
            d = rows[r]
            if not d:
                continue
            w.writerow([r, src.get(r, "")] + [("" if t not in d else repr(float(d[t]))) for t in TYPES])
            n += 1
    print(f"wrote {out} ({n} regions)")


if __name__ == "__main__":
    main()
