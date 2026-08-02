# How to run a CAPRI scenario for shock-magnitude validation

To complete the last validation (does CAPRI-Python move prices/quantities by the
same magnitudes as CAPRI under a strong policy shock?), we need a CAPRI scenario
with a **large, clear policy contrast** — unlike the Green Deal runs, which differ
by <1%.

## What makes a good validation scenario

A strong, well-defined shock the Python model can also apply:
- **Full trade liberalisation** (all tariffs → 0) — largest, cleanest price effects
- **Removal of direct payments** (Pillar 1/2 to zero) — strong supply reallocation
- **A large tariff change** on specific commodities
- **A demand or biofuel-mandate shock**

Avoid technology/productivity scenarios (like Green Deal endotech) — those bake in
exogenous trends the comparative-static Python model doesn't represent.

## Route A — CAPRI GUI (recommended)

1. Open the CAPRI GUI (`gui/capri.jar` or the launcher).
2. Task: **"Run scenario with market model"** (capmod).
3. Baseline: pick the reference (e.g. the 2030 baseline you already have).
4. Scenario: choose or define a strong shock. Built-in examples in `pol_input/`:
   - `RemoveP2.gms` — removes Pillar-2 payments (regional; can be broadened)
   - trade/tariff scenarios under `pol_input/` and `gams/global/`
5. Run for a single year (e.g. 2030) to keep it fast.
6. Results land in `output/results/capmod/res_<scenario>...gdx`.

## Route B — minimal tariff shock (simplest strong contrast)

If you want the cleanest possible test, a full tariff removal is ideal because the
Python model can replicate it exactly (set all import tariffs to zero):
1. In the GUI scenario editor, set tariffs to zero for all commodities, or
2. Use/adapt a liberalisation scenario file if present.

## What to extract and send

From BOTH the reference run and the shocked run, extract DATAOUT (same as before):
```
execute 'gdxdump <path>\res_<REFERENCE>.gdx symb=DATAOUT output=<path>\scen_ref.txt';
execute 'gdxdump <path>\res_<SHOCK>.gdx     symb=DATAOUT output=<path>\scen_shock.txt';
```
Zip the two .txt files and upload. I compare the % changes in prices and quantities
(reference → shock) against the same shock applied to CAPRI-Python.

## What I'll do with it

1. Read CAPRI's price/quantity change for each commodity under the shock.
2. Apply the equivalent shock to CAPRI-Python.
3. Compare magnitudes — report where they match and where they diverge.
That completes the shock-magnitude validation and closes the last gap.
