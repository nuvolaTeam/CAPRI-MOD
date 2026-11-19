"""CAPRI's supply/supply_model.gms (star 3.0, 5,631 lines, about 160 equations), one module per block of the file.

Each module holds the equations of one of CAPRI's blocks, one function per equation named as CAPRI's equation (or as
the equation's term the function writes, under its equation), with CAPRI's GAMS statement, its file and lines, the
equation in this project's notation and the departures in the function's docstring. A module is added when its first
equation is written; the blocks not listed have none yet.

    module          CAPRI block (supply/supply_model.gms)                                           lines
    nutrients.py    the crops' nutrient balances: fertDistCres_ (the residue pool), NUTNED_           1049-1298
    n_surplus.py    the soil surface N balance: e_ATMOSD, e_CRESID, e_SURTOTHa                        1389-1483
    mitigation.py   the cost of the mitigation options: GHG_Mit_Cost_                                 5057-5190

Blocks to come (the file's own section marks): land use (l. 332-...), feed use balances (l. 794-...), the use of young
animals (l. 845-...), manure trade and ManureNPK_ (l. 895-...), the inner fertiliser model (l. 1498-1790), the N
surplus restriction (l. 1864-...), emissions.
"""
