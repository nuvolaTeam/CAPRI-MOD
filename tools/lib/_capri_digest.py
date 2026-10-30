"""The fibre (NDF) and fat shares of a cattle activity's ration as CAPRI computes them for 3-NOP (KNOWN_ISSUES K93).

CAPRI's envind/digestibility.gms (the standard path, GHGLCA off), per regional unit ru and cattle activity:

  1. the feeds' composition: CAPRI's table p_digestPar("EU", "DCOL", product, item) (envind/def_digestibility.gms,
     capri_data/sources/envind/capri_digestpar.csv), missing items filled from the default products DEF_PRD (l. 37);
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
ENV = ROOT / "capri_data" / "sources" / "envind"
#: fert/fertpar.gms's statements, converted to CSV by tools/build/convert_sources_to_csv.py
FERTPAR = ROOT / "capri_data" / "sources" / "capri_gams" / "fert"
_ROW = re.compile(r"^'([^']*)'\.'([^']*)'\.'([^']*)'\.'Y'\s+(\S+)")


def _num(s):
    s = s.rstrip(",").strip()
    return 0.0 if s.lower() in ("eps", "na", "undf", "") else float(s)


def _csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def table():
    """CAPRI's p_digestPar("EU", "DCOL", ...) with the DEF_PRD fill (digestibility.gms l. 37)."""
    t = defaultdict(dict)
    for r in _csv(ENV / "capri_digestpar.csv"):
        t[r["feed"]][r["item"]] = float(r["value"])
    base = {k: dict(v) for k, v in t.items()}
    for r in _csv(ENV / "capri_digest_default_prd.csv"):
        for item, v in base.get(r["default"], {}).items():
            if not t[r["feed"]].get(item):
                t[r["feed"]][item] = v
    return t


def nfix_rates():
    """fert/fertpar.gms p_nfixRate_gras per member state; missing: p_nitrFact RALL GRAE BioFix (fertpar.gms l. 295)
    (fertpar_p_nfixRate_gras.csv, fertpar_p_nitrFact_RALL_GRAE_BioFix.csv)."""
    rates = {r["region"]: float(r["value"]) for r in _csv(FERTPAR / "fertpar_p_nfixRate_gras.csv")}
    g = _csv(FERTPAR / "fertpar_p_nitrFact_RALL_GRAE_BioFix.csv")
    return rates, float(g[0]["value"])


def read_dump(path, regions):
    """DATA(r, row, col, "Y") of a CAPREG text dump for the regions given."""
    out = {}
    for line in open(path, errors="ignore"):
        m = _ROW.match(line)
        if m and m.group(1) in regions:
            out[(m.group(1), m.group(2), m.group(3))] = _num(m.group(4))
    return out


def ration_ndf_fat(dump: Path, ms: str, rus, feed_to_o, catacts, graz) -> dict:
    """{catact: (NDF %, FAT %)} of the member state's ration (line_nitr.gms l. 124-134); graz(catact) -> GRAZ."""
    T = table()
    rates, default_fix = nfix_rates()
    nfix = min(rates.get(ms, default_fix) or 0.05, 0.75)
    D = read_dump(dump, set(rus) | {ms})
    rows_of = defaultdict(list)
    for f, r in feed_to_o:
        rows_of[f].append(r)

    def dm(ru, row):
        return D.get((ru, "DRMA", row)) or D.get((ms, "DRMA", row), 0.0)

    def use(row):
        return D.get((ms, "FEDM", row), 0.0) + D.get((ms, "INTF", row), 0.0)

    def comp(ru, act):
        """digestPar(ru, act, row, item) for NDF, FAT (and what step 4 needs), steps 1-4."""
        g = graz(act)
        mix = lambda a, b: (1 - nfix / 0.75) * T[a].get(it, 0.0) + nfix / 0.75 * T[b].get(it, 0.0)
        P = {row: dict(v) for row, v in T.items()}
        gras = {}
        for it in set(T["GRPS"]) | set(T["GRSI"]) | set(T["GRHA"]):
            gras[it] = g * mix("GRPS", "LGPS") + (1 - g) * (mix("GRSI", "LGSI") * 0.5 + mix("GRHA", "LGHA") * 0.5)
        P["GRAS"] = gras
        fleg = D.get((ru, "FLEG", "LEVL"), 0.0)
        if fleg:
            P["OFAR"] = {it: gras.get(it, 0.0) * (1 - fleg)
                         + (0.5 * T["LGSI"].get(it, 0.0) + 0.5 * T["LGHA"].get(it, 0.0)) * fleg
                         for it in set(gras) | set(T["LGSI"]) | set(T["LGHA"])}
        for row, p in P.items():
            if p.get("EE", 0.0) >= 1:
                p["FAT"] = p["EE"] - 1
            d_ = dm(ru, row)
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

    res = {}
    for act in catacts:
        num_n = num_f = den = 0.0
        for ru in rus:
            P = comp(ru, act)
            for feed, rows in rows_of.items():
                q = D.get((ru, act, feed), 0.0)
                if not q:
                    continue
                w = {r: use(r) * dm(ru, r) for r in rows}
                W = sum(w.values())
                ndf = sum(P.get(r, {}).get("NDF", 0.0) * w[r] / W for r in rows) if W else 0.0
                fat = sum(P.get(r, {}).get("FAT", 0.0) * w[r] / W for r in rows) if W else 0.0
                x = q * dm(ru, feed)
                num_n += ndf * x
                num_f += fat * x
                den += x
        if den > 0:
            res[act] = (num_n / den, num_f / den)
    return res


def nop_ch4_rel(ndf: float, fat: float, shr_of_dm: float = 0.0009) -> float:
    """3-NOP's relative change of enteric CH4 per head adopting (line_nitr.gms l. 125-134; p_mitiEffFac 1)."""
    return -(32.36 + 0.282 * (shr_of_dm * 100000 - 70.5) - 0.915 * (ndf - 32.9) - 3.08 * (fat - 4.2)) / 100
