"""CAPRI's nitrogen loss cascade of the regional supply model (ghgAbatement on; supply/supply_model.gms GRAZN_, HOUSN_,
STORN_, RUNHOUSN_, RUNSURFN_, APPLN_, RUNTOTN_, GASRUNTOTN_, GASTOTNETF_, RUNTOTNETF_, GASRUNTOTNETF_), written
equation by equation; docs/N_CASCADE_SPEC.md has the factors (p_Nemidat) with their sources.

Every function takes plain arithmetic, so it evaluates with floats (accounts, checks) and with CasADi symbols (the
regional NLP) alike. Losses are fractions of the N excreted (animals) or of the mineral N bought (NETF).

Arguments
  f       p_Nemidat of the region and animal activity: tsg, graz_<g>, hous_<g>, stor_<g>, appl_<g>, run_hous
          (tools/build/build_n_cascade.py, n_cascade_factors.csv)
  run_surf  p_Nemidat(RUNR, MAACT, "N", "Runoff", "Surf") (n_cascade_region.csv; 0 where the activity has no base level)
  sh      the animal's option shares v_Miti {tech: share} (missing = 0)
  eff     the options' othImpact {(tech, item): value}, items as CAPRI's (NH3HOU, NOXHOU, N2OHOU, N2HOU, NH3STO, ...,
          no3runh, no3mrun)
  m_runsurf   RUNSURFN_'s crop factors (a, b): a = 1 - winter cover - tillage - fertiliser options (the application
          options' own no3mrun is taken off a here), b = 1 - buffer strips - biodiversity
  m_appl_run  APPLN_'s crop factor on the runoff from the surface: (1 - winter cover - NoTill - fertiliser options) x
          (1 - buffer strips - biodiversity)
  fert_appl   APPLN_'s fertiliser-option terms by gas (sum over AllTechFert of (shares + AECM initial) x effect)

CAPRI's own code is kept where it reads oddly (REGISTERED, docs/N_CASCADE_SPEC.md section 4):
  * HOUSN_ sums only LowEmHous, AirPur, AirPurCovLow, AirPurCovLowC, AirPurCovHigh and ManAcid, so the storage covers'
    N2O effect, moved by ammo_tech.gms (l. 2236) from N2OSTO to N2OHOU, does not act;
  * STORN_ takes NH3 + NOX off before N2 only (N2O at storage is 0 by data);
  * APPLN_ takes NH3 + NOX off for N2O inside the bracket multiplied by (1 - runoff).
"""
from __future__ import annotations

GASES = ("NH3", "NOX", "N2O")
NMAT = ("N2O", "NH3", "NOX", "N2")
HOUS_TECHS = ("LowEmHous", "AirPur", "AirPurCovLow", "AirPurCovLowC", "AirPurCovHigh", "ManAcid")
STOR_TECHS = ("CovStorLow", "CovStorLowCon", "CovStorHigh", "AirPurCovLow", "AirPurCovLowC", "AirPurCovHigh",
              "LowEmHous", "ManAcid")
RUNH_TECHS = ("LowEmHous", "CovStorLow", "CovStorLowCon", "CovStorHigh", "ManStorCon", "AirPurCovLowC",
              "AirPurCovHigh")
APPL_TECHS = ("AmmAppHE", "AmmAppLE")


def _s(sh, t):
    return sh.get(t, 0.0)


def _e(eff, t, item):
    return eff.get((t, item), 0.0)


_NZ = {}


def _terms(eff, techs, item):
    """The options of techs with a nonzero effect on item, with that effect: ((tech, effect), ...), cached per effect
    table. A zero effect adds e x share = 0 exactly (CasADi drops such terms too), so leaving them out of the sums below
    changes no result; it spares most of the cascade's work (27 October 2026: the cascade was 28% of a regional solve)."""
    k = (id(eff), techs, item)
    v = _NZ.get(k)
    if v is None or v[0] is not eff:
        v = (eff, tuple((t, eff[(t, item)]) for t in techs if eff.get((t, item), 0.0) != 0.0))
        _NZ[k] = v
    return v[1]


def losses(f, run_surf, sh, eff, m_runsurf=(1.0, 1.0), m_appl_run=1.0, fert_appl=None):
    """CAPRI's v_emiLoss of one animal activity: {(gas, stage): fraction of excreted N}, stages Graz, Hous, Stor, Appl,
    and ("N", "RunHous"), ("N", "RunSurf"), ("N", "RunTot"), ("N", "GasRunTot").
    fert_appl: {gas: sum over the fertiliser options (shares + AECM initial shares) x othImpact <gas>APP} (APPLN_)."""
    fert_appl = fert_appl or {}
    tsg = f.get("tsg", 0.0)
    L = {}
    # GRAZN_
    for g in GASES:
        L[(g, "Graz")] = tsg * f.get(f"graz_{g}", 0.0)
    L[("N2", "Graz")] = 0.0
    # HOUSN_ (NH3 and NOX first: N2O is applied after their removal)
    ad = _s(sh, "AD_AnCh")
    for g in ("NH3", "NOX", "N2O"):
        tag = f"{g}HOU"
        base = 1.0 - tsg
        if g == "N2O":
            base = base - (L[("NH3", "Hous")] + L[("NOX", "Hous")])
        red = 0.0
        for t, e in _terms(eff, HOUS_TECHS, tag):
            red = red + e * _s(sh, t)
        v = base * f.get(f"hous_{g}", 0.0) * (1.0 - red)
        if g == "N2O":
            v = v * (1.0 - ad * _e(eff, "AD_AnCh", "N2OHOU"))
        L[(g, "Hous")] = v
    L[("N2", "Hous")] = 0.0
    hous = L[("NH3", "Hous")] + L[("NOX", "Hous")] + L[("N2O", "Hous")]
    # STORN_ (N2 after NH3 and NOX)
    for g in ("NH3", "NOX", "N2", "N2O"):
        tag = f"{g}STO"
        base = 1.0 - tsg - hous
        if g == "N2":
            base = base - (L[("NH3", "Stor")] + L[("NOX", "Stor")])
        red = 0.0
        for t, e in _terms(eff, STOR_TECHS, tag):
            red = red + e * _s(sh, t)
        v = base * f.get(f"stor_{g}", 0.0) * (1.0 - red)
        if g in ("NH3", "NOX"):
            v = v * (1.0 - ad * _e(eff, "AD_AnCh", tag))
        L[(g, "Stor")] = v
    stor = sum(L[(g, "Stor")] for g in NMAT)
    hous_all = hous + L[("N2", "Hous")]
    # RUNHOUSN_
    red = 0.0
    for t, e in _terms(eff, RUNH_TECHS, "no3runh"):
        red = red + e * _s(sh, t)
    L[("N", "RunHous")] = (1.0 - tsg - hous - stor) * f.get("run_hous", 0.0) * (1.0 - red)
    graz = L[("NH3", "Graz")] + L[("NOX", "Graz")] + L[("N2O", "Graz")]
    left = 1.0 - tsg - hous_all - stor - L[("N", "RunHous")]
    # RUNSURFN_ (the application options' own runoff effect enters the first factor)
    app_run = 0.0
    for t, e in _terms(eff, APPL_TECHS, "no3mrun"):
        app_run = app_run + e * _s(sh, t)
    L[("N", "RunSurf")] = (tsg * (1.0 - graz) + left) * run_surf * (m_runsurf[0] - app_run) * m_runsurf[1]
    # APPLN_ (N2O after NH3 and NOX, inside the bracket)
    ro = 1.0 - run_surf * m_appl_run
    for g in ("NH3", "NOX", "N2O"):
        tag = f"{g}APP"
        base = left
        if g == "N2O":
            base = base - (L[("NH3", "Appl")] + L[("NOX", "Appl")])
        red = 0.0
        for t, e in _terms(eff, APPL_TECHS, tag):
            red = red + e * _s(sh, t)
        red = red + fert_appl.get(g, 0.0)
        if g == "N2O":
            red = red + _e(eff, "AD_AnCh", "N2OAPP") * ad
        L[(g, "Appl")] = base * ro * f.get(f"appl_{g}", 0.0) * (1.0 - red)
    L[("N2", "Appl")] = 0.0
    L[("N", "RunTot")] = L[("N", "RunHous")] + L[("N", "RunSurf")]
    tot = 0.0
    for g in NMAT:
        for st in ("Graz", "Hous", "Stor", "Appl"):
            tot = tot + L[(g, st)]
    L[("N", "GasRunTot")] = tot + L[("N", "RunHous")] + L[("N", "RunSurf")]
    return L


def netf(fr, run_surf, urea=0.0, urea_eff=0.0, fert_syn=None, till_n2o=0.0, m_run=1.0):
    """CAPRI's v_emiLoss of mineral fertiliser (GASTOTNETF_, RUNTOTNETF_, GASRUNTOTNETF_) as fractions of mineral N.
    fr: netf_NH3, netf_NOX, netf_N2O (n_cascade_region.csv); urea: share of UreaSubst, urea_eff its othImpact NH3SYN;
    fert_syn {gas: sum over fertiliser options of (shares + AECM initial shares) x othImpact <gas>SYN}; till_n2o: sum
    over tillage options of othImpact n2osyn x share; m_run: RUNTOTNETF_'s crop factors."""
    fert_syn = fert_syn or {}
    L = {}
    L["NH3"] = fr.get("netf_NH3", 0.0) * (1.0 - urea * urea_eff - fert_syn.get("NH3", 0.0))
    L["NOX"] = fr.get("netf_NOX", 0.0) * (1.0 - fert_syn.get("NOX", 0.0))
    L["N2O"] = (1.0 - L["NH3"] - L["NOX"]) * fr.get("netf_N2O", 0.0) * (1.0 - fert_syn.get("N2O", 0.0) - till_n2o)
    gas = L["NH3"] + L["NOX"] + L["N2O"]
    L["RunTot"] = (1.0 - gas) * run_surf * m_run
    L["GasRunTot"] = gas + L["RunTot"]
    return L


def mineral_n2o_n(fr, ef4):
    """CAPRI's soil N2O of mineral fertiliser per unit of mineral N, as N2O-N (envind/gases.gms (7) N2OSYN and the
    mineral part of (9) N2OAMM): direct emiLoss(NETF, N2O, GasTot) and indirect (emiLoss(NETF, NH3) + emiLoss(NETF,
    NOx)) x EF4, from the region's MITERRA fractions (netf; before the fertiliser options' side effects, which the
    accounts apply as factors). Returns (direct, indirect); None without the region's fractions."""
    if not fr or "netf_N2O" not in fr:
        return None
    L = netf(fr, 0.0)
    return float(L["N2O"]), float(L["NH3"] + L["NOX"]) * float(ef4)


_DATA = {}


def load(data_dir=None):
    """The cascade's data (tools/build/build_n_cascade.py): (factors {(region, act): {factor: v}}, regional
    {region: {factor: v}}, effects {(region, act): {(tech, item): v}}), CAPRI regions (8 characters)."""
    from capri_mod.supply.inputs import SupplyInputs, current
    inp = SupplyInputs(data_dir, current().base_year) if data_dir else current()
    key = str(inp.path("", "abatement/ammonia"))
    if key not in _DATA:
        F, G, E = {}, {}, {}
        for r in inp.rows("n_cascade_factors.csv", "abatement/ammonia"):
            F.setdefault((r["region"], r["activity"]), {})[r["factor"]] = float(r["value"])
        for r in inp.rows("n_cascade_region.csv", "abatement/ammonia"):
            G.setdefault(r["region"], {})[r["factor"]] = float(r["value"])
        for r in inp.rows("n_cascade_effects.csv", "abatement/ammonia"):
            E.setdefault((r["region"], r["activity"]), {})[(r["technology"], r["item"])] = float(r["value"])
        _DATA[key] = (F, G, E)
    return _DATA[key]


#: winter cover's effect on runoff and leaching (envind/cover_crops.gms l. 400-402, endoLeach on)
WINTERCOV_NO3 = 0.35


def activity_losses(region, act, shares, winter_cover=0.0, data_dir=None):
    """losses() for a CAPRI region (8 characters) and animal activity with its option shares and the region's winter
    cover share (CAPRI's other crop options' runoff effects are 0 or not modelled: tillage's no3mrun is commented out
    in envind/tillage.gms l. 561-566; buffer strips, biodiversity options and fertiliser techniques are not in
    capri-mod)."""
    F, G, E = load(data_dir)
    f = F[(region, act)]
    wc = 1.0 - WINTERCOV_NO3 * winter_cover
    return losses(f, G.get(region, {}).get("run_surf", 0.0), shares, E.get((region, act), {}),
                  m_runsurf=(wc, 1.0), m_appl_run=wc)
