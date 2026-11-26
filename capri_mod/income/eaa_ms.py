r"""CAPRI's economic accounts at producer prices of a member state at the solution (income I2c; reports/sol_simy.gms,
star 3.0; the statements in coupling/equations/sol_simy_ms.py and sol_simy.py).

CAPRI's member-state row nets the farms' own use out of each item (l. 1964-1970: NETF = GROF - SEDF - LOSF - INTF) and
values the net at UVAP = UVAG x NETF / GROF (l. 2389-2390), so EAAP = NETF x UVAP / 1000 (l. 2547) is EAAG x
(NETF / GROF)^2; TOOU and TOIN are the sums over CAPRI's outputs and inputs (l. 2557-2558), GVAP their difference and
MGVA GVAP + PRME (l. 2560-2562). The farm balance's positions:
  SEDF, LOSF  a final product's (END) seed and losses on farm in proportion to its production at "CUR" (l. 1889-1898):
              ms_farm_balance_<year>.csv (sim_ini_21730's DATA at "Y" for 2030, "BAS" for the base year; tools/build/
              build_ms_farm_balance.py); CAPRI's fodder crops' LOSF is their on-farm share (p_onFarmShare, K213)
  INTF        the young animals bought, all internal (IYANI, l. 789-791), and on the output side the heads used of the
              same young animals (OYANI, l. 793-799); the fertiliser nutrients' need less the purchases (l. 866), the
              purchases the sum over the member state's regions (l. 315); the manure (FOUT) applied or lost, so its NETF
              is 0 (l. 870-874)
  the rest    NETF = GROF: the feeds, the other inputs, the products outside END.

The model's member state: the sum of its units' gross accounts by item (income/eaa.py eaag_items, by_act) in CAPRI's
codes, computed only where all of the member state's units (capri_data/codes/regional_units.csv) are in the run:
  - a crop's product item (the model activity's code) is its CAPRI members' product (PACT_TO_Y; CORN MAIZ, GRAE and
    GRAI GRAS, WINE TWIN);
  - an animal's market product (MILK, POUL) is the product of CAPRI's output table at the same position
    (livestock_product_value_by_market_coef.csv against livestock_output_by_product_coef.csv: DCOW's MILK COMI, SHGM's
    MILK SGMI, POUL POUM);
  - an animal's other outputs (OTHER_O) by CAPRI output: its manure, its milk for feeding and its young animals
    (eaa._other_output_parts);
  - the fertiliser nutrients (NITF, PHOF, POTF) in quantity (kt), the young animals in heads (1000), the other items in
    value (GROF the value in EUR million and UVAG 1000, as the regional account's), NETF / GROF being CAPRI's ratio in
    either.
PRME is the sum of the units' (eaap_eaab). EUR million, the model's 2017 money.

Departures from CAPRI:
  - the milk for feeding (COMF, SGMF) has NETF = GROF. CAPRI's 2030 reference has NETF = 2 GROF in Denmark (LOSF
    -105.9 kt = GROF - FEDM at the regional unit, l. 278, which for a member state of one unit is the member state's
    row; FEDM twice the output there) and NETF = GROF in the member states of several units;
  - the margins' input cost in one item (TOIN_lin, IY, OTHER_I, FERT) and the other outputs no young animal holds
    (OTHER_O: the poultry's chicks, which the model's young-animal tables do not have) are not CAPRI items: NETF = GROF
    and their value at basic prices that at producer prices (register DEP-56);
  - the young animals' heads are the young-animal tables' coefficients x the activity levels (the cattle member splits'
    columns not apart), their value the rest of the animals' other outputs over the categories they produce, by value.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

#: CAPRI's fertiliser nutrients (FNUT) and the manure outputs (FOUT)
FNUT = ("NITF", "PHOF", "POTF")
FOUT = ("MANN", "MANP", "MANK")


def crop_products() -> dict:
    """{model crop: CAPRI product} through its CAPRI members' PACT_TO_Y (capri_data/codes/capri/PACT_TO_Y.csv), where
    the members have one product."""
    from capri_mod.data.definitions import CAPRI_MEMBERS, capri_pairs
    p2y = defaultdict(set)
    for a, y in capri_pairs("PACT_TO_Y"):
        p2y[a].add(y)
    out = {}
    for a, ms in CAPRI_MEMBERS.items():
        ys = set().union(*(p2y.get(m, set()) for m in ms))
        if len(ys) == 1:
            out[a] = next(iter(ys))
    return out


def animal_products() -> dict:
    """{(model animal, market item): CAPRI output}: the outputs of an animal's output table (livestock_output_by_product_
    coef.csv, "ANIMAL.OUTPUT") and the market item of each (CAPRIModel.LIVESTOCK_PRODUCT_MARKET: COMI and SGMI MILK,
    POUM POUL, the others their own code)."""
    from capri_mod.model import CAPRIModel
    from capri_mod.supply import inputs as _inputs
    ocols = _inputs.current().csv("livestock_output_by_product_coef.csv", "supply", index_col=0, nrows=0).columns
    mkt = CAPRIModel.LIVESTOCK_PRODUCT_MARKET
    out = {}
    for c in ocols:
        a, o = str(c).split(".", 1)
        out[(a, mkt.get(o, o))] = o
    return out


def _uvab(it, uvag, bas, qform, defl, marr, ioe, io, DATA_UVAB_MARR, DATA_UVAB_IO_SIMY):
    """A member state's item's unit value at basic prices at the solution, in the model's money and the row's unit
    (module docstring): a market product (MARR) its UVAG plus the base year's wedge (sol_market.gms l. 1336-1337), in
    quantity only; a good outside the market part (NOT IOE) its base year UVAB by inflation (inflation_and_trend_
    interpolation.gms l. 70), in value as UVAB / UVAG of the base year; a CAPRI item without either None; the model's
    own items (outside IO) 1000 in value, their value as at producer prices. bas: (UVAG, UVAB) of the base year or
    None."""
    g0, b0 = (bas if bas is not None else (None, None))
    has_b = b0 is not None and b0 == b0 and float(b0) != 0.0
    if it in marr and has_b:
        return DATA_UVAB_MARR(float(uvag) * defl, b0, g0) / defl if qform else None
    if it not in ioe and has_b:
        u_ = DATA_UVAB_IO_SIMY(b0, defl) / defl
        if qform:
            return u_
        return 1000.0 * u_ / float(g0) if (g0 is not None and g0 == g0 and float(g0)) else None
    if it in io:
        return None
    return 1000.0


def _units_by_ms() -> dict:
    from capri_mod.data.definitions import _load_units
    out = defaultdict(set)
    for r, ms, _c in _load_units():
        out[ms].add(r)
    return out


def ms_accounts(supply_results, year=None) -> dict:
    """{member state: {"items": DataFrame (side, item: CAPRI's code, GROF, NETF, UVAG, UVAP, EAAG, EAAP), "EAAP":
    {TOOU, TOIN, GVAP, PRME, MGVA}}} for the member states all of whose units are in supply_results with their gross
    account (module docstring). year: the farm balance's ("CUR"); by default the run's market year (RunInputs.
    market_year), else the base year."""
    from capri_mod.coupling.equations.inflation_and_trend_interpolation import DATA_UVAB_IO_SIMY
    from capri_mod.coupling.equations.sol_simy import (DATA_EAAB_GVAB, DATA_EAAB_IO, DATA_EAAP_GVAP, DATA_EAAP_IO,
                                                       DATA_EAAP_MGVA, DATA_GEAAC_TOIN, DATA_GEAAC_TOOU)
    from capri_mod.data.inputs import money_deflator
    from capri_mod.market.equations.sol_market import DATA_UVAB_MARR
    from capri_mod.coupling.equations.sol_simy_ms import (DATA_INTF_FNUT, DATA_INTF_IYANI, DATA_INTF_OYANI,
                                                          DATA_LOSF_FOUT, DATA_LOSF_O_SIMY, DATA_NETF_FNUT_MSAGG,
                                                          DATA_NETF_MS, DATA_NETF_OYANI, DATA_SEDF_O_SIMY,
                                                          DATA_UVAP_MS)
    from capri_mod.data.definitions import capri_ms, capri_set
    from capri_mod.supply import inputs as _inputs
    eaa = {r: getattr(res, "eaa", None) for r, res in supply_results.items()}
    units = _units_by_ms()
    done = {}
    for r, e in eaa.items():
        ms = capri_ms(r)
        if ms in done or not units.get(ms):
            continue
        es = [eaa.get(u) for u in units[ms]]
        done[ms] = es if all(e_ and isinstance(e_.get("by_act"), pd.DataFrame) and e_.get("EAAP") for e_ in es) else None
    done = {ms: es for ms, es in done.items() if es}
    if not done:
        return {}
    inp = _inputs.current()
    year = year if year is not None else (getattr(inp, "market_year", None) or inp.base_year)
    year = int(year)
    name = f"ms_farm_balance_{year}.csv"

    def load(i):
        t = i.csv(name, "supply")
        return {(str(a), str(b)): (float(g), float(s), float(l_)) for a, b, g, s, l_ in
                zip(t.ms, t["product"], t.grof, t.sedf, t.losf)}
    cur = inp.cached(f"income_{name}", load)

    def load_uv(i):
        t = i.csv("ms_unit_values_2017.csv", "supply")
        return {(str(a), str(b)): (g, b_) for a, b, g, b_ in zip(t.ms, t["item"], t.uvag, t.uvab)}
    uvb = inp.cached("income_ms_unit_values_bas", load_uv)
    defl = money_deflator(year)
    end, marr, ioe, io = (set(capri_set(n)) for n in ("END", "MARR", "IOE", "IO"))
    cp, ap = crop_products(), animal_products()
    out = {}
    for ms, es in done.items():
        val = defaultdict(float)                       # (side, CAPRI item) -> EAAG
        qt, qv = defaultdict(float), defaultdict(float)  # (side, CAPRI item) -> GROF in quantity, the EAAG it covers
        fq, pur = defaultdict(float), defaultdict(list)  # FNUT: need kt; purchases kt by unit
        yh = defaultdict(lambda: [0.0, 0.0])           # OYANI: [heads produced, used]
        yu = defaultdict(float)                        # IYANI: heads used
        prme = 0.0
        for e in es:
            oo = e.get("other_o")
            oo = oo if isinstance(oo, pd.DataFrame) else pd.DataFrame(columns=["activity", "side", "item", "EAAG"])
            if "GROF" not in oo:
                oo = oo.assign(GROF=None)
            split = {(s_, a) for a, s_ in zip(oo.activity, oo.side)}
            pt = e.get("products_t")
            pt = ({(a, it): g for a, it, g in pt.itertuples(index=False)} if isinstance(pt, pd.DataFrame) else {})
            for side, it, a, v in e["by_act"].itertuples(index=False):
                if (side == "O" and it == "OTHER_O" or side == "I" and it == "YOUNG") and (side, a) in split:
                    continue
                if side == "O" and (a, it) in ap:
                    it = ap[(a, it)]
                    if (a, it) in pt:                  # the animal's product in quantity (1000 t)
                        qt[(side, it)] += pt[(a, it)]
                        qv[(side, it)] += float(v)
                elif side == "O" and it in cp:
                    it = cp[it]
                val[(side, it)] += float(v)
            for a, s_, it, v, g in oo[["activity", "side", "item", "EAAG", "GROF"]].itertuples(index=False):
                val[(s_, it)] += float(v)
                if g is not None and g == g:           # the manure and the milk for feeding in quantity (1000 t)
                    qt[(s_, it)] += float(g)
                    qv[(s_, it)] += float(v)
            for it, side, g, u, v in e["items"][["item", "side", "GROF", "UVAG", "EAAG"]].itertuples(index=False):
                if it in FNUT and side == "I" and float(u) != 1000.0:
                    fq[it] += float(g)
                elif float(u) != 1000.0:               # an item in quantity (1000 t): the crops', feeds', manure's
                    k_ = (side, cp.get(it, it) if side == "O" else it)
                    qt[k_] += float(g)
                    qv[k_] += float(v)
            p_ = e.get("purchases")
            if isinstance(p_, pd.DataFrame):
                for it, n in zip(p_["item"], p_.NETF):
                    pur[it].append(float(n))
            y_ = e.get("young")
            if isinstance(y_, pd.DataFrame):
                for it, ii, g, u in zip(y_["item"], y_["iyani"], y_.GROF, y_.USE):
                    yh[it][0] += float(g)
                    yh[it][1] += float(u)
                    yu[ii] += float(u)
            prme += float(e["EAAP"]["PRME"])
        rows = []
        for (side, it), eaag in sorted(val.items()):
            grof, uvag = eaag, 1000.0                  # value form
            if qt.get((side, it)) and abs(qv[(side, it)] - eaag) <= 1e-9 * max(1.0, abs(eaag)):
                grof, uvag = qt[(side, it)], eaag * 1000.0 / qt[(side, it)]          # all of it in quantity
            if side == "I" and it in FNUT and fq.get(it):
                grof = fq[it]
                uvag = eaag * 1000.0 / grof
                netf = DATA_NETF_MS(grof, INTF=DATA_INTF_FNUT(grof, DATA_NETF_FNUT_MSAGG(pur.get(it, []))))
            elif side == "I" and (it == "YOUNG" or it in yu):
                if yu.get(it):                         # the young animals bought in heads
                    grof = yu[it]
                    uvag = eaag * 1000.0 / grof
                netf = DATA_NETF_MS(grof, INTF=DATA_INTF_IYANI(grof))
            elif side == "O" and it in yh and yh[it][0] > 0:
                grof = yh[it][0]
                uvag = eaag * 1000.0 / grof
                netf = DATA_NETF_OYANI(grof, DATA_INTF_OYANI([DATA_INTF_IYANI(yh[it][1])]))
            elif side == "O" and it in FOUT:
                netf = DATA_NETF_MS(grof, LOSF=DATA_LOSF_FOUT(grof, 0.0))
            elif side == "O" and (ms, it) in cur:
                g0, s0, l0 = cur[(ms, it)]
                netf = DATA_NETF_MS(grof, SEDF=DATA_SEDF_O_SIMY(grof, s0, g0, it in end),
                                    LOSF=DATA_LOSF_O_SIMY(grof, l0, g0, it in end))
            else:
                netf = grof
            uvap = DATA_UVAP_MS(uvag, netf, grof)
            eaap = DATA_EAAP_IO(netf, uvap) if (netf and uvap is not None) else 0.0
            uvab = _uvab(it, uvag, uvb.get((ms, it)), uvag != 1000.0 or grof != eaag, defl, marr, ioe, io,
                         DATA_UVAB_MARR, DATA_UVAB_IO_SIMY)
            eaab = DATA_EAAB_IO(netf, uvab) if (netf and uvab is not None) else 0.0
            rows.append({"side": side, "item": it, "GROF": grof, "NETF": netf, "UVAG": uvag, "UVAP": uvap,
                         "UVAB": uvab, "EAAG": eaag, "EAAP": eaap, "EAAB": eaab})
        t = pd.DataFrame(rows, columns=["side", "item", "GROF", "NETF", "UVAG", "UVAP", "UVAB", "EAAG", "EAAP",
                                        "EAAB"])
        tou = DATA_GEAAC_TOOU(t.loc[t.side == "O", "EAAP"])
        tin = DATA_GEAAC_TOIN(t.loc[t.side == "I", "EAAP"])
        gvap = DATA_EAAP_GVAP(tou, tin)
        b_tou = DATA_GEAAC_TOOU(t.loc[t.side == "O", "EAAB"])
        b_tin = DATA_GEAAC_TOIN(t.loc[t.side == "I", "EAAB"])
        out[ms] = {"items": t, "EAAP": {"TOOU": tou, "TOIN": tin, "GVAP": gvap, "PRME": prme,
                                        "MGVA": DATA_EAAP_MGVA(gvap, prme)},
                   "EAAB": {"TOOU": b_tou, "TOIN": b_tin, "GVAB": DATA_EAAB_GVAB(b_tou, b_tin)}}
    return out
