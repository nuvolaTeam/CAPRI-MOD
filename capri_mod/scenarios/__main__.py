"""Create and check scenarios (refactor stage 5; capri_mod/scenarios/definition.py).

    python -m capri_mod.scenarios list                         the references, groups and scenarios found
    python -m capri_mod.scenarios new NAME --reference REF [--group greendeal_group] [--dir FOLDER]
                                                              a scenario folder with a commented settings.toml
    python -m capri_mod.scenarios check NAME [--dir FOLDER]    checks a folder without running the model

--dir is the folder of your own scenarios (the setting run.scenarios_dir; default: capri_data/scenarios). A run takes
the scenario by name: python tools/run/run_f2f_2030.py OUT.pkl --scenario NAME [--scenarios-dir FOLDER].
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from capri_mod.scenarios import definition as D

TEMPLATE = '''# A scenario of capri-mod (python -m capri_mod.scenarios check {name}). Remove the lines you do not need: every
# key not given takes its reference's value or the model's default. CAPRI's own scenario files are cited per key.
[scenario]
name = "{name}"
kind = "scenario"
description = ""
# the CAPRI files this scenario follows (paths under CAPRI's gams folder), for the record
capri_files = []
# the reference it is compared with (its folder); it gives the trajectory and the reference-level settings
reference = "{reference}"
{group_line}
# settings that hold for this scenario and its baseline (default: the reference's)
# manure_trade = true          # CAPRI's manure trade (manureTradeNew)
# biofuel_markets = true       # CAPRI's endogenous biofuel markets (BIOF_M)

# [scenario.endotech]          # CAPRI's endogenous technologies (pol_input/greendeal/refpol_endotech_all_sup.gms)
# ghgTechMYld = 0.0            # milk-yield genomics
# ghgTechFEff = 0.1            # feed-efficiency genomics

{greendeal_block}
[scenario.shocks]
# carbon_tax = 0.0             # EUR per t CO2-eq (ghgTax, pol_input/ecampa/carbtax50_endotech_*.gms)
# biss_rate_change = 0.0       # EUR per ha
# lfa_budget_change = 0.0      # relative change of the rural-development budgets (policy/rd_logic.gms)
# ae_budget_change = 0.0
# n2k_budget_change = 0.0
# biofuel_mandate = 1.0        # EU and UK blending mandates x this factor (scen/bio_fuels/change_biof_mandate.gms)
# milk_quota = 0.0             # 1000 t
# sugar_quota = 0.0            # 1000 t
{set_aside_line}
# Tables, as CSV files beside this one (each optional):
#   coupled_support.csv     activity,value
#   premium_factors.csv     region,activity,factor          (regional units; new premium / old)
#   tariff_changes.csv      region,commodity,change_pct     (market regions)
#   trq_volume_changes.csv  commodity,change_kt
'''

GREENDEAL = '''[scenario.greendeal]          # CAPRI's Green Deal group (pol_input/greendeal/greendeal_scenarios.gms; the GUI's values)
lndscpTarg = 0                 # landscape elements, %: 0, 7, 8, 9, 10
orgTarg = 0                    # organic area, %: 0, 15, 18, 22, 25
pestRedu = 0                   # pesticide reduction, %: 0, 5, 13, 15, 20, 26, 30, 32, 35, 40, 50
mineRedu = "00"                # mineral fertiliser: "00", "20", "10crp", "13crp", "17crp", "20crp"
surpRedu = 0                   # nutrient surplus reduction, %: 0, 20, 30, 35, 40, 50
surplus_rule = "star3"         # "star3" (surptot.gms) or "jrc121368" (the tiered rule, 50% only)
pesticide_rule = "star3"       # "star3" (no yield loss) or "jrc121368" (10% at a 50% cut)
'''


def _new(a) -> int:
    root = Path(a.dir).expanduser() if a.dir else D.ROOT
    folder = root / a.name
    if folder.exists():
        print(f"{folder} exists", file=sys.stderr)
        return 1
    D.load(a.reference)                                  # the reference must exist and be valid
    gd = a.group == "greendeal_group"
    folder.mkdir(parents=True)
    (folder / "settings.toml").write_text(TEMPLATE.format(
        name=a.name, reference=a.reference,
        group_line=f'group = "{a.group}"' if a.group else "# group = \"greendeal_group\"   # the Green Deal group's data",
        greendeal_block=GREENDEAL if gd else "",
        set_aside_line="" if gd else "# set_aside_requirement = 0.0  # a set-aside floor, share of UAA"))
    print(f"wrote {folder / 'settings.toml'}; edit it, then: python -m capri_mod.scenarios check {a.name}"
          + (f" --dir {a.dir}" if a.dir else ""))
    return 0


def _check(a) -> int:
    root = Path(a.dir).expanduser() if a.dir else None
    try:
        d = D.load(a.name, root)
        if d.kind == "scenario":
            sc = D.to_policy_scenario(d, root)
            blank = type(sc)(name=sc.name)
            changed = [f for f in sc.__dataclass_fields__ if f not in ("name", "description")
                       and getattr(sc, f) != getattr(blank, f)]
            print(f"{d.name}: a scenario on {d.reference} (trajectory {D.trajectory_of(d, root)}); "
                  f"set: {', '.join(changed) or 'nothing'}")
            if d.reference_note:
                print(f"note: {d.reference_note}")
        else:
            print(f"{d.name}: a reference (trajectory {d.trajectory})")
    except Exception as exc:                       # every problem, with the key and the allowed values
        print(f"{a.name}: {exc}", file=sys.stderr)
        return 1
    return 0


def _list(a) -> int:
    for name, kind in sorted(D.available().items(), key=lambda t: (t[1], t[0])):
        print(f"{kind:10s} {name}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m capri_mod.scenarios", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new")
    p.add_argument("name")
    p.add_argument("--reference", required=True)
    p.add_argument("--group", default="")
    p.add_argument("--dir", default="")
    p = sub.add_parser("check")
    p.add_argument("name")
    p.add_argument("--dir", default="")
    sub.add_parser("list")
    a = ap.parse_args(argv)
    run = {"new": _new, "check": _check, "list": _list}[a.cmd]
    if not getattr(a, "dir", ""):
        return run(a)
    # --dir holds for this command only: the previous settings come back (main is also called from tests)
    from capri_mod import settings as S
    prev = S.current()
    S.activate(S.load([], overrides={"run.scenarios_dir": a.dir}))
    try:
        return run(a)
    finally:
        S.activate(prev)


if __name__ == "__main__":
    raise SystemExit(main())
