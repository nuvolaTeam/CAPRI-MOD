r"""The biofuels' residues (biofuel/resids.gms: ARES, NECR, SECG) (capmod/load_base_data_and_trends.gms; moved from
capri_mod/projection/equations/load_base_data_and_trends.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass

from capri_mod.data.definitions import capri_pairs, capri_set
from capri_mod.projection.equations.year_data.data_sets import Data, YearSets  # noqa: E402




@dataclass
class ResidsParams:
    """CAPRI's literal parameters of biofuel/resids.gms (capri_data/2017/supply/biofuel_resids_params.csv,
    tools/build/build_resids_params.py): p_residYield(PACT), the crop residues' dry weight per unit of the main yield;
    p_newEnergyCropYield, the new energy crops' biomass yield per member state (REST for the others); p_secgConv, the
    biomass needed per unit of second-generation biofuel."""
    p_residYield: dict
    p_newEnergyCropYield: dict
    p_secgConv: dict

    @classmethod
    def from_csv(cls, path=None):
        import csv
        from pathlib import Path
        path = path or Path(__file__).resolve().parents[4] / "capri_data" / "2017" / "supply" / \
            "biofuel_resids_params.csv"
        out = {"p_residYield": {}, "p_newEnergyCropYield": {}, "p_secgConv": {}}
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                out[row["symbol"]][row["item"]] = float(row["value"])
        return cls(**out)


def DATA_ARES(D: Data, S: YearSets, P: ResidsParams) -> None:
    r"""The member states' crop residues (ARES): per hectare, the main yield times the residue's yield factor (zero
    for the activities without one), and their gross production over the main activities.

    CAPRI's GAMS (biofuel/resids.gms l. 45-46; the factors p_residYield, l. 24-35, in ResidsParams):

           Data(MS,PACT,"ARES",SCEN) = SUM(PACT_TO_Y(PACT,O), DATA(MS,PACT,O,SCEN)) *  p_residYield(PACT);
           Data(MS,"GROF","ARES",SCEN) = SUM(MPACT, DATA(MS,MPACT,"ARES",SCEN)*DATA(MS,MPACT,"LEVL",SCEN))/1000;

    The water module's statement (l. 39-41) is off in CAPRI's baseline. Departures from CAPRI: none."""
    main = {}
    for (a, o) in S.PACT_TO_Y:
        main.setdefault(a, []).append(o)
    for ms in S.MS:
        for a in S.PACT:
            for t in S.SCEN:
                D.set(ms, a, "ARES", t, sum(D.get(ms, a, o, t) for o in main.get(a, ()))
                      * P.p_residYield.get(a, 0.0))
    for ms in S.MS:
        for t in S.SCEN:
            D.set(ms, "GROF", "ARES", t, sum(D.get(ms, a, "ARES", t) * D.get(ms, a, "LEVL", t) for a in S.MPACT)
                  / 1000)


def _necr_yield(P: ResidsParams, ms):
    """p_newEnergyCropYield(MS) + p_newEnergyCropYield("REST") $ (NOT p_newEnergyCropYield(MS))."""
    y = P.p_newEnergyCropYield.get(ms, 0.0)
    return y + (P.p_newEnergyCropYield["REST"] if not y else 0.0)


def DATA_NECR_LEVL_1_2(D: Data, S: YearSets, P: ResidsParams, same_year: bool = False) -> None:
    r"""The new energy crops' area for second-generation biofuels (LEVL_1: half the biomass the second generation
    needs, at the crops' yield, at most 90% of their area) and the rest of their area (LEVL_2); on "CAL" those of "Y",
    or of "BAS" when the simulation year is the base year (same_year).

    CAPRI's GAMS (biofuel/resids.gms l. 69-85; p_newEnergyCropYield l. 49-57 and p_secgConv l. 64-67 in ResidsParams):

        ** We assume that Second generation biofuels are propduced 50/50 by agricultural residuals and new energy crops
        * That would require new energy crop area (Stored on levl_1)

           DATA(MS,"NECR","LEVL_1",SCEN) = MIN(DATA(MS,"NECR","LEVL",SCEN) *0.9, 0.5*SUM(XXBIOF,Data(MS,"SECG",XXBIOF,SCEN) /p_secgConv(XXBIOF))
                                            / (p_newEnergyCropYield(MS) + p_newEnergyCropYield("REST") $ (NOT p_newEnergyCropYield(MS))));


        * the NECR area that is used by other than fuel bioenergy is stored on LEVL_2

          DATA(MS,"NECR","LEVL_2",SCEN) = DATA(MS,"NECR","LEVL",SCEN)-DATA(MS,"NECR","LEVL_1",SCEN);


          DATA(MS,"NECR","LEVL_1","CAL") = DATA(MS,"NECR","LEVL_1","Y")   $ (NOT (CALYEA("BAS") = CALYEA("Y")))
                                         + DATA(MS,"NECR","LEVL_1","BAS") $ (CALYEA("Y") = CALYEA("BAS"));

          DATA(MS,"NECR","LEVL_2","CAL") = DATA(MS,"NECR","LEVL_2","Y")   $ (NOT (CALYEA("BAS") = CALYEA("Y")))
                                         + DATA(MS,"NECR","LEVL_2","BAS") $ (CALYEA("Y") = CALYEA("BAS"));

    Departures from CAPRI: none."""
    for ms in S.MS:
        for t in S.SCEN:
            need = sum(D.get(ms, "SECG", f, t) / P.p_secgConv[f] for f in S.XXBIOF)
            D.set(ms, "NECR", "LEVL_1", t, min(D.get(ms, "NECR", "LEVL", t) * 0.9, 0.5 * need / _necr_yield(P, ms)))
    for ms in S.MS:
        for t in S.SCEN:
            D.set(ms, "NECR", "LEVL_2", t, D.get(ms, "NECR", "LEVL", t) - D.get(ms, "NECR", "LEVL_1", t))
    for w in ("LEVL_1", "LEVL_2"):
        for ms in S.MS:
            D.set(ms, "NECR", w, "CAL", D.get(ms, "NECR", w, "BAS" if same_year else "Y"))


def DATA_SECG_ARES_bio(D: Data, S: YearSets, P: ResidsParams) -> None:
    r"""The agricultural residues for second-generation biofuels (SECG of ARES): the biomass the second generation
    needs less the new energy crops' (LEVL_1 at their yield); each biofuel's part from the new energy crops (bioNECR)
    and from the residues (bioARES).

    CAPRI's GAMS (biofuel/resids.gms l. 87-99):

        ** and Agricultural residuals

           Data(MS,"SECG","ARES",SCEN) = SUM(XXBIOF,Data(MS,"SECG",XXBIOF,SCEN) /p_secgConv(XXBIOF))
                                             - DATA(MS,"NECR","LEVL_1",SCEN)*(p_newEnergyCropYield(MS) +
                                                                                   p_newEnergyCropYield("REST") $ (NOT p_newEnergyCropYield(MS)));

           DATA(MS,"bioNECR",XXBIOF,SCEN) $ (Data(MS,"SECG","BIOE",SCEN)+Data(MS,"SECG","BIOD",SCEN))
                                          =  DATA(MS,"NECR","LEVL_1",SCEN)*(p_newEnergyCropYield(MS) +
                                                                            p_newEnergyCropYield("REST") $ (NOT p_newEnergyCropYield(MS)))
                                          * Data(MS,"SECG",XXBIOF,SCEN) /(Data(MS,"SECG","BIOE",SCEN)+Data(MS,"SECG","BIOD",SCEN));


           DATA(MS,"bioARES",XXBIOF,SCEN) =  Data(MS,"SECG",XXBIOF,SCEN)- DATA(MS,"bioNECR",XXBIOF,SCEN);

    Departures from CAPRI: none."""
    for ms in S.MS:
        for t in S.SCEN:
            D.set(ms, "SECG", "ARES", t, sum(D.get(ms, "SECG", f, t) / P.p_secgConv[f] for f in S.XXBIOF)
                  - D.get(ms, "NECR", "LEVL_1", t) * _necr_yield(P, ms))
    for ms in S.MS:
        for f in S.XXBIOF:
            for t in S.SCEN:
                tot = D.get(ms, "SECG", "BIOE", t) + D.get(ms, "SECG", "BIOD", t)
                if tot:
                    D.set(ms, "bioNECR", f, t, D.get(ms, "NECR", "LEVL_1", t) * _necr_yield(P, ms)
                          * D.get(ms, "SECG", f, t) / tot)
    for ms in S.MS:
        for f in S.XXBIOF:
            for t in S.SCEN:
                D.set(ms, "bioARES", f, t, D.get(ms, "SECG", f, t) - D.get(ms, "bioNECR", f, t))
