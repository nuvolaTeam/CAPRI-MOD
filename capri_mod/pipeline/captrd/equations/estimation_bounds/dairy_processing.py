r"""CAPTRD's estimation bounds of the dairy products, the processing yields, the stock changes and the market balances
(captrd/fix_est.gms; moved from capri_mod/pipeline/captrd/equations/fix_est.py as they were, 26 November 2026).
"""
from __future__ import annotations




def V_EstV_MLKSECO(basm, x, span):
    r"""V_EstV.LO and .UP of a milk content of a dairy product: the base plus and minus up to 20% at the last
    ex-ante year.

    basm: p_data(., m, s, "BASM"); x, span: as V_EstV_MEAT. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 681-687):

           v_estV.lO(REST,MLKCNT,MLKSECO,exAnte) $ (p_data(Rest,MLKCNT,MLKSECO,"nObs") $ NUTS0(Rest))
               = p_data(REST,MLKCNT,MLKSECO,"BASM")
               * (1. - 0.20 * (MAX(OrdT("BAS")+1,OrdT(ExAnte)) - OrdT("BAS"))/(OrdT("lst_exAnte")-OrdT("BAS")));
        *
           v_estV.UP(REST,MLKCNT,MLKSECO,exAnte) $ (p_data(Rest,MLKCNT,MLKSECO,"nObs") $ NUTS0(Rest))
               = p_data(REST,MLKCNT,MLKSECO,"BASM")
               * (1. + 0.20 * (MAX(OrdT("BAS")+1,OrdT(ExAnte)) - OrdT("BAS"))/(OrdT("lst_exAnte")-OrdT("BAS")));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    r = 0.20 * x / span
    return basm * (1.0 - r), basm * (1.0 + r)


def V_EstV_fx_MLKCNT(basm):
    r"""V_EstV.FX of the milk contents of MILK, BUTT and SMIP: their base.

    CAPRI's GAMS (captrd/fix_est.gms l. 689-691):

           v_estV.fx(REST,MLKCNT,"MILK",exAnte)  $ p_data(Rest,MLKCNT,"MILK","nObs")  = p_data(REST,MLKCNT,"MILK","BASM");
           v_estV.fx(REST,MLKCNT,"BUTT",exAnte)  $ p_data(Rest,MLKCNT,"BUTT","nObs")  = p_data(REST,MLKCNT,"BUTT","BASM");
           v_estV.fx(REST,MLKCNT,"SMIP",exAnte)  $ p_data(Rest,MLKCNT,"SMIP","nObs")  = p_data(REST,MLKCNT,"SMIP","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return basm


def V_EstV_PRCY(basm, proc_yield):
    r"""V_EstV.LO and .UP of a processing yield: 1% around the base; for the oilseeds' cakes and oils within 10% of
    their technical yields (Proc_Yields), which the bounds include.

    basm: p_data(., "PRCY", s, "BASM"); proc_yield: Proc_Yields(s) (captrd.gms), None where the product has none.
    Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 693-700):

           v_estV.LO(REST,"PRCY",SECO,exAnte)    $ p_data(Rest,"PRCY",SECO,"nObs")   = p_data(Rest,"PRCY",SECO,"BASM")*0.99;
           v_estV.UP(REST,"PRCY",SECO,exAnte)    $ p_data(Rest,"PRCY",SECO,"nObs")   = p_data(Rest,"PRCY",SECO,"BASM")*1.01;

        *        Try to squeeze prcy into range arround BAS and tech coefficeints in line with bounds in data_cal
           v_estV.LO(REST,"PRCY",SECO,exAnte)    $ (p_data(Rest,"PRCY",SECO,"nObs") $ Proc_yields(SECO))
               = min(max(Proc_Yields(SECO) * 0.90,p_data(Rest,"PRCY",SECO,"BASM")*0.99),Proc_Yields(SECO)) ;
           v_estV.UP(REST,"PRCY",SECO,exAnte)    $ (p_data(Rest,"PRCY",SECO,"nObs") $ Proc_yields(SECO))
               = max(min(Proc_Yields(SECO) * 1.1,p_data(Rest,"PRCY",SECO,"BASM")*1.01),Proc_Yields(SECO)) ;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    lo, up = basm * 0.99, basm * 1.01
    if proc_yield is not None:
        py = proc_yield
        lo = min(max(py * 0.90, basm * 0.99), py)
        up = max(min(py * 1.1, basm * 1.01), py)
    return lo, up


def V_EstV_fx_PRCY_MILK(basm):
    r"""V_EstV.FX of raw milk's processing yield: its base.

    CAPRI's GAMS (captrd/fix_est.gms l. 702-702):

           v_estV.FX(REST,"PRCY","MILK",exAnte)  $ p_data(Rest,"PRCY","MILK","nObs")     = p_data(Rest,"PRCY","MILK","BASM");

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return basm


def V_EstV_PRCY_MLKSECO(basm):
    r"""V_EstV.LO and .UP of a dairy product's processing yield: 50% and 150% of its base. Returns (lo, up).

    CAPRI's GAMS (captrd/fix_est.gms l. 704-705):

           v_estV.LO(REST,"PRCY",MLKSECO,exAnte) $ p_data(Rest,"PRCY",MLKSECO,"nObs")   = p_data(Rest,"PRCY",MLKSECO,"BASM")*0.50;
           v_estV.UP(REST,"PRCY",MLKSECO,exAnte) $ p_data(Rest,"PRCY",MLKSECO,"nObs")   = p_data(Rest,"PRCY",MLKSECO,"BASM")*1.50;

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return basm * 0.50, basm * 1.50


def V_EstV_up_STCM(levels, cows):
    r"""V_EstV.UP of a young animal's stock change: 20% of the herds producing it (YCOW's with the dairy and
    suckler cows' herds added to each).

    levels: p_data(., a, "LEVL", "BASM") of the activities producing it (PACT_TO_O), in the caller's order; cows:
    DCOW's and SCOW's BASM summed for YCOW, else 0.

    CAPRI's GAMS (captrd/fix_est.gms l. 707-711):

           v_estV.UP(REST,"STCM",OYANI,exAnte) $ NUTS0(Rest)
                                                   = 0.2*ABS(SUM(PACT_TO_O(MPACT,OYANI),
                                                                   p_data(Rest,MPACT,"LEVL","BASM")
                                                                +  p_data(Rest,"DCOW","LEVL","BASM") $ SAMEAS(OYANI,"YCOW")
                                                                +  p_data(Rest,"SCOW","LEVL","BASM") $ SAMEAS(OYANI,"YCOW")));

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    tot = 0.0
    for levl in levels:
        tot += levl + cows
    return 0.2 * abs(tot)


def V_EstV_lo_MrkBalee(e, lo):
    r"""V_EstV.LO of a market balance position, not fixed and not negative: at least 1e-8 (the losses and the
    seed and feed uses SEDM, SEDF, LOSM, LOSF from 1e-8 only).

    e: the column; lo: the bound before.

    CAPRI's GAMS (captrd/fix_est.gms l. 713-723):

           v_estV.lO(REST,MrkBalee,S_RowsEst,exAnte) $ (
                                                         (v_estV.lO(REST,MrkBalee,S_RowsEst,exAnte) GE 0)
                                                       $ (v_estV.lO(REST,MrkBalee,S_RowsEst,exAnte) NE v_estV.up(REST,MrkBalee,S_RowsEst,exAnte))
                                                       $ p_data(Rest,MrkBalee,S_RowsEst,"nObs")
                                                       $ NUTS0(Rest))
              = MAX(v_estV.lO(REST,MrkBalee,S_RowsEst,exAnte)
                          $ (NOT (   SAMEAS(MrkBalee,"SEDM")
                                  or SAMEAS(MrkBalee,"SEDF")
                                  or SAMEAS(MrkBalee,"LOSM")
                                  or SAMEAS(MrkBalee,"LOSF"))),
                    1.E-8  );

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    keep = lo if e not in ("SEDM", "SEDF", "LOSM", "LOSF") else 0.0
    return max(keep, 1.0e-8)


def V_EstV_lo_STCM(up):
    r"""V_EstV.LO of a young animal's stock change: minus its upper bound.

    CAPRI's GAMS (captrd/fix_est.gms l. 725-725):

           v_estV.lO(REST,"STCM",OYANI,exAnte) $ NUTS0(Rest)  = -v_estV.UP(REST,"STCM",OYANI,exAnte);

    Departures from CAPRI: none in the arithmetic; the domain condition, the loops over the sets and the bounds it reads in the
    caller (estimate_bounds.bounds)."""
    return -up
