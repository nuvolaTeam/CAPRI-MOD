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
surpRedu    surptot.gms                   CAPRI's tiered nutrient-surplus rule
mineRedu    minfert_redu_*.gms            NOT IMPLEMENTED - refused if non-zero
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
    "lndscpTarg": range(0, 101),
    "orgTarg": range(0, 101),
    "pestRedu": range(0, 101),
    "surpRedu": (0, 50),          # CAPRI's tiered rule implements the 50% target
}
_NOT_IMPLEMENTED = ("mineRedu", "dietShift", "othPol")


def scenario_name(lndscpTarg=0, orgTarg=0, pestRedu=0, mineRedu=0,
                  surpRedu=0, dietShift=0, othPol=0) -> str:
    """CAPRI's name for the scenario (greendeal_scenarios.gms, 'scenNameFromGroup')."""
    name = (f"greendeal_lnds{lndscpTarg:02d}_org{orgTarg:02d}_pest{pestRedu:02d}"
            f"_mine{mineRedu:02d}_surp{surpRedu:02d}_diet{dietShift:02d}_oth{othPol:02d}")
    if name == "greendeal_lnds00_org00_pest00_mine00_surp00_diet00_oth00":
        return "greendeal_reference"
    return name


def greendeal_scenario(lndscpTarg: int = 10, orgTarg: int = 25, pestRedu: int = 50,
                       mineRedu: int = 0, surpRedu: int = 50,
                       dietShift: int = 0, othPol: int = 0) -> PolicyScenario:
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
    for key, allowed in _SUPPORTED.items():
        if given[key] not in allowed:
            raise ValueError(f"{key}={given[key]} is not a value capri-mod supports "
                             f"(allowed: {list(allowed) if len(allowed) < 10 else '0-100'})")
    return PolicyScenario(
        name=scenario_name(**given),
        description=("CAPRI Green Deal scenario group: landscape {}%, organic {}%, "
                     "pesticides -{}%, nutrient surplus -{}%").format(
                         lndscpTarg, orgTarg, pestRedu, surpRedu),
        set_aside_requirement=lndscpTarg / 100.0,
        organic_area_target=orgTarg / 100.0,
        pesticide_reduction=pestRedu / 100.0,
        nutrient_surplus_target=bool(surpRedu),
    )
