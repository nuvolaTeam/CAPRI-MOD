"""The end of CAPTRD's expert supports and their storage as p_result Expert and TrustLevl.

  captrd/expert_support.gms
    l. 794-807   the herds' and levels' support of the member states' animal activities floored: at least 90% of the
                 year before compounded from BAS (and from BAST, the smaller), or a linear decline to 20% of them by
                 Lst_exAnte (herd_floor; the same formula national_supports.gms applies to CS000000)
    l. 814-834   TOOU: the support made an expert support, with a low trust level, where the output's price has expert
                 information (Absolute, PercentChange or Longrun1) and TOOU has no trust level yet (toou)
    l. 841-848   no position may have both an Absolute and a PercentChange support (check_duplicates)
  captrd/define_stats_and_supports.gms
    l. 485-500   Expert: the Absolute, else (1 + PercentChange/100) x BASM, on S_ColsEst x S_RowsEst (expert)
    l. 589-596   (adjust_to_biof_supports.gms with "support", per ex-ante year outside ExAnteD) only its l. 175 here:
                 BIOF.SUGA's Expert deleted where MAPR.SUGA has no nObs (biof_suga); its support adjustments are not
                 ported yet
    l. 627-630   the member states' trade of sugar beet (IMPT, EXPT, NTRD .SUGB): Expert (and support) = BAST, else
                 BASM, in every ex-ante year (expert, sugb_trade)
    l. 637-645   TrustLevl where Expert: the COCO support's, else the expert support's, else 10 (trust)
"""
from __future__ import annotations

from typing import Dict, Iterable, Sequence, Set, Tuple

K3 = Tuple[str, str, str]
K4 = Tuple[str, str, str, int]

#: expert_support.gms l. 795-806: the yearly decline and the share of the base kept by Lst_exAnte
YEARLY = 0.9
DECLINE = 0.8
#: l. 828-833: TOOU's trust level, half the support's ratio to BASM (at most 1, at least 1e-10)
TOOU_TRUST = 0.5
TOOU_MIN = 1.e-10
#: define_stats_and_supports.gms l. 643: the trust level of an expert support without one
DEFAULT_TRUST = 10.0


def floor_value(s: float, bas: float, bast: float, y: int, base_year: int, bast_year: int, lst_exante: int) -> float:
    """expert_support.gms l. 794-807 for one position and year (GAMS's $ conditions as written)."""
    if bast:
        f1 = min(bast * YEARLY ** (y - bast_year), bas * YEARLY ** (y - base_year))
        f2 = min(bast * (1 - DECLINE * (y - bast_year) / (lst_exante - bast_year)),
                 bas * (1 - DECLINE * (y - base_year) / (lst_exante - base_year)))
    else:
        f1 = bas * YEARLY ** (y - base_year)
        f2 = bas * (1 - DECLINE * (y - base_year) / (lst_exante - base_year))
    return max(s, f1, f2)


def herd_floor(support: Dict[K4, float], *, ms: Iterable[str], maact: Iterable[str], bas: Dict[K3, float],
               bast: Dict[K3, float], exantet: Sequence[int], base_year: int, bast_year: int, lst_exante: int) -> None:
    """l. 794-807, in place: P_Result(MS, mAACT, herdLevl, ExAnteT, "support")."""
    new = {}
    for r in ms:
        for c in maact:
            for w in ("HERD", "LEVL"):
                b, t = bas.get((r, c, w), 0.0), bast.get((r, c, w), 0.0)
                for y in exantet:
                    new[(r, c, w, y)] = floor_value(support.get((r, c, w, y), 0.0), b, t, y, base_year, bast_year,
                                                    lst_exante)
    for k, v in new.items():
        if v:
            support[k] = v
        else:
            support.pop(k, None)


def toou(S, *, support: Dict[K4, float], basm: Dict[K3, float], ms: Iterable[str], s_colsest: Iterable[str],
         exante: Sequence[int], pact_to_y: Iterable[Tuple[str, str]], longrun1: Dict[K4, float]) -> None:
    """l. 814-834, in place on S (national_supports.Expert)."""
    outs: Dict[str, Set[str]] = {}
    for a, o in pact_to_y:
        outs.setdefault(a, set()).add(o)
    cols = set(s_colsest)
    new_ab, new_tr = {}, {}
    for r in ms:
        for c in cols:
            for y in exante:
                k = (r, c, "TOOU", y)
                s = support.get(k, 0.0)
                if S.tr.get(k) or not s:
                    continue
                if not any(S.pc.get((r, "UVAG", o, y)) or S.ab.get((r, "UVAG", o, y)) or longrun1.get((r, "UVAG", o, y))
                           for o in outs.get(c, ())):
                    continue
                new_ab[k] = s
                b = basm.get((r, c, "TOOU"), 0.0)
                new_tr[k] = TOOU_TRUST * max(TOOU_MIN, min(1.0, s / b) if b else 0.0)
    for k, v in new_ab.items():
        S.put(S.ab, k, v)
    for k, v in new_tr.items():
        S.put(S.tr, k, v)


def check_duplicates(S) -> None:
    """l. 841-848: GAMS aborts where a position has both an Absolute and a PercentChange support."""
    both = sorted(k for k in S.ab if S.pc.get(k))
    if both:
        raise ValueError(f"expert_support.gms l. 847: Absolute and PercentChange at {len(both)} positions, e.g. "
                         f"{both[:5]}")


def expert(S, *, basm: Dict[K3, float], s_colsest: Iterable[str], s_rowsest: Iterable[str],
           rest: Iterable[str], rmaggsup: Iterable[str] = ()) -> Dict[K4, float]:
    """define_stats_and_supports.gms l. 485-500: p_result(..., "Expert")."""
    cols, rows, rest, agg = set(s_colsest), set(s_rowsest), set(rest), set(rmaggsup)
    out: Dict[K4, float] = {}
    for k, v in S.ab.items():                                                  # l. 485-487 (rmAggSup)
        if k[0] in agg and k[1] in cols and k[2] in rows and v:
            out[k] = v
    for k in set(S.ab) | set(S.pc):                                            # l. 489-500 (Rest)
        r, c, w, y = k
        if r not in rest or c not in cols or w not in rows:
            continue
        a, p = S.ab.get(k, 0.0), S.pc.get(k, 0.0)
        if a or p:
            v = (a if a else 0.0) + ((1 + p / 100) * basm.get((r, c, w), 0.0) if p else 0.0)
            if v:
                out[k] = v
            else:
                out.pop(k, None)
    return out


def biof_suga(expert_: Dict[K4, float], *, rest: Iterable[str], exante: Sequence[int], exanted: Iterable[int],
              nobs: Set[K3]) -> None:
    """adjust_to_biof_supports.gms l. 175 (called by define_stats_and_supports.gms l. 589-596 for the ex-ante years
    outside ExAnteD), in place: BIOF.SUGA's Expert deleted where MAPR.SUGA has no nObs."""
    skip = set(exanted)
    for r in rest:
        if (r, "MAPR", "SUGA") not in nobs:
            for y in exante:
                if y not in skip:
                    expert_.pop((r, "BIOF", "SUGA", y), None)


def sugb_trade(expert_: Dict[K4, float], support: Dict[K4, float], *, ms: Iterable[str], exante: Sequence[int],
               bast: Dict[K3, float], basm: Dict[K3, float]) -> None:
    """define_stats_and_supports.gms l. 627-630, in place: P_Result(MS, tradeEst, "SUGB", ExAnte, support/expert)
    = BAST, else BASM (tradeEst: IMPT, EXPT, NTRD; sets_captrd.gms l. 314-316)."""
    for r in ms:
        for c in ("IMPT", "EXPT", "NTRD"):
            v = bast.get((r, c, "SUGB"), 0.0) or basm.get((r, c, "SUGB"), 0.0)
            for y in exante:
                for d in (expert_, support):
                    if v:
                        d[(r, c, "SUGB", y)] = v
                    else:
                        d.pop((r, c, "SUGB", y), None)


def trust(expert_: Dict[K4, float], *, coco_trust: Dict[K4, float], expert_trust: Dict[K4, float],
          s_colsest: Iterable[str], s_rowsest: Iterable[str], rest: Iterable[str]) -> Dict[K4, float]:
    """define_stats_and_supports.gms l. 637-645: p_result(..., "TrustLevl") where Expert."""
    cols, rows, rest = set(s_colsest), set(s_rowsest), set(rest)
    out: Dict[K4, float] = {}
    for k in expert_:
        if k[0] in rest and k[1] in cols and k[2] in rows:
            out[k] = coco_trust.get(k) or expert_trust.get(k) or DEFAULT_TRUST
    return out
