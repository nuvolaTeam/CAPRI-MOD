"""CAPTRD's expert supports from COCO's nowcasts (captrd/define_stats_and_supports.gms l. 377-455 and 522-534, CAPRI
star 3.0): the data of the ex-ante years COCO covers (ExAnteD, after CAPREG's last year) taken as expert supports
("coco"), which overwrite the other experts' for those years ("Expert").

  l. 386-394  the relative deviation of the nowcast from the base year, 2 |P - BASM| / (P + BASM), and a flag
              "closeToBas" where it is below 1.2. As coded the flag assigns itself (l. 392-394:
              p_dataPositionIsOk("closeToBas", ...) = p_dataPositionIsOk("closeToBas", ...)), so it is never set and the
              exception it guards (the columns colsNoCoco in years up to the last ex-post year) never applies: kept as
              coded
  l. 396-410  p_cocoSupport Absolute = the year's data, where the column is not in colsNoCoco (or the row is raw milk,
              MLKO), the row is not in rowsNoCoco (the requirements and two young-animal rows), and the series has
              observations (nObs) or is a biofuel column or row
  l. 424-454  its trust levels: 7; 0.5 for the derived positions (EAAG, TOOU); 10 for activity levels and yields
  l. 522-534  "coco" = p_cocoSupport where the column is not in colsNoCoco or the year is not after the last ex-post year
              or the row is raw milk, the row not in rowsNoCoco, the data nonzero; "Expert" = "coco" where nonzero
"""
from __future__ import annotations

from typing import Dict, Iterable, Tuple

import pandas as pd

#: load_coco1_data.gms l. 32-37 (REQST added by the caller), l. 316-317
COLS_NO_COCO = {"LOSF", "LOSM", "SEDM", "SEDF"}
ROWS_NO_COCO_EXTRA = {"IPIG", "ICHI"}
#: l. 425-449 trust levels
TRUST_COCO = 7.0
TRUST_DERIVED = 0.5
TRUST_LEVL_YIELD = 10.0
DERIVED_COLS, DERIVED_ROWS = {"EAAG"}, {"TOOU"}
#: l. 391: the nowcast's relative deviation from BASM below which it is "close to BAS" (the flag is never set, above)
CLOSE_TO_BAS = 1.2


def coco_supports(pdata: pd.DataFrame, nobs: pd.DataFrame, exanted: Iterable[int], lst_expost: int,
                  reqst: Iterable[str], mlko: Iterable[str], bio_cols: Iterable[str], bio_rows: Iterable[str],
                  pact_to_y: Iterable[Tuple[str, str]], cols_est: Iterable[str], rows_est: Iterable[str],
                  regions: Iterable[str]) -> pd.DataFrame:
    """Expert supports from COCO (columns region, col, row, t, absolute, trust, coco): p_cocoSupport's Absolute and
    TrustLevl, and the "coco" position that becomes "Expert" (0 where it does not)."""
    rows_no = set(reqst) | ROWS_NO_COCO_EXTRA
    mlko, bio_cols, bio_rows = set(mlko), set(bio_cols), set(bio_rows)
    pty = set(pact_to_y)
    cols_est, rows_est, regs = set(cols_est), set(rows_est), set(regions)
    have_obs = {(r, c, w) for r, c, w, v in zip(nobs.region, nobs.col, nobs.row, nobs.value) if v != 0}
    basm: Dict[tuple, float] = {}
    b = pdata[pdata.t == "BASM"]
    for r, c, w, v in zip(b.region, b.col, b.row, b.value):
        basm[(r, c, w)] = float(v)
    out = []
    for y in exanted:
        d = pdata[(pdata.t == str(y)) & pdata.region.isin(regs) & pdata.col.isin(cols_est) & pdata.row.isin(rows_est)
                  & (pdata.value != 0)]
        for r, c, w, v in zip(d.region, d.col, d.row, d.value.astype(float)):
            close = False                        # l. 392-394 as coded: never set
            ok = ((c not in COLS_NO_COCO or (y <= lst_expost and close) or w in mlko) and w not in rows_no
                  and ((r, c, w) in have_obs or c in bio_cols or w in bio_rows))
            absolute = v if ok else 0.0
            trust = 0.0
            if absolute:
                trust = TRUST_COCO
                if c in DERIVED_COLS or w in DERIVED_ROWS:
                    trust = TRUST_DERIVED
                if w == "LEVL":
                    trust = TRUST_LEVL_YIELD
                if (c, w) in pty:
                    trust = TRUST_LEVL_YIELD
            coco_ok = (c not in COLS_NO_COCO or y <= lst_expost or w in mlko) and w not in rows_no
            coco = absolute if coco_ok else 0.0
            out.append((r, c, w, str(y), absolute, trust, coco))
    return pd.DataFrame(out, columns=["region", "col", "row", "t", "absolute", "trust", "coco"])
