r"""CAPRI's premium outlays per product and their budget columns at the solution (income I4; reports/feoga.gms l. 62-162,
policy/policy_sets.gms l. 1582-1593; the statements in coupling/equations/feoga.py).

CAPRI's report, per member state: each activity's premiums x its level go to its main output (PACT_TO_Y, sets.gms l.
5377-5445), FEOP(MS, O) in EUR million; the fallow land's and the voluntary set-aside's premiums (FALL, VSET) are spread
over the crops with a premium and a main output by their area; the same by budget (budEU, budPil1, budPil2, budNAT,
budRestEU), each activity's premium per unit paid from a budget being its premiums by payment x the budget's share of
the payment (p_budToPsdPay: Pillar I to the EU's Pillar I budget, Pillar II half to the EU's Pillar II budget and half
to the national budget, the national payments to the national budget).

What the model holds at the solution, per region: each activity's premium per unit (the regional model's premiums,
SupplyModule._compute_net_revenues) and level; the technology mix's premium difference on the area moved (ev.mix_parts,
added to its crop, as CAPRI weights the technologies' premiums, reports/sol_simy.gms l. 377-390); the share of each
activity's premium per main output and scheme aggregate in CAPRI's 2030 reference (premium_output_shares_2030.csv:
level-weighted over the activity's CAPRI members, so a model activity whose members have different main outputs, the
heifers and the calves, is split as CAPRI's members' premiums), and per scheme aggregate for FALL and VSET
(premium_scheme_shares_2030.csv). The scheme aggregates are CAPRI's p_aggToPsdPay groups: DPPIL1, DPNAT and the Pillar
II schemes DPRD_LFA, DPRD_N2K and DPAE (CAPRI's DPPIL2 = their sum: in CAPRI's 2030 reference, Denmark's soft wheat
DPPIL2 14.624 = DPRD_LFA 0.698 + DPAE 13.926 EUR/ha, its dairy cows 42.166 = DPAE). The member state's rows are those of
the run's units (all of a member state's units in a full-EU run). Register DEP-57.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

#: the scheme aggregates of premium_scheme_shares_2030.csv by CAPRI's p_aggToPsdPay group (policy/policy_sets.gms l.
#: 1209-1261: DPPIL2 is PSDPAY_RD, the rural development payments, of which the LFA, Natura 2000 and agri-environment
#: schemes)
SCHEME_GROUP = {"DPPIL1": "DPPIL1", "DPRD_LFA": "DPPIL2", "DPRD_N2K": "DPPIL2", "DPAE": "DPPIL2", "DPNAT": "DPNAT"}
BUDGETS = ("budEU", "budPil1", "budPil2", "budNAT", "budRestEU")
#: the idle land's activities whose premiums CAPRI spreads over the crops (reports/feoga.gms l. 120-135; the
#: obligatory set-aside ISET and TSET is not in the model)
IDLE = ("FALL", "VSET")


def feop_by_product(supply_results, supply_module, data) -> pd.DataFrame:
    """The premium outlays per member state and product at the solution (module docstring), EUR million: rows (member
    state, product), columns FEOP and the budgets. Empty without CAPRI's premium shares."""
    from capri_mod.coupling.equations.feoga import (DATA_FEOP_O, DATA_FEOP_O_idle, DATA_FEOP_UAAR, DATA_MPACT_psBudRows,
                                                    DATA_psBudCols_O, p_budToPsdPay)
    from capri_mod.data.definitions import CROPS, capri_ms
    so, ss = data.get("premium_output_shares_2030"), data.get("premium_scheme_shares_2030")
    if so is None or ss is None:
        return pd.DataFrame(columns=["FEOP", *BUDGETS])
    schemes = list(SCHEME_GROUP)
    pb = {s: p_budToPsdPay(SCHEME_GROUP[s]) for s in schemes}
    so = so.set_index(["region", "activity", "output"])[schemes].sort_index()
    has_out = set(so.index.droplevel(2))
    ss = ss.set_index(["region", "activity"])[schemes].sort_index()
    # per member state: (activity's main output, the activity's premium x level, its budgets' x level, level, crop?)
    parts = defaultdict(list)
    idle = defaultdict(list)
    for reg, res in supply_results.items():
        m = getattr(supply_module, "_models", {}).get(reg)
        acts = getattr(res, "activities", None)
        pr = getattr(m, "premiums", None) if m is not None else None
        if pr is None or acts is None:
            continue
        ms = capri_ms(reg)
        mz = dict(getattr(res, "technology_mix", None) or {})
        mp = dict(getattr(getattr(m, "ev", None), "mix_parts", None) or {})
        for a, p_a in pr.items():
            L = float(acts.get(a, 0.0) or 0.0)
            if L <= 0 or not float(p_a):
                continue
            # the premium per unit with the technology mix's difference on the area moved (CAPRI's DATA(SIMY) weights
            # the technologies' premiums)
            p_tot = float(p_a) + (float(mp[a]["PRME"]) * float(mz[a]) / L if a in mz and a in mp else 0.0)
            if a in IDLE:
                if (reg, a) in ss.index:
                    sh = ss.loc[(reg, a)]
                    idle[ms].append((a, p_tot, {b: DATA_MPACT_psBudRows([p_tot * float(sh[s]) for s in schemes],
                                                                        [pb[s][b] for s in schemes]) for b in BUDGETS},
                                     L))
                continue
            if (reg, a) not in has_out:
                continue
            for o, sh in so.loc[(reg, a)].iterrows():
                w = float(sh.sum())
                parts[ms].append((o, p_tot * w,
                                  {b: DATA_MPACT_psBudRows([p_tot * float(sh[s]) for s in schemes],
                                                           [pb[s][b] for s in schemes]) for b in BUDGETS},
                                  L, a in CROPS))
    rows = {}
    for ms, ps in parts.items():
        outs = sorted({o for o, *_ in ps})
        feop = {o: DATA_FEOP_O([p for o_, p, _b, _l, _c in ps if o_ == o], [l_ for o_, _p, _b, l_, _c in ps if o_ == o])
                for o in outs}
        bud = {o: {b: (DATA_psBudCols_O([bb[b] for o_, _p, bb, _l, _c in ps if o_ == o],
                                        [l_ for o_, _p, _bb, l_, _c in ps if o_ == o]) if feop[o] else 0.0)
                   for b in BUDGETS} for o in outs}
        # the idle land's premiums per 1000 ha of the crops with a premium (and with the budget's premium)
        crops = [(o, l_, bb) for o, p, bb, l_, c in ps if c and p]
        iu = idle.get(ms, [])
        u = DATA_FEOP_UAAR([p for _a, p, _b, _l in iu], [l_ for _a, _p, _b, l_ in iu], [l_ for _o, l_, _bb in crops])
        ub = {b: DATA_FEOP_UAAR([bb[b] for _a, _p, bb, _l in iu], [l_ for _a, _p, _bb, l_ in iu],
                                [l_ for _o, l_, bb in crops if bb[b]]) for b in BUDGETS}
        for o in outs:
            lc = [l_ for o_, l_, _bb in crops if o_ == o]
            rows[(ms, o)] = {"FEOP": DATA_FEOP_O_idle(feop[o], lc, u),
                             **{b: DATA_FEOP_O_idle(bud[o][b], lc, ub[b]) for b in BUDGETS}}
    out = pd.DataFrame.from_dict(rows, orient="index", columns=["FEOP", *BUDGETS])
    out.index = pd.MultiIndex.from_tuples(out.index, names=["member_state", "product"]) if len(out) else out.index
    return out
