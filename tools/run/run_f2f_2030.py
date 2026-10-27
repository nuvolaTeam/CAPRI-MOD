"""Run the full-EU 2030 Farm-to-Fork scenario (JRC121368 set-up) and save the results.

Baseline and scenario for 2030 through the projection module, with the model's default
settings unless options say otherwise. Saves a pickle read by tools/check/compare_runs.py:
EU27 domestic price changes, activity and output totals (base, scenario), the
environmental tables (base, scenario) and convergence metadata.

Usage: python tools/run/run_f2f_2030.py OUT.pkl [--scenario f2f|greendeal|greendeal2030|carbontax]
                                            [--targets lndscpTarg=0,orgTarg=0,pestRedu=0,surpRedu=0]
                                            [--settings FILE.toml] [--set section.key=value] ...
Any setting of capri_mod/settings/defaults.toml is changed with --set (e.g. --set market.eu_blocks=true,
--set diagnostics.trace_outer=true for the outer-loop trace) or a --settings file.
"""
import os as _os
import sys as _sys
# reproducible runs: the model iterates sets of names in a few places, and Python randomises string hashing per
# process, which changed results by up to ~0.2% between two runs of the same scenario (degenerate regions more).
# A fixed hash seed makes a run repeat exactly (Sprint 9n).
if _os.environ.get("PYTHONHASHSEED") != "0":
    _os.environ["PYTHONHASHSEED"] = "0"
    _os.execv(_sys.executable, [_sys.executable] + _sys.argv)
import argparse
import pickle
import sys
import time
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--regions", default="", help="diagnostics: a comma-separated subset of regions")
    ap.add_argument("--manure-market", action="store_true", help="manure trade on (overrides the scenario)")
    ap.add_argument("--endotech", default="",
                    help="CAPRI endogenous-technology settings for baseline and scenario, e.g. ghgTechMYld=0.2 "
                         "(default: star 3.0's refpol_endotech_all_sup, ghgTechMYld 0, ghgTechFEff 0.1); "
                         "'jrc121368' = the JRC121368-era references (ghgTechMYld 0.2)")
    ap.add_argument("--carbon-tax", type=float, default=None,
                    help="CAPRI's emission tax (ghgTax), EUR/t CO2-eq on the EU regions' emissions inside the supply "
                         "models; with --scenario carbontax the only shock (carbtax50_endotech_*.gms), else added to "
                         "the scenario")
    ap.add_argument("--scenario", default="f2f", choices=("f2f", "greendeal", "greendeal2030", "carbontax"),
                    help="'f2f' (default): Farm-to-Fork with JRC121368's own settings (tiered surplus rule with its "
                         "36%% cap, no manure trade, milk-yield genomics 0.2: policy.greendeal.farm_to_fork_scenario); "
                         "'greendeal': CAPRI star 3.0's Green Deal group as its files set it (surptot.gms: every "
                         "region's surplus/ha cut by surpRedu%%, manure trade on, genomics 0), with --targets values "
                         "(default: the series' full targets lnds10 org25 pest50 surp50 applied in 2030); "
                         "'greendeal2030': CAPRI's own 2030 step of its Green Deal series (lnds8 org18 pest20 "
                         "mine13crp surp30, policy.greendeal.GREENDEAL_2030_TARGETS)")
    ap.add_argument("--pesticide-rule", default="", choices=("", "jrc121368", "star3"),
                    help="yield effect of the pesticide target: 'jrc121368' (10%% at a 50%% cut) or 'star3' (none, "
                         "CAPRI star 3.0's Green Deal group); default: the scenario's (f2f jrc121368, greendeal star3)")
    ap.add_argument("--no-manure-market", action="store_true", help="manure trade off (overrides the scenario)")
    ap.add_argument("--biofuel-markets", action="store_true", help="endogenous biofuel markets on (BIOF_M)")
    ap.add_argument("--biofuel-mandate", type=float, default=None,
                    help="EU and UK blending mandates x this factor (CAPRI change_biof_mandate.gms)")
    ap.add_argument("--no-biofuel-markets", action="store_true",
                    help="biofuel quantities fixed at the reference (CAPRI without BIOF_M; overrides the scenario)")
    ap.add_argument("--surplus-rule", default="", choices=("", "jrc121368", "star3"),
                    help="override the scenario's nutrient-surplus rule")
    ap.add_argument("--mine-redu", default="", choices=("", "00", "20", "10crp", "13crp", "17crp", "20crp"),
                    help="CAPRI's mineral fertiliser reduction (Green Deal mineRedu; minfert_redu_*.gms)")
    ap.add_argument("--targets", default="", help="CAPRI switches to change, e.g. "
                    "'lndscpTarg=0,orgTarg=0,pestRedu=0' for the nitrogen-balance target alone")
    ap.add_argument("--capped-regions", default="",
                    help="sensitivity: regions given JRC121368's 36%% cut instead of the nine highest "
                         "CAPRI baseline surpluses per ha (comma list; '+' prefix adds to the nine)")
    ap.add_argument("--trajectory", default="capri_ref",
                    help="2030 baseline trajectory: capri_ref (CAPRI's 2030 reference, default), captrd (CAPRI's trend "
                         "projection) or a file name in capri_data/trajectories")
    ap.add_argument("--settings", action="append", default=[],
                    help="a TOML settings file (capri_mod/settings/defaults.toml's keys); repeatable, later files win")
    ap.add_argument("--set", action="append", default=[],
                    help="one setting, e.g. --set market.eu_blocks=true (after the files and the flags)")
    ap.add_argument("--base-prices", action="store_true",
                    help="keep 2017 prices in the 2030 baseline (default: CAPRI's 2030 prices in 2017 money)")
    a = ap.parse_args()
    warnings.filterwarnings("ignore")
    # a regional solve whose last IPOPT point is kept (non-optimal, as CAPRI) is always shown
    warnings.filterwarnings("always", message=".*IPOPT's last point kept")
    warnings.filterwarnings("always", message="CAPRI's stop rule not evaluated")
    warnings.filterwarnings("always", message="market supply Hessian not built")
    warnings.filterwarnings("always", message="scenario market supply Hessian not measured")
    warnings.filterwarnings("always", message="bilateral market did not converge")
    warnings.filterwarnings("always", message="CAPRI's crop-group fertiliser allocation")
    sys.path.insert(0, str(ROOT))
    from capri_mod.model import CAPRIModel
    from capri_mod.projection import ProjectionModule, BaselineTrajectory
    from capri_mod.policy.greendeal import greendeal_scenario
    # the run's settings (capri_mod/settings): defaults.toml, then --settings files, then the flags below, then --set
    from capri_mod import settings as _S
    ov = {}
    flag_map = [  # (flag on, setting, value); every other setting: --set or --settings
        (bool(a.capped_regions), "supply.jrc_capped_override", a.capped_regions),
    ]
    for on, k, v in flag_map:
        if on:
            ov[k] = v
    import tomllib as _tl
    for kv in a.set:
        k, v = kv.split("=", 1)
        try:                                           # a TOML value (true, 0.5, [1, 2], "text") ...
            ov[k.strip()] = _tl.loads(f"v = {v.strip()}")["v"]
        except _tl.TOMLDecodeError:                    # ... or a bare word, taken as text
            ov[k.strip()] = v.strip()
    run_settings = _S.load(a.settings, overrides=ov)
    _S.activate(run_settings)
    m = CAPRIModel(data_dir=str(ROOT / "capri_data"), verbose=False,
                   regions=[x for x in a.regions.split(",") if x] or None)
    t0 = time.time()
    # CAPRI simulates from its calibrated 2030 reference (CAPMOD's reference run); the trend projection (CAPTRD) is
    # that calibration's input and stays available (--trajectory captrd)
    _tf = {"capri_ref": "capri_ref_2030.json", "captrd": "captrd_2030.json"}.get(a.trajectory, a.trajectory)
    traj = BaselineTrajectory.from_file(str(ROOT / "capri_data" / "trajectories" / _tf))
    kw = {k: (v if k == "mineRedu" else int(v)) for k, v in (x.split("=") for x in a.targets.split(",") if x)}
    _pdir = None if a.base_prices else str(ROOT / "capri_data" / "trajectories")
    pmod = ProjectionModule(m, traj, capri_prices_dir=_pdir)
    from capri_mod.policy.endotech import JRC121368_ENDOTECH, effective
    _et = (dict(JRC121368_ENDOTECH) if a.endotech.lower() == "jrc121368"
           else {k: float(v) for k, v in (x.split("=") for x in a.endotech.split(",") if x)})
    from capri_mod.policy.greendeal import farm_to_fork_scenario
    if a.scenario == "carbontax":
        from capri_mod.scenarios.scenarios import carbon_tax_scenario
        _scen = carbon_tax_scenario(a.carbon_tax if a.carbon_tax is not None else 50.0)
    elif a.scenario == "f2f" and not kw:
        _scen = farm_to_fork_scenario()
    elif a.scenario == "greendeal2030":
        from capri_mod.policy.greendeal import greendeal_2030_scenario
        _scen = greendeal_2030_scenario(**kw)
    else:
        _scen = greendeal_scenario(**kw) if a.scenario == "greendeal" else farm_to_fork_scenario()
        if a.scenario == "f2f":           # F2F settings with other targets
            _g = greendeal_scenario(**kw, surplus_rule="jrc121368" if kw.get("surpRedu", 50) in (0, 50) else "star3")
            for _f in ("set_aside_requirement", "organic_area_target", "pesticide_reduction", "nutrient_surplus_target",
                       "surplus_rule", "surplus_cut"):
                setattr(_scen, _f, getattr(_g, _f))
    # command-line overrides of the scenario's settings
    if a.surplus_rule:
        _scen.surplus_rule = a.surplus_rule
    if a.pesticide_rule:
        _scen.pesticide_rule = a.pesticide_rule
    if a.manure_market:
        _scen.manure_trade = True
    if a.no_manure_market:
        _scen.manure_trade = False
    if a.biofuel_markets:
        _scen.biofuel_markets = True
    if a.no_biofuel_markets:
        _scen.biofuel_markets = False
    if a.biofuel_mandate is not None:
        _scen.biofuel_mandate = a.biofuel_mandate
    if a.mine_redu:
        _scen.mineral_redu = a.mine_redu
        if _scen.name.startswith("greendeal"):
            _scen.name = _scen.name.replace(_scen.name.split("_mine")[1].split("_")[0], a.mine_redu, 1) \
                if "_mine" in _scen.name else _scen.name
    if a.carbon_tax is not None:
        _scen.carbon_tax = float(a.carbon_tax)
    if a.endotech:
        _scen.endotech = effective(_et)
    _scen.endotech = effective(_scen.endotech)
    res = pmod.run(policy_scenario=_scen, years=[2030])
    b, s = res.baseline[2030], res.scenario[2030]
    _pmm = (getattr(pmod, "_last_projected_model", None) or m).market_module
    db, ds = b["market"].domestic_prices.loc["EU27"], s["market"].domestic_prices.loc["EU27"]

    # the adoption shares below are EU27 shares: Norway's regions (no EU mitigation options, msNoEU) left out (K56)
    sEU = {r_: v_ for r_, v_ in s["supply"].items() if not str(r_).startswith("NO")}
    bEU = {r_: v_ for r_, v_ in b["supply"].items() if not str(r_).startswith("NO")}
    def agg(r, f):
        """EU27 totals of the regional results: Norway's regions (NO..) left out, as in CAPRI's EU27 figures
        (KNOWN_ISSUES K56)."""
        o = {}
        for reg_, v in r["supply"].items():
            if str(reg_).startswith("NO"):
                continue
            for k, x in getattr(v, f).items():
                if np.isfinite(x):
                    o[k] = o.get(k, 0.0) + float(x)
        return o
    # EU adoption of CAPRI's technologies, as JRC121368 Table 17 reports it (adoption rate =
    # the technology's share v_Miti averaged over the EU; the baseline column matches CAPRI's
    # initial shares weighted by manure N - housing 12 vs 17, covers 14 vs 13, air purification
    # 0 vs 0 - while shares of eligible units do not: 38 and 33). Fertiliser options: share of
    # crop area (regions weighted by crop area). Ammonia options: share of animal units weighted
    # by excreted N (units x N per head); 'eligible' = the options' maximum shares, same weights.
    from capri_mod.data.definitions import CROPS
    env = m.env_module

    def adoption(r):
        fert_num, fert_den, amm = {}, 0.0, {}
        for reg, v in r["supply"].items():
            area = sum(float(v.activities.get(c, 0.0)) for c in CROPS if np.isfinite(v.activities.get(c, 0.0)))
            fs = getattr(v, "fert_tech_shares", None) or {}
            if fs:
                fert_den += area
                for k, sh in fs.items():
                    fert_num[k] = fert_num.get(k, 0.0) + sh * area
            for (act, tech), sh in (getattr(v, "manure_tech_shares", None) or {}).items():
                x = float(v.activities.get(act, 0.0))
                wN = x * float(env._n_excretion(reg, act) or 0.0)
                a_ = amm.setdefault(tech, [0.0, 0.0]); a_[0] += sh * wN
        # denominator: excreted N of all animals with any ammonia option
        den = 0.0
        for reg, v in r["supply"].items():
            acts = {act for (act, _t) in (getattr(v, "manure_tech_shares", None) or {})}
            den += sum(float(v.activities.get(a, 0.0)) * float(env._n_excretion(reg, a) or 0.0) for a in acts)
        return ({k: n / fert_den for k, n in fert_num.items()} if fert_den > 0 else {},
                {k: n / den for k, (n, _) in amm.items()} if den > 0 else {})
    md = s.get("metadata", {}) or {}
    # adoption of the animal options as CAPRI reports shares of herds: livestock units (LEVW; livestock_units.csv)
    # of the heads adopting over the livestock units of the eligible heads (the option's eligible share of the
    # herd, before CAPRI's MaxShare cap), and the cap's ceiling on the same base ("capped"); baseline and scenario
    _gu, _lu = m.data.get("genetics_effects_unit") or {}, m.data.get("livestock_units")

    def adoption_lu(sup, opt):
        ad = el = cp = 0.0
        for r_, v in sup.items():
            for (a_, o_), e in (_gu.get(r_) or {}).items():
                if o_ != opt:
                    continue
                w = (float(_lu.at[r_, a_]) if _lu is not None and r_ in _lu.index and a_ in _lu.columns
                     and _lu.at[r_, a_] == _lu.at[r_, a_] else 1.0)
                x = float(v.activities.get(a_, 0.0) or 0.0)
                es = float(e.get("elig_share", 0.0) or 0.0)
                ms = float(e["max_share"]) if "max_share" in e and e["max_share"] == e["max_share"] else 1.0
                el += w * es * x
                cp += w * es * min(ms, 1.0) * x
                ad += w * float((getattr(v, "genetics_shift", None) or {}).get((a_, o_), 0.0) or 0.0)
        return {"adopting": ad, "eligible": el, "capped": cp}

    out = {"prices": {c: float(ds[c] / db[c] - 1) for c in db.index if db[c] > 0},
           "act": (agg(b, "activities"), agg(s, "activities")),
           "out": (agg(b, "gross_output"), agg(s, "gross_output")),
           # EU production of the market commodities (1000 t), baseline and scenario
           "prod": tuple({c: float(x["market"].production.loc["EU27"].get(c, float("nan")))
                          for c in ("BEEF", "PORK", "POUL", "MILK", "EGGS", "SGMT")} for x in (b, s)),
           "environmental": (b["environmental"], s["environmental"]),
           # EU biofuel block (crushing stage 4): feedstock use by commodity and feedstock, baseline and
           # scenario (MarketEquilibrium.biofuel)
           "biofuel": tuple(getattr(x["market"], "biofuel", None) for x in (b, s)),
           # CAPRI's inner fertiliser distribution (region x crop group, kg N/ha by source), baseline, scenario
           "fert_dist": tuple((x.get("fert_dist").to_dict("records") if x.get("fert_dist") is not None else None)
                              for x in (b, s)),
           # EU market balance of the dairy chain, baseline and scenario (1000 t)
           "dairy": tuple({c: (float(x["market"].production.loc["EU27"].get(c, float("nan"))),
                               float(x["market"].consumption.loc["EU27"].get(c, float("nan"))))
                           for c in x["market"].production.columns
                           if c in ("MILK", "BUTR", "SKIM", "CHES", "WHEY", "FRMI", "CREM", "COCM", "WMIO", "CASE")}
                          for x in (b, s)),
           # the dairy block itself (MarketEquilibrium.dairy) and the EU premium, baseline and scenario
           "dairy_block": tuple(getattr(x["market"], "dairy", None) for x in (b, s)),
           "adoption": adoption(s), "adoption_base": adoption(b),
           # CAPRI's catch crops under the Farm-to-Fork requirement (1000 ha): baseline, scenario,
           # area that can carry one (eligible), EU regions with a requirement
           # CAPRI's dairy split: cows moved from DCOH to DCOL (1000 heads) and the dairy herd
           # CAPRI's histosol fallowing: idled histosol area (1000 ha) and the histosol area (eligible)
           "histosol": {"fallow": sum(sum(float(x_) for x_ in (getattr(v, "histosol_fallow", None) or {}).values())
                                      for v in s["supply"].values()),
                        "eligible": float(sum(
                            (float(m.data["histosol"].at[reg, "share_crop"]) * sum(float(v.activities.get(c, 0.0)) for c in CROPS if c != "GRAS")
                             + float(m.data["histosol"].at[reg, "share_grass"]) * float(v.activities.get("GRAS", 0.0)))
                            for reg, v in s["supply"].items() if m.data.get("histosol") is not None and reg in m.data["histosol"].index))},
           # cattle genomics (breeding.gms): heads adopting and all heads of the animals concerned, scenario
           "endotech": dict(_scen.endotech),
           "scenario_settings": {"name": _scen.name, "surplus_rule": _scen.surplus_rule,
                                 "manure_trade": _scen.manure_trade, "biofuel_markets": _scen.biofuel_markets,
                                 "biofuel_mandate": _scen.biofuel_mandate,
                                 "mineral_redu": _scen.mineral_redu,
                                 "endotech": dict(_scen.endotech)},
           # biofuel markets (MarketEquilibrium.biofuel): EU feedstock use, every region's biofuel output, use and
           # price ratio, EU member states' first-generation output and processing margin; baseline, scenario
           "biofuel": tuple(getattr(x["market"], "biofuel", None) for x in (b, s)),
           # CAPRI's inner fertiliser distribution (region x crop group, kg N/ha by source), baseline, scenario
           "fert_dist": tuple((x.get("fert_dist").to_dict("records") if x.get("fert_dist") is not None else None)
                              for x in (b, s)),
           # EU market levels of the BASELINE (1000 t, EUR/t), for tools/check/compare_baseline_capri.py
           "base_market": {"prod": b["market"].production.loc["EU27"].astype(float).to_dict(),
                           "cons": b["market"].consumption.loc["EU27"].astype(float).to_dict(),
                           "net_exports": (b["market"].net_exports.loc["EU27"].astype(float).to_dict()
                                           if "EU27" in b["market"].net_exports.index else {}),
                           "price": db.astype(float).to_dict(),
                           "world": b["market"].world_prices.astype(float).to_dict()},
           # EU market levels of the SCENARIO (1000 t; EUR/t at the reported domestic price)
           "scen_market": {"prod": s["market"].production.loc["EU27"].astype(float).to_dict(),
                           "cons": s["market"].consumption.loc["EU27"].astype(float).to_dict(),
                           "net_exports": (s["market"].net_exports.loc["EU27"].astype(float).to_dict()
                                           if "EU27" in s["market"].net_exports.index else {}),
                           "price": s["market"].domestic_prices.loc["EU27"].astype(float).to_dict(),
                           "world": s["market"].world_prices.astype(float).to_dict()},
           # the outer loop's state per iteration, base and scenario (signals, targets, young-animal prices, member
           # states' milk, EU herds; KNOWN_ISSUES K75)
           "outer_history": tuple(x.get("outer_history") for x in (b, s)),
           # raw milk per market region, base and scenario: production, use, domestic price (EUR/t). Raw milk is not
           # traded in CAPRI, so production equals use in every region (audit M11)
           "raw_milk": {lab: {rg: (float(x["market"].production.at[rg, "MILK"]),
                                   float(x["market"].consumption.at[rg, "MILK"]),
                                   float(x["market"].domestic_prices.at[rg, "MILK"]))
                              for rg in x["market"].production.index}
                        for lab, x in (("base", b), ("scen", s)) if "MILK" in x["market"].production.columns},
           # EU market regions (CAPRI's two trade blocks with --eu-blocks): production, use, price, base and scenario,
           # and the flows between them
           "eu_regions": {lab: {rg: {"prod": x["market"].production.loc[rg].astype(float).to_dict(),
                                     "cons": x["market"].consumption.loc[rg].astype(float).to_dict(),
                                     "price": x["market"].domestic_prices.loc[rg].astype(float).to_dict()}
                                for rg in getattr(_pmm, "EU", ("EU27",))}
                          for lab, x in (("base", b), ("scen", s))},
           "eu_block_flows": {lab: (x["market"].trade_flows.loc[[(e, i) for e in getattr(_pmm, "EU", ()) for i in getattr(_pmm, "EU", ()) if e != i]].astype(float).to_dict()
                                    if len(getattr(_pmm, "EU", ())) > 1 else {})
                              for lab, x in (("base", b), ("scen", s))},
           "adoption_lu": {opt: {"base": adoption_lu(bEU, opt), "scen": adoption_lu(sEU, opt),
                                 "weights": "livestock_units" if _lu is not None else "heads"}
                           for opt in ("genet_yld", "genet_eff", "lowNFeed", "LINE_Tot", "Nitr_Tot")},
           "genetics": {opt: {"adopting": sum(float(z_) for v in sEU.values()
                                               for (a_, o_), z_ in (getattr(v, "genetics_shift", None) or {}).items() if o_ == opt),
                              "heads": sum(float(v.activities.get(a_, 0.0)) for v in sEU.values()
                                           for a_ in (("DCOW",) if opt == "genet_yld" else ("BULL", "BCOW", "CALV", "HFRS", "SHGF")))}
                        for opt in ("genet_yld", "genet_eff")},
           # CAPRI's low-nitrogen feeding (Sprint 9g): manure N of the heads adopting / manure N of all heads (base
           # manure N per head of each region and animal), scenario
           "lownfeed": (lambda mn: {"adopting_n": sum(float(z_) * float(mn.at[r, a_]) for r, v in sEU.items()
                                                       for (a_, o_), z_ in (getattr(v, "genetics_shift", None) or {}).items()
                                                       if o_ == "lowNFeed" and r in mn.index and a_ in mn.columns
                                                       and mn.at[r, a_] == mn.at[r, a_]),
                                      "manure_n": sum(float(v.activities.get(a_, 0.0)) * float(mn.at[r, a_]) for r, v in sEU.items()
                                                      if r in mn.index for a_ in mn.columns if mn.at[r, a_] == mn.at[r, a_])})(
               m.data.get("livestock_manure_n_coef")) if m.data.get("livestock_manure_n_coef") is not None else None,
           # CAPRI's feed supplements (Sprint 9g): cattle heads fed linseed / nitrate, of all cattle heads, scenario
           "supplements": {opt: {"adopting": sum(float(z_) for v in sEU.values()
                                                  for (a_, o_), z_ in (getattr(v, "genetics_shift", None) or {}).items() if o_ == opt),
                                 "heads": sum(float(v.activities.get(a_, 0.0)) for v in sEU.values()
                                              for a_ in ("DCOW", "BCOW", "BULL", "HFRS", "CALV"))}
                           for opt in ("LINE_Tot", "Nitr_Tot")},
           "dairy_split": {"low_shift": sum(float(getattr(v, "dairy_low_shift", 0.0) or 0.0) for v in sEU.values()),
                           "cows": sum(float(v.activities.get("DCOW", 0.0)) for v in sEU.values())},
           # bulls and heifers (Sprint 7c): low-intensity stalls, baseline and scenario (share_low x heads + z)
           # CAPRI's cattle activities inside the model's animals: the "low" activity's stalls (BULL; HEIL; HEIR for
           # HFRS:rep; fattening calves CAMF / CAFF for CALV:male / female), baseline and scenario (share x heads + z)
           "cattle_split": {k: {"low_base": sum(float(((m.data.get("cattle_intensity") or {}).get(r) or {}).get(k, {}).get("share_low", 0.0))
                                                * float(bEU[r].activities.get(k.split(":")[0], 0.0)) for r in bEU),
                                "low": sum(float(((m.data.get("cattle_intensity") or {}).get(r) or {}).get(k, {}).get("share_low", 0.0))
                                           * float(v.activities.get(k.split(":")[0], 0.0)) + float((getattr(v, "cattle_shift", None) or {}).get(k, 0.0))
                                           for r, v in sEU.items()),
                                "heads_base": sum(float(bEU[r].activities.get(k.split(":")[0], 0.0)) for r in bEU
                                                  if k in (((m.data.get("cattle_intensity") or {}).get(r)) or {})),
                                "heads": sum(float(v.activities.get(k.split(":")[0], 0.0)) for r, v in sEU.items()
                                             if k in (((m.data.get("cattle_intensity") or {}).get(r)) or {}))}
                            for k in ("BULL", "HFRS", "HFRS:rep", "CALV:male", "CALV:female")},
           # CAPRI's labour accounts (million hours: LABT, LABF, LABP) and set-aside split (1000 ha; premiums million
           # EUR), EU27 sums (Norway out), baseline and scenario
           "labour": tuple((lambda t: {k: float(t.loc[[r_ for r_ in t.index if not str(r_).startswith("NO")], k].sum())
                                       for k in t.columns} if t is not None else None)(x.get("labour")) for x in (b, s)),
           "set_aside": tuple((lambda t: {k: float(t.loc[[r_ for r_ in t.index if not str(r_).startswith("NO")], k].sum())
                                          for k in t.columns} if t is not None else None)(x.get("set_aside")) for x in (b, s)),
           "cover_crops": {k: sum(float((getattr(v, "cover_crops", None) or {}).get(f, 0.0) or 0.0)
                                  for v in sEU.values())
                           for k, f in (("base", "base"), ("scenario", "req"), ("eligible", "potential"))},
           # per region: N-balance price (EUR/kg N), technology shares (diagnostics)
           "act_regional": tuple({reg: {k: float(x_) for k, x_ in v.activities.items() if np.isfinite(x_)}
                                  for reg, v in x["supply"].items()} for x in (b, s)),
           "regional": {reg: {"lam": float((getattr(v, "shadow_prices", {}) or {}).get("N_balance", 0.0) or 0.0),
                              "fert": dict(getattr(v, "fert_tech_shares", None) or {}),
                              "amm": {f"{a_}|{t_}": float(x_) for (a_, t_), x_ in (getattr(v, "manure_tech_shares", None) or {}).items()},
                              # every constraint's shadow price, the manure trade and the land types
                              "duals": {k_: float(x_) for k_, x_ in (getattr(v, "shadow_prices", {}) or {}).items()
                                        if x_ is not None and np.isfinite(x_)},
                              "manure_trade": tuple(float(t_) for t_ in (getattr(v, "manure_trade", None) or (0.0, 0.0))),
                              "land_types": dict(getattr(v, "land_types", None) or {}),
                              "n_target_relaxed": bool(getattr(v, "n_target_relaxed", False)),
                              # (0, the N balance's shortfall): the first item was the landscape floor's, which is
                              # no longer relaxed (K84, 27 October 2026); kept so earlier runs compare
                              "shortfall": (0.0, float(getattr(v, "balance_shortfall", 0.0) or 0.0)),
                              "manure_pool_price": float((getattr((getattr(pmod, "_last_projected_model", None) or m).supply_module, "manure_pool_price", None) or {}).get(reg[:2], 0.0) or 0.0)}
                        for reg, v in s["supply"].items()},
           # baseline manure trade per region (t N exported, imported), for the check against CAPRI's MTRADE
           "manure_trade_base": {reg: tuple(float(t_) for t_ in (getattr(v, "manure_trade", None) or (0.0, 0.0)))
                                 for reg, v in b["supply"].items()},
           "meta": {"conv": md.get("outer_converged"), "it": md.get("n_outer_iterations"),
                    "young_animals": (md.get("young_animal_prices"), md.get("young_animal_imbalance")),
                    "young_animal_markets": md.get("young_animal_markets"),
                    "seconds": round(time.time() - t0), "options": vars(a),
                    # the effective settings of the run (also written next to the pickle as <out>.settings.toml)
                    "settings": run_settings.to_dict(), "settings_changed": run_settings.diff(),
                    "market_supply_hessian": getattr(getattr(pmod, "_last_projected_model", None) or m,
                                                     "market_supply_hessian_info", None),
                    "market_supply_hessian_log": getattr(getattr(pmod, "_last_projected_model", None) or m,
                                                         "market_supply_hessian_log", None),
                    "base_iterations": b.get("metadata", {}).get("n_outer_iterations"),
                    # CAPRI's stop rule at the last iteration, baseline and scenario (capri_mod/utils/capri_stop.py)
                    "capri_stop": {lab_: (d_.get("metadata") or {}).get("capri_stop") for lab_, d_ in (("base", b), ("scen", s))},
                     "prices": pmod.price_summary,
                     # regions where CAPRI's form failed (K55, K57): JRC121368's relaxed N target, or IPOPT's last point
                     # kept (non-optimal, as CAPRI)
                     "nlp_fallback": {lab_: dict((d_.get("metadata") or {}).get("nlp_fallback") or {})
                                      for lab_, d_ in (("baseline", b), ("scenario", s))},
                     # Norway's last price gap and product (K56; out of the convergence test from iteration 15)
                     "nor_price_gap": (s.get("metadata") or {}).get("nor_price_gap"),
                     "market_calibration_bound_hits": {lab_: (d_.get("metadata") or {}).get("market_calibration_bound_hits")
                                                       for lab_, d_ in (("base", b), ("scen", s))},
                     "pmp_source": (s.get("metadata") or {}).get("pmp_source"),
                     "pmp_capri_parts": (s.get("metadata") or {}).get("pmp_capri_parts"),
                     # regions whose NLP form needed the Green Deal's mineral caps relaxed (KNOWN_ISSUES K50)
                     "nlp_relaxed": dict((s.get("metadata") or {}).get("nlp_relaxed") or {}),
                     # regions whose last IPOPT point was kept (non-optimal, as CAPRI keeps a non-optimal solve)
                     "nlp_nonoptimal": {lab_: sorted(r_ for r_, v_ in d_["supply"].items()
                                                     if getattr(v_, "nlp_nonoptimal", None))
                                        for lab_, d_ in (("baseline", b), ("scenario", s))},
                     # the final market solve of the baseline and of the scenario met its balances (residual < 1e-7)
                     "market_converged": {lab_: bool(getattr(d_["market"], "converged", True))
                                          for lab_, d_ in (("baseline", b), ("scenario", s))}}}
    _pmm = (getattr(pmod, "_last_projected_model", None) or m).market_module
    out["eu_premium"] = {c: float(v) for c, v in (getattr(_pmm, "eu_premium", None) if getattr(_pmm, "eu_premium", None) is not None else {}).items()}
    # diagnostics: the final regional problems of selected regions (CAPRI_DUMP_REGIONS=SE32,NL34)
    import os as _os
    _dump = [r_ for r_ in _os.environ.get("CAPRI_DUMP_REGIONS", "").split(",") if r_]
    if _dump:
        _d = {}
        _pm = getattr(pmod, "_last_projected_model", None) or m       # the scenario's own model
        for r_ in _dump:
            md_ = _pm.supply_module._models.get(r_)
            if md_ is None:
                continue
            _d[r_] = {k_: getattr(md_, k_, None) for k_ in ("_last_aug", "_last_plain", "_row_labels", "_last_duals",
                                                            "_land_types_used", "_fert_tech_shares", "_n_intensity",
                                                            "_cover", "_fall_floor", "_last_grass_z")}
            _d[r_].update({"acts": list(md_.acts), "Q": md_.Q, "f": md_.f, "net_revenues": md_.net_revenues.copy(),
                           "base": md_._base_levels(), "nb_price": getattr(_pm.supply_module, "_nbal_state", {}).get(r_),
                           "surplus_row": getattr(md_, "_surplus_row", None),
                           "balance_coefs": _pm.supply_module._balance_coefs(r_, md_)})
        pickle.dump(_d, open(a.out.replace(".pkl", "_dump.pkl"), "wb"))
    pickle.dump(out, open(a.out, "wb"))
    run_settings.save(str(a.out).rsplit(".", 1)[0] + ".settings.toml")
    _no = out["meta"]["nlp_nonoptimal"]
    print(f"saved {a.out} | converged {out['meta']['conv']} in {out['meta']['it']} iterations, {out['meta']['seconds']} s"
          f" | non-optimal regional solves kept: baseline {len(_no['baseline'])}, scenario {len(_no['scenario'])}"
          + (f" ({', '.join(_no['baseline'] + _no['scenario'])})" if _no['baseline'] or _no['scenario'] else "")
          + f" | PMP {out['meta'].get('pmp_source')}"
          + (f", mineral caps relaxed: {out['meta']['nlp_relaxed']}" if out['meta'].get('nlp_relaxed') else "")
          + ("" if all(out["meta"]["market_converged"].values()) else
             f" | MARKET NOT CONVERGED: {[k_ for k_, v_ in out['meta']['market_converged'].items() if not v_]}"))


if __name__ == "__main__":
    main()
