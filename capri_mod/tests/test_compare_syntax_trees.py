"""tools/check/compare_syntax_trees.py (the code quality plan, steps 6 and 8): a change of comments or layout leaves
the syntax tree as it was, a change of code does not; docstrings exact, normalised (a formatter's re-indentation) or
ignored."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("compare_syntax_trees", ROOT / "tools" / "check" / "compare_syntax_trees.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

SRC = '''def f(x, y):
    """The sum.

        Indented line."""
    # a comment
    return x + y   # trailing comment
'''


def test_comments_and_layout_leave_the_tree():
    shortened = SRC.replace("    # a comment\n", "").replace("   # trailing comment", "")
    reflowed = SRC.replace("return x + y", "return (x +\n            y)")
    assert T.same_tree(SRC, shortened) and T.same_tree(SRC, reflowed)


def test_a_change_of_code_changes_the_tree():
    assert not T.same_tree(SRC, SRC.replace("x + y", "y + x"))      # an operand order is code (floats)
    assert not T.same_tree(SRC, SRC.replace("x + y", "x + y + 0"))


def test_the_docstring_modes():
    reindented = SRC.replace("        Indented line.", "    Indented line.")
    reworded = SRC.replace("The sum.", "The total.")
    assert not T.same_tree(SRC, reindented, "exact") and T.same_tree(SRC, reindented, "normalised")
    assert not T.same_tree(SRC, reworded, "normalised") and T.same_tree(SRC, reworded, "ignored")


def test_the_command_on_the_repository():
    assert T.main(["HEAD", "HEAD"]) == 0
