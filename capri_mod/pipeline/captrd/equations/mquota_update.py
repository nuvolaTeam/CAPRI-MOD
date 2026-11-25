r"""CAPTRD's statements of pol_input/mquota_update.gms (CAPRI star 3.0, batincluded by captrd/captrd_policy.gms l. 40
with Years ORDT p_data BASM): the milk quotas in p_data, as named functions.

CAPRI's GAMS statement of each block is in the docstring of the function that computes it (one function per statement
block, named after the assigned symbol). capri_mod/pipeline/captrd/policy.py (milk_quotas) holds the loops over the
countries and the years, the data and the conditions, and calls them; the arithmetic is the port's, so the quotas are
unchanged.
"""
from __future__ import annotations


def p_MQuotaDat_BL(be, lu):
    r"""p_MQuotaDat("BL000000", MQuotaInfo, simyy): Belgium and Luxembourg's quota data summed.

    CAPRI's GAMS (pol_input/mquota_update.gms l. 32-32):

           p_MQuotaDat("BL000000",MQuotaInfo,simyy) = p_MQuotaDat("BE000000",MQuotaInfo,simyy) + p_MQuotaDat("LU000000",MQuotaInfo,simyy) ;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.milk_quotas)."""
    return be + lu


def PMquotaReg_QUTtot(qut_tot):
    r"""PMquotaReg(MS, "QUTtot", Years): the total quota in t (the table's 1000 t x 1000).

    CAPRI's GAMS (pol_input/mquota_update.gms l. 67-67):

            PMquotaReg(MS,"QUTtot",%1) = PMquotaReg(MS,"QUTtot",%1) * 1000;

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.milk_quotas)."""
    return qut_tot * 1000.0


def PMquotaReg_QUTtot_before2004(qut_del, qut_dir):
    r"""PMquotaReg(MS, "QUTtot", Years) before 2004: the delivery and direct-sales quotas summed.

    CAPRI's GAMS (pol_input/mquota_update.gms l. 70-71):

            PMquotaReg(MS,"QUTtot",%1)  $ (%2(%1) LT %2("2004"))
                                  = (p_MQuotaDat(MS,"QUTdel",%1)+p_MQuotaDat(MS,"QUTdir",%1));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.milk_quotas)."""
    return qut_del + qut_dir


def PPQuotas_QTot(qut_tot):
    r"""PPQuotas(MS, "QTot", Years): the total quota.

    CAPRI's GAMS (pol_input/mquota_update.gms l. 73-73):

            PPQuotas(MS,"QTot",%1) = PMquotaReg(MS,"QUTtot",%1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.milk_quotas)."""
    return qut_tot


def PPQuotas_QDel_QDir(qut_del, qut_dir, qtot):
    r"""PPQuotas(MS, "QDel" / "QDir", Years): the total quota split by the delivery and direct-sales quotas' shares
    (where their sum is nonzero). Returns (QDel, QDir).

    CAPRI's GAMS (pol_input/mquota_update.gms l. 83-87):

            PPQuotas(MS,"QDel",%1) $ (p_MQuotaDat(MS,"QUTdel",%1)+p_MQuotaDat(MS,"QUTdir",%1))
                                      = p_MQuotaDat(MS,"QUTDel",%1)*PPQuotas(MS,"QTot",%1)/(p_MQuotaDat(MS,"QUTdel",%1)+p_MQuotaDat(MS,"QUTdir",%1));

            PPQuotas(MS,"QDir",%1) $ (p_MQuotaDat(MS,"QUTdel",%1)+p_MQuotaDat(MS,"QUTdir",%1))
                                      = p_MQuotaDat(MS,"QUTDir",%1)*PPQuotas(MS,"QTot",%1)/(p_MQuotaDat(MS,"QUTdel",%1)+p_MQuotaDat(MS,"QUTdir",%1));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.milk_quotas)."""
    den = qut_del + qut_dir
    return qut_del * qtot / den, qut_dir * qtot / den


def PPQuotas_Deli_DirS(observed):
    r"""PPQuotas(MS, "Deli" / "DirS", Years): the observed deliveries and direct sales.

    CAPRI's GAMS (pol_input/mquota_update.gms l. 90-91):

            PPQuotas(MS,"Deli",%1)= p_MQuotaDat(MS,"Delivs",%1);
            PPQuotas(MS,"DirS",%1)= p_MQuotaDat(MS,"DSTotl",%1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.milk_quotas)."""
    return observed


def PPQuotas_BASM(values, n_nonzero):
    r"""PPQuotas(MS, PSQTYPE, "BASM"): the mean over the base years with a value (where there is one).

    values: the base years' values (zeros included), in the caller's order; n_nonzero: how many are nonzero.

    CAPRI's GAMS (pol_input/mquota_update.gms l. 97-98):

           PPQuotas(MS,PSQTYPE,"BASM") $ SUM(BASYRSM $ PPQuotas(MS,PSQTYPE,BASYRSM),1)
               = SUM(BASYRSM, PPQuotas(MS,PSQTYPE,BASYRSM))/SUM(BASYRSM $ PPQuotas(MS,PSQTYPE,BASYRSM),1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.milk_quotas)."""
    return sum(values) / n_nonzero


def PPQuotas_QdelFac(ms, qdel, deli):
    r"""PPQuotas(MS, "QdelFac", exAnte): the delivery quota's factor, the base delivery quota over the base
    deliveries; 1 for AT, DE, FR, FI, UK, SE, IT, CY, CZ, HU and PL; Malta the mean of 1 and its own.

    ms: the country; qdel, deli: PPQuotas(MS, "QDel" / "Deli", "BASM").

    CAPRI's GAMS (pol_input/mquota_update.gms l. 102-103):

           PPQuotas(MS,"QdelFac",exAnte_temp) $  (PPQuotas(MS,"QDel","BASM")  AND PPQuotas(MS,"Deli","BASM"))
                      = PPQuotas(MS,"Qdel","BASM")/PPQuotas(MS,"Deli","BASM");

    CAPRI's GAMS (pol_input/mquota_update.gms l. 107-119):

           PPQuotas(MS,"QdelFac",exAnte_temp)  $ (
                         SAMEAS(MS,"AT000000") Or
                         SAMEAS(MS,"DE000000") Or
                         SAMEAS(MS,"FR000000") Or
                         SAMEAS(MS,"FI000000") Or
                         SAMEAS(MS,"UK000000") Or
                         SAMEAS(MS,"SE000000") Or
                         SAMEAS(MS,"IT000000") Or
                         SAMEAS(MS,"CY000000") Or
                         SAMEAS(MS,"CZ000000") Or
                         SAMEAS(MS,"HU000000") Or
                         SAMEAS(MS,"PL000000")
                         ) = 1.;

    CAPRI's GAMS (pol_input/mquota_update.gms l. 123-124):

           PPQuotas(MS,"QdelFac",exAnte_temp)  $ ( (SAMEAS(MS,"MT000000"))  and PPQuotas(MS,"Deli","BASM"))
                        = (1+(PPQuotas(MS,"Qdel","BASM")/PPQuotas(MS,"Deli","BASM")-1.)/2);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.milk_quotas)."""
    fac = qdel / deli if (qdel and deli) else 0.0
    if ms in ("AT000000", "DE000000", "FR000000", "FI000000", "UK000000", "SE000000", "IT000000", "CY000000",
              "CZ000000", "HU000000", "PL000000"):
        fac = 1.0
    if ms == "MT000000" and deli:
        fac = 1.0 + (qdel / deli - 1.0) / 2.0
    return fac


def p_data_QUTA_COMI(prcm, hcom, qtot, qtot_basm, fac, after_expost):
    r"""p_data(MS, "QUTA", "COMI", exAnte): the dairies' quota, the base deliveries (PRCM) at the total quota's change
    and, after the last ex-post year, the delivery factor; without a base quota the total quota's share of PRCM in
    the milk use (t / 1000).

    prcm, hcom: p_data(MS, "PRCM" / "HCOM", "COMI", "BASM"); qtot, qtot_basm: PPQuotas(MS, "Qtot", year / "BASM");
    fac: PPQuotas_QdelFac; after_expost: the year is after Lst_Expost.

    CAPRI's GAMS (pol_input/mquota_update.gms l. 133-148):

            %3(MS,"QUTA","COMI",exAnte_temp) $ (PPQuotas(MS,"Qtot",exAnte_temp) and %3(MS,"PRCM","COMI","%4"))
        *                start from BASM
                      =( %3(MS,"PRCM","COMI","%4")
        *                change in total official quotas relative to bas
                      * (PPQuotas(MS,"Qtot",exAnte_temp)/PPQuotas(MS,"Qtot","BASM"))
        *                factor for correction of over/underderivery in BAS (but no adjustment in expost period)
                      * (PPQuotas(MS,"QdelFac",exAnte_temp)  $      (%2(exAnte_temp) GT %2("Lst_Expost"))
                        +1.                                  $ (NOT (%2(exAnte_temp) GT %2("Lst_Expost")))))

                                      $      PPQuotas(MS,"Qtot","BASM")

                      +(PPQuotas(MS,"Qtot",exAnte_temp)/1000
                      * %3(MS,"PRCM","COMI","%4")
                      /(%3(MS,"HCOM","COMI","%4")+%3(MS,"PRCM","COMI","%4")))

                                      $ (NOT PPQuotas(MS,"Qtot","BASM"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.milk_quotas)."""
    f = fac if after_expost else 1.0
    return prcm * (qtot / qtot_basm) * f if qtot_basm else qtot / 1000.0 * prcm / (hcom + prcm)


def p_data_QUTB_COMI(prcm, hcom, qtot, qtot_basm):
    r"""p_data(MS, "QUTB", "COMI", exAnte): the direct sales' quota, the base direct sales (HCOM) at the total quota's
    change; without a base quota the total quota's share of HCOM in the milk use (t / 1000).

    CAPRI's GAMS (pol_input/mquota_update.gms l. 151-163):

            %3(MS,"QUTB","COMI",exAnte_temp) $ (PPQuotas(MS,"Qtot",exAnte_temp) and %3(MS,"HCOM","COMI","%4"))
        *                  if possible start from BASM
                      = (  %3(MS,"HCOM","COMI","%4")
        *                  change in total quotas relative to bas
                         * PPQuotas(MS,"Qtot",exAnte_temp)/PPQuotas(MS,"Qtot","BASM"))

                                      $      PPQuotas(MS,"Qtot","BASM")
        *
                      + (  PPQuotas(MS,"Qtot",exAnte_temp)/1000
                         * %3(MS,"HCOM","COMI","%4")
                         /(%3(MS,"HCOM","COMI","%4")+%3(MS,"PRCM","COMI","%4")))

                                      $ (NOT PPQuotas(MS,"Qtot","BASM"));

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.milk_quotas)."""
    return hcom * qtot / qtot_basm if qtot_basm else qtot / 1000.0 * hcom / (hcom + prcm)


def p_data_Quotas_COMI_BASM(values, nonzero):
    r"""p_data(MS, Quotas, "COMI", "BASM"): each region's mean over the base years with a quota.

    values: the quota's Series over (region, year); nonzero: the base years' records with a value (a boolean Series
    of the same index). Returns (the means by region, the counts by region), pandas' sums as the port had them.

    CAPRI's GAMS (pol_input/mquota_update.gms l. 166-167):

           %3(MS,Quotas,"COMI","BASM")  $ SUM(BASYRSM $ %3(MS,Quotas,"COMI",BASYRSM),1)
               = SUM(BASYRSM, %3(MS,Quotas,"COMI",BASYRSM))/SUM(BASYRSM $ %3(MS,Quotas,"COMI",BASYRSM),1);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.milk_quotas)."""
    s = values.where(nonzero, 0.0).groupby(level="region").sum()
    n = nonzero.groupby(level="region").sum()
    return (s / n.where(n != 0, 1.0)).where(n != 0, 0.0), n


def p_data_QUTS_COMI(quta, qutb):
    r"""p_data(MS, "QUTS", "COMI", exAnte): the quota, deliveries plus direct sales (Series).

    CAPRI's GAMS (pol_input/mquota_update.gms l. 169-169):

           %3(MS,"QUTS","COMI",exAnte_temp) = %3(MS,"QUTA","COMI",exAnte_temp) + %3(MS,"QUTB","COMI",exAnte_temp);

    Departures from CAPRI: none in the arithmetic; the domain condition and the loops over the sets in the
    caller (policy.milk_quotas)."""
    return quta + qutb
