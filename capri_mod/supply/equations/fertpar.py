"""CAPRI's fertiliser parameters of the simulation year that the crops' nutrient data use, as fert/fertpar.gms sets
them (run by capmod/def_fert_and_requirements.gms l. 121 before fert/fertned.gms; this package's fertned.py).

Used by tools/build/build_capri_crop_n_coefs.py; the values (the RALL table, the regional grassland rates) are read
there from CAPRI's fertpar.gms itself (KNOWN_ISSUES K191).
"""
from __future__ import annotations

def p_nitrFact_BioFix(crop: str, BioFix_RALL: float, nfixRate_gras_MS: float = None, FLEG_LEVL: float = 0.0,
                      BioFix_FLEG: float = 0.0, GRAE_RALL: float = 0.0, GRSACT: bool = None) -> float:
    r"""p_nitrFact(RS, crop, "BioFix"): the share of the crop's nutrient removal fixed biologically (e_BIOFIX,
    supply/supply_model.gms l. 1438-1461; NUTNED_'s need net of it, l. 1095-1137).

    CAPRI's GAMS (fert/fertpar.gms l. 259):

           p_nitrFact(RS,MCACT,"BioFix")         =  p_nitrFact("RALL",MCACT,"BioFix");

    CAPRI's GAMS (fert/fertpar.gms l. 295-308):

           p_nfixRate_gras(MS) $ (NOT p_nfixRate_gras(MS)) = p_nitrFact("RALL","GRAE","BioFix");
           p_nitrFact(MS,"OFAR","BioFix") $ p_nfixRate_gras(MS) =  p_nfixRate_gras(MS) * (1.-%data%(MS,"FLEG","LEVL","BAS"))
                                        + p_nitrFact("RALL","FLEG","BioFix") *     %data%(MS,"FLEG","LEVL","BAS");
           p_nitrFact(MS,GRSACT,"BioFix") $ p_nfixRate_gras(MS) =  p_nfixRate_gras(MS);
           p_nitrFact(RS,"OFAR","BioFix") $ sum(map_rr(ms,rs),p_nfixRate_gras(ms)) =  sum(map_rr(ms,rs),p_nfixRate_gras(ms) * (1.-%data%(RS,"FLEG","LEVL","BAS"))
                                        + p_nitrFact("RALL","FLEG","BioFix") *     %data%(RS,"FLEG","LEVL","BAS"));
           p_nitrFact(RS,GRSACT,"BioFix") $ sum(map_rr(ms,rs),p_nfixRate_gras(ms))  =    sum(map_rr(ms,rs),p_nfixRate_gras(ms));

    In this project's notation, for crop a of region r in member state m: f(a) the RALL table's rate (fertpar.gms
    l. 209-239: soya and pulses 0.75, other arable fodder, extensive and intensive grassland 0.05, the other crops none),
    g(m) the member state's grassland rate (p_nfixRate_gras, fertpar.gms l. 265-293; f(GRAE) where the table has none),
    s(r) the share of fodder legumes in other arable fodder (DATA(r, "FLEG", "LEVL", "BAS")):

        BioFix(r, a) = g(m)                                   for a in GRSACT
                       g(m) (1 - s(r)) + f(FLEG) s(r)         for a = OFAR
                       f(a)                                   otherwise

    nfixRate_gras_MS: g(m) as the table gives it (None where it has none: then GRAE_RALL, as l. 295). GRSACT: the crop
    is in CAPRI's set GRSACT ("Gras and Grazings", sets.gms l. 2940: GRAE, GRAI, IHISGR, FALLGR; the caller reads it
    there; None: GRAE or GRAI)."""
    g = float(nfixRate_gras_MS) if nfixRate_gras_MS else float(GRAE_RALL or 0.0)
    a = str(crop).upper()
    grs = (a in ("GRAE", "GRAI")) if GRSACT is None else bool(GRSACT)
    if grs and g:
        return g
    if a == "OFAR" and g:
        s = float(FLEG_LEVL or 0.0)
        return g * (1.0 - s) + float(BioFix_FLEG or 0.0) * s
    return float(BioFix_RALL or 0.0)
