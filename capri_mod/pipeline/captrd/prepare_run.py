"""CAPTRD's data preparation over all countries, in CAPTRD's order (captrd.gms l. 486-937).

Per country file, in passes where a step needs every country:
  1  load the years, load fixes, BASM                        captrd.gms l. 504-580       (UAAR -> ExPost, l. 673)
  2  COCO data of the country prepared                        load_coco1_data.gms l. 37-334 (ExAnteD from every country)
  3  COCO applied, checks, deletions                          load_coco1_data.gms l. 250-561 (biofuel flags from every
                                                              country); captrd.gms l. 830-850
  4  UVAD averaged over the market aggregates                 l. 852-860 (every country's UVAD)
  5  regions' cleaning, LABH, prep_data_for_estimation        l. 862-898; prep_data_for_estimation.gms l. 15-162
The time sets come from timesets.py's rules: ExPost from CAPREG's UAAR, ExPostT adds ExAnteD, BASYRS5 and BASYRSM
around the base year within ExPost (captrd.gms l. 673-705, 721-722).

Not yet in this order (docs/design/CAPTRD_MOD.md section 12.2): the labour agelines (baseline/labour_ageline.gms) and
the policy data (captrd_policy.gms), between steps 5's LABH and prep_data_for_estimation.

    python -m capri_mod.pipeline.captrd.prepare_run --out DIR [--countries DK AT ...]
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd

from capri_mod.pipeline.captrd import coco as C
from capri_mod.pipeline.captrd import prepare as P

log = logging.getLogger(__name__)
REF = P.ROOT / "capri_reference"


def _cc(ms: str) -> str:
    return ms[:2] if ms.endswith("000000") else ms


def run(countries: Iterable[str], sets: P.CaptrdSets, base_year: int, first_year: int, last_year: int,
        tseries_dir: Path, base_dir: Path, coco_file: Path, biofuel_file: Optional[Path], work: Path,
        extr: Optional[dict] = None) -> Dict[str, Path]:
    """The prepared p_data of each country (MS code), written to work/<CC>.parquet. A country without its CAPREG files
    stops the run (CAPTRD aborts on missing base-year data, captrd.gms l. 568)."""
    work.mkdir(parents=True, exist_ok=True)
    ms_list = [m for m in sets.ms if m in set(countries)]
    years = list(range(first_year, last_year + 1))
    for m in ms_list:
        for f in (tseries_dir / f"{_cc(m)}.csv.gz", base_dir / f"{_cc(m)}.csv.gz"):
            if not f.exists():
                raise FileNotFoundError(f"{m}: {f} missing")
    # 1
    ua = []
    for m in ms_list:
        raw = P.read_series(tseries_dir / f"{_cc(m)}.csv.gz", sets, years)
        ua.append(raw[(raw["col"] == "UAAR") & (raw["row"] == "LEVL")])
        p = P.load_basm(P.load_fixes(raw, sets), pd.read_csv(base_dir / f"{_cc(m)}.csv.gz", keep_default_na=False),
                        sets)
        p.to_parquet(work / f"{_cc(m)}.1.parquet", index=False)
        log.info("%s: loaded, %d records", m, len(p))
    expost = P.expost_years(pd.concat(ua, ignore_index=True), sets.ms)
    coco = pd.concat(c[c["region"].isin(set(ms_list)) & (c["item"].str.upper() == "COCO1")]
                     for c in pd.read_csv(coco_file, chunksize=2_000_000, dtype={"t": str}, keep_default_na=False))
    exanted = C.exante_d(coco, sets.ms, expost, years)
    expostt = sorted(set(expost) | set(exanted))
    from capri_mod.settings import current as _settings
    h = int(_settings().get("captrd.basyrs5_halfwidth"))
    basyrs5 = [y for y in expost if abs(y - base_year) <= h]       # captrd.gms l. 703
    basyrsm = [y for y in expost if abs(y - base_year) <= 1]       # l. 704
    log.info("ExPost %s-%s, ExAnteD %s", expost[0], expost[-1], exanted)
    # 2
    prepared, usable = {}, {}
    for m in ms_list:
        p = pd.read_parquet(work / f"{_cc(m)}.1.parquet")
        prepared[m], usable[m] = C.prepare_country(coco[coco["region"] == m], p, m, sets, expost, exanted, years,
                                                   basyrs5, basyrsm)
    flags = C.bio_flags(prepared, expostt)
    bf = None
    if biofuel_file is not None:
        bf = pd.read_csv(biofuel_file, dtype=str, keep_default_na=False).astype({"value": float, "eps": int})
    # 3
    uv, skipped = [], set()
    for m in ms_list:
        p = pd.read_parquet(work / f"{_cc(m)}.1.parquet")
        p, sk = C.apply_country(p, prepared[m], usable[m], m, sets, expost, exanted, years, basyrsm, flags, bf, extr)
        skipped |= set(sk)
        p = P.delete_early_years(P.delete_unestimated(P.check_and_cor(p, sets), sets), sets)
        p.to_parquet(work / f"{_cc(m)}.3.parquet", index=False)
        uv.append(p[p["col"] == "UVAD"])
    for s_ in sorted(skipped):
        log.warning("skipped: %s", s_)
    # 4
    added = P.fill_uvad(pd.concat(uv, ignore_index=True), sets, expostt)
    # 5
    out = {}
    for m in ms_list:
        p = pd.read_parquet(work / f"{_cc(m)}.3.parquet")
        p = pd.concat([p, added[added["region"].isin(set(p["region"]))]], ignore_index=True)
        p = P.labour_household(P.clean_regions(p, sets, expost))
        p = P.prep_for_estimation(p, sets, expostt, basyrs5, basyrsm, years)
        out[m] = work / f"{_cc(m)}.parquet"
        p.to_parquet(out[m], index=False)
    return out


def main(argv: Optional[List[str]] = None) -> None:
    from capri_mod.settings import current as _settings
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--countries", nargs="*", help="MS codes or two-letter codes; default: every country with files")
    ap.add_argument("--base-year", type=int, default=2017)
    ap.add_argument("--last-year", type=int, default=2019, help="last year of the data (Years runs further in CAPTRD)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    sets = P.read_sets()
    ts_dir, base_dir = REF / "capreg_tseries" / "17", REF / "capreg_base" / "17"
    if args.countries:
        want = {c if len(c) > 2 else c + "000000" for c in args.countries}
    else:
        want = {m for m in sets.ms if (ts_dir / f"{_cc(m)}.csv.gz").exists() and (base_dir / f"{_cc(m)}.csv.gz").exists()}
    run(want, sets, args.base_year, int(_settings().get("captrd.first_year")), args.last_year, ts_dir, base_dir,
        REF / "coco2" / "17" / "coco2_output.csv.gz", REF / "fao_agg" / "17" / "p_biofuelData.csv.gz", Path(args.out))


if __name__ == "__main__":
    main()
