"""copy_labour_biofuel_on_presult.gms (capri_mod/pipeline/captrd/step3_copies.py): labour from the activity levels and
the trends of GROF.LABO and GROF.LABN, the fossil fuels from the expert supports, INHA from p_data."""
import pytest

from capri_mod.pipeline.captrd import step3_copies as SC


def test_labour_fuels_and_inhabitants_copied_as_captrd():
    basm = {("SWHE", "LABT"): 20.0, ("SWHE", "LABF"): 12.0, ("SWHE", "LEVL"): 100.0,
            ("DCOL", "LABT"): 40.0, ("DCOL", "LABF"): 30.0, ("DCOL", "LEVL"): 50.0,
            ("GROF", "LABO"): 10.0, ("GROF", "LABN"): 5.0}
    step3 = {("SWHE", "LEVL"): 110.0, ("DCOL", "LEVL"): 40.0, ("GROF", "LABO"): 9.0, ("GROF", "LABN"): 4.0,
             ("HCOM", "DISL"): 0.0}
    s = SC.copy(step3, lambda c, w: basm.get((c, w), 0.0), ["SWHE", "DCOL"], ["SWHE", "DCOL"], ["DISL"],
                {("HCOM", "DISL"): 2500.0, ("HCOM", "SWHE"): 7.0}, 5900.0)
    # GROF's BASM: LABT 20 x 100 + 40 x 50 = 4000 x 0.001 = 4; LABF 1.2 + 1.5 = 2.7; LABP 4 - 2.7 = 1.3
    assert s[("GROF", "LABT")] == pytest.approx(4.0 * 9.0 / 10.0)
    assert s[("GROF", "LABP")] == pytest.approx(1.3 * 4.0 / 5.0)
    assert s[("GROF", "LABF")] == pytest.approx(s[("GROF", "LABT")] - s[("GROF", "LABP")])
    # each activity's coefficient scaled to the total: step1 LABF = (12 x 110 + 30 x 40) x 0.001 = 2.52
    assert s[("SWHE", "LABF")] == pytest.approx(12.0 * s[("GROF", "LABF")] / 2.52)
    assert s[("DCOL", "LABT")] == pytest.approx(s[("DCOL", "LABF")] + s.get(("DCOL", "LABP"), 0.0))   # no LABP coefficients: step1 0, not scaled
    assert s[("HCOM", "DISL")] == 2500.0 and ("HCOM", "SWHE") not in s
    assert s[("INHA", "LEVL")] == 5900.0
