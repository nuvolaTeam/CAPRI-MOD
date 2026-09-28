# CAPRI reference — what the official documentation says

Notes taken from CAPRI's own documentation, kept here so this project does not
have to re-derive things from GAMS source. Sources:

- **Online manual**, capri-model.org/dokuwiki_help (current; Annex last modified
  2022-11-07, CC0 1.0) and the Thünen mirror bw-pages.thuenen.de/capri/capri/
- **CAPRI Modelling System Documentation**, Britz (ed.), Bonn 2005, 133 pp —
  authoritative on method, but **twenty years old**; treat its *numbers* as
  provisional. One confirmed drift: it says 18 trade blocks, the current Thünen
  page says 28.

---

## 1. How CAPRI builds its inputs

```
Eurostat / FAOSTAT / OECD / FADN
        ↓
COCO    national scale — "Complete and Consistent"
        ↓
CAPREG  regionalised to NUTS-2, takes national data as given
        ↓
Input allocation (fertiliser, feed, young animals, other)
        ↓
Global database (SUA, bilateral trade, trade policy)
```

Stated purpose: *"Specific modules ensure that the data used in CAPRI are
mutually compatible and complete in time and space."*

### COCO's estimation method — this is what `data/reconcile_base.py` reproduces

§2.3.2: **minimisation of normalised least squares under constraints**, where

- accounting identities constrain the fit (market balances sum to zero, etc.)
- bounds come from engineering knowledge and from the mean/variance of the series
- a Hodrick-Prescott filter supplies "supports" for missing points
- as many series as possible are estimated **simultaneously**

They explicitly **rejected** Cross-Entropy and Maximum-Entropy estimators:
*"the ex-ante knowledge can be expressed mainly relating to the estimated value
and not in relation to estimated parameters."* Our reconciler chose weighted
least squares for the same reason, independently.

**Self-correcting bounds.** Original data are fixed unless the identities cannot
be satisfied. Infeasibility shadow prices identify exactly which bounds to relax,
and only those are relaxed. So consistent data are never "corrected".

### CAPREG's concordance — §2.4.8

REGIO carries only a few aggregates (cereals with wheat/barley/grain maize/rice;
potatoes; sugar beet; oilseeds with rape and sunflower; tobacco; fodder maize;
grassland; permanent crops with vineyards and olive plantations). CAPRI has ~30
crop activities. The aggregates are broken down **using national shares**.

*Consequence for this project:* any REGIO-derived regional file is
share-allocated by construction. That is the direct explanation for the 35% of
values in `capri_data/archive/base_areas_eurostat.csv` carrying repeating
decimals. The full mapping is saved at
`capri_data/shared/capri_regio_concordance.json`.

### CAPREG's aggregation — §2.4.9

`CORR = national_level / Σ regional_levels`, then `Levl = Levl* × CORR`.
Proportional scaling — the same operation as `_project_to_total`.

Yields use a **Hodrick-Prescott filter** (§2.4.10) so that input allocation is
linked to *expected*, not realised, yields.

---

## 2. Things CAPRI does that this model does not

| | CAPRI | Here |
|---|---|---|
| Production intensities | Two per livestock activity — DCOL/DCOH at 60%/140% of average milk yield, BULL/BULH and HEIL/HEIH at ±20% meat output, *explicitly to avoid overstating technological rigidity* | One |
| Paddy rice (`PARI`) | A cereal activity | Absent |
| `TABO` table olives | Distinct from `OLIV` olives-for-oil | Absent |
| `OWIN` other wine | Distinct from `TWIN` table wine | Absent |
| `NURS`, `FLOW`, `OCRO`, `OIND`, `ROOF` | Present | Absent |
| `FALL`, `NONF` | Separate from `SETA` | Folded into `SETA` |
| Farm types | FADN-based layer below NUTS-2 | Absent |
| CAPDIS | 1 km grid / Farm Structure Units | Absent |

CAPRI's own words on the single-intensity assumption: *"the Leontief assumption
is an abstraction and simplification of the 'real' agricultural technology."*

## 3a. Region codes — NOT in the documentation

The Annex Code Lists map **items**, not **regions**: REGIO row/column codes, the
crop and herd concordance, supply-model activities, inputs, land-use classes. The
only region codes are member-state sets in Table 6 (`NEUR`, `SEUR`).

The NUTS **version** correspondence lives only in the GAMS source, at
`gams/compile_rdp_data/build_general_set_structure.gms`, as explicit pairs:

```
IT110000.IT11
IT110000.ITC1
```

184 codes extracted to `capri_data/shared/nuts_version_correspondence.json`.
CAPRI's result files use old numeric codes for member states that changed scheme,
so any lookup keyed on NUTS-2016 letter codes will silently match nothing for
Italy. One CAPRI code can map to several NUTS codes; prefer whichever exists in
the target region set.

## 3. Naming: our codes vs CAPRI's

| Ours | CAPRI | Note |
|---|---|---|
| `CORN` | `MAIZ` | grain maize — the alias behind a real bug in three modules |
| `WINE` | `TWIN` | table wine |
| `COTT` + `OFIB` | `TEXT` | flax and hemp, split differently here |
| `OFOD` | ≈ `OFAR` | other fodder on arable land |

---

## 4. Useful reference points for validation

- **Soft wheat activity record** (documentation Table 1, Denmark 2000-02):
  yield 7853.84 kg/ha, `NITF` 175.52 kg N/ha, `PLAP` **59.85 EUR/ha**,
  `TOIN` 522.13 EUR/ha, `PRME` 328.86 EUR/ha.
  → PLAP is **11.5% of total input cost**. Our `PPP_COST_SHARE["SWHE"]` is 5.7%,
  so our pesticide channel may be understated by about half.
- **Three identities** linking the database (`GROF = Σ LEVL × IO`; the farm and
  market balance; `EAAP = UVAP × NETF`).
- **Scale**: ~250 NUTS-2 regions, ~50 activities, ~50 inputs and outputs,
  28 trade blocks (current).

---

## 5. Baseline generation (CAPTRD) — chapter 4 of the 2022 documentation

The counterpart to this model's projection layer. Three points matter.

**CAPRI says its own baseline process is partly opaque.** Verbatim:

> "baselines are in most cases not a straight outcome from a model but developed
> using a combination of trend analysis, model runs and expert consultations. In
> this process, model parameters such as elasticities and exogenous assumptions
> … are adjusted in order to achieve plausible results (as regarded by experts…).
> **It is almost unavoidable that the process is somewhat intransparent.**"

That is a direct endorsement of this model's design choice to treat the
trajectory as an **exogenous, versioned, swappable input** rather than something
generated internally. A projection is defended by showing which conclusions
survive across plausible trajectories — not by claiming one is correct.

**CAPTRD runs in three steps**, which our `trajectory.py` / `reconcile.py` split
mirrors:

1. independent trends on all series, giving initial forecasts and goodness-of-fit
2. impose constraints — identities (production = area × yield), technical bounds
3. add "supports" from external results (AgLink, Commission projections) and
   break down from Member State to regional level

The trend estimates serve as a **"safety net"** where no external projection
exists — the same role our per-activity medians play where regional detail is
missing.

**The baseline is then three tasks plus a verification run**: CAPTRD forecast →
market model calibration → supply model calibration → a *"no change"* simulation
whose purpose is "to verify that the calibration of the baseline worked as
intended".

That last step is conceptually our **null-trajectory identity test**: run the
machinery with no change and confirm it reproduces what it should. CAPRI calls it
a baseline reproduction run. Arriving at the same check independently is
reassuring about the design.

**Regional coverage** (2022): EU as of 2019, Turkey, Norway, Albania, North
Macedonia, Montenegro, Bosnia and Herzegovina, Kosovo, Serbia.

---

## 6. Scenario simulation (CAPMOD) — chapter 5

**Two-stage decision process.** Stage one: producers choose optimal variable
input coefficients per hectare or head *for given yields*, where yields "are
determined exogenously by trend analysis (CAPRI reference scenario) **and updated
depending on price changes against the baseline**". Stage two: the profit-
maximising activity mix is solved simultaneously with cost-minimising feed and
fertiliser.

So CAPRI *does* carry a yield response to prices — a general intensity margin, of
which `supply/intensity.py` implements the nitrogen part only.

**Why permanent crops are inelastic in CAPRI — and it is by construction.** The
PMP first-order condition is

```
Rev_j = Cost_j + ac_j + Σ_k bc_{j,k} · Levl_k + Σ_i λ_i · a_{ij}
```

and the documentation states: *"The cross effects are only introduced to let major
arable crop groups interact, whereas for **fruits & vegetables, permanent crops,
grassland and the animal sectors, only diagonal terms are introduced**."*

This independently explains the elasticity structure we measured from
`supply_elas_*.gdx` — permanents at 0.18-0.22 against annuals at 1.2-8.7. It is
not an artefact of their data; CAPRI deliberately gives permanents no cross-price
substitution. Our earlier rescaling of permanents *upward* was wrong for a
structural reason, not just an empirical one.

**Market module.** Normalised quadratic functions for feed, processing and
supply; a generalised Leontief expenditure function for human consumption;
homogeneity of degree zero, symmetry and correct curvature imposed. Armington
bilateral trade. Dairy handled specially, with fat and protein balancing
equations.

**The iteration loop**, which matches ours: supply models solved at exogenous
prices → results aggregated → a small non-spatial module for young-animal trade →
market module calibrated to the supply results, then solved → producer prices at
Member State level returned to the supply models. Premiums are adjusted between
iterations if CMO ceilings are overshot.

**A discrepancy worth flagging:** this chapter says the market module "breaks
down the world into **40 country aggregates or trading partners**", while the
current Thünen model page says 28 trade blocks. This model has 29. The figure to
trust is unclear; worth checking before claiming our coverage is complete.

---

## 7. Not yet read

Fetched and read: the landing page, the full **Annex: Code lists**, and the 2005
documentation through **chapter 3** (introduction, the whole data base chapter,
input allocation to feed).

The **2022 documentation** (348 pp, `caprijan2022.pdf`) is the current version and
supersedes the 2005 PDF. Chapter map: data base p23, **baseline generation p145**,
scenario simulation p178, post model analysis p283, CAPDIS p303, code lists p338.

**Still unread** — worth doing before work in those areas:

- **Scenario simulation (CAPMOD)** — the supply and market model equations
- **Post model analysis** — dual analysis, welfare, decomposition
- **CAPDIS** — spatial downscaling
- 2005 PDF pages 46-133
