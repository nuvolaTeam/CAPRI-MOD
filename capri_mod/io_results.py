"""
Result storage for CAPRI-Python.

The model's run() returns results in memory. This module persists them to a
conventional, git-ignored `outputs/` tree so that runs are reproducible,
auditable, and directly usable for batch / sensitivity analysis.

Layout
------
outputs/                          (git-ignored; created on demand)
  <experiment>/                   a named study, e.g. "sensitivity_biofuel"
    manifest.json                 what/when/model+data version, run count
    runs/
      <run_id>/                   one self-contained model run
        summary.json              scenario, sampled inputs, scalar outputs
        market_world_prices.csv
        market_production.csv
        market_consumption.csv
        market_trade_flows.csv
        supply_activities.csv     region x activity levels
        supply_indicators.csv     region x (gross_margin, ghg, n_balance, ...)
        feed.csv / environmental.csv   (when those modules ran)
    batch_summary.csv             ALL runs, one row each — the analysis table

Typical use
-----------
    exp = Experiment("sensitivity_biofuel")          # -> outputs/sensitivity_biofuel/
    for i, mandate in enumerate(mandates):
        r = model.run(..., biofuel_output_scale={"BIOD": scale})
        exp.save_run(r, run_id=f"run_{i:04d}", inputs={"biodiesel_output_scale": scale})
    exp.finalise()                                    # writes batch_summary.csv
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from capri_mod.data.definitions import is_eu

DEFAULT_OUTPUT_ROOT = "outputs"


# --------------------------------------------------------------------------- #
# Flattening: one run -> one flat record of scalar outputs
# --------------------------------------------------------------------------- #
def flatten_outputs(results: dict) -> dict:
    """Reduce a run to a flat dict of scalar output indicators.

    This is the natural unit for sensitivity analysis: one record per run.
    Keys are prefixed by block: 'price_<comm>' (world prices), 'price_EU27_<comm>' and 'prod_EU27_<comm>' (the EU's
    market price and production, 1000 t; Norway apart: 'price_NOR_<comm>', 'prod_NOR_<comm>'), 'env_EU_<indicator>'
    (EU totals of the environmental accounts: GHG in kt CO2-eq, NH3 in kt, N in t, P in t P2O5, organic area in
    1000 ha; Norway's regions apart: 'env_NO_<indicator>'), 'supply_total_gross_margin' (EUR 1000), 'biofuel_*' (with run_biofuel=True),
    'market_converged', 'outer_converged'.
    """
    out: dict = {}

    mkt = results.get("market")
    if mkt is not None:
        wp = getattr(mkt, "world_prices", None)
        if wp is not None:
            for c, v in dict(wp).items():
                try:
                    out[f"price_{c}"] = float(v)
                except (TypeError, ValueError):
                    pass
        prod = getattr(mkt, "production", None)
        if prod is not None and hasattr(prod, "items") and not hasattr(prod, "ndim"):
            for c, v in dict(prod).items():
                try:
                    out[f"prod_{c}"] = float(v)
                except (TypeError, ValueError):
                    pass
        elif prod is not None and hasattr(prod, "loc") and "EU27" in getattr(prod, "index", []):
            # the market's production table (trade region x commodity, 1000 t): the EU's row
            for c, v in prod.loc["EU27"].items():
                try:
                    out[f"prod_EU27_{c}"] = float(v)
                except (TypeError, ValueError):
                    pass
        if prod is not None and hasattr(prod, "loc") and "NO000000" in getattr(prod, "index", []):
            # Norway's market region (its supply models' output; not part of the EU's, KNOWN_ISSUES K56)
            for c, v in prod.loc["NO000000"].items():
                try:
                    out[f"prod_NOR_{c}"] = float(v)
                except (TypeError, ValueError):
                    pass
        dom = getattr(mkt, "domestic_prices", None)
        if dom is not None and hasattr(dom, "loc") and "EU27" in getattr(dom, "index", []):
            for c, v in dom.loc["EU27"].items():
                try:
                    out[f"price_EU27_{c}"] = float(v)
                except (TypeError, ValueError):
                    pass
        if dom is not None and hasattr(dom, "loc") and "NO000000" in getattr(dom, "index", []):
            for c, v in dom.loc["NO000000"].items():
                try:
                    out[f"price_NOR_{c}"] = float(v)
                except (TypeError, ValueError):
                    pass
        welfare = getattr(mkt, "welfare", None)
        if welfare is not None and not hasattr(welfare, "__len__"):
            try:
                out["market_welfare"] = float(welfare)
            except (TypeError, ValueError):
                pass
        out["market_converged"] = bool(getattr(mkt, "converged", False))
        out["market_iterations"] = int(getattr(mkt, "iterations", 0) or 0)

    bio = results.get("biofuel")
    if bio is not None:
        out["biofuel_bioethanol_kt"] = float(getattr(bio, "bioethanol_kt", 0) or 0)
        out["biofuel_biodiesel_kt"] = float(getattr(bio, "biodiesel_kt", 0) or 0)
        for k, x in (getattr(bio, "feedstock_demand", None) or {}).items():
            out[f"biofuel_feedstock_{k}_kt"] = float(x)

    sup = results.get("supply")
    if isinstance(sup, dict) and sup:
        def _agg(field):
            vals = []
            for r in sup.values():
                v = getattr(r, field, None)
                if v is None:
                    continue
                try:
                    vals.append(float(v))
                except (TypeError, ValueError):
                    pass
            return sum(vals) if vals else None

        for field, name in [("gross_margin", "supply_total_gross_margin"),
                            ("gross_output", "supply_total_gross_output"),
                            ("ghg_emissions", "supply_total_ghg")]:
            v = _agg(field)
            if v is not None:
                out[name] = v
        out["supply_n_regions"] = len(sup)
        out["supply_all_converged"] = all(
            bool(getattr(r, "converged", True)) for r in sup.values()
        )
    env = results.get("environmental")
    if env is not None and hasattr(env, "columns") and len(env):
        # EU totals of the environmental accounts (regions outside the EU, Norway's "NO..", left out) and Norway's
        # totals apart (env_NO_*)
        eu = [r for r in env.index if is_eu(str(r))]
        no = [r for r in env.index if not is_eu(str(r))]
        for c in ("ghg_total", "ghg_non_co2", "ghg_enteric", "ghg_manure_ch4", "ghg_manure_n2o", "ghg_soil_n2o",
                  "ghg_leaching_n2o", "nh3_total", "n_surplus", "n_mineral_input", "n_organic_input",
                  "p_input", "p_uptake", "p_surplus", "p_mineral_input", "p_manure_excretion", "p_manure_net_export",
                  "p_crop_residues", "p_runoff", "p_surplus_soil", "organic_area"):
            if c in env.columns:
                out[f"env_EU_{c}"] = float(env.loc[eu, c].sum())
                if no:
                    out[f"env_NO_{c}"] = float(env.loc[no, c].sum())
    md = results.get("metadata") or {}
    if "outer_converged" in md:
        out["outer_converged"] = bool(md["outer_converged"])
    return out


# --------------------------------------------------------------------------- #
# Experiment: a named group of runs under outputs/<experiment>/
# --------------------------------------------------------------------------- #
class Experiment:
    """A named group of model runs, stored under outputs/<name>/.

    Parameters
    ----------
    name : str
        Experiment name; becomes the folder under the output root.
    root : str
        Output root (default "outputs", which is git-ignored).
    description : str
        Free text recorded in the experiment manifest.
    """

    def __init__(self, name: str, root: str = DEFAULT_OUTPUT_ROOT,
                 description: str = "", model=None):
        self.name = name
        self.dir = Path(root) / name
        self.runs_dir = self.dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.description = description
        self._records: list[dict] = []

        self.manifest = {
            "experiment": name,
            "description": description,
            "created": datetime.now().isoformat(timespec="seconds"),
            "base_year": getattr(model, "base_year", None) if model else None,
            "n_runs": 0,
        }
        self._write_manifest()

    # -- internals ---------------------------------------------------------- #
    def _write_manifest(self):
        (self.dir / "manifest.json").write_text(
            json.dumps(self.manifest, indent=2, default=str)
        )

    # -- public API --------------------------------------------------------- #
    def save_run(self, results: dict, run_id: Optional[str] = None,
                 inputs: Optional[dict] = None) -> Path:
        """Save one run under runs/<run_id>/ and record it for the batch summary.

        `inputs` should carry the parameter values that produced this run (the
        sensitivity-analysis X); they are stored in summary.json and become
        columns of batch_summary.csv alongside the outputs (the Y).
        """
        run_id = run_id or datetime.now().strftime("run_%Y%m%d_%H%M%S_%f")
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        _write_market(results.get("market"), run_dir)
        _write_supply(results.get("supply"), run_dir)
        for key in ("feed", "environmental", "convergence"):
            v = results.get(key)
            if isinstance(v, pd.DataFrame) and not v.empty:
                v.to_csv(run_dir / f"{key}.csv")

        outputs = flatten_outputs(results)
        summary = {
            "run_id": run_id,
            "scenario": results.get("scenario"),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "inputs": inputs or {},
            "metadata": results.get("metadata", {}),
            "outputs": outputs,
        }
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))

        record = {"run_id": run_id, "scenario": results.get("scenario")}
        record.update({f"in_{k}": v for k, v in (inputs or {}).items()})
        record.update(outputs)
        self._records.append(record)

        self.manifest["n_runs"] = len(self._records)
        self._write_manifest()
        return run_dir

    def finalise(self) -> pd.DataFrame:
        """Write batch_summary.csv (one row per run) and return it.

        This is the table a sensitivity analysis consumes: `in_*` columns are the
        sampled inputs, the rest are output indicators.
        """
        df = self.batch_summary()
        if not df.empty:
            df.to_csv(self.dir / "batch_summary.csv")
        self.manifest["finalised"] = datetime.now().isoformat(timespec="seconds")
        self._write_manifest()
        return df

    def batch_summary(self) -> pd.DataFrame:
        """All runs as one DataFrame (from memory, or re-read from disk)."""
        if self._records:
            return pd.DataFrame(self._records).set_index("run_id")
        return load_experiment(self.dir)


# --------------------------------------------------------------------------- #
# Readers
# --------------------------------------------------------------------------- #
def load_experiment(experiment_dir: str | Path) -> pd.DataFrame:
    """Rebuild an experiment's batch table by reading every run's summary.json."""
    exp = Path(experiment_dir)
    runs = exp / "runs"
    search = runs if runs.exists() else exp
    rows = []
    for sf in sorted(search.glob("*/summary.json")):
        s = json.loads(sf.read_text())
        row = {"run_id": s.get("run_id"), "scenario": s.get("scenario")}
        row.update({f"in_{k}": v for k, v in (s.get("inputs") or {}).items()})
        row.update(s.get("outputs", {}))
        rows.append(row)
    return pd.DataFrame(rows).set_index("run_id") if rows else pd.DataFrame()


# --------------------------------------------------------------------------- #
# Convenience: save a single run without an Experiment
# --------------------------------------------------------------------------- #
def save_results(results: dict, experiment: str = "adhoc",
                 run_id: Optional[str] = None,
                 root: str = DEFAULT_OUTPUT_ROOT,
                 inputs: Optional[dict] = None) -> Path:
    """Save one run to outputs/<experiment>/runs/<run_id>/ (no batch bookkeeping)."""
    exp = Experiment(experiment, root=root)
    return exp.save_run(results, run_id=run_id, inputs=inputs)


# --------------------------------------------------------------------------- #
# Writers for the individual blocks
# --------------------------------------------------------------------------- #
def _write_market(mkt, run_dir: Path):
    if mkt is None:
        return
    for field in ("world_prices", "domestic_prices", "production",
                  "consumption", "net_exports", "trade_flows"):
        val = getattr(mkt, field, None)
        if val is None:
            continue
        try:
            if hasattr(val, "ndim") and val.ndim == 2:
                pd.DataFrame(val).to_csv(run_dir / f"market_{field}.csv")
            else:
                pd.Series(val).to_frame(field).to_csv(run_dir / f"market_{field}.csv")
        except Exception:
            pass


def _write_supply(sup, run_dir: Path):
    """Write region x activity levels, and region x scalar indicators."""
    if not isinstance(sup, dict) or not sup:
        return
    acts = {}
    inds = {}
    for reg, res in sup.items():
        a = getattr(res, "activities", None)
        if a is not None:
            acts[reg] = a
        row = {}
        for f in ("gross_margin", "gross_output", "ghg_emissions", "converged"):
            v = getattr(res, f, None)
            if v is not None and not hasattr(v, "__len__"):
                row[f] = v
        nb = getattr(res, "nutrient_balance", None)
        if isinstance(nb, dict):
            for k, v in nb.items():
                row[f"nutrient_{k}"] = v
        if row:
            inds[reg] = row
    if acts:
        pd.DataFrame(acts).T.to_csv(run_dir / "supply_activities.csv")
    if inds:
        pd.DataFrame(inds).T.to_csv(run_dir / "supply_indicators.csv")


# --------------------------------------------------------------------------- #
# The long results table (refactor stage 5; docs/design/STAGE5_INVENTORY.md §3.4 and its decisions of 3 November 2026)
# --------------------------------------------------------------------------- #
# One row per number, in the layout of CAPRI's results parameter DATAOUT(rall, dim5, cols, rows, year)
# (capmod/set_and_store_dataout.gms l. 53-64). Each block keeps CAPRI's convention for which dimension carries the
# item: the supply's items in rows with the activity in cols (DATA(RU, "SWHE", "LEVL")), the market's items in cols with
# the product in rows (DATA(RM, "Prod", XX): reports/sol_market.gms l. 267), the bilateral flows with the importer as
# region and the exporter in dim5 (DATAOUT(RMALL, RMALL1, "ImportQ", XX): set_and_store_dataout.gms l. 151). The
# model's own codes fill region, dim5, cols and rows; CAPRI's codes, where results_items.csv gives one, fill
# capri_region, capri_dim5, capri_cols and capri_rows (empty where CAPRI has no such item or the mapping is not
# determined).
LONG_COLUMNS = ("point", "block", "region", "dim5", "cols", "rows", "value")
#: the run's results not in the table: run metadata and diagnostics (meta.json beside the table), the outer
#: iterations' record (its own table), the scenario's name, the policy summary's text
LONG_EXCLUDED = ("scenario", "metadata", "convergence", "outer_history")
#: SupplyResult fields that are text (the solver's message, the region's own id)
_SUPPLY_TEXT = ("region_id", "solver_message")
#: the market tables of MarketEquilibrium (trade region x commodity)
_MARKET_TABLES = ("production", "consumption", "net_exports", "domestic_prices", "wedge_prices")
#: the environmental accounts summed over the EU's regions (additive ones: flatten_outputs' list)
ENV_EU_SUMS = ("ghg_total", "ghg_non_co2", "ghg_enteric", "ghg_manure_ch4", "ghg_manure_n2o", "ghg_soil_n2o",
               "ghg_leaching_n2o", "nh3_total", "n_surplus", "n_mineral_input", "n_organic_input", "p_input",
               "p_uptake", "p_surplus", "p_mineral_input", "p_manure_excretion", "p_manure_net_export",
               "p_crop_residues", "p_runoff", "p_surplus_soil", "organic_area")
EU = "EU27"


def _num(x):
    """A leaf as a float, or None for text and missing values (booleans as 0/1)."""
    import numpy as _np
    if isinstance(x, (bool, _np.bool_)):
        return float(x)
    if isinstance(x, (int, float, _np.integer, _np.floating)):
        return float(x)
    return None


def _leaves(x, path=()):
    """(path, value) of every numeric leaf of a nested result (dicts, lists, tuples, Series, DataFrames, arrays)."""
    import numpy as _np
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _leaves(v, path + (k,))
    elif isinstance(x, pd.DataFrame):
        for i, row in zip(x.index, x.itertuples(index=False, name=None)):
            for c, v in zip(x.columns, row):
                yield from _leaves(v, path + (i, c))
    elif isinstance(x, pd.Series):
        for k, v in x.items():
            yield from _leaves(v, path + (k,))
    elif isinstance(x, (list, tuple, _np.ndarray)):
        for i, v in enumerate(x):
            yield from _leaves(v, path + (i,))
    else:
        v = _num(x)
        if v is not None:
            yield path, v


def _key(parts):
    """The last key of a path and the rest for dim5: a tuple key (activity, option) gives the activity as the key and
    the option to dim5."""
    flat, last = [], parts[-1] if parts else ""
    for p in parts[:-1]:
        flat.extend(map(str, p) if isinstance(p, tuple) else [str(p)])
    if isinstance(last, tuple):
        flat.extend(map(str, last[1:]))
        last = last[0]
    return str(last), "|".join(flat)


def _eu_sum(sup: dict, field: str) -> dict:
    """EU totals of a supply field, as the run script sums them (tools/run/run_f2f_2030.py agg): the regions in the
    results' order, Norway's (NO..) left out (KNOWN_ISSUES K56), non-finite values skipped."""
    import numpy as _np
    o: dict = {}
    for reg, v in sup.items():
        if str(reg).startswith("NO"):
            continue
        for k, x in getattr(v, field).items():
            if _np.isfinite(x):
                o[k] = o.get(k, 0.0) + float(x)
    return o


def to_long(results: dict, point: str) -> pd.DataFrame:
    """One run point's results (ProjectionResult.baseline[year] or .scenario[year]) as long rows in the model's codes
    (LONG_COLUMNS; CAPRI's codes are added by with_capri_codes). ``point`` is "base" or "scen"."""
    rows: list = []
    add = rows.append

    def item_in_rows(block, region, item, rest, v):
        c, d = _key(rest)
        add((point, block, str(region), d, c if rest else "", str(item), v))

    def item_in_cols(block, region, item, rest, v):
        r, d = _key(rest)
        add((point, block, str(region), d, str(item), r, v))

    known = set(LONG_EXCLUDED)
    sup = results.get("supply") or {}
    known.add("supply")
    for reg, v in sup.items():
        for f, x in vars(v).items():
            if f in _SUPPLY_TEXT:
                continue
            for p, val in _leaves(x):
                item_in_rows("supply", reg, f, p, val)
    for f in ("activities", "gross_output"):
        for k, val in _eu_sum(sup, f).items():
            add((point, "supply", EU, "", str(k), f, val))
    mkt = results.get("market")
    known.add("market")
    if mkt is not None:
        for f, x in vars(mkt).items():
            if f in ("converged", "iterations"):
                continue                       # in the run's metadata
            if f in _MARKET_TABLES and x is not None:
                for (reg, com), val in ((pc[:2], val) for pc, val in _leaves(x)):
                    add((point, "market", str(reg), "", f, str(com), val))
            elif f == "trade_flows" and x is not None:
                for (exim, com), val in ((pc[:2], val) for pc, val in _leaves(x)):
                    add((point, "market", str(exim[1]), str(exim[0]), f, str(com), val))
            elif f in ("world_prices", "excess_demand") and x is not None:
                for (com,), val in _leaves(x):
                    add((point, "market", "WORLD", "", f, str(com), val))
            elif f == "welfare" and x is not None:
                for (reg, pos), val in _leaves(x):
                    add((point, "welfare", str(reg), "", str(pos), "", val))
            elif f == "luc" and x is not None:   # CAPRI's land-use change outside the EU, per CAPRI region
                for rms, d in x.items():
                    for k, val in d["transitions"].items():
                        add((point, "market", str(rms), "", "luc_transitions", str(k), val))
                    for k, val in d["classes"].items():
                        add((point, "market", str(rms), "", "luc_classes", str(k), val))
            elif x is not None:                # the EU's biofuel and dairy blocks
                for p, val in _leaves(x):
                    item_in_cols("market", EU, f, p, val)
    for blk in ("environmental", "luc", "set_aside", "labour", "welfare_supply"):
        known.add(blk)
        t = results.get(blk)
        if t is None:
            continue
        b_ = blk
        for (reg, it), val in _leaves(t):
            if blk == "welfare_supply":       # the supply models' welfare components: their own block
                add((point, b_, str(reg), "", str(it), "", val))
            else:
                add((point, b_, str(reg), "", "", str(it), val))
        eu = [r_ for r_ in t.index if not str(r_).startswith("NO")]
        sums = ENV_EU_SUMS if blk == "environmental" else (t.columns if blk in ("labour", "set_aside") else ())
        for it in sums:
            if it in t.columns:
                add((point, b_, EU, "", "", str(it), float(t.loc[eu, it].sum())))
    known.add("fert_dist")
    fd = results.get("fert_dist")
    if fd is not None:
        num = [c for c in fd.columns if c not in ("region", "capri_region", "ngrp")]
        for rec in fd.to_dict("records"):
            for c in num:
                val = _num(rec[c])
                if val is not None:
                    add((point, "fert_dist", str(rec["region"]), "", str(rec["ngrp"]), c, val))
    known.add("fert_npk")
    fn = results.get("fert_npk")
    if fn is not None:
        for rec in fn.to_dict("records"):
            add((point, "fert_npk", str(rec["region"]), f"{rec['nutrient']}|{rec['source']}", str(rec["ngrp"]), "t",
                 float(rec["t"])))
    known.add("feed")
    for reg, an in (results.get("feed") or {}).items():
        for p, val in _leaves(an):
            c, d = _key(p[:1])
            r_, d2 = _key(p[1:])
            add((point, "feed", str(reg), "|".join(z for z in (d, d2) if z), c, r_, val))
    known.add("policy_summary")
    for p, val in _leaves(results.get("policy_summary") or {}):
        if len(p) == 3:                        # national_budgets: member state x column
            add((point, "policy", str(p[1]), "", str(p[0]), str(p[2]), val))
        else:
            item_in_cols("policy", EU, p[0], p[1:], val)
    for blk, x in results.items():             # any other block (biofuel, abatement, ...) by its path
        if blk in known or x is None:
            continue
        for p, val in _leaves(x):
            item_in_cols(blk, EU, blk, p, val)
    return pd.DataFrame(rows, columns=list(LONG_COLUMNS))


#: the blocks whose items are in cols (CAPRI's market convention); the others' items are in rows
ITEM_IN_COLS = ("market", "welfare", "welfare_supply", "policy")
#: the table's columns after with_capri_codes
TABLE_COLUMNS = ("point", "block", "region", "dim5", "cols", "rows", "capri_region", "capri_dim5", "capri_cols",
                 "capri_rows", "unit", "value")


def results_items() -> pd.DataFrame:
    """The declared items of the long table and CAPRI's code of each (capri_data/codes/results_items.csv)."""
    p = Path(__file__).resolve().parents[1] / "capri_data" / "codes" / "results_items.csv"
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def _item_of(df: pd.DataFrame) -> pd.Series:
    return df["cols"].where(df["block"].isin(ITEM_IN_COLS), df["rows"])


def with_capri_codes(long: pd.DataFrame) -> pd.DataFrame:
    """The long rows with CAPRI's codes and the unit (results_items.csv): an item's CAPRI cols and rows codes as given
    there, "*" taking the model's own coordinate in CAPRI's code (an activity: model_activities.csv capri_codes, when
    one code; a product: model_commodities.csv), "act" the activity's code in rows (a crop's product), applies_to
    restricting the mapping to the listed activities or products; the market region and the exporter from model_trade_regions.csv;
    regional units keep their code (they are CAPRI's). CAPRI's columns stay empty where a coordinate has no CAPRI code
    (an item CAPRI does not have or not determined, the model's ROW, an aggregated activity). An item not declared in
    results_items.csv raises: the table has no undeclared rows."""
    import csv as _csv
    from capri_mod.data import definitions as D
    items = results_items()
    key = list(zip(long["block"], _item_of(long)))
    decl = {(b, i): (c, r, u, set(a.split(";")) - {""}) for b, i, c, r, u, a in zip(
        items["block"], items["item"], items["capri_cols"], items["capri_rows"], items["unit"], items["applies_to"])}
    missing = sorted(set(key) - set(decl))
    if missing:
        raise ValueError(f"results_items.csv does not declare {len(missing)} item(s) of the results: {missing[:20]}")
    with open(Path(__file__).resolve().parents[1] / "capri_data" / "codes" / "model_activities.csv", newline="") as f:
        act = {r["code"]: r["capri_codes"] for r in _csv.DictReader(f) if ";" not in r["capri_codes"]}
    rm = {m: c for c, m in D.TRADE_REGION_OF_CAPRI.items()}
    out = long.copy()
    dc = pd.Series([decl[k][0] for k in key], index=long.index)
    dr = pd.Series([decl[k][1] for k in key], index=long.index)
    out["unit"] = [decl[k][2] for k in key]
    act_c = long["cols"].map(lambda a: act.get(a, ""))
    cols = dc.where(dc != "*", act_c)
    rows = dr.where(dr != "*", long["rows"].map(lambda c: D.COMMODITY_CAPRI_CODE.get(c, "")))
    rows = rows.where(dr != "act", act_c)                # "act": the activity's own CAPRI code (its product)
    # applies_to: the model codes of the item's other coordinate the mapping holds for (empty: all)
    other = long["cols"].where(~long["block"].isin(ITEM_IN_COLS), long["rows"])
    ok = pd.Series([not decl[k][3] or o in decl[k][3] for k, o in zip(key, other)], index=long.index)
    region = long["region"].map(lambda r: rm.get(r, r if r[:2].isalpha() and len(r) == 8 else ""))
    dim5 = long["dim5"].map(lambda r: rm.get(r, ""))
    has = ok & (cols != "") & (rows != "") & (region != "") & ((long["dim5"] == "") | (dim5 != ""))
    out["capri_region"] = region.where(has, "")
    out["capri_dim5"] = dim5.where(has & (long["dim5"] != ""), "")
    out["capri_cols"] = cols.where(has, "")
    out["capri_rows"] = rows.where(has, "")
    return out[list(TABLE_COLUMNS)]


def pickle_blocks(base: pd.DataFrame, scen: pd.DataFrame) -> dict:
    """The run pickle's blocks that the readers use (tools/check/compare_runs.py and others), rebuilt from the long
    rows of the reference (base) and the scenario (scen): act, out, prod, environmental, labour, set_aside,
    act_regional, base_market, scen_market. check_pickle compares them with the pickle."""
    import numpy as _np

    def pick(d, block, **eq):
        m = d["block"] == block
        for k, v in eq.items():
            m &= d[k] == v
        return d[m]

    def dct(d, key, region=None):
        if region is not None:
            d = d[d["region"] == region]
        return dict(zip(d[key], d["value"].astype(float)))

    def two(f):
        return tuple(f(d) for d in (base, scen))

    def table(d, block):
        x = pick(d, block)
        x = x[x["region"] != EU]
        t = x.pivot(index="region", columns="rows", values="value")
        return t

    def market(d):
        m = pick(d, "market")
        return {"prod": dct(m[m["cols"] == "production"], "rows", EU),
                "cons": dct(m[m["cols"] == "consumption"], "rows", EU),
                "net_exports": dct(m[m["cols"] == "net_exports"], "rows", EU),
                "price": dct(m[m["cols"] == "domestic_prices"], "rows", EU),
                "world": dct(m[m["cols"] == "world_prices"], "rows", "WORLD")}

    def act_regional(d):
        x = pick(d, "supply", rows="activities")
        x = x[(x["region"] != EU) & _np.isfinite(x["value"].astype(float))]
        return {r: dict(zip(g["cols"], g["value"].astype(float))) for r, g in x.groupby("region", sort=False)}

    return {
        "act": two(lambda d: dct(pick(d, "supply", rows="activities"), "cols", EU)),
        "out": two(lambda d: dct(pick(d, "supply", rows="gross_output"), "cols", EU)),
        "prod": two(lambda d: {c: v for c, v in dct(pick(d, "market", cols="production"), "rows", EU).items()
                               if c in ("BEEF", "PORK", "POUL", "MILK", "EGGS", "SGMT")}),
        "environmental": two(lambda d: table(d, "environmental")),
        "labour": two(lambda d: dct(pick(d, "labour"), "rows", EU)),
        "set_aside": two(lambda d: dct(pick(d, "set_aside"), "rows", EU)),
        "act_regional": two(act_regional),
        "base_market": market(base),
        "scen_market": market(scen),
    }


def check_pickle(blocks: dict, out: dict) -> list:
    """The differences between pickle_blocks and the run pickle's blocks (empty: identical). Numbers must be equal as
    doubles (NaN equal to NaN); the environmental tables are compared cell by cell in the pickle's order."""
    import math
    diffs: list = []

    def same(a, b):
        return a == b or (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b))

    def cmp(path, a, b):
        if isinstance(b, pd.DataFrame):
            a = a.reindex(index=b.index, columns=b.columns)
            for c in b.columns:
                for i in b.index:
                    if not same(float(a.at[i, c]), float(b.at[i, c])):
                        diffs.append(f"{path}[{i},{c}]: {a.at[i, c]!r} vs {b.at[i, c]!r}")
        elif isinstance(b, dict):
            if set(a) != set(b):
                diffs.append(f"{path}: keys {sorted(set(a) ^ set(b))[:10]}")
            for k in b:
                if k in a:
                    cmp(f"{path}.{k}", a[k], b[k])
        elif isinstance(b, (tuple, list)):
            for i, (x, y) in enumerate(zip(a, b)):
                cmp(f"{path}[{i}]", x, y)
        elif not same(float(a), float(b)):
            diffs.append(f"{path}: {a!r} vs {b!r}")

    for k, v in blocks.items():
        cmp(k, v, out[k])
    return diffs


# --------------------------------------------------------------------------- #
# The Delta store of the long table (decisions of 3 November 2026: CAPRI's way, the reference stored once)
# --------------------------------------------------------------------------- #
STORED_COLUMNS = ("block", "region", "dim5", "cols", "rows", "capri_region", "capri_dim5", "capri_cols", "capri_rows",
                  "unit", "year", "value")
_KEY = ["block", "region", "dim5", "cols", "rows", "year"]


def fingerprint(parts: dict) -> str:
    """The SHA-256 of a reference run's inputs (its definition, the settings, the code commit and changed files, the
    input files' hashes, the software, the regions and years), so that a later run on the same inputs reuses the
    stored reference."""
    import hashlib
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def _stored(rows: pd.DataFrame, year: int) -> pd.DataFrame:
    out = rows.drop(columns=["point"]).copy()
    out["year"] = year
    return out[list(STORED_COLUMNS)]


# --------------------------------------------------------------------------- #
# Run ids (the store's layout of 7 November 2026, the project lead's decision): every stored partition, a reference's
# or a scenario's, is named by the SHA-256 of what it is - its results and its definition - so the id identifies
# exactly those rows and anyone can recompute it from the store (run_id_of, verify_run). The tables are not
# partitioned (no scenario=/run_id= folders): scenario and run_id are columns, each run appended as its own files.
# --------------------------------------------------------------------------- #
#: the recipe's version, the first line hashed: a change of the recipe changes every id
RUN_ID_RECIPE = "capri-mod run id 1"
RUNS_COLUMNS = ("seq", "scenario", "run_id", "kind", "reference", "reference_run_id", "fingerprint", "commit",
                "created", "rows", "note", "result_name", "label", "series", "status")
#: the columns added on 9 November 2026 (CAPRI-style result names, the user's label and series, the solve status): a
#: store written before has none of them; _runs reads them as empty text
RUNS_NAMING_COLUMNS = ("result_name", "label", "series", "status")


def rows_digest(rows: pd.DataFrame) -> str:
    """The SHA-256 of a partition's rows (STORED_COLUMNS), independent of their order: each row as a JSON list (the text
    columns as text, an empty text for a missing one; the year as an integer; the value as float.hex, "nan" for a
    missing one), the lines sorted and joined by newlines, UTF-8."""
    import hashlib
    import math
    text_cols = [c for c in STORED_COLUMNS if c not in ("year", "value")]
    cols = {c: rows[c].tolist() for c in STORED_COLUMNS}

    def txt(v):
        return "" if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NA else str(v)

    def num(v):
        v = float(v)
        return "nan" if math.isnan(v) else v.hex()
    lines = sorted(json.dumps([txt(cols[c][i]) for c in text_cols] + [int(cols["year"][i]), num(cols["value"][i])],
                              ensure_ascii=False, separators=(",", ":"))
                   for i in range(len(rows)))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def run_id_of(kind: str, name: str, definition: str, rows_sha: str, reference_run_id: str = "") -> str:
    """A partition's run id: the SHA-256 of RUN_ID_RECIPE, its kind ("reference" or "scenario"), its name, the run id
    of its reference (a scenario's; empty for a reference), the fingerprint of its definition (the runs table's
    fingerprint) and its rows' digest (rows_digest), one per line."""
    import hashlib
    return hashlib.sha256("\n".join((RUN_ID_RECIPE, kind, name, reference_run_id, definition, rows_sha))
                          .encode("utf-8")).hexdigest()


def meta_dir(root, run_id: str) -> Path:
    """A scenario run's metadata folder: root/meta/<run id>/ (meta.json; the run script adds settings.toml and
    manifest.json)."""
    return Path(root) / "meta" / run_id


def _runs(root: Path) -> pd.DataFrame:
    from deltalake import DeltaTable
    p = Path(root) / "runs"
    if not p.exists():
        return pd.DataFrame(columns=list(RUNS_COLUMNS))
    r = DeltaTable(str(p)).to_pandas()
    for c in RUNS_NAMING_COLUMNS:                 # a store written before 9 November 2026, or its earlier records
        r[c] = r[c].fillna("") if c in r.columns else ""
    return r


# --------------------------------------------------------------------------- #
# CAPRI's result names (set_and_store_dataout.gms l. 477: res_<NTSLVL>_<BAS><SIM><scenario><ResId>.gdx), the solve
# status of a run (CAPRI's p_INFES and META in its result file) and a readable catalogue of the store (RUNS.csv)
# --------------------------------------------------------------------------- #
def _two_digits(year) -> str:
    """CAPRI's BAS and SIM in its result names: a year's last two digits (2017 -> "17", 2030 -> "30")."""
    return str(int(year))[-2:]


def _slug(text: str) -> str:
    """A label as part of a file name: letters, digits, '-' and '.' kept, anything else '_'."""
    import re
    return re.sub(r"[^A-Za-z0-9.-]+", "_", str(text)).strip("_")


def result_name(short: str, base_year, year, *, n_units: Optional[int] = None, label: str = "") -> str:
    """A stored run's name as CAPRI names its result files: res_2_<BAS><SIM><scenario> (NTSLVL 2: the supply models
    are NUTS 2 regions; BAS and SIM the base and simulation years' last two digits; the scenario's short name, its
    folder's short_name), then _<n>u where the run solved a subset of n regions (CAPRI's ResId names a run's variant;
    a subset has no CAPRI counterpart) and _<label> for the user's label (--label). Not unique: CAPRI overwrites a
    result file of the same name, the store keeps every run under its run id."""
    name = f"res_2_{_two_digits(base_year)}{_two_digits(year)}{_slug(short)}"
    if n_units:
        name += f"_{int(n_units)}u"
    if label:
        name += f"_{_slug(label)}"
    return name


def short_name(scenario: str) -> str:
    """A scenario's (or reference's) short name in result names: its folder's short_name
    (capri_data/scenarios/<name>/settings.toml), else its own name (a scenario built on the command line)."""
    try:
        from capri_mod.scenarios import definition as _SD
        return _SD.load(scenario).short_name or scenario
    except Exception:
        return scenario


def status_of(meta: dict) -> str:
    """A run's solve status in a word or a few (CAPRI's p_INFES and its META item for the market model): "ok" where
    the outer loop converged, both final market solves met their balances and no regional solve's last IPOPT point
    was kept; else the reasons, separated by "; "."""
    flags = []
    conv = meta.get("conv")
    if conv is None:
        flags.append("convergence not evaluated")
    elif not conv:
        flags.append(f"not converged in {meta.get('it')} iterations")
    bad = [k for k, v in (meta.get("market_converged") or {}).items() if not v]
    if bad:
        flags.append("market not converged: " + ", ".join(bad))
    no = meta.get("nlp_nonoptimal") or {}
    n = sum(len(v or []) for v in no.values())
    if n:
        flags.append(f"{n} regional solves non-optimal at the end ("
                     + ", ".join(f"{k} {len(v)}" for k, v in no.items() if v) + ")")
    return "; ".join(flags) or "ok"


def run_record(meta: dict, rec: dict, units: Optional[list] = None) -> pd.DataFrame:
    """A run's record as CAPRI's META in its result file (set_and_store_dataout.gms: the task's provenance, every GUI
    setting with "[default]" where it is the default; DATAOUT's META rows NUM_MS, NUM_RU, MinutesNeeded): columns item,
    value, note. NUM_RU is the number of regions solved, NUM_MS the countries among them (the regions' first two
    letters; CAPRI counts its member states)."""
    rows = [(k, rec.get(k, ""), "") for k in ("result_name", "scenario", "kind", "reference", "label", "series",
                                              "status", "run_id", "reference_run_id", "commit", "created")]
    if units is not None:
        rows += [("NUM_RU", len(units), "regions solved"),
                 ("NUM_MS", len({u[:2] for u in units}), "countries of the regions solved (first two letters)")]
    rows += [("MinutesNeeded", round(float(meta.get("seconds") or 0) / 60.0, 1), "the run's wall time"),
             ("iterations", meta.get("it"), "outer iterations of the scenario"),
             ("base_iterations", meta.get("base_iterations"), "outer iterations of the baseline")]
    changed = meta.get("settings_changed") or {}
    for sec, kv in sorted((meta.get("settings") or {}).items()):
        for k, v in sorted(kv.items()):
            key = f"{sec}.{k}"
            rows.append((f"setting {key}", json.dumps(v, default=str) if not isinstance(v, str) else v,
                         "changed" if key in changed or (sec in changed and isinstance(changed[sec], dict)
                                                          and k in changed[sec]) else "[default]"))
    return pd.DataFrame(rows, columns=["item", "value", "note"]).astype({"value": str})


CATALOGUE_COLUMNS = ("seq", "created", "result_name", "kind", "scenario", "reference", "label", "series", "status",
                     "run_id", "reference_run_id", "rows", "commit", "note")


def catalogue(root) -> pd.DataFrame:
    """The store's runs, newest first, as RUNS.csv shows them: the run ids cut to 12 characters (a unique prefix is
    enough everywhere), the commit to 10. Records written before 9 November 2026 have no result name or status: they
    are given theirs here from their metadata (meta.json; a reference takes its scenario's), the note says so."""
    root = Path(root)
    r = _runs(root).copy()
    if r.empty:
        return pd.DataFrame(columns=list(CATALOGUE_COLUMNS))
    r = r.sort_values("seq", ascending=False).reset_index(drop=True)
    for i, rec in r[(r["result_name"] == "") & (r["kind"] == "scenario")].iterrows():
        mf = meta_dir(root, rec["run_id"]) / "meta.json"
        if not mf.exists():
            continue
        meta = json.loads(mf.read_text())
        regions = [x for x in str((meta.get("options") or {}).get("regions") or "").split(",") if x]
        by = (meta.get("settings") or {}).get("run", {}).get("base_year")
        if by is None:
            continue
        lab = str((meta.get("options") or {}).get("label") or "")
        n = len(regions) or None
        from deltalake import DeltaTable
        yrs = DeltaTable(str(root / "long")).to_pandas(columns=["year"], filters=[("run_id", "=", rec["run_id"])])
        if yrs["year"].nunique() != 1:
            continue
        yr = int(yrs["year"].iloc[0])
        r.at[i, "result_name"] = result_name(short_name(rec["scenario"]), by, yr, n_units=n, label=lab)
        r.at[i, "status"] = status_of(meta)
        r.at[i, "note"] = "; ".join(x for x in (rec["note"], "named afterwards from meta.json") if x)
        ref = (r["run_id"] == rec["reference_run_id"]) & (r["result_name"] == "")
        r.loc[ref, "result_name"] = result_name(short_name(rec["reference"]), by, yr, n_units=n, label=lab)
        r.loc[ref, "note"] = r.loc[ref, "note"].map(lambda x: "; ".join(y for y in (x, "named afterwards from "
                                                                                 "its scenario's meta.json") if y))
    for c in ("run_id", "reference_run_id"):
        r[c] = r[c].fillna("").astype(str).str[:12]
    r["commit"] = r["commit"].fillna("").astype(str).str[:10]
    return r[list(CATALOGUE_COLUMNS)]


def write_catalogue(root) -> Path:
    """root/RUNS.csv: the store's catalogue (catalogue), rewritten after every stored run; a view of root/runs, which
    stays the record."""
    f = Path(root) / "RUNS.csv"
    catalogue(root).to_csv(f, index=False)
    return f


def _rows_of(root, table: str, run_id: str) -> pd.DataFrame:
    from deltalake import DeltaTable
    p = Path(root) / table
    if not p.exists():
        return pd.DataFrame()
    return DeltaTable(str(p)).to_pandas(filters=[("run_id", "=", run_id)])


def read_partition(root, scenario: str, run_id: str) -> pd.DataFrame:
    """One stored partition (a reference's or a scenario's rows) of results_dir/long, by its run id (the scenario is
    checked)."""
    df = _rows_of(root, "long", run_id)
    if len(df) and set(df["scenario"]) != {scenario}:
        raise KeyError(f"{root}: run {run_id} is {sorted(set(df['scenario']))}, not {scenario}")
    return df.drop(columns=["scenario", "run_id"]).sort_values(_KEY).reset_index(drop=True)


def verify_run(root, run_id: str) -> bool:
    """Recompute a stored partition's run id from its rows and its record in the runs table."""
    runs = _runs(Path(root))
    r = runs[runs["run_id"] == run_id]
    if len(r) != 1:
        raise KeyError(f"{root}: {len(r)} records of run {run_id}")
    rec = r.iloc[0]
    rows = read_partition(root, rec["scenario"], run_id)
    return run_id_of(rec["kind"], rec["scenario"], rec["fingerprint"], rows_digest(rows),
                     rec["reference_run_id"] or "") == run_id


def _jsonable(x):
    """The run's metadata for JSON: tuple and other non-text dict keys as text ("a|b" for a tuple)."""
    if isinstance(x, dict):
        return {(k if isinstance(k, str) else "|".join(map(str, k)) if isinstance(k, tuple) else str(k)): _jsonable(v)
                for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    return x


def write_run(base: pd.DataFrame, scen: pd.DataFrame, *, scenario: str, reference: str, year: int,
              fingerprint_parts: dict, meta: dict, root, summary: Optional[dict] = None,
              iterations: Optional[tuple] = None, scenario_parts: Optional[dict] = None,
              created: Optional[str] = None, reference_fingerprint: Optional[str] = None,
              names: Optional[dict] = None, units: Optional[list] = None) -> dict:
    """Store a run: the reference's rows and the scenario's rows each as its own partition of root/long, named by its
    run id (run_id_of: the SHA-256 of its results and its definition). The reference's definition is
    fingerprint(fingerprint_parts) (its inputs); the scenario's is fingerprint({"reference": that fingerprint,
    **scenario_parts}) (scenario_parts: what the scenario adds, e.g. overrides on the command line). A reference
    already stored with the same id (the same definition and identical rows) is reused; a reference with the same
    fingerprint but other rows is stored as its own partition and the note says so. A scenario already stored with
    the same id is not stored again (the record returned says "duplicate"). summary (the run script's EU summaries)
    goes to root/summary and iterations (the outer iterations' records of the reference and the scenario) to
    root/iterations under the partitions' run ids (encode_record's rows); meta (the run's metadata) to
    meta_dir(root, run id)/meta.json. reference_fingerprint, when given, is the reference's fingerprint itself in place
    of fingerprint(fingerprint_parts) (a store converted from an older layout keeps its references' fingerprints:
    tools/run/migrate_results_store.py). names: the records' result names, label, series and status
    ({"result_name", "reference_result_name", "label", "series", "status"}; empty where not given); units: the regions
    solved (the run record's NUM_RU and NUM_MS). Besides meta.json the scenario's metadata folder gets run_record.csv
    (run_record), and root/RUNS.csv is rewritten (write_catalogue). Returns the scenario's record (root/runs)."""
    import pyarrow as pa
    from datetime import datetime as _dt
    from deltalake import write_deltalake
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    fp = reference_fingerprint or fingerprint(fingerprint_parts)
    fp_s = fingerprint({"reference": fp, **(scenario_parts or {})})
    commit = str(fingerprint_parts.get("commit") or "")
    runs = _runs(root)
    b, s = _stored(base, year), _stored(scen, year)
    ref_id = run_id_of("reference", reference, fp, rows_digest(b))
    scen_id = run_id_of("scenario", scenario, fp_s, rows_digest(s), ref_id)
    have = runs[runs["run_id"] == scen_id]
    if len(have):
        return {**have.iloc[0].to_dict(), "reference_reused": True, "duplicate": True}
    note = ""
    ref_new = not (runs["run_id"] == ref_id).any()
    if ref_new:
        same_fp = runs[(runs["kind"] == "reference") & (runs["scenario"] == reference) & (runs["fingerprint"] == fp)]
        if len(same_fp):
            note = (f"reference {reference}: same fingerprint as run(s) {list(same_fp['run_id'])}, other results; "
                    "stored as its own run")
            print(f"WARNING: {note}", flush=True)

    def put(df, scen_name, rid, table="long"):
        df = df.copy()
        if table != "long":
            df["pos"] = range(len(df))        # a record's row order (decode_record rebuilds in it)
        df["scenario"], df["run_id"] = scen_name, rid
        write_deltalake(str(root / table), pa.Table.from_pandas(df, preserve_index=False), mode="append")

    nm = {k: str(v or "") for k, v in (names or {}).items()}
    now = created or _dt.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    seq = int(runs["seq"].max()) + 1 if len(runs) else 0
    recs = []
    if ref_new:
        put(b, reference, ref_id)
        if iterations is not None:
            put(encode_record(iterations[0]), reference, ref_id, "iterations")
        recs.append({"seq": seq, "scenario": reference, "run_id": ref_id, "kind": "reference", "reference": "",
                     "reference_run_id": "", "fingerprint": fp, "commit": commit, "created": now, "rows": len(b),
                     "note": note, "result_name": nm.get("reference_result_name", ""), "label": nm.get("label", ""),
                     "series": nm.get("series", ""), "status": ""})
    put(s, scenario, scen_id)
    if summary is not None:
        put(encode_record(summary), scenario, scen_id, "summary")
    if iterations is not None:
        put(encode_record(iterations[1]), scenario, scen_id, "iterations")
    rec = {"seq": seq + len(recs), "scenario": scenario, "run_id": scen_id, "kind": "scenario", "reference": reference,
           "reference_run_id": ref_id, "fingerprint": fp_s, "commit": commit, "created": now, "rows": len(s),
           "note": "", "result_name": nm.get("result_name", ""), "label": nm.get("label", ""),
           "series": nm.get("series", ""), "status": nm.get("status", "")}
    recs.append(rec)
    # schema_mode "merge": a store written before 9 November 2026 gains the naming columns (RUNS_NAMING_COLUMNS)
    write_deltalake(str(root / "runs"), pa.Table.from_pandas(pd.DataFrame(recs)[list(RUNS_COLUMNS)],
                                                             preserve_index=False), mode="append", schema_mode="merge")
    md = meta_dir(root, scen_id)
    md.mkdir(parents=True, exist_ok=True)
    (md / "meta.json").write_text(json.dumps(_jsonable(meta), indent=1, default=str))
    run_record(meta, rec, units).to_csv(md / "run_record.csv", index=False)
    write_catalogue(root)
    return {**rec, "reference_reused": not ref_new, "duplicate": False}


def read_run(root, scenario: str, run_id: Optional[str] = None) -> tuple:
    """A stored scenario run and its reference: (reference rows, scenario rows, the run's record); the latest run of
    the scenario when run_id is not given (a unique prefix of the id is enough)."""
    runs = _runs(Path(root))
    r = runs[(runs["scenario"] == scenario) & (runs["kind"] == "scenario")]
    if run_id is not None:
        r = r[r["run_id"].astype(str).str.startswith(run_id)]
        if len(r) > 1:
            raise KeyError(f"{root}: run id prefix {run_id} matches {len(r)} runs of {scenario}")
    if r.empty:
        raise KeyError(f"{root}: no stored run of {scenario}" + (f" {run_id}" if run_id else ""))
    rec = r.sort_values("seq").iloc[-1].to_dict()
    return (read_partition(root, rec["reference"], rec["reference_run_id"]),
            read_partition(root, scenario, rec["run_id"]), rec)


def as_points(base: pd.DataFrame, scen: pd.DataFrame) -> tuple:
    """Stored rows back to the long rows of pickle_blocks (the point column restored)."""
    return tuple(d.assign(point=p) for d, p in ((base, "base"), (scen, "scen")))


# --------------------------------------------------------------------------- #
# Nested records beside the long table: the run script's EU summaries and the outer iterations' record
# --------------------------------------------------------------------------- #
# Both are the coupling's or the run script's own structures (dicts, tuples, lists of numbers, flags and names), not
# results by region and item: they are stored as (path, value, text) rows that rebuild them exactly. A path is a JSON
# list of steps: ["d", key] a dict key (["dt", [...]] a tuple key), ["t", i] a tuple position, ["l", i] a list
# position, ["a", i] a NumPy array position, ["e"] an empty container of the kind of the step before, and the leaf
# type last: ["f"] float, ["i"] int, ["b"] bool, ["s"] text (in the text column), ["n"] None, ["x"] NumPy float.
RECORD_COLUMNS = ("path", "value", "text")


def encode_record(x) -> pd.DataFrame:
    """A nested record as (path, value, text) rows (decode_record rebuilds it)."""
    import numpy as _np
    rows: list = []

    def walk(v, path):
        if isinstance(v, dict):
            if not v:
                rows.append((json.dumps(path + [["ed"]]), float("nan"), ""))
            for k, y in v.items():
                walk(y, path + [["dt", list(k)] if isinstance(k, tuple) else ["d", k]])
        elif isinstance(v, (tuple, list, _np.ndarray)):
            tag = "t" if isinstance(v, tuple) else "l" if isinstance(v, list) else "a"
            if len(v) == 0:
                rows.append((json.dumps(path + [["e" + tag]]), float("nan"), ""))
            for i, y in enumerate(v):
                walk(y.item() if isinstance(y, _np.generic) and tag == "a" else y, path + [[tag, i]])
        elif isinstance(v, (bool, _np.bool_)):
            rows.append((json.dumps(path + [["b"]]), float(v), ""))
        elif isinstance(v, (int, _np.integer)):
            rows.append((json.dumps(path + [["i"]]), float(v), ""))
        elif isinstance(v, _np.floating):
            rows.append((json.dumps(path + [["x"]]), float(v), ""))
        elif isinstance(v, float):
            rows.append((json.dumps(path + [["f"]]), v, ""))
        elif isinstance(v, str):
            rows.append((json.dumps(path + [["s"]]), float("nan"), v))
        elif v is None:
            rows.append((json.dumps(path + [["n"]]), float("nan"), ""))
        else:
            raise TypeError(f"encode_record: {type(v).__name__} at {path}")
    walk(x, [])
    return pd.DataFrame(rows, columns=list(RECORD_COLUMNS))


def decode_record(df: pd.DataFrame):
    """The nested record of encode_record's rows (in their order)."""
    import numpy as _np
    root: dict = {}

    def leaf(tag, value, text):
        return {"f": float, "x": _np.float64, "i": lambda v: int(v), "b": lambda v: bool(v)}.get(tag, lambda v: v)(
            value) if tag in ("f", "x", "i", "b") else text if tag == "s" else None

    # build with dicts keyed by the steps, then turn the tuple, list and array steps into their containers
    for path, value, text in zip(df["path"], df["value"], df["text"]):
        steps = json.loads(path)
        node = root
        for s in steps[:-2]:
            node = node.setdefault(("dt", tuple(s[1])) if s[0] == "dt" else tuple(s), {})
        last, typ = steps[-2] if len(steps) > 1 else None, steps[-1]
        if typ[0].startswith("e"):
            container = node if last is None else node.setdefault(
                ("dt", tuple(last[1])) if last[0] == "dt" else tuple(last), {})
            container[("empty", typ[0][1:])] = None
            continue
        key = ("dt", tuple(last[1])) if last[0] == "dt" else tuple(last)
        node[key] = ("leaf", leaf(typ[0], value, text))

    def build(node):
        if isinstance(node, tuple) and len(node) == 2 and node[0] == "leaf":
            return node[1]
        keys = list(node)
        if len(keys) == 1 and keys[0][0] == "empty":
            return {"d": {}, "t": (), "l": [], "a": _np.array([])}[keys[0][1]]
        kind = keys[0][0]
        if kind in ("t", "l", "a"):
            items = [build(node[k]) for k in sorted(keys, key=lambda k: k[1])]
            return tuple(items) if kind == "t" else items if kind == "l" else _np.array(items)
        return {(tuple(k[1]) if k[0] == "dt" else k[1]): build(v) for k, v in node.items()}
    return build(root)


#: the key of the summary record that keeps the label order of the tables rebuilt from the long rows
LABELS_KEY = "_labels"


def summary_of(out: dict) -> dict:
    """The run script's pickle without the blocks rebuilt from the long rows, the metadata and the iterations' record:
    what write_run stores as the summary record, with the environmental tables' label order (LABELS_KEY)."""
    summ = {k: v for k, v in out.items() if k not in LONG_BLOCKS + ("meta", "outer_history")}
    summ[LABELS_KEY] = {"environmental": tuple((tuple(map(str, t.index)), tuple(map(str, t.columns)))
                                               for t in out["environmental"])}
    return summ


#: the pickle's blocks rebuilt from the long rows (pickle_blocks); the others are the run script's summaries, stored
#: as records, and the metadata
LONG_BLOCKS = ("act", "out", "prod", "environmental", "labour", "set_aside", "act_regional", "base_market",
               "scen_market")


def _record(root, table, scenario, run_id):
    df = _rows_of(root, table, run_id)
    if not len(df):
        return None
    if "pos" in df.columns:
        df = df.sort_values("pos", kind="stable")
    return decode_record(df[list(RECORD_COLUMNS)].reset_index(drop=True))


def load_store(root, scenario: str, run_id: Optional[str] = None) -> dict:
    """A stored run as the run script's pickle: the blocks rebuilt from the long rows, the summaries, the outer
    iterations' records (reference, scenario) and the metadata (meta.json: tuple keys as text)."""
    rb, rs, rec = read_run(root, scenario, run_id)
    out = pickle_blocks(*as_points(rb, rs))
    summ = _record(root, "summary", scenario, rec["run_id"]) or {}
    # the environmental tables' labels in the run's order (the long rows are read in key order)
    for i, (idx, cols) in enumerate((summ.pop(LABELS_KEY, None) or {}).get("environmental") or ()):
        t = out["environmental"]
        out["environmental"] = tuple(x.reindex(index=list(idx), columns=list(cols)) if j == i else x
                                     for j, x in enumerate(t))
    out.update(summ)
    it = (_record(root, "iterations", rec["reference"], rec["reference_run_id"]),
          _record(root, "iterations", scenario, rec["run_id"]))
    if it != (None, None):
        out["outer_history"] = it
    mp = meta_dir(root, rec["run_id"]) / "meta.json"
    if mp.exists():
        out["meta"] = json.loads(mp.read_text())
    return out


def load_run(spec: str) -> dict:
    """A run for the check tools: a pickle (a path ending in .pkl) or a stored run, "store:ROOT:SCENARIO[:RUN_ID]"
    (load_store)."""
    import pickle
    if spec.startswith("store:"):
        parts = spec.split(":")
        return load_store(parts[1], parts[2], parts[3] if len(parts) > 3 and parts[3] else None)
    with open(spec, "rb") as fh:
        return pickle.load(fh)
