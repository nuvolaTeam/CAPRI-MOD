"""Refactor stages 4a and 4c (docs/design/ARCHITECTURE_REFACTOR.md): a class's methods moved, unchanged, into block mixins in a
sub-package beside its module, as stage 3a did for the regional supply model (tools/refactor/split_regional_model.py,
of which this is the general form). A move only: every method's text is copied as it is (with its decorators and the
comment lines directly above it), the class attributes stay on the class, and the blocks see the module's module-level
names, which the module gives them once it is loaded (blocks/__init__.py, inject).

    python tools/refactor/split_class.py environment          # writes the blocks and rewrites the module
    python tools/refactor/split_class.py environment --check  # lists the assignment, writes nothing

Run once per configuration. The check of the move is a run identical to the reference
(tools/check/compare_pickles_exact.py) and the test suite.

History: on 30 October 2026 the blocks sub-packages this tool wrote (capri_mod/supply/blocks,
capri_mod/environmental/blocks) were moved up into their packages, as the market's modules are, and their inject
became capri_mod/utils/mixins.py (the project lead's preference). The tool is kept as the record of the split;
it is not to be run again.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: name -> (module file, class, blocks package (dotted), {block: (class name, docstring, methods)})
CONFIGS = {
    "environment": (
        "capri_mod/environmental/environmental_module.py", "EnvironmentalModule", "capri_mod.environmental.blocks", {
            "ghg": ("GHGBlock",
                    "Greenhouse gases of the environmental accounts: manure N excretion and its loss shares, enteric and "
                    "manure CH4, manure N2O (CAPRI's factors, the ammonia technologies' cascade, anaerobic digestion), "
                    "CO2 coefficients (CAPRI's gases.gms and envind files).",
                    ["_manure_loss_shares", "_n_excretion", "_n_excretion_uncached", "_n_animal_products",
                     "_ch4_per_head", "_co2_coefs", "compute_ghg", "_enteric_factors", "_manure_n2o_factor",
                     "_manure_n2o_tech", "_manure_n2o_cascade", "_ad_ch4_factor", "_manure_n2o_full"]),
            "nitrogen": ("NitrogenBlock",
                         "Nitrogen of the environmental accounts: CAPRI's gross nitrogen balance (e_SURTOTHa) and its "
                         "items, the fertiliser distribution, manure trade and substitution, the fertiliser options' "
                         "side effects, winter cover, leaching and mineral N2O.",
                         ["set_manure_trade", "_substitution", "_gnb_row", "_manure_marginal_factor", "_cached_row",
                          "_capri_crop_n", "_base_mineral_rate", "grass_intensity_delta", "_need_weight", "_need_base",
                          "_residue_availability", "unit_nitrogen_balance", "compute_nitrogen_balance",
                          "fert_distribution", "fert_side_factors", "_winter_cover_now", "_leach_animals",
                          "_mineral_n2o_n", "leaching"]),
            "ammonia": ("AmmoniaBlock",
                        "Ammonia of the environmental accounts (CAPRI's NH3 factors and the ammonia technologies).",
                        ["_nh3_factors", "compute_ammonia"]),
            "phosphorus": ("PhosphorusBlock",
                           "The phosphorus balance (P2O5; docs/P_BALANCE.md): CAPRI's applied ratios and runoff.",
                           ["_p_capri_region", "_p_applied_ratio", "_p_runtot", "compute_phosphorus_balance"]),
            "biodiversity": ("BiodiversityBlock",
                             "Biodiversity indicators of the environmental accounts.",
                             ["compute_biodiversity_indicators"]),
        }),
    "model": (
        "capri_mod/model.py", "CAPRIModel", "capri_mod.coupling", {
            "hessian": ("HessianBlock",
                        "The market supply Hessian measured on the supply models (CAPRI's simu_calibration_to_supply: "
                        "price shocks, the split by member state, the pending measurements).",
                        ["_measure_pending_hessian", "_market_supply_hessian", "_split_hessian", "_sum_frames"]),
            "feed": ("FeedBlock",
                     "Feed between the supply models and the market: the bulk feed price ratios, the rations' update, "
                     "the market's feed demand from the supply models.",
                     ["feed_bulk_price_ratios", "_update_rations", "_set_feed_demand"]),
            "young_animals": ("YoungAnimalBlock",
                              "Young animals between the supply models and the market: their balance by market region, "
                              "prices from the market or the model's own update, the state the market clears.",
                              ["_yani_market_region", "_young_animal_net_by_country", "_young_animal_balance",
                               "_update_young_animal_prices", "_yani_in_market_now", "_young_animal_state_to_market",
                               "_young_animal_prices_from_market", "_publish_young_animal_prices"]),
            "price_step": ("PriceStepBlock",
                           "The outer loop's price step and stop rule as CAPRI's (capmod/price_forecast.gms, the stop "
                           "test).",
                           ["_capri_stop_step", "_capri_price_update", "_capri_forecast", "_capri_special_forecast",
                            "_capri_step_special"]),
            "manure": ("ManureBlock",
                       "The manure pools between regions (CAPRI's manure trade, cleared between solves).",
                       ["_update_manure_pools"]),
            "bridge": ("BridgeBlock",
                       "Supply to market: the supply models' output aggregated to the market's commodities and regions "
                       "(livestock products, dairy and processing yields, sugar per beet).",
                       ["_livestock_products_by_country", "_bridge_supply_to_market", "_dairy_yield",
                        "_processing_yield", "_sugar_per_beet"]),
            "reporting": ("ReportingBlock",
                          "Reports of a run: the welfare of the supply side, comparisons of runs, the reporter, the "
                          "trace of the slowest regional solves.",
                          ["_trace_nlp_regions", "_welfare_supply", "compare", "get_reporter"]),
        }),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("config", choices=sorted(CONFIGS))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    rel, cname_main, pkg, assign = CONFIGS[a.config]
    src_path = ROOT / rel
    blocks_dir = src_path.parent / pkg.rsplit(".", 1)[1]
    depth = len(Path(rel).parts) - 1                          # parents[depth] of the module is the repository root
    src = src_path.read_text()
    lines = src.split("\n")
    tree = ast.parse(src)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cname_main)
    if cls.bases or cls.decorator_list:
        raise SystemExit(f"{cname_main} has bases or decorators: not handled")
    members = list(cls.body)
    meth = {}
    for k, b in enumerate(members):
        if not isinstance(b, ast.FunctionDef):
            continue
        start = (b.decorator_list[0].lineno if b.decorator_list else b.lineno)
        prev_end = members[k - 1].end_lineno if k else cls.body[0].lineno - 1
        s = start
        while s - 1 > prev_end and lines[s - 2].strip().startswith("#"):
            s -= 1
        meth[b.name] = (s, b.end_lineno)
    owner = {m: blk for blk, (_, _, ms) in assign.items() for m in ms}
    unknown = [m for m in owner if m not in meth]
    if unknown:
        raise SystemExit(f"assigned methods not found: {unknown}")
    stay = [m for m in meth if m not in owner]
    print(f"{len(meth)} methods: {len(owner)} moved to {len(assign)} blocks, {len(stay)} stay: {stay}")
    if a.check:
        return
    for m in owner:
        s, e = meth[m]
        body = "\n".join(lines[s - 1:e])
        if "super()" in body or "global " in body:
            raise SystemExit(f"{m}: super() or global in a moved method: not handled")
    blocks_dir.mkdir(exist_ok=True)
    mod_name = Path(rel).stem
    for blk, (cname, doc, ms) in assign.items():
        body = []
        for m in sorted(ms, key=lambda m_: meth[m_][0]):          # the order of the module
            s, e = meth[m]
            body.append("\n".join(lines[s - 1:e]))
        text = (f'"""{doc}\n\n{cname_main}\'s methods, moved unchanged from {rel} (refactor stage 4a,\n'
                f'docs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are {mod_name}\'s, given to '
                f'this\nmodule once {mod_name} is loaded ({pkg}.inject); the annotations are not evaluated.\n"""\n'
                f"from __future__ import annotations\n\n\nclass {cname}:\n" + "\n\n".join(body) + "\n")
        # a block sits one folder below the module: the repository root is one parent further from __file__
        text = text.replace(f"__file__).resolve().parents[{depth}]", f"__file__).resolve().parents[{depth + 1}]")
        (blocks_dir / f"{blk}.py").write_text(text)
    init = (f'"""The blocks of {cname_main} (refactor stage 4a): mixins of {mod_name}.{cname_main}.\n\n'
            f"Their methods were moved unchanged from {mod_name}.py and use its module-level names: inject gives each "
            f"block module\nthose names once {mod_name} is loaded (a name a block defines itself is kept).\n\"\"\"\n"
            + "".join(f"from {pkg}.{b} import {c}  # noqa: F401\n" for b, (c, _, _) in assign.items())
            + "\nMODULES = (" + ", ".join(f'"{b}"' for b in assign) + ",)\n\n\n"
            "def inject(names: dict) -> None:\n"
            f"    \"\"\"Give every block module the names of {mod_name} (its globals), keeping the block's own.\"\"\"\n"
            "    import importlib\n"
            "    for b in MODULES:\n"
            f"        mod = importlib.import_module(f\"{pkg}.{{b}}\")\n"
            "        for k, v in names.items():\n"
            "            if not (k.startswith(\"__\") and k.endswith(\"__\")) and k not in mod.__dict__:\n"
            "                mod.__dict__[k] = v\n")
    (blocks_dir / "__init__.py").write_text(init)
    drop = set()
    for m in owner:
        s, e = meth[m]
        drop.update(range(s, e + 1))
    out = []
    names = ", ".join(c for c, _, _ in assign.values())
    for i, ln in enumerate(lines, start=1):
        if i in drop:
            continue
        if i == cls.lineno:
            out += [f"from {pkg} import (  # noqa: E402  (refactor stage 4a: the blocks)", f"    {names},", ")", "", "",
                    f"class {cname_main}({names}):"]
            continue
        out.append(ln)
    res, blank = [], 0
    for ln in out:
        blank = blank + 1 if not ln.strip() else 0
        if blank <= 2:
            res.append(ln)
    text = "\n".join(res).rstrip("\n") + "\n"
    text += (f"\n\n# refactor stage 4a: the blocks' methods see this module's names ({pkg.replace('.', '/')}/__init__.py)\n"
             f"from {pkg.rsplit('.', 1)[0]} import {pkg.rsplit('.', 1)[1]} as _blocks  # noqa: E402\n"
             "_blocks.inject(globals())\n")
    src_path.write_text(text)
    print("written:", ", ".join(f"{blocks_dir.relative_to(ROOT)}/{b}.py" for b in assign), "and", rel)


if __name__ == "__main__":
    main()
