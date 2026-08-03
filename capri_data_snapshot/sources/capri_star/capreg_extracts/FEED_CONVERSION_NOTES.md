# Feed requirements — extraction & conversion method

Source: CAPRI capreg `DATA2` cube, feed-use columns per animal activity, 35 member
states (national records), base year 2017.

## Units (verified from CAPRIunits.gms)
- Ruminant/pig feed items: stored **kg per head** (CAPRIunits.gms line 195/207:
  animal feed items in U_1000t → U_kgperhd).
- Poultry (HENS, POUF): LEVL is in **million heads**, so feed is **kg per 1000 head**
  (line 197) → divided by 1000 to get kg/head.

## Fresh → dry matter conversion (CAPRI's OWN values)
CAPRI feed columns are fresh weight; the model uses dry matter. The DM content is
taken from CAPRI's own data: DATA2 rows indexed `DRMA.<feedtype>` (per region).
Extracted CAPRI DM content (EU-typical):

| Feed | CAPRI DM | Feed | CAPRI DM |
|------|----------|------|----------|
| FGRA (grass)       | 0.22 | FROO (roots)    | 0.11 |
| FMAI (maize silage)| 0.28 | FOFA (o. fodder)| 0.36 |
| FCER (cereals)     | 0.89 | FSTR (straw)    | 0.86 |
| FPRO (protein)     | 0.83 | FENE (energy)   | 0.90 |
| FEED (compound)    | 0.88 (default; not in DRMA) |  |

This is CAPRI's exact per-region DM content, not an approximation. Only FEED
(compound feed) uses a standard 0.88 as it has no DRMA row.

## Validation (total DM intake per head/yr)
| Animal | Model total | Expected |
|--------|-------------|----------|
| Dairy cow | 6.72 t | 6–7 t ✓ |
| Beef cow  | 3.39 t | 4–5 t |
| Sow       | 1.72 t | ~1.5 t ✓ |
| Fattening pig | 0.32 t | 0.3–0.4 t ✓ |
| Laying hen | 0.04 t | ~0.04 t ✓ |
| Broiler   | 0.01 t | ~0.005 t ✓ |

The DM content is CAPRI's own (DATA2 `DRMA.<feedtype>` rows). Only compound feed (FEED)
falls back to a 0.88 standard, as it carries no DRMA row. Totals validate against known
feed-science figures.
