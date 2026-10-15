"""EU agricultural outlook 2020-2030 (DG AGRI, December 2020): the annex market balances as CSV.

python tools/build_eu_outlook_2030.py REPORT.pdf
-> capri_data/validation/eu_outlook_2020_2030.csv: table, title, item, one column per year 2016-2030.

Source: EC (2020), EU agricultural outlook for markets, income and environment, 2020-2030, DG AGRI, Brussels,
doi:10.2762/252413, Annex tables 8.8-8.44. Text extracted with pdftotext -layout; a row is kept when it carries a
value for every year 2016-2030 (15 numbers). Rows whose label is split over two lines in the PDF get the label of the
line above or below ("Fodder (green maize, temp. grassland etc.)"). The outlook's 2030 is the medium-term baseline of
DG AGRI and the JRC (AGLINK-COSIMO, with CAPRI for the environment) - an independent check of CAPRI-mod's 2030
baseline, which is calibrated to CAPRI star 3.0's own 2030 reference.
"""
import csv
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "capri_data" / "validation" / "eu_outlook_2020_2030.csv"
YEARS = list(range(2016, 2031))
NUM = re.compile(r"-?[\d.,]+%?|n\.a\.|-")


def _join_thousands(vals, n):
    """Values printed with a space as thousands separator ("10 503") come as two tokens: join a 1-2 digit token with a
    following 3-digit token, left to right, until n values remain (None if that is not possible)."""
    out, i = [], 0
    extra = len(vals) - n
    while i < len(vals):
        if extra > 0 and i + 1 < len(vals) and re.fullmatch(r"-?\d{1,2}", vals[i]) and re.fullmatch(r"\d{3}(\.\d+)?", vals[i + 1]):
            out.append(vals[i] + vals[i + 1]); i += 2; extra -= 1
        else:
            out.append(vals[i]); i += 1
    return out if len(out) == n else None


def main(pdf):
    txt = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    lines = txt.splitlines()
    tab, rows = None, []
    for i, l in enumerate(lines):
        m = re.match(r"\s*TABLE (8\.\d+) (.*)", l)
        if m:
            tab = (m.group(1), m.group(2).strip())
            continue
        if tab is None or int(tab[0].split(".")[1]) < 8:
            continue
        toks = l.split()
        lab = []
        for t in toks:
            if NUM.fullmatch(t):
                break
            lab.append(t)
        vals = [t for t in toks[len(lab):] if NUM.fullmatch(t)]
        if len(vals) > len(YEARS):
            vals = _join_thousands(vals, len(YEARS))
        if vals is None or len(vals) != len(YEARS):
            continue
        label = " ".join(lab)
        if label in ("", ) and vals[0] == "2016":
            continue                                        # the year header
        if not label:                                       # label split over the neighbouring lines
            label = " ".join((lines[i - 1].strip() + " " + lines[i + 1].strip()).split())
        rows.append([tab[0], tab[1], label] + [v.replace(",", "") for v in vals])
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["table", "title", "item"] + [str(y) for y in YEARS])
        w.writerows(rows)
    print(f"{len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
