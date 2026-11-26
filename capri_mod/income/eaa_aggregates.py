r"""CAPRI's aggregates of the accounts and of the welfare by product (star 3.0): the product and account aggregates of a
member state's or a regional aggregate's accounts (reports/aggreg_res_data.gms l. 50-91), the regional aggregates of
the member states' accounts (reports/sol_simy.gms l. 2317-2403, 2547-2562) and of the welfare by product (reports/
welfare.gms l. 861-868, 897, 901-902). The statements are in coupling/equations/aggreg_res_data.py, sol_simy_ms.py,
sol_simy.py and market/equations/welfare.py; the sets CAPRI's as its run built them (capri_data/codes/capri: R_T_OAGG,
OAGG, EAAGA, REGAGG, MAP_RR, RMS_TO_RM, RW_TO_RM).

  product_aggregates   the product aggregates OAGG (CERE, OILS, MEAS, ALLP, the inputs' FEEC, FERC, ...): EAAG the sum
                       over their rows (R_T_OAGG less CERE's WHEA and OANP's MILK, l. 50-51), GROF and NETF the sums,
                       UVAG their ratio; then the accounts' aggregates EAAGA (TOOA, CRPA, ANIA, TOIA, CRPI, ANMI, RESI,
                       PRMA, AGGA, RESA) the sums over their rows and product aggregates. The data rows TOOU, TOIN, PRME,
                       MGVA are the account's EAAG totals (sol_simy.gms l. 2557-2566).
  regional_accounts    a regional aggregate of REGAGG (A_EU_WEST, A_EU_EAST, EU_WEST, EU_EAST, EU, EU27yr19, ...) where
                       all its member states (MAP_RR) have their accounts: GROF and NETF the sums (l. 2321-2322), UVAG,
                       UVAP, UVAB the member states' weighted by GROF and NETF (l. 2365-2403), EAAG, EAAP, EAAB from
                       them (l. 2547-2549; the sums), the totals (l. 2557-2562), PRME the member states' sum.
  welfare_aggregates   the welfare by product's product aggregates per region (R_T_OAGG(OAGG, XX), l. 897), the market
                       regions' rows (RMS_TO_RM, l. 864-868) and the world regions' (RW_TO_RM, l. 901-902), where all
                       their members are in the table.

Departures from CAPRI: a product aggregate's GROF, NETF and UVAG are reported only where all its rows are in quantity
(CAPRI sums its rows' quantities; the model holds some rows in value alone: the animals' other outputs and inputs in one
item, OANI); an item a regional aggregate's member states hold in different forms is summed in value. The model's own
items (TOIN_lin, IY, OTHER_I, FERT, OTHER_O) are in no aggregate: TOIA and the input aggregates leave them out (TOIN holds
them). The welfare's market-model products (MARRC, l. 751-780) are not split.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

#: the account's total rows in the EAAG data (sol_simy.gms l. 2557-2566)
TOTALS = ("TOOU", "TOIN", "PRME", "MGVA")


def _sets():
    from capri_mod.coupling.equations.aggreg_res_data import R_T_OAGG_REPORT
    from capri_mod.data.definitions import capri_pairs, capri_set
    pairs = list(capri_pairs("R_T_OAGG"))
    return {"report": R_T_OAGG_REPORT(pairs), "all": pairs, "OAGG": list(capri_set("OAGG")),
            "EAAGA": list(capri_set("EAAGA")), "ROWS": set(capri_set("ROWS"))}


def product_aggregates(items: pd.DataFrame, eaag_totals: dict) -> pd.DataFrame:
    """The product and account aggregates of one account (module docstring): DataFrame item (CAPRI's aggregate code),
    GROF, NETF, UVAG (None where a row is in value), EAAG. items: the account's rows (item, GROF, NETF, UVAG, EAAG; a
    row in value has UVAG 1000 and GROF its EAAG); eaag_totals: {TOOU, TOIN, PRME, MGVA} of the gross account."""
    from capri_mod.coupling.equations.aggreg_res_data import (p_dataCopy_BALPOS_OAGG, p_dataCopy_EAAG_EAAGA,
                                                              p_dataCopy_EAAG_OAGG, p_dataCopy_GROF_OAGG,
                                                              p_dataCopy_UVAG_OAGG)
    st = _sets()
    eaag, q = dict(eaag_totals), {}
    for it, g, n, u, v in items[["item", "GROF", "NETF", "UVAG", "EAAG"]].itertuples(index=False):
        eaag[it] = eaag.get(it, 0.0) + float(v)
        qf = float(u) != 1000.0 or float(g) != float(v)
        q[it] = (float(g), float(n)) if qf else None
    mem = defaultdict(list)
    for a, r in st["report"]:
        mem[a].append(r)
    rows, p = [], dict(eaag)
    for a in st["OAGG"]:
        ms = [r for r in mem.get(a, ()) if r in eaag]
        if not ms:
            continue
        v = p_dataCopy_EAAG_OAGG([eaag[r] for r in ms])
        qs = [q.get(r) for r in ms]
        g = n = u = None
        if all(x is not None for x in qs):
            g = p_dataCopy_GROF_OAGG([x[0] for x in qs])
            n = p_dataCopy_BALPOS_OAGG([x[1] for x in qs])
            u = p_dataCopy_UVAG_OAGG(v, g)
        p[a] = v
        rows.append({"item": a, "GROF": g, "NETF": n, "UVAG": u, "EAAG": v})
    done = {r["item"]: r for r in rows}
    for a in st["EAAGA"]:
        ms = [r for r in mem.get(a, ()) if r in p]
        if not ms:
            continue
        v = p_dataCopy_EAAG_EAAGA([p[r] for r in ms if r in st["ROWS"]], [p[r] for r in ms if r not in st["ROWS"]])
        p[a] = v
        if a in done:
            done[a].update({"EAAG": v, "GROF": None, "NETF": None, "UVAG": None})
        else:
            done[a] = {"item": a, "GROF": None, "NETF": None, "UVAG": None, "EAAG": v}
    return pd.DataFrame(list(done.values()), columns=["item", "GROF", "NETF", "UVAG", "EAAG"])


def regional_accounts(ms_acc: dict) -> dict:
    """{regional aggregate: {"items", "EAAP", "EAAB", "EAAG"}} for CAPRI's REGAGG all of whose member states (MAP_RR,
    the member states of CAPRI's MS) are in ms_acc (eaa_ms.ms_accounts' output); module docstring."""
    from capri_mod.coupling.equations.sol_simy import (DATA_EAAB_GVAB, DATA_EAAB_IO, DATA_EAAG_IO, DATA_EAAP_GVAP,
                                                       DATA_EAAP_IO, DATA_EAAP_MGVA, DATA_GEAAC_TOIN, DATA_GEAAC_TOOU)
    from capri_mod.coupling.equations.sol_simy_ms import (DATA_BALPOS_REGAGG, DATA_UVAB_REGAGG, DATA_UVAG_REGAGG,
                                                          DATA_UVAP_REGAGG)
    from capri_mod.data.definitions import capri_pairs, capri_set
    msset = set(capri_set("MS"))
    members = defaultdict(set)
    for r, m in capri_pairs("MAP_RR"):
        if m in msset:
            members[r].add(m)
    out = {}
    for ra in capri_set("REGAGG"):
        ms = members.get(ra, set())
        if ra in msset or not ms or not all(m in ms_acc for m in ms):
            continue
        recs = defaultdict(list)                     # (side, item) -> the member states' rows
        for m in sorted(ms):
            for r in ms_acc[m]["items"].to_dict("records"):
                recs[(r["side"], r["item"])].append(r)
        rows = []
        for (side, it), rs in sorted(recs.items()):
            qf = [float(r["UVAG"]) != 1000.0 or float(r["GROF"]) != float(r["EAAG"]) for r in rs]
            if any(qf) and not all(qf):              # different forms: all in value
                rs = [_in_value(r) for r in rs]
            grof = DATA_BALPOS_REGAGG([r["GROF"] for r in rs])
            netf = DATA_BALPOS_REGAGG([r["NETF"] for r in rs])
            uvag = DATA_UVAG_REGAGG([r["GROF"] for r in rs], [r["UVAG"] for r in rs], grof)
            uvap = DATA_UVAP_REGAGG([r["NETF"] for r in rs], [_v(r.get("UVAP")) for r in rs], netf)
            uvab = DATA_UVAB_REGAGG([r["NETF"] for r in rs], [_v(r.get("UVAB")) for r in rs], netf)
            rows.append({"side": side, "item": it, "GROF": grof, "NETF": netf, "UVAG": uvag, "UVAP": uvap,
                         "UVAB": uvab,
                         "EAAG": DATA_EAAG_IO(grof, uvag) if uvag is not None else float(sum(r["EAAG"] for r in rs)),
                         "EAAP": DATA_EAAP_IO(netf, uvap) if uvap is not None else 0.0,
                         "EAAB": DATA_EAAB_IO(netf, uvab) if uvab is not None else 0.0})
        t = pd.DataFrame(rows, columns=["side", "item", "GROF", "NETF", "UVAG", "UVAP", "UVAB", "EAAG", "EAAP",
                                        "EAAB"])
        prme = float(sum(ms_acc[m]["EAAP"]["PRME"] for m in ms))
        tou, tin = DATA_GEAAC_TOOU(t.loc[t.side == "O", "EAAP"]), DATA_GEAAC_TOIN(t.loc[t.side == "I", "EAAP"])
        gvap = DATA_EAAP_GVAP(tou, tin)
        b_tou, b_tin = DATA_GEAAC_TOOU(t.loc[t.side == "O", "EAAB"]), DATA_GEAAC_TOIN(t.loc[t.side == "I", "EAAB"])
        out[ra] = {"items": t, "EAAP": {"TOOU": tou, "TOIN": tin, "GVAP": gvap, "PRME": prme,
                                        "MGVA": DATA_EAAP_MGVA(gvap, prme)},
                   "EAAB": {"TOOU": b_tou, "TOIN": b_tin, "GVAB": DATA_EAAB_GVAB(b_tou, b_tin)},
                   "members": sorted(ms)}
    return out


def _v(x):
    return None if x is None or x != x else float(x)


def _in_value(r):
    """A row in value: GROF its EAAG, NETF in proportion, UVAG 1000, UVAP and UVAB per 1000 of value."""
    g, u = float(r["GROF"]), float(r["UVAG"])
    if u == 1000.0 and g == float(r["EAAG"]):
        return r
    f = float(r["EAAG"]) / g if g else 0.0          # the value per unit of GROF / 1000 x 1000
    out = dict(r)
    out.update({"GROF": float(r["EAAG"]), "NETF": float(r["NETF"]) * f, "UVAG": 1000.0,
                "UVAP": (1000.0 * _v(r.get("UVAP")) / u) if _v(r.get("UVAP")) is not None and u else None,
                "UVAB": (1000.0 * _v(r.get("UVAB")) / u) if _v(r.get("UVAB")) is not None and u else None})
    return out


def eaag_totals(acc: dict) -> dict:
    """{TOOU, TOIN, PRME, MGVA} of an account's gross account: the items' EAAG sums, PRME EAAP's (l. 2557-2566)."""
    from capri_mod.coupling.equations.sol_simy import DATA_EAAG_MGVA, DATA_GEAAC_TOIN, DATA_GEAAC_TOOU
    t = acc["items"]
    tou, tin = DATA_GEAAC_TOOU(t.loc[t.side == "O", "EAAG"]), DATA_GEAAC_TOIN(t.loc[t.side == "I", "EAAG"])
    prme = float(acc["EAAP"]["PRME"])
    return {"TOOU": tou, "TOIN": tin, "PRME": prme, "MGVA": DATA_EAAG_MGVA(tou, tin, prme)}


def _sum_or_nan(fn, vals):
    v = [x for x in vals if x == x]
    return fn(v) if v else float("nan")


def accounts(supply_results, year=None) -> dict:
    """The member states' accounts (eaa_ms.ms_accounts) and the regional aggregates' (regional_accounts), each with its
    gross account's totals ("EAAG") and its product and account aggregates ("aggregates"); {} where no member state is
    complete."""
    from capri_mod.income.eaa_ms import ms_accounts
    acc = ms_accounts(supply_results, year)
    acc.update(regional_accounts(acc))
    for a in acc.values():
        a["EAAG"] = eaag_totals(a)
        a["aggregates"] = product_aggregates(a["items"], a["EAAG"])
    return acc


def welfare_aggregates(wp: pd.DataFrame) -> pd.DataFrame:
    """The welfare by product (welfare_products.welfare_by_product's table: rows (member state, product), columns
    ProfitAgr, PSEs) with the market regions' and the world regions' rows where all their members are in it, and every
    region's product aggregates (module docstring)."""
    from capri_mod.data.definitions import capri_pairs, capri_set
    from capri_mod.market.equations.welfare import p_welfareRes_OAGG, p_welfareRes_RW, p_welfareRes_rmAgg
    if wp is None or not len(wp):
        return wp
    cols = list(wp.columns)
    tab = {reg: g.droplevel(0) for reg, g in wp.groupby(level=0)}

    def up(groups, fn):
        mem = defaultdict(set)
        for a, b in groups:
            mem[b].add(a)
        new = {}
        for agg, ms in mem.items():
            if agg in tab or not all(m in tab for m in ms):
                continue
            prods = sorted(set().union(*(set(tab[m].index) for m in ms)))
            new[agg] = pd.DataFrame({c: [_sum_or_nan(fn, [tab[m].at[p_, c] for m in ms if p_ in tab[m].index])
                                         for p_ in prods] for c in cols}, index=prods)
        tab.update(new)
    up(capri_pairs("RMS_TO_RM"), p_welfareRes_rmAgg)
    up(capri_pairs("RW_TO_RM"), p_welfareRes_RW)
    xx = set(capri_set("XX"))
    mem = defaultdict(list)
    for a, r in capri_pairs("R_T_OAGG"):
        if r in xx:
            mem[a].append(r)
    for reg, t in tab.items():
        add = {}
        for a in capri_set("OAGG"):
            ps = [r for r in mem.get(a, ()) if r in t.index]
            if ps:
                add[a] = {c: _sum_or_nan(p_welfareRes_OAGG, [t.at[r, c] for r in ps]) for c in cols}
        if add:
            tab[reg] = pd.concat([t, pd.DataFrame.from_dict(add, orient="index")[cols]])
    out = pd.concat(tab, names=["member_state", "product"])
    return out.sort_index()
