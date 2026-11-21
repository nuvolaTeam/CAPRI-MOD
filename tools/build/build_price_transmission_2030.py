"""CAPRI's transmission of the market's producer prices to the unit values the supply models are paid (KNOWN_ISSUES
K169), per member state: the factor on the market price's relative change that gives CAPRI's change of the unit value.

CAPRI (arm/set_prices.gms, after each market solve) moves a database output's unit value by the ABSOLUTE change of its
market product's producer price, for the outputs mapped to a market product (CAP_TO_TRD, arm/arm_sets.gms l. 683):
    UVAG(o) = UVAG0(o) + PPRI(XX) - PPRI0(XX)                    l. 43-46
so its relative change is PPRI0(XX) / UVAG0(o) times the market's. The model moves every output by the market's
relative change; the factor PPRI0 / UVAG0 restores CAPRI's rule. The member state's unit value is what CAPRI's regional
supply models are paid (supply_model.gms l. 4701: SUM(R_RAGG(RUNR, MSACT), DATA(MSACT, "UVAG", o, "Y"))).

CAPRI's own rules where it has one:
    raw milk COMI and sheep and goat milk SGMI follow MILK's producer price plus its PSEI, absolute (l. 63-75; PSEI is
        zero for 2030)
    olives OLIV follow olive oil OLIO, absolute (l. 85-89)
    paddy rice PARI follows milled rice RICE, absolute, x MAPR(RICE) / GROF(PARI) (l. 79-83)
    durum wheat takes half of the wheat market's relative change (l. 57-61): model_price_follows.csv
        (K168), factor 1 here
    sugar beet follows sugar by the ratio (l. 91-95): factor 1
Young animals have their own markets (yaniMarket_), not here.

Source: CAPRI's 2030 Green Deal baseline, dataOut of res_2_1730greendeal_refdefaulta (tools/lib/paths.BASELINE_REF, the
run the model's 2030 base reproduces): UVAG, PPRI, MAPR, GROF of the EU member states, 2030.

Output
  capri_data/baselines/capri_greendeal_ref/1730/supply/price_transmission_2030.csv
      ms, activity, commodity (the model's market commodity whose price change the activity's output takes), capri_item
      (CAPRI's output), capri_market (CAPRI's market product), uvag_2030, ppri_2030, factor, rule
  Only rows whose factor differs from 1 by more than 1e-9 are written (the model's factor is 1 where none is listed).

    python tools/build/build_price_transmission_2030.py [--src ZIP]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from paths import BASELINE_REF  # noqa: E402  (CAPRI's material outside the repository)
from _grep import lines  # noqa: E402  (a listing's lines, plain or zipped)

OUT = ROOT / "capri_data" / "baselines" / "capri_greendeal_ref" / "1730" / "supply" / "price_transmission_2030.csv"
CODES = ROOT / "capri_data" / "codes"
#: the animals' final-product value per head by market (the parts the model's revenue moves with each market's price)
VBM = ROOT / "capri_data" / "2017" / "supply" / "livestock_product_value_by_market_coef.csv"
#: CAPRI's EU member states (dataOut codes)
EU_MS = ("AT", "BL", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IR", "IT", "LT", "LV",
         "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK")
#: CAP_TO_TRD (arm/arm_sets.gms l. 683-735): CAPRI's crop and animal outputs and their market products, of those the
#: model's activities produce
CAP_TO_TRD = {"SWHE": "WHEA", "DWHE": "WHEA", "BARL": "BARL", "MAIZ": "MAIZ", "RYEM": "RYEM", "OATS": "OATS",
              "OCER": "OCER", "POTA": "POTA", "PULS": "PULS", "SOYA": "SOYA", "SUNF": "SUNF", "RAPE": "RAPE",
              "TOBA": "TOBA", "TEXT": "TEXT", "APPL": "APPL", "CITR": "CITR", "TAGR": "TAGR", "OFRU": "OFRU",
              "TOMA": "TOMA", "TABO": "TABO", "OVEG": "OVEG", "TWIN": "TWIN", "BEEF": "BEEF", "PORK": "PORK",
              "SGMT": "SGMT", "POUM": "POUM", "EGGS": "EGGS"}
#: CAPRI's own rules (set_prices.gms): output -> its market product
SPECIAL = {"COMI": "MILK", "SGMI": "MILK", "OLIV": "OLIO", "PARI": "RICE"}
#: outputs whose price CAPRI moves by a relative rule (factor 1 here): durum (half, K168), beet (ratio)
RELATIVE = {"DWHE", "SUGB"}
#: the animals' output on each market of the model (livestock_product_value_by_market_coef.csv's parts): CAPRI's item
ANIMAL_ITEM = {("MILK", "cattle"): "COMI", ("MILK", "small"): "SGMI", ("BEEF", None): "BEEF", ("PORK", None): "PORK",
               ("SGMT", None): "SGMT", ("POUL", None): "POUM", ("EGGS", None): "EGGS"}
SMALL_RUMINANTS = ("SHGM", "SHGF")


def num(s: str) -> float:
    s = s.strip().rstrip(",").strip()
    return 0.0 if s.upper() == "EPS" else float(s)


def read(src: Path) -> dict:
    """{(ms, item, field): value} of UVAG, PPRI, MAPR, GROF at 2030 for the EU member states."""
    rx = re.compile(r"^'([A-Z]{2})000000'\.''\.'(UVAG|PPRI|MAPR|GROF)'\.'([A-Z]+)'\.'2030'\s+(\S+)")
    out = {}
    for line in lines(src):
        if "'2030'" not in line:
            continue
        m = rx.match(line)
        if m and m.group(1) in EU_MS:
            out[(m.group(1) + "000000", m.group(3), m.group(2))] = num(m.group(4))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=BASELINE_REF)
    a = ap.parse_args()
    cap = read(a.src)
    with open(CODES / "model_commodities.csv", newline="") as f:
        comm = {r["code"]: r["capri_code"] for r in csv.DictReader(f)}
    capri_to_comm = {v: k for k, v in comm.items()}
    with open(CODES / "model_activities.csv", newline="") as f:
        arows = list(csv.DictReader(f))
    with open(CODES / "model_activity_classes.csv", newline="") as f:
        psrc = {r["code"]: r["price_source"] for r in csv.DictReader(f)}
    with open(VBM, newline="") as f:
        pairs = [tuple(c.split(".", 1)) for c in next(csv.reader(f))[1:] if "." in c]
    rows = []
    for ms in sorted({k[0] for k in cap}):
        def g(item, field):
            return float(cap.get((ms, item, field), 0.0) or 0.0)
        for r in arows:
            act = r["code"]
            items = [x for x in str(r.get("capri_codes", "") or "").split(";") if x]
            if act in psrc and psrc[act]:
                continue                                    # animals: per market below
            if len(items) != 1:
                continue
            item = items[0]
            if item in RELATIVE:
                continue
            market = SPECIAL.get(item) or CAP_TO_TRD.get(item)
            if market is None or market not in capri_to_comm:
                continue
            u0, p0 = g(item, "UVAG"), g(market, "PPRI")
            if not (u0 > 0 and p0 > 0):
                continue
            fac, rule = p0 / u0, "set_prices.gms l. 43-46: UVAG + PPRI change"
            if item == "OLIV":
                rule = "set_prices.gms l. 85-89: olives follow olive oil, absolute"
            if item == "PARI":
                gp, mp = g("PARI", "GROF"), g("RICE", "MAPR")
                if not (gp > 0 and mp > 0):
                    continue
                fac, rule = p0 * mp / gp / u0, "set_prices.gms l. 79-83: x MAPR(RICE) / GROF(PARI)"
            if abs(fac - 1.0) > 1e-9:
                rows.append(dict(ms=ms, activity=act, commodity=capri_to_comm[market], capri_item=item,
                                 capri_market=market, uvag_2030=u0, ppri_2030=p0, factor=fac, rule=rule))
        # the animals' outputs on the model's markets: the pairs of livestock_product_value_by_market_coef.csv
        for act, comm_ in pairs:
            key = (comm_, ("small" if act in SMALL_RUMINANTS else "cattle")) if comm_ == "MILK" else (comm_, None)
            item = ANIMAL_ITEM.get(key)
            market = comm.get(comm_)
            if item is None or market is None:
                continue
            u0, p0 = g(item, "UVAG"), g(market, "PPRI")
            if not (u0 > 0 and p0 > 0):
                continue
            fac = p0 / u0
            rule = ("set_prices.gms l. 63-75: milk follows MILK's PPRI + PSEI, absolute" if item in ("COMI", "SGMI")
                    else "set_prices.gms l. 43-46: UVAG + PPRI change")
            if abs(fac - 1.0) > 1e-9:
                rows.append(dict(ms=ms, activity=act, commodity=comm_, capri_item=item, capri_market=market,
                                 uvag_2030=u0, ppri_2030=p0, factor=fac, rule=rule))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cols = ["ms", "activity", "commodity", "capri_item", "capri_market", "uvag_2030", "ppri_2030", "factor", "rule"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    big = [r for r in rows if abs(r["factor"] - 1.0) > 0.05]
    print(f"price_transmission_2030.csv: {len(rows)} rows with a factor other than 1, {len(big)} beyond +-5%, "
          f"{len({r['ms'] for r in rows})} member states")


if __name__ == "__main__":
    main()
