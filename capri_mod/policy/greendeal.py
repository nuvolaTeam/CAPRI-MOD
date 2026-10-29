"""CAPRI's Green Deal scenario switchboard, for capri-mod.

Mirrors ``pol_input/greendeal/greendeal_scenarios.gms``: the same settings, in
the same units, and the same result naming, so a CAPRI user can drive
capri-mod the way they drive CAPRI::

    from capri_mod.policy.greendeal import greendeal_scenario
    f2f = greendeal_scenario(lndscpTarg=10, orgTarg=25, pestRedu=50, surpRedu=50)
    f2f.name   # 'greendeal_lnds10_org25_pest50_mine00_surp50_diet00_oth00'
    model.run(custom_scenario=f2f)

Each setting maps onto the capri-mod implementation of CAPRI's own file:

==========  ============================  =====================================
setting     CAPRI file                    capri-mod
==========  ============================  =====================================
lndscpTarg  landscape.gms                 landscape floor; CAPRI's per-country
            (floor = lndscpTarg/10 x      missing share of UAA plus existing
            p_setAsideTarget x UAA+SETF)  set-aside; 10 = the full target
orgTarg     organic_area.gms              organic conversion burden-shared by
                                          member state and crop group; 25 = full
pestRedu    pesticides.gms,               a TOTAL target, applied to the
            conventional_io.gms           conventional area only; 10% yield loss
surpRedu    surptot.gms                   surplus_rule="star3" (default): star 3.0's file, every NUTS2
                                          region's baseline surplus/ha cut by surpRedu%;
                                          "jrc121368": the report's tiered rule with the
                                          nine-region 36% cap (the 2020 CAPRI run)
mineRedu    minfert_redu_uaa.gms ("20"),  mineral N cap per ha of UAA ("20") or
            minfert_redu_by_crop.gms      per crop group ("10crp".."20crp", with
            ("10crp", ..., "20crp")       CAPRI's exemptions); EU27 only
dietShift   diets_disagg.gms              NOT IMPLEMENTED - refused if non-zero
othPol      oth_pol.gms                   NOT IMPLEMENTED - refused if non-zero
==========  ============================  =====================================

An option capri-mod does not implement raises an error instead of being
silently ignored: a result labelled with a setting it never applied would be
worse than no result.
"""
from __future__ import annotations

from capri_mod.policy.policy_module import PolicyScenario

#: settings capri-mod implements, with the values CAPRI's file allows
_SUPPORTED = {
    # the values CAPRI star 3.0's GUI offers (GUI/capri_gui_definition.xml, scenario group greenDeal)
    "lndscpTarg": (0, 7, 8, 9, 10),
    "orgTarg": (0, 15, 18, 22, 25),
    "pestRedu": (0, 5, 13, 15, 20, 26, 30, 32, 35, 40, 50),
    "surpRedu": (0, 20, 30, 35, 40, 50),
}
#: mineRedu values of star 3.0's GUI (capri_gui_definition.xml: 00, 20, 10crp, 13crp, 17crp, 20crp)
_MINE_REDU = ("00", "20", "10crp", "13crp", "17crp", "20crp")
_NOT_IMPLEMENTED = ("dietShift", "othPol")


def _mine(v) -> str:
    """CAPRI's mineRedu string (0 and 20 may be given as integers)."""
    return f"{v:02d}" if isinstance(v, int) else str(v)


def scenario_name(lndscpTarg=0, orgTarg=0, pestRedu=0, mineRedu=0,
                  surpRedu=0, dietShift=0, othPol=0) -> str:
    """CAPRI's name for the scenario (greendeal_scenarios.gms, 'scenNameFromGroup')."""
    # the GUI's option strings: "00" for zero, the number as written otherwise (lnds8, org18; CAPRI's result names,
    # e.g. res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00defaultA)
    g = lambda v: "00" if int(v) == 0 else str(int(v))
    name = (f"greendeal_lnds{g(lndscpTarg)}_org{g(orgTarg)}_pest{g(pestRedu)}"
            f"_mine{_mine(mineRedu)}_surp{g(surpRedu)}_diet{g(dietShift)}_oth{g(othPol)}")
    if name == "greendeal_lnds00_org00_pest00_mine00_surp00_diet00_oth00":
        return "greendeal_reference"
    return name


def greendeal_scenario(lndscpTarg: int = 10, orgTarg: int = 25, pestRedu: int = 50,
                       mineRedu=0, surpRedu: int = 50,
                       dietShift: int = 0, othPol: int = 0,
                       surplus_rule: str = "star3", manure_trade=None, endotech=None,
                       pesticide_rule: str = "star3") -> PolicyScenario:
    """A Green Deal scenario with CAPRI's switches. Defaults are Farm-to-Fork.

    Values are CAPRI's: percentages as integers (lndscpTarg=10 is the 10%
    landscape target, pestRedu=50 the 50% pesticide cut).
    """
    given = dict(lndscpTarg=lndscpTarg, orgTarg=orgTarg, pestRedu=pestRedu,
                 mineRedu=mineRedu, surpRedu=surpRedu, dietShift=dietShift,
                 othPol=othPol)
    for key in _NOT_IMPLEMENTED:
        if given[key]:
            raise NotImplementedError(
                f"{key}={given[key]}: capri-mod does not implement this CAPRI option "
                f"yet. Run with {key}=0, or implement it from CAPRI's file first.")
    if _mine(mineRedu) not in _MINE_REDU:
        raise ValueError(f"mineRedu={mineRedu!r} is not a value of CAPRI's GUI (allowed: {list(_MINE_REDU)})")
    for key, allowed in _SUPPORTED.items():
        if given[key] not in allowed:
            raise ValueError(f"{key}={given[key]} is not a value capri-mod supports "
                             f"(allowed: {list(allowed) if len(allowed) < 10 else '0-100'})")
    if surplus_rule not in ("jrc121368", "star3"):
        raise ValueError(f"surplus_rule={surplus_rule!r}: 'jrc121368' or 'star3'")
    if pesticide_rule not in ("jrc121368", "star3"):
        raise ValueError(f"pesticide_rule={pesticide_rule!r}: 'jrc121368' or 'star3'")
    if surplus_rule == "jrc121368" and surpRedu not in (0, 50):
        raise ValueError("the JRC121368 tiered rule is the 50% target; use surplus_rule='star3' for other values")
    return PolicyScenario(
        name=scenario_name(**given),
        description=("CAPRI Green Deal scenario group: landscape {}%, organic {}%, "
                     "pesticides -{}%, mineral fertiliser {}, nutrient surplus -{}%").format(
                         lndscpTarg, orgTarg, pestRedu, _mine(mineRedu), surpRedu),
        set_aside_requirement=lndscpTarg / 100.0,
        organic_area_target=orgTarg / 100.0,
        pesticide_reduction=pestRedu / 100.0,
        nutrient_surplus_target=bool(surpRedu),
        surplus_rule=surplus_rule,
        surplus_cut=surpRedu / 100.0,
        mineral_redu=_mine(mineRedu),
        pesticide_rule=pesticide_rule,
        manure_trade=manure_trade,
        endotech=dict(endotech or {}),
        # greendeal_scenarios.gms l. 66-67 (with the market model): negative raw milk prices allowed
        negative_milk_price=True,
    )


def farm_to_fork_scenario() -> PolicyScenario:
    """The Farm-to-Fork scenario as JRC121368 ran it (the 2020 CAPRI): the Green Deal group's four targets
    (landscape 10%, organic 25%, pesticides -50%, nutrient surplus -50%) with the report's own settings -
    the tiered surplus rule with the nine-region 36% cap (sect. 4.3.4), no manure trade ("all manure
    generated in a region has to be used within that region", p. 24), milk-yield genomics active (Table 17:
    adopted on 15% of dairy cows; ghgTechMYld 0.2 of the endotech references of that time). Everything the
    report does not state takes capri-mod's (star 3.0's) setting."""
    from capri_mod.policy.endotech import JRC121368_ENDOTECH
    sc = greendeal_scenario(lndscpTarg=10, orgTarg=25, pestRedu=50, surpRedu=50, surplus_rule="jrc121368",
                            manure_trade=False, endotech=JRC121368_ENDOTECH, pesticide_rule="jrc121368")
    sc.name = "farm_to_fork_jrc121368"
    sc.description = ("Farm-to-Fork as JRC121368: landscape 10%, organic 25%, pesticides -50%, nutrient surplus "
                      "-50% (tiered, 36% cap), no manure trade, milk-yield genomics 0.2")
    return sc


#: CAPRI's own 2030 step of its Green Deal production series (P. Witzke's batch for the Green Deal scenarios,
#: section "f2f": targets phased in 2025 / 2030 / 2035 / 2040; 2030: N surplus -30%, mineral fertiliser 13crp,
#: organic 18%, pesticides -20%, landscape elements 8%; result res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30
#: _diet00_oth00defaultA, named in the batch as the reference of the 2035 step). Settings of that batch not in the
#: GUI group: manure trade on, inner fertiliser model on.
GREENDEAL_2030_TARGETS = dict(lndscpTarg=8, orgTarg=18, pestRedu=20, mineRedu="13crp", surpRedu=30)
#: the full targets of the series, reached in 2040 (surplus -50%, 20crp, organic 25%, pesticides -32%, landscape 10%)
GREENDEAL_2040_TARGETS = dict(lndscpTarg=10, orgTarg=25, pestRedu=32, mineRedu="20crp", surpRedu=50)


def greendeal_2030_scenario(**kw) -> PolicyScenario:
    """CAPRI's 2030 Green Deal settings of its production series (GREENDEAL_2030_TARGETS), with star 3.0's rules
    (surptot.gms surplus rule, pesticides without a yield shock, manure trade on)."""
    args = dict(GREENDEAL_2030_TARGETS, manure_trade=True)
    args.update(kw)
    return greendeal_scenario(**args)
