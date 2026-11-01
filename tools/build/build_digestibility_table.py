"""CAPRI's feed digestibility table and its default products, from CAPRI's code to CSV (KNOWN_ISSUES K93: 3-NOP).

CAPRI writes the composition of the feeds in its code: envind/def_digestibility.gms, TABLE p_digestPar("EU", "DCOL",
feed, item) (NRC 2001, partly INRA 2002; the commented alternatives are not CAPRI's values), and the set DEF_PRD of the
products whose values fill a feed's missing items (digestibility.gms l. 37-38). This builder reads the table as GAMS
reads it (a value belongs to the column whose header it overlaps; lines starting with * are comments) and writes:

  capri_data/sources/envind/capri_digestpar.csv           feed, item, value     (items PAF, DM, CP, NDICP, ADICP, EE,
                                                                                 NDF, ADF, LI, ASH, CAT)
  capri_data/sources/envind/capri_digest_default_prd.csv  default, feed         (DEF_PRD: feed takes default's values)

    python tools/build/build_digestibility_table.py [CAPRI gams folder, default /home/claude/work/allgms/gams]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from capri_mod.csvio import to_csv  # noqa: E402

import pandas as pd  # noqa: E402

OUT = ROOT / "capri_data" / "sources" / "envind"


def parse_table(text: str) -> list:
    lines = text.replace("\r", "").split("\n")
    i = next(k for k, ln in enumerate(lines) if ln.startswith("TABLE p_digestPar"))
    head = lines[i + 1]
    cols = [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\S+", head)]
    rows = []
    for ln in lines[i + 2:]:
        if ln.strip() == ";":
            break
        if not ln.strip() or ln.lstrip().startswith("*"):
            continue
        toks = list(re.finditer(r"\S+", ln))
        key = toks[0].group(0)
        if not key.startswith("EU.DCOL."):
            raise SystemExit(f"unexpected row {ln!r}")
        feed = key.split(".")[2]
        for t in toks[1:]:
            s, e = t.start(), t.end()
            hit = [c for c in cols if s < c[2] and e > c[1]]
            if len(hit) != 1:
                raise SystemExit(f"{feed}: value {t.group(0)!r} at {s}-{e} overlaps {len(hit)} headers")
            rows.append((feed, hit[0][0], float(t.group(0))))
    return rows


def parse_def_prd(text: str) -> list:
    m = re.search(r"SET DEF_PRD\(ROWS,ROWS\)[^/]*/(.*?)/;", text, re.S)
    body = "\n".join(ln for ln in m.group(1).replace("\r", "").split("\n") if not ln.lstrip().startswith("*"))
    out = []
    for d, members in re.findall(r"(\w+)\.\(([^)]*)\)", body):
        out += [(d, x.strip()) for x in members.split(",") if x.strip()]
    return out


def main(gams: Path):
    text = (gams / "envind" / "def_digestibility.gms").read_text(errors="ignore")
    t = pd.DataFrame(parse_table(text), columns=["feed", "item", "value"])
    if t.duplicated(["feed", "item"]).any():
        raise SystemExit("a feed and item twice in CAPRI's table")
    d = pd.DataFrame(parse_def_prd(text), columns=["default", "feed"])
    if d.duplicated("feed").any():
        raise SystemExit("a feed with two default products")
    to_csv(t, OUT / "capri_digestpar.csv", index=False)
    to_csv(d, OUT / "capri_digest_default_prd.csv", index=False)
    print(f"capri_digestpar.csv: {t.feed.nunique()} feeds, {len(t)} values; capri_digest_default_prd.csv: {len(d)} pairs")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/claude/work/allgms/gams"))
