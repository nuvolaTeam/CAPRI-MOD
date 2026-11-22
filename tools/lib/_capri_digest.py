"""The fibre (NDF) and fat shares of a cattle activity's ration as CAPRI computes them for 3-NOP (KNOWN_ISSUES K93).

CAPRI's envind/digestibility.gms (the standard path, GHGLCA off), per regional unit ru and cattle activity:

  1. the feeds' composition: CAPRI's table p_digestPar("EU", "DCOL", product, item) (envind/def_digestibility.gms,
     capri_data/sources/intermediate/envind/capri_digestpar.parquet), missing items filled from the default products DEF_PRD (l. 37);
  2. grass: by the activity's grazing share GRAZ (p_NEMIDAT TypeShare, envind/ammo.gms l. 604-613) and the member
     state's grass N-fixation rate (fert/fertpar.gms p_nfixRate_gras, default 0.05, at most 0.75), pasture (GRPS,
     LGPS) or half silage (GRSI, LGSI), half hay (GRHA, LGHA), grass or legumes (l. 43-54); other fodder (OFAR) the
     grass mixed with legume silage and hay by the region's legume share FLEG (l. 56-58);
  3. FAT = EE - 1 where EE >= 1 (l. 60);
  4. CAPRI's own data where they agree with the table: NDF from the region's FIDI and CP from its CRPR, both per dry
     matter (x 100), kept only if both lie within max(20%, 5 points) of the table and the shares add to at most 100
     with FIDI above NDICP (l. 64-94); NDF at least NDICP + 0.1 (l. 99-100);
  5. the feed bulks (FCER, FPRO, ...): their products' NDF and FAT weighted by the member state's feed use (FEDM +
     INTF) times dry matter (l. 230-262; FEED_TO_O of sets.gms).

3-NOP's effect (envind/line_nitr.gms l. 124-134) then takes, per member state, the ration's NDF and FAT over its
regional units ru: sum_{feed, ru} x data(ru, act, feed) DRMA(ru, feed) / sum_{feed, ru} data(ru, act, feed)
DRMA(ru, feed), the rations per head summed over the units as CAPRI writes it (not weighted by herd size).
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / "capri_data" / "sources" / "intermediate" / "envind"
#: fert/fertpar.gms's statements, converted to CSV by tools/build/convert_sources.py
FERTPAR = ROOT / "capri_data" / "sources" / "raw" / "capri" / "gams" / "fert"
_ROW = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'Y'\s+(\S+)")


def _num(s):
    s = s.rstrip(",").strip()
    return 0.0 if s.lower() in ("eps", "na", "undf", "") else float(s)


def _csv(path):
    if str(path).endswith(".parquet"):                 # a table of capri_data/sources
        from _sources_io import source_records
        return source_records(path)
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def table():
    """CAPRI's p_digestPar("EU", "DCOL", ...) with the DEF_PRD fill (digestibility.gms l. 37)."""
    t = defaultdict(dict)
    for r in _csv(ENV / "capri_digestpar.parquet"):
        t[r["feed"]][r["item"]] = float(r["value"])
    base = {k: dict(v) for k, v in t.items()}
    for r in _csv(ENV / "capri_digest_default_prd.parquet"):
        for item, v in base.get(r["default"], {}).items():
            if not t[r["feed"]].get(item):
                t[r["feed"]][item] = v
    return t


def nfix_rates():
    """fert/fertpar.gms p_nfixRate_gras per member state; missing: p_nitrFact RALL GRAE BioFix (fertpar.gms l. 295)
    (fertpar_p_nfixRate_gras.parquet, fertpar_p_nitrFact_RALL_GRAE_BioFix.parquet)."""
    rates = {r["region"]: float(r["value"]) for r in _csv(FERTPAR / "fertpar_p_nfixRate_gras.parquet")}
    g = _csv(FERTPAR / "fertpar_p_nitrFact_RALL_GRAE_BioFix.parquet")
    return rates, float(g[0]["value"])


def read_dump(path, regions):
    """DATA(r, row, col, "Y") of a CAPREG text dump for the regions given."""
    out = {}
    for line in open(path, errors="ignore"):
        m = _ROW.match(line)
        if m and m.group(1) in regions:
            out[(m.group(1), m.group(2), m.group(3))] = _num(m.group(4))
    return out


def row_comp(T: dict, D: dict, ms: str, ru: str, GRAZ: float, nfix: float) -> dict:
    """digestPar(ru, act, row, item) of the products, steps 1-4 (digestibility.gms l. 41-100), for an activity with
    grazing share GRAZ; nfix the member state's rate after l. 44-45 (equations/digestibility.py
    p_nfixRate_gras_digest). The statements of l. 31-60: capri_mod/supply/equations/digestibility.py."""
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from capri_mod.supply.equations.digestibility import (
        p_DryMatterContent, p_digestPar_GRAS, p_digestPar_OFAR, p_digestPar_FAT)
    P = {row: dict(v) for row, v in T.items()}
    P["GRAS"] = {it: p_digestPar_GRAS(GRAZ, nfix, *(T[r].get(it, 0.0) for r in ("GRPS", "LGPS", "GRSI", "LGSI", "GRHA",
                                                                                "LGHA")))
                 for it in set(T["GRPS"]) | set(T["GRSI"]) | set(T["GRHA"])}
    gras = P["GRAS"]
    fleg = D.get((ru, "FLEG", "LEVL"), 0.0)
    if fleg:
        P["OFAR"] = {it: p_digestPar_OFAR(gras.get(it, 0.0), T["LGSI"].get(it, 0.0), T["LGHA"].get(it, 0.0), fleg)
                     for it in set(gras) | set(T["LGSI"]) | set(T["LGHA"])}
    for row, p in P.items():
        if p.get("EE", 0.0) >= 1:
            p["FAT"] = p_digestPar_FAT(p["EE"], p.get("FAT"))
        d_ = p_DryMatterContent(D.get((ru, "DRMA", row)), D.get((ms, "DRMA", row), 0.0))
        fidi, crpr = D.get((ru, "FIDI", row), 0.0), D.get((ru, "CRPR", row), 0.0)
        nf = fidi / d_ * 100 if (d_ and fidi) else 0.0
        nc = crpr / d_ * 100 if (d_ and crpr) else 0.0
        ndf, cp = p.get("NDF", 0.0), p.get("CP", 0.0)
        out = (nf > ndf + max(ndf * 0.2, 5) or nf < ndf - max(ndf * 0.2, 5)
               or nc > cp + max(cp * 0.2, 5) or nc < cp - max(cp * 0.2, 5))
        if out:
            nf = nc = 0.0
        tot = nc + nf + p.get("FAT", 0.0) + p.get("ASH", 0.0) + p.get("NDICP", 0.0)
        ok = tot <= 100 and nf > p.get("NDICP", 0.0)
        if nc and ok:
            p["CP"] = nc
        if nf and ok:
            p["NDF"] = nf
        if p.get("CAT"):
            p["NDF"] = max(p.get("NDF", 0.0), p.get("NDICP", 0.0) + 0.1)
    return P


def bulk_values(P: dict, D: dict, ms: str, ru: str, rows: list, items) -> dict:
    """{item: digestPar(ru, act, FEED, item)} of a feed bulk with the products `rows` (step 5, digestibility.gms
    l. 200-232: equations/digestibility.py p_digestPar_shFEED, p_digestPar_FEED)."""
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from capri_mod.supply.equations.digestibility import p_DryMatterContent, p_digestPar_shFEED, p_digestPar_FEED
    w = {r: (D.get((ms, "FEDM", r), 0.0) + D.get((ms, "INTF", r), 0.0))
         * p_DryMatterContent(D.get((ru, "DRMA", r)), D.get((ms, "DRMA", r), 0.0)) for r in rows}
    W = sum(w.values())
    sh = [p_digestPar_shFEED(w[r], W) for r in rows]
    return {it: p_digestPar_FEED([P.get(r, {}).get(it, 0.0) for r in rows], sh) for it in items}


def ration_ndf_fat(dump: Path, ms: str, rus, feed_to_o, catacts, graz) -> dict:
    """{catact: (NDF %, FAT %)} of the member state's ration (line_nitr.gms l. 124-134); graz(catact) -> GRAZ."""
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from capri_mod.supply.equations.digestibility import p_DryMatterContent, p_nfixRate_gras_digest
    T = table()
    rates, default_fix = nfix_rates()
    nfix = p_nfixRate_gras_digest(rates.get(ms, default_fix))
    D = read_dump(dump, set(rus) | {ms})
    rows_of = defaultdict(list)
    for f, r in feed_to_o:
        rows_of[f].append(r)

    res = {}
    for act in catacts:
        num_n = num_f = den = 0.0
        for ru in rus:
            P = row_comp(T, D, ms, ru, graz(act), nfix)
            for feed, rows in rows_of.items():
                q = D.get((ru, act, feed), 0.0)
                if not q:
                    continue
                b = bulk_values(P, D, ms, ru, rows, ("NDF", "FAT"))
                x = q * p_DryMatterContent(D.get((ru, "DRMA", feed)), D.get((ms, "DRMA", feed), 0.0))
                num_n += b["NDF"] * x
                num_f += b["FAT"] * x
                den += x
        if den > 0:
            res[act] = (num_n / den, num_f / den)
    return res


def feed_ee(D: dict, ms: str, rus, feed_to_o, graz_of: dict) -> dict:
    """{(ru, key): {FEED: (EE %, dry-matter content)}} of the feed bulks per regional unit and grazing class, the ether
    extract of digestibility.gms l. 223-225 (steps 1-5) and p_DryMatterContent(ru, FEED) (l. 31-33), from the data D
    {(region, row, col): value} of the year digestibility.gms runs with: the inputs of the feed bulks' fat,
    line_nitr.gms l. 175-176 (equations/line_nitr.py p_emisFeed_TotFAT_FEED). graz_of {key: GRAZ}: the bulks differ
    between activities only by the grazing share (GRAS, and OFAR through it)."""
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from capri_mod.supply.equations.digestibility import p_DryMatterContent, p_nfixRate_gras_digest
    T = table()
    rates, default_fix = nfix_rates()
    nfix = p_nfixRate_gras_digest(rates.get(ms, default_fix))
    rows_of = defaultdict(list)
    for f, r in feed_to_o:
        rows_of[f].append(r)
    out = {}
    for ru in rus:
        for key, g in graz_of.items():
            P = row_comp(T, D, ms, ru, g, nfix)
            out[(ru, key)] = {feed: (bulk_values(P, D, ms, ru, rows, ("EE",))["EE"],
                                     p_DryMatterContent(D.get((ru, "DRMA", feed)), D.get((ms, "DRMA", feed), 0.0)))
                              for feed, rows in rows_of.items()}
    return out


def nop_ch4_rel(ndf: float, fat: float, shr_of_dm: float = 0.0009) -> float:
    """3-NOP's relative change of enteric CH4 per head adopting (line_nitr.gms l. 125-134; p_mitiEffFac 1)."""
    return -(32.36 + 0.282 * (shr_of_dm * 100000 - 70.5) - 0.915 * (ndf - 32.9) - 3.08 * (fat - 4.2)) / 100
