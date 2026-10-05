# Fodder balance — design

Status: **implemented as use ≤ production**; equality (CAPRI) to come together with the ration wiring. Must come before the EU ration is wired in
(docs/FEED_RATION.md): without it, extra fodder is free.

## The gap

The supply model has no fodder balance. Its only fodder constraint is an upper
limit on grassland area (grass + fodder maize + other fodder ≤ grassland + 20%
of arable land). Herds are not tied to the fodder they eat, and fodder crops do
not depend on herds.

## CAPRI's equation (`supply/supply_model.gms`, `SUPBAL_`)

For non-tradable fodder, feed use equals production net of on-farm use:

    feed use (FGRA, FMAI, FOFA, ...)  =  production of GRAS, MAIF, OFAR, ...
                                         × (1 − p_onFarmShare)

with a stated 1:1 relation between feed and crop output, and seed and losses
"kept in constant proportion" (`p_onFarmShare`). CAPRI's DE11 base: grass used
2,723 kt of 4,538 produced (share 0.60), fodder maize 928 of 2,263 (0.41), other
fodder 352 of 592 (0.59).

## Implementation in capri-mod

Per region and fodder, a usable-fodder coefficient per hectare,

    u_f = CAPRI base fodder use (herds × rations, t fresh) ÷ base fodder area,

so the balance

    Σ_animals ration_f × heads  −  u_f × area_crop  ≤  0

holds with equality at base by construction (CAPRI's loss share embedded). The
rows enter the supply model's first-stage LP, so the calibrator produces
**fodder shadow prices** the way it already does for land; fodder crops then earn
that value, and animals pay it. The ration model's fodder prices become those
shadow prices, closing the loop ration ↔ fodder ↔ land.

Units: the model holds grass yields in dry matter (`loaders._reconcile_grass_yield_units`);
rations are fresh. The balance uses CAPRI's fresh quantities throughout, via u_f.

## Data check (done)

Usable fresh fodder per ha (CAPRI use ÷ our base area): median grass 10.5 t/ha,
fodder maize 33.1, other fodder 11.5 — plausible; DE11 matches CAPRI exactly.
But the tails exceed any real yield (Brittany grass 59.6 t/ha; fodder maize 90th
percentile 68.9 t/ha), so in some regions **our base fodder areas are smaller than
CAPRI's** (e.g. temporary grassland under another activity). Next: compare our base
areas of GRAS, MAIF, OFOD with CAPRI's `LEVL` of GRAE+GRAI, MAIF, OFAR per region,
and resolve the differences before adding the rows.

## Validation

Base identical (anchors, null trajectory) with the rows binding; fodder shadow
prices plausible against CAPRI's fodder unit values; then the ration wired in and
Farm-to-Fork re-run.

**Resolved.** After the NUTS-correspondence fix (73 regions now on regional CAPRI
data), usable fresh fodder per ha is plausible almost everywhere: median grass
6.8, fodder maize 18.4, other fodder 6.5 t/ha. Remaining outliers: FI1B (our
area is a sixth of CAPRI's); fallback regions (IE04, IE06, HR03); and five
regions where **CAPRI's own** fodder-maize production implies impossible yields
(Catalonia 182, Murcia 260, Veneto 114, ITF3 131, ITF5 169 t/ha) although areas
match CAPRI exactly and CAPRI's balance holds (use/production 0.70–0.89). The
faithful coefficient is CAPRI's implied one (base use ÷ base area); these are
registered as CAPRI data anomalies.

## Calibration — two-way coupling

The supply calibration sets each activity's PMP constant so the base solves the
unconstrained first-order conditions; constraints are slack at base or binding
with a zero dual. A fodder balance added that way would be one-sided: herds
growing would need fodder area, but herds shrinking would not lower fodder's
value. CAPRI's balance carries a positive shadow price at base. So the fodder
rows enter the calibration's first-order conditions with a **base fodder value
λ₀ = CAPRI's unit value of the fodder (`UVAG`)**: f = r − Q·x₀ − Aᵀλ₀. The base is
reproduced exactly with the balance binding and its dual equal to λ₀; when herds
shrink the dual falls and fodder area follows, when herds grow it rises. The ration
model then prices fodder at that dual.

## First Farm-to-Fork result

Herds fall more, toward CAPRI (dairy −8.8% vs −10%, beef −10.9% vs −18%;
manure methane −12.5% vs CAPRI −12.2%). But fodder areas do not follow herds
down (grassland −2.2%, silage maize +17.6%, with 6.7% fewer ruminants): written
as use ≤ production, the balance allows fodder grown and not eaten. CAPRI's
`SUPBAL_` is an **equality**. With fixed rations an equality would tie fodder
area rigidly to herds, whereas CAPRI's ration absorbs part of the adjustment —
so the equality comes together with the ration wiring.

### Equality band

CAPRI's equality is implemented as use ≤ production ≤ use + 0.1% of base use
(slack at base). Fodder areas now follow herds under Farm-to-Fork (grassland
−8.9%, other fodder −11.4%). Open: pigs fall 22% (CAPRI −14.5%) although their
price rises — to be traced (hypothesis: freed grassland leaving agriculture
through the land market tightens the nitrogen target in pig regions).
