"""CAPTRD-MOD: CAPRI's baseline projection (CAPTRD, CAPRI star 3.0 gams/captrd.gms), ported from the GAMS code.

Modules
    timesets  CAPTRD's time sets: ExPost(T), ExAnte, BASYRS5/M, EIGHTLST, BAST, YearsEst (captrd.gms l. 203-271,
              665-812)
    step1     the trend estimator x = a + b*t^c and its statistics (estimate_trends.gms,
              prep_data_for_estimation.gms l. 205-247, define_stats_and_supports.gms l. 44-49, 113-132, 177-179)
    supports  the supports from Step 1 and the stored error variance (define_stats_and_supports.gms l. 186-330)

Parity references (CAPRI's own files, read by the tests only): capri_reference/capreg_tseries (CAPREG's time series)
and capri_reference/captrd_results (CAPTRD's p_result), built by tools/build/build_capreg_tseries_reference.py and
tools/build/build_captrd_results_reference.py. Design and status: docs/design/CAPTRD_MOD.md section 12.
"""
