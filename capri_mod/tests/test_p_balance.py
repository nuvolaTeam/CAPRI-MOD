"""CAPRI's gross phosphate balance in the environmental accounts (reports/calc_nbalance.gms with FNUT = PHOF;
capri_mod/environmental/p_balance.py, EnvironmentalModule.compute_phosphorus_balance, tools/build/build_p_balance.py,
docs/P_BALANCE.md). Units: t P2O5 in the accounts, 1000 t P2O5 in CAPRI's tables.

The formula tests use CAPRI's own levels and items (its Green Deal 2030 reference and the same run with endogenous
technologies at their initial shares); the level test compares the accounts at the model's base data with CAPRI's 2030
reference; the slow tests solve regional models."""
import copy
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "capri_data"
SRC = DATA_DIR / "sources" / "capri_res"
REGIONS = ("DE110000", "NL220000", "PL220000", "DK000000")
#: CAPRI's elementary activities (tools/build/build_p_balance.py)
CAPRI_CROPS = ("SWHE", "DWHE", "RYEM", "BARL", "OATS", "MAIZ", "OCER", "PARI", "RAPE", "SUNF", "SOYA", "OOIL", "OIND",
               "NURS", "FLOW", "OCRO", "NECR", "MAIF", "ROOF", "OFAR", "GRAE", "GRAI", "PULS", "POTA", "SUGB", "TEXT",
               "TOBA", "TOMA", "OVEG", "APPL", "OFRU", "CITR", "TAGR", "TABO", "TWIN", "OLIV", "FALL", "ISET", "GSET",
               "TSET", "VSET", "NONF")
CAPRI_ANIMALS = ("DCOL", "DCOH", "BULL", "BULH", "HEIL", "HEIH", "HEIR", "CAFF", "CAFR", "CAMF", "CAMR", "SCOW", "SHGM",
                 "SHGF", "PIGF", "SOWS", "HENS", "POUF")
EU27 = ("AT", "BL", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IR", "IT", "LT", "LV", "MT",
        "NL", "PL", "PT", "RO", "SE", "SI", "SK")


def _read(f):
    d = defaultdict(dict)
    for r in csv.DictReader(open(f)):
        d[r["region"]][(r["col"], r["row"])] = float(r["value"])
    return d


@pytest.fixture(scope="module")
def ini():
    return _read(SRC / "gd2030_endotech_ini_pbalance.csv")


@pytest.fixture(scope="module")
def ref():
    return _read(SRC / "gd2030_ref_pbalance.csv")


@pytest.fixture(scope="module")
def data():
    from capri_mod.data.loaders import load_all_data
    return load_all_data(DATA_DIR)


def test_balance_identities_are_capris(ini, ref):
    """IMPORT, SURTOT, SURSOI from CAPRI's items with p_balance.balance reproduce CAPRI's own (calc_nbalance.gms
    l. 238-310), in every region of both runs."""
    from capri_mod.environmental.p_balance import balance
    n = 0
    for run in (ini, ref):
        for reg, x in run.items():
            if ("SURTOT", "PHOF") not in x:
                continue
            it = lambda k: x.get((k, "PHOF"), 0.0)
            b = balance(it("EXCRET"), it("MTRADE"), it("MINFER"), it("CRESID"), it("EXPPRD"), it("RUNANI"))
            for k in ("IMPORT", "SURTOT", "SURSOI"):
                assert abs(b[k] - it(k)) < 1e-9 * max(1.0, abs(it(k))), (reg, k, b[k], it(k))
            assert abs(it("MINFER") - it("NETF")) < 1e-9 * max(1.0, it("NETF"))
            n += 1
    assert n > 500


def test_p_items_follow_capri(ini):
    """With CAPRI's own levels (Green Deal 2030 reference, endogenous technologies at their initial shares) the items'
    formulas give CAPRI's items for DE11, NL22, PL22 and DK: EXCRET = sum LEVL x MANP, CRESID = sum LEVL x PCRD,
    EXPPRD = sum LEVL x PRET (retention, not the managed need PHOF), RUNANI = sum LEVL x MANP x RunTot with the runoff
    share from capri-mod's loss cascade (n_cascade.activity_losses) at CAPRI's option shares and winter cover."""
    from capri_mod.supply import n_cascade as nc
    R = defaultdict(dict)
    for r in csv.DictReader(open(DATA_DIR / "validation" / "n_cascade_capri_gd2030.csv")):
        R[(r["region"], r["key"])][(r["col"], r["row"])] = float(r["value"])
    F, _, _ = nc.load()
    for reg in REGIONS:
        x = ini[reg]
        it = lambda k: x[(k, "PHOF")]
        shr = R[(reg, "SHARE")]
        wc = shr.get(("CATC", "WinterCov"), 0.0)
        ex = sum(x.get((a, "LEVL"), 0.0) * x.get((a, "MANP"), 0.0) for a in CAPRI_ANIMALS) / 1000.0
        cr = sum(x.get((c, "LEVL"), 0.0) * x.get((c, "PCRD"), 0.0) for c in CAPRI_CROPS) / 1000.0
        ep = sum(x.get((c, "LEVL"), 0.0) * x.get((c, "PRET"), 0.0) for c in CAPRI_CROPS) / 1000.0
        ru = 0.0
        for a in CAPRI_ANIMALS:
            if x.get((a, "LEVL"), 0.0) > 0 and (reg, a) in F:
                L = nc.activity_losses(reg, a, {t: v for (aa, t), v in shr.items() if aa == a}, winter_cover=wc)
                ru += x[(a, "LEVL")] * x.get((a, "MANP"), 0.0) * L[("N", "RunTot")] / 1000.0
        assert abs(ex / it("EXCRET") - 1.0) < 1e-9, (reg, ex, it("EXCRET"))
        assert abs(cr / it("CRESID") - 1.0) < 1e-9, (reg, cr, it("CRESID"))
        assert abs(ep / it("EXPPRD") - 1.0) < 1e-3, (reg, ep, it("EXPPRD"))
        assert abs(ru / it("RUNANI") - 1.0) < 1e-6, (reg, ru, it("RUNANI"))


def test_crop_coefs_keep_capris_totals(ref):
    """p_balance_crop_coefs_2030.csv pools CAPRI's crops into the model's crops by area: at CAPRI's own areas the pooled
    retention and residue output give CAPRI's EXPPRD and CRESID of its 2030 reference."""
    t = pd.read_csv(DATA_DIR / "2017" / "environment" / "p_balance_crop_coefs_2030.csv")
    for reg in REGIONS:
        d = t[(t.capri_region == reg) & ~t.model_crop.isin(["GRAE", "GRAI"])]
        ep = float((d.levl_kha * d.pret_kg_ha).sum()) / 1000.0
        cr = float((d.levl_kha * d.pcrd_kg_ha).sum()) / 1000.0
        assert abs(ep / ref[reg][("EXPPRD", "PHOF")] - 1.0) < 1e-6, reg
        assert abs(cr / ref[reg][("CRESID", "PHOF")] - 1.0) < 1e-6, reg
        g = t[(t.capri_region == reg) & t.model_crop.isin(["GRAE", "GRAI", "GRAS"])].set_index("model_crop")
        if "GRAE" in g.index and "GRAI" in g.index:
            lv = g.at["GRAE", "levl_kha"] + g.at["GRAI", "levl_kha"]
            assert abs(lv - g.at["GRAS", "levl_kha"]) < 1e-6
            assert abs((g.at["GRAE", "levl_kha"] * g.at["GRAE", "pret_kg_ha"] + g.at["GRAI", "levl_kha"]
                        * g.at["GRAI", "pret_kg_ha"]) / lv - g.at["GRAS", "pret_kg_ha"]) < 1e-6


def test_nutned_mineral_closes_at_base():
    """CAPRI's NUTNED_ for P summed over the crop groups gives the base purchases at the base levels (kappa closes it
    there) and falls with the manure applied by g0 / eff per t."""
    from capri_mod.environmental.p_balance import nutned_mineral
    from capri_mod.fert.npk import NPKData
    D = NPKData.get()
    cr = "DE110000"
    crops = ("SWHE", "BARL", "RAPE", "GRAS", "APPL")
    col = lambda k: {c: D.crop_coef(cr, "P", c, k) for c in crops}
    need, own, pool, mine0 = col("need_kg_ha"), col("own_kg_ha"), col("pool_kg_ha"), col("mine_kg_ha")
    xb = {"SWHE": 90.0, "BARL": 55.0, "RAPE": 40.0, "GRAS": 137.0, "APPL": 0.7}
    sq = {c: 1.0 for c in crops}
    E0 = 5000.0
    m = nutned_mineral(D, cr, need, own, own, pool, mine0, xb, xb, sq, E0, E0)
    assert abs(m - sum(mine0[c] * xb[c] for c in crops)) < 1e-6 * m
    R = D.region(cr, "P")
    m2 = nutned_mineral(D, cr, need, own, own, pool, mine0, xb, xb, sq, E0, E0 + 100.0)
    assert abs((m - m2) - 100.0 * float(R.excr_avail) / float(R.mine_eff)) < 1e-6


def test_p_accounts_at_the_base_against_capri(data, ref):
    """The accounts at the model's base data (2017 levels, CAPRI's 2030 coefficients; mineral P2O5 = the fertilisation
    block's base purchases) against CAPRI's 2030 reference: the EU items per ha of UAA within 10% (measured: excretion
    27.8 / 27.6, mineral 15.6 / 15.6, residues 24.0 / 24.1, removal 53.1 / 53.4, surplus 14.4 / 13.9 kg P2O5/ha) and
    the regional surplus per ha correlated above 0.95 (measured 0.99, 213 NUTS-2 regions). Level differences (herds,
    areas) remain: excretion in DE11 19.3 kt against CAPRI's 15.7. The runoff is at CAPRI's initial option shares (its
    'ini' run's), 1.6 kg/ha against the reference's 1.4 (ini 1.5)."""
    from capri_mod.environmental.environmental_module import EnvironmentalModule
    env = EnvironmentalModule(data)
    out = {}
    for reg in data["areas"].index:
        if reg.startswith("NO"):
            continue
        acts = dict(data["areas"].loc[reg])
        acts.update(dict(data["animal_numbers"].loc[reg]))
        out[reg] = env.compute_phosphorus_balance(acts, data["yields"].loc[reg], reg)
    for reg, b in out.items():
        assert all(np.isfinite(b[k]) for k in ("EXCRET", "MINFER", "CRESID", "EXPPRD", "RUNANI", "SURTOT")), reg
        assert b["MINFER"] >= 0 and b["RUNANI"] >= 0 and b["mineral_source"] == "nutned"
        assert abs(b["SURSOI"] - (b["SURTOT"] - b["RUNANI"])) < 1e-6
    uaa_m = sum(float(data["areas"].loc[r].sum()) for r in out)
    uaa_c = sum(ref[m + "000000"][("UAAR", "LEVL")] for m in EU27)
    for k in ("EXCRET", "MINFER", "CRESID", "EXPPRD", "SURTOT"):
        mo = sum(b[k] for b in out.values()) / uaa_m
        ca = sum(ref[m + "000000"].get((k, "PHOF"), 0.0) for m in EU27) * 1000.0 / uaa_c
        assert abs(mo / ca - 1.0) < 0.10, (k, mo, ca)
    from capri_mod.fert.inner_fert_dist import InnerFertDist
    inner = InnerFertDist()
    xs, ys = [], []
    for reg, b in out.items():
        c8 = inner._map.get(reg)
        a = float(data["areas"].loc[reg].sum())
        if a > 0 and c8 in ref and not c8.endswith("000000") and ref[c8].get(("UAAR", "LEVL"), 0.0) > 0:
            xs.append(b["SURTOT"] / a)
            ys.append(ref[c8][("SURTOT", "PHOF")] / ref[c8][("UAAR", "LEVL")] * 1000.0)
    assert len(xs) > 200 and np.corrcoef(xs, ys)[0, 1] > 0.95


def test_flatten_outputs_exports_eu_p_totals():
    """io_results.flatten_outputs: EU totals (Norway left out) of the P items and the organic area."""
    from capri_mod.io_results import flatten_outputs
    env = pd.DataFrame({"p_surplus": [1.0, 2.0, 40.0], "p_input": [3.0, 4.0, 50.0], "p_runoff": [0.1, 0.2, 9.0],
                        "organic_area": [5.0, 6.0, 7.0]}, index=["DE11", "NL22", "NO01"])
    f = flatten_outputs({"environmental": env})
    assert f["env_EU_p_surplus"] == 3.0 and f["env_EU_p_input"] == 7.0 and f["env_EU_organic_area"] == 11.0
    assert abs(f["env_EU_p_runoff"] - 0.3) < 1e-12


def _realised_yields(m, reg, sr):
    y = m.data["yields"].loc[reg].copy()
    for c in sr.activities.index:
        if c in sr.gross_output.index and float(sr.activities[c]) > 1e-9 and float(sr.gross_output[c]) > 0:
            y[c] = float(sr.gross_output[c]) / float(sr.activities[c])
    return y


@pytest.mark.slow
def test_p_accounts_from_the_nlp_solution():
    """NLP form, baseline and Farm-to-Fork (one market iteration, DE11 and NL22): mineral P2O5 is the fertilisation
    block's purchase, manure P2O5 applied the sum of its manure flows (MTRADE = EXCRET - applied); CAPRI's NUTNED_ for
    P summed over the groups at the solution gives the same purchase; the organic area is the
    crops' area times their converted share (0 at the baseline)."""
    from capri_mod.model import CAPRIModel
    from capri_mod.policy.greendeal import farm_to_fork_scenario
    m = CAPRIModel(data_dir=str(DATA_DIR), verbose=False)
    for kw in ({"scenario": "BASELINE"}, {"custom_scenario": farm_to_fork_scenario()}):
        res = m.run(regions=["DE11", "NL22"], max_outer_iter=1, **kw)
        env = res["environmental"]
        for reg in ("DE11", "NL22"):
            sr = res["supply"][reg]
            blk = (sr.fert_npk or {}).get("P")
            assert blk is not None, reg
            row = env.loc[reg]
            assert abs(row["p_mineral_input"] - blk["purchase"]) < 1e-6 * max(1.0, blk["purchase"])
            applied = sum(v for (g, s_), v in blk["flows"].items() if s_ == "EXCR")
            assert abs(row["p_manure_excretion"] - row["p_manure_net_export"] - applied) < 1e-6 * applied
            r2 = copy.copy(sr)
            r2.fert_npk = None
            b = m.env_module.compute_phosphorus_balance(sr.activities, _realised_yields(m, reg, sr), reg, r2)
            assert b["mineral_source"] == "nutned"
            assert abs(b["MINFER"] - blk["purchase"]) < 1e-4 * max(1.0, blk["purchase"]), (reg, b["MINFER"])
            oc = getattr(sr, "organic_conv", None) or {}
            org = sum(float(sr.activities.get(c, 0.0)) * (1.0 - v) for c, v in oc.items())
            assert abs(row["organic_area"] - org) < 1e-9
            if "scenario" in kw:
                assert row["organic_area"] == 0.0
            else:
                assert 0.0 < row["organic_area"] < row["uaa_total"]
            assert abs(row["p_surplus"] - (row["p_input"] - row["p_uptake"])) < 1e-6
            assert row["p_runoff"] >= 0.0

