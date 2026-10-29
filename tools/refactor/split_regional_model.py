"""Refactor stage 3a (docs/design/ARCHITECTURE_REFACTOR.md): the regional supply model's methods moved, unchanged, from
capri_mod/supply/supply_module.py into one module per block (capri_mod/supply/blocks/), the blocks mixins of
RegionalSupplyModel, as stage 1 did for the market. A move only: every method's text is copied as it is (with the
comment lines directly above it), the class attributes stay on RegionalSupplyModel, and the blocks see supply_module's
module-level names, which supply_module gives them once it is loaded (blocks/__init__.py, inject).

    python tools/refactor/split_regional_model.py          # writes the blocks and rewrites supply_module.py
    python tools/refactor/split_regional_model.py --check  # lists the assignment, writes nothing

Run once. The check of the move is a run identical to the reference (tools/check/compare_pickles_exact.py) and the
test suite.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_mod" / "supply" / "supply_module.py"
BLOCKS = ROOT / "capri_mod" / "supply" / "blocks"

#: block -> (class name, docstring, methods)
ASSIGN = {
    "livestock": ("LivestockBlock",
                  "Animals in the regional model: the young-animal coefficients, columns and markets' response, the "
                  "intensity and member splits of cattle, dairy and grassland (CAPRI's split activities), genetics, the "
                  "fodder rows, the cake index and protein feed cost, the animals' cost per head.",
                  ["_young_animal_coefs", "young_animal_columns", "_yani_response", "_apply_young_animal_prices",
                   "_grass_intensity_column", "_dairy_intensity_column", "_split_pending", "_split_record",
                   "_cattle_columns", "cattle_split_hessian", "_cattle_calibrate_from_duals", "_genetics_columns",
                   "_genetics_calibrate_from_duals", "_dairy_column_only", "_dairy_calibrate_from_duals",
                   "_grass_calibrate_from_duals", "_fodder_rows", "_animal_cost_per_head", "_cake_index",
                   "_protein_feed_cost_change"]),
    "fertilisation": ("FertilisationBlock",
                      "Fertilisation and nitrogen in the regional model: CAPRI's NPK block (NUTNED_, the purchases, "
                      "the organic and mineral caps, the fertiliser options), the emission factors of mineral N, the N "
                      "balance price and tiered surplus target with JRC121368's relaxation, the nitrate terms.",
                      ["_mctx", "_ef_mineral_n2o", "_ef_mineral_lea", "_ef_nh3_n2o", "_need_yf", "_yields_scen_now",
                       "_crop_mineral_now", "_fert_tax_terms", "_tech_list", "_npk_spec", "_npk_base_alloc",
                       "_npk_organic_cap", "_merge_organic_regs", "_npk_mineral_cap", "_n_row_mineral_parts",
                       "_npk_recalibrate_priors", "_npk_applied_ratio", "_crop_mineral_rate", "_fert_params_raw",
                       "_fert_alloc_params", "_nitrate_extra", "_nitrate_row_term", "_apply_balance_price",
                       "tiered_surplus_target", "_relax_n_target", "_n_relax_key"]),
    "abatement": ("AbatementBlock",
                  "Mitigation in the regional model: the ammonia technologies, manure techniques and inhibitors, the "
                  "winter cover (catch crops), the GHG price terms, histosol fallowing.",
                  ["_techs_inside", "_amm_context", "_amm_scale", "_amm_incentive", "_catc_spec",
                   "_nlp_abatement_spec", "_nlp_tax_terms", "_manure_techs", "_winter_cover_shares", "_amm_record",
                   "_apply_manure_techs", "_apply_manure_inhibitor", "_ni_inside", "_manure_inhibitor_params",
                   "_manure_inhibitor_tax_value", "_cover_n_increment", "_cover_crop_requirement", "_ghg_cost",
                   "_apply_ghg_tax", "_ghg_feed_cost", "_histosol_base_area", "_histosol_columns",
                   "_histosol_calibrate_from_duals"]),
    "policy": ("PolicyBlock",
               "Policy rules in the regional model: CAP greening and crop diversification, the organic area target and "
               "yield gaps, the pesticide reduction, the Green Deal input changes, the yield response to prices and its "
               "input costs.",
               ["_cap_rules_spec", "_organic_baseline", "_input_cost", "apply_pesticide_reduction",
                "yield_price_elasticity", "apply_yield_price_response", "_organic_yield_gap",
                "_organic_yield_gap_uncached", "_organic_target_scale", "_organic_region_target",
                "_organic_crop_target", "_input_row", "_greendeal_tech_progress", "_apply_greendeal_input_changes",
                "_apply_yield_input_costs", "_organic_converted", "apply_organic_area_target"]),
    "land": ("LandBlock",
             "Land in the regional model: CAPRI's land market (the land types as variables, Trustee_land).",
             ["_land_of", "_land_augment"]),
    "nlp": ("NLPBlock",
            "The regional model's solve in CAPRI's form (capri_regional_nlp.CapriRegionalNLP with IPOPT): the build, "
            "the starts, the warm and jump checks, the mineral-cap exemptions, the last-point fallback.",
            ["_aug_col_labels", "_nlp_mine_fingerprint", "_nlp_relax_spec", "_nlp_cap_shortfall", "_capri_nlp_solve",
             "_nlp_solve", "_note_floor_failure", "_nlp_last_point"]),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    src = SRC.read_text()
    lines = src.split("\n")
    tree = ast.parse(src)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "RegionalSupplyModel")
    members = list(cls.body)
    meth = {}
    for k, b in enumerate(members):
        if not isinstance(b, ast.FunctionDef):
            continue
        start = (b.decorator_list[0].lineno if b.decorator_list else b.lineno)
        prev_end = members[k - 1].end_lineno if k else cls.body[0].lineno - 1
        # the comment lines directly above the method (no blank line between) go with it
        s = start
        while s - 1 > prev_end and lines[s - 2].strip().startswith("#"):
            s -= 1
        meth[b.name] = (s, b.end_lineno)
    owner = {m: blk for blk, (_, _, ms) in ASSIGN.items() for m in ms}
    unknown = [m for m in owner if m not in meth]
    if unknown:
        raise SystemExit(f"assigned methods not found: {unknown}")
    stay = [m for m in meth if m not in owner]
    print(f"{len(meth)} methods: {len(owner)} moved to {len(ASSIGN)} blocks, {len(stay)} stay: {stay}")
    if a.check:
        return
    BLOCKS.mkdir(exist_ok=True)
    for blk, (cname, doc, ms) in ASSIGN.items():
        body = []
        for m in sorted(ms, key=lambda m_: meth[m_][0]):          # the order of supply_module.py
            s, e = meth[m]
            body.append("\n".join(lines[s - 1:e]))
        text = (f'"""{doc}\n\nRegionalSupplyModel\'s methods, moved unchanged from capri_mod/supply/supply_module.py (refactor '
                f'stage 3a,\ndocs/design/ARCHITECTURE_REFACTOR.md); the module-level names they use are supply_module\'s, '
                f'given to\nthis module once supply_module is loaded (capri_mod.supply.blocks.inject); the annotations are '
                f'not evaluated\n(they name supply_module\'s types).\n"""\nfrom __future__ import annotations\n\n\n'
                f"class {cname}:\n" + "\n\n".join(body) + "\n")
        (BLOCKS / f"{blk}.py").write_text(text)
    init = ('"""The regional supply model\'s blocks (refactor stage 3a): mixins of supply_module.RegionalSupplyModel.\n\n'
            "Their methods were moved unchanged from supply_module.py and use its module-level names (numpy as np, the "
            "settings,\nthe data tables' readers, SupplyModule, ...): inject gives each block module those names once "
            "supply_module is\nloaded (a name a block defines itself is kept).\n\"\"\"\n"
            + "".join(f"from capri_mod.supply.blocks.{b} import {c}  # noqa: F401\n" for b, (c, _, _) in ASSIGN.items())
            + "\nMODULES = (" + ", ".join(f'"{b}"' for b in ASSIGN) + ",)\n\n\n"
            "def inject(names: dict) -> None:\n"
            "    \"\"\"Give every block module the names of supply_module (its globals), keeping the block's own.\"\"\"\n"
            "    import importlib\n"
            "    for b in MODULES:\n"
            "        mod = importlib.import_module(f\"capri_mod.supply.blocks.{b}\")\n"
            "        for k, v in names.items():\n"
            "            if not (k.startswith(\"__\") and k.endswith(\"__\")) and k not in mod.__dict__:\n"
            "                mod.__dict__[k] = v\n")
    (BLOCKS / "__init__.py").write_text(init)
    # supply_module: the moved methods out, the class from the blocks, the names given at the end
    drop = set()
    for m in owner:
        s, e = meth[m]
        drop.update(range(s, e + 1))
    out = []
    for i, ln in enumerate(lines, start=1):
        if i in drop:
            continue
        if i == cls.lineno:
            out.append("from capri_mod.supply.blocks import (  # noqa: E402  (refactor stage 3a: the blocks)")
            out.append("    " + ", ".join(c for c, _, _ in ASSIGN.values()) + ",")
            out.append(")")
            out.append("")
            out.append("")
            out.append("class RegionalSupplyModel(" + ", ".join(c for c, _, _ in ASSIGN.values()) + "):")
            continue
        out.append(ln)
    # collapse the runs of blank lines the removals left (more than two in a row)
    res, blank = [], 0
    for ln in out:
        blank = blank + 1 if not ln.strip() else 0
        if blank <= 2:
            res.append(ln)
    text = "\n".join(res).rstrip("\n") + "\n"
    text += ("\n\n# refactor stage 3a: the blocks' methods see this module's names (capri_mod/supply/blocks/__init__.py)\n"
             "from capri_mod.supply import blocks as _blocks  # noqa: E402\n"
             "_blocks.inject(globals())\n")
    SRC.write_text(text)
    print("written:", ", ".join(f"blocks/{b}.py" for b in ASSIGN), "and supply_module.py")


if __name__ == "__main__":
    main()
