# Rebuilding the data on CAPRI's regional units: log (from 27 October 2026)

The model's regions become CAPRI's 221 regional units of the EU27 and Norway under CAPRI's 8-character codes
(`capri_data/shared/regional_units.csv`, `tools/build/build_regional_units.py`; inventory:
`REGIONAL_UNITS_INVENTORY.md`; builders and their order: `REGIONAL_UNITS_BUILDERS.md`). Each region-keyed file is
rebuilt by its builder on the units, then compared with the file on the old NUTS-2016 regions
(`tools/check/compare_rekeyed.py <file>`): for the 196 regions whose CAPRI unit was theirs alone (one-to-one in the old
`shared/region_capri_map.csv`), the rebuilt row must equal the old one, since both read the same CAPRI row. Every
difference found is listed here with its cause.

## Code

- `capri_mod/data/definitions.py`: `NUTS2_REGIONS`, `ALL_REGIONS`, `REGION_TO_COUNTRY` read from
  `regional_units.csv` (the hard-coded list of 248 NUTS-2016 codes is gone). The country key stays the NUTS-0 code
  (BE, LU, IE, EL...; BL400000 is Luxembourg): CAPRI's prefix IR (Ireland) is Iran among the market's ISO codes.
- `tools/lib/_model_regions.py`: `capri_groups` and `region_to_capri` are the identity on CAPRI's units (including the
  member states without regional detail, DK000000 ...); `is_unit`, `regional_row` for builders that skipped every code
  ending in 000000.
- `tools/build/build_capri_base.py`: each unit reads its own CAPRI row. Removed: the renames, merges, splits by Eurostat
  cattle numbers, the national copies, Ireland's 2016 shares, Norway's pooling, the Saxony and Croatia crop re-splits
  from p_REGIO, the `ZERO` list. `build_spec` is the identity (used by build_crop_economics_2017,
  build_ghg_coefs_2017, build_norway_pigs).

## Files

### Base tables (build_capri_base, build_crop_economics_2017)

On the 196 one-to-one units, equal to the last digit except:

| file, column | old | new | cause |
|---|---|---|---|
| base_areas PARI, ES230000 | 0 | 0.081 kha | CAPRI's LEVL; the old 0 came from another writer (to be traced) |
| animal_numbers PIGS, PIGF | census PIGS - SOWS, by the removed one-off tools/build_pig_split.py | the same rule in build_capri_base | the rule is now in a builder |
| animal_numbers PIGF, DEA20000, DEB10000, FI200000 | 0 | CAPRI's PIGF HERD (20.8, 32.2, 0.28 thousand) | CAPRI has fattening pigs there but no census total or sows; the old split set both to 0. Now CAPRI's PIGF herd, as Norway's regions already had (build_norway_pigs) |
| animal_numbers SHGM, SHGF | census SHGT x CAPRI's HERD share (build_shg_split) | CAPRI's SHGM, SHGF HERD | relative differences up to 1e-6 (the old values were rounded); CAPRI's SHGT = SHGM + SHGF to 1e-11 |
| land_availability OTHER_AG | values of unknown origin (6.25, 2.97619 ...) | dropped | written by no builder; read only by the environmental module's HNV indicator through the land total |
| yields, variable_costs: crops CAPRI has nowhere in the member state (citrus, olives, table grapes in Germany; durum wheat in Poland; soya in the Netherlands ...; 12 columns, 513 cells) | values kept from the synthetic template removed in Sprint 9s (DE11 citrus 24.2 t/ha, 1,599 EUR/ha; wine 1,313 EUR/ha) | 0 | build_crop_economics_2017 left such cells as the file had them; now 0, as the file had for rice outside the rice countries |
| crop_premium, cap_payments BPS | rounded to 4 decimals | full precision | the exact-I/O change (relative differences below 3e-6) |
| capreg_producer_prices: items not written by build_capri_base / build_crop_economics_2017 (AGGT, ARAB, BULF, DCOL, SHGM, ...) | from the DATA2 extraction | empty until that extraction is re-run on the units | next step |
