# Changelog

Recorded because the project's documentation had drifted in **both** directions:
claims of validation outlived their truth (the CAP policy layer was inert while
documented as validated), and claims of failure outlived their fix (the pulse
elasticity sign error and the DE60 non-convergence had both been resolved long
before anyone retired the note). Limitations should be re-measured, not
inherited.

Full provenance for every entry is in `capri_data/DATA_SOURCING_REGISTRY.json`.

---

## Validation status

| Component | Reference | Result |
|---|---|---|
| Market prices | CAPRI `PMRK` | 12/12 within 15% |
| 2030 projection | CAPRI 2030 reference run | correlation **+0.997**, total area within 2% |
| Carbon MACC | EcAMPA 2 (JRC 2016) | agrees at €50/t |
| Fertiliser | CAPRI `p_FertPerHa` | ~10% |
| Feed, monogastrics | CAPRI capreg reference | within ~5% |
| CAP budget | Real EU CAP | €58.8bn vs ~€55–58bn |
| Nitrogen balance | Eurostat gross N balance | median 54 vs ~45–50 kg N/ha |
| Water demand | Known EU irrigation geography | Mediterranean 79%, correct hotspots |
| Biofuel | Observed EU statistics | both within 10% |
| **Farm-to-Fork scenarios** | Published CAPRI (JRC121368) | reported as a range; CAPRI's figure falls inside it for oilseeds |

---

## New capability

**Projection layer (`projection/`)** — versioned trajectory input with mandatory
provenance, weighted least-squares reconciliation, recursive loop, and baseline
drift reported separately from the policy increment. Driven by CAPRI's own
`captrd` baseline. Two correctness properties hold: a null trajectory reproduces
the comparative-static result **exactly**, and the projection reproduces CAPRI's
independent 2030 reference at +0.997.

This changes what the model *is*: it is no longer purely comparative-static, and
the README description was updated accordingly. Three caveats bound the claim —
validation covers a **single step** to 2030, not multi-period recursion; only
**perennial areas** are carried between periods, so herds are re-optimised each
period and livestock adjustment speed is overstated; and the trajectory is
**exogenous**, adopted rather than generated.

**Nitrogen intensity margin (`supply/intensity.py`)** — N per hectare is now a
decision variable with a Mitscherlich yield response, normalised so the base
year is reproduced exactly. Without it a nitrogen constraint could only cut
*area*, overstating the response roughly tenfold.

**Farm-to-Fork instruments** — all four CAPRI targets are now representable:
landscape elements (a fallow floor, as `landscape.gms` does it), organic area
share (I/O adjustment, as `organic_io.gms` does it), the tiered nutrient-surplus
rule, and the pesticide yield-loss channel.

**Water demand (`water/`)** and **farm-income distribution (`income/`)**.

---

## Defects fixed

Every one was surfaced by an **external reference**, not by an internal
consistency check. That is the single most useful lesson in this log.

| Defect | Effect |
|---|---|
| CAP support double-counted | ~29% supply inflation in **every scenario ever run** |
| All policy instruments inert | Scenarios returned baseline numbers while reporting success — four separate causes |
| Nitrogen balance meaningless | Median −170,196 kg N/ha, from a grass fresh-matter artifact and a manure-N scale error |
| Permanent crops destroyed | Olives 78% error in every base solve; invisible to a fidelity measure that only checked annual crops |
| Permanent-crop elasticities inverted | 10× *less* elastic than annuals, where CAPRI has them 2.47× *more* |
| Livestock yields unit-inconsistent | ~56 regions in tonnes, ~192 in kg; drove the MACC 2–3× too high |
| Consumption fabricated | A clamp invented supply where exports exceeded production |
| Set-aside mapped to the wrong instrument | Modelled as an arable cut; CAPRI uses a fallow floor |
| Market price test asserting stale values | Failed for the life of the project against deliberately-corrected data |
| Hard-coded 2017 paths | Re-basing would have silently fallen back to literature defaults |
| Organic target missing | Only a payment *rate* existed, not an area *target* |

---

## Farm-to-Fork comparison (JRC121368)

**Now a single estimate, not a range.** The plant-protection cost was derived
from CAPRI data (see below), which removed the reason for reporting bounds.

| | CAPRI-mod | CAPRI published (JRC121368) |
|---|---|---|
| Cereals | −23.6% | −15% |
| Oilseeds | −15.9% | −15% |
| Permanent / fruit & veg | −10.2% | −12% |

Oilseeds (1.07x) and permanent crops (0.86x) are close. **Cereals still
overshoots at 1.62x**, and the pesticide cost channel does not explain it — the
real saving for cereals is small (4.3% of variable cost, halved = ~2% margin
gain) and cannot offset a 10% yield loss. That residual is a genuine open
question, not a rounding artefact.

**The pesticide cost is CAPRI-derived, not assumed.** Built as
`PESTOTAL (g a.i./ha, capreg) / 1000 x UVAB.PLAP (EUR/kg, coco)`. Two unit checks
were run rather than assumed: summing PESTOTAL x area over Spain gives 89,888 t
against a national quantity of 83,104 t (within 8%, fixing the unit as grams per
hectare), and `UVAB x NETF` reproduces `EAAB` exactly at EUR 1,110.7m — which is
Spain's real annual pesticide spend.

**Confirmed independently on a second country.** Both checks were re-run from
scratch on Italy and passed *better*: reconciliation within 2% (against Spain's
8%), and `UVAB x NETF` matching `EAAB` to the decimal (947.6 vs 947.59 m EUR).
Two countries agreeing on the unit interpretation is far stronger than one.

**Country variation is real**, which is why one country was not enough: Italian
costs run a median 1.15x Spanish, but from 0.95x for maize to ~1.7x for olives,
citrus and apples. Mediterranean permanent crops are where the two disagree most.
Shares are now the median across both countries.

---|---|---|---|
| Cereals | −26.4% | −19.8% | −15% |
| Oilseeds | −16.7% | −12.2% | **−15%** (inside) |
| Permanent / fruit & veg | −10.6% | −7.7% | −12% |

CAPRI's published figure falls **inside** our range for oilseeds. For cereals
and permanent crops it falls just outside — but in **opposite** directions (we
overstate the cereal decline, understate the permanent-crop one), which argues
against a single systematic bias and points instead to residual differences in
how the individual instruments are represented.

---

## Known assumptions carrying weight

- **`PPP_COST_SHARE`** — plant-protection cost shares, anchored to farm-management
  per-hectare figures, **not** CAPRI-derived. An `EAAB.PLAP` extract in million
  euro would replace them with measured values.
- **Permanent-crop elasticities** — CAPRI's *relative* structure (2.47× annuals),
  not its absolute levels, which are member-state market elasticities rather than
  regional PMP targets.
- **Organic yield gap 20%, cost premium 15%** — literature (Seufert 2012, Ponisio 2015).
- **Mitscherlich curvature k = 3.0** — agronomic literature; not tuned to fit CAPRI.

---

## Regression anchors

`capri_data/validation/REGRESSION_ANCHORS.json` + `tools/check_regression.py`.

A machine-checkable snapshot of the numbers that **external references**
validated. It reports *which validation broke*, not merely that a number moved —
each anchor names the reference it was checked against, so a failure points at a
source you can go and re-read.

```bash
python tools/check_regression.py            # exit 1 on breach
python tools/check_regression.py --update   # accept an intended change
```

Eight cheap anchors run every time (regions, convergence, base fidelity, olive
fidelity, N surplus, world balance, price reproduction, CAP budget); two
expensive ones (MACC, projection correlation) are recorded but checked on demand.

Two design points worth keeping:

- **Olives have their own anchor.** The aggregate base-fidelity measure looks
  only at annual crops and did not see the permanent-crop collapse. An anchor
  that shares a blind spot with the bug it should catch is worthless.
- **`--update` is how an intended change is accepted, not how a failure is
  silenced.** Verified to exit 1 on a breach and 0 when clean, so it is usable
  in CI.

Run it before and after any base-year re-base — that is the situation this
exists for.

---

## Still open

- **Policy-scenario results are a range, not a single number.** Two offsetting
  cost effects of the pesticide target cannot be computed from the available
  data, so the model is run both ways and the answer lies between. An
  `EAAB.PLAP` extract (plant-protection cost in million euro) would make both
  computable and collapse the range to a single figure.
- Phase 2 (base-year update) not started; the base year remains 2017.
