"""The results browser's reading layer (capri_gradio/results_browser.py): read-only over a results store.

A results store (the run script's run.results_dir; capri_mod/io_results.py) holds
  runs/                 one record per stored run (a reference's or a scenario's), its run id the SHA-256 of its
                        results and its definition (io_results.run_id_of)
  long/                 the results in CAPRI's DATAOUT layout, scenario and run_id as columns (not partitioned)
  summary/, iterations/ the run script's EU summaries and the outer iterations' records (encode_record's rows)
  meta/<run id>/        meta.json, settings.toml, manifest.json
The page shows a run id's first ID_SHOWN characters; a unique prefix names a run.
This module turns them into the tables the browser shows; it writes nothing. The comparisons with CAPRI use the check
tools' own code and references (tools/check/compare_baseline_capri.py, tools/check/compare_runs.py), so the browser
shows the same numbers they print.
"""
from __future__ import annotations

import importlib.util
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
__import__("sys").path.insert(0, str(ROOT))
from capri_mod import io_results as IO  # noqa: E402

#: the dimensions of a stored row a view can filter on and pivot by, with the browser's names for them
DIMS = {"region": "region", "rows": "item (rows)", "cols": "column (cols)", "dim5": "dim5"}
#: the values a view can show for a scenario run
MEASURES = ("scenario", "baseline", "scenario - baseline", "% change")


def default_store() -> Path:
    """The store the run script writes to: the setting run.results_dir, relative to the repository's root."""
    from capri_mod.settings import current
    d = str(current().get("run.results_dir") or "results")
    return Path(d) if Path(d).is_absolute() else ROOT / d


# --------------------------------------------------------------------------- #
# Runs and their metadata
# --------------------------------------------------------------------------- #
def _full(root, scenario: str, run_id: str) -> str:
    """A scenario run's whole id from a unique prefix (the labels' ID_SHOWN characters)."""
    return run_id if len(run_id) == 64 else run_record(root, scenario, run_id)["run_id"]


def read_meta(root, scenario: str, run_id: str) -> dict:
    p = IO.meta_dir(root, _full(root, scenario, run_id)) / "meta.json"
    return json.loads(p.read_text()) if p.is_file() else {}


def read_settings(root, scenario: str, run_id: str) -> str:
    p = IO.meta_dir(root, _full(root, scenario, run_id)) / "settings.toml"
    return p.read_text() if p.is_file() else ""


def _flat_text(d) -> str:
    """A settings or overrides record as "key=value" text ("" when empty)."""
    if not d:
        return ""
    out = []

    def walk(x, pre):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{pre}.{k}" if pre else str(k))
        else:
            out.append(f"{pre}={x}")
    walk(d, "")
    return "; ".join(out)


def runs(root) -> pd.DataFrame:
    """The store's scenario runs, newest first, with their convergence, settings changed and code version."""
    r = IO._runs(Path(root))
    if r.empty:
        return pd.DataFrame(columns=["seq", "created", "result name", "label", "series", "status", "scenario", "run_id", "reference", "reference_run_id",
                                     "converged", "market converged", "base iterations", "iterations", "seconds",
                                     "regions", "settings changed", "overrides", "commit", "note"])
    rows = []
    # CAPRI-style result names and the solve status (io_results.catalogue: given afterwards to earlier runs)
    cat = IO.catalogue(Path(root)).set_index("run_id")
    for rec in r[r["kind"] == "scenario"].sort_values("seq", ascending=False).to_dict("records"):
        m = read_meta(root, rec["scenario"], rec["run_id"])
        c = cat.loc[str(rec["run_id"])[:12]] if str(rec["run_id"])[:12] in cat.index else {}
        mc = m.get("market_converged") or {}
        reg = str((m.get("options") or {}).get("regions") or "")
        git = ((m.get("run_manifest") or {}).get("git") or {})
        rows.append({"seq": int(rec["seq"]), "created": rec["created"],
                     "result name": c.get("result_name", "") if len(c) else "", "label": rec.get("label") or "",
                     "series": rec.get("series") or "", "status": c.get("status", "") if len(c) else "",
                     "scenario": rec["scenario"],
                     "run_id": rec["run_id"], "reference": rec["reference"],
                     "reference_run_id": rec["reference_run_id"], "converged": m.get("conv"),
                     "market converged": "/".join(str(mc.get(k, "")) for k in ("baseline", "scenario")) if mc else "",
                     "base iterations": m.get("base_iterations"), "iterations": m.get("it"),
                     "seconds": m.get("seconds"),
                     "regions": len([x for x in reg.split(",") if x]) or "all",
                     "settings changed": _flat_text(m.get("settings_changed")),
                     "overrides": _flat_text(m.get("scenario_overrides")),
                     "commit": (f"{str(git.get('commit', ''))[:7]} {git.get('branch') or ''}".strip()
                                + (f" +{len(git.get('changed_files') or [])} changed"
                                   if git.get("changed_files") else "")),
                     "note": rec.get("note") or ""})
    return pd.DataFrame(rows)


#: the characters of a run id shown in the page's labels (a unique prefix names a run, as a git commit's)
ID_SHOWN = 12


def run_label(scenario: str, run_id: str) -> str:
    return f"{scenario} | {run_id[:ID_SHOWN]}"


def parse_label(label: str) -> tuple:
    s, r = label.split(" | ")
    return s.strip(), r.strip()


def run_record(root, scenario: str, run_id: str) -> dict:
    """A scenario run's record, by its id or a unique prefix of it (the labels show ID_SHOWN characters)."""
    r = IO._runs(Path(root))
    r = r[(r["scenario"] == scenario) & (r["run_id"].astype(str).str.startswith(run_id)) & (r["kind"] == "scenario")]
    if len(r) != 1:
        raise KeyError(f"{root}: {len(r)} stored scenario runs {scenario} {run_id}")
    return r.iloc[0].to_dict()


def run_summary(root, scenario: str, run_id: str) -> dict:
    """The run's metadata worth reading first: convergence, solver fallbacks, settings changed, the code version."""
    m = read_meta(root, scenario, run_id)
    keep = ("conv", "it", "base_iterations", "seconds", "market_converged", "capri_stop", "settings_changed",
            "scenario_overrides", "nlp_fallback", "nlp_relaxed", "nlp_nonoptimal", "market_calibration_bound_hits",
            "nor_price_gap", "pmp_source", "market_supply_hessian")
    out = {k: m[k] for k in keep if k in m}
    opt = m.get("options") or {}
    out["options"] = {k: v for k, v in opt.items() if v not in (None, "", False)}
    man = m.get("run_manifest") or {}
    out["run_manifest"] = {"created": man.get("created"), "git": {k: v for k, v in (man.get("git") or {}).items()
                                                                if k in ("commit", "branch", "changed_files")}}
    return out


# --------------------------------------------------------------------------- #
# The outer iterations
# --------------------------------------------------------------------------- #
#: the convergence measures of an outer iteration (capri_mod/model.py, outer_history[...]["conv"])
CONV_MEASURES = {"last_change": "largest price change since the last iteration",
                 "gap": "largest gap of the price signal to its target",
                 "capri.max": "CAPRI's stop test (capmod/price_forecast.gms): largest change of a member state's "
                              "production, feed use or price since the last iteration, %",
                 "yani": "young animals' market imbalance",
                 "nbal": "largest nitrogen-balance price update",
                 "pool": "manure pool imbalance",
                 "cal": "market calibration residual"}


def _iter_record(root, scenario: str, run_id: str) -> list:
    rec = IO._record(root, "iterations", scenario, run_id)
    return rec if isinstance(rec, list) else []


def iterations(root, scenario: str, run_id: str) -> pd.DataFrame:
    """The baseline's and the scenario's outer iterations, one row per iteration and convergence measure (long, for a
    line chart): point, it, measure, value."""
    rec = run_record(root, scenario, run_id)
    rows = []
    for point, (s, r) in (("baseline", (rec["reference"], rec["reference_run_id"])),
                          ("scenario", (scenario, rec["run_id"]))):
        for x in _iter_record(root, s, r):
            c = x.get("conv") or {}
            vals = {k: c.get(k) for k in CONV_MEASURES if "." not in k}
            vals["capri.max"] = (c.get("capri") or {}).get("max")
            for k, v in vals.items():
                if isinstance(v, (int, float)) and np.isfinite(v):
                    rows.append({"point": point, "it": int(x.get("it", 0)), "measure": k, "value": float(v)})
    return pd.DataFrame(rows, columns=["point", "it", "measure", "value"])


# --------------------------------------------------------------------------- #
# Results: one run's scenario against its baseline, two runs against each other
# --------------------------------------------------------------------------- #
_KEY = ["block", "region", "dim5", "cols", "rows"]


@lru_cache(maxsize=8)
def _partition(root: str, scenario: str, run_id: str) -> pd.DataFrame:
    return IO.read_partition(root, scenario, run_id)


def points(root, scenario: str, run_id: str) -> tuple:
    """(baseline rows, scenario rows) of a stored scenario run."""
    rec = run_record(root, scenario, run_id)
    return (_partition(str(root), rec["reference"], rec["reference_run_id"]),
            _partition(str(root), scenario, rec["run_id"]))


def _filtered(df: pd.DataFrame, block: Optional[str], filters: dict) -> pd.DataFrame:
    if block:
        df = df[df["block"] == block]
    for dim, vals in (filters or {}).items():
        if vals:
            df = df[df[dim].isin(list(vals))]
    return df


def choices(df: pd.DataFrame, block: Optional[str], filters: dict, dim: str) -> list:
    """The values of a dimension left after the block and the OTHER dimensions' filters."""
    other = {k: v for k, v in (filters or {}).items() if k != dim}
    return sorted(map(str, _filtered(df, block, other)[dim].unique()))


def joined(a: pd.DataFrame, b: pd.DataFrame, block: Optional[str], filters: dict) -> pd.DataFrame:
    """Two sets of rows matched on block, region, dim5, cols and rows: a, b, b - a and the % change (b / a - 1, NaN
    where a is 0). A row in one set only keeps NaN on the other side."""
    a_, b_ = _filtered(a, block, filters), _filtered(b, block, filters)
    m = a_[_KEY + ["unit", "value"]].merge(b_[_KEY + ["unit", "value"]], on=_KEY, how="outer",
                                           suffixes=("_a", "_b"))
    m["unit"] = m["unit_a"].fillna(m["unit_b"]).fillna("")
    m = m.drop(columns=["unit_a", "unit_b"]).rename(columns={"value_a": "a", "value_b": "b"})
    m["b - a"] = m["b"] - m["a"]
    with np.errstate(divide="ignore", invalid="ignore"):
        m["% change"] = np.where(m["a"].abs() > 0, (m["b"] / m["a"] - 1.0) * 100.0, np.nan)
    return m.sort_values(_KEY).reset_index(drop=True)


def scenario_vs_baseline(root, scenario: str, run_id: str, block: Optional[str], filters: dict) -> pd.DataFrame:
    base, scen = points(root, scenario, run_id)
    return joined(base, scen, block, filters).rename(
        columns={"a": "baseline", "b": "scenario", "b - a": "scenario - baseline"})


def pivot(df: pd.DataFrame, measure: str, row_dim: str, col_dim: str) -> pd.DataFrame:
    """A joined table as CAPRI's GUI shows it: one dimension down, one across, one measure in the cells. The cells
    are single stored rows: the other dimensions must be fixed by the filters, else the view says so (no sums: units
    and prices do not add up)."""
    if df.empty:
        return pd.DataFrame()
    keys = [row_dim] + ([col_dim] if col_dim and col_dim != row_dim else [])
    dup = df.duplicated(keys, keep=False)
    if dup.any():
        free = [d for d in DIMS if d not in keys and df[d].nunique() > 1]
        raise ValueError("several stored rows per cell: fix " + ", ".join(DIMS[d] for d in free)
                         + " with a filter, or pivot by it")
    if len(keys) == 1:
        return df.set_index(row_dim)[[measure]]
    return df.pivot(index=row_dim, columns=col_dim, values=measure)


def compare_runs(root_a, label_a: str, point_a: str, root_b, label_b: str, point_b: str,
                 block: Optional[str], filters: dict) -> pd.DataFrame:
    """Two stored runs' rows (each its baseline or its scenario) matched: A, B, B - A, % change."""
    sa, ra = parse_label(label_a)
    sb, rb = parse_label(label_b)
    a = points(root_a, sa, ra)[0 if point_a == "baseline" else 1]
    b = points(root_b, sb, rb)[0 if point_b == "baseline" else 1]
    return joined(a, b, block, filters).rename(columns={"a": "A", "b": "B", "b - a": "B - A"})


def deviation_summary(df: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    """Per block and column (cols): rows matched, rows in one run only, rows that differ, the largest and the median
    absolute relative difference (|b - a| / max(|a|, |b|), 0 where both are 0)."""
    if df.empty:
        return pd.DataFrame()
    x = df.copy()
    both = x[a].notna() & x[b].notna()
    den = np.maximum(x[a].abs(), x[b].abs())
    with np.errstate(divide="ignore", invalid="ignore"):
        x["rel"] = np.where(den > 0, (x[b] - x[a]).abs() / den, 0.0)
    x["both"], x["differ"] = both, both & (x[a] != x[b])
    g = x.groupby(["block", "cols"], dropna=False)
    out = pd.DataFrame({"rows matched": g["both"].sum(), "one run only": g["both"].apply(lambda s: int((~s).sum())),
                        "rows differing": g["differ"].sum(),
                        "max |rel diff| %": g.apply(lambda d: d.loc[d["both"], "rel"].max() * 100,
                                                    include_groups=False),
                        "median |rel diff| %": g.apply(lambda d: d.loc[d["both"], "rel"].median() * 100,
                                                       include_groups=False)})
    return out.reset_index().sort_values("max |rel diff| %", ascending=False, na_position="last")


# --------------------------------------------------------------------------- #
# Against CAPRI: the check tools' comparisons, on a stored run
# --------------------------------------------------------------------------- #
def _tool(name: str):
    spec = importlib.util.spec_from_file_location(f"_check_{name}", ROOT / "tools" / "check" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _loaded(root, scenario: str, run_id: str) -> dict:
    return IO.load_store(str(root), scenario, run_id)


def baseline_vs_capri(root, scenario: str, run_id: str) -> pd.DataFrame:
    """tools/check/compare_baseline_capri.py on the run: the model's 2030 baseline against CAPRI's own 2030 reference
    (EU27 activity levels, market production and domestic use; prices as relative structure)."""
    o = _loaded(root, scenario, run_id)
    if not o.get("base_market"):
        return pd.DataFrame()
    rows = _tool("compare_baseline_capri").rows(o)
    df = pd.DataFrame(rows, columns=["block", "model code", "CAPRI code", "model", "CAPRI"])
    df["dev %"] = (df["model"] / df["CAPRI"] - 1.0) * 100.0
    return df


def jrc_indicators(root, labels: Sequence[str]) -> pd.DataFrame:
    """tools/check/compare_runs.py's indicators (% change from the baseline, EU27) for one or more runs, beside the
    Farm-to-Fork figures JRC121368 published from CAPRI."""
    cr = _tool("compare_runs")
    cols = {}
    for lab in labels:
        s, r = parse_label(lab)
        cols[lab] = cr.indicators(_loaded(root, s, r))
    df = pd.DataFrame(cols)
    df["JRC121368 (CAPRI)"] = pd.Series(cr.CAPRI)
    df.index.name = "indicator"
    return df.reset_index()


# --------------------------------------------------------------------------- #
# Maps and member-state charts: the regional units' results on NUTS 2024
# --------------------------------------------------------------------------- #
#: units of stored rows whose values add up over regions (areas, heads, quantities, emissions, money, hours); a row of
#: another unit, or of none recorded, is never summed: where a map or a member-state bar would need a sum of it, the
#: value is left empty
ADDITIVE_UNIT_PREFIXES = ("1000 ha", "1000 t", "1000 heads", "kt", "t ", "EUR 1000", "EUR million", "million hours")


def additive(unit: str) -> bool:
    u = str(unit or "")
    return any(u.startswith(p) for p in ADDITIVE_UNIT_PREFIXES)


@lru_cache(maxsize=1)
def nuts_mapping() -> pd.DataFrame:
    """CAPRI's regional units linked to NUTS-2024 regions (capri_mod/nuts_reporting.py): capri_unit, nuts2024, group,
    weight (the region's share of its group's utilised agricultural area)."""
    from capri_mod import nuts_reporting as NR
    return NR.load_mapping()


@lru_cache(maxsize=1)
def nuts_geometry() -> dict:
    """The NUTS-2024 level-2 boundaries (capri_gradio/geo/nuts2024_level2.csv, Eurostat GISCO) as a GeoJSON
    FeatureCollection with id = NUTS code."""
    g = pd.read_csv(Path(__file__).resolve().parent / "geo" / "nuts2024_level2.csv")
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "id": r.nuts_id, "properties": {"name": r.name, "country": r.country},
                          "geometry": json.loads(r.geometry)} for r in g.itertuples()]}


def unit_values(root, scenario: str, run_id: str, block: str, cols: str, rows: str, dim5: str = "") -> pd.DataFrame:
    """One stored item for every regional unit of a run: capri_unit, unit (of measure), baseline, scenario."""
    units = set(nuts_mapping()["capri_unit"])
    j = scenario_vs_baseline(root, scenario, run_id, block,
                             {"cols": [cols], "rows": [rows], "dim5": [dim5]})
    j = j[j["region"].isin(units)]
    return j.rename(columns={"region": "capri_unit"})[["capri_unit", "unit", "baseline", "scenario"]]


def _measure(base, scen, measure):
    if measure == "baseline":
        return base
    if measure == "scenario":
        return scen
    if measure == "scenario - baseline":
        return scen - base
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(np.abs(base) > 0, (scen / base - 1.0) * 100.0, np.nan)


def map_frame(values: pd.DataFrame, measure: str) -> pd.DataFrame:
    """The unit values on NUTS-2024 regions: nuts2024, value, units (the CAPRI units it comes from), note.
    - a group of one unit: its value; for an additive item a level (baseline, scenario, change) is split by the
      region's weight, a % change is the unit's;
    - a group of several units: the group's sum for an additive item (split as above), else empty (a mean of rates,
      prices or shares would need weights this table does not hold)."""
    m = nuts_mapping()
    v = values.set_index("capri_unit")
    add = bool(len(values)) and additive(values["unit"].iloc[0])
    out = []
    for gid, g in m.groupby("group"):
        us = sorted(set(g["capri_unit"]) & set(v.index))
        regs = g.drop_duplicates("nuts2024")
        if not us:
            continue
        note = ""
        if len(us) == 1:
            b, s = float(v.at[us[0], "baseline"]), float(v.at[us[0], "scenario"])
        elif add:
            b, s = float(v.loc[us, "baseline"].sum()), float(v.loc[us, "scenario"].sum())
            note = "sum of " + ", ".join(us)
        else:
            b = s = float("nan")
            note = f"{len(us)} units, item not additive: no value"
        val = float(_measure(np.array(b), np.array(s), measure))
        for r in regs.itertuples():
            share = r.weight if (add and measure != "% change" and len(regs) > 1) else 1.0
            out.append({"nuts2024": r.nuts2024, "value": val * share, "units": ", ".join(us),
                        "note": note + (f"; {share:.0%} of the group (UAA weight)" if share != 1.0 else "")})
    return pd.DataFrame(out, columns=["nuts2024", "value", "units", "note"])


def member_state_frame(values: pd.DataFrame, measure: str) -> pd.DataFrame:
    """The unit values summed by CAPRI member state (the units' first two letters) for an additive item:
    member_state, baseline, scenario, value; empty for an item that does not add up."""
    if values.empty or not additive(values["unit"].iloc[0]):
        return pd.DataFrame(columns=["member_state", "baseline", "scenario", "value"])
    ms = (values.assign(member_state=values["capri_unit"].str[:2])
          .groupby("member_state")[["baseline", "scenario"]].sum())
    ms["value"] = _measure(ms["baseline"].to_numpy(float), ms["scenario"].to_numpy(float), measure)
    return ms.reset_index()


def regional_items(root, scenario: str, run_id: str) -> pd.DataFrame:
    """The items a run holds for every regional unit: block, cols, rows, dim5, unit, additive."""
    base, scen = points(root, scenario, run_id)
    units = set(nuts_mapping()["capri_unit"])
    s = scen[scen["region"].isin(units)]
    it = s.groupby(["block", "cols", "rows", "dim5"], dropna=False).agg(unit=("unit", "first"),
                                                                        n=("region", "nunique")).reset_index()
    it["additive"] = it["unit"].map(additive)
    return it[it["n"] >= 2].drop(columns="n")
