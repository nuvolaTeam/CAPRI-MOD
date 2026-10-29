"""Shared helpers for builders: the model's regions and the CAPRI national-code fallback.

Since 27 October 2026 the model's regions are CAPRI's regional units under CAPRI's own codes
(capri_data/shared/regional_units.csv): each region is its own CAPRI region, including the units of the member states
without regional detail, whose code is the member state's (DK000000, EE000000, ...). capri_groups and region_to_capri
are then the identity. The NUTS correspondence below is kept only for regions that are not CAPRI units (none in the
model's data; the functions refuse a mixed list).
"""
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[2]
# CAPRI member-state codes (sets.gms NUTS0: BL = Belgium and Luxembourg, IR, EL, UK), the table the model uses
# (capri_mod.data.definitions.MS_CODE)
with open(ROOT / "capri_data" / "shared" / "capri_member_state_codes.csv", newline="") as _f:
    CTRY = {r["nuts_prefix"]: r["capri_ms"][:2] for r in csv.DictReader(_f)}


with open(ROOT / "capri_data" / "shared" / "regional_units.csv", newline="") as _f:
    UNITS = [r["region"] for r in csv.DictReader(_f)]
UNIT_SET = frozenset(UNITS)


def is_unit(code: str) -> bool:
    """A CAPRI regional unit of the model (a NUTS-2 unit, or a member state without regional detail: DK000000)."""
    return code in UNIT_SET


def regional_row(code: str) -> bool:
    """A CAPRI row that is a regional unit's own: every code not ending in 000000, and the member-state codes that are
    units (DK000000, ...). For a builder's 'regional rows, not national totals' test."""
    return not code.endswith("000000") or code in UNIT_SET


def _all_units(regs) -> bool:
    regs = list(regs)
    n = sum(1 for r in regs if r in UNIT_SET)
    if 0 < n < len(regs):
        raise ValueError(f"mixed region list: {n} CAPRI units and {len(regs) - n} other codes")
    return n > 0


def model_regions():
    """The model's regional units in their order: capri_data/shared/regional_units.csv (the model's areas are indexed
    the same, checked by tests). Until 29 October 2026 the model's whole data were loaded for this list, so every
    builder calling it opened about 80 model inputs, its own outputs among them (docs/design/DATA_PIPELINE_DOIT.md)."""
    import csv
    with open(ROOT / "capri_data" / "shared" / "regional_units.csv", newline="") as fh:
        return [r["region"] for r in csv.DictReader(fh)]


def national_code(nuts2: str) -> str:
    return CTRY.get(nuts2[:2], nuts2[:2]) + "000000"


#: model region -> CAPRI region(s), for NUTS changes the correspondence file leaves out (it keeps
#: only one-to-one matches verified by area): NUTS 2013 FI1D = FI13 + FI1A, FI1B + FI1C = FI18
#: (Etelae-Suomi 2006); ITH1/ITH2 Bolzano/Trento = CAPRI's Trentino-Alto Adige IT31; Saxony's
#: DED2/4/5 = DED0; PL72/81/82/84 renamed (2016) from PL33/31/32/34, PL91/92 split from PL12;
#: HU11/HU12 split from HU10; Ireland 2016: IE04 within IE01, IE05 within IE02, IE06 = parts of both
SPLITS_MERGES = {
    "FI1D": ("FI130000", "FI1A0000"), "FI1B": ("FI180000",), "FI1C": ("FI180000",),
    "ITH1": ("IT310000",), "ITH2": ("IT310000",),
    "DED2": ("DED00000",), "DED4": ("DED00000",), "DED5": ("DED00000",),
    "PL72": ("PL330000",), "PL81": ("PL310000",), "PL82": ("PL320000",), "PL84": ("PL340000",),
    "PL91": ("PL120000",), "PL92": ("PL120000",),
    "HU11": ("HU100000",), "HU12": ("HU100000",),
    "IE04": ("IR010000",), "IE05": ("IR020000",), "IE06": ("IR010000", "IR020000"),
}
#: wrong entries in nuts_version_correspondence.json: FI19 (Laensi-Suomi) is unchanged since 2006;
#: FI1C comes from FI18, not FI19
CORR_FIXES = {"FI190000": ["FI19"], "FI180000": ["FI18"]}


def capri_groups(model_regions=None):
    """CAPRI regions and model regions in groups that cover the same territory.

    Returns {capri_code: group id} and {group id: (set of CAPRI codes, set of model regions)}.
    A group is a connected set: one CAPRI region to one model region (most), one to several
    (splits), several to one (merges) or several to several (Ireland). Builders that turn CAPRI
    totals into per-head or per-ha values do it per GROUP - the group's CAPRI total over the
    group's model total - so a split never puts a parent region's total on one of its parts
    (Finland's FI1B carried all of Etelae-Suomi's manure on its own herd: 990 kg N per dairy cow)."""
    regs = set(model_regions if model_regions is not None else model_regions_list())
    if _all_units(regs):                       # CAPRI's units: each region is its own group
        out = {i: ({r}, {r}) for i, r in enumerate(sorted(regs))}
        return {r: i for i, (cs, _) in out.items() for r in cs}, out
    import json
    corr = json.loads((ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]
    corr = {**corr, **CORR_FIXES}
    edges = []
    for c8, lst in corr.items():
        if c8.endswith("000000"):
            continue
        for r in lst or []:
            if r in regs:
                edges.append((c8, r))
    for r, parents in SPLITS_MERGES.items():
        if r in regs:
            edges = [(c, x) for (c, x) in edges if x != r]
            edges += [(p, r) for p in parents]
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for c, r in edges:
        parent[find(("c", c))] = find(("r", r))
    groups = {}
    for c, r in edges:
        g = find(("c", c))
        groups.setdefault(g, (set(), set()))
        groups[g][0].add(c); groups[g][1].add(r)
    ids = {g: i for i, g in enumerate(sorted(groups, key=str))}
    out = {ids[g]: v for g, v in groups.items()}
    code_to_group = {c: ids[g] for g, (cs, _) in groups.items() for c in cs}
    return code_to_group, out


def model_regions_list():
    return model_regions()


def region_to_capri():
    """{model region: CAPRI code} for builders that read ONE CAPRI region's per-unit values (shares,
    factors, per-ha terms): the NUTS correspondence with its fixes, then the splits and merges -
    a split part takes its parent's values; a merged region the first of its parents (REGISTERED;
    FI1D: FI13 Itae-Suomi; IE06: IE01). Count-type builders use capri_groups instead. On CAPRI's units: the
    identity."""
    if _all_units(model_regions_list()):
        return {r: r for r in model_regions_list()}
    import json
    corr = json.loads((ROOT / "capri_data" / "shared" / "nuts_version_correspondence.json").read_text())["capri8_to_nuts"]
    corr = {**corr, **CORR_FIXES}
    out = {}
    for c8, lst in corr.items():
        if not c8.endswith("000000"):
            for r in lst or []:
                out.setdefault(r, c8)
    for r, parents in SPLITS_MERGES.items():
        out[r] = parents[0]
    return out
