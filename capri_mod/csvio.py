"""CSV reading and writing to the last digit.

pandas' default CSV float parser is fast but not exact: about two thirds of the values of a full-precision file come
back one unit in the last place off (KNOWN_ISSUES K82). Every CSV the model and its builders read goes through
`read_csv`, which parses floats exactly ("round_trip"); every CSV they write goes through `to_csv`, which writes each
float with the 17 significant digits that give it back exactly. CAPRI's values (GDX doubles) then reach the model as
they are.
"""
from __future__ import annotations

import pandas as pd


def read_csv(path, *args, **kwargs) -> pd.DataFrame:
    """pandas.read_csv with floats parsed exactly (float_precision="round_trip")."""
    kwargs.setdefault("float_precision", "round_trip")
    return pd.read_csv(path, *args, **kwargs)


def to_csv(df, path, **kwargs) -> None:
    """DataFrame.to_csv with floats written in full (repr: 17 significant digits where needed)."""
    kwargs.pop("float_format", None)
    df.to_csv(path, **kwargs)
