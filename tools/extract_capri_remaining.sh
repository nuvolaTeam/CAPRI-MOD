#!/usr/bin/env bash
#
# CAPRI-Python — extract the remaining real data
# ==============================================
#
# This produces the same kind of dump as the coco2.csv you already sent: a flat
# GAMS parameter listing with explicit dimensions and years. That file worked
# perfectly, which is why this script simply repeats the method on the results
# that matter now.
#
# Requires gdxdump (ships with GAMS). Run it from anywhere:
#
#     bash extract_capri_remaining.sh /path/to/capri/output/results
#
# Output lands in ./capri_export/ . Upload whatever it produces — partial is
# fine, each file is independently useful and a missing symbol never halts the
# batch.
#
# Priority order if you can only get some of it:
#   1. capreg DATA2      -> yields (incl. livestock), areas, herds, at a known year
#   2. estnlp PELA       -> regional supply elasticities for all activities
#   3. capreg pmppar     -> the PMP quadratic terms themselves
#   4. feed + fert       -> removes the last two fully synthetic inputs
#
set -uo pipefail

RESULTS="${1:-.}"
OUT="./capri_export"
mkdir -p "$OUT"

dump () {                      # dump <gdx-file> <symbol> <output-name>
  local gdx="$1" sym="$2" name="$3"
  [ -f "$gdx" ] || return 0
  echo "  $sym  <-  $(basename "$gdx")"
  gdxdump "$gdx" symb="$sym" format=csv > "$OUT/${name}.csv" 2>/dev/null \
    || gdxdump "$gdx" symb="$sym" > "$OUT/${name}.txt" 2>/dev/null \
    || echo "     (symbol not present, skipped)"
}

echo "=== 1. capreg regional results: DATA2 ==========================="
# The master regional cube: region x activity x item x year.
# This is the single most valuable file. It carries YILD for livestock as well
# as crops, which COCO does not, and it is regional rather than national.
for f in "$RESULTS"/capreg/res_*.gdx; do
  [ -e "$f" ] || continue
  dump "$f" DATA2 "capreg_DATA2_$(basename "${f%.gdx}")"
done

echo "=== 2. estnlp: regional supply elasticities ====================="
# PELA is the econometric elasticity estimate set. Currently the model has real
# elasticities for 132 of 248 regions and 14 of 40 activities; this closes it.
for f in "$RESULTS"/estnlp/*.gdx "$RESULTS"/../estnlp/*.gdx; do
  [ -e "$f" ] || continue
  dump "$f" PELA   "estnlp_PELA_$(basename "${f%.gdx}")"
  dump "$f" p_pela "estnlp_ppela_$(basename "${f%.gdx}")"
done

echo "=== 3. PMP quadratic terms ======================================"
# p_pmpQuadTechn is the activity-level diagonal, p_pmpQuadPact the group-level
# term. Together they give CAPRI's Q matrix directly, replacing both the
# elasticity-derived diagonal and the invented off-diagonal heuristic.
for f in "$RESULTS"/capreg/pmppar_*.gdx "$RESULTS"/baseline/pmppar_*.gdx; do
  [ -e "$f" ] || continue
  b="$(basename "${f%.gdx}")"
  dump "$f" p_pmpQuadTechn "pmp_quadTechn_$b"
  dump "$f" p_pmpQuadPact  "pmp_quadPact_$b"
  dump "$f" p_pmpCnstTechn "pmp_cnstTechn_$b"
  dump "$f" p_pmpFeedInpCoeff "feed_coeff_$b"
done

echo "=== 4. fertiliser / nutrients ==================================="
for f in "$RESULTS"/capreg/fert_out*.gdx; do
  [ -e "$f" ] || continue
  dump "$f" fert_out "fert_out_$(basename "${f%.gdx}")"
done

echo
echo "=== done ==="
ls -la "$OUT" 2>/dev/null | tail -n +2
cat <<'NOTE'

If gdxdump is not available, the fallback is the same one that produced
coco2.csv — load the gdx in GAMS and write the parameter out, e.g.

    $gdxin res_17DE.gdx
    parameter DATA2(*,*,*,*,*);
    $load DATA2
    $gdxin
    file f /capreg_DATA2_DE.csv/;
    put f; put DATA2;

Whatever method produced coco2.csv will work here too.
NOTE
