"""CAPRI's aggregates of the accounts and of the welfare by product (capri_mod/income/eaa_aggregates.py;
reports/aggreg_res_data.gms l. 50-91, sol_simy.gms l. 2317-2403, welfare.gms l. 861-902), by hand."""
import pandas as pd
import pytest


def _acc(scale=1.0):
    rows = [("O", "SWHE", 100.0, 90.0, 150.0), ("O", "DWHE", 10.0, 9.0, 200.0), ("O", "BARL", 50.0, 40.0, 120.0),
            ("O", "OANI", 30.0, 30.0, 1000.0), ("O", "EGGS", 5.0, 5.0, 1300.0), ("I", "NITF", 20.0, 12.0, 1000.0),
            ("I", "FCER", 40.0, 40.0, 110.0), ("I", "TOIN_lin", 3.0, 3.0, 1000.0)]
    t = pd.DataFrame([{"side": s, "item": i, "GROF": g * scale, "NETF": n * scale, "UVAG": u,
                       "EAAG": g * scale * u / 1000.0} for s, i, g, n, u in rows])
    t.loc[t["item"] == "OANI", ["GROF", "NETF"]] = [t.loc[t["item"] == "OANI", "EAAG"].iloc[0]] * 2   # value form
    t.loc[t["item"] == "NITF", "UVAG"] = 1062.5                                                       # in quantity
    t["EAAG"] = t.GROF * t.UVAG / 1000.0
    t["UVAP"] = t.UVAG * t.NETF / t.GROF
    t["UVAB"] = t.UVAP
    t["EAAP"] = t.NETF * t.UVAP / 1000.0
    t["EAAB"] = t.EAAP
    return {"items": t, "EAAP": {"PRME": 7.0 * scale}}


def test_the_product_and_account_aggregates():
    """CERE the cereals' rows without WHEA (l. 50-51): its EAAG, GROF, NETF the sums, UVAG their ratio (l. 53-91);
    an aggregate with a row in value (OANP: OANI) has no quantity; TOOA the gross account's TOOU, CRPA the crop
    aggregates', PRMA PRME, AGGA MGVA (l. 83-84)."""
    from capri_mod.income.eaa_aggregates import eaag_totals, product_aggregates
    a = _acc()
    tot = eaag_totals(a)
    t = a["items"].set_index("item")
    assert tot["TOOU"] == pytest.approx(t.loc[t.side == "O", "EAAG"].sum()) and tot["PRME"] == 7.0
    ag = product_aggregates(a["items"], tot).set_index("item")
    cere = t.loc[["SWHE", "DWHE", "BARL"]]
    assert ag.at["CERE", "EAAG"] == pytest.approx(cere.EAAG.sum())
    assert ag.at["CERE", "GROF"] == pytest.approx(160.0) and ag.at["CERE", "NETF"] == pytest.approx(139.0)
    assert ag.at["CERE", "UVAG"] == pytest.approx(cere.EAAG.sum() / 160.0 * 1000.0)
    assert ag.at["OANP", "EAAG"] == pytest.approx(t.loc[["OANI", "EGGS"], "EAAG"].sum())
    assert pd.isna(ag.at["OANP", "GROF"])
    assert ag.at["TOOA", "EAAG"] == pytest.approx(tot["TOOU"]) and ag.at["PRMA", "EAAG"] == 7.0
    assert ag.at["AGGA", "EAAG"] == pytest.approx(tot["MGVA"])
    assert ag.at["CRPA", "EAAG"] == pytest.approx(ag.at["CERE", "EAAG"])
    assert ag.at["FERC", "EAAG"] == pytest.approx(t.at["NITF", "EAAG"])
    assert ag.at["TOIA", "EAAG"] == pytest.approx(t.loc[["NITF", "FCER"], "EAAG"].sum())      # the model's own items out


def test_the_regional_aggregates_need_all_their_member_states():
    """A_EU_WEST's thirteen member states (MAP_RR): with all of them its rows are the sums, UVAG weighted by GROF and
    UVAP by NETF (l. 2321-2403); with one missing none."""
    from capri_mod.data.definitions import capri_pairs
    from capri_mod.income.eaa_aggregates import regional_accounts
    west = sorted(m for r, m in capri_pairs("MAP_RR") if r == "A_EU_WEST")
    assert len(west) == 13 and "DK000000" in west
    acc = {m: _acc(1.0 + i) for i, m in enumerate(west)}
    out = regional_accounts(acc)
    assert "A_EU_WEST" in out and "A_EU_EAST" not in out
    t = out["A_EU_WEST"]["items"].set_index("item")
    sw = [acc[m]["items"].set_index("item").loc["SWHE"] for m in west]
    assert t.at["SWHE", "GROF"] == pytest.approx(sum(r.GROF for r in sw))
    assert t.at["SWHE", "EAAP"] == pytest.approx(sum(r.EAAP for r in sw))
    assert t.at["NITF", "UVAP"] == pytest.approx(sum(r.NETF * r.UVAP for r in
                                                     [acc[m]["items"].set_index("item").loc["NITF"] for m in west])
                                                 / t.at["NITF", "NETF"])
    e = out["A_EU_WEST"]["EAAP"]
    assert e["PRME"] == pytest.approx(7.0 * sum(1.0 + i for i in range(13)))
    assert e["MGVA"] == pytest.approx(e["TOOU"] - e["TOIN"] + e["PRME"])
    del acc[west[0]]
    assert "A_EU_WEST" not in regional_accounts(acc)


def test_the_welfare_by_product_aggregates():
    """The welfare's product aggregates per region (R_T_OAGG(OAGG, XX), l. 897: CERE with WHEA) and the market
    region's rows the member states' sums (RMS_TO_RM, l. 864-868), only where all its member states are."""
    from capri_mod.data.definitions import capri_pairs
    from capri_mod.income.eaa_aggregates import welfare_aggregates
    east = sorted(m for m, r in capri_pairs("RMS_TO_RM") if r == "A_EU_EAST")
    rows = {}
    for m in east:
        rows[(m, "WHEA")] = {"ProfitAgr": 10.0, "PSEs": -2.0}
        rows[(m, "BARL")] = {"ProfitAgr": 5.0, "PSEs": float("nan")}
    wp = pd.DataFrame.from_dict(rows, orient="index")
    wp.index = pd.MultiIndex.from_tuples(wp.index, names=["member_state", "product"])
    out = welfare_aggregates(wp)
    assert out.at[(east[0], "CERE"), "ProfitAgr"] == pytest.approx(15.0)
    assert out.at[(east[0], "CERE"), "PSEs"] == pytest.approx(-2.0)
    assert out.at[("A_EU_EAST", "WHEA"), "ProfitAgr"] == pytest.approx(10.0 * len(east))
    assert out.at[("A_EU_EAST", "CERE"), "ProfitAgr"] == pytest.approx(15.0 * len(east))
    assert ("A_EU_WEST", "WHEA") not in out.index
