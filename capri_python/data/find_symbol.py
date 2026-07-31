"""
CAPRI symbol finder — solves the "which symbol do I need out of hundreds?" problem.

Two capabilities:
  1. search(keyword)         — find CAPRI symbols by keyword, with descriptions
                               (from capri_symbol_dictionary.json, built from the
                                GAMS source: 2400+ symbols -> human-readable text)
  2. list_gdx(path)          — list the actual symbols present in a GDX file
                               (names + dims, via gdx_parser) so you can confirm a
                               symbol is in YOUR results database before exporting

Typical workflow to fill a model input from a CAPRI results GDX:
    python find_symbol.py search fertiliser
    # -> p_FertPerHa  "Fertiliser use per ha for CAPRI regions"
    python find_symbol.py gdx  output/results/capreg/res_time_series.gdx
    # -> confirm p_FertPerHa is present
    # then in GAMS:  gdxdump res_time_series.gdx symb=p_FertPerHa format=csv > fert.csv
"""
import sys, json, re
from pathlib import Path

DICT_PATH = Path(__file__).parent / "capri_symbol_dictionary.json"


def load_dict():
    if DICT_PATH.exists():
        return json.load(open(DICT_PATH))
    return {}


def search(keyword, limit=15):
    d = load_dict()
    kw = keyword.lower()
    hits = []
    for sym, desc in d.items():
        score = 0
        if kw in sym.lower():
            score += 2
        if kw in desc.lower():
            score += 1
        if score:
            hits.append((score, sym, desc))
    # prefer data parameters (p_) and name matches
    hits.sort(key=lambda x: (-x[0], not x[1].startswith("p_"), len(x[1])))
    if not hits:
        print(f"No symbols match '{keyword}'.")
        return
    print(f"Symbols matching '{keyword}':\n")
    for _, sym, desc in hits[:limit]:
        print(f"  {sym:30s} {desc}")


def list_gdx(path):
    """List symbols actually present in a GDX file (names + dims)."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from gdx_parser import GDXFile  # the project's parser
        gdx = GDXFile(path)
        d = load_dict()
        print(f"Symbols in {path}:\n")
        for s in gdx.symbols:
            name = getattr(s, "name", str(s))
            ndim = getattr(s, "ndims", "?")
            desc = d.get(name, "")
            print(f"  {name:30s} dims={ndim}  {desc[:60]}")
    except Exception as e:
        print(f"Could not read GDX ({e}).")
        print("Tip: export the symbol with GAMS gdxdump instead:")
        print("  gdxdump FILE.gdx symb=SYMBOL format=csv > out.csv")


# Curated map: model input file -> best CAPRI symbol(s) to fill it
MODEL_NEEDS = {
    "feed_requirements.csv": [
        ("p_feedInpCoeff", "feed input coefficients (fresh matter) by activity"),
        ("v_feedInpCoeff", "feeding per head and year in kg"),
    ],
    "nutrient_coefs.csv": [
        ("p_FertPerHa", "fertiliser use per ha for CAPRI regions"),
        ("v_minfert", "N input from mineral fertilizers [kg/ha]"),
    ],
    "base_areas.csv / yields.csv": [
        ("p_nutsLevl", "given hectares at NUTS-2 level"),
        ("p_regioData", "regional database (areas, yields, herds)"),
    ],
    "producer_prices.csv / world_prices.csv": [
        ("p_price", "prices"),
        ("(fao_dataMarket.gdx)", "market SUA prices+balances for a newer base"),
    ],
    "biofuel coefficients (module)": [
        ("p_bioDat", "consolidated biofuel data from AGLINK and FO LICHT"),
        ("p_bioDemPar", "biofuel demand function parameters"),
    ],
}


def needs():
    print("Model input  ->  CAPRI symbol to export from your results GDX:\n")
    for fn, syms in MODEL_NEEDS.items():
        print(f"  {fn}")
        for s, d in syms:
            print(f"      {s:20s} {d}")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python find_symbol.py search <keyword>")
        print("  python find_symbol.py gdx <path-to.gdx>")
        print("  python find_symbol.py needs")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "search" and len(sys.argv) > 2:
        search(sys.argv[2])
    elif cmd == "gdx" and len(sys.argv) > 2:
        list_gdx(sys.argv[2])
    elif cmd == "needs":
        needs()
    else:
        print("Unknown command. Use: search <kw> | gdx <path> | needs")
