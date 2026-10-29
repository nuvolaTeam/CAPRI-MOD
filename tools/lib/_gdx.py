"""Reading a symbol of a CAPRI GDX file with GAMS's GDX library (gams.core.gdx; libgdxcclib64.so, README section 3).

    from _gdx import read_symbol
    rows = read_symbol(path, "p_landscapeTargets", gdxlib)      # [(key1, ..., value), ...], EPS as 0.0

The library's folder: the argument, else the environment variable CAPRI_GDXLIB.
"""
from __future__ import annotations

import os
from pathlib import Path


def read_symbol(path, name: str, gdxlib: str | None = None) -> list[tuple]:
    """The records of symbol name in the GDX file path: (keys..., level value), EPS as 0.0; UNDF and NA raise."""
    import gams.core.gdx as g
    lib = gdxlib or os.environ.get("CAPRI_GDXLIB", "")
    h = g.new_gdxHandle_tp()
    ok, msg = g.gdxCreateD(h, lib, g.GMS_SSSIZE)
    if not ok:
        raise RuntimeError(f"GDX library not loaded from {lib!r}: {msg}")
    try:
        if not g.gdxOpenRead(h, str(Path(path)))[0]:
            raise RuntimeError(f"cannot open {path}")
        ok, idx = g.gdxFindSymbol(h, name)
        if not ok:
            raise KeyError(f"{path}: no symbol {name}")
        sv = g.doubleArray(g.GMS_SVIDX_MAX)
        g.gdxGetSpecialValues(h, sv)
        eps, undf, na = sv[g.GMS_SVIDX_EPS], sv[g.GMS_SVIDX_UNDEF], sv[g.GMS_SVIDX_NA]
        _, n = g.gdxDataReadStrStart(h, idx)
        out = []
        for _ in range(n):
            _, keys, vals, _ = g.gdxDataReadStr(h)
            v = vals[g.GMS_VAL_LEVEL]
            if v == eps:
                v = 0.0
            elif v in (undf, na):
                raise ValueError(f"{path}: special value {v} at {keys}")
            out.append((*keys, float(v)))
        g.gdxDataReadDone(h)
        g.gdxClose(h)
        return out
    finally:
        g.gdxFree(h)
