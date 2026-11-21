"""CAPRI's nutrient content of crop residues, as envind/def_gascoeff.gms defines it (read by fert/fertned.gms; this
package's fertned.py p_residRel).

Used by tools/build/build_capri_crop_n_coefs.py; the tables p_nutContCropOutput and Nindex are read there from CAPRI's
def_gascoeff.gms itself (KNOWN_ISSUES K191).
"""
from __future__ import annotations


def Resid(output: str, nutCont: float, Nindex: float, cereal: bool) -> float:
    r"""Resid(CROPO, FNUT): the nutrient of the crop residues left on the field per t of harvested material (kg per t).

    CAPRI's GAMS (envind/def_gascoeff.gms l. 422-423):

           Resid(CROPO,FNUT) $ (NINDEX(CROPO) AND ((NOT SUM(PACT_TO_Y(CERE,CROPO),1.)) OR SAMEAS(CROPO,"MAIZ")))
                                                       = p_nutContCropOutput(cropo, fnut) / Nindex(cropo);

    In this project's notation, for an output o with nutrient content c(o, n) (p_nutContCropOutput, kg per t,
    def_gascoeff.gms l. 332-376) and N index I(o) (kg N in the main product over kg N in the residues, l. 378-418):

        Resid(o, n) = c(o, n) / I(o)     for o not a cereal's main output, or maize
                      0                  otherwise (CAPRI's note: straw is handled apart)

    cereal: o is the main output of a cereal activity (PACT_TO_Y(CERE, o))."""
    if not float(Nindex or 0.0) or (cereal and str(output).upper() != "MAIZ"):
        return 0.0
    return float(nutCont or 0.0) / float(Nindex)
