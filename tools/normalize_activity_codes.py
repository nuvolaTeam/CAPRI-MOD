"""
Fix 1 — normalise the 'other animals' activity code to CAPRI's canonical `OANI`.

Four spellings were found in the codebase, none of which agreed with CAPRI:

  OANI    U+004F 41 4E 49              canonical (capreg/regio_sets.gms) - reference files only
  OАНИ    U+004F 0410 041D 0418        Cyrillic homoglyph corruption     - definitions/loaders/data
  OANII   U+004F 41 4E 49 49           ASCII, doubled I                  - feed module, prices
  OАНИИ   U+004F 0410 041D 0418 49     Cyrillic + doubled I              - environmental module

Because the canonical activity list in definitions.py used the Cyrillic form while
the feed and environmental modules used the doubled-I forms, every 'other animals'
lookup silently missed and fell through to a default. This rewrites all variants to
`OANI` across code and data.

Idempotent: safe to re-run.
"""
from __future__ import annotations
import pathlib, sys

CANON = "OANI"
# longest first so OANII is not eaten by OANI
VARIANTS = [
    "O\u0410\u041d\u0418I",   # Cyrillic + doubled I
    "O\u0410\u041d\u0418",    # Cyrillic
    "OANII",                  # ASCII doubled I
]
SUFFIXES = {".py", ".csv", ".json", ".md"}
SKIP_DIRS = {".git", "__pycache__", "tools"}


def normalize(root: pathlib.Path) -> list[tuple[str, int]]:
    changed = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        n = sum(text.count(v) for v in VARIANTS)
        if not n:
            continue
        for v in VARIANTS:
            text = text.replace(v, CANON)
        p.write_text(text, encoding="utf-8")
        changed.append((str(p.relative_to(root)), n))
    return changed


if __name__ == "__main__":
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    changed = normalize(root)
    for f, n in changed:
        print(f"  {n:3d}  {f}")
    print(f"\n{len(changed)} files normalised, "
          f"{sum(n for _, n in changed)} occurrences -> {CANON}")
