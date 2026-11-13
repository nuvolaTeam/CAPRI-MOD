"""CAPRI's calibrated 2030 market state from a CAPMOD restart file (sim_ini) as CSV, for the move of the market onto
CAPRI's market regions (docs/design/MARKET_REGIONS_INVENTORY.md section 7 item 4: "the 2030 market is built from
sim_ini, extracted to CSV sources") and for the parity checks of the ports (MODEL_CONTENT_PLAN.md sections 1-2).

Source: the project lead's sim_ini_21730.gdx (the endotech Green Deal 2030 run with base year 2017, written at the
simulation start; the same file as capri_sources/reference/sets/simini_21730). The symbols written are listed, each with the
reason it is needed, in tools/build/simini_reference_symbols.csv; any other symbol can be added there.

Output (CAPRI's own data, read-only; capri_sources/reference/README.md):
  capri_sources/reference/simini/<tag>/<symbol>.csv.gz   parameters: d0, ..., dn, value, eps
                                                 variables:  d0, ..., dn, level, eps, lower, upper, marginal
  capri_sources/reference/simini/<tag>/_index.csv        symbol, kind, dim, domains, records, description
  capri_sources/reference/simini/<tag>/_acronyms.csv     number, name, description: the file's acronyms (a value
                                                 written as an acronym, e.g. an application type, is number x 1e301)

Values: written with repr (full precision). GAMS Eps is written as 0 with eps = 1 (for a variable, eps flags the level;
Eps in a bound or a marginal is written as 0). +INF and -INF are written as inf and -inf, NA as nan. A record CAPRI did
not store is absent. An undefined value (UNDF) stops the build.

    python tools/build/build_simini_reference.py --src sim_ini_21730.gdx --tag simini_21730 [--check OTHER.gdx]

--check compares every listed symbol with a second restart file (e.g. sim_ini_21730_1.gdx) record by record and
reports the differences; nothing is written for it.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _REFERENCE():
    """capri_sources/reference or $CAPRI_REFERENCE (tools/lib/paths.py)."""
    import sys as _s
    _s.path.insert(0, str(ROOT / "tools" / "lib"))
    from paths import REFERENCE
    return REFERENCE
# folder of libgdxcclib64.so (README section 3): --gdxlib or the environment variable CAPRI_GDXLIB
DEFAULT_GDXLIB = os.environ.get("CAPRI_GDXLIB", "")
SYMBOLS = ROOT / "tools" / "build" / "simini_reference_symbols.csv"


class _Gdx:
    def __init__(self, path: Path, gdxlib: str):
        import gams.core.gdx as g
        self.g = g
        self.h = g.new_gdxHandle_tp()
        ok, msg = g.gdxCreateD(self.h, gdxlib, g.GMS_SSSIZE)
        if not ok:
            raise RuntimeError(f"GDX library not loaded from {gdxlib!r}: {msg}")
        if not g.gdxOpenRead(self.h, str(path))[0]:
            raise RuntimeError(f"cannot open {path}")
        sv = g.doubleArray(g.GMS_SVIDX_MAX)
        g.gdxGetSpecialValues(self.h, sv)
        self.sv = {k: sv[getattr(g, f"GMS_SVIDX_{k}")] for k in ("EPS", "PINF", "MINF", "NA", "UNDEF")}

    def info(self, name: str):
        g = self.g
        ok, idx = g.gdxFindSymbol(self.h, name)
        if not ok:
            raise KeyError(f"{name} is not in the file")
        _, _, dim, typ = g.gdxSymbolInfo(self.h, idx)
        _, cnt, _, txt = g.gdxSymbolInfoX(self.h, idx)
        _, doms = g.gdxSymbolGetDomainX(self.h, idx)
        kind = {g.GMS_DT_PAR: "par", g.GMS_DT_VAR: "var"}.get(typ)
        if kind is None:
            raise ValueError(f"{name}: only parameters and variables are extracted")
        return idx, kind, dim, list(doms), cnt, txt

    def value(self, v: float, name: str):
        """(value as written, eps flag)."""
        sv = self.sv
        if v == sv["EPS"]:
            return 0.0, 1
        if v == sv["PINF"]:
            return math.inf, 0
        if v == sv["MINF"]:
            return -math.inf, 0
        if v == sv["NA"]:
            return math.nan, 0
        if v == sv["UNDEF"]:
            raise ValueError(f"{name}: an undefined value (UNDF) in the file")
        return v, 0

    def records(self, name: str):
        g = self.g
        idx, kind, *_ = self.info(name)
        _, n = g.gdxDataReadStrStart(self.h, idx)
        for _ in range(n):
            _, keys, vals, _ = g.gdxDataReadStr(self.h)
            lv, e = self.value(vals[g.GMS_VAL_LEVEL], name)
            if kind == "par":
                yield tuple(keys), (lv, e)
            else:
                rest = tuple(self.value(vals[k], name)[0]
                             for k in (g.GMS_VAL_LOWER, g.GMS_VAL_UPPER, g.GMS_VAL_MARGINAL))
                yield tuple(keys), (lv, e) + rest
        g.gdxDataReadDone(self.h)

    def acronyms(self) -> list[tuple]:
        """The file's acronyms: (number, name, text); a value written as an acronym is stored as number x 1e301."""
        out = []
        for i in range(1, self.g.gdxAcronymCount(self.h) + 1):
            _, name, text, number = self.g.gdxAcronymGetInfo(self.h, i)
            out.append((number, name, text))
        return out

    def close(self):
        self.g.gdxClose(self.h)


def _symbols(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    names = [r["symbol"] for r in rows]
    if len(set(n.lower() for n in names)) != len(names):
        raise ValueError(f"{path}: a symbol listed twice")
    return rows


def _fmt(v: float) -> str:
    return repr(float(v))


def write(src: Path, tag: str, gdxlib: str, symbols: Path) -> None:
    out = _REFERENCE() / "simini" / tag
    out.mkdir(parents=True, exist_ok=True)
    gdx = _Gdx(src, gdxlib)
    index = []
    for row in _symbols(symbols):
        name = row["symbol"]
        _, kind, dim, doms, cnt, txt = gdx.info(name)
        if kind != row["kind"]:
            raise ValueError(f"{name}: listed as {row['kind']}, the file has a {kind}")
        head = [f"d{k}" for k in range(dim)] + (["value", "eps"] if kind == "par"
                                                  else ["level", "eps", "lower", "upper", "marginal"])
        n = 0
        with gzip.open(out / f"{name}.csv.gz", "wt", newline="", encoding="utf-8", compresslevel=6) as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(head)
            for keys, vals in gdx.records(name):
                w.writerow(list(keys) + [_fmt(vals[0]), vals[1]] + [_fmt(v) for v in vals[2:]])
                n += 1
        if n != cnt:
            raise RuntimeError(f"{name}: {n} records written, the file declares {cnt}")
        index.append((name, kind, dim, " ".join(doms), n, txt))
        print(f"{name}: {n} records")
    with open(out / "_acronyms.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["number", "name", "description"])
        w.writerows(sorted(gdx.acronyms()))
    gdx.close()
    with open(out / "_index.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["symbol", "kind", "dim", "domains", "records", "description"])
        w.writerows(index)
    print(f"{len(index)} symbols -> {out}")


def check(src: Path, other: Path, gdxlib: str, symbols: Path) -> int:
    a, b = _Gdx(src, gdxlib), _Gdx(other, gdxlib)
    bad = 0
    for row in _symbols(symbols):
        name = row["symbol"]
        ra = dict(a.records(name))
        rb = dict(b.records(name))
        keys = set(ra) | set(rb)
        diff = [k for k in keys if k not in ra or k not in rb
                or any(not (x == y or (math.isnan(x) and math.isnan(y))) for x, y in zip(ra[k], rb[k]))]
        if diff:
            bad += 1
            k = sorted(diff)[0]
            print(f"{name}: {len(diff)} of {len(keys)} records differ, e.g. {k}: {ra.get(k)} vs {rb.get(k)}")
        else:
            print(f"{name}: identical ({len(keys)} records)")
    a.close()
    b.close()
    return bad


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True)
    ap.add_argument("--tag")
    ap.add_argument("--check", help="a second restart file to compare with, record by record")
    ap.add_argument("--symbols", default=str(SYMBOLS))
    ap.add_argument("--gdxlib", default=DEFAULT_GDXLIB)
    args = ap.parse_args()
    if args.check:
        raise SystemExit(1 if check(Path(args.src), Path(args.check), args.gdxlib, Path(args.symbols)) else 0)
    if not args.tag:
        ap.error("--tag is needed to write")
    write(Path(args.src), args.tag, args.gdxlib, Path(args.symbols))


if __name__ == "__main__":
    main()
