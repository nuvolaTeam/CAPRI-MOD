# Variable costs from CAPRI (TOIN)

## The finding

CAPRI's capreg `DATA2` cube contains **`TOIN` = "Total intermediate input"**, in
**EUR/ha**, per region and activity. CAPRI's own GAMS confirms both:

- definition: `TOIN   Total intermdiate input`
- units: declared as `'Euro/ha'`
- usage: `Gross Value Added = TOOU (revenue) − TOIN (cost)`

This is exactly what `variable_costs.csv` needs.

## Why it is a significant improvement

The previous `variable_costs.csv` was a crop-**group** approximation — every arable
crop in a region shared a single number:

```
DE11 (old):  SWHE 443.91   BARL 443.91   CORN 443.91   ...all identical
```

CAPRI's real TOIN is crop- and region-specific, and also substantially higher:

```
DE11 (TOIN): SWHE 743   DWHE 954   RYEM 560   BARL 730   OATS 580
             CORN 1276  RAPE 1022  POTA 4501  SUGB 1461  GRAS 684
```

## How to extract

1. Dump DATA2 per member state in GAMS Studio (distinct output file each time):

```
execute 'gdxdump <path>\capreg\res_17DE.gdx symb=DATA2 output=<path>\DE_data2.txt';
execute 'gdxdump <path>\capreg\res_17FR.gdx symb=DATA2 output=<path>\FR_data2.txt';
```

2. Run the extractor over all dumps at once:

```bash
python extract_variable_costs.py DE_data2.txt FR_data2.txt IT_data2.txt ... \
    -o variable_costs.csv
```

3. Place the result at `capri_data/<year>/supply/variable_costs.csv`.

## Result on the German dump (validation)

- 39 NUTS-2 regions × 74 activities, **92% cell coverage**
- 28 of the model's 40 activities covered

The 12 uncovered activities are expected:

- **`CITR`, `OLIV`, `COTT`, `WINE`, `TAGR`** — Mediterranean crops, genuinely absent
  from Germany. They appear once ES / IT / GR dumps are added.
- **`BCOW`, `CALV`, `HFRS`, `PIGS`, `OFIB`, `OFOD`** — CAPRI uses slightly different
  animal/other codes (`SCOW`, `CAMF`, `HEIF`, `PIGF`, …). Extend `CAPRI_TO_MODEL`
  in the extractor as needed.

## Code mapping

`CAPRI_TO_MODEL` in `extract_variable_costs.py` renames CAPRI codes to the model's:

| CAPRI | Model | Meaning |
|-------|-------|---------|
| `MAIZ` | `CORN` | grain maize |
| `HENS` | `LAYS` | laying hens |
| `POUF` | `BROI` | broilers |
| `SHGF` | `SHGP` | sheep & goats |

## Caveats

- **Gaps are left blank, not zero-filled.** A missing value means the activity is not
  present in that region — filling it with 0 would tell the model the crop is free.
  Decide explicitly how the model should treat a missing cost (currently the loader's
  behaviour applies).
- TOIN is *total* intermediate input. If you need the breakdown (fertiliser, plant
  protection, seed, energy), those are separate DATA2 columns: `FERT`, `PLAP`,
  `SEED`, `ENER`, `INPO`.
