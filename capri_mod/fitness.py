"""Look up how far a model output can be trusted.

Every other file in ``capri_data`` says where an INPUT came from. This one says
how far an OUTPUT can be relied on, so a caller can check a number before
reporting it rather than depending on someone having read the README.

    >>> from capri_mod.fitness import check
    >>> check("scenario.permanent_crops").status
    'overstated'
    >>> check("supply.gross_margin").ok
    True

Lookup is most-specific-first: ``scenario.permanent_crops`` is consulted before
``scenario``, and ``activities.WINE`` before ``activities``. An unknown key
returns status ``unknown`` — which means no finding is recorded, NOT that the
output is validated. That distinction is deliberate: silence is not a clean bill
of health.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "capri_data" / "FITNESS_FOR_USE.json"

#: statuses whose numbers can be reported as levels without a caveat
_CLEAN = {"validated"}
#: statuses where the number should not be used at all
_UNUSABLE = {"not_supported"}


@dataclass(frozen=True)
class Fitness:
    """What is recorded about one output."""

    key: str                      #: the key that matched, which may be a parent
    status: str
    note: str = ""
    scope: str = ""
    reference: str = ""
    evidence: str = ""
    ratio_vs_reference: Optional[float] = None

    @property
    def ok(self) -> bool:
        """True only for outputs recorded as validated."""
        return self.status in _CLEAN

    @property
    def usable(self) -> bool:
        """True unless the model cannot answer the question at all.

        ``overstated`` and ``understated`` are usable: the direction and the
        ranking hold, the level does not.
        """
        return self.status not in _UNUSABLE

    def caveat(self) -> str:
        """One line to carry alongside the number, empty when validated."""
        if self.ok or not self.note:
            return ""
        scope = f" [{self.scope}]" if self.scope else ""
        return f"{self.status}{scope}: {self.note}"


@lru_cache(maxsize=4)
def _load(path: str) -> Dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check(output: str, path: Path | str | None = None) -> Fitness:
    """Fitness of one output, falling back to its parent keys.

    ``output`` is a dotted key such as ``"scenario.oilseeds"`` or
    ``"environmental.n_surplus.IE"``.
    """
    doc = _load(str(path or DEFAULT_PATH))
    entries = doc.get("outputs", {})
    parts = output.split(".")
    for i in range(len(parts), 0, -1):
        key = ".".join(parts[:i])
        if key in entries:
            e = entries[key]
            return Fitness(key=key, status=e.get("status", "unknown"),
                           note=e.get("note", ""), scope=e.get("scope", ""),
                           reference=e.get("reference", ""),
                           evidence=e.get("evidence", ""),
                           ratio_vs_reference=e.get("ratio_vs_reference"))
    return Fitness(key=output, status="unknown",
                   note="no finding recorded; this is not a statement that the "
                        "output is validated")


def caveats(outputs: List[str], path: Path | str | None = None) -> Dict[str, str]:
    """Caveats for several outputs at once; validated ones are omitted.

    Intended for the end of a run: pass what you are about to report and print
    whatever comes back.
    """
    out = {}
    for o in outputs:
        c = check(o, path).caveat()
        if c:
            out[o] = c
    return out


def unusable(outputs: List[str], path: Path | str | None = None) -> List[str]:
    """Those of ``outputs`` the model cannot answer, in the order given."""
    return [o for o in outputs if not check(o, path).usable]
