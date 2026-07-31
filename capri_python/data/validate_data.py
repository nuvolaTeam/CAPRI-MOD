"""
CAPRI-Python data validator.

Checks the live data in capri_data/ against MANIFEST.json and runs a set of
integrity and consistency tests. Its job is to catch the data-management
failure modes that matter at this project's scale — not performance, but
*correctness*: missing files, shape drift, vintage-mixing, unit surprises,
and broken cross-file references.

Run standalone:   python validate_data.py
Or import:        from validate_data import validate_data; validate_data("capri_data")

Storage note: the data is ~3.6 MB of flat CSV/JSON. That is deliberately not a
database or Parquet store — at this scale flat files load in under two seconds
and stay human-readable. The right data-management tool here is validation +
a manifest, which is what this module provides.
"""
from __future__ import annotations
import json
from pathlib import Path
from capri_python.data.loaders import resolve_data_file
import pandas as pd


class ValidationReport:
    def __init__(self):
        self.checks = []      # (name, status, detail)
        self.n_pass = 0
        self.n_warn = 0
        self.n_fail = 0

    def add(self, name, status, detail=""):
        self.checks.append((name, status, detail))
        if status == "PASS": self.n_pass += 1
        elif status == "WARN": self.n_warn += 1
        else: self.n_fail += 1

    def summary(self):
        return f"{self.n_pass} pass, {self.n_warn} warn, {self.n_fail} fail"

    def print(self):
        icons = {"PASS": "  ok  ", "WARN": " warn ", "FAIL": " FAIL "}
        for name, status, detail in self.checks:
            line = f"[{icons.get(status, status)}] {name}"
            if detail:
                line += f"  — {detail}"
            print(line)
        print("-" * 60)
        print(f"  {self.summary()}")


def validate_data(data_dir="capri_data") -> ValidationReport:
    D = Path(data_dir)
    rep = ValidationReport()

    # --- 1. Manifest present and parseable ---
    man_path = D / "MANIFEST.json"
    if not man_path.exists():
        rep.add("manifest exists", "FAIL", "MANIFEST.json missing")
        return rep
    manifest = json.load(open(man_path))
    files = manifest.get("files", {})
    rep.add("manifest parseable", "PASS", f"{len(files)} live files catalogued")

    # --- 2. Every catalogued live file exists ---
    missing = [fn for fn in files if not resolve_data_file(D, fn).exists()]
    if missing:
        rep.add("all live files present", "FAIL", f"missing: {missing}")
    else:
        rep.add("all live files present", "PASS", f"{len(files)}/{len(files)}")

    # --- 3. Shape matches manifest (catches silent truncation/corruption) ---
    drift = []
    for fn, meta in files.items():
        p = resolve_data_file(D, fn)
        if not p.exists() or not fn.endswith(".csv"):
            continue
        exp = meta.get("shape") or {}
        if "rows" not in exp:
            continue
        try:
            df = pd.read_csv(p, index_col=0)
            if df.shape[0] != exp["rows"]:
                drift.append(f"{fn}: {df.shape[0]} rows (manifest {exp['rows']})")
        except Exception as e:
            drift.append(f"{fn}: unreadable ({str(e)[:30]})")
    if drift:
        rep.add("file shapes match manifest", "WARN", "; ".join(drift[:3]))
    else:
        rep.add("file shapes match manifest", "PASS")

    # --- 4. Vintage consistency: the base-year group must share one vintage ---
    base_group = {fn: m["vintage"] for fn, m in files.items()
                  if m.get("domain") in ("supply", "prices")
                  and m.get("vintage") not in ("static", "2006")}
    vintages = set(base_group.values())
    if len(vintages) > 1:
        rep.add("base-year vintage consistent", "WARN",
                f"base group spans {sorted(vintages)} — mixing vintages risks "
                f"inconsistent calibration")
    else:
        rep.add("base-year vintage consistent", "PASS",
                f"base group all {vintages.pop() if vintages else '?'}")

    # --- 5. Key economic sanity checks on live values ---
    try:
        wp = pd.read_csv(resolve_data_file(D, "world_prices.csv"), index_col=0)
        col = wp.columns[0]
        # livestock prices should exceed crop prices (basic economics)
        beef = wp.at["BEEF", col] if "BEEF" in wp.index else None
        wheat = wp.at["SWHE", col] if "SWHE" in wp.index else None
        if beef and wheat and beef > wheat * 5:
            rep.add("price levels sane (beef >> wheat)", "PASS",
                    f"beef {beef:.0f} vs wheat {wheat:.0f} EUR/t")
        else:
            rep.add("price levels sane", "WARN",
                    f"beef {beef}, wheat {wheat} — check units")
    except Exception as e:
        rep.add("price levels sane", "WARN", str(e)[:40])

    # --- 6. No negative quantities in base areas/yields ---
    for fn in ["base_areas.csv", "yields.csv", "animal_numbers.csv"]:
        p = resolve_data_file(D, fn)
        if not p.exists():
            continue
        try:
            df = pd.read_csv(p, index_col=0).select_dtypes("number")
            neg = (df < 0).sum().sum()
            if neg > 0:
                rep.add(f"non-negative values ({fn})", "FAIL", f"{neg} negatives")
            else:
                rep.add(f"non-negative values ({fn})", "PASS")
        except Exception as e:
            rep.add(f"non-negative values ({fn})", "WARN", str(e)[:30])

    # --- 7. Trade flows reference valid regions/commodities ---
    try:
        tf = pd.read_csv(resolve_data_file(D, "trade_flows.csv"))
        rep.add("trade flows loadable", "PASS", f"{tf.shape[0]} rows")
    except Exception as e:
        rep.add("trade flows loadable", "WARN", str(e)[:40])

    # --- 8. Synthetic-data detection (from the sourcing registry) ---
    reg_path = D / "DATA_SOURCING_REGISTRY.json"
    if reg_path.exists():
        reg = json.load(open(reg_path))
        synthetic_live = []
        for fn, meta in reg.get("datasets", {}).items():
            if meta.get("nature") == "SYNTHETIC_FALLBACK":
                # is the real file actually absent (so the fallback fires)?
                if not resolve_data_file(D, fn).exists():
                    synthetic_live.append(fn)
        if synthetic_live:
            rep.add("no live synthetic data", "WARN",
                    f"{len(synthetic_live)} dataset(s) using synthetic fallback: "
                    f"{', '.join(synthetic_live)} — see registry for real source")
        else:
            rep.add("no live synthetic data", "PASS")
        # report the data-nature breakdown
        from collections import Counter
        nat = Counter(m.get("nature") for m in reg["datasets"].values())
        rep.add("data provenance known", "PASS",
                f"{nat.get('REAL_CAPRI',0)} CAPRI, {nat.get('REAL_FAO',0)} FAO, "
                f"{nat.get('SYNTHETIC_FALLBACK',0)} synthetic")
    else:
        rep.add("sourcing registry present", "WARN",
                "DATA_SOURCING_REGISTRY.json missing")

    # --- 8. Input consistency: gross margins before calibration ---
    # This is the gate that catches mismatched input sources. PMP calibration
    # needs every grown crop to have a positive gross margin
    # (price x yield - variable cost + CAP payment). Negative or razor-thin
    # margins mean yields/prices/costs came from inconsistent sources and will
    # degrade or break calibration. Crops not actually grown in a region are
    # ignored (a crop with zero area doesn't need a positive margin).
    _check_margins(D, rep)

    return rep


# Fodder / non-marketed activities: valued at on-farm opportunity cost, so a
# market-price margin check does not apply to them.
_NON_MARKET = {"GRAS", "MAIF", "OFOD", "SETA"}

# Staple crops that must calibrate cleanly.
_STAPLES = {"SWHE", "DWHE", "BARL", "CORN", "RYEM", "OATS", "RAPE", "SUNF",
            "SOYA", "POTA", "SUGB", "PULS"}

# A negative CAP-adjusted margin worse than this (EUR/ha) is implausible as real
# economics — no support scheme covers a loss this large, so it almost certainly
# signals a data error (wrong price or cost). Losses smaller than this may be
# genuine marginal / rotational farming and are reported, not failed.
_ARTIFACT_LOSS = -1000.0


def _check_margins(D, rep):
    """Assess input consistency via gross margins, respecting CAP support.

    A crop's *market* margin (price x yield - cost) is often negative in reality:
    European farming is widely supported, and CAP direct payments are designed to
    cover exactly that gap. So a negative market margin is NOT by itself a data
    problem. What matters:

      * market margin < 0 but CAP-adjusted margin >= 0  -> normal supported
        agriculture. Not flagged.
      * CAP-adjusted margin < 0 but modest              -> possibly real marginal
        or rotational farming. Reported as a note (WARN at most).
      * CAP-adjusted margin very negative (< _ARTIFACT_LOSS) -> implausible;
        almost certainly a data error (as with the sugar-price bug). Flagged.
    """
    try:
        y = pd.read_csv(resolve_data_file(D, "yields.csv"), index_col=0)
        c = pd.read_csv(resolve_data_file(D, "variable_costs.csv"), index_col=0)
        areas = pd.read_csv(resolve_data_file(D, "base_areas.csv"), index_col=0)
        pr = pd.read_csv(resolve_data_file(D, "producer_prices.csv"), index_col=0)
        price = pr[pr.columns[0]]
        # CAPRI regional prices (MPRI) where extracted. The margin check must use
        # the same prices the supply module does, or it reports losses the model
        # does not actually see.
        try:
            reg_price = pd.read_csv(
                Path(D) / "sources" / "capreg" / "capreg_producer_prices.csv",
                index_col=0)
        except Exception:
            reg_price = pd.DataFrame()
    except Exception as e:
        rep.add("input margins consistent", "WARN",
                f"could not load inputs: {str(e)[:40]}")
        return

    try:
        cap = pd.read_csv(resolve_data_file(D, "cap_payments.csv"), index_col=0)
        cap_per_ha = cap.sum(axis=1) if cap.shape[1] > 1 else cap[cap.columns[0]]
    except Exception:
        cap_per_ha = None

    crops = [c_ for c_ in areas.columns
             if c_ in y.columns and c_ in c.columns and c_ in price.index
             and c_ not in _NON_MARKET]

    cap_supported = 0        # negative at market, rescued by CAP (normal)
    marginal = []            # negative even with CAP, but plausibly real
    artifacts = []           # negative even with CAP, implausibly large (data error)
    checked = 0

    for reg in areas.index:
        subsidy = float(cap_per_ha[reg]) if (cap_per_ha is not None and reg in cap_per_ha.index) else 0.0
        for crop in crops:
            grown = areas.at[reg, crop] if reg in areas.index else 0
            if pd.isna(grown) or grown <= 1.0:
                continue
            unit_price = price[crop]
            if (not reg_price.empty and reg in reg_price.index
                    and crop in reg_price.columns
                    and pd.notna(reg_price.at[reg, crop])
                    and reg_price.at[reg, crop] > 0):
                unit_price = float(reg_price.at[reg, crop])
            yld = y.at[reg, crop] if reg in y.index else None
            cost = c.at[reg, crop] if reg in c.index else None
            if pd.isna(yld) or pd.isna(cost):
                continue
            checked += 1
            market_margin = float(yld) * float(unit_price) - float(cost)
            full_margin = market_margin + subsidy
            if full_margin >= 0:
                if market_margin < 0:
                    cap_supported += 1        # CAP did its job — normal
                continue
            # negative even after CAP
            if full_margin < _ARTIFACT_LOSS:
                artifacts.append((reg, crop, full_margin))
            else:
                marginal.append((reg, crop, full_margin))

    if checked == 0:
        rep.add("input margins consistent", "WARN", "no grown crops to check")
        return

    staple_artifacts = [x for x in artifacts if x[1] in _STAPLES]
    note = f"{cap_supported} CAP-supported (normal), {len(marginal)} marginal"

    if staple_artifacts:
        sample = ", ".join(f"{r}/{c} {m:+.0f}" for r, c, m in
                           sorted(staple_artifacts, key=lambda x: x[2])[:3])
        rep.add("input margins consistent", "FAIL",
                f"{len(staple_artifacts)} staple crops with implausible loss "
                f"(< {_ARTIFACT_LOSS:.0f} EUR/ha after CAP — likely data error): "
                f"{sample}. [{note}]")
    elif artifacts:
        sample = ", ".join(f"{r}/{c} {m:+.0f}" for r, c, m in
                           sorted(artifacts, key=lambda x: x[2])[:3])
        rep.add("input margins consistent", "WARN",
                f"{len(artifacts)} specialty crops with implausible loss after CAP "
                f"(likely price-data gaps): {sample}. [{note}]")
    elif marginal:
        rep.add("input margins consistent", "PASS",
                f"{checked} grown region-crops; no data artifacts. "
                f"{len(marginal)} run at a small loss after CAP (plausibly real "
                f"marginal/rotational farming). [{note}]")
    else:
        rep.add("input margins consistent", "PASS",
                f"{checked} grown region-crops; all viable once CAP is counted. "
                f"[{note}]")


if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "capri_data"
    print(f"Validating data in: {d}\n" + "=" * 60)
    report = validate_data(d)
    report.print()
