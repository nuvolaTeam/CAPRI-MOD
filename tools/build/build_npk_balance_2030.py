"""CAPRI's crop nutrient balance for N, P and K (supply/supply_model.gms NUTNED_, fertDistMine_, fertDistExcr_,
fertDistCres_, ManureNPK_), from CAPRI's 2030 reference results, for the regional supply model in CAPRI's form
(capri_mod/supply/capri_regional_nlp.py, docs/NLP_PORT_DESIGN.md).

Source: res_2_1730greendeal_refdefaulta (dataOut, 2030), the same dump the nitrogen data come from
(tools/build/build_fert_dist_priors.py, tools/build/build_capri_gnb_components.py). CAPRI reports, per region, crop and nutrient
(NITF, PHOF, POTF), the terms of NUTNED_ in 1000 t:
  nutNed_lhs                    the need of the crop's group spread over its crops by area (so equal per ha within a
                                group); the group's total is sum LEVL x the crop's own NITF/PHOF/POTF (net of fixation;
                                within 0.1% in the median group, checked below)
  fertDist_mine / _excr / _cres the flows from mineral fertiliser, manure and the arable residue pool
  perm_cres                     the permanent crops' own residues and deposition (GRAE, GRAI, the PERM group)
  nutNed_mine_loss_gasRunTot    mineral N lost (N only)
  nutNed_excr_unavailable       manure nutrient not available to the crop
  nutNed_cres_unavailable, nutNed_cres_loss_gasRunTot   residue N not available / lost (N only)
with need = mineral - loss + manure - unavailable + residues (pooled or own) - unavailable - loss, exact per crop
(nutNed_rest ~ 1e-15). This builder checks that identity, and the pools: sum of manure flows = EXCRET - GASANI -
RUNANI - MTRADE (ManureNPK_, manExportOrAppl_), sum of mineral flows = NETF (fertDistMine_).

Outputs (capri_data/2017/environment/):
  npk_crop_coefs_2030.csv   capri_region, model_crop, nutrient (N, P, K), need_kg_ha (the crop's own NITF/PHOF/POTF),
                            pool_kg_ha (contribution to the
                            arable residue pool, fertDistCres_; non-permanent crops), own_kg_ha (permanent crops' own
                            residues, perm_cres), mine_kg_ha (CAPRI's mineral flow), levl_kha; CAPRI crops pooled into
                            the model's crops by area (CORN = MAIZ, WINE = TWIN, GRAS = GRAE + GRAI, OFOD = OFAR + ROOF,
                            SETA = FALL + VSET + ISET + GSET + TSET), and GRAE and GRAI on their own (the model's
                            grassland split column); main_share and straw_share, the parts of the need that follow the
                            main output's yield and the straw yield (fert/fertned.gms: need = MIN(cap, MAX(15, O_HP x
                            need per t + STRA x straw content)); 0 for crops at the floor or the cap), with CAPRI's straw
                            content and caps read from the vendored envind/gascoeff.gms and fert/fertpar.gms
  npk_region_2030.csv       capri_region, nutrient, mine_eff (1 + loss / mineral), excr_avail (1 + unavailable /
                            manure), cres_avail (1 + (unavailable + loss) / (pooled + own residues)), uvag_eur_t (CAPRI's
                            unit value of NITF/PHOF/POTF), mine_kt, excr_kt, pool_kt, own_kt, need_kt, land_kha
  fert_dist_priors_npk_2030.csv  as fert_dist_priors_2030.csv with a nutrient column (N, P, K): CAPRI's posterior
                            mode per ha of each crop group and source, accuracy 1 (tools/build/build_fert_dist_priors.py)
  livestock_manure_p_coef.csv, livestock_manure_k_coef.csv   manure P2O5 and K2O per model head (kg), CAPRI's 2017
                            regional total (MANP, MANK) / the model's herd, as livestock_manure_n_coef.csv
                            (tools/build/build_livestock_output_coef.py), from the CAPREG dumps (--capreg-dir)

    python tools/build/build_npk_balance_2030.py [--dump res_2_1730greendeal_refdefaulta.zip] [--capreg-dir DIR]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import functools as _ft
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / "capri_data" / "2017" / "environment"
SRC = ROOT / "capri_data" / "sources" / "environment" / "npk_dataout_2030.csv.xz"
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from build_fert_dist_priors import GROUP, PERM_NGRP, NGRPS, ngrp  # noqa: E402

NUTS = {"NITF": "N", "PHOF": "P", "POTF": "K"}
CRD = {"NITF": "NCRD", "PHOF": "PCRD", "POTF": "KCRD"}
#: CAPRI's crop activities (sets.gms MCACT: MECACT + MFCACT), the elementary rows of the dump; the dump's other crop
#: rows (CERE, OILS, ARAB, PERM, GRAS, SETA, VEGE, WHEA, RAPN, OAFC, ...) are aggregates
ELEM = ("SWHE", "DWHE", "RYEM", "BARL", "OATS", "MAIZ", "OCER", "PARI", "RAPE", "SUNF", "SOYA", "OOIL", "OIND", "NURS",
        "FLOW", "OCRO", "NECR", "MAIF", "ROOF", "OFAR", "GRAE", "GRAI", "PULS", "POTA", "SUGB", "TEXT", "TOBA", "TOMA",
        "OVEG", "APPL", "OFRU", "CITR", "TAGR", "TABO", "TWIN", "OLIV", "FALL", "ISET", "GSET", "TSET", "VSET", "NONF")
#: model crop <- CAPRI crops
MODEL = {"CORN": ("MAIZ",), "WINE": ("TWIN",), "GRAS": ("GRAE", "GRAI"), "OFOD": ("OFAR", "ROOF"),
         "SETA": ("FALL", "VSET", "ISET", "GSET", "TSET")}
FLOWS = ("fertDist_mine", "fertDist_excr", "fertDist_cres", "perm_cres", "nutNed_mine_loss_gasRunTot",
         "nutNed_cres_loss_gasRunTot", "nutNed_excr_unavailable", "nutNed_cres_unavailable", "nutNed_lhs")
BAL = ("EXCRET", "MTRADE", "GASANI", "RUNANI", "NETF", "UVAG")
GMS = ROOT / "capri_data" / "sources" / "capri_gams"


def straw_content() -> dict:
    """CAPRI's nutrient content of straw, kg per t (envind/gascoeff.gms, p_nutContCropOutput("STRA", FNUT)); CAPREG
    copies it to DATA(RS, FNUT, "STRA") and fert/fertned.gms prices straw at it (no residue relation for STRA)."""
    txt = (GMS / "envind" / "gascoeff.gms").read_text(errors="replace")
    blk = txt[txt.index("TABLE p_nutContCropOutput"):]
    m = re.search(r"^\s*STRA\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", blk, re.M)
    return dict(zip(("NITF", "PHOF", "POTF"), map(float, m.groups())))


def need_bounds() -> tuple:
    """fert/fertned.gms's bounds on a crop's need per ha: MAX(15, ...) and MIN(MAXF x (1 + 1 $ doubleMaxf), ...) with
    MAXF and doubleMaxf from fert/fertpar.gms (the last assignments: 200/160/140 x 2.0; GRAE, GRAI, OFAR, MAIF)."""
    txt = (GMS / "fert" / "fertpar.gms").read_text(errors="replace")
    mx = {k: float(v) for k, v in re.findall(r'^\s*MAXF\("(NITF|PHOF|POTF)"\)\s*=\s*([\d.]+)\s*;', txt, re.M)}
    sc = float(re.search(r"^\s*MAXF\(FNUT\)\s*=\s*MAXF\(FNUT\)\s*\*\s*([\d.]+)\s*;", txt, re.M).group(1))
    dbl = re.search(r"set doubleMaxf\(PACT\)[^/]*/([^/]*)/", txt).group(1)
    return 15.0, {k: v * sc for k, v in mx.items()}, {c.strip() for c in dbl.split(",") if c.strip()}


def extract(dump: Path) -> pd.DataFrame:
    cr = "|".join(ELEM + ("AGGT",))
    nu = "NITF|PHOF|POTF"
    pat = (rf"^'[A-Z0-9]+'\.'({'|'.join(FLOWS)})'\.'({cr})'\.'({nu})'\.'2030'"
           rf"|^'[A-Z0-9]+'\.''\.'({'|'.join(ELEM)})'\.'(LEVL|{nu}|NCRD|PCRD|KCRD|STRA)'\.'2030'"
           rf"|^'[A-Z0-9]+'\.''\.'({'|'.join(BAL)})'\.'({nu})'\.'2030'"
           rf"|^'[A-Z0-9]+'\.''\.'UAAR'\.'LEVL'\.'2030'")
    p1 = subprocess.Popen(["unzip", "-p", str(dump)], stdout=subprocess.PIPE)
    out = subprocess.run(["grep", "-E", pat], stdin=p1.stdout, capture_output=True, text=True).stdout
    rx = re.compile(r"^'([A-Z0-9]+)'\.'([^']*)'\.'([A-Za-z]+)'\.'([A-Z]+)'\.'2030'\s+([-\d.Ee+]+)")
    rows = []
    for line in out.splitlines():
        m = rx.match(line)
        if m:
            r, item, row, col, v = m.groups()
            rows.append(dict(region=r, item=item, row=row, col=col, value=float(v)))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, default=Path("/mnt/user-data/uploads/res_2_1730greendeal_refdefaulta.zip"))
    ap.add_argument("--capreg-dir", type=Path, default=Path("/home/claude/work/capreg"))
    ap.add_argument("--out-dir", type=Path, default=ENV, help="where to write the outputs (default: the data folder)")
    a = ap.parse_args()
    out = a.out_dir
    out.mkdir(parents=True, exist_ok=True)
    if a.dump.exists():
        src = extract(a.dump)
        SRC.parent.mkdir(parents=True, exist_ok=True)
        src.to_csv(SRC, index=False)
        print(f"extracted {len(src)} rows -> {SRC.relative_to(ROOT)}")
    src = _read_csv(SRC, keep_default_na=False)
    v = {(r.region, r.item, r.row, r.col): r.value for r in src.itertuples(index=False)}
    regions = sorted({r for r in src.region if len(r) == 8})
    nuts0 = {r for r in regions if r.endswith("000000") and
             any(x.startswith(r[:2]) and not x.endswith("000000") for x in regions)}
    rev = {c: mc for mc, cs in MODEL.items() for c in cs}
    stra_c = straw_content()
    floor_, maxf, dbl = need_bounds()
    print(f"CAPRI straw content {stra_c} kg/t; need bounds {floor_} kg/ha, MAXF {maxf} (x2 for {sorted(dbl)})")
    n_bound = n_crop = 0
    crow, rrow, prow = [], [], []
    worst_need = worst_man = worst_min = worst_grp = 0.0
    grp_err = []
    for r in regions:
        lev = {c: v.get((r, "", c, "LEVL"), 0.0) for c in ELEM}
        lev = {c: x for c, x in lev.items() if x > 0}
        if not lev:
            continue
        land = v.get((r, "", "UAAR", "LEVL"), sum(lev.values()))
        for col, nut in NUTS.items():
            f = lambda item, c: v.get((r, item, c, col), 0.0)
            tot = {it: sum(f(it, c) for c in lev) for it in FLOWS}
            # NUTNED_ per crop: need = mine + loss + excr + unav + cres + own + cres losses (losses negative)
            for c in lev:
                rhs = (f("fertDist_mine", c) + f("nutNed_mine_loss_gasRunTot", c) + f("fertDist_excr", c)
                       + f("nutNed_excr_unavailable", c) + f("fertDist_cres", c) + f("perm_cres", c)
                       + f("nutNed_cres_unavailable", c) + f("nutNed_cres_loss_gasRunTot", c))
                lhs = f("nutNed_lhs", c)
                worst_need = max(worst_need, abs(rhs - lhs) / max(1.0, abs(lhs)))
            # NUTNED_ per group: CAPRI's group need against the crops' own need summed (the multiplier and the soil and
            # yield factors aside, which the model's need multiplier takes per region)
            gl, gs = {}, {}
            for c in lev:
                g_ = ngrp(c)
                gl[g_] = gl.get(g_, 0.0) + f("nutNed_lhs", c)
                gs[g_] = gs.get(g_, 0.0) + lev[c] * v.get((r, "", c, col), 0.0) / 1000.0
            tl, ts = sum(gl.values()), sum(gs.values())
            if tl > 0 and ts > 0:
                for g_ in gl:
                    if gl[g_] > 0.01 * tl:
                        e_ = abs(gs[g_] / ts - gl[g_] / tl) / (gl[g_] / tl)
                        worst_grp = max(worst_grp, e_); grp_err.append(e_)
            # pools: ManureNPK_ (manure applied = excreted - losses - net exports) and fertDistMine_
            man = v.get((r, "", "EXCRET", col), 0.0) - v.get((r, "", "MTRADE", col), 0.0) \
                - (v.get((r, "", "GASANI", col), 0.0) + v.get((r, "", "RUNANI", col), 0.0) if col == "NITF" else 0.0)
            if (r, "", "EXCRET", col) in v:
                worst_man = max(worst_man, abs(man - tot["fertDist_excr"]) / max(1.0, abs(man)))
            if (r, "", "NETF", col) in v:
                worst_min = max(worst_min, abs(v[(r, "", "NETF", col)] - tot["fertDist_mine"]) / max(1.0, tot["fertDist_mine"]))
            mine, excr = tot["fertDist_mine"], tot["fertDist_excr"]
            cres, own = tot["fertDist_cres"], tot["perm_cres"]
            meff = 1.0 + tot["nutNed_mine_loss_gasRunTot"] / mine if mine > 0 else 1.0
            eav = 1.0 + tot["nutNed_excr_unavailable"] / excr if excr > 0 else float("nan")
            cav = 1.0 + (tot["nutNed_cres_unavailable"] + tot["nutNed_cres_loss_gasRunTot"]) / (cres + own) \
                if (cres + own) > 0 else float("nan")
            # the arable residue pool (fertDistCres_ rhs): per crop, levl x the crop's residue output. CAPRI's
            # residue item (NCRD/PCRD/KCRD) is taken as each non-permanent crop's share of the pool; scaled so the
            # crops add up to the pool CAPRI distributes
            pool_raw = {c: lev[c] * v.get((r, "", c, CRD[col]), 0.0) / 1000.0 for c in lev if ngrp(c) not in PERM_NGRP}
            sraw = sum(pool_raw.values())
            kpool = cres / sraw if sraw > 0 else 0.0
            rrow.append(dict(capri_region=r, level="nuts0" if r in nuts0 else "ru", nutrient=nut, mine_eff=meff,
                             excr_avail=eav, cres_avail=cav, uvag_eur_t=v.get((r, "", "UVAG", col), float("nan")),
                             mine_kt=mine, excr_kt=excr, pool_kt=cres, own_kt=own, need_kt=tot["nutNed_lhs"],
                             land_kha=land, pool_scale=kpool))
            # model crops
            agg = {}
            for c, x in lev.items():
                mc = rev.get(c, c)
                d = agg.setdefault(mc, dict(levl=0.0, need=0.0, pool=0.0, own=0.0, mine=0.0, main=0.0, straw=0.0))
                d["levl"] += x
                # the parts of the need that follow yields (fert/fertned.gms, CropResi_IDEAG_NG off as in capmod):
                # need = MIN(cap, MAX(15, O_HP x need per t of main output + STRA x straw content)); O_HP moves with
                # the main output's yield (capmod/define_inputs.gms after shift_yields and supply/endog_yields.gms),
                # STRA with scenario yield shifts only (endog_yields.gms leaves it). At a bound neither moves
                Dc = v.get((r, "", c, col), 0.0)
                Sc = v.get((r, "", c, "STRA"), 0.0) / 1000.0 * stra_c[col]
                cap_ = maxf[col] * (2.0 if c in dbl else 1.0)
                if Dc > 0:
                    n_crop += 1
                    if Dc <= floor_ + 1e-6 or Dc >= cap_ - 1e-6:
                        n_bound += 1
                    else:
                        d["main"] += x * max(Dc - Sc, 0.0) / 1000.0
                        d["straw"] += x * min(Sc, Dc) / 1000.0
                # the crop's own need (NITF/PHOF/POTF per ha, net of fixation): CAPRI's nutNed_lhs per crop is its
                # group's need spread by area (GRAE and GRAI, fallow and the arable crops of its group get the same per
                # ha); NUTNED_ sums levl x need over the group's crops
                d["need"] += x * v.get((r, "", c, col), 0.0) / 1000.0
                d["pool"] += pool_raw.get(c, 0.0) * kpool
                d["own"] += f("perm_cres", c)
                d["mine"] += f("fertDist_mine", c)
            # CAPRI's two grassland activities on their own as well (the model's grassland split column moves area
            # from GRAI to GRAE; NUTNED_ takes each one's need)
            for gc in ("GRAE", "GRAI"):
                if gc in lev:
                    Dg = v.get((r, "", gc, col), 0.0)
                    bnd = Dg <= floor_ + 1e-6 or Dg >= maxf[col] * (2.0 if gc in dbl else 1.0) - 1e-6
                    agg["_" + gc] = dict(levl=lev[gc], need=lev[gc] * Dg / 1000.0, pool=0.0,
                                         own=f("perm_cres", gc),
                                         mine=f("fertDist_mine", gc),
                                         main=0.0 if bnd else lev[gc] * Dg / 1000.0, straw=0.0)
            for mc, d in agg.items():
                mc = mc.lstrip("_")
                L = d["levl"]
                crow.append(dict(capri_region=r, model_crop=mc, nutrient=nut, levl_kha=L,
                                 need_kg_ha=1000.0 * d["need"] / L, pool_kg_ha=1000.0 * d["pool"] / L,
                                 own_kg_ha=1000.0 * d["own"] / L, mine_kg_ha=1000.0 * d["mine"] / L,
                                 main_share=d["main"] / d["need"] if d["need"] > 0 else 1.0,
                                 straw_share=d["straw"] / d["need"] if d["need"] > 0 else 0.0))
            # priors per crop group (posterior mode per ha of CAPRI's 2030 run, accuracy 1)
            garea = {}
            for c, x in lev.items():
                garea[ngrp(c)] = garea.get(ngrp(c), 0.0) + x
            for g in NGRPS:
                A = garea.get(g, 0.0)
                if A <= 0:
                    continue
                cs = [c for c in lev if ngrp(c) == g]
                fl = lambda s: sum(f(f"fertDist_{s}", c) for c in cs) * 1000.0 / A
                mi, ex, cr = fl("mine"), fl("excr"), (0.0 if g in PERM_NGRP else fl("cres"))
                if mi + ex + cr <= 0:
                    continue
                prow.append(dict(capri_region=r, level="nuts0" if r in nuts0 else "ru", nutrient=nut, ngrp=g,
                                 perm=int(g in PERM_NGRP), area_kha=A, mine_kg_ha=mi, excr_kg_ha=ex, cres_kg_ha=cr,
                                 accuracy=1.0))
    print(f"crop need at fertned.gms's floor or cap: {n_bound} of {n_crop} crop x region x nutrient")
    print(f"NUTNED_ identity per crop: worst relative residual {worst_need:.2e}")
    print(f"group need from the crops' own need (sum levl x NITF) against CAPRI's group need: worst {worst_grp:.2e}, "
          f"median {np.median(grp_err) if grp_err else float('nan'):.2e}")
    print(f"ManureNPK_ (EXCRET - GASANI - RUNANI - MTRADE = sum of manure flows): worst {worst_man:.2e}")
    print(f"fertDistMine_ (NETF = sum of mineral flows): worst {worst_min:.2e}")
    cdf = pd.DataFrame(crow).sort_values(["capri_region", "model_crop", "nutrient"])
    rdf = pd.DataFrame(rrow).sort_values(["capri_region", "nutrient"])
    pdf = pd.DataFrame(prow).sort_values(["capri_region", "nutrient", "ngrp"])
    cdf.to_csv(out / "npk_crop_coefs_2030.csv", index=False)
    rdf.to_csv(out / "npk_region_2030.csv", index=False)
    pdf.to_csv(out / "fert_dist_priors_npk_2030.csv", index=False)
    print(f"npk_crop_coefs_2030.csv {len(cdf)} rows; npk_region_2030.csv {len(rdf)} rows; "
          f"fert_dist_priors_npk_2030.csv {len(pdf)} rows")
    for nut in ("N", "P", "K"):
        q = rdf[rdf.nutrient == nut]
        print(f"  {nut}: mineral efficiency median {q.mine_eff.median():.3f}, manure availability median "
              f"{q.excr_avail.median():.3f}, residue availability median {q.cres_avail.median():.3f}, "
              f"pool scale median {q.pool_scale.median():.3f}, price median {q.uvag_eur_t.median():.0f} EUR/t")
    # the N priors must be those of fert_dist_priors_2030.csv
    old = _read_csv(ENV / "fert_dist_priors_2030.csv")
    m = pdf[pdf.nutrient == "N"].merge(old, on=["capri_region", "ngrp"], suffixes=("", "_old"))
    d = max((m[c] - m[c + "_old"]).abs().max() for c in ("mine_kg_ha", "excr_kg_ha", "cres_kg_ha"))
    print(f"N priors against fert_dist_priors_2030.csv: {len(m)} rows, largest difference {d:.2e} kg/ha")
    # manure P and K per model head (CAPRI 2017 regional totals / the model's herds)
    if a.capreg_dir.exists():
        import build_livestock_output_coef as B
        for item, name in (("MANP", "livestock_manure_p_coef.csv"), ("MANK", "livestock_manure_k_coef.csv")):
            t = B.build(a.capreg_dir, item)
            t.to_csv(out / name)
            print(f"{name}: {t.shape[0]} regions x {t.shape[1]} animals")
    else:
        print(f"CAPREG dumps not at {a.capreg_dir}: manure P/K per head not rebuilt")


if __name__ == "__main__":
    main()
