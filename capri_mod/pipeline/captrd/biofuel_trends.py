"""CAPTRD's expert supports for the biofuel sector from PRIMES (biofuel/biofuel_trends.gms, included by
captrd/expert_support.gms l. 108 with %NewBiofuelModule% on; CAPRI star 3.0), with the reference run's switches:
%aglinkTightLink%, %consBioTrends%, %stronglycutNECR%, %FixExogenFactGlobiom% off, %ScaleToDGAGRI% off (the GUI's
"Scaling to DG Agri baseline", and l. 627-628 keep it off for projections beyond 2020), %FARM_B% off.

In GAMS's order (line numbers of biofuel_trends.gms):
  l. 237-243  PRIMES's results p_primesWithUnits (dat/biofuel/%primesBiofuelFile%.gdx), loaded over their domains
  l. 338-392  aggregated to p_primesResults: production, demand, net trade, the biodiesel from oils, the second
              generation shares, the feedstock shares of ethanol (at least 5% first generation)
  l. 395-443  fossil fuels' demand, prices and excise taxes (PRIMES, else fossilFuel.gdx); Belgium + Luxembourg
  l. 448-457  fuels from ktoe to 1000 t (p_oilEqu)
  l. 482-509  gaps filled by distance-weighted means, then linear interpolation over the years between PRIMES's
  l. 511-613  shares of second generation and non-agricultural fuels, waste oil, industrial use, fuel demand
  l. 645-659  ethanol from sugar and cereals
  l. 669-871  the expert supports: the ex-post p_data of the biofuel series; demand, industrial use, biofuel use and
              production as PRIMES's change on the 2015 data; net trade, exports and imports; second generation; the
              new energy crops NECR (member states and NUTS 2 regions, trust 10, revenue 250)
  l. 943-1011 non-agricultural fuels; processing coefficients PRCB (Aglink's yield changes) and by-products PRCBY,
              extrapolated beyond %lst_dgagri%
  l. 1013-1272 feedstock use: sugar from PRIMES's change, the other feedstocks by their base shares (at least
              p_potentialStocks), DDGS; small feedstocks removed or fixed close to zero
  l. 1276-1291 ethanol production recomputed from its feedstocks
  l. 1297-1318 %constBionergy% (the 2023 Brightspace baseline): the EU28 member states' biofuel positions after 2020 at
              their 2020 values (setting captrd.const_bioenergy: off, as the reference run, which did not apply it)
  l. 1323-1413 fossil fuel demand, per inhabitant; excise taxes (Biofuel_data.gms's p_taxData), prices from PRIMES's
              change, consumer prices, per ton; EXPD
  l. 1415-1478 trust levels; p_data's nObs of the new series

A statement whose right side reads the parameter it assigns takes the values from before the statement (the cereal and
sugar shares of l. 536-543, the gaps of l. 482-493), as GAMS does: CAPTRD's sugar feedstock (Germany 2020: 192.464)
is reproduced that way and not with the values the statement has already written (180.813). EPS (the new energy
crops' zero years, l. 874-876) is carried as such: CAPTRD's results store it, and a $ condition takes it as nonzero.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

#: l. 79, 428: PRIMES's reference year (%BASprimes%)
BAS_PRIMES = 2015
#: l. 355-362: heating values (GJ/t) of rape seed and rape oil, GJ per toe
LHV_RAPE = 26.5
LHV_RAPO = 37.2
GJ_PER_TOE = 41.9
#: l. 391, 551-556: first generation kept at least 5%; shares of second generation and non-agricultural fuels at most 95%
MIN_FIRST_GEN = 0.05
MAX_SHARE = 0.95
#: l. 432-433: an excise tax above 1.5 x the mean of its neighbours is replaced by that mean
CTAX_OUTLIER = 1.5
CTAX_PREV = 2010
CTAX_NEXT = 2020
#: l. 1377-1378: PRIMES's 2015 excise tax counts above this
CTAX_MIN_BASE = 1e-12
#: l. 568-575: waste oil's increase limited to the line between 2005 and 2015
WOIL_FROM = 2005
#: l. 580: pure vegetable oils at least 5% of waste oil
VOIL_MIN_SHARE = 0.05
#: l. 486-492: weights 1 / (distance^2 + 0.01) of the gap filling
GAP_EPS = 0.01
#: small values (l. 674-693, 853-859, 948-961, 1257-1270)
TINY = 1e-14
TINY_IMPT = 1e-12
#: l. 1253-1254: feedstocks below this are removed
MIN_FEEDSTOCK = 0.01
#: l. 893-894: revenue of new energy crops (EUR/ha, constant prices)
NECR_REVENUE = 250.0
TRUST_NECR = 10.0
#: l. 1239-1240: DDGS's feed use, imports
DDGS_IMPORT_SHARE = 0.05
#: l. 1420-1452: trust levels
TRUST_BIO = 7.0
TRUST_TRADE = 1.0
TRUST_DDGS = 3.0
TRUST_EXPD = 1.0
#: l. 1003-1005: PRCB's extrapolation runs from 2020 to %lst_dgagri%
PRCB_FROM = 2020
#: l. 1306: the constant-bioenergy hold starts after 2020
CONST_BIO_AFTER = 2020
#: l. 1360: "no change for excise taxes on biofuels after 2005"
CTAX_BIO_LAST = 2005

#: l. 990-997: Aglink's yields per feedstock (p_BFyld's source, fuel) and the stocks they move
PRCB_YIELDS = [("WT", "ET", {"SWHE"}), ("CG", "ET", {"BARL", "RYEM", "OATS", "OCER", "MAIZ"}),
               ("SBE", "ET", {"SUGA"})]
PRCB_YIELD_OILS = ("VL", "BD")
#: l. 1295-1306: map_constBioPos
CONST_BIO_COLS_SECO = ["NTRD", "NAGR", "FSTG", "SECG", "EXOG"]
#: biofuel_trends.gms's AgEUTot (l. 37: Aglink's EU total)
AG_EU_TOT = "EUN"

K4 = Tuple[str, str, str, int]


def _csv(path: Path) -> List[dict]:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def _set(d: Path, name: str) -> List[Tuple[str, ...]]:
    rows = _csv(d / f"{name}.csv")
    cols = [c for c in rows[0] if c.startswith("d")] if rows else ["d0"]
    return [tuple(r[c].upper() for c in cols) for r in rows]


@dataclass
class Inputs:
    """The file's own sets and data (tools/build/build_captrd_biofuel.py)."""
    units: Set[str]
    aux_cols: Set[str]
    aux_rows: Set[str]
    pcols: List[str]
    prows: List[str]
    aux_to_pcols: List[Tuple[str, str]]
    aux_to_prows: List[Tuple[str, str]]
    pyears: List[int]
    all_ferm: List[str]
    fstg_ferm: List[str]
    scale_cols: List[str]
    fuel_match: List[Tuple[str, str]]
    fuel_map: List[Tuple[str, str]]
    primes_ms_extra: List[str]
    potential: Dict[Tuple[str, str], float]
    proc_yields: Dict[str, float]
    primes: Dict[Tuple[str, str, str, str, int], float]
    fossil: Dict[Tuple[str, str, str, int], float]
    tax: Dict[Tuple[str, str, str, int], float]


def read_inputs(sets_dir: Path, dat_dir: Path) -> Inputs:
    b = sets_dir / "biofuel"
    one = lambda n: [x[0] for x in _set(b, n)]                     # noqa: E731
    pr = {}
    for r in _csv(dat_dir / "biofuel_p_primeswithunits.csv"):
        k = (r["region"].upper(), r["col"].upper(), r["row"].upper(), r["unit"].upper(), int(r["year"]))
        pr[k] = pr.get(k, 0.0) + float(r["value"])
    return Inputs(
        units=set(one("allunit")), aux_cols=set(one("auxcols")), aux_rows=set(one("auxrows")), pcols=one("pcols"),
        prows=one("prows"), aux_to_pcols=_set(b, "aux_to_pcols"), aux_to_prows=_set(b, "aux_to_prows"),
        pyears=[int(x) for x in one("pyears")], all_ferm=one("allfermentastocks"), fstg_ferm=one("fstgfermentastocks"),
        scale_cols=one("scalecols"), fuel_match=_set(b, "fuelmatch"), fuel_map=_set(b, "fuelmap"),
        primes_ms_extra=one("primesms_extra"),
        potential={(r["region"].upper(), r["stock"].upper()): float(r["value"])
                   for r in _csv(dat_dir / "biofuel_p_potentialstocks.csv")},
        proc_yields={r["row"].upper(): float(r["value"]) for r in _csv(dat_dir / "biofuel_proc_yields.csv")},
        primes=pr,
        fossil={(r["region"].upper(), r["col"].upper(), r["row"].upper(), int(r["year"])): float(r["value"])
                for r in _csv(dat_dir / "biofuel_p_fossilfuel.csv")},
        tax={(r["region"].upper(), r["fuel"].upper(), r["item"].upper(), int(r["year"])): float(r["value"])
             for r in _csv(dat_dir / "biofuel_p_taxdata.csv")})


class _P(dict):
    """A sparse GAMS parameter: a missing key is 0; storing 0 deletes the record, storing EPS keeps it (`eps`)."""

    def __init__(self):
        super().__init__()
        self.eps: Set[tuple] = set()

    def g(self, *k) -> float:
        return dict.get(self, k, 0.0)

    def nz(self, *k) -> bool:
        """GAMS's $ test: nonzero, EPS included."""
        return dict.get(self, k, 0.0) != 0.0 or k in self.eps

    def put(self, k, v, eps: bool = False) -> None:
        if v != 0.0:
            self[k] = v
            self.eps.discard(k)
        else:
            self.pop(k, None)
            if eps:
                self.eps.add(k)
            else:
                self.eps.discard(k)


@dataclass
class Result:
    expert: Dict[K4, Tuple[float, float]] = field(default_factory=dict)   # (Absolute, TrustLevl)
    eps: Set[K4] = field(default_factory=set)                             # EPS records of Absolute
    pdata: Dict[K4, float] = field(default_factory=dict)                  # p_data written (UVAG of the fuels)
    nobs: Set[Tuple[str, str, str]] = field(default_factory=set)          # p_data's nObs set to 1
    primes: Dict[K4, float] = field(default_factory=dict)                 # p_primesResults, for checking


def trends(I: Inputs, *, ms: Sequence[str], msincl: Sequence[str], msall: Iterable[str], nt2est: Sequence[str],
           years: Sequence[int], expostt: Sequence[int], exante: Sequence[int], exantet: Sequence[int],
           lst_dgagri: int, basy: int, pdata: Dict[K4, float], nobs: Set[Tuple[str, str, str]],
           basm: Dict[Tuple[str, str, str], float], step1: Dict[K4, float], aglink: Dict[tuple, float],
           bfyld: Dict[Tuple[str, str, str], float], extr_rates: Dict[Tuple[str, str], float],
           byproduct: Dict[Tuple[str, str], float], oilequ: Dict[str, float], density: Dict[str, float],
           s_colsest: Iterable[str], s_rowsest: Iterable[str], map_rr: Iterable[Tuple[str, str]],
           seco_biof: Sequence[str], fossil_fuels: Sequence[str], fuels: Sequence[str], biostock: Sequence[str],
           biostock_oilp: Iterable[str], stock_to_fuel: Iterable[Tuple[str, str]],
           stock_to_by: Iterable[Tuple[str, str]], bio_by: Iterable[str], cere: Sequence[str], balpos: Iterable[str],
           const_bio: Optional[bool] = None) -> Result:
    """The biofuel trends. pdata: p_data of the years (region, col, row, year); nobs: the (region, col, row) with
    p_data's nObs; basm: BASM per (region, col, row); step1: Step 1's results; aglink: Aglink's p_aglink
    (region, col, row, year as text); bfyld: p_BFyld (feedstock, fuel, year as text); extr_rates, byproduct:
    p_ExtrRates(fuel, stock), p_ByProduct(by-product, stock); const_bio: %constBionergy% (default: the setting
    captrd.const_bioenergy)."""
    if const_bio is None:
        from capri_mod.settings import current as _settings
        const_bio = bool(_settings().get("captrd.const_bioenergy"))
    ms = list(ms)
    msincl = list(msincl)
    ms_set = set(ms)
    msall = list(msall)
    exante = sorted(exante)
    exantet = sorted(exantet)
    expostt = sorted(expostt)
    years = sorted(years)
    yearscur = sorted(set(expostt) | set(exante))
    lst_expostt = max(expostt)
    seco = list(seco_biof)
    fos = list(fossil_fuels)
    mrr = set(map_rr)
    s2f = list(stock_to_fuel)
    s2by = list(stock_to_by)
    pd_ = lambda r, c, w, y: float(pdata.get((r, c, w, y), 0.0))    # noqa: E731
    out = Result()

    # l. 237-243: PRIMES's results over their domains (primesMs: BE, LU and MSALL; the units of AllUnit; the years of
    # SIMYY)
    primes_ms = set(I.primes_ms_extra) | set(msall)
    W = _P()
    for (r, c, w, u, y), v in I.primes.items():
        if r in primes_ms and c in I.aux_cols and w in I.aux_rows and u in I.units and y in years and v:
            W.put((r, c, w, u, y), v)
    pms = sorted(primes_ms)
    pyears = I.pyears
    R = _P()
    a2c: Dict[str, List[str]] = {}
    for a, p in I.aux_to_pcols:
        a2c.setdefault(p, []).append(a)
    a2r: Dict[str, List[str]] = {}
    for a, p in I.aux_to_prows:
        a2r.setdefault(p, []).append(a)
    units = list(I.units)
    for r in pms:                                                            # l. 338-340
        for pc in I.pcols:
            for pr in I.prows:
                for y in pyears:
                    R.put((r, pc, pr, y), sum(W.g(r, ac, ar, u, y) for ar in a2r.get(pr, [])
                                              for ac in a2c.get(pc, []) for u in units))
    for r in pms:                                                            # l. 342-344
        for pr in I.prows:
            for y in pyears:
                R.put((r, "NTRD", pr, y), -sum(W.g(r, "IMPT", ar, u, y) for ar in a2r.get(pr, []) for u in units))
    for r in pms:                                                            # l. 354-367
        for y in pyears:
            W.put((r, "BIOF", "OILS", "KTON", y), W.g(r, "BIOF", "OILS", "KTOE", y) * GJ_PER_TOE / LHV_RAPE)
            W.put((r, "BIOF", "VOIL", "KTOE", y),
                  max(0.0, W.g(r, "BIOF", "OILS", "KTON", y) * I.proc_yields["RAPO"] * LHV_RAPO / GJ_PER_TOE
                      + W.g(r, "IMPT", "VOIL", "KTOE", y)))
            for pr in ("VOIL", "WOIL"):
                if pr in I.prows:
                    R.put((r, "BIOF", pr, y), W.g(r, "BIOF", pr, "KTOE", y) * GJ_PER_TOE / LHV_RAPO)
    for r in pms:                                                            # l. 371-386
        for y in pyears:
            R.put((r, "SECG", "BIOD", y), max(0.0, R.g(r, "MAPR", "BIOD", y) - W.g(r, "TRANSEST", "NONFUNGI", "KTOE", y)))
            allf = sum(W.g(r, "FERMENTA", f, "KTOE", y) for f in I.all_ferm)
            fst = sum(W.g(r, "FERMENTA", f, "KTOE", y) for f in I.fstg_ferm)
            R.put((r, "SECG", "BIOE", y), max(0.0, (R.g(r, "MAPR", "BIOE", y) - W.g(r, "FERMENTA", "BIOETHAN", "KTOE", y))
                                              * (1 - ((fst / allf) if allf else 0.0))))
    for r in pms:                                                            # l. 393-399 (ExPostT)
        for y in expostt:
            R.put((r, "MAPR", "BIOE", y), R.g(r, "MAPR", "BIOE", y) - R.g(r, "SECG", "BIOE", y))
            R.put((r, "DOMM", "BIOE", y), R.g(r, "DOMM", "BIOE", y) - R.g(r, "SECG", "BIOE", y))
            R.put((r, "SECG", "BIOE", y), 0.0)
    for r in pms:                                                            # l. 401-402
        for y in pyears:
            if R.nz(r, "MAPR", "BIOE", y):
                R.put((r, "BIOESHARE", "SECG", y), R.g(r, "SECG", "BIOE", y) / R.g(r, "MAPR", "BIOE", y))
    for r in pms:                                                            # l. 405-412
        for pr in I.prows:
            if pr not in ("SUGA", "CERE"):
                continue
            for y in pyears:
                den = W.g(r, "BIOF", "CERE", "KTOE", y) + W.g(r, "BIOF", "SUGA", "KTOE", y)
                if den:
                    R.put((r, "BIOESHARE", pr, y), W.g(r, "BIOF", pr, "KTOE", y) / den
                          * max(MIN_FIRST_GEN, 1.0 - R.g(r, "BIOESHARE", "SECG", y)))
    for r in pms:                                                            # l. 415-428
        for f in fos:
            b_h = any(W.g(r, "HCOM", f, u, BAS_PRIMES) for u in ("KTOE",))
            b_u = W.g(r, "UVAP", f, "EUROPERTOE", BAS_PRIMES)
            for y in pyears:
                R.put((r, "HCOM", f, y), W.g(r, "HCOM", f, "KTOE", y)
                      + (I.fossil.get((r, "DOMM", f, y), 0.0) if not b_h else 0.0))
                R.put((r, "UVAP", f, y), W.g(r, "UVAP", f, "EUROPERTOE", y)
                      + (I.fossil.get((r, "UVAP", f, y), 0.0) if not b_u else 0.0))
                R.put((r, "CTAX", f, y), W.g(r, "CTAX", f, "EUROPERTOE", y))
    for r in pms:                                                            # l. 430-434
        for f in fos:
            c10, c15, c20 = (R.g(r, "CTAX", f, y) for y in (CTAX_PREV, BAS_PRIMES, CTAX_NEXT))
            if c15 > CTAX_OUTLIER * (c10 + c20) / 2:
                R.put((r, "CTAX", f, BAS_PRIMES), (c10 + c20) / 2)
    for pc in I.pcols:                                                       # l. 437-439
        for pr in I.prows:
            for y in pyears:
                R.put(("BL000000", pc, pr, y), R.g("BE000000", pc, pr, y)
                      + (R.g("LU000000", pc, pr, y) if pc != "BIOESHARE" else 0.0))
    for pc in I.pcols:                                                       # l. 440-446
        if pc not in ("UVAP", "CTAX"):
            continue
        for f in fos:
            for y in pyears:
                hb, hl = R.g("BE000000", "HCOM", f, y), R.g("LU000000", "HCOM", f, y)
                if hb + hl:
                    R.put(("BL000000", pc, f, y), (R.g("BE000000", pc, f, y) * hb + R.g("LU000000", pc, f, y) * hl)
                          / (hb + hl))
    for r in ms:                                                             # l. 452-453
        for c in I.scale_cols:
            for f in fuels:
                for y in pyears:
                    if R.nz(r, c, f, y):
                        R.put((r, c, f, y), R.g(r, c, f, y) / oilequ[f])
    for r in msall:                                                          # l. 482-493: the gaps
        for pc in I.pcols:
            for pr in I.prows:
                has = [y1 for y1 in pyears if R.nz(r, pc, pr, y1)]          # the values before the statement
                vals = {y1: R.g(r, pc, pr, y1) for y1 in has}
                for y in pyears:
                    if y in vals:
                        continue
                    if any(y1 > y for y1 in has) and any(y1 < y for y1 in has):
                        num = sum(vals[y1] / ((y1 - y) ** 2 + GAP_EPS) for y1 in has)
                        den = sum(1.0 / ((y1 - y) ** 2 + GAP_EPS) for y1 in has)
                        R.put((r, pc, pr, y), num / den)
    last_biod = max((y1 for y1 in pyears if any(R.nz(r, "MAPR", "BIOD", y1) for r in msall)), default=None)
    for i, y in enumerate(pyears):                                           # l. 497-505: interpolation
        if last_biod is None or y > last_biod or i + 1 >= len(pyears):
            continue
        y1 = pyears[i + 1]
        fill = [t for t in years if y < t < y1]
        for r in msall:
            for pc in I.pcols:
                for pr in I.prows:
                    if not any(R.nz(r, pc, pr, z) for z in pyears):
                        continue
                    for t in fill:
                        R.put((r, pc, pr, t), R.g(r, pc, pr, y) + (t - y) * (R.g(r, pc, pr, y1) - R.g(r, pc, pr, y))
                              / (y1 - y))
    for r in ms:                                                             # l. 509-512
        for y in yearscur:
            R.put((r, "BIOESHARE", "SECG", y), min(MAX_SHARE, R.g(r, "BIOESHARE", "SECG", y)))
            if R.nz(r, "MAPR", "BIOD", y):
                R.put((r, "BIODSHARE", "SECG", y), min(MAX_SHARE, R.g(r, "SECG", "BIOD", y) / R.g(r, "MAPR", "BIOD", y)))
    for r in msall:                                                          # l. 518-519
        for y in expostt:
            R.put((r, "NAGR", "BIOE", y), pd_(r, "NAGR", "BIOE", y))
        for y in exantet:
            R.put((r, "NAGR", "BIOE", y), pd_(r, "NAGR", "BIOE", lst_expostt))
    for r in ms:                                                             # l. 524-534
        for y in yearscur:
            R.put((r, "SECG", "BIOE", y), R.g(r, "MAPR", "BIOE", y) * R.g(r, "BIOESHARE", "SECG", y))
        for y in yearscur:
            R.put((r, "MAPR", "BIOE", y), R.g(r, "MAPR", "BIOE", y) + R.g(r, "NAGR", "BIOE", y))
        for y in yearscur:
            if R.nz(r, "MAPR", "BIOE", y):
                R.put((r, "BIOESHARE", "SECG", y), min(MAX_SHARE, R.g(r, "SECG", "BIOE", y) / R.g(r, "MAPR", "BIOE", y)))
        for y in yearscur:
            if R.nz(r, "MAPR", "BIOE", y):
                R.put((r, "BIOESHARE", "NAGR", y), min(MAX_SHARE, R.g(r, "NAGR", "BIOE", y) / R.g(r, "MAPR", "BIOE", y)))
    for r in ms:                                                             # l. 536-543 (on the values before it)
        old = {y: R.g(r, "BIOESHARE", "CERE", y) + R.g(r, "BIOESHARE", "SUGA", y) for y in yearscur}
        for pr in I.prows:
            if pr not in ("SUGA", "CERE"):
                continue
            for y in yearscur:
                den = old[y]
                if den:
                    R.put((r, "BIOESHARE", pr, y), R.g(r, "BIOESHARE", pr, y) / den
                          * max(MIN_FIRST_GEN, 1.0 - R.g(r, "BIOESHARE", "SECG", y) - R.g(r, "BIOESHARE", "NAGR", y)))
    fill = [t for t in years if WOIL_FROM < t < BAS_PRIMES]                  # l. 551-558
    for r in msall:
        if not R.nz(r, "BIOF", "WOIL", BAS_PRIMES):
            continue
        for t in fill:
            R.put((r, "BIOF", "WOIL", t), min(R.g(r, "BIOF", "WOIL", t), R.g(r, "BIOF", "WOIL", WOIL_FROM)
                                              + (t - WOIL_FROM) * (R.g(r, "BIOF", "WOIL", BAS_PRIMES)
                                                                   - R.g(r, "BIOF", "WOIL", WOIL_FROM))
                                              / (BAS_PRIMES - WOIL_FROM)))
    for r in msall:                                                          # l. 560-561
        for y in yearscur:
            R.put((r, "BIOF", "VOIL", y), max(R.g(r, "BIOF", "VOIL", y), R.g(r, "BIOF", "WOIL", y) * VOIL_MIN_SHARE))
    for r in msall:                                                          # l. 568-574
        for y in yearscur:
            wo, vo = R.g(r, "BIOF", "WOIL", y), R.g(r, "BIOF", "VOIL", y)
            if wo + vo:
                R.put((r, "NAGR", "BIOD", y), max(0.0, R.g(r, "MAPR", "BIOD", y) * (1 - R.g(r, "BIODSHARE", "SECG", y))
                                                  * wo / (wo + vo)))
    for r in ms:                                                             # l. 576-577
        for y in yearscur:
            if R.nz(r, "MAPR", "BIOD", y):
                R.put((r, "BIODSHARE", "NAGR", y), min(MAX_SHARE, R.g(r, "NAGR", "BIOD", y) / R.g(r, "MAPR", "BIOD", y)))
    for r in msall:                                                          # l. 580-581
        for f in seco:
            for y in expostt:
                R.put((r, "INDM", f, y), pd_(r, "INDM", f, y))
            for y in exantet:
                R.put((r, "INDM", f, y), pd_(r, "INDM", f, lst_expostt))
    for r in msall:                                                          # l. 589-596
        for f in seco:
            for y in yearscur:
                R.put((r, "BIOF", f, y), R.g(r, "DOMM", f, y))
            for y in yearscur:
                R.put((r, "DOMM", f, y), R.g(r, "INDM", f, y) + R.g(r, "BIOF", f, y))
        for f in fos:
            for y in yearscur:
                R.put((r, "DOMM", f, y), R.g(r, "HCOM", f, y))
    for r in ms:                                                             # l. 645-659
        for y in yearscur:
            R.put((r, "SUGA", "BIOE", y), R.g(r, "MAPR", "BIOE", y) * R.g(r, "BIOESHARE", "SUGA", y))
        for y in yearscur:
            R.put((r, "CERE", "BIOE", y), max(0.0, R.g(r, "MAPR", "BIOE", y) - R.g(r, "SUGA", "BIOE", y)
                                              - R.g(r, "SECG", "BIOE", y) - R.g(r, "NAGR", "BIOE", y)))
    out.primes = dict(R)

    # --- the expert supports (l. 669 on)
    E = _P()
    T = _P()
    bio_cols = {"BIOF", "PRCB", "PRCBY"}                                     # frm_timesets.gms l. 60-61
    bio_rows = {"BIOD", "BIOE", "DISL", "GASL", "CRDO", "DDGS"}
    ce, re_ = set(s_colsest), set(s_rowsest)
    for (r, c, w, y), v in pdata.items():                                    # l. 671-674
        if r in msincl and y in expostt and c in ce and w in re_ and (w in bio_rows or c in bio_cols) and v:
            E.put((r, c, w, y), v)
    for r in msincl:                                                         # l. 677-693
        for f in seco:
            for y in exantet:
                E.put((r, "DOMM", f, y), max(TINY, R.g(r, "DOMM", f, y) + (pd_(r, "DOMM", f, BAS_PRIMES)
                                                                         - R.g(r, "DOMM", f, BAS_PRIMES))))
                E.put((r, "INDM", f, y), max(TINY, min(R.g(r, "INDM", f, y), E.g(r, "DOMM", f, y))))
                E.put((r, "BIOF", f, y), max(TINY, E.g(r, "DOMM", f, y) - E.g(r, "INDM", f, y)))
                E.put((r, "MAPR", f, y), max(TINY, R.g(r, "MAPR", f, y) + (pd_(r, "MAPR", f, BAS_PRIMES)
                                                                         - R.g(r, "MAPR", f, BAS_PRIMES))))
    for r in msincl:                                                         # l. 744-778
        for f in seco:
            for y in exantet:
                E.put((r, "NTRD", f, y), E.g(r, "MAPR", f, y) - E.g(r, "BIOF", f, y) - E.g(r, "INDM", f, y))
            E.put((r, "NTRD", f, BAS_PRIMES), pd_(r, "EXPT", f, BAS_PRIMES) - pd_(r, "IMPT", f, BAS_PRIMES))
            n0 = E.g(r, "NTRD", f, BAS_PRIMES)
            for y in exantet:
                if E.g(r, "NTRD", f, y) >= n0:
                    E.put((r, "EXPT", f, y), pd_(r, "EXPT", f, BAS_PRIMES) + (E.g(r, "NTRD", f, y) - n0))
            for y in exantet:
                if E.g(r, "NTRD", f, y) >= n0:
                    E.put((r, "IMPT", f, y), pd_(r, "IMPT", f, BAS_PRIMES))
            for y in exantet:
                if E.g(r, "NTRD", f, y) < n0:
                    E.put((r, "IMPT", f, y), pd_(r, "IMPT", f, BAS_PRIMES) - (E.g(r, "NTRD", f, y) - n0))
            for y in exantet:
                if E.g(r, "NTRD", f, y) < n0:
                    E.put((r, "EXPT", f, y), pd_(r, "EXPT", f, BAS_PRIMES))
            E.put((r, "NTRD", f, BAS_PRIMES), 0.0)
    for r in msincl:                                                         # l. 783-789
        for y in exantet:
            E.put((r, "SECG", "BIOD", y), max(TINY, E.g(r, "MAPR", "BIOD", y) * R.g(r, "BIODSHARE", "SECG", y)))
            E.put((r, "SECG", "BIOE", y), max(TINY, E.g(r, "MAPR", "BIOE", y) * R.g(r, "BIOESHARE", "SECG", y)))
    for r in msincl:                                                         # l. 792-803: new energy crops
        for y in exantet:
            if R.nz(r, "LIGN", "LEVL", y):
                E.put((r, "NECR", "LEVL", y), max(0.0, step1.get((r, "TSET", "LEVL", y), 0.0)) + R.g(r, "LIGN", "LEVL", y))
        if any(E.nz(r, "NECR", "LEVL", y) for y in exante):
            for y in exantet:
                if not E.nz(r, "NECR", "LEVL", y):
                    E.put((r, "NECR", "LEVL", y), 0.0, eps=True)
    m_of = {n: [m for m in ms if (m, n) in mrr] for n in nt2est}
    for n in nt2est:                                                         # l. 807-813
        if n in ms_set:
            continue
        for y in exante:
            if not sum(basm.get((m, "UAAR", "LEVL"), 0.0) for m in m_of[n]):
                continue
            v = sum(E.g(m, "NECR", "LEVL", y) / basm[(m, "UAAR", "LEVL")] for m in m_of[n]
                    if basm.get((m, "UAAR", "LEVL"), 0.0)) * basm.get((n, "UAAR", "LEVL"), 0.0)
            eps = any(E.nz(m, "NECR", "LEVL", y) for m in m_of[n]) and basm.get((n, "UAAR", "LEVL"), 0.0) != 0.0
            E.put((n, "NECR", "LEVL", y), v, eps=eps)
    rest = list(dict.fromkeys(list(msincl) + [n for n in nt2est if n not in ms_set]))
    for r in rest:                                                           # l. 814-822
        for y in exante:
            if E.nz(r, "NECR", "LEVL", y):
                T.put((r, "NECR", "LEVL", y), TRUST_NECR)
                E.put((r, "NECR", "OCRO", y), NECR_REVENUE)
        if any(E.nz(r, "NECR", "LEVL", y) for y in exante):
            out.nobs.update({(r, "NECR", "LEVL"), (r, "NECR", "OCRO")})
    for r in msincl:                                                         # l. 943-958
        for f, sh in (("BIOE", "BIOESHARE"), ("BIOD", "BIODSHARE")):
            for y in exantet:
                if R.nz(r, "NAGR", f, y):
                    E.put((r, "NAGR", f, y), max(TINY, min(pd_(r, "NAGR", f, BAS_PRIMES) + R.g(r, "NAGR", f, y)
                                                           - R.g(r, "NAGR", f, BAS_PRIMES),
                                                           E.g(r, "MAPR", f, y) * R.g(r, sh, "NAGR", y))))
    oilp = set(biostock_oilp)

    def yl(src, fuel, y):
        return bfyld.get((src, fuel, str(y)), 0.0)
    for r in msincl:                                                         # l. 986-997
        for s in biostock:
            for y in exante:
                if E.nz(r, "PRCB", s, y):
                    continue
                f = 1.0
                for src, fuel, stocks in PRCB_YIELDS:
                    if s in stocks:
                        f += yl(src, fuel, y) / yl(src, fuel, BAS_PRIMES) - 1
                if s in oilp:
                    f += yl(*PRCB_YIELD_OILS, y) / yl(*PRCB_YIELD_OILS, BAS_PRIMES) - 1
                E.put((r, "PRCB", s, y), sum(extr_rates.get((sf, s), 0.0) for sf in seco) * f)
            for y in exante:
                if not E.nz(r, "PRCBY", s, y):
                    E.put((r, "PRCBY", s, y), sum(byproduct.get((b, s), 0.0) for b in bio_by))
    has2020 = PRCB_FROM in exantet
    base_y = PRCB_FROM if has2020 else min(exante)
    for r in msincl:                                                         # l. 999-1009
        for s in biostock:
            last = E.g(r, "PRCB", s, lst_dgagri)
            for y in exantet:
                if y > lst_dgagri and last:
                    E.put((r, "PRCB", s, y), last * (1 + (last / E.g(r, "PRCB", s, base_y) - 1) * (y - lst_dgagri)
                                                     / (lst_dgagri - base_y)))
            for y in exantet:
                if y > lst_dgagri:
                    E.put((r, "PRCBY", s, y), E.g(r, "PRCBY", s, lst_dgagri))
    # l. 1013-1272: feedstocks
    run_stock = [s for s in biostock if s not in ("SUGA", "TWIN")]
    for r in msincl:                                                         # l. 1062
        for y in exantet:
            E.put((r, "BIOF", "TWIN", y), pd_(r, "BIOF", "TWIN", BAS_PRIMES))
    if any(E.nz(r, "BIOF", "SUGA", y) for r in msall for y in exantet):     # l. 1064-1085: KWS's supports
        raise NotImplementedError("biofuel trends: sugar supports from KWS (l. 1064-1085) are not ported: not "
                                  "reached in the reference run")
    for r in msincl:                                                         # l. 1088-1091
        for y in exantet:
            if E.nz(r, "PRCB", "SUGA", y):
                E.put((r, "BIOF", "SUGA", y), max(0.0, E.g(r, "BIOF", "SUGA", BAS_PRIMES)
                                                  + (R.g(r, "SUGA", "BIOE", y) - R.g(r, "SUGA", "BIOE", BAS_PRIMES))
                                                  / E.g(r, "PRCB", "SUGA", y)))
    agr = _P()
    share = _P()
    for rb in seco:                                                          # l. 1116-1210
        st = [s for s in run_stock if (s, rb) in set(s2f)]
        for r in msincl:
            for y in exantet:
                if E.nz(r, "MAPR", rb, y):
                    fix = (E.g(r, "BIOF", "SUGA", y) * E.g(r, "PRCB", "SUGA", y)
                           + E.g(r, "BIOF", "TWIN", y) * E.g(r, "PRCB", "TWIN", y)) if rb == "BIOE" else 0.0
                    agr.put((r, rb, y), max(TINY, E.g(r, "MAPR", rb, y) - E.g(r, "SECG", rb, y)
                                            - E.g(r, "NAGR", rb, y) - fix))
        for r in msincl:
            for s in st:
                for y in expostt:
                    tot = sum(pd_(r, "PRCB", s1, y) * pd_(r, "BIOF", s1, y) for s1 in st)
                    own = pd_(r, "PRCB", s, y) * pd_(r, "BIOF", s, y)
                    if tot and own:
                        share.put((r, s, y), own / tot)
            for s in st:
                if pd_(r, "PRCB", s, BAS_PRIMES):
                    for y in exantet:
                        share.put((r, s, y), share.g(r, s, BAS_PRIMES))
            for s in st:
                if (r, "DOMM", s) in nobs:
                    for y in exantet:
                        share.put((r, s, y), max(share.g(r, s, y), I.potential.get((r, s), 0.0)))
            for y in exantet:
                share.put((r, rb, y), sum(share.g(r, s, y) for s in st))
            for s in st:
                for y in exantet:
                    if share.nz(r, rb, y) and share.nz(r, s, y):
                        share.put((r, s, y), share.g(r, s, y) / share.g(r, rb, y))
            for s in st:
                for y in exantet:
                    if E.nz(r, "PRCB", s, y):
                        E.put((r, "BIOF", s, y), agr.g(r, rb, y) * share.g(r, s, y) / E.g(r, "PRCB", s, y))
    ddgs_src = [o for o, b in s2by if b == "DDGS"]
    for r in msincl:                                                         # l. 1213-1247: DDGS
        for y in exantet:
            if any(E.nz(r, "PRCBY", o, y) for o in ddgs_src):
                E.put((r, "MAPR", "DDGS", y), sum(E.g(r, "PRCBY", o, y) * E.g(r, "BIOF", o, y) for o in ddgs_src))
            mp, fp = E.g(r, "MAPR", "DDGS", y), basm.get((r, "GROF", "FPRO"), 0.0)
            if mp + fp:
                E.put((r, "FEDM", "DDGS", y), mp * (1.0 - mp / (mp + fp)))
            E.put((r, "DOMM", "DDGS", y), E.g(r, "FEDM", "DDGS", y))
            if E.nz(r, "MAPR", "DDGS", y):
                E.put((r, "NTRD", "DDGS", y), E.g(r, "MAPR", "DDGS", y) - E.g(r, "DOMM", "DDGS", y))
            if E.nz(r, "FEDM", "DDGS", y):
                E.put((r, "IMPT", "DDGS", y), max(TINY_IMPT, DDGS_IMPORT_SHARE * E.g(r, "MAPR", "DDGS", y)))
            E.put((r, "EXPT", "DDGS", y), E.g(r, "IMPT", "DDGS", y) + E.g(r, "NTRD", "DDGS", y))
    fuel_of: Dict[str, List[str]] = {}
    for s, f in s2f:
        fuel_of.setdefault(s, []).append(f)
    for r in msincl:                                                         # l. 1251-1264
        for s in biostock:
            for y in exantet:
                if E.g(r, "BIOF", s, y) < MIN_FEEDSTOCK:
                    E.put((r, "BIOF", s, y), 0.0)
            for y in exantet:
                if (not E.nz(r, "BIOF", s, y) and any(E.nz(r, "MAPR", f, y) for f in fuel_of.get(s, []))
                        and (pd_(r, "DOMM", s, BAS_PRIMES) or pd_(r, "BIOF", s, BAS_PRIMES)) and r in ms_set):
                    E.put((r, "BIOF", s, y), TINY)
    for r in msincl:                                                         # l. 1267-1280
        for y in exante:
            E.put((r, "BIOF", "CERE", y), sum(E.g(r, "BIOF", c, y) for c in cere))
        for s in biostock:
            for y in exante:
                mapr = any(E.nz(r, "MAPR", f, y) for f in fuel_of.get(s, []))
                if not E.nz(r, "BIOF", s, y) and E.nz(r, "PRCB", s, y) and r in ms_set:
                    E.put((r, "PRCB", s, y), TINY if mapr else 0.0)
            for y in exante:
                mapr = any(E.nz(r, "MAPR", f, y) for f in fuel_of.get(s, []))
                if not E.nz(r, "BIOF", s, y) and r in ms_set:
                    E.put((r, "PRCBY", s, y), TINY if mapr else 0.0)
    for r in msincl:                                                         # l. 1283-1288
        for y in exante:
            E.put((r, "MAPR", "BIOE", y), sum(E.g(r, "BIOF", s, y) * E.g(r, "PRCB", s, y) for s, f in s2f if f == "BIOE")
                  + E.g(r, "SECG", "BIOE", y) + E.g(r, "NAGR", "BIOE", y))
    if const_bio:                                                            # l. 1297-1318
        bal = set(balpos)
        eu = {m for m in msincl if ("EU028000", m) in mrr}

        def hold(c, w):
            return (c == "BIOF" or (c in bal and w in seco) or (c in CONST_BIO_COLS_SECO and w in seco)
                    or (c, w) == ("NECR", "LEVL") or (c in bal and w == "DDGS") or (c, w) == ("NTRD", "DDGS"))
        keys = {(r, c, w) for (r, c, w, y) in list(E) + list(E.eps) if r in eu and hold(c, w)}
        for r, c, w in sorted(keys):
            for y in exante:
                if y > CONST_BIO_AFTER:
                    E.put((r, c, w, y), E.g(r, c, w, CONST_BIO_AFTER), eps=(r, c, w, CONST_BIO_AFTER) in E.eps)
    for r in msincl:                                                         # l. 1323-1331
        for f in fos:
            for y in exante:
                E.put((r, "DOMM", f, y), R.g(r, "HCOM", f, y))
                E.put((r, "HCOM", f, y), R.g(r, "HCOM", f, y))
            for y in exantet:
                inha = pd_(r, "INHA", "LEVL", y)
                if inha:
                    E.put((r, "INHA", f, y), E.g(r, "HCOM", f, y) / inha * 1000)
    tax = dict(I.tax)                                                        # l. 1344-1366
    for r in msincl:
        for f in seco:
            for y in expostt:
                if y > CTAX_BIO_LAST:
                    v = tax.get((r, f, "CTAX", CTAX_BIO_LAST), 0.0)
                    if v:
                        tax[(r, f, "CTAX", y)] = v
                    else:
                        tax.pop((r, f, "CTAX", y), None)
            for y in expostt:
                v = tax.get((r, f, "CTAX", y), 0.0)
                if v:
                    tax[(r, f, "CTAX", y)] = v / oilequ[f] / density[f]
    ycur = set(yearscur)

    def any_dom(r, f):
        return any(E.nz(r, "DOMM", f, y) for y in ycur)
    for r in msincl:
        for f in seco:
            if any_dom(r, f):
                for y in exante:
                    E.put((r, "CTAX", f, y), tax.get((r, f, "CTAX", y), 0.0)
                          + (tax.get((r, f, "CTAX", BAS_PRIMES), 0.0) if y not in set(expostt) else 0.0) + TINY)
        for f in fos:                                                        # l. 1369-1381
            if any_dom(r, f) and not any(E.nz(r, "CTAX", f, y) for y in ycur):
                for y in expostt:
                    E.put((r, "CTAX", f, y), R.g(r, "CTAX", f, y))
            if any_dom(r, f):
                b = R.g(r, "CTAX", f, BAS_PRIMES)
                for y in exantet:
                    E.put((r, "CTAX", f, y), E.g(r, "CTAX", f, BAS_PRIMES)
                          + ((R.g(r, "CTAX", f, y) - b) if b > CTAX_MIN_BASE else 0.0) + TINY)
    fmap: Dict[str, List[str]] = {}
    for f, a in I.fuel_map:
        fmap.setdefault(f, []).append(a)
    ag = lambda col, a, y: aglink.get((AG_EU_TOT, col, a, str(y)), 0.0)    # noqa: E731
    P = dict(pdata)
    for r in msincl:                                                         # l. 1386-1394: p_data's fuel prices
        for f in fuels:
            if not P.get((r, "UVAG", f, basy), 0.0):
                v = sum(ag("PP", a, basy) for a in fmap.get(f, []))
                if v:
                    P[(r, "UVAG", f, basy)] = v
                    out.pdata[(r, "UVAG", f, basy)] = v
            base = sum(ag("PP", a, basy) for a in fmap.get(f, []))
            for y in expostt:
                if not P.get((r, "UVAG", f, y), 0.0) and base and y > basy:
                    v = P.get((r, "UVAG", f, basy), 0.0) * sum(ag("PP", a, y) for a in fmap.get(f, [])) / base
                    if v:
                        P[(r, "UVAG", f, y)] = v
                        out.pdata[(r, "UVAG", f, y)] = v
            for y in expostt:
                if not E.nz(r, "UVAG", f, y):
                    E.put((r, "UVAG", f, y), P.get((r, "UVAG", f, y), 0.0))
    match: Dict[str, List[str]] = {}
    for f, ff in I.fuel_match:
        match.setdefault(f, []).append(ff)
    for r in msincl:                                                         # l. 1397-1411
        for f in fuels:
            own = sum(R.g(r, "UVAP", ff, BAS_PRIMES) for ff in match.get(f, []))
            eu = sum(R.g("EU028000", "UVAP", ff, BAS_PRIMES) for ff in match.get(f, []))
            for y in exante:
                if y in set(expostt) or not (own or eu):
                    continue
                if own:
                    ratio = sum(R.g(r, "UVAP", ff, y) / R.g(r, "UVAP", ff, BAS_PRIMES) for ff in match.get(f, [])
                                if R.g(r, "UVAP", ff, BAS_PRIMES))
                else:
                    ratio = sum(R.g("EU028000", "UVAP", ff, y) / R.g("EU028000", "UVAP", ff, BAS_PRIMES)
                                for ff in match.get(f, []) if R.g("EU028000", "UVAP", ff, BAS_PRIMES))
                E.put((r, "UVAG", f, y), E.g(r, "UVAG", f, BAS_PRIMES) * ratio)
        for f in fuels:                                                      # l. 1413-1414
            if any_dom(r, f):
                for y in exante:
                    E.put((r, "UVAD", f, y), E.g(r, "UVAG", f, y) + E.g(r, "CTAX", f, y))
        for f in fuels:                                                      # l. 1416-1417
            for c in ("UVAG", "UVAD", "CTAX"):
                for y in yearscur:
                    if E.nz(r, c, f, y):
                        E.put((r, c, f, y), E.g(r, c, f, y) * oilequ[f])
        for f in fuels:                                                      # l. 1419-1421
            for y in exante:
                if E.nz(r, "UVAD", f, y) and E.nz(r, "INHA", f, y):
                    E.put((r, "EXPD", f, y), E.g(r, "UVAD", f, y) * E.g(r, "INHA", f, y) / 1000.0)
    cols_seen = {k[1] for k in list(E) + list(E.eps)}
    for r in msincl:                                                         # l. 1424-1452: trust levels
        for y in exante:
            for c in cols_seen:
                for f in seco:
                    if E.nz(r, c, f, y):
                        T.put((r, c, f, y), TRUST_BIO)
            for f in seco:
                for c in ("IMPT", "EXPT"):
                    if E.nz(r, c, f, y):
                        T.put((r, c, f, y), TRUST_TRADE)
            for c in cols_seen:
                for f in fos:
                    if E.nz(r, c, f, y):
                        T.put((r, c, f, y), TRUST_BIO)
            for s in biostock:
                if E.nz(r, "BIOF", s, y):
                    T.put((r, "BIOF", s, y), TRUST_BIO)
            if E.nz(r, "BIOF", "CERE", y):
                T.put((r, "BIOF", "CERE", y), TRUST_BIO)
            for s in biostock:
                if E.nz(r, "BIOF", s, y):
                    T.put((r, "PRCB", s, y), TRUST_BIO)
                    T.put((r, "PRCBY", s, y), TRUST_BIO)
            for f in fuels:
                if E.nz(r, "UVAD", f, y) and E.nz(r, "INHA", f, y) and E.nz(r, "EXPD", f, y):
                    T.put((r, "EXPD", f, y), TRUST_EXPD)
            for c in ("FEDM", "DOMM", "MAPR", "EXPT", "IMPT"):
                if E.nz(r, c, "DDGS", y):
                    T.put((r, c, "DDGS", y), TRUST_DDGS)
            if E.nz(r, "NTRD", "DDGS", y) and E.nz(r, "EXPT", "DDGS", y):
                T.put((r, "NTRD", "DDGS", y), TRUST_TRADE * T.g(r, "EXPT", "DDGS", y) * E.g(r, "NTRD", "DDGS", y)
                      / E.g(r, "EXPT", "DDGS", y))
    ex = set(exante)
    for (r, c, w, y) in list(E) + list(E.eps):                               # l. 1455-1470: nObs
        if y in ex and r in set(msincl) and (w in set(seco) or w == "DDGS" or w in set(fuels)
                                             or (c in ("BIOF", "PRCB", "PRCBY") and w in set(biostock))
                                             or (c, w) == ("BIOF", "CERE")):
            if c in ("PRCB", "PRCBY") and not any(E.nz(r, "BIOF", w, z) for z in ex):
                continue
            if (r, c, w) not in nobs:
                out.nobs.add((r, c, w))
    keys = set(E) | E.eps | set(T)
    out.expert = {k: (E.g(*k), T.g(*k)) for k in keys}
    out.eps = set(E.eps)
    return out
