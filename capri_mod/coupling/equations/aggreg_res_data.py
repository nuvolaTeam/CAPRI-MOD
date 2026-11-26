r"""CAPRI's aggregates of the reports' rows (reports/aggreg_res_data.gms, star 3.0): the product aggregates' (OAGG)
balance positions and values in the economic accounts, the accounts' aggregates (EAAGA) and the aggregates' unit
values. capri_mod/income/eaa_aggregates.py applies them to a member state's accounts (income I2c).
"""
from __future__ import annotations


def R_T_OAGG_REPORT(pairs):
    r"""R_T_OAGG as the report's aggregation uses it: CAPRI's links of rows to aggregates less wheat in the cereals and
    the dairies' raw milk in the other animal products (which double count soft and durum wheat and the farms' milk).

    CAPRI's GAMS (reports/aggreg_res_data.gms l. 50-51):

             R_T_OAGG("CERE","WHEA") = NO;
             R_T_OAGG("OANP","MILK") = NO;

    In this project's notation: the pairs (aggregate, row) of R_T_OAGG but (CERE, WHEA) and (OANP, MILK). Departures from
    CAPRI: none."""
    return [(a, r) for a, r in pairs if (a, r) not in (("CERE", "WHEA"), ("OANP", "MILK"))]


def p_dataCopy_GROF_OAGG(GROF_ROWS):
    r"""p_dataCopy(RSS, "GROF", OAGG): a product aggregate's gross production, the sum over its rows.

    CAPRI's GAMS (reports/aggreg_res_data.gms l. 53):

             p_dataCopy(RSS,"GROF",OAGG,%1)     = SUM(R_T_OAGG(OAGG,ROWS), data(RSS,"GROF",ROWS,%1));

    Departures from CAPRI: none (the model sums it where all of the aggregate's rows are in quantity: eaa_aggregates)."""
    return float(sum(float(v) for v in GROF_ROWS))


def p_dataCopy_BALPOS_OAGG(BALPOS_ROWS):
    r"""p_dataCopy(RSST, BALPOS, OAGG): a product aggregate's balance position (NETF here), the sum over its rows.

    CAPRI's GAMS (reports/aggreg_res_data.gms l. 55):

             p_dataCopy(RSST,BALPOS,OAGG,%1)    = SUM(R_T_OAGG(OAGG,ROWS), data(RSST,BALPOS,ROWS,%1));

    Departures from CAPRI: none (as p_dataCopy_GROF_OAGG)."""
    return float(sum(float(v) for v in BALPOS_ROWS))


def p_dataCopy_EAAG_OAGG(EAAG_ROWS):
    r"""p_dataCopy(RSS, "EAAG", OAGG): a product aggregate's value in the gross account, the sum over its rows'.

    CAPRI's GAMS (reports/aggreg_res_data.gms l. 79):

             p_dataCopy(RSS,"EAAG",OAGG,%1)    = SUM(R_T_OAGG(OAGG,ROWS), data(RSS,"EAAG",ROWS,%1));

    Departures from CAPRI: none."""
    return float(sum(float(v) for v in EAAG_ROWS))


def p_dataCopy_EAAG_EAAGA(EAAG_ROWS, EAAG_OAGG_NOT_ROWS=()):
    r"""p_dataCopy(RSS, "EAAG", EAAGA): an aggregate of the economic accounts (TOOA, CRPA, ANIA, TOIA, CRPI, ANMI, RESI,
    PRMA, AGGA, RESA), the sum over its members: the rows and the product aggregates already summed (p_dataCopy holds
    both), and the product aggregates outside ROWS.

    CAPRI's GAMS (reports/aggreg_res_data.gms l. 83-84):

             p_dataCopy(RSS,"EAAG",EAAGA,%1)   =   SUM(R_T_OAGG(EAAGA,ROWS),  p_dataCopy(RSS,"EAAG",ROWS,%1))
                                                 + SUM(R_T_OAGG(EAAGA,OAGG) $ (not ROWS(OAGG)),  p_dataCopy(RSS,"EAAG",OAGG,%1));

    Departures from CAPRI: none."""
    return float(sum(float(v) for v in EAAG_ROWS)) + float(sum(float(v) for v in EAAG_OAGG_NOT_ROWS))


def p_dataCopy_UVAG_OAGG(EAAG, GROF):
    r"""p_dataCopy(RSS, "UVAG", OAGG): a product aggregate's unit value, its value over its production (EUR per t);
    None where GROF is 0.

    CAPRI's GAMS (reports/aggreg_res_data.gms l. 90-91):

             p_dataCopy(RSS,"UVAG",OAGG,%1) $ p_dataCopy(RSS,"GROF",OAGG,%1)
                                          = p_dataCopy(RSS,"EAAG",OAGG,%1)/p_dataCopy(RSS,"GROF",OAGG,%1) * 1000.;

    Departures from CAPRI: none."""
    return float(EAAG) / float(GROF) * 1000.0 if float(GROF) else None
