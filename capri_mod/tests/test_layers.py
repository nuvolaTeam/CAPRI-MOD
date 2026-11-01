"""The layer rules of the supply, environment, fertiliser and water packages (docs/design/ARCHITECTURE_REFACTOR.md,
stages 3b and 4b): only the run's data adapter (capri_mod/data/inputs.py; the supply package's name for it,
capri_mod/supply/inputs.py) reads files, and the inputs follow the run's data directory and base year."""
import io
import tokenize
from pathlib import Path

SUPPLY = Path(__file__).resolve().parents[1] / "supply"
#: diagnostic dumps the solver writes on request (environment variables CAPRI_NLP_DUMP, CAPRI_TRACE_*): writes, not
#: inputs
WRITES = ("CAPRI_NLP_DUMP", "_fn, \"ab\"")


#: the packages that read their inputs through the run's data adapter (capri_mod/data/inputs.py): supply (stage 3b),
#: environment, fertiliser distribution and water (stage 4b)
PACKAGES = [SUPPLY] + [SUPPLY.parent / d for d in ("environmental", "fert", "water")]


def test_only_the_data_adapter_reads_files():
    offenders = []
    for p in sorted(q for d in PACKAGES for q in d.rglob("*.py")):
        if p.name == "inputs.py":
            continue
        toks = [t for t in tokenize.generate_tokens(io.StringIO(p.read_text()).readline)
                if t.type not in (tokenize.STRING, tokenize.COMMENT)]
        for a, b in zip(toks, toks[1:]):
            if (a.string in ("read_csv", "read_input", "open", "read_text", "read_json", "read_parquet")
                    and b.string == "(") or (a.string == "json" and b.string == ".") or a.string == "__file__":
                if any(w in a.line for w in WRITES):
                    continue
                offenders.append(f"{p.relative_to(SUPPLY.parent)}:{a.start[0]}: {a.line.strip()[:100]}")
    assert offenders == [], offenders


def test_inputs_follow_the_data_directory_and_base_year(tmp_path):
    from capri_mod.supply.inputs import SupplyInputs
    inp = SupplyInputs(tmp_path, "2030")
    assert inp.path("crop_cost_shares.csv", "supply") == tmp_path / "2030" / "supply" / "crop_cost_shares.csv"
    assert inp.path("n_cascade_region.csv", "abatement/ammonia") == tmp_path / "2030" / "abatement" / "ammonia" / \
        "n_cascade_region.csv"
    assert inp.path("npk_dataout_2030.csv.xz", "sources/environment") == tmp_path / "sources" / "environment" / \
        "npk_dataout_2030.csv.xz"
    assert inp.csv("crop_cost_shares.csv", "supply", required=False) is None
    import pytest
    with pytest.raises(FileNotFoundError):
        inp.csv("crop_cost_shares.csv", "supply")


def test_module_tables_are_read_from_the_run_inputs(tmp_path):
    """A table the supply code caches at module level comes from the inputs the run set, not a fixed path."""
    import pandas as pd
    from capri_mod.supply import inputs as I
    from capri_mod.supply import supply_module as sm
    saved = I.current()
    try:
        (tmp_path / "2017" / "supply").mkdir(parents=True)
        pd.DataFrame({"crop": ["SWHE"], "fert_cost_share": [0.25]}).to_csv(
            tmp_path / "2017" / "supply" / "crop_cost_shares.csv", index=False)
        I.use(I.SupplyInputs(tmp_path, "2017"))
        assert sm.RegionalSupplyModel.FERT_COST_SHARE == {"SWHE": 0.25}
        I.use(I.SupplyInputs())
        assert sm.RegionalSupplyModel.FERT_COST_SHARE != {"SWHE": 0.25}
    finally:
        I.use(saved)


def test_a_missing_supply_input_stops_the_run(tmp_path):
    """A required input that is missing raises, naming the file (stage 3b; before, several tables fell back to none,
    some with a warning, some silently)."""
    import pytest
    from capri_mod.supply import inputs as I
    from capri_mod.supply import supply_module as sm
    saved = I.current()
    try:
        I.use(I.SupplyInputs(tmp_path, "2017"))
        with pytest.raises(FileNotFoundError, match="fert_options_jul15.csv"):
            sm.fert_option_table()
        with pytest.raises(FileNotFoundError, match="fert_side_effects.csv"):
            sm.fert_side_value("DK000000", "NITR_INH", "N2O")
    finally:
        I.use(saved)
