"""Inputs of CAPRI's feed-based cattle enteric CH4 (GWPCH4ENT_, envind/gases.gms l. 365-376).

p_emisFeed(r, act, feed, CH4ENT) = Ym / 55.65 x GE x 4.1868 x DM content      [kg CH4 per kg fresh feed]

This builder writes GE (Mcal per kg DM) per country, cattle type and feed group, and Ym per animal;
the model applies each ration's own DM content.

GE per feedstuff (envind/digestibility.gms l. ~134, NRC):
    CP/100 x 5.6 + FAT/100 x 9.4 + (100 - CP - FAT - ASH)/100 x 4.2,  FAT = EE - 1 (EE >= 1)
    composition: TABLE p_digestPar in envind/def_digestibility.gms (NRC 2001, INRA 2002)
Grass (digestibility.gms l. ~30-40): grazing share x pasture + (1 - grazing) x (1/2 silage + 1/2 hay),
    each mixed with its legume variant by n/0.75 (N-fixation rate n; CAPRI default 0.05 - REGISTERED:
    default used, regional rates not in the project); grazing share from MITERRA RCEmissions as in
    the ammonia step.
Feed groups (FEED_TO_O, sets.gms l. 5622): GE averaged over feedstuffs weighted by national
    feed use (FEDM + INTF) x DM (digestibility.gms l. 205-225); capreg dumps res_17XX.txt.
Ym: TABLE EMISCALC0 in envind/create_rawdat_gascoeff_gdx.gms (IPCC 2006), EU000000 rows.
Usage: python tools/build_enteric_feed_factors.py <CAPRI gams folder> <capreg dump folder>
"""
import csv, glob, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "capri_data" / "2017" / "environment"
FEED_TO_O = {
    "FCER": "SWHE DWHE RYEM BARL OATS MAIZ OCER PARI RICE",
    "FPRO": "PULS RAPO SUNO SOYO OLIO OTHO RAPC SUNC SOYC OLIC OTHC DDGS FPRI SFIS FFIS OAQU",
    "FOTH": "POTA RAPE SUNF SOYA OLIV OOIL TEXT TOMA OVEG APPL OFRU CITR TAGR TABO TWIN SUGA EGGS PORK BEEF",
    "FMIL": "SMIP WMIP BUTT CREM COCM CHES FRMI",
    "FENE": "MOLA STAR FENI",
    "FMAI": "MAIF", "FSTR": "STRA", "FOFA": "OFAR", "FROO": "ROOF",
}
CATTLE = {"DCOW": "DAICOW_S", "BCOW": "OCOW_S", "BULL": "OCOW_S", "HFRS": "OCOW_S", "CALV": "OCOW_S"}
YM_MAP = {"DCOW": ("DCOW", "DCOL", "DCOH"), "BCOW": ("SCOW",), "CALV": ("CAFR", "CAMR", "CAFF", "CAMF"),
          "BULL": ("BULF", "BULL", "BULH"), "HFRS": ("HEIF", "HEIL", "HEIH", "HEIR")}
NFIX = 0.05


def _table(path, name):
    """Positional GAMS table -> {row_key: {col: value}}. The key is everything before the
    first number (spaces and quotes removed); each number goes to the header column whose
    right edge is closest to the number's right edge (GAMS right-justified tables)."""
    lines = Path(path).read_text(encoding="latin-1").replace("\r", "").split("\n")
    i = next(k for k, l in enumerate(lines) if re.match(rf"\s*TABLE\s+{name}\b", l, re.I))
    hdr_i = next(k for k in range(i + 1, len(lines)) if lines[k].strip() and not lines[k].lstrip().startswith("*"))
    cols = [(m.end(), m.group()) for m in re.finditer(r"\S+", lines[hdr_i])]
    num = re.compile(r"(?<![\w.])[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?(?![\w.])")
    out = {}
    for l in lines[hdr_i + 1:]:
        st = l.strip()
        if st.startswith(";"):
            break
        if not st or st.startswith("*") or st.startswith("$"):
            continue
        ms = [m for m in num.finditer(l) if m.start() >= cols[0][0] - len(cols[0][1]) - 6]
        key_end = ms[0].start() if ms else len(l)
        key = re.sub(r"\s+", "", l[:key_end]).replace('"', "").replace("'", "")
        vals = {}
        for m in ms:
            c = min(cols, key=lambda cc: abs(cc[0] - m.end()))
            vals[c[1]] = float(m.group())
        if key:
            out[key] = vals
        if st.endswith(";"):
            break
    return out


def main(gams, dumps):
    nrc = _table(Path(gams) / "envind" / "def_digestibility.gms", "p_digestPar")
    comp = {k.split(".")[-1]: v for k, v in nrc.items() if k.startswith("EU.DCOL.") and v}

    def ge(row):
        v = comp.get(row)
        if not v or "CP" not in v:
            return None
        ee = v.get("EE", 0.0); fat = ee - 1.0 if ee >= 1.0 else 0.0
        cp, ash = v.get("CP", 0.0), v.get("ASH", 0.0)
        return cp / 100 * 5.6 + fat / 100 * 9.4 + (100 - cp - fat - ash) / 100 * 4.2
    ems = _table(Path(gams) / "envind" / "create_rawdat_gascoeff_gdx.gms", "EMISCALC0")
    ym = {}
    for a, srcs in YM_MAP.items():
        vals = [v.get("YM") for k, v in ems.items() if k.startswith("EU000000.") and k.split(".")[1] in srcs and v.get("YM")]
        if vals:
            ym[a] = sum(vals) / len(vals)
    rce = {}
    for r in csv.DictReader(open(ROOT / "capri_data" / "2017" / "abatement" / "ammonia" / "RCEmissions.csv")):
        rce[(r["region"], r["animal_mitt"], r["item"])] = float(r["value"])
    rows = []
    for f in sorted(glob.glob(str(Path(dumps) / "res_17*.txt"))):
        txt = open(f, encoding="latin-1").read()
        use = {}
        for m in re.finditer(r"'(\w{2}000000)'\.'(FEDM|INTF)'\.'(\w+)'\.'Y'\s+([-+0-9.eE]+)", txt):
            use[m.group(3)] = use.get(m.group(3), 0.0) + float(m.group(4))
        ctrys = set(re.findall(r"'(\w{2}000000)'\.'(?:FEDM|INTF)'", txt))
        for ctry in ctrys:
            for a, cat in CATTLE.items():
                hd, et = rce.get((ctry, cat, "HD")), rce.get((ctry, cat, "Et"), 0.0)
                graz = max(0.0, (1 - hd / 365.0) * (1 - (et or 0.0) / 100)) if hd is not None else 0.0
                w = NFIX / 0.75
                mix = lambda g, l: (1 - w) * (ge(g) or 0) + w * (ge(l) or ge(g) or 0)
                ge_gras = graz * mix("GRPS", "LGPS") + (1 - graz) * (0.5 * mix("GRSI", "LGSI") + 0.5 * mix("GRHA", "LGHA"))
                rows.append([ctry, a, "FGRA", round(ge_gras, 5), ym.get(a, ""), round(graz, 4)])
                for grp, members in FEED_TO_O.items():
                    num = den = 0.0
                    for rw in members.split():
                        g = ge(rw)
                        if g is None:
                            continue
                        dmc = comp[rw].get("DM", 100.0) / 100.0
                        wt = use.get(rw, 0.0) * dmc
                        num += wt * g; den += wt
                    if den <= 0:            # no national use recorded: simple mean (REGISTERED)
                        gs = [ge(rw) for rw in members.split() if ge(rw) is not None]
                        if not gs:
                            continue
                        val = sum(gs) / len(gs)
                    else:
                        val = num / den
                    rows.append([ctry, a, grp, round(val, 5), ym.get(a, ""), round(graz, 4)])
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "enteric_feed_factors.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["country", "animal", "feed", "ge_mcal_per_kg_dm", "ym", "grazing_share"]); w.writerows(rows)
    return comp, ym, rows


if __name__ == "__main__":
    comp, ym, rows = main(sys.argv[1], sys.argv[2])
    print(f"feedstuffs with composition: {len(comp)} | Ym: {ym} | rows: {len(rows)}")
