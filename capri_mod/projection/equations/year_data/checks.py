r"""The deletions of contents and the year data's check (capmod/load_base_data_and_trends.gms; moved from
capri_mod/projection/equations/load_base_data_and_trends.py as they were, 26 November 2026).
"""
from __future__ import annotations

from dataclasses import dataclass

from capri_mod.data.definitions import capri_pairs, capri_set
from capri_mod.projection.equations.year_data.data_sets import Data, YearSets  # noqa: E402




def DATA_delete_contents(D: Data, S: YearSets) -> None:
    r"""The EAA's positions, the outputs' feed contents but CRPR and DRMA, and the regions' (not the member states')
    contents of the feeds deleted.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 797-803):

           SET EAA(COLS) / EAAP,EAAB,EAAG /;
           DATA(RS,EAA,IO,SCEN)      = 0;
        *
        *  --- delete data never needed in the following (feed related contents of outputs)
        *      except those for CRPR and DRMA which are used in digestibility.gms
           DATA(RS,REQSC,OSECO,SCEN) $ (NOT (SAMEAS(REQSC,"CRPR") or SAMEAS(REQSC,"DRMA")))  = 0;
           DATA(RU,REQSC,FEED,SCEN) $ (NOT SUM(SAMEAS(RU,MS),1)) = 0;

    Departures from CAPRI: none."""
    for t in S.SCEN:
        for (c, w) in D.keys(t):
            drop = ((c in ("EAAP", "EAAB", "EAAG") and w in S.IO)
                    or (c in S.REQSC and w in S.OSECO and c not in ("CRPR", "DRMA")))
            sub = c in S.REQSC and w in S.FEED
            if not (drop or sub):
                continue
            for r in list(D.at(c, w, t)):
                if r in S.RS and (drop or (r in S.RU and r not in S.MS)):
                    D.set(r, c, w, t, 0)


def assert_year_data(D: Data, S: YearSets) -> None:
    r"""The year's activity levels are at least 1e-4 where positive, and each output's gross production is its
    activities' levels times yields within 1e-4 (but ARES and the organic fertilisers): CAPRI stops otherwise.

    CAPRI's GAMS (capmod/load_base_data_and_trends.gms l. 849-863):

        p_problemTol = 1E-4;
        p_problem2D(rs,mpact) $ [(data(rs,mpact,"levl","y") gt 0) and (data(rs,mpact,"levl","y") lt p_problemTol)]
                                  = data(rs,mpact,"levl","y");

        $batInclude 'util\assert_empty_set.gms' p_problem2D 'Trend activity level is smaller than tolerable minimum'


        * --- Verify that the loaded data satisfies basic balancing conditions
        p_problemTol = 0.0001;
        *     GROF must be LEVL*yield
        problemItem2D(rs,o) $ [(not sameas(o,"ares")) and (not fout(o)) and (abs(data(rs,"grof",o,"y")
                                  - sum(mpact $ pact_to_o(mpact,o), data(rs,mpact,"levl","y")*data(rs,mpact,o,"y"))/1000)
                                  gt p_problemTol)] = yes;

        $batInclude 'util\assert_empty_set.gms' problemItem2D 'Grof does not match levl*yield'

    Departures from CAPRI: none."""
    small = sorted((r, a, v) for a in S.MPACT for r, v in D.at(a, "LEVL", "Y").items()
                   if r in S.RS and 0 < v < 1e-4)
    if small:
        raise ValueError(f"Trend activity level is smaller than tolerable minimum: {small[:10]}")
    acts_of = {}
    for (a, o) in S.PACT_TO_O:
        if a in S.MPACT:
            acts_of.setdefault(o, []).append(a)
    bad = []
    for o in S.O:
        if o == "ARES" or o in S.FOUT:
            continue
        for r in S.RS:
            g = D.get(r, "GROF", o, "Y")
            s = sum(D.get(r, a, "LEVL", "Y") * D.get(r, a, o, "Y") for a in acts_of.get(o, ())) / 1000.
            if abs(g - s) > 1e-4:
                bad.append((r, o, g, s))
    if bad:
        raise ValueError(f"Grof does not match levl*yield: {bad[:10]}")
