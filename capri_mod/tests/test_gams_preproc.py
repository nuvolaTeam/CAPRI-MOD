"""tools/lib/gams_preproc.py: the GAMS compile-time branches it selects."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))

from gams_preproc import preprocess  # noqa: E402

SRC = """\
$setlocal glo_scen euclimit7
$setlocal glo_scen bright
$iftheni.a %glo_scen%==euclimit7
a = 1;
$elseifi.a %glo_scen%==Bright
b = 2;
$else.a
c = 3;
$endif.a
$ifi %glo_scen%==bright $setlocal file f_%glo_scen%
$ifthene.n "%n%>52"
big;
$endif.n
$if not setlocal missing d = 4;
$ontext
skipped;
$offtext
p(r) $ x(r)
  $ y(r) = 1;
* comment
$ifi exist "x.gdx" e = 5;
load "%file%";
"""


def test_branches_variables_and_conditions():
    r = preprocess(SRC, {"n": "58"})
    code = [s for _, s in r.lines]
    assert "a = 1;" not in code and "b = 2;" in code and "c = 3;" not in code
    assert "big;" in code and "d = 4;" in code and "skipped;" not in code
    assert "  $ y(r) = 1;" in code                       # an indented $ is a condition, not a compile command
    assert "* comment" in code                           # comments kept, so line numbers stay the source's
    assert 'load "f_bright";' in code
    assert r.undecided and "exist" in r.undecided[0][1]  # undecidable conditions reported and taken as false
    assert "e = 5;" not in code
    assert dict(r.lines)[6] == "b = 2;"                  # line numbers of the source
