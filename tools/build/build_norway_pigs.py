"""Give Norway's seven supply regions (NO01-NO07) their pig herds from CAPRI (KNOWN_ISSUES K56, 21 October 2026).

Why
---
Norway's supply regions had no pig activity: animal_numbers.csv held PIGS (sows, CAPRI SOWS) and PIGF (fattening
pigs, CAPRI PIGF) = 0 for every NO0x row, so every per-head pig coefficient was empty for Norway and Norway's pork
came from CAPRI's market supply function instead of its supply models. The cause is the source item, not missing
data: tools/build/build_capri_base.py read the census total 'PIGS'.'HERD' (HERD_MAP "PIGS": "PIGS") and
tools/build_pig_split.py set PIGS := SOWS, PIGF := census total - SOWS, both zero where the total is zero. CAPRI's
EU dumps carry the census total (DE110000: PIGS HERD 1061.37, SOWS HERD 107.80 -> model PIGF 953.57), but CAPRI's
Norwegian data (res_17NO.txt) has no 'PIGS' item, only 'SOWS'.'HERD' and 'PIGF'.'HERD' (and LEVL).

Source
------
CAPRI's 2017 regional results /home/claude/work/capreg/res_17NO.txt (capreg DATA2): 'SOWS'.'HERD' and
'PIGF'.'HERD' of NO020000, NO060000, NO070000, NO080000, NO090000, NO0A0000 (their sums equal NO000000's:
SOWS 49.84, PIGF 451.45 thousand head).

Method
------
    NO02, NO06, NO07:        PIGS := CAPRI 'SOWS'.'HERD'(own region),  PIGF := CAPRI 'PIGF'.'HERD'(own region)
    NO01, NO03, NO04, NO05:  PIGS := s_breeding(r) x sum of CAPRI 'SOWS'.'HERD' over NO080000, NO090000, NO0A0000
                             PIGF := s_fattening(r) x sum of CAPRI 'PIGF'.'HERD' over the same three

NO02, NO06, NO07 take their own CAPRI region (tools/build/build_capri_base.build_spec, imported, not restated).
NO01, NO03, NO04, NO05 (NUTS 2016 redrew CAPRI's NO08, NO09, NO0A into four regions covering the same territory)
share CAPRI's NO080000 + NO090000 + NO0A0000 herds by Statistics Norway's county census of 1 January 2017
(capri_data/sources/ssb/ssb_pigs_county_2017.csv from SSB's file ssb_husdyr_fylke_2017_original.csv, tables
03710 / 03791, by tools/build/build_ssb_pigs.py; the county sums equal SSB's national totals): PIGS by breeding pigs (alssvin), PIGF by fattening pigs (slaktesvin, pigs
slaughtered or sold live in the previous year), counties to NUTS 2016 regions (NO01 Akershus og Oslo; NO03
Ostfold, Buskerud, Vestfold, Telemark; NO04 Aust-Agder, Vest-Agder, Rogaland; NO05 Hordaland, Sogn og Fjordane,
More og Romsdal). Since 22 October 2026; before, the four took Eurostat's cattle shares (a proxy: NO05 0.36 of the
pool's pigs against SSB's 0.09-0.10, NO04 0.42 against 0.54-0.56). Checks: on the regions CAPRI holds itself
(NO02, NO06, NO07) SSB's national shares are within 2.3 points of CAPRI's HERD shares; the project lead's SSB file
of pig places by 2020 county (capri_data/sources/ssb/ssb_pig_places_county_2020.csv) gives the pool's shares NO04
0.537, NO05 0.091, NO01 + NO03 0.372 (2017 census, fattening: 0.539, 0.100, 0.361); it cannot split NO01 from NO03
(the 2020 county Viken spans both), so the 2017 table is the source. Per-head coefficients are per territory group
(CAPRI's three regions with the four model regions), so the split changes the herds and the piglets' base net
exports of the four regions only.

Head definition (differs from the EU rows): the EU rule (census total - sows) cannot be applied because Norway's
capreg data have no census total, so Norway's PIGF is CAPRI's fattening-pig HERD (average stock of fattening
places), while the EU rows' PIGF is the census stock of all non-sow pigs (piglets and young pigs included):
DE11 953.6 (census) against CAPRI's PIGF HERD 604.1. PIGS (sows) is CAPRI's SOWS HERD in both. This is harmless
for the model's base data because every per-head coefficient rebuilt here is CAPRI's regional total divided by the
model's heads (tools/build/build_livestock_output_coef.py "Method"; feed rations, young animals, premiums, manure P and K
and methane the same way), so level x coefficient reproduces CAPRI's totals whatever the head definition (checked:
Norway's pork 139.757 kt = CAPRI's GROF PORK of NO000000, manure N, P, K, CH4, feed, costs and revenue equal CAPRI's
LEVL x item), and capri_level_ratio (model heads per CAPRI LEVL; Norway's PIGF 0.28) adapts the additive term of
CAPRI's activity bounds. Norway's per-head values are therefore not comparable with the EU's (a Norwegian PIGF head
is about 3.6 fattened pigs a year, an EU census head about 2), only their products with the herds are.
Exception found (not changed here, KNOWN_ISSUES K56): the ammonia options' cost per head is CAPRI's cost per place
x DAYS/365 (ammonia_tech_model.csv stock_factor, places per CAPRI LEVL unit), applied per model head as if a model
head were one LEVL unit; for Norway's fattening pigs that is 0.28 of CAPRI's cost (for the EU's census PIGF about
0.5). Shares (NH3, housing losses, N2O per kg N) and 2030 trajectory factors are ratios and need no rebuild.

Rebuild
-------
With --rebuild the per-head files are rebuilt by their existing builders, in the order of
tools/build/build_shg_split.py (coefficient tables, then STEPS), followed by the builders those steps leave out
(manure P and K: build_npk_balance_2030.py; capri_level_ratio: build_capri_level_ratio.py). Each builder rewrites
its whole file; a builder whose output is no longer the file in the data (a file edited after its builder last
ran) would change EU rows too. GUARDED files keep their non-Norwegian rows from the version before the rebuild and
take only Norway's rows from the builder (the check of 21 October 2026 against a copy of capri_data: only
manure_n2o_tech.csv; every other rebuilt file changed in Norway's pig cells only).

Note: tools/build/build_capri_base.py, if rerun, writes CAPRI's census 'PIGS' item into the PIGS column of every region
(HERD_MAP predates the pig split); this tool sets Norway's rows only.

Usage
-----
    python tools/build/build_norway_pigs.py [--dump-dir /home/claude/work/capreg] [--rebuild]
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERDS = ROOT / "capri_data" / "2017" / "supply" / "animal_numbers.csv"
#: model column -> CAPRI activity whose HERD it takes (build_pig_split: PIGS = sows, PIGF = fattening pigs)
PIG_HERD = {"PIGS": "SOWS", "PIGF": "PIGF"}


def _base():
    sp = importlib.util.spec_from_file_location("build_capri_base", ROOT / "tools" / "build" / "build_capri_base.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


#: Statistics Norway's pig census by county, 1 January 2017 (capri_data/sources/ssb/ssb_pigs_county_2017.csv, written by
#: tools/build/build_ssb_pigs.py from SSB's own file ssb_husdyr_fylke_2017_original.csv, tables 03710 / 03791; county sums
#: equal the national totals 89,138 and 1,607,644):
#: breeding pigs (alssvin) and fattening pigs (slaktesvin: pigs slaughtered or sold live in the year before), each
#: county with its NUTS 2016 region
SSB = ROOT / "capri_data" / "sources" / "ssb" / "ssb_pigs_county_2017.csv"
SSB_COL = {"PIGS": "breeding_pigs_alssvin", "PIGF": "fattening_pigs_slaktesvin"}


def ssb_shares() -> dict:
    """{model column: {NO01/NO03/NO04/NO05: share of the four}} from SSB's county census (sows: breeding pigs;
    fattening pigs: pigs slaughtered or sold live)."""
    s = pd.read_csv(SSB)
    B = _base()
    g = s[s.nuts2016.isin(B.NORWAY_CHILDREN)].groupby("nuts2016")[list(SSB_COL.values())].sum()
    return {col: (g[c] / g[c].sum()).to_dict() for col, c in SSB_COL.items()}


def norway_herds(dump: Path) -> pd.DataFrame:
    """Norway's PIGS and PIGF (1000 head): NO02, NO06, NO07 their own CAPRI region; NO01, NO03, NO04, NO05 CAPRI's
    NO080000 + NO090000 + NO0A0000 (the same territory) split by Statistics Norway's county census (ssb_shares)."""
    B = _base()
    capri = B.read_capri(dump)
    a = pd.read_csv(HERDS, index_col=0, float_precision="round_trip")
    nor = [r for r in a.index if r.startswith("NO")]
    spec = B.build_spec(capri, nor)
    sh = ssb_shares()
    out = pd.DataFrame(0.0, index=nor, columns=list(PIG_HERD))
    for reg in nor:
        for col, act in PIG_HERD.items():
            if reg in B.NORWAY_CHILDREN:
                pool = sum(capri.get(c, {}).get("HERD", {}).get(act, 0.0) for c in B.NORWAY_PARENTS)
                out.at[reg, col] = sh[col][reg] * pool
            else:
                out.at[reg, col] = sum(w * capri.get(c, {}).get("HERD", {}).get(act, 0.0) for c, w in spec[reg])
    for col, act in PIG_HERD.items():           # the split must keep Norway's national total
        nat = capri.get("NO000000", {}).get("HERD", {}).get(act, 0.0)
        assert nat > 0 and abs(out[col].sum() - nat) < 1e-6 * nat, (col, out[col].sum(), nat)
    return out


def set_herds(dump: Path) -> pd.DataFrame:
    a = pd.read_csv(HERDS, index_col=0, float_precision="round_trip")
    h = norway_herds(dump)
    for col in PIG_HERD:
        a.loc[h.index, col] = h[col]
    a.to_csv(HERDS)
    print("animal_numbers.csv, Norway (1000 head):\n" + h.round(3).to_string())
    print(f"  total PIGS {h['PIGS'].sum():.3f}, PIGF {h['PIGF'].sum():.3f}")
    return h


# ---------------------------------------------------------------- rebuild --
#: builders run after build_shg_split's steps (files those steps do not write)
EXTRA_STEPS = (["tools/build/build_npk_balance_2030.py"], ["tools/build/build_capri_level_ratio.py", "--dump-dir", "{dump}"])
#: files whose builder no longer reproduces the EU rows in the data: only Norway's rows are taken from it.
#: manure_n2o_tech.csv: tools/build/build_manure_n2o.py now writes 29 AirPurCovHigh rows for pigs (PIGF, PIGS) in EU
#: regions that the file in the data does not hold (BE10, CZ01, DE30, DE50, DE60, DK01-DK05, ES64, FI20, LT01, ...);
#: its Norwegian rows are the same either way (check of 21 October 2026)
GUARDED = ("capri_data/2017/environment/manure_n2o_tech.csv",)


def _norway_rows_only(path: Path, before: Path):
    """Write `before` back with only its Norwegian rows (first column starting 'NO') replaced by `path`'s, text kept
    line by line (CSV files whose first column is the model region)."""
    old = before.read_text().splitlines(keepends=True)
    new = path.read_text().splitlines(keepends=True)
    assert old[0] == new[0], f"{path.name}: header changed"
    is_no = lambda line: line.split(",", 1)[0].strip('"').startswith("NO")
    nor = [l for l in new[1:] if is_no(l)]
    out, placed = [old[0]], False
    for l in old[1:]:
        if is_no(l):
            if not placed:
                out += nor
                placed = True
            continue
        out.append(l)
    if not placed:
        out += nor
    path.write_text("".join(out))


def rebuild(dump: Path):
    sp = importlib.util.spec_from_file_location("build_shg_split", ROOT / "tools" / "build" / "build_shg_split.py")
    S = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(S)
    keep = Path(tempfile.mkdtemp())
    for rel in GUARDED:
        shutil.copy2(ROOT / rel, keep / Path(rel).name)
    S.coefficient_tables(dump)
    S.run_steps(dump)
    for cmd in EXTRA_STEPS:
        cmd = [c.format(dump=dump) for c in cmd]
        r = subprocess.run([sys.executable] + cmd, cwd=ROOT, capture_output=True, text=True)
        tail = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
        print(cmd[0], "->", tail[:160], ("FAILED: " + r.stderr.strip()[-400:]) if r.returncode else "")
    for rel in GUARDED:
        _norway_rows_only(ROOT / rel, keep / Path(rel).name)
        print(rel, "-> non-Norwegian rows kept from before the rebuild")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, default=Path("/home/claude/work/capreg"))
    ap.add_argument("--rebuild", action="store_true", help="rebuild the per-head files after setting the herds")
    a = ap.parse_args()
    set_herds(a.dump_dir)
    if a.rebuild:
        rebuild(a.dump_dir)


if __name__ == "__main__":
    main()
