"""Physical constants and unit conversions, named once (refactor stage 3, N4; the project lead's decision Q5 of
2 November 2026: physical constants are named code constants, not rows of the parameters file).

They are written as the code used them, so the arithmetic is unchanged: an N2O-N to N2O conversion reads
`x * M_N2O / M_N2O_N` (44 / 28), as `x * 44.0 / 28.0` did.
"""
from __future__ import annotations

#: molar mass of N2O, g per mol (CAPRI's 44/28 conversion of N2O-N to N2O, envind/gases.gms)
M_N2O = 44.0
#: the nitrogen in a mole of N2O, g (2 x 14)
M_N2O_N = 28.0
#: MJ per Mcal (the International Table calorie: 4.1868 J per cal), as CAPRI's gases.gms converts gross energy
MJ_PER_MCAL = 4.1868
