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

Outputs (capri_data/baselines/capri_greendeal_ref/1730/environment/; the two livestock_manure_*_coef.csv, 2017 values, in capri_data/2017/environment/):
  npk_crop_coefs_2030.csv   capri_region, model_crop, nutrient (N, P, K), need_kg_ha (the crop's own NITF/PHOF/POTF),
                            pool_kg_ha (contribution to the
                            arable residue pool, fertDistCres_: levl x DATA(crop, MANN/MANP/MANK), scaled to CAPRI's pool;
                            non-permanent crops; until 16 November 2026 from NCRD/PCRD/KCRD, KNOWN_ISSUES K163), own_kg_ha (permanent crops' own
                            residues: CAPRI's DATA(R, crop, MANN/MANP/MANK, "Y") of each crop, the term NUTNED_ adds for
                            PERM_NGRP, supply_model.gms; until 16 November 2026 the dump's perm_cres per crop, which is
                            the group's total spread by area: GRAE and GRAI had the same value, KNOWN_ISSUES K162),
                            mine_kg_ha (CAPRI's mineral flow), levl_kha; CAPRI crops pooled into
                            the model's crops by area (CORN = MAIZ, WINE = TWIN; GRAE and GRAI the model's own
                            since 7 November 2026). Until 20 November 2026 also main_share and straw_share, the parts
                            of the need that follow the main output's yield and the straw yield, from the reported need
                            (net of fixation, KNOWN_ISSUES K191) and envind/gascoeff.gms's straw content: the need's
                            yield factor now reruns fertned.gms on CAPRI's simulation data (capri_crop_fertned_parts_
                            2030.csv, tools/build/build_capri_crop_n_coefs.py; capri_mod/fert/npk.py need_yield_factor;
                            KNOWN_ISSUES K189)
  npk_region_2030.csv       capri_region, nutrient, mine_eff (1 + loss / mineral), excr_avail (1 + unavailable /
                            manure), cres_avail (1 + (unavailable + loss) / (pooled + own residues)), uvag_eur_t (CAPRI's
                            2030 unit value of NITF/PHOF/POTF over its inflation to 2030: the model's 2017 money,
                            KNOWN_ISSUES K108), mine_kt, excr_kt, pool_kt, own_kt, need_kt, land_kha
  fert_dist_priors_npk_2030.csv  as fert_dist_priors_2030.csv with a nutrient column (N, P, K): CAPRI's posterior
                            mode per ha of each crop group and source, accuracy 1 (tools/build/build_fert_dist_priors.py)
  manure_npk_applied_share_2030.csv  capri_region, nutrient (N, P, K), excret_kt, mtrade_kt, applied_share: CAPRI's
                            manure applied in the region per unit excreted, 1 - MTRADE / EXCRET (applied_share())
  livestock_manure_p_coef.csv, livestock_manure_k_coef.csv   manure P2O5 and K2O per model head (kg), CAPRI's 2017
                            regional total (MANP, MANK) / the model's herd, as livestock_manure_n_coef.csv
                            (tools/build/build_livestock_output_coef.py), from the CAPREG dumps (--capreg-dir)

    python tools/build/build_npk_balance_2030.py [--dump res_2_1730greendeal_refdefaulta.zip] [--capreg-dir DIR]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import functools as _ft
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from _grep import grep  # noqa: E402  (grep -E in Python: any system)
from paths import EXPORTS, SOURCES  # noqa: E402  (CAPRI's material outside the repository)
from _sources_io import read_source, source_records, write_source  # noqa: E402  (capri_data/sources: Parquet)
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "environment"
ENV_BASE = ROOT / "capri_data" / "2017" / "environment"   # the files without a year in their name (DATA_LAYOUT (b))
SRC = ROOT / "capri_data" / "sources" / "raw" / "capri" / "results" / "res_2_1730greendeal_refdefaulta" / "npk_dataout_2030.parquet"
sys.path[:0] = [str(ROOT / "tools" / _d) for _d in ("lib", "build", "run", "check")]
from build_fert_dist_priors import GROUP, PERM_NGRP, NGRPS, ngrp  # noqa: E402

NUTS = {"NITF": "N", "PHOF": "P", "POTF": "K"}
#: the permanent crops' own residue (and, for N, deposition) output per ha in NUTNED_ (FOUT_T_N: MANN.NITF, MANP.PHOF,
#: MANK.POTF; global/fromimpact/sets.gms l. 2529-2530)
MANX = {"NITF": "MANN", "PHOF": "MANP", "POTF": "MANK"}
#: CAPRI's crop activities (sets.gms MCACT: MECACT + MFCACT), the elementary rows of the dump; the dump's other crop
#: rows (CERE, OILS, ARAB, PERM, GRAS, SETA, VEGE, WHEA, RAPN, OAFC, ...) are aggregates
ELEM = ("SWHE", "DWHE", "RYEM", "BARL", "OATS", "MAIZ", "OCER", "PARI", "RAPE", "SUNF", "SOYA", "OOIL", "OIND", "NURS",
        "FLOW", "OCRO", "NECR", "MAIF", "ROOF", "OFAR", "GRAE", "GRAI", "PULS", "POTA", "SUGB", "TEXT", "TOBA", "TOMA",
        "OVEG", "APPL", "OFRU", "CITR", "TAGR", "TABO", "TWIN", "OLIV", "FALL", "ISET", "GSET", "TSET", "VSET", "NONF")
#: model crop <- CAPRI crops
MODEL = {"CORN": ("MAIZ",), "WINE": ("TWIN",)}   # (GRAS = GRAE + GRAI until 7 November 2026)
#  (VSET and FALL the model's own since 7 November 2026; before SETA = FALL + VSET + ISET + GSET + TSET; ISET, GSET
#  and TSET have no area in CAPRI's 2017 and 2030 data)
FLOWS = ("fertDist_mine", "fertDist_excr", "fertDist_cres", "perm_cres", "nutNed_mine_loss_gasRunTot",
         "nutNed_cres_loss_gasRunTot", "nutNed_excr_unavailable", "nutNed_cres_unavailable", "nutNed_lhs")
BAL = ("EXCRET", "MTRADE", "GASANI", "RUNANI", "NETF", "UVAG")
GMS = ROOT / "capri_data" / "sources" / "raw" / "capri" / "gams"


def _gms_csv(name):
    """A statement of CAPRI's GAMS code converted to CSV (capri_data/sources/raw/capri/gams,
    tools/build/convert_sources.py)."""
    return read_source(GMS / name, dtype=str, keep_default_na=False)


def extract(dump: Path) -> pd.DataFrame:
    cr = "|".join(ELEM + ("AGGT",))
    nu = "NITF|PHOF|POTF"
    pat = (rf"^'[A-Z0-9]+'\.'({'|'.join(FLOWS)})'\.'({cr})'\.'({nu})'\.'2030'"
           rf"|^'[A-Z0-9]+'\.''\.'({'|'.join(ELEM)})'\.'(LEVL|{nu}|NCRD|PCRD|KCRD|STRA|MANN|MANP|MANK)'\.'2030'"
           rf"|^'[A-Z0-9]+'\.''\.'({'|'.join(BAL)})'\.'({nu})'\.'2030'"
           rf"|^'[A-Z0-9]+'\.''\.'UAAR'\.'LEVL'\.'2030'")
    out = grep(pat, str(dump))
    rx = re.compile(r"^'([A-Z0-9]+)'\.'([^']*)'\.'([A-Za-z]+)'\.'([A-Z]+)'\.'2030'\s+([-\d.Ee+]+)")
    rows = []
    for line in out.splitlines():
        m = rx.match(line)
        if m:
            r, item, row, col, v = m.groups()
            rows.append(dict(region=r, item=item, row=row, col=col, value=float(v)))
    return pd.DataFrame(rows)


def applied_share(src: pd.DataFrame) -> pd.DataFrame:
    """CAPRI's 2030 manure N, P2O5 and K2O applied in the region per unit excreted, 1 - MTRADE / EXCRET (ManureNPK_,
    manExportOrAppl_: the region's net manure exports, MTRADE, leave its balance), for every region with EXCRET > 0:
    capri_region, nutrient (N, P, K), excret_kt, mtrade_kt (0 where CAPRI reports none), applied_share (at least 0).
    The model's fertilisation block (capri_mod/supply/fertilisation.py) and P balance (capri_mod/environmental/
    phosphorus.py) read it; until 3 November 2026 each computed it from the extract under capri_data/sources."""
    s = src[(src.item == "") & (src.row.isin(["EXCRET", "MTRADE"]))]
    v = {(t.region, t.row, t.col): float(t.value) for t in s.itertuples(index=False)}
    rows = []
    for (r, row, col), x in v.items():
        if row == "EXCRET" and x > 0:
            m = v.get((r, "MTRADE", col), 0.0)
            rows.append({"capri_region": r, "nutrient": {"PHOF": "P", "POTF": "K", "NITF": "N"}[col],
                         "excret_kt": x, "mtrade_kt": m, "applied_share": max(0.0, 1.0 - m / x)})
    return pd.DataFrame(rows).sort_values(["capri_region", "nutrient"])


def main():
    sys.path.insert(0, str(ROOT / "tools" / "lib"))
    import _money
    money = _money.deflator(2030)
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, default=EXPORTS / "res_2_1730greendeal_refdefaulta.zip")
    ap.add_argument("--capreg-dir", type=Path, default=SOURCES / "capreg")
    ap.add_argument("--out-dir", type=Path, default=ENV, help="where to write the outputs (default: the data folder)")
    a = ap.parse_args()
    out = a.out_dir
    out.mkdir(parents=True, exist_ok=True)
    if a.dump.exists():
        src = extract(a.dump)
        SRC.parent.mkdir(parents=True, exist_ok=True)
        write_source(src, SRC, index=False)
        print(f"extracted {len(src)} rows -> {SRC.relative_to(ROOT)}")
    src = read_source(SRC, keep_default_na=False)
    applied_share(src).to_csv(out / "manure_npk_applied_share_2030.csv", index=False)
    v = {(r.region, r.item, r.row, r.col): r.value for r in src.itertuples(index=False)}
    regions = sorted({r for r in src.region if len(r) == 8})
    nuts0 = {r for r in regions if r.endswith("000000") and
             any(x.startswith(r[:2]) and not x.endswith("000000") for x in regions)}
    rev = {c: mc for mc, cs in MODEL.items() for c in cs}
    crow, rrow, prow = [], [], []
    worst_need = worst_man = worst_min = worst_grp = worst_own = 0.0
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
            # the crops' own residues (levl x MANx) add up to CAPRI's reported total per permanent group (the split
            # between the group's crops is all that K162 changes)
            for g_ in PERM_NGRP:
                o_rep = sum(f("perm_cres", c) for c in lev if ngrp(c) == g_)
                o_dat = sum(lev[c] * v.get((r, "", c, MANX[col]), 0.0) / 1000.0 for c in lev if ngrp(c) == g_)
                if o_rep > 1e-6:
                    worst_own = max(worst_own, abs(o_dat - o_rep) / o_rep)
            mine, excr = tot["fertDist_mine"], tot["fertDist_excr"]
            cres, own = tot["fertDist_cres"], tot["perm_cres"]
            meff = 1.0 + tot["nutNed_mine_loss_gasRunTot"] / mine if mine > 0 else 1.0
            eav = 1.0 + tot["nutNed_excr_unavailable"] / excr if excr > 0 else float("nan")
            cav = 1.0 + (tot["nutNed_cres_unavailable"] + tot["nutNed_cres_loss_gasRunTot"]) / (cres + own) \
                if (cres + own) > 0 else float("nan")
            # the arable residue pool (fertDistCres_ rhs, supply_model.gms): per non-permanent crop, levl x DATA(crop,
            # MANN/MANP/MANK) (FOUT_T_N's output for the nutrient), scaled so the crops add up to the pool CAPRI
            # distributes. (Until 16 November 2026 the crops' NCRD/PCRD/KCRD, "from crop residues and atmospheric
            # deposition": another spread over the crops; KNOWN_ISSUES K163)
            pool_raw = {c: lev[c] * v.get((r, "", c, MANX[col]), 0.0) / 1000.0 for c in lev if ngrp(c) not in PERM_NGRP}
            sraw = sum(pool_raw.values())
            kpool = cres / sraw if sraw > 0 else 0.0
            rrow.append(dict(capri_region=r, level="nuts0" if r in nuts0 else "ru", nutrient=nut, mine_eff=meff,
                             excr_avail=eav, cres_avail=cav, uvag_eur_t=v.get((r, "", "UVAG", col), float("nan")) / money,
                             mine_kt=mine, excr_kt=excr, pool_kt=cres, own_kt=own, need_kt=tot["nutNed_lhs"],
                             land_kha=land, pool_scale=kpool))
            # model crops
            agg = {}
            for c, x in lev.items():
                mc = rev.get(c, c)
                d = agg.setdefault(mc, dict(levl=0.0, need=0.0, pool=0.0, own=0.0, mine=0.0))
                d["levl"] += x
                # the crop's own need (NITF/PHOF/POTF per ha, net of fixation): CAPRI's nutNed_lhs per crop is its
                # group's need spread by area (GRAE and GRAI, fallow and the arable crops of its group get the same per
                # ha); NUTNED_ sums levl x need over the group's crops
                d["need"] += x * v.get((r, "", c, col), 0.0) / 1000.0
                d["pool"] += pool_raw.get(c, 0.0) * kpool
                # the permanent crops' own residues per crop, CAPRI's NUTNED_ term: levl x DATA(crop, MANx) (the dump's
                # perm_cres per crop is the group's total spread by area; K162)
                d["own"] += (x * v.get((r, "", c, MANX[col]), 0.0) / 1000.0) if ngrp(c) in PERM_NGRP else f("perm_cres", c)
                d["mine"] += f("fertDist_mine", c)
            # (GRAE and GRAI on their own rows here too until 7 November 2026: the model's crops since)
            for mc, d in agg.items():
                mc = mc.lstrip("_")
                L = d["levl"]
                crow.append(dict(capri_region=r, model_crop=mc, nutrient=nut, levl_kha=L,
                                 need_kg_ha=1000.0 * d["need"] / L, pool_kg_ha=1000.0 * d["pool"] / L,
                                 own_kg_ha=1000.0 * d["own"] / L, mine_kg_ha=1000.0 * d["mine"] / L))
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
    print(f"NUTNED_ identity per crop: worst relative residual {worst_need:.2e}")
    print(f"group need from the crops' own need (sum levl x NITF) against CAPRI's group need: worst {worst_grp:.2e}, "
          f"median {np.median(grp_err) if grp_err else float('nan'):.2e}")
    print(f"ManureNPK_ (EXCRET - GASANI - RUNANI - MTRADE = sum of manure flows): worst {worst_man:.2e}")
    print(f"permanent groups' own residues, sum of levl x MANx against CAPRI's perm_cres: worst {worst_own:.2e}")
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
        out_base = ENV_BASE if a.out_dir == ENV else out
        for item, name in (("MANP", "livestock_manure_p_coef.csv"), ("MANK", "livestock_manure_k_coef.csv")):
            t = B.build(a.capreg_dir, item)
            t.to_csv(out_base / name)
            print(f"{name}: {t.shape[0]} regions x {t.shape[1]} animals")
    else:
        print(f"CAPREG dumps not at {a.capreg_dir}: manure P/K per head not rebuilt")


if __name__ == "__main__":
    main()
