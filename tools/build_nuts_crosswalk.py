"""
Build a NUTS-2 crosswalk from the model's region codes back to CAPRI's.

The model keys regions with modern NUTS-2 codes (FRB0, ITH1). CAPRI's
`gams/capreg/regio_sets.gms` keys them with the older classification (FR24,
ITE1) padded to eight characters (FR240000). 88 of the model's 248 regions
therefore failed to match on the `NUTS2 + "0000"` rule alone.

This walks Eurostat's official correspondence tables backwards through the
version chain (2027 -> 2024 -> 2021 -> 2016 -> 2013) and composes them, so a
modern code can be resolved to whichever historical code CAPRI knows.

Only **1:1 recodes** are emitted as usable crosswalk entries. Splits and merges
(one 2013 region becoming three 2021 regions, or the reverse) cannot be resolved
by code mapping alone — they need area-weighted aggregation and are reported
separately rather than guessed at.

Usage
-----
    python tools/build_nuts_crosswalk.py --nuts-dir /path/to/nuts/tables \\
                                         --capri-gams /path/to/capri/gams \\
                                         --out capri_data/shared/nuts_crosswalk.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

# (filename, sheet, older-version label, newer-version label)
CHAIN = [
    ("nuts1995-1999.xlsx", "NUTS1995-NUTS1999", "1995", "1999"),
    ("nuts1999-2003.xlsx", "NUTS1999-NUTS2003", "1999", "2003"),
    ("nuts2003-2006.xlsx", "NUTS2003-NUTS2006", "2003", "2006"),
    ("nuts2006_2010.xlsx", "Correspondence NUTS-2", "2006", "2010"),
    ("NUTS_2010_-_NUTS_2013.xlsx", "Correspondence NUTS-2", "2010", "2013"),
    ("NUTS2013-NUTS2016__1_.xlsx", "Correspondence NUTS-2", "2013", "2016"),
    ("NUTS2021.xlsx", "Changes NUTS-2", "2016", "2021"),
    ("NUTS2021-NUTS2024.xlsx", "Changes NUTS-2", "2021", "2024"),
    ("NUTS2024-NUTS2027.xlsx", "Changes NUTS-2", "2024", "2027"),
]

NUTS2_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{2}$")

# CAPRI merges Belgium and Luxembourg into a single pseudo-country BL, so the
# model's BE and LU regions have no BE/LU-prefixed counterpart. Verified against
# DATA2_BL.txt: BL21..BL35 carry Belgian regional yields (BL21 SWHE 6.23 t/ha)
# and BL40 is Luxembourg. Brussels (BE10 / BL10) has no arable data, which is
# expected rather than missing.
COUNTRY_ALIASES = {
    "BE": lambda code: "BL" + code[2:],
    "LU": lambda code: "BL40",
}


def read_correspondence(path: Path, sheet: str) -> pd.DataFrame:
    """
    Return a two-column frame [old, new]; blanks mark discontinued/new rows.

    Layouts differ across Eurostat vintages. The 2013+ tables put the two code
    columns first; the 1995-2010 tables shipped with CAPRI carry a leading index
    column and interleave all NUTS levels in one sheet. So the code columns are
    located by their header text ("Code 1999", "Code 2003", ...) rather than by
    position, and rows are filtered to NUTS-2 shape afterwards.
    """
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    hdr = None
    for i in range(min(10, len(raw))):
        if raw.iloc[i].astype(str).str.match(r"Code\s*\d{4}", na=False).any():
            hdr = i
            break
    if hdr is None:
        raise SystemExit(f"no 'Code <year>' header found in {path.name}:{sheet}")

    header = raw.iloc[hdr].astype(str)
    pat = re.compile(r"Code\s*\d{4}")
    code_cols = [c for c in raw.columns if pat.match(str(header[c]).strip())]
    if len(code_cols) < 2:
        raise SystemExit(f"expected two code columns in {path.name}:{sheet}")

    df = raw.iloc[hdr + 1:, code_cols[:2]].copy()
    df.columns = ["old", "new"]
    for c in ("old", "new"):
        df[c] = df[c].astype(str).str.strip()
        # NUTS-2 shape only: two country letters plus two alphanumerics.
        df.loc[~df[c].str.match(NUTS2_RE), c] = None
    return df.dropna(how="all")


def one_to_one(df: pd.DataFrame) -> dict[str, str]:
    """new -> old, keeping only unambiguous 1:1 recodes."""
    pairs = df.dropna(subset=["old", "new"])
    # Drop any code appearing more than once on either side: that is a split
    # or a merge, not a recode.
    ok_new = pairs["new"].value_counts()
    ok_old = pairs["old"].value_counts()
    pairs = pairs[pairs["new"].map(ok_new).eq(1) & pairs["old"].map(ok_old).eq(1)]
    return dict(zip(pairs["new"], pairs["old"]))


def ambiguous(df: pd.DataFrame) -> list[str]:
    pairs = df.dropna(subset=["old", "new"])
    n, o = pairs["new"].value_counts(), pairs["old"].value_counts()
    bad = pairs[~(pairs["new"].map(n).eq(1) & pairs["old"].map(o).eq(1))]
    return sorted({f'{r.old}->{r.new}' for r in bad.itertuples()})


def load_capri_codes(gams_root: Path) -> set[str]:
    text = (gams_root / "capreg" / "regio_sets.gms").read_text(
        encoding="utf-8", errors="replace")
    return set(re.findall(r"\b([A-Z]{2}[A-Z0-9]{6})\b", text))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nuts-dir", required=True, type=Path)
    ap.add_argument("--capri-gams", required=True, type=Path)
    ap.add_argument("--model-regions", type=Path,
                    default=Path("capri_data/2017/supply/yields.csv"))
    ap.add_argument("--out", type=Path,
                    default=Path("capri_data/shared/nuts_crosswalk.json"))
    args = ap.parse_args()

    # Compose the chain newest -> oldest.
    steps, splits = [], {}
    for fname, sheet, old_v, new_v in CHAIN:
        path = args.nuts_dir / fname
        if not path.exists():
            print(f"  (skipped, not present: {fname})")
            continue
        df = read_correspondence(path, sheet)
        steps.append((f"{new_v}->{old_v}", one_to_one(df)))
        amb = ambiguous(df)
        if amb:
            splits[f"{old_v}->{new_v}"] = amb
        print(f"  {fname:34s} {len(one_to_one(df)):4d} 1:1, {len(amb):3d} split/merge")

    def to_oldest(code: str) -> list[str]:
        """All historical aliases of a modern code, newest first."""
        chain, cur = [code], code
        for _, mapping in reversed(steps):   # 2027->2024, ... , 2016->2013
            cur = mapping.get(cur, cur)
            if cur != chain[-1]:
                chain.append(cur)
        return chain

    capri = load_capri_codes(args.capri_gams)
    regions = pd.read_csv(args.model_regions, index_col=0).index

    # A model region can have several historical aliases, and regio_sets.gms
    # often contains more than one of them. Which one the *data* uses is a
    # different question -- CAPRI's Italian DATA2 is keyed IT110000 (1995 codes)
    # even though ITC10000 (2003 codes) is also declared. So every alias is
    # emitted, oldest last, and consumers try them in order.
    resolved, aliases, direct, unresolved = {}, {}, 0, []
    for r in regions:
        chain = [f"{a}0000" for a in to_oldest(r)]
        alias_fn = COUNTRY_ALIASES.get(r[:2])
        if alias_fn:
            chain.append(f"{alias_fn(r)}0000")
        attested = [c for c in chain if c in capri]
        if not attested:
            unresolved.append(r)
            continue
        resolved[r] = attested[0]
        aliases[r] = attested
        if attested[0] == f"{r}0000":
            direct += 1

    print(f"\nmodel regions            : {len(regions)}")
    print(f"  direct (NUTS2+'0000')  : {direct}")
    print(f"  via version chain      : {len(resolved) - direct}")
    print(f"  still unresolved       : {len(unresolved)}")
    if unresolved:
        by_c = pd.Series([u[:2] for u in unresolved]).value_counts()
        print(f"  unresolved by country  : {by_c.to_dict()}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "_purpose": "model NUTS-2 code -> CAPRI 8-character region code",
        "_method": "direct NUTS2+'0000', else Eurostat correspondence chain "
                   "2027->2024->2021->2016->2013, 1:1 recodes only",
        "_caveat": "splits and merges are excluded; they need area-weighted "
                   "aggregation, not code mapping",
        "resolved": resolved,
        "aliases": aliases,
        "unresolved": unresolved,
        "splits_and_merges_by_step": splits,
    }, indent=1))
    print(f"\nwritten: {args.out}")


if __name__ == "__main__":
    main()
