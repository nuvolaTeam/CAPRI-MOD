"""Extract CAPRI's per-activity marginal decomposition and 2030 unit values from a scenario result.

Source: a CAPRI result file res_2_1730<scenario>.gdx (dataOut), dumped to text with gdxdump
(lines 'REGION'.'ACT'.'ITEM'.'2030' value, or the five-index form 'REGION'.'CUR'.'ACT'.'ITEM'.'2030').
CAPRI computes the decomposition in reports/margcr.gms: for every activity the marginal revenue and
cost terms (shadow values) that sum to zero at an interior optimum (D_PROV = their sum):
  D_O      outputs at their shadow prices (SUPBAL_.M)       D_FEED  feed at feed-balance shadow values
  D_YANI   young animals bought/sold (INPANI_.M)            D_NUTNED value of nutrient need (crops, <0)
                                                                     or of manure nutrients (animals, >0)
  D_OBJC   fixed accounting costs (p_linObjeCont)           D_PREM  premiums
  D_PMPL   PMP terms -(p_pmpCnst + quadratic at levels)     D_PMPF  feed PMP terms
  D_AREA   land shadow price                                D_CRPR/D_ENNE requirement duals (not in D_PROV)
Written: capri_data/validation/greendeal_2030/capri_marginal_terms_<tag>_2030.csv.xz (region, activity, item, value;
         the max file is kept to LEVL, MANN, MREV, D_O, D_FEED, D_NUTNED, D_PMPL, D_PMPF, D_PROV for size)
         capri_data/validation/greendeal_2030/capri_unit_values_<tag>_2030.csv (member state, product, UVAG 2030)

    python tools/extract_capri_marginal_terms.py <dump.csv> <tag>
"""
from __future__ import annotations
import csv, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS = {"LEVL", "MREV", "TOOU", "TOIN", "MANN", "PRME"}
UV_PRODUCTS = {"PORK", "BEEF", "COMI", "POUM", "EGGS", "SGMT", "SGMI", "SWHE", "DWHE", "BARL", "RYEM", "OATS",
               "MAIZ", "OCER", "RAPE", "SUNF", "SOYA", "PULS", "SUGB", "POTA", "TOMA", "OVEG", "APPL", "OFRU",
               "CITR", "TAGR", "TWIN", "OLIV", "NITF", "PHOF", "POTF", "YPIG", "IPIG", "YCAM", "YCAF", "YBUL",
               "YHEI", "YCOW", "SGMF", "SOYC", "RAPC", "SUNC", "GRAS", "MAIF", "OFAR", "ROOF", "TEXT", "TOBA", "PARI",
               "OCRO", "OIND", "NURS", "FLOW", "OOIL",
               # inputs (CAPRI moves them with its general price index)
               "EFUL", "ELEC", "EGAS", "ELUB", "SEED", "PLAP", "REPM", "REPB", "INPO", "IPHA"}
#: the max file keeps only these items (size)
MAX_ITEMS = {"LEVL", "MANN", "MREV", "D_O", "D_FEED", "D_NUTNED", "D_PMPL", "D_PMPF", "D_PROV"}
#: region . [qualifier .] activity . item . 2030 ; only the per-unit rows (empty qualifier), not CUR (a near-duplicate),
#: 'total', 'perUAA', 'perAWU' variants
RX = re.compile(r"^'([^']*)'\.(?:'([^']*)'\.)?'([^']*)'\.'([^']*)'\.'2030'\s+(\S+?),?\s*$")


def main(src: str, tag: str) -> None:
    out = ROOT / "capri_data" / "validation" / "greendeal_2030"
    terms, uv = [], []
    for line in open(src, errors="ignore"):
        m = RX.match(line)
        if not m:
            continue
        reg, q, a, it, v = m.groups()
        if q not in (None, ""):
            continue
        try:
            val = float(v)
        except ValueError:
            continue
        if (it.startswith("D_") or it in ITEMS) and (tag != "max" or it in MAX_ITEMS):
            terms.append((reg, a, it, val))
        elif a == "UVAG" and reg.endswith("000000") and it in UV_PRODUCTS:
            uv.append((reg, it, val))
    import lzma, io
    with lzma.open(out / f"capri_marginal_terms_{tag}_2030.csv.xz", "wt", newline="") as f:   # xz: package size
        w = csv.writer(f); w.writerow(["region", "activity", "item", "value"]); w.writerows(terms)
    with open(out / f"capri_unit_values_{tag}_2030.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["region", "product", "uvag"]); w.writerows(uv)
    print(f"{len(terms)} marginal-term rows, {len(uv)} unit values -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
