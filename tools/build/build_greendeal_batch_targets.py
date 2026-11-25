"""CAPRI's Green Deal targets by simulation year of its production series (register DEP-20): section "f2f" of the
batch file of CAPRI's Green Deal production runs (GUI/batchfiles/greendeal_scen2.txt, author P. Witzke).

The batch sets the Green Deal group's GUI settings before its loop over the simulation years (the section's values)
and again inside the loop, one block per year (IF %curYear%=2025 ... ENDIF), phasing the targets in: 2025, 2030,
2035, 2040 and 2050. A setting is a GUI control's title (``Organic agriculture target = 18``); the control's GAMS name
is the GUI definition's (GUI/capri_gui_definition.xml, <title> and <gamsName>), and the settings of the group are
those of CAPRI's scenario name (pol_input/greendeal/greendeal_scenarios.gms l. 192: lndscpTarg, orgTarg, pestRedu,
mineRedu, surpRedu, dietShift, othPol). A year's value is its block's, else the section's. Lines starting with "*" are
comments of the batch (its earlier choices), not read.

Check: each year's block names the result of the year before as its reference for carbon accounting
(``Reference scenario for carbon accounting = res_2_%bas%25greendeal_lnds7_org15_pest13_mine10crp_surp20_diet00
_oth00defaultA``); where that year is in the table, the name must be CAPRI's scenario name of its targets
(greendeal_scenarios.gms l. 192-193). The builder stops if one is not.

The years after 2050 (2060, 2070) have blocks without targets: in the batch's loop they keep the values set last,
2050's (the 2070 block's reference, the 2060 result, is named lnds10_org25_pest32_mine20crp_surp50); they are not rows
of the table.

Sources: capri_sources/gui/batchfiles/greendeal_scen2.txt and capri_sources/gui/capri_gui_definition.xml (CAPRI's GUI
folder, GUI.zip), capri_sources/gams/pol_input/greendeal/greendeal_scenarios.gms.

Output: capri_data/scenarios/greendeal_group/greendeal_targets_by_year.csv
    year, lndscpTarg, orgTarg, pestRedu, mineRedu, surpRedu, dietShift, othPol (the values as the batch writes them)

    python tools/build/build_greendeal_batch_targets.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import SOURCES, need  # noqa: E402  (CAPRI's material outside the repository)

BATCH = SOURCES / "gui" / "batchfiles" / "greendeal_scen2.txt"
GUI_DEF = SOURCES / "gui" / "capri_gui_definition.xml"
GMS = SOURCES / "gams" / "pol_input" / "greendeal" / "greendeal_scenarios.gms"
OUT = ROOT / "capri_data" / "scenarios" / "greendeal_group" / "greendeal_targets_by_year.csv"
#: the batch's section of the series
SECTION = "f2f"


def gui_gams_names(xml_path) -> dict:
    """{GUI title: GAMS name} of CAPRI's GUI controls (capri_gui_definition.xml: <control> with <title> and <gamsName>;
    the titles are unique)."""
    out = {}
    for c in ET.parse(xml_path).getroot().iter("control"):
        t, g = (c.findtext("title") or "").strip(), (c.findtext("gamsName") or "").strip()
        if t and g:
            if t in out and out[t] != g:
                raise ValueError(f"GUI title {t!r} has two GAMS names: {out[t]}, {g}")
            out[t] = g
    return out


def scenNameFromGroup(gms_text: str):
    r"""CAPRI's name of a Green Deal scenario from its settings, and the settings it names.

    CAPRI's GAMS (pol_input/greendeal/greendeal_scenarios.gms l. 139, 192-193):

        $setglobal gdversion
        $setglobal scenNameFromGroup  greendeal%gdversion%_lnds%lndscpTarg%_org%orgTarg%_pest%pestRedu%_mine%mineRedu%_surp%surpRedu%_diet%dietShift%_oth%othPol%
        $ifi %scenNameFromGroup%==greendeal%gdversion%_lnds00_org00_pest00_mine00_surp00_diet00_oth00 $setglobal scenNameFromGroup greendeal_reference

    Returns (name(values), the GAMS names in the template's order); %gdversion% empty (l. 139)."""
    m = re.search(r"^\$setglobal\s+scenNameFromGroup\s+(\S+)\s*$", gms_text, re.M | re.I)
    if not m:
        raise ValueError("greendeal_scenarios.gms: no $setglobal scenNameFromGroup")
    tmpl = m.group(1).replace("%gdversion%", "")
    keys = re.findall(r"%(\w+)%", tmpl)

    def name(values: dict) -> str:
        s = tmpl
        for k in keys:
            s = s.replace(f"%{k}%", str(values[k]))
        ref = tmpl
        for k in keys:
            ref = ref.replace(f"%{k}%", "00")
        return "greendeal_reference" if s.lower() == ref.lower() else s
    return name, keys


def batch_section(lines, flag: str):
    """The lines of the batch's section IF %<flag>% = ON ... its ENDIF (nested IF blocks kept)."""
    start = next((i for i, l in enumerate(lines) if re.match(rf"\s*IF\s+%{flag}%\s*=\s*ON\s*$", l, re.I)), None)
    if start is None:
        raise ValueError(f"batch: no section IF %{flag}% = ON")
    depth, out = 0, []
    for l in lines[start:]:
        s = l.strip()
        if s.startswith("*"):
            out.append(l)
            continue
        if re.match(r"IF\s", s, re.I):
            depth += 1
        elif re.match(r"ENDIF\b", s, re.I):
            depth -= 1
            if depth == 0:
                return out[1:]
        out.append(l)
    raise ValueError(f"batch: section {flag} has no ENDIF")


def section_settings(sec, titles: dict, keys):
    """The section's values (before the years' blocks), each year's block's, and each block's reference for carbon
    accounting. Settings: ``<GUI title> = <value>`` lines not commented out; only the scenario name's settings."""
    base, years, refs, year = {}, {}, {}, None
    for l in sec:
        s = l.strip()
        if not s or s.startswith("*"):
            continue
        m = re.match(r"IF\s+%curYear%\s*=\s*(\d{4})\s*$", s, re.I)
        if m:
            year = int(m.group(1))
            years.setdefault(year, {})
            continue
        if re.match(r"ENDIF\b", s, re.I):
            year = None
            continue
        m = re.match(r"(.+?)\s*=\s*(.*?)\s*$", s)
        if not m:
            continue
        k, v = m.group(1).strip(), m.group(2).strip()
        if k == "Reference scenario for carbon accounting" and year is not None:
            refs[year] = v
        g = titles.get(k)
        if g in keys:
            (years[year] if year is not None else base)[g] = v
    return base, years, refs


def main(check: bool = False):
    titles = gui_gams_names(need(GUI_DEF, "CAPRI's GUI definition"))
    name, keys = scenNameFromGroup(need(GMS, "CAPRI's greendeal_scenarios.gms").read_text(errors="replace"))
    lines = need(BATCH, "CAPRI's Green Deal production batch").read_text(errors="replace").splitlines()
    m = next((re.match(r"\s*MACRO\s*=\s*bas\s+(\d+)\s*$", l, re.I) for l in lines
              if re.match(r"\s*MACRO\s*=\s*bas\s", l, re.I)), None)
    bas = m.group(1) if m else None
    base, years, refs = section_settings(batch_section(lines, SECTION), titles, keys)
    missing = [k for k in keys if k not in base]
    if missing:
        raise ValueError(f"section {SECTION}: no value of {missing} before the years' blocks")
    rows = []
    for y in sorted(years):
        if not years[y]:
            continue                        # a block without targets (2060, 2070): not a row
        rows.append({"year": y, **{k: years[y].get(k, base[k]) for k in keys}})
    by_year = {r["year"]: r for r in rows}
    n_chk = 0
    for y, ref in sorted(refs.items()):
        m = re.match(r"res_2_%bas%(\d\d)(\S+?)defaultA$", ref)
        if not m:
            raise ValueError(f"{y}: reference {ref!r} is not CAPRI's result name form")
        prev = 2000 + int(m.group(1))
        if prev in by_year:
            want = name(by_year[prev])
            if m.group(2) != want:
                raise ValueError(f"{y}: its reference {m.group(2)} is not the {prev} targets' name {want}")
            n_chk += 1
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["year"] + keys, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    text = buf.getvalue()
    print(f"section {SECTION} (bas {bas}): {len(rows)} years; {n_chk} references are the year before's scenario name")
    print(text, end="")
    if check:
        if OUT.read_text() != text:
            raise SystemExit(f"{OUT.relative_to(ROOT)} differs from the batch")
        print("unchanged:", OUT.relative_to(ROOT))
        return
    OUT.write_text(text)
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    main(ap.parse_args().check)
