"""Parity of CAPTRD's expert supports from COCO's nowcasts (capri_mod/pipeline/captrd/coco_supports.py;
define_stats_and_supports.gms l. 377-455, 522-534) with CAPTRD's own Expert of 2018 (its only ExAnteD year), on
CAPTRD's stored P_Data and nObs.

Results on 10 November 2026 (Expert 2018, 107,619 records in CAPTRD's results):
  - 91,880 records on both sides, 91,794 equal; the others, and the 197 only here, are biofuel positions (BIOF, NAGR,
    SECG, PRCB, PRCBY or the fuel and DDGS rows: 216) and sugar (SUGA, SUGB, MOLA: 65), which expert_support.gms's
    biofuel trends and sugar rules and adjust_to_biof_supports.gms rework (not yet ported), and 2 (CS000000 INHA.CERE,
    MO000000 PRCM.CERE; not traced);
  - the records only in CAPTRD's: the yield rows YILD (12,642) and DEMD (2,638), which the reporting writes
    (aggreg_and_report.gms), and 459 expert supports of other sources for 2018 (biofuel processing PRCB/PRCBY,
    HFCS, sugar; expert_support.gms, not yet ported).
"""
from __future__ import annotations

import pandas as pd
import pytest

from capri_mod.external_paths import REFERENCE
from capri_mod.pipeline.captrd import coco_supports as C
from capri_mod.pipeline.captrd import prepare as P
from capri_mod.pipeline.captrd.coco import BIO_COLS_COCO, BIO_ROWS_COCO

R = REFERENCE / "captrd_results" / "1770"
need = pytest.mark.skipif(not (R / "Expert.csv.gz").exists(), reason="CAPRI reference files not built")
K = ["region", "col", "row", "t"]


def test_the_close_to_base_flag_is_never_set_as_coded():
    """l. 392-394 assigns the flag to itself: colsNoCoco stay out even in the last ex-post year (only raw milk passes)."""
    p = pd.DataFrame([("DK000000", "LOSF", "SWHE", "2018", 5.0), ("DK000000", "LOSF", "SWHE", "BASM", 5.0),
                      ("DK000000", "LOSF", "COMI", "2018", 3.0), ("DK000000", "GROF", "SWHE", "2018", 9.0)],
                     columns=["region", "col", "row", "t", "value"])
    nobs = pd.DataFrame([("DK000000", "LOSF", "SWHE", 30.0), ("DK000000", "LOSF", "COMI", 30.0),
                         ("DK000000", "GROF", "SWHE", 30.0)], columns=["region", "col", "row", "value"])
    c = C.coco_supports(p, nobs, [2018], 2018, ["ENNE"], ["COMI"], set(), set(), set(), {"LOSF", "GROF"},
                        {"SWHE", "COMI"}, ["DK000000"]).set_index(["col", "row"])
    assert c.loc[("LOSF", "SWHE"), "coco"] == 0.0 and c.loc[("LOSF", "COMI"), "coco"] == 3.0
    assert c.loc[("GROF", "SWHE"), "coco"] == 9.0 and c.loc[("GROF", "SWHE"), "trust"] == C.TRUST_COCO


@pytest.mark.slow
@need
def test_coco_supports_equal_captrds_expert_of_2018():
    s = P.read_sets()
    pdata = pd.read_csv(R / "P_Data.csv.gz", dtype={"t": str})
    d = pd.read_csv(R / "data.csv.gz", dtype={"t": str})
    mlko = pd.read_csv(REFERENCE / "sets" / "simini_21730" / "MLKO.csv", keep_default_na=False).d0
    c = C.coco_supports(pdata, d[d.t == "nObs"], [2018], 2018, s.reqst, mlko, BIO_COLS_COCO, BIO_ROWS_COCO,
                        s.pact_to_y, s.s_colsest, s.s_rowsest, sorted(set(pdata.region)))
    e = pd.read_csv(R / "Expert.csv.gz", dtype={"t": str})
    e = e[(e.t == "2018") & (e.row != "YILD") & (e.col != "DEMD")]
    mine = c[c.coco != 0][K + ["coco"]].rename(columns={"coco": "value"})
    m = mine.merge(e[K + ["value"]], on=K, how="outer", suffixes=("", "_ref"), indicator=True)
    m = m.fillna({"value": 0.0, "value_ref": 0.0})
    m["ok"] = (m.value - m.value_ref).abs() <= 1e-9 * m.value_ref.abs().clip(lower=1e-9)
    both = m[m._merge == "both"]
    assert len(both) > 90_000 and both.ok.sum() > 91_700
    x = m[(m._merge == "left_only") | ((m._merge == "both") & ~m.ok)]
    later = (x.col.isin(["BIOF", "NAGR", "SECG", "PRCB", "PRCBY"])
             | x.row.isin(["BIOE", "BIOD", "GASL", "DISL", "DDGS", "CRDO", "SUGA", "SUGB", "MOLA"]))
    assert (~later).sum() <= 2, x[~later]
