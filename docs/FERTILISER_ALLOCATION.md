# Fertiliser allocation — design

Status: **Stages 1 (manure trade) and 2 (mineral N follows need, with CAPRI's minimum-mineral
floor) implemented; base balance identical by construction (tested).** Stage 2 was implemented
as a linearisation around the base rather than a new solver variable: mineral N = base rate +
manure-covered share of need − (availability/efficiency) × (1 − floor share) × manure available,
with need ∝ √yield. A new variable remains an option if the linearisation proves too coarse.

## Why

CAPRI does not give crops fixed mineral-fertiliser rates. In its supply model
(`supply/supply_model.gms`, equation `NUTNED_`), each crop group's nitrogen
**need** must be covered by mineral fertiliser, manure, crop residues and
deposition, each net of its losses:

```
Σ_crops area × need × (1 − fixation share) × over-fertilisation factor × √(yield factor)
   =  mineral N × (1 − losses) × (1 + technology gains)
   +  manure N  × availability  × (1 + technology gains)
   +  residues × availability + deposition …
```

Mineral fertiliser is therefore **whatever the crops need beyond what manure,
residues and deposition cover**. Three consequences this model lacked:

1. **Manure has a fertiliser value**: it replaces mineral N, so shrinking herds
   raises mineral use where manure was being used efficiently.
2. **In manure-surplus regions extra manure is pure surplus**: mineral use cannot
   fall below zero, so there the herd is the only lever.
3. **Manure is traded between regions** (`manExportOrAppl_`): 11% of EU manure N
   leaves its region of origin; 38 regions export more than a fifth (Weser-Ems
   31%).

## Verified against CAPRI's own numbers

From the reference run (`res_2_1730greendeal_refdefaulta`, dataOut), Weser-Ems,
winter wheat, kg N/ha:

| term | value |
|---|---|
| mineral delivered (`fertDist_mine_perha`) | 192.8 |
| − mineral losses (`nutNed_mine_loss_gasRunTot_perha`) | −13.5 |
| manure delivered (`fertDist_excr_perha`) | 56.5 |
| − manure unavailable (`nutNed_excr_unavailable_perha`) | −16.5 |
| residues net (`fertDist_cres_perha` − losses) | 8.7 |
| **= need (`NITF` = `nutNed_lhs` = `nutNed_rhs`)** | **228.0** |

A crop's `NITF` in dataOut is its **total need**, not mineral fertiliser.

## Data (in `capri_data/2017/environment/`)

- `capri_fertiliser_allocation_2030.csv` — per region and crop: area, need,
  mineral, manure and residue deliveries, losses, over-fertilisation, fixation
  (153 regions, 47 CAPRI crop codes; `crop` maps MAIZ→CORN, GRAE/GRAI→GRAS).
- `capri_regional_n_balance_2030.csv` — per region: MINFER, EXCRET, MTRADE
  (manure net export), IMPORT, EXPPRD, CRESID, BIOFIX, ATMOSD, SURTOT.

Vintage 2030 (the scenario year); used for **shares and efficiencies**, not
levels, so the 2017 base levels stay this model's own.

## Model change, in stages

**Stage 1 — manure trade.** Each region's manure N enters its balance net of its
base export share, and importing regions receive it. Fixed shares at first
(CAPRI makes them endogenous with a cost). Small change, no new variable.

**Stage 2 — mineral fertiliser as a variable.** One variable per region,
`M ≥ 0` (t N), with a need-coverage row

```
Σ_c need_c · x_c  −  a_man · (1 − export) · Σ_a man_a · x_a  −  R  ≤  e_min · M
```

and cost `p_N · M` in the objective. Crops' variable costs lose their fertiliser
share (it moves to `p_N · M`); `p_N` is calibrated per region so that base
fertiliser spending is unchanged. The nitrogen balance uses `M` instead of fixed
per-crop mineral rates. Calibration requirement: the base solve must reproduce
base activity levels exactly (the PMP terms are recalibrated with the new row
binding at base). **Every baseline anchor must hold before anything else.**

**Stage 3 — technologies on the variable.** The fertiliser-efficiency
technologies act on `e_min` (CAPRI's `1 + Σ share × NMIN`), replacing the current
per-crop scaling.

**Stage 4 — validation.** Against CAPRI's reference: regional mineral use,
manure allocation and surplus; then Farm-to-Fork against Figure 5 and Table 15.

## Simplifications (documented, deliberate)

- Need is covered at **regional** level, not per crop group; CAPRI's group
  constraints (`NUTMIN_`, `NUTMAX_`) restrict where manure can go. To revisit if
  regional aggregation lets manure substitute too freely.
- Manure export shares fixed at their base values in Stage 1.
- Phosphorus and potassium are not modelled.
