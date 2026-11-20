# Fodder balance

Status: revised 20 October 2026 against the code. The build history (the grassland-area limit it replaced, the first
one-sided version, the Farm-to-Fork results of each step) was removed; the data checks below are those made when the
data were built (dates as in the text).

## CAPRI's equation (`supply/supply_model.gms`, `SUPBAL_`)

For non-tradable fodder, feed use equals production net of on-farm use:

    feed use (FGRA, FMAI, FOFA, ...)  =  production of GRAS, MAIF, OFAR, ...  x  (1 - p_onFarmShare)

with a stated 1:1 relation between feed and crop output, and seed and losses kept in constant proportion
(`p_onFarmShare`). CAPRI's DE11 base: grass used 2,723 kt of 4,538 produced (share 0.60), fodder maize 928 of 2,263
(0.41), other fodder 352 of 592 (0.59). Fodder is not traded between regions, so herds are tied to the fodder area of
their region and fodder crops to the herds.

## capri-mod

Data: `tools/build/build_fodder_balance.py` -> `capri_data/2017/feed/fodder_balance_2017.csv`, per region and fodder
(grass FGRA on GRAS, fodder maize FMAI on MAIF, other fodder FOFA on OFOD):

- `u_t_per_ha`: usable fresh fodder per ha = CAPRI's base fodder use (herds x rations, t fresh) / base fodder area, so
  CAPRI's loss share and yield are embedded and use = u x area holds at base;
- `use_t_head`: fodder per head per animal, from the rations (`feed_ration_2017.csv`);
- `value_eur_t`: CAPRI's unit value of the fodder (UVAG), the value the balance carries at base.

The model holds grass yields in dry matter; rations are fresh. The balance uses CAPRI's fresh quantities throughout,
through u.

Row (`RegionalSupplyModel._fodder_rows`), per region and fodder:

    sum_animals feed use  -  u x area of the fodder crop  =  base gap

- NLP form (default): an equality, with FEDUSE_ (per-head feed x herd) in place of the animals' fixed coefficients.
- Conic form: use <= production <= use + 0.1% of base use (a band, since the conic model is written with
  inequalities; slack at base), with total feed as the variable.
- Base gap: use at the base rations x base herds minus production at base areas, carried as a constant in both
  directions, as CAPRI's baseline holds its balances (K36, K46). In projected years the projected herds' use and the
  projected fodder output need not match; before K36 the row forced the fodder area down to the use.
- Projection: `u_t_per_ha` follows CAPRI's 2030 usable fodder per ha (FEDM / LEVL of the fodder crops, 2030 over 2017,
  `capri_ref_fodder_2030.csv`) and `value_eur_t` CAPRI's own 2030 unit value of the fed fodder (UVAG, region and
  fodder, in 2017 money; `fodder_value_2030.csv`, K161); pairs without it take CAPRI's 2030/2017 ratio of the value.

Milk for feeding (since 20 November 2026, KNOWN_ISSUES K189). CAPRI's COMF (cow milk fed to calves) and SGMF (sheep
and goat milk fed to lambs) are non-tradable outputs too (FODDO): the dairy and suckler cows (DCOW, DCOL, DCOH, SCOW)
and the milk sheep and goats (SHGM) produce them, the calves (and the other animals whose ration holds it) feed them
as FCOM and FSGM, and FEDUSE_ adds CAPRI's losses, v_lossQuant between 0 and infinity (supply/prep_sim.gms l. 222-223),
so the balance is use <= output. In 2030 runs the model writes it the same way: `milk_for_feeding_2030.csv`
(tools/build/build_milk_for_feeding_2030.py: CAPRI's 2030 output per head and UVAG, in 2017 money) puts each region's
FCOM and FSGM balance into the fodder balances (`projection/prices.py`), with the producing animals' output per head
on the output side, the users read from the base rations, and the row an inequality in the NLP form. At ES41's 2030
base the calves' milk is the cows' output (271.56 thousand t, as CAPRI's GROF = FEDM) and the dual CAPRI's value
(120.4 against 119.8 EUR/t). Before, the rations priced FCOM and FSGM at 0 and nothing tied the calves' milk to the
cows. The 2017 base has no such balance (no CAPRI value at hand).

Valuation. Fodder carries no price in the objective; its value is the dual of its balance. The regional calibration
makes the base a first-order point with the balance binding and its dual at CAPRI's unit value (the feeds' calibration
takes the fodder's base value as the expected dual, `calibrate_feed_terms`). When herds shrink the dual falls and
fodder area follows; when herds grow it rises. Without CAPRI's equality, written as use <= production, fodder grown
and not eaten was allowed, and fodder areas did not follow herds down.

Without feeding inside the models (an older path), the outside ration can price fodder at the balance's dual
(`CAPRIModel.fodder_at_shadow_price`, off: the run with it on did not converge); regions without fodder balance data
fall back to a loose roughage limit in `_build_constraints`.

## Data checks (when the data were built)

Usable fresh fodder per ha after the NUTS-correspondence fix: median grass 6.8, fodder maize 18.4, other fodder 6.5 t/ha.
Outliers: FI1B (the model's area a sixth of CAPRI's); regions on fallback data (IE04, IE06, HR03); and five regions
where CAPRI's own fodder-maize production implies yields that cannot be right (Catalonia 182, Murcia 260, Veneto 114,
ITF3 131, ITF5 169 t/ha), although the areas match CAPRI's and CAPRI's balance holds (use / production 0.70-0.89). The
coefficient kept is CAPRI's implied one (base use / base area); these are registered as CAPRI data anomalies.
