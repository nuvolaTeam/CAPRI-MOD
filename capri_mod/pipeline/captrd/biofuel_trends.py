"""CAPTRD's expert supports for the biofuel sector from PRIMES (biofuel/biofuel_trends.gms, included by
captrd/expert_support.gms l. 108 with %NewBiofuelModule% on; CAPRI star 3.0), with the reference run's switches:
%aglinkTightLink%, %consBioTrends%, %stronglycutNECR%, %FixExogenFactGlobiom% off, %ScaleToDGAGRI% off (the GUI's
"Scaling to DG Agri baseline", and l. 627-628 keep it off for projections beyond 2020), %FARM_B% off.

In GAMS's order (line numbers of biofuel_trends.gms):
  l. 243      PRIMES's results p_primesWithUnits (dat/biofuel/%primesBiofuelFile%.gdx), loaded over their domains
  l. 339-406  aggregated to p_primesResults: production, demand, net trade, the biodiesel from oils, the second
              generation shares, the feedstock shares of ethanol (at least 5% first generation)
  l. 411-449  fossil fuels' demand, prices and excise taxes (PRIMES, else fossilFuel.gdx); Belgium + Luxembourg
  l. 456-460  fuels from ktoe to 1000 t (p_oilEqu)
  l. 482-506  gaps filled by distance-weighted means, then linear interpolation over the years between PRIMES's
  l. 512-613  shares of second generation and non-agricultural fuels, waste oil, industrial use, fuel demand
  l. 641-658  ethanol from sugar and cereals
  l. 667-902  the expert supports: the ex-post p_data of the biofuel series; demand, industrial use, biofuel use and
              production as PRIMES's change on the 2015 data; net trade, exports and imports; second generation; the
              new energy crops NECR (member states and NUTS 2 regions, trust 10, revenue 250)
  l. 945-1011 non-agricultural fuels; processing coefficients PRCB (Aglink's yield changes) and by-products PRCBY,
              extrapolated beyond %lst_dgagri%
  l. 1020-1283 feedstock use: sugar from PRIMES's change, the other feedstocks by their base shares (at least
              p_potentialStocks), DDGS; small feedstocks removed or fixed close to zero
  l. 1288-1293 ethanol production recomputed from its feedstocks
  l. 1299-1318 %constBionergy% (the 2023 Brightspace baseline): the EU28 member states' biofuel positions after 2020 at
              their 2020 values (setting captrd.const_bioenergy: on, CAPRI's default, acting only with that long-run
              selection; the reference run did not apply it, so its parity test sets it off)
  l. 1325-1423 fossil fuel demand, per inhabitant; excise taxes (biofuel_data.gms's p_taxData), prices from PRIMES's
              change, consumer prices, per ton; EXPD
  l. 1428-1483 trust levels; p_data's nObs of the new series

A statement whose right side reads the parameter it assigns takes the values from before the statement (the cereal and
sugar shares of l. 544-550, the gaps of l. 482-492), as GAMS does: CAPTRD's sugar feedstock (Germany 2020: 192.464)
is reproduced that way and not with the values the statement has already written (180.813). EPS (the new energy
crops' zero years, l. 877-879) is carried as such: CAPTRD's results store it, and a $ condition takes it as nonzero.

CAPRI's GAMS statement of each block is quoted by the function that computes it, in
capri_mod/pipeline/captrd/equations/biofuel_trends.py; trends holds the loops, the conditions and the data, and
calls them.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from capri_mod.pipeline.captrd.equations import biofuel_trends as BT

#: l. 79, 428: PRIMES's reference year (%BASprimes%)
BAS_PRIMES = 2015
#: captrd.gms l. 97, biofuel_trends.gms l. 1299: the long-run selection with which %constBionergy% acts
BRIGHT_SCENARIO = "globiom_eu_bright_s0_2023+REFERENCE+REFERENCE"
#: l. 430-433: an excise tax above 1.5 x the mean of its neighbours is replaced by that mean
CTAX_OUTLIER = 1.5
CTAX_PREV = 2010
CTAX_NEXT = 2020
#: l. 560-569: waste oil's increase limited to the line between 2005 and 2015
WOIL_FROM = 2005
#: l. 1253-1257: feedstocks below this are removed
MIN_FEEDSTOCK = 0.01
#: l. 1001-1008: PRCB's extrapolation runs from 2020 to %lst_dgagri%
PRCB_FROM = 2020
#: l. 1314: the constant-bioenergy hold starts after 2020
CONST_BIO_AFTER = 2020
#: l. 1347-1348: "no change for excise taxes on biofuels after 2005"
CTAX_BIO_LAST = 2005

#: l. 988-992: Aglink's yields per feedstock (p_BFyld's source, fuel) and the stocks they move
PRCB_YIELDS = [("WT", "ET", {"SWHE"}), ("CG", "ET", {"BARL", "RYEM", "OATS", "OCER", "MAIZ"}),
               ("SBE", "ET", {"SUGA"})]
PRCB_YIELD_OILS = ("VL", "BD")
#: l. 1301-1311: map_constBioPos
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
    p_ExtrRates(fuel, stock), p_ByProduct(by-product, stock); const_bio: whether l. 1297-1318 apply (default: the
    setting captrd.const_bioenergy, with the long-run selection captrd.longrun_scenario the Brightspace baseline, as
    the $iftheni of l. 1299 requires both)."""
    if const_bio is None:
        from capri_mod.settings import current as _settings
        const_bio = (bool(_settings().get("captrd.const_bioenergy"))
                     and str(_settings().get("captrd.longrun_scenario")) == BRIGHT_SCENARIO)
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

    # l. 243: PRIMES's results over their domains (primesMs: BE, LU and MSALL; the units of AllUnit; the years of
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
    for r in pms:                                                            # l. 339-341
        for pc in I.pcols:
            for pr in I.prows:
                for y in pyears:
                    R.put((r, pc, pr, y), BT.p_primesResults([W.g(r, ac, ar, u, y) for ar in a2r.get(pr, [])
                                                              for ac in a2c.get(pc, []) for u in units]))
    for r in pms:                                                            # l. 344-346
        for pr in I.prows:
            for y in pyears:
                R.put((r, "NTRD", pr, y), BT.p_primesResults_NTRD([W.g(r, "IMPT", ar, u, y) for ar in a2r.get(pr, [])
                                                                   for u in units]))
    for r in pms:                                                            # l. 357-368
        for y in pyears:
            W.put((r, "BIOF", "OILS", "KTON", y), BT.p_primesWithUnits_OILS_kton(W.g(r, "BIOF", "OILS", "KTOE", y)))
            W.put((r, "BIOF", "VOIL", "KTOE", y),
                  BT.p_primesWithUnits_VOIL_ktoe(W.g(r, "BIOF", "OILS", "KTON", y), I.proc_yields["RAPO"],
                                                 W.g(r, "IMPT", "VOIL", "KTOE", y)))
            for pr in ("VOIL", "WOIL"):
                if pr in I.prows:
                    R.put((r, "BIOF", pr, y), BT.p_primesResults_BIOF_oil(W.g(r, "BIOF", pr, "KTOE", y)))
    for r in pms:                                                            # l. 373-384
        for y in pyears:
            R.put((r, "SECG", "BIOD", y), BT.p_primesResults_SECG_BIOD(R.g(r, "MAPR", "BIOD", y),
                                                                       W.g(r, "TRANSEST", "NONFUNGI", "KTOE", y)))
            allf = sum(W.g(r, "FERMENTA", f, "KTOE", y) for f in I.all_ferm)
            fst = sum(W.g(r, "FERMENTA", f, "KTOE", y) for f in I.fstg_ferm)
            R.put((r, "SECG", "BIOE", y), BT.p_primesResults_SECG_BIOE(R.g(r, "MAPR", "BIOE", y),
                                                                       W.g(r, "FERMENTA", "BIOETHAN", "KTOE", y), fst,
                                                                       allf))
    for r in pms:                                                            # l. 390-394 (expostT)
        for y in expostt:
            R.put((r, "MAPR", "BIOE", y), BT.p_primesResults_expostT_first_gen(R.g(r, "MAPR", "BIOE", y),
                                                                               R.g(r, "SECG", "BIOE", y)))
            R.put((r, "DOMM", "BIOE", y), BT.p_primesResults_expostT_first_gen(R.g(r, "DOMM", "BIOE", y),
                                                                               R.g(r, "SECG", "BIOE", y)))
            R.put((r, "SECG", "BIOE", y), BT.p_primesResults_SECG_BIOE_expostT())
    for r in pms:                                                            # l. 396-397
        for y in pyears:
            if R.nz(r, "MAPR", "BIOE", y):
                R.put((r, "BIOESHARE", "SECG", y), BT.p_primesResults_bioeShare_SECG(R.g(r, "SECG", "BIOE", y),
                                                                                     R.g(r, "MAPR", "BIOE", y)))
    for r in pms:                                                            # l. 400-406
        for pr in I.prows:
            if pr not in ("SUGA", "CERE"):
                continue
            for y in pyears:
                den = W.g(r, "BIOF", "CERE", "KTOE", y) + W.g(r, "BIOF", "SUGA", "KTOE", y)
                if den:
                    R.put((r, "BIOESHARE", pr, y), BT.p_primesResults_bioeShare_stocks(
                        W.g(r, "BIOF", pr, "KTOE", y), W.g(r, "BIOF", "CERE", "KTOE", y),
                        W.g(r, "BIOF", "SUGA", "KTOE", y), R.g(r, "BIOESHARE", "SECG", y)))
    for r in pms:                                                            # l. 415-426
        for f in fos:
            b_h = any(W.g(r, "HCOM", f, u, BAS_PRIMES) for u in ("KTOE",))
            b_u = W.g(r, "UVAP", f, "EUROPERTOE", BAS_PRIMES)
            for y in pyears:
                R.put((r, "HCOM", f, y), BT.p_primesResults_fossil(W.g(r, "HCOM", f, "KTOE", y),
                                                                   I.fossil.get((r, "DOMM", f, y), 0.0), b_h))
                R.put((r, "UVAP", f, y), BT.p_primesResults_fossil(W.g(r, "UVAP", f, "EUROPERTOE", y),
                                                                   I.fossil.get((r, "UVAP", f, y), 0.0), b_u))
                R.put((r, "CTAX", f, y), BT.p_primesResults_CTAX(W.g(r, "CTAX", f, "EUROPERTOE", y)))
    for r in pms:                                                            # l. 430-433
        for f in fos:
            c10, c15, c20 = (R.g(r, "CTAX", f, y) for y in (CTAX_PREV, BAS_PRIMES, CTAX_NEXT))
            if c15 > CTAX_OUTLIER * (c10 + c20) / 2:
                R.put((r, "CTAX", f, BAS_PRIMES), BT.p_primesResults_CTAX_2015(c10, c20))
    for pc in I.pcols:                                                       # l. 439-441
        for pr in I.prows:
            for y in pyears:
                R.put(("BL000000", pc, pr, y), BT.p_primesResults_BL(R.g("BE000000", pc, pr, y),
                                                                     R.g("LU000000", pc, pr, y), pc == "BIOESHARE"))
    for pc in I.pcols:                                                       # l. 443-449
        if pc not in ("UVAP", "CTAX"):
            continue
        for f in fos:
            for y in pyears:
                hb, hl = R.g("BE000000", "HCOM", f, y), R.g("LU000000", "HCOM", f, y)
                if hb + hl:
                    R.put(("BL000000", pc, f, y), BT.p_primesResults_BL_price(R.g("BE000000", pc, f, y), hb,
                                                                              R.g("LU000000", pc, f, y), hl))
    for r in ms:                                                             # l. 459-460
        for c in I.scale_cols:
            for f in fuels:
                for y in pyears:
                    if R.nz(r, c, f, y):
                        R.put((r, c, f, y), BT.p_primesResults_scaleCols(R.g(r, c, f, y), oilequ[f]))
    for r in msall:                                                          # l. 482-492: the gaps
        for pc in I.pcols:
            for pr in I.prows:
                has = [y1 for y1 in pyears if R.nz(r, pc, pr, y1)]          # the values before the statement
                vals = {y1: R.g(r, pc, pr, y1) for y1 in has}
                for y in pyears:
                    if y in vals:
                        continue
                    if any(y1 > y for y1 in has) and any(y1 < y for y1 in has):
                        R.put((r, pc, pr, y), BT.p_primesResults_gap(vals, y))
    last_biod = max((y1 for y1 in pyears if any(R.nz(r, "MAPR", "BIOD", y1) for r in msall)), default=None)
    for i, y in enumerate(pyears):                                           # l. 496-506: interpolation
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
                        R.put((r, pc, pr, t), BT.p_primesResults_Fillyears(R.g(r, pc, pr, y), R.g(r, pc, pr, y1), y,
                                                                           y1, t))
    for r in ms:                                                             # l. 512-516
        for y in yearscur:
            R.put((r, "BIOESHARE", "SECG", y), BT.p_primesResults_bioeShare_SECG_max(R.g(r, "BIOESHARE", "SECG", y)))
            if R.nz(r, "MAPR", "BIOD", y):
                R.put((r, "BIODSHARE", "SECG", y), BT.p_primesResults_share(R.g(r, "SECG", "BIOD", y),
                                                                            R.g(r, "MAPR", "BIOD", y)))
    for r in msall:                                                          # l. 523-524
        for y in expostt:
            R.put((r, "NAGR", "BIOE", y), BT.p_primesResults_P_DATA(pd_(r, "NAGR", "BIOE", y)))
        for y in exantet:
            R.put((r, "NAGR", "BIOE", y), BT.p_primesResults_P_DATA(pd_(r, "NAGR", "BIOE", lst_expostt)))
    for r in ms:                                                             # l. 530-542
        for y in yearscur:
            R.put((r, "SECG", "BIOE", y), BT.p_primesResults_from_share(R.g(r, "MAPR", "BIOE", y),
                                                                        R.g(r, "BIOESHARE", "SECG", y)))
        for y in yearscur:
            R.put((r, "MAPR", "BIOE", y), BT.p_primesResults_MAPR_BIOE(R.g(r, "MAPR", "BIOE", y),
                                                                       R.g(r, "NAGR", "BIOE", y)))
        for y in yearscur:
            if R.nz(r, "MAPR", "BIOE", y):
                R.put((r, "BIOESHARE", "SECG", y), BT.p_primesResults_share(R.g(r, "SECG", "BIOE", y),
                                                                            R.g(r, "MAPR", "BIOE", y)))
        for y in yearscur:
            if R.nz(r, "MAPR", "BIOE", y):
                R.put((r, "BIOESHARE", "NAGR", y), BT.p_primesResults_share(R.g(r, "NAGR", "BIOE", y),
                                                                            R.g(r, "MAPR", "BIOE", y)))
    for r in ms:                                                             # l. 544-550 (on the values before it)
        old = {y: R.g(r, "BIOESHARE", "CERE", y) + R.g(r, "BIOESHARE", "SUGA", y) for y in yearscur}
        for pr in I.prows:
            if pr not in ("SUGA", "CERE"):
                continue
            for y in yearscur:
                den = old[y]
                if den:
                    R.put((r, "BIOESHARE", pr, y), BT.p_primesResults_bioeShare_stocks_MS(
                        R.g(r, "BIOESHARE", pr, y), den, R.g(r, "BIOESHARE", "SECG", y),
                        R.g(r, "BIOESHARE", "NAGR", y)))
    fill = [t for t in years if WOIL_FROM < t < BAS_PRIMES]                  # l. 560-569
    for r in msall:
        if not R.nz(r, "BIOF", "WOIL", BAS_PRIMES):
            continue
        for t in fill:
            R.put((r, "BIOF", "WOIL", t), BT.p_primesResults_WOIL_Fillyears(
                R.g(r, "BIOF", "WOIL", t), R.g(r, "BIOF", "WOIL", WOIL_FROM), R.g(r, "BIOF", "WOIL", BAS_PRIMES), t))
    for r in msall:                                                          # l. 574-575
        for y in yearscur:
            R.put((r, "BIOF", "VOIL", y), BT.p_primesResults_BIOF_VOIL(R.g(r, "BIOF", "VOIL", y),
                                                                       R.g(r, "BIOF", "WOIL", y)))
    for r in msall:                                                          # l. 585-589
        for y in yearscur:
            wo, vo = R.g(r, "BIOF", "WOIL", y), R.g(r, "BIOF", "VOIL", y)
            if wo + vo:
                R.put((r, "NAGR", "BIOD", y), BT.p_primesResults_NAGR_BIOD(R.g(r, "MAPR", "BIOD", y),
                                                                           R.g(r, "BIODSHARE", "SECG", y), wo, vo))
    for r in ms:                                                             # l. 591-592
        for y in yearscur:
            if R.nz(r, "MAPR", "BIOD", y):
                R.put((r, "BIODSHARE", "NAGR", y), BT.p_primesResults_share(R.g(r, "NAGR", "BIOD", y),
                                                                            R.g(r, "MAPR", "BIOD", y)))
    for r in msall:                                                          # l. 596-597
        for f in seco:
            for y in expostt:
                R.put((r, "INDM", f, y), BT.p_primesResults_P_DATA(pd_(r, "INDM", f, y)))
            for y in exantet:
                R.put((r, "INDM", f, y), BT.p_primesResults_P_DATA(pd_(r, "INDM", f, lst_expostt)))
    for r in msall:                                                          # l. 604-613
        for f in seco:
            for y in yearscur:
                R.put((r, "BIOF", f, y), BT.p_primesResults_copy(R.g(r, "DOMM", f, y)))
            for y in yearscur:
                R.put((r, "DOMM", f, y), BT.p_primesResults_DOMM_SECO_BIOF(R.g(r, "INDM", f, y), R.g(r, "BIOF", f, y)))
        for f in fos:
            for y in yearscur:
                R.put((r, "DOMM", f, y), BT.p_primesResults_copy(R.g(r, "HCOM", f, y)))
    for r in ms:                                                             # l. 641-658
        for y in yearscur:
            R.put((r, "SUGA", "BIOE", y), BT.p_primesResults_from_share(R.g(r, "MAPR", "BIOE", y),
                                                                        R.g(r, "BIOESHARE", "SUGA", y)))
        for y in yearscur:
            R.put((r, "CERE", "BIOE", y), BT.p_primesResults_CERE_BIOE(R.g(r, "MAPR", "BIOE", y),
                                                                       R.g(r, "SUGA", "BIOE", y),
                                                                       R.g(r, "SECG", "BIOE", y),
                                                                       R.g(r, "NAGR", "BIOE", y)))
    out.primes = dict(R)

    # --- the expert supports (l. 667 on)
    E = _P()
    T = _P()
    bio_cols = {"BIOF", "PRCB", "PRCBY"}                                     # frm_timesets.gms l. 60-61
    bio_rows = {"BIOD", "BIOE", "DISL", "GASL", "CRDO", "DDGS"}
    ce, re_ = set(s_colsest), set(s_rowsest)
    for (r, c, w, y), v in pdata.items():                                    # l. 667-669
        if r in msincl and y in expostt and c in ce and w in re_ and (w in bio_rows or c in bio_cols) and v:
            E.put((r, c, w, y), BT.p_expertSupprt_expostT(v))
    for r in msincl:                                                         # l. 677-695
        for f in seco:
            for y in exantet:
                E.put((r, "DOMM", f, y), BT.p_expertSupprt_PRIMES_change(
                    R.g(r, "DOMM", f, y), pd_(r, "DOMM", f, BAS_PRIMES), R.g(r, "DOMM", f, BAS_PRIMES)))
                E.put((r, "INDM", f, y), BT.P_expertSupprt_INDM(R.g(r, "INDM", f, y), E.g(r, "DOMM", f, y)))
                E.put((r, "BIOF", f, y), BT.p_expertSupprt_BIOF_SECO_BIOF(E.g(r, "DOMM", f, y), E.g(r, "INDM", f, y)))
                E.put((r, "MAPR", f, y), BT.p_expertSupprt_PRIMES_change(
                    R.g(r, "MAPR", f, y), pd_(r, "MAPR", f, BAS_PRIMES), R.g(r, "MAPR", f, BAS_PRIMES)))
    for r in msincl:                                                         # l. 810-844
        for f in seco:
            for y in exantet:
                E.put((r, "NTRD", f, y), BT.P_expertSupprt_NTRD(E.g(r, "MAPR", f, y), E.g(r, "BIOF", f, y),
                                                                E.g(r, "INDM", f, y)))
            E.put((r, "NTRD", f, BAS_PRIMES), BT.P_expertSupprt_NTRD_BASprimes(pd_(r, "EXPT", f, BAS_PRIMES),
                                                                               pd_(r, "IMPT", f, BAS_PRIMES)))
            n0 = E.g(r, "NTRD", f, BAS_PRIMES)
            for y in exantet:
                if E.g(r, "NTRD", f, y) >= n0:
                    E.put((r, "EXPT", f, y), BT.p_expertSupprt_trade_up(pd_(r, "EXPT", f, BAS_PRIMES),
                                                                        E.g(r, "NTRD", f, y), n0))
            for y in exantet:
                if E.g(r, "NTRD", f, y) >= n0:
                    E.put((r, "IMPT", f, y), BT.p_expertSupprt_trade_base(pd_(r, "IMPT", f, BAS_PRIMES)))
            for y in exantet:
                if E.g(r, "NTRD", f, y) < n0:
                    E.put((r, "IMPT", f, y), BT.p_expertSupprt_trade_down(pd_(r, "IMPT", f, BAS_PRIMES),
                                                                          E.g(r, "NTRD", f, y), n0))
            for y in exantet:
                if E.g(r, "NTRD", f, y) < n0:
                    E.put((r, "EXPT", f, y), BT.p_expertSupprt_trade_base(pd_(r, "EXPT", f, BAS_PRIMES)))
            E.put((r, "NTRD", f, BAS_PRIMES), BT.p_expertSupprt_NTRD_BASprimes_removed())
    for r in msincl:                                                         # l. 855-862
        for y in exantet:
            E.put((r, "SECG", "BIOD", y), BT.p_expertSupprt_SECG(E.g(r, "MAPR", "BIOD", y),
                                                                 R.g(r, "BIODSHARE", "SECG", y)))
            E.put((r, "SECG", "BIOE", y), BT.p_expertSupprt_SECG(E.g(r, "MAPR", "BIOE", y),
                                                                 R.g(r, "BIOESHARE", "SECG", y)))
    for r in msincl:                                                         # l. 867-879: new energy crops
        for y in exantet:
            if R.nz(r, "LIGN", "LEVL", y):
                E.put((r, "NECR", "LEVL", y), BT.p_expertSupprt_NECR_LEVL(step1.get((r, "TSET", "LEVL", y), 0.0),
                                                                          R.g(r, "LIGN", "LEVL", y)))
        if any(E.nz(r, "NECR", "LEVL", y) for y in exante):
            for y in exantet:
                if not E.nz(r, "NECR", "LEVL", y):
                    E.put((r, "NECR", "LEVL", y), BT.p_expertSupprt_NECR_LEVL_EPS(), eps=True)
    m_of = {n: [m for m in ms if (m, n) in mrr] for n in nt2est}
    for n in nt2est:                                                         # l. 883-889
        if n in ms_set:
            continue
        for y in exante:
            if not sum(basm.get((m, "UAAR", "LEVL"), 0.0) for m in m_of[n]):
                continue
            v = BT.p_expertSupprt_NECR_LEVL_NT2Est([(E.g(m, "NECR", "LEVL", y), basm[(m, "UAAR", "LEVL")])
                                                    for m in m_of[n] if basm.get((m, "UAAR", "LEVL"), 0.0)],
                                                   basm.get((n, "UAAR", "LEVL"), 0.0))
            eps = any(E.nz(m, "NECR", "LEVL", y) for m in m_of[n]) and basm.get((n, "UAAR", "LEVL"), 0.0) != 0.0
            E.put((n, "NECR", "LEVL", y), v, eps=eps)
    rest = list(dict.fromkeys(list(msincl) + [n for n in nt2est if n not in ms_set]))
    for r in rest:                                                           # l. 892-902
        for y in exante:
            if E.nz(r, "NECR", "LEVL", y):
                T.put((r, "NECR", "LEVL", y), BT.p_expertSupprt_NECR_LEVL_TrustLevl())
                E.put((r, "NECR", "OCRO", y), BT.p_expertSupprt_NECR_OCRO())
        if BT.P_DATA_nObs(any(E.nz(r, "NECR", "LEVL", y) for y in exante), False):
            out.nobs.update({(r, "NECR", "LEVL"), (r, "NECR", "OCRO")})
    for r in msincl:                                                         # l. 945-957
        for f, sh in (("BIOE", "BIOESHARE"), ("BIOD", "BIODSHARE")):
            for y in exantet:
                if R.nz(r, "NAGR", f, y):
                    E.put((r, "NAGR", f, y), BT.P_expertSupprt_NAGR(pd_(r, "NAGR", f, BAS_PRIMES), R.g(r, "NAGR", f, y),
                                                                    R.g(r, "NAGR", f, BAS_PRIMES),
                                                                    E.g(r, "MAPR", f, y), R.g(r, sh, "NAGR", y)))
    oilp = set(biostock_oilp)

    def yl(src, fuel, y):
        return bfyld.get((src, fuel, str(y)), 0.0)
    for r in msincl:                                                         # l. 986-996
        for s in biostock:
            for y in exante:
                if E.nz(r, "PRCB", s, y):
                    continue
                yields = [(yl(src, fuel, y), yl(src, fuel, BAS_PRIMES)) for src, fuel, stocks in PRCB_YIELDS
                          if s in stocks]
                if s in oilp:
                    yields.append((yl(*PRCB_YIELD_OILS, y), yl(*PRCB_YIELD_OILS, BAS_PRIMES)))
                E.put((r, "PRCB", s, y), BT.P_expertSupprt_PRCB([extr_rates.get((sf, s), 0.0) for sf in seco], yields))
            for y in exante:
                if not E.nz(r, "PRCBY", s, y):
                    E.put((r, "PRCBY", s, y), BT.P_expertSupprt_PRCBY([byproduct.get((b, s), 0.0) for b in bio_by]))
    has2020 = PRCB_FROM in exantet
    base_y = PRCB_FROM if has2020 else min(exante)
    for r in msincl:                                                         # l. 1001-1011
        for s in biostock:
            last = E.g(r, "PRCB", s, lst_dgagri)
            for y in exantet:
                if y > lst_dgagri and last:
                    E.put((r, "PRCB", s, y), BT.P_expertSupprt_PRCB_after_lst_dgagri(last, E.g(r, "PRCB", s, base_y), y,
                                                                                     lst_dgagri, base_y))
            for y in exantet:
                if y > lst_dgagri:
                    E.put((r, "PRCBY", s, y), BT.P_expertSupprt_PRCBY_after_lst_dgagri(E.g(r, "PRCBY", s, lst_dgagri)))
    # l. 1013-1283: feedstocks
    run_stock = [s for s in biostock if s not in ("SUGA", "TWIN")]
    for r in msincl:                                                         # l. 1073
        for y in exantet:
            E.put((r, "BIOF", "TWIN", y), BT.p_expertSupprt_BIOF_TWIN(pd_(r, "BIOF", "TWIN", BAS_PRIMES)))
    if any(E.nz(r, "BIOF", "SUGA", y) for r in msall for y in exantet):     # l. 1077-1103: KWS's supports
        raise NotImplementedError("biofuel trends: sugar supports from KWS (l. 1077-1103) are not ported: not "
                                  "reached in the reference run")
    for r in msincl:                                                         # l. 1109-1112
        for y in exantet:
            if E.nz(r, "PRCB", "SUGA", y):
                E.put((r, "BIOF", "SUGA", y), BT.p_expertSupprt_BIOF_SUGA(E.g(r, "BIOF", "SUGA", BAS_PRIMES),
                                                                          R.g(r, "SUGA", "BIOE", y),
                                                                          R.g(r, "SUGA", "BIOE", BAS_PRIMES),
                                                                          E.g(r, "PRCB", "SUGA", y)))
    agr = _P()
    share = _P()
    for rb in seco:                                                          # l. 1147-1220
        st = [s for s in run_stock if (s, rb) in set(s2f)]
        for r in msincl:
            for y in exantet:
                if E.nz(r, "MAPR", rb, y):
                    agr.put((r, rb, y), BT.p_agrFuel(E.g(r, "MAPR", rb, y), E.g(r, "SECG", rb, y),
                                                     E.g(r, "NAGR", rb, y), E.g(r, "BIOF", "SUGA", y),
                                                     E.g(r, "PRCB", "SUGA", y), E.g(r, "BIOF", "TWIN", y),
                                                     E.g(r, "PRCB", "TWIN", y), rb == "BIOE"))
        for r in msincl:
            for s in st:
                for y in expostt:
                    products = [pd_(r, "PRCB", s1, y) * pd_(r, "BIOF", s1, y) for s1 in st]
                    tot = sum(products)
                    own = pd_(r, "PRCB", s, y) * pd_(r, "BIOF", s, y)
                    if tot and own:
                        share.put((r, s, y), BT.p_stockShare_expostT(own, products))
            for s in st:
                if pd_(r, "PRCB", s, BAS_PRIMES):
                    for y in exantet:
                        share.put((r, s, y), BT.p_stockShare_exanteT(share.g(r, s, BAS_PRIMES)))
            for s in st:
                if (r, "DOMM", s) in nobs:
                    for y in exantet:
                        share.put((r, s, y), BT.p_stockShare_potential(share.g(r, s, y), I.potential.get((r, s), 0.0)))
            for y in exantet:
                share.put((r, rb, y), BT.p_stockShare_runBio([share.g(r, s, y) for s in st]))
            for s in st:
                for y in exantet:
                    if share.nz(r, rb, y) and share.nz(r, s, y):
                        share.put((r, s, y), BT.p_stockShare_normalised(share.g(r, s, y), share.g(r, rb, y)))
            for s in st:
                for y in exantet:
                    if E.nz(r, "PRCB", s, y):
                        E.put((r, "BIOF", s, y), BT.p_expertSupprt_BIOF_runStock(agr.g(r, rb, y), share.g(r, s, y),
                                                                                 E.g(r, "PRCB", s, y)))
    ddgs_src = [o for o, b in s2by if b == "DDGS"]
    for r in msincl:                                                         # l. 1224-1248: DDGS
        for y in exantet:
            if any(E.nz(r, "PRCBY", o, y) for o in ddgs_src):
                E.put((r, "MAPR", "DDGS", y), BT.p_expertSupprt_MAPR_DDGS([(E.g(r, "PRCBY", o, y), E.g(r, "BIOF", o, y))
                                                                           for o in ddgs_src]))
            mp, fp = E.g(r, "MAPR", "DDGS", y), basm.get((r, "GROF", "FPRO"), 0.0)
            if mp + fp:
                E.put((r, "FEDM", "DDGS", y), BT.p_expertSupprt_FEDM_DDGS(mp, fp))
            E.put((r, "DOMM", "DDGS", y), BT.p_expertSupprt_DOMM_DDGS(E.g(r, "FEDM", "DDGS", y)))
            if E.nz(r, "MAPR", "DDGS", y):
                E.put((r, "NTRD", "DDGS", y), BT.p_expertSupprt_NTRD_DDGS(E.g(r, "MAPR", "DDGS", y),
                                                                          E.g(r, "DOMM", "DDGS", y)))
            if E.nz(r, "FEDM", "DDGS", y):
                E.put((r, "IMPT", "DDGS", y), BT.p_expertSupprt_IMPT_DDGS(E.g(r, "MAPR", "DDGS", y)))
            E.put((r, "EXPT", "DDGS", y), BT.p_expertSupprt_EXPT_DDGS(E.g(r, "IMPT", "DDGS", y),
                                                                      E.g(r, "NTRD", "DDGS", y)))
    fuel_of: Dict[str, List[str]] = {}
    for s, f in s2f:
        fuel_of.setdefault(s, []).append(f)
    for r in msincl:                                                         # l. 1253-1264
        for s in biostock:
            for y in exantet:
                if E.g(r, "BIOF", s, y) < MIN_FEEDSTOCK:
                    E.put((r, "BIOF", s, y), BT.p_expertSupprt_BIOF_small())
            for y in exantet:
                if (not E.nz(r, "BIOF", s, y) and any(E.nz(r, "MAPR", f, y) for f in fuel_of.get(s, []))
                        and (pd_(r, "DOMM", s, BAS_PRIMES) or pd_(r, "BIOF", s, BAS_PRIMES)) and r in ms_set):
                    E.put((r, "BIOF", s, y), BT.p_expertSupprt_BIOF_tiny())
    for r in msincl:                                                         # l. 1271-1283
        for y in exante:
            E.put((r, "BIOF", "CERE", y), BT.P_expertSupprt_BIOF_CERE([E.g(r, "BIOF", c, y) for c in cere]))
        for s in biostock:
            for y in exante:
                mapr = any(E.nz(r, "MAPR", f, y) for f in fuel_of.get(s, []))
                if not E.nz(r, "BIOF", s, y) and E.nz(r, "PRCB", s, y) and r in ms_set:
                    E.put((r, "PRCB", s, y), BT.P_expertSupprt_PRCB_tiny(mapr))
            for y in exante:
                mapr = any(E.nz(r, "MAPR", f, y) for f in fuel_of.get(s, []))
                if not E.nz(r, "BIOF", s, y) and r in ms_set:
                    E.put((r, "PRCBY", s, y), BT.P_expertSupprt_PRCB_tiny(mapr))
    for r in msincl:                                                         # l. 1288-1293
        for y in exante:
            E.put((r, "MAPR", "BIOE", y), BT.P_expertSupprt_MAPR_BIOE([(E.g(r, "BIOF", s, y), E.g(r, "PRCB", s, y))
                                                                       for s, f in s2f if f == "BIOE"],
                                                                      E.g(r, "SECG", "BIOE", y),
                                                                      E.g(r, "NAGR", "BIOE", y)))
    if const_bio:                                                            # l. 1299-1318
        bal = set(balpos)
        eu = {m for m in msincl if ("EU028000", m) in mrr}

        def hold(c, w):
            return (c == "BIOF" or (c in bal and w in seco) or (c in CONST_BIO_COLS_SECO and w in seco)
                    or (c, w) == ("NECR", "LEVL") or (c in bal and w == "DDGS") or (c, w) == ("NTRD", "DDGS"))
        keys = {(r, c, w) for (r, c, w, y) in list(E) + list(E.eps) if r in eu and hold(c, w)}
        for r, c, w in sorted(keys):
            for y in exante:
                if y > CONST_BIO_AFTER:
                    E.put((r, c, w, y), BT.P_expertSupprt_constBioPos(E.g(r, c, w, CONST_BIO_AFTER)),
                          eps=(r, c, w, CONST_BIO_AFTER) in E.eps)
    for r in msincl:                                                         # l. 1325-1337
        for f in fos:
            for y in exante:
                E.put((r, "DOMM", f, y), BT.P_expertSupprt_fossil(R.g(r, "HCOM", f, y)))
                E.put((r, "HCOM", f, y), BT.P_expertSupprt_fossil(R.g(r, "HCOM", f, y)))
            for y in exantet:
                inha = pd_(r, "INHA", "LEVL", y)
                if inha:
                    E.put((r, "INHA", f, y), BT.p_expertSupprt_INHA_fossil(E.g(r, "HCOM", f, y), inha))
    tax = dict(I.tax)                                                        # l. 1344-1374
    for r in msincl:
        for f in seco:
            for y in expostt:
                if y > CTAX_BIO_LAST:
                    v = BT.p_taxData_CTAX_2005(tax.get((r, f, "CTAX", CTAX_BIO_LAST), 0.0))
                    if v:
                        tax[(r, f, "CTAX", y)] = v
                    else:
                        tax.pop((r, f, "CTAX", y), None)
            for y in expostt:
                v = tax.get((r, f, "CTAX", y), 0.0)
                if v:
                    tax[(r, f, "CTAX", y)] = BT.p_taxData_CTAX_per_t(v, oilequ[f], density[f])
    ycur = set(yearscur)

    def any_dom(r, f):
        return any(E.nz(r, "DOMM", f, y) for y in ycur)
    for r in msincl:
        for f in seco:
            if any_dom(r, f):
                for y in exante:
                    E.put((r, "CTAX", f, y), BT.P_expertSupprt_CTAX_SECO_BIOF(tax.get((r, f, "CTAX", y), 0.0),
                                                                              tax.get((r, f, "CTAX", BAS_PRIMES), 0.0),
                                                                              y in set(expostt)))
        for f in fos:                                                        # l. 1364-1374
            if any_dom(r, f) and not any(E.nz(r, "CTAX", f, y) for y in ycur):
                for y in expostt:
                    E.put((r, "CTAX", f, y), BT.P_expertSupprt_CTAX_fossil_expostT(R.g(r, "CTAX", f, y)))
            if any_dom(r, f):
                b = R.g(r, "CTAX", f, BAS_PRIMES)
                for y in exantet:
                    E.put((r, "CTAX", f, y), BT.P_expertSupprt_CTAX_fossil_exanteT(E.g(r, "CTAX", f, BAS_PRIMES),
                                                                                   R.g(r, "CTAX", f, y), b))
    fmap: Dict[str, List[str]] = {}
    for f, a in I.fuel_map:
        fmap.setdefault(f, []).append(a)
    ag = lambda col, a, y: aglink.get((AG_EU_TOT, col, a, str(y)), 0.0)    # noqa: E731
    P = dict(pdata)
    for r in msincl:                                                         # l. 1380-1391: p_data's fuel prices
        for f in fuels:
            if not P.get((r, "UVAG", f, basy), 0.0):
                v = BT.P_result_UVAG_basy([ag("PP", a, basy) for a in fmap.get(f, [])])
                if v:
                    P[(r, "UVAG", f, basy)] = v
                    out.pdata[(r, "UVAG", f, basy)] = v
            base = sum(ag("PP", a, basy) for a in fmap.get(f, []))
            for y in expostt:
                if not P.get((r, "UVAG", f, y), 0.0) and base and y > basy:
                    v = BT.P_result_UVAG_expostT(P.get((r, "UVAG", f, basy), 0.0),
                                                 [ag("PP", a, y) for a in fmap.get(f, [])], base)
                    if v:
                        P[(r, "UVAG", f, y)] = v
                        out.pdata[(r, "UVAG", f, y)] = v
            for y in expostt:
                if not E.nz(r, "UVAG", f, y):
                    E.put((r, "UVAG", f, y), BT.P_expertSupprt_UVAG_expostT(P.get((r, "UVAG", f, y), 0.0)))
    match: Dict[str, List[str]] = {}
    for f, ff in I.fuel_match:
        match.setdefault(f, []).append(ff)
    for r in msincl:                                                         # l. 1395-1407
        for f in fuels:
            own = sum(R.g(r, "UVAP", ff, BAS_PRIMES) for ff in match.get(f, []))
            eu = sum(R.g("EU028000", "UVAP", ff, BAS_PRIMES) for ff in match.get(f, []))
            for y in exante:
                if y in set(expostt) or not (own or eu):
                    continue
                src = r if own else "EU028000"
                E.put((r, "UVAG", f, y), BT.P_expertSupprt_UVAG_EXANTE(
                    E.g(r, "UVAG", f, BAS_PRIMES), [(R.g(src, "UVAP", ff, y), R.g(src, "UVAP", ff, BAS_PRIMES))
                                                    for ff in match.get(f, []) if R.g(src, "UVAP", ff, BAS_PRIMES)]))
        for f in fuels:                                                      # l. 1410-1411
            if any_dom(r, f):
                for y in exante:
                    E.put((r, "UVAD", f, y), BT.P_expertSupprt_UVAD(E.g(r, "UVAG", f, y), E.g(r, "CTAX", f, y)))
        for f in fuels:                                                      # l. 1415-1416
            for c in ("UVAG", "UVAD", "CTAX"):
                for y in yearscur:
                    if E.nz(r, c, f, y):
                        E.put((r, c, f, y), BT.P_expertSupprt_per_ton(E.g(r, c, f, y), oilequ[f]))
        for f in fuels:                                                      # l. 1421-1423
            for y in exante:
                if E.nz(r, "UVAD", f, y) and E.nz(r, "INHA", f, y):
                    E.put((r, "EXPD", f, y), BT.p_expertSupprt_EXPD(E.g(r, "UVAD", f, y), E.g(r, "INHA", f, y)))
    cols_seen = {k[1] for k in list(E) + list(E.eps)}
    for r in msincl:                                                         # l. 1428-1459: trust levels
        for y in exante:
            for c in cols_seen:
                for f in seco:
                    if E.nz(r, c, f, y):
                        T.put((r, c, f, y), BT.P_expertSupprt_TrustLevl_7())
            for f in seco:
                for c in ("IMPT", "EXPT"):
                    if E.nz(r, c, f, y):
                        T.put((r, c, f, y), BT.P_expertSupprt_TrustLevl_1())
            for c in cols_seen:
                for f in fos:
                    if E.nz(r, c, f, y):
                        T.put((r, c, f, y), BT.P_expertSupprt_TrustLevl_7())
            for s in biostock:
                if E.nz(r, "BIOF", s, y):
                    T.put((r, "BIOF", s, y), BT.P_expertSupprt_TrustLevl_7())
            if E.nz(r, "BIOF", "CERE", y):
                T.put((r, "BIOF", "CERE", y), BT.P_expertSupprt_TrustLevl_7())
            for s in biostock:
                if E.nz(r, "BIOF", s, y):
                    T.put((r, "PRCB", s, y), BT.P_expertSupprt_TrustLevl_7())
                    T.put((r, "PRCBY", s, y), BT.P_expertSupprt_TrustLevl_7())
            for f in fuels:
                if E.nz(r, "UVAD", f, y) and E.nz(r, "INHA", f, y) and E.nz(r, "EXPD", f, y):
                    T.put((r, "EXPD", f, y), BT.P_expertSupprt_TrustLevl_1())
            for c in ("FEDM", "DOMM", "MAPR", "EXPT", "IMPT"):
                if E.nz(r, c, "DDGS", y):
                    T.put((r, c, "DDGS", y), BT.p_expertSupprt_TrustLevl_DDGS())
            if E.nz(r, "NTRD", "DDGS", y) and E.nz(r, "EXPT", "DDGS", y):
                T.put((r, "NTRD", "DDGS", y), BT.p_expertSupprt_NTRD_DDGS_TrustLevl(
                    T.g(r, "EXPT", "DDGS", y), E.g(r, "NTRD", "DDGS", y), E.g(r, "EXPT", "DDGS", y)))
    ex = set(exante)
    for (r, c, w, y) in list(E) + list(E.eps):                               # l. 1464-1483: nObs
        if y in ex and r in set(msincl) and (w in set(seco) or w == "DDGS" or w in set(fuels)
                                             or (c in ("BIOF", "PRCB", "PRCBY") and w in set(biostock))
                                             or (c, w) == ("BIOF", "CERE")):
            if c in ("PRCB", "PRCBY") and not any(E.nz(r, "BIOF", w, z) for z in ex):
                continue
            if BT.P_DATA_nObs(True, (r, c, w) in nobs):
                out.nobs.add((r, c, w))
    keys = set(E) | E.eps | set(T)
    out.expert = {k: (E.g(*k), T.g(*k)) for k in keys}
    out.eps = set(E.eps)
    return out
