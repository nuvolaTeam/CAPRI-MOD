# tools/

Scripts around the model, by role. Run every tool from the repository root, e.g.
`python tools/run/run_f2f_2030.py OUT.pkl`.

| Folder | Content |
|---|---|
| `build/` | Builders of the model's data files in `capri_data/` (and of the CAPRI reference copies in `capri_reference/`). Each data file names its builder in `capri_data/DATA_SOURCING_REGISTRY.json` or in its own docstring. |
| `run/` | Model runs: `run_f2f_2030.py` (Farm-to-Fork / Green Deal 2030), `run_vcs_2030.py`, `run_policy_comparison.py`, and the test runner `run_tests.py` (used by the Dockerfile). |
| `check/` | Comparisons with CAPRI and diagnostics. They write only reports (`capri_data/validation/`, or paths given on the command line). |
| `gams/` | GAMS export scripts to run in a CAPRI installation; they produce the extracts the builders read. |
| `lib/` | Modules shared by the tools: `_model_regions.py` (model ↔ CAPRI regions), `_capri_costsavings.py`, and `paths.py`. `paths.py` finds the repository root and any tool by name (`tool_file`, `load_tool`). |

A tool that imports another adds the folders to `sys.path`:

```
sys.path[:0] = [str(ROOT / "tools" / d) for d in ("lib", "build", "run", "check")]
```

or loads it by name with `paths.tool_file` or `paths.load_tool`. ROOT is the repository root:
`Path(__file__).resolve().parents[2]` from a file in one of these folders.

## Reorganised on 23 October 2026

The 166 files of the flat `tools/` folder were moved into these folders. Every reference was updated: imports,
paths, subprocess calls, tests, the Dockerfile, docs and data catalogues. Docs and code comments that describe
history may still name a removed tool.

**Removed: no longer used, superseded, or one-off migrations already applied.**
- **Superseded GAMS and shell exports:**
  - `dump_all_res.gms`, `extract_capreg.gms`: replaced by `gams/dump_capreg_explicit.gms`;
  - `dump_capmod_market.gms`: replaced by `gams/dump_capmod_base1717.gms`;
  - `dump_remaining_four.gms`: replaced by `gams/dump_remaining_corrected.gms`;
  - `extract_capri_remaining.sh`: an early version of the exports, its outputs read by nothing.
- **Report generators with fixed text about an early data state:** `build_reference.py`, `build_report.py` (they
  wrote PDFs outside the repository).
- **Diagnostics that no longer work:**
  - `checks/ad_check.py`, hard-coded to another copy of the repository; its logic is in
    `build/build_ad_option.py`;
  - `diag_n_abatement.py`, which set attributes the model no longer has.
- **One-off migrations, already applied:** `build_pig_split.py` (its tables are rebuilt by the regular builders; `build_shg_split.py`, the sheep-and-goat
  split, retired on 29 October 2026 once a rebuild without it reproduced every file), `build_tabo_split.py`, `build_text_merge.py`, `merge_coco_yields.py`, `merge_capreg_yields.py`,
  `validate_capreg_yields.py`, `normalize_activity_codes.py`. Today's builders write the files these patched. Their
  reports in `capri_data/validation/` are kept as the record.
- **Builders of files no code reads:**
  - `build_genetics_milk.py` and its `genetics_milk_yield.csv`;
  - `extract_armington_from_source.py` and its `sources/capri_source/capri_armington_*` (the Armington terms come
    from `build/build_bilateral_market.py`).

**Kept as a record although nothing reads its output:** `gams/dump_elas1717.gms`, the only record of how
`capri_supply_elas_market_1717.csv` was extracted.
