"""CAPRI's per-crop nitrogen coefficients per region, 2030 (for the gross N balance's crop terms).

Two sources:
- CAPRI's 2030 reference results, res_2_1730greendeal_refdefaulta (dataOut; tools/lib/paths.BASELINE_REF), per region
  and crop: LEVL (1000 ha), YILD (kg/ha), NITF (CAPRI's reported N per ha, the need net of fixation: not the removal,
  KNOWN_ISSUES K191), NCRD (N from crop residues and deposition, global/fromimpact/sets.gms), MANN (the crop's N
  delivered to the soil: deposition and residues), nutNed_biofix (1000 t N fixed, fert_dist_results; it gives extensive
  grassland intensive grassland's value, K191).
- CAPRI's simulation data of the same year, which its supply model uses (K191): fert/fertned.gms rebuilds each crop's
  N, P2O5 and K2O per ha, DATA(crop, NITF | PHOF | POTF, "Y") (e_EXPPRD's removal, NUTNED_'s base) and its deliveries
  DATA(crop, MANN, "Y"), from the year's yields, the outputs' nutrient contents, the residues' contents
  (envind/def_gascoeff.gms Resid) and the fodder's losses; fert/fertpar.gms sets the fixation rates p_nitrFact(crop,
  BioFix) (the member states' grassland rates, other arable fodder's legume share). Ported as named functions
  (capri_mod/supply/equations/fertned.py, fertpar.py, def_gascoeff.py) and computed here on sim_ini_21730's DATA at "Y"
  (capri_sources/reference/simini/simini_21730/DATA.csv.gz, tools/build/build_simini_reference.py; the fodder legume
  share at "BAS"), with CAPRI's tables read from its GAMS files (fertpar.gms: the RALL rates, p_nfixRate_gras, MAXF,
  doubleMaxf; def_gascoeff.gms: p_nutContCropOutput, Nindex; sets.gms: PACT_TO_Y, FODF, CERE).

Output: capri_data/baselines/capri_greendeal_ref/1730/environment/capri_crop_n_coefs_2030.csv
  capri_region, crop, levl, yild, nitf, ncrd, mann, biofix_t (dataOut, as before) and data_nitf (CAPRI's simulation
  DATA(crop, NITF), kg N/ha), biofix_rate (p_nitrFact(crop, BioFix)), data_mann (fertned's MANN, kg N/ha: a check on
  MANN, not used)
Checks printed: the region's removal sum(levl x data_nitf) against CAPRI's EXPPRD; data_mann against MANN.

Use (capri_mod/environmental/nitrogen.py, _capri_crop_n): removal data_nitf, fixation data_nitf x biofix_rate,
residues MANN less deposition, per ha x the run's yield / the data's yield.

Usage: python tools/build/build_capri_crop_n_coefs.py [<zip>] [--simini-data CSV.GZ] [--gams DIR]
"""
import argparse
import csv
import gzip
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import BASELINE_REF, SOURCES  # noqa: E402  (CAPRI's material outside the repository)
from _model_regions import MS_OF_PREFIX  # noqa: E402  (CAPRI's member state of a region)
import gams_sets as G  # noqa: E402
from capri_mod.supply.equations import fertned as FN, fertpar as FP, def_gascoeff as DG  # noqa: E402

OUT = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "environment" / "capri_crop_n_coefs_2030.csv"
DEPOSITION = ROOT / "capri_data" / "2017" / "environment" / "n_deposition_regional.csv"
P1 = re.compile(r"'([^']+)'\.''\.'([^']+)'\.'(LEVL|YILD|NITF|NCRD|MANN)'\.'2030'\s+([-0-9.eE+]+)")
P2 = re.compile(r"'([^']+)'\.'nutNed_biofix'\.'([^']+)'\.'NITF'\.'2030'\s+([-0-9.eE+]+)")
P3 = re.compile(r"'([^']+)'\.''\.'EXPPRD'\.'NITF'\.'2030'\s+([-0-9.eE+]+)")
#: CAPRI's aggregates among the reported columns (SETA: "Set aside total" of ISET, GSET, TSET, NONF and VSET, sets.gms
#: l. 246, 3088; until 20 November 2026 kept, so the regions' crop land counted the set-aside twice and the removal and
#: residues of capri_mod/environmental/nitrogen.py were scaled up by its share, ES41 6.6%; K191)
AGG = {"ARAB", "CERE", "PERM", "FODD", "SETF", "OILS", "OAR1", "AGGT", "UAAR", "GROF", "INTF", "NETF", "SETA"}
FNUT = ("NITF", "PHOF", "POTF")
FOUT_T_N = {"MANN": "NITF", "MANP": "PHOF", "MANK": "POTF"}


def _gams_lines(path: Path):
    """The file's lines without GAMS comment lines ('*' in the first column) and $ontext ... $offtext blocks."""
    out, skip = [], False
    for no, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        s = line.strip().lower()
        if s.startswith("$ontext"):
            skip = True
            continue
        if s.startswith("$offtext"):
            skip = False
            continue
        if skip or line.startswith("*"):
            continue
        out.append((no, line))
    return out


def _table(lines, header_rx, cols):
    """A GAMS TABLE's rows (label -> {column: value}) by the header's column positions; the table starts after the line
    matching header_rx and ends at ';'."""
    rows, it, pos = {}, iter(lines), None
    for no, line in it:
        if re.search(header_rx, line, re.I):
            break
    for no, line in it:
        if pos is None:
            if line.strip():
                pos = {c: line.index(c) for c in cols}
            continue
        end = line.rstrip().endswith(";")
        body = line.rstrip().rstrip(";")
        toks = list(re.finditer(r"\S+", body))
        if toks:
            lab, vals = toks[0].group(0), {}
            for t in toks[1:]:            # GAMS: a value belongs to the column whose header it overlaps
                for c, p in pos.items():
                    if t.start() < p + len(c) and t.end() > p:
                        vals[c] = float(t.group(0))
            rows[lab.upper()] = vals
        if end:
            break
    return rows


def _list(lines, header_rx):
    """A GAMS parameter list / label value ... / after the line matching header_rx."""
    out, on = {}, False
    for no, line in lines:
        if not on:
            on = bool(re.search(header_rx, line, re.I))
            continue
        s = line.strip()
        if s.startswith("/") and out:
            break
        m = re.match(r"([A-Za-z0-9_]+)\s+([-0-9.eE+]+)", s)
        if m:
            out[m.group(1).upper()] = float(m.group(2))
    return out


def capri_tables(gams: Path) -> dict:
    """CAPRI's constants of fertpar.gms and def_gascoeff.gms, and the sets fertned uses."""
    fp = _gams_lines(gams / "fert" / "fertpar.gms")
    nf = _table(fp, r"^TABLE p_nitrFact\(", ("NOM", "AtmDep", "NITRO", "BioFix"))
    rall = {k.split(".", 1)[1]: v.get("BioFix", 0.0) for k, v in nf.items() if k.startswith("RALL.")}
    nfix = _list(fp, r"^PARAMETER p_nfixRate_gras")
    maxf = {}
    for no, line in fp:
        m = re.match(r'\s*MAXF\("(\w+)"\)\s*=\s*([-0-9.]+)\s*;', line)
        if m:
            maxf[m.group(1).upper()] = float(m.group(2))
    mult = next(float(m.group(1)) for no, line in fp
                if (m := re.match(r"\s*MAXF\(FNUT\)\s*=\s*MAXF\(FNUT\)\s*\*\s*([-0-9.]+)\s*;", line)))
    maxf = {k: v * mult for k, v in maxf.items()}
    dmx = next(set(x.strip().upper() for x in m.group(1).split(",")) for no, line in fp
               if (m := re.search(r"set doubleMaxf\(PACT\)[^/]*/([^/]*)/", line, re.I)))
    dg = _gams_lines(gams / "envind" / "def_gascoeff.gms")
    cont = _table(dg, r"TABLE p_nutContCropOutput\(O,FNUT\)", FNUT)
    for no, line in dg:            # p_nutContCropOutput("TABO",FNUT) = p_nutContCropOutput("OLIV",FNUT) * 5; (l. 375-376)
        m = re.match(r'\s*p_nutContCropOutput\("(\w+)",FNUT\)\s*=\s*p_nutContCropOutput\("(\w+)",FNUT\)\s*([*/])\s*([-0-9.]+)', line)
        if m:
            f = float(m.group(4))
            cont[m.group(1).upper()] = {k: (v * f if m.group(3) == "*" else v / f) for k, v in cont[m.group(2).upper()].items()}
    nidx = _list(dg, r"^Parameter Nindex")
    gs = G.read(gams / "sets.gms", gams, {"BaseYear": "2017", "BAS": "17"})
    p2y = defaultdict(list)
    for a, o in gs.get("PACT_TO_Y"):
        p2y[a.upper()].append(o.upper())
    fodf = {x[0].upper() for x in gs.get("FODF")}
    grsact = {x[0].upper() for x in gs.get("GRSACT")}
    cere = {x[0].upper() for x in gs.get("CERE")}
    cereal_out = {o for a in cere for o in p2y.get(a, [])}
    resid = {o: {n: DG.Resid(o, cont[o].get(n, 0.0), nidx.get(o, 0.0), o in cereal_out) for n in FNUT} for o in cont}
    return dict(rall=rall, nfix=nfix, maxf=maxf, double=dmx, resid=resid, p2y=p2y, fodf=fodf, grsact=grsact)


def simini(path: Path) -> dict:
    """sim_ini_21730's DATA: {(region, row, col): value} at "Y", and the fodder legume share at "BAS"."""
    out, fleg = {}, {}
    with gzip.open(path, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["d3"] == "Y":
                out[(r["d0"].upper(), r["d1"].upper(), r["d2"].upper())] = float(r["value"])
            elif r["d3"] == "BAS" and r["d1"].upper() == "FLEG" and r["d2"].upper() == "LEVL":
                fleg[r["d0"].upper()] = float(r["value"])
    return out, fleg


def capri_data_y(region: str, crop: str, D: dict, fleg: dict, T: dict, dep: float) -> dict:
    """CAPRI's simulation DATA of a region's crop (fertned.gms, fertpar.gms; capri_mod/supply/equations)."""
    v = lambda a, b: D.get((region, a, b), 0.0)          # noqa: E731
    prods = T["p2y"].get(crop, [])
    lev = v(crop, "LEVL")
    y = sum(v(crop, o) for o in prods)
    ohp = FN.O_HP(y, lev)
    out, rr = {}, {}
    for n in FNUT:
        needs = []
        for o in prods:
            r0 = FN.p_residRel(v(n, o), T["resid"].get(o, {}).get(n, 0.0), o in T["fodf"])
            needs.append(FN.p_cropNeed(v(n, o), r0))
            rr[n] = rr.get(n, 0.0) + (FN.p_residRel_LOSF(r0, v("LOSF", o), v("GROF", o)) if o in T["fodf"] else r0)
        need_stra = FN.p_cropNeed(v(n, "STRA"), 0.0)
        out[n] = FN.DATA_FNUT_yield(ohp, v(crop, "STRA"), needs, need_stra, T["maxf"][n], crop in T["double"]) if lev > 0 else 0.0
    resid_pact = any(T["resid"].get(o, {}).get(n, 0.0) for o in prods for n in FNUT)
    for f, n in FOUT_T_N.items():
        x = FN.DATA_FOUT_dep(dep) if (f == "MANN" and lev > 0) else 0.0
        if resid_pact and lev > 0:
            x = FN.DATA_FOUT_resid(x, out[n], rr.get(n, 0.0))
        out[f] = FN.DATA_FOUT_straw(x, v(crop, "STRA"), v("LOSF", "STRA"), v("GROF", "STRA"), v(n, "STRA"))
    ms = MS_OF_PREFIX.get(region[:2], region[:2] + "000000")
    out["biofix_rate"] = FP.p_nitrFact_BioFix(crop, T["rall"].get(crop, 0.0), T["nfix"].get(ms), fleg.get(region, fleg.get(ms, 0.0)),
                                              T["rall"].get("FLEG", 0.0), T["rall"].get("GRAE", 0.0), crop in T["grsact"])
    return out


def main(src: Path, simini_path: Path, gams: Path):
    v, exp = defaultdict(dict), {}
    with zipfile.ZipFile(src) as z, z.open(z.namelist()[0]) as fh:
        for raw in fh:
            line = raw.decode("latin-1")
            m = P3.match(line)
            if m:
                exp[m.group(1)] = float(m.group(2)); continue
            m = P1.match(line)
            if m:
                v[(m.group(1), m.group(2))][m.group(3)] = float(m.group(4)); continue
            m = P2.match(line)
            if m:
                v[(m.group(1), m.group(2))]["BIOFIX"] = float(m.group(3))
    T = capri_tables(gams)
    D, fleg = simini(simini_path)
    with open(DEPOSITION, newline="") as fh:
        dep = {r["region"]: float(r["deposition_kg_n_per_ha"]) for r in csv.DictReader(fh)}
    rows, rem, mann_dev, missing = [], defaultdict(float), [], 0
    for (r, c), d in sorted(v.items()):
        if c in AGG or not d.get("LEVL") or "NITF" not in d:
            continue
        cd = capri_data_y(r.upper(), c.upper(), D, fleg, T, dep.get(r, 0.0)) if c != "GRAS" else None
        if cd is not None and not D.get((r.upper(), c.upper(), "LEVL")):
            missing += 1
        if cd is not None:
            rem[r] += d["LEVL"] * cd["NITF"] / 1000.0
            if r in dep and d.get("MANN") and d["LEVL"] > 0.5:
                mann_dev.append(abs(cd["MANN"] / d["MANN"] - 1.0))
        rows.append([r, c, d.get("LEVL"), d.get("YILD", ""), d.get("NITF"), d.get("NCRD", ""), d.get("MANN", ""),
                     d.get("BIOFIX", ""), "" if cd is None else cd["NITF"], "" if cd is None else cd["biofix_rate"],
                     "" if cd is None else cd["MANN"]])
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["capri_region", "crop", "levl", "yild", "nitf", "ncrd", "mann", "biofix_t", "data_nitf", "biofix_rate",
                    "data_mann"])
        w.writerows(rows)
    ratios = sorted(rem[r] / exp[r] for r in rem if exp.get(r))
    within = lambda t: sum(abs(x - 1.0) < t for x in ratios)        # noqa: E731
    print(len(rows), "rows,", len({r[0] for r in rows}), "regions ->", OUT.name, f"({missing} crop rows without CAPRI's "
          f"simulation level)")
    print(f"removal sum(levl x data_nitf) / CAPRI's EXPPRD over {len(ratios)} regions: median "
          f"{ratios[len(ratios) // 2]:.5f}, within 0.1% {within(1e-3)}, within 1% {within(1e-2)}, min {ratios[0]:.4f}")
    mann_dev.sort()
    print(f"data_mann / MANN over {len(mann_dev)} crop rows: within 0.5% {sum(x < 5e-3 for x in mann_dev)}, "
          f"within 2% {sum(x < 2e-2 for x in mann_dev)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", type=Path, default=BASELINE_REF)
    ap.add_argument("--simini-data", type=Path, default=SOURCES / "reference" / "simini" / "simini_21730" / "DATA.csv.gz")
    ap.add_argument("--gams", type=Path, default=SOURCES / "gams")
    a = ap.parse_args()
    main(a.src, a.simini_data, a.gams)
