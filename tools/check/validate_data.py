"""The data checks' command line, kept at this path for the gates, dodo.py and the documents: the code is
capri_mod/data/validate_data.py (moved there on 31 October 2026, with the model's data definitions and loaders).

    python tools/check/validate_data.py [--root DIR] [--db FILE]      (or: python -m capri_mod.data.validate_data)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from capri_mod.data.validate_data import *  # noqa: E402,F401,F403
from capri_mod.data.validate_data import check_table, layout, main, parse, validate  # noqa: E402,F401

if __name__ == "__main__":
    main()
