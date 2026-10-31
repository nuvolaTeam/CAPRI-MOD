"""The model's nested inputs as long CSV tables, one value per row (converted from JSON on 31 October 2026; the project
rule: input data are CSV).

Each table has a writer, used by its builder in tools/build, and a reader, used by the model, the builders and the
tests, which gives back the structure the code used before (the same nesting, keys in the file's order, floats to the
last digit: written with repr, read with float). A missing file raises FileNotFoundError naming it.

    manure pools      manure_pool_centres.csv (pool, region); manure_pool_costs.csv (from, to, km, eur_per_t_n)
                      -> {"centre": {pool: region}, "pairs": {"A|B": {"km", "eur_per_t_n"}}}
    NH3 factors       nh3_factors_capri.csv (region, animal, manure_share);
                      nh3_factors_capri_regions.csv (region, mineral_share, source, capri_nh3_total_ktN)
                      -> {region: {"manure_share": {animal: v}, "mineral_share", "source", "capri_nh3_total_ktN"}}
    feed rations      feed_ration_2017.csv (region, animal, block, feed, nutrient, value): a block keyed by feed
                      (ration, price, capri_slope, capri_slope_2030: nutrient empty), by nutrient (req: feed empty) or
                      by both (content) -> {region: {animal: {block: {feed: v} | {nutrient: v} | {feed: {nutrient: v}}}}}
    fodder balances   fodder_balance_2017.csv (region, fodder, crop, u_t_per_ha, value_eur_t);
                      fodder_balance_2017_use.csv (region, fodder, animal, use_t_head)
                      -> {region: {fodder: {"crop", "u_t_per_ha", "value_eur_t", "use_t_head": {animal: v}}}}
    market balances   dairy_world_baseline.csv, world_market_baseline.csv (region, commodity, item, value);
                      world_market_baseline_products.csv (product, capri_product)
                      -> {"REGION|COMM": {item: v}}; {product: [CAPRI products]}
    non-EU feed       feed_demand_nonEU.csv (region, commodity, feed_share);
                      feed_demand_nonEU_elasticities.csv (region, commodity, price_of, elasticity);
                      feed_demand_nonEU_capri_regions.csv (region, commodity, capri_region)
                      -> {"REGION|COMM": {"feed_share", "elasticities": {price_of: v}, "capri_regions": [...]}}
    young animals     young_animals_2017.csv, young_animals_by_sex_2017.csv (region, category, base_net_export,
                      value_eur_head) with <name>_coef.csv (region, category, side, activity, coefficient), side
                      produce or use -> {region: {category: {"produce": {act: v}, "use": {act: v}, "base_net_export",
                      "value_eur_head"}}}
    NUTS versions     nuts_version_correspondence.csv (capri_code, nuts_code): the candidates in order, an empty
                      nuts_code for a CAPRI code without one -> {capri_code: [nuts codes]}
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List


# -- the file level ------------------------------------------------------------------------------------------------
def _num(v) -> str:
    """A value as written: a float in full (repr gives it back exactly), None as an empty field."""
    return "" if v is None else repr(float(v))


def _opt(s: str):
    """An optional value as read: None for an empty field."""
    return None if s == "" else float(s)


def _write(path: Path, header: List[str], rows: Iterable[list]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def _rows(path: Path, header: List[str]) -> list:
    """The rows of a table as lists of strings; the file must exist and carry the header."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"input {path} is missing")
    with open(path, newline="") as fh:
        r = csv.reader(fh)
        head = next(r, None)
        if head != header:
            raise ValueError(f"{path}: header {head}, expected {header}")
        return list(r)


def _sibling(path: Path, suffix: str) -> Path:
    """<stem><suffix>.csv next to <stem>.csv."""
    path = Path(path)
    return path.with_name(path.stem + suffix + ".csv")


def _split(key: str):
    a, b = key.split("|")
    return a, b


# -- manure pools ----------------------------------------------------------------------------------------------------
MANURE_CENTRES = ["pool", "region"]
MANURE_COSTS = ["from", "to", "km", "eur_per_t_n"]


def write_manure_pools(costs_csv: Path, centre: dict, pairs: dict) -> None:
    """costs_csv: .../manure_pool_costs.csv; the centres go to manure_pool_centres.csv next to it."""
    costs_csv = Path(costs_csv)
    _write(costs_csv.with_name("manure_pool_centres.csv"), MANURE_CENTRES, ([p, r] for p, r in centre.items()))
    _write(costs_csv, MANURE_COSTS, ([*_split(k), _num(v["km"]), _num(v["eur_per_t_n"])] for k, v in pairs.items()))


def read_manure_pools(costs_csv: Path) -> dict:
    costs_csv = Path(costs_csv)
    centre = {p: r for p, r in _rows(costs_csv.with_name("manure_pool_centres.csv"), MANURE_CENTRES)}
    pairs = {f"{a}|{b}": {"km": float(km), "eur_per_t_n": float(c)} for a, b, km, c in _rows(costs_csv, MANURE_COSTS)}
    return {"centre": centre, "pairs": pairs}


# -- NH3 factors -----------------------------------------------------------------------------------------------------
NH3_SHARES = ["region", "animal", "manure_share"]
NH3_REGIONS = ["region", "mineral_share", "source", "capri_nh3_total_ktN"]


def write_nh3_factors(path: Path, regions: dict) -> None:
    """path: .../nh3_factors_capri.csv; the regional values go to nh3_factors_capri_regions.csv."""
    _write(path, NH3_SHARES, ([r, a, _num(v)] for r, rec in regions.items() for a, v in rec["manure_share"].items()))
    _write(_sibling(path, "_regions"), NH3_REGIONS,
           ([r, _num(rec["mineral_share"]), rec["source"], _num(rec["capri_nh3_total_ktN"])]
            for r, rec in regions.items()))


def read_nh3_factors(path: Path) -> dict:
    shares: dict = {}
    for r, a, v in _rows(path, NH3_SHARES):
        shares.setdefault(r, {})[a] = float(v)
    out = {}
    for r, mi, src, tot in _rows(_sibling(path, "_regions"), NH3_REGIONS):
        out[r] = {"manure_share": shares.pop(r, {}), "mineral_share": _opt(mi), "source": src,
                  "capri_nh3_total_ktN": _opt(tot)}
    if shares:
        raise ValueError(f"{path}: regions without their row in {_sibling(path, '_regions').name}: {sorted(shares)[:5]}")
    return out


# -- feed rations ----------------------------------------------------------------------------------------------------
RATION = ["region", "animal", "block", "feed", "nutrient", "value"]


def write_feed_rations(path: Path, regions: dict) -> None:
    def rows():
        for reg, acts in regions.items():
            for act, rec in acts.items():
                for block, d in rec.items():
                    for k, v in d.items():
                        if isinstance(v, dict):                    # content: feed -> nutrient
                            for q, x in v.items():
                                yield [reg, act, block, k, q, _num(x)]
                        elif block == "req":                       # requirements: by nutrient
                            yield [reg, act, block, "", k, _num(v)]
                        else:                                      # ration, prices, slopes: by feed
                            yield [reg, act, block, k, "", _num(v)]
    _write(path, RATION, rows())


def read_feed_rations(path: Path) -> dict:
    out: dict = {}
    for reg, act, block, feed, q, v in _rows(path, RATION):
        d = out.setdefault(reg, {}).setdefault(act, {}).setdefault(block, {})
        if feed and q:
            d.setdefault(feed, {})[q] = float(v)
        else:
            d[feed or q] = float(v)
    return out


# -- fodder balances -------------------------------------------------------------------------------------------------
FODDER = ["region", "fodder", "crop", "u_t_per_ha", "value_eur_t"]
FODDER_USE = ["region", "fodder", "animal", "use_t_head"]


def write_fodder_balances(path: Path, regions: dict) -> None:
    """path: .../fodder_balance_2017.csv; the fodder per head goes to fodder_balance_2017_use.csv."""
    _write(path, FODDER, ([r, f, b["crop"], _num(b["u_t_per_ha"]), _num(b["value_eur_t"])]
                          for r, fs in regions.items() for f, b in fs.items()))
    _write(_sibling(path, "_use"), FODDER_USE, ([r, f, a, _num(t)] for r, fs in regions.items() for f, b in fs.items()
                                                for a, t in b["use_t_head"].items()))


def read_fodder_balances(path: Path) -> dict:
    use: dict = {}
    for r, f, a, t in _rows(_sibling(path, "_use"), FODDER_USE):
        use.setdefault((r, f), {})[a] = float(t)
    out: dict = {}
    for r, f, crop, u, val in _rows(path, FODDER):
        out.setdefault(r, {})[f] = {"crop": crop, "u_t_per_ha": float(u), "value_eur_t": float(val),
                                    "use_t_head": use.pop((r, f), {})}
    if use:
        raise ValueError(f"{_sibling(path, '_use')}: balances without their row in {Path(path).name}: {list(use)[:5]}")
    return out


# -- market balances (CAPRI's FAO_agg base balances) ------------------------------------------------------------------
BALANCES = ["region", "commodity", "item", "value"]
PRODUCTS = ["product", "capri_product"]


def write_balances(path: Path, balances: dict, products: dict = None) -> None:
    """balances {"REGION|COMM": {item: kt}}; products {model product: [CAPRI products]} to <stem>_products.csv."""
    _write(path, BALANCES, ([*_split(k), i, _num(v)] for k, d in balances.items() for i, v in d.items()))
    if products is not None:
        _write(_sibling(path, "_products"), PRODUCTS, ([m, c] for m, cs in products.items() for c in cs))


def read_balances(path: Path) -> dict:
    out: dict = {}
    for r, c, i, v in _rows(path, BALANCES):
        out.setdefault(f"{r}|{c}", {})[i] = float(v)
    return out


def read_balance_products(path: Path) -> dict:
    """{model product: [CAPRI products]} of a balances file (path: the balances file, <stem>_products.csv read)."""
    out: dict = {}
    for m, c in _rows(_sibling(path, "_products"), PRODUCTS):
        out.setdefault(m, []).append(c)
    return out


# -- non-EU feed demand ------------------------------------------------------------------------------------------------
FEED_SHARE = ["region", "commodity", "feed_share"]
FEED_ELAS = ["region", "commodity", "price_of", "elasticity"]
FEED_REGIONS = ["region", "commodity", "capri_region"]


def write_feed_demand(path: Path, parameters: dict) -> None:
    """path: .../feed_demand_nonEU.csv, with feed_demand_nonEU_elasticities.csv and feed_demand_nonEU_capri_regions.csv."""
    _write(path, FEED_SHARE, ([*_split(k), _num(v["feed_share"])] for k, v in parameters.items()))
    _write(_sibling(path, "_elasticities"), FEED_ELAS,
           ([*_split(k), p, _num(e)] for k, v in parameters.items() for p, e in v["elasticities"].items()))
    _write(_sibling(path, "_capri_regions"), FEED_REGIONS,
           ([*_split(k), cr] for k, v in parameters.items() for cr in v["capri_regions"]))


def read_feed_demand(path: Path) -> dict:
    elas: dict = {}
    for r, c, p, e in _rows(_sibling(path, "_elasticities"), FEED_ELAS):
        elas.setdefault(f"{r}|{c}", {})[p] = float(e)
    regs: dict = {}
    for r, c, cr in _rows(_sibling(path, "_capri_regions"), FEED_REGIONS):
        regs.setdefault(f"{r}|{c}", []).append(cr)
    out = {}
    for r, c, s in _rows(path, FEED_SHARE):
        k = f"{r}|{c}"
        out[k] = {"feed_share": float(s), "elasticities": elas.pop(k, {}), "capri_regions": regs.pop(k, [])}
    if elas or regs:
        raise ValueError(f"{path}: keys of the elasticities or CAPRI regions without a feed share: "
                         f"{(list(elas) + list(regs))[:5]}")
    return out


# -- young animals ---------------------------------------------------------------------------------------------------
YOUNG = ["region", "category", "base_net_export", "value_eur_head"]
YOUNG_COEF = ["region", "category", "side", "activity", "coefficient"]


def write_young_animals(path: Path, regions: dict) -> None:
    """path: .../young_animals_2017.csv (or _by_sex_2017.csv), the coefficients to <stem>_coef.csv."""
    _write(path, YOUNG, ([r, c, _num(b["base_net_export"]), _num(b["value_eur_head"])]
                         for r, cs in regions.items() for c, b in cs.items()))
    _write(_sibling(path, "_coef"), YOUNG_COEF,
           ([r, c, side, a, _num(v)] for r, cs in regions.items() for c, b in cs.items()
            for side in ("produce", "use") for a, v in b[side].items()))


def read_young_animals(path: Path) -> dict:
    coef: dict = {}
    for r, c, side, a, v in _rows(_sibling(path, "_coef"), YOUNG_COEF):
        if side not in ("produce", "use"):
            raise ValueError(f"{_sibling(path, '_coef')}: side {side!r} (produce or use)")
        coef.setdefault((r, c), {"produce": {}, "use": {}})[side][a] = float(v)
    out: dict = {}
    for r, c, bne, val in _rows(path, YOUNG):
        k = coef.pop((r, c), {"produce": {}, "use": {}})
        out.setdefault(r, {})[c] = {"produce": k["produce"], "use": k["use"], "base_net_export": float(bne),
                                    "value_eur_head": float(val)}
    if coef:
        raise ValueError(f"{_sibling(path, '_coef')}: categories without their row in {Path(path).name}: {list(coef)[:5]}")
    return out


# -- NUTS version correspondence ---------------------------------------------------------------------------------------
NUTS = ["capri_code", "nuts_code"]


def write_nuts_correspondence(path: Path, capri8_to_nuts: dict) -> None:
    _write(path, NUTS, ([c8, n] for c8, lst in capri8_to_nuts.items() for n in (lst or [""])))


def read_nuts_correspondence(path: Path) -> dict:
    out: dict = {}
    for c8, n in _rows(path, NUTS):
        lst = out.setdefault(c8, [])
        if n:
            lst.append(n)
    return out
