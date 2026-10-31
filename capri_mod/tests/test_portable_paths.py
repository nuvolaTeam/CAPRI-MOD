"""Every file of the repository runs on any machine: no file names a folder of a particular machine.

CAPRI's material outside git is found relative to the repository (capri_sources/, capri_reference/; tools/lib/paths.py,
docs/EXTERNAL_SOURCES.md). A path such as /home/<user>/..., /mnt/..., /Users/<user>/..., C:\\Users\\... or a session's
temporary folder in a delivered file works only where it was written, so the test lists every one.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: a folder of one machine: a user's home, a mount, a session's scratch folder, root's home
MACHINE = re.compile(r"(?<![\w.$])(/home/\w+|/mnt/[\w-]+|/Users/\w+|[A-Za-z]:\\\\?Users|/tmp/claude|/root/(?!\.cache\b))")
#: the text files checked (the data files are values, checked by their declarations)
SUFFIXES = (".py", ".toml", ".json", ".gms", ".sh", ".cfg", ".yml", ".yaml", ".md", ".sql", ".txt", ".cff")
#: (file, the line's text) of the only allowed occurrences: system prefixes that the file-access traces leave out
ALLOWED = {
    ("capri_mod/run_manifest.py", '"/usr", "/proc", "/sys", "/dev", "/etc", "/lib", "/opt/conda", "/root/.cache")'),
    ("tools/check/reproduce_builders.py",
     '_SKIP = ("/usr/", "/proc/", "/sys/", "/dev/", "/etc/", "/lib", "/opt/", "/root/", "/var/", "/run/")'),
    ("capri_mod/tests/test_portable_paths.py", None),
}


def _files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    return [f for f in out if f.endswith(SUFFIXES) and (ROOT / f).is_file()]


def test_no_file_names_a_machine_folder():
    found = []
    for f in _files():
        if (f, None) in ALLOWED:
            continue
        for i, line in enumerate((ROOT / f).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if MACHINE.search(line) and (f, line.strip()) not in ALLOWED:
                found.append(f"{f}:{i}: {line.strip()[:120]}")
    assert not found, f"{len(found)} lines name a folder of one machine:\n" + "\n".join(found[:40])


#: programs outside Python that a delivered .py file may run: git (the repository's own), strace (the builder trace,
#: Linux, checked before use) and pdftotext (one validation builder, checked before use); docs/EXTERNAL_SOURCES.md
PROGRAMS_ALLOWED = {"git", "strace", "pdftotext"}
_RUN = re.compile(r"""(?:subprocess\.\w+|_sp\w*\.\w+)\(\s*\[\s*["']([\w.-]+)["']""")


def test_no_file_runs_a_unix_tool():
    """No .py file runs a shell or a Unix tool (grep, unzip, awk, ...): they do not exist on every system; Python's
    standard library does the same (tools/lib/_grep.py)."""
    found = []
    for f in _files():
        if not f.endswith(".py"):
            continue
        text = (ROOT / f).read_text(encoding="utf-8", errors="replace")
        for m in _RUN.finditer(text):
            if m.group(1) not in PROGRAMS_ALLOWED:
                found.append(f"{f}: runs {m.group(1)}")
        if "shell=True" in text or "os.system(" in text:
            if f != "capri_mod/tests/test_portable_paths.py":
                found.append(f"{f}: runs a shell")
    assert not found, "\n".join(found)
