# State of the art: recursive-dynamic agricultural sector models and dynamic PMP

Research note for capri-mod, 22 Oct 2026. Read-only desk review: web sources plus the local CAPRI
star-3.0 GAMS code and the CAPRI documentation (Jan 2022) already in the project.

**Conventions.** `[Sn]` points to the source list at the end. **[UNVERIFIED]** marks a claim I could not
confirm in a primary source during this session; treat it as a lead, not a fact. **[MY VIEW]** marks
recommendations that are my judgement, not established practice. Where a primary document did not cover
a point, I say "not found in the documentation reviewed" rather than "absent".

**Access limits.** Some primary sources were blocked in this session: the GLOBIOM documentation PDF on
pure.iiasa.ac.at, iiasa.github.io, the PMC copy of Havlík et al. 2014, and full-text AgEcon PDFs. GLOBIOM
details therefore come from secondary or partial sources, and are marked as such.

---

## 1. Which models are recursive-dynamic, and what links year t-1 to year t

### 1.1 Summary table

| Model | Type (per own docs) | Links between periods (verified) | Src |
|---|---|---|---|
| **CAPRI** | Comparative static. "the market equilibrium simulated for a given point in time does not involve lags or leads of endogenous variables" | None in the economic core. Inside one run, the land-use transitions follow a Markov time path, and the CAPTRD baseline uses trends | S1, S4 |
| **Aglink-Cosimo** | Recursive-dynamic PE, annual, about 10-year horizon | "Lagged values ... are considered exogenous; therefore, for every year the model is solved separately." Area shares depend on **returns per ha in t-1**. Meat production depends on feed costs in t-1..t-3 and **cow inventories in t-1 and t-2** (beef) or t-1 (dairy). Milk = cow inventory × yield. Year-specific shocks enter through r-factors. Biofuel expected returns use a 2-4 year lag | S5, S6 |
| **AGMEMOD** | "econometric, dynamic, partial-equilibrium, multi-country" | "The lagged variables induce a recursive model structure." Land shares depend on **expected (moving-average) gross margins** and own-lagged shares. Livestock: **ending breeding stocks** are behavioural; other stocks follow an accounting identity (beginning stock + births ± live trade − slaughter − losses). Dairy cows follow as an identity from milk and yield | S8 |
| **FAPRI (MU/ISU; FAPRI-UK)** | Econometric PE, multi-year baselines | Area depends on **expected net returns** = (lagged price + loan deficiency payment) × trend yield − variable cost + part of the payments. Expected price is a function of the lagged price and the lagged yield deviation. Livestock model: "Except for the breeding herd, all stock variables are derived in an accounting identity from the changes in the flow variables" | S17, S18 |
| **IFPRI IMPACT v3** | Multimarket PE, solved **year by year** | Exogenous intrinsic yield and area growth rates, compounded annually. Land supply is updated "at the end of each year" using the **3-year average land shadow price**. Area and yield respond to current-year prices (annual response). Livestock: exogenous number trends; "there is no modeling of herd dynamics". Stocks are exogenous | S9 |
| **GLOBIOM** | Recursive-dynamic PE, linear programming, **10-year step** from 2000 to 2100 | Land-use change costs that rise with accumulated conversion in the period; a "maximum share of conversion per period"; land cover carried forward; the reference trade quantity is the previous period's trade (trade inertia); demand shifted by GDP and population; myopic landowners ("consider only current period payments") | S10, S11, S12 (secondary, forest-module SI); details **[UNVERIFIED in main documentation]** |
| **MAGNET** (CGE) | "recursive dynamic, multi-region, multi-sector CGE"; user-chosen step, minimum 1 year | Period t+1 initialises on the updated database of period t. Capital accumulation and investment follow GTAP-Dyn: the expected rate of return "gradually move[s] towards the actual rate of return" (adaptive, error-correcting expectations). Endogenous land supply curve. Exogenous factor-augmenting technical change | S14, S15, S16 |
| **ESIM** | Not verified: the documentation landing page does not state it | **[UNVERIFIED]** | S37 |
| **AROPAj** | Regional farm-type **LP** models (FADN-based); the 2025 description stresses "non-time dependent data" | No recursive mechanism described in the abstract. Iterations are for shadow prices only | S22 |
| **IFM-CAP** | "static positive mathematical programming model", "fixed farms structure", single time point | None. A 2016-17 Thünen project studied structural change (an MCI model of specialisation shifts and farm exit) for later integration; integration status not found | S20, S21 |
| **SWISSland** (agent-based, farm PMP/LP) | Recursive dynamic, annual, 10-15-year horizon | Production capacities and investments carried over year to year; land exchange between farms | S26, S27 |
| **FarmDyn** (single farm, mixed-integer) | "Fully dynamic" (also comparative-static or short-run modes) | Integer investments in buildings and machinery; dairy herd by lactation; annual steps with sub-annual management | S32 |
| **SILAS-Dyn** (Swiss sector programming) | Recursive-dynamic | "the only recursive-dynamic model in that group and the only one using a capital stock constraint" (in the 2012 PMP review's table) | S24 |
| **Thessaly recursive LP** (2024) | Recursive farm-level LP | Farm stay/exit and expansion decisions carried over years | S29 |

### 1.2 Cross-cutting observations

1. **Two families.**
   - *Econometric outlook models* (Aglink-Cosimo, AGMEMOD, FAPRI) are dynamic through **lagged endogenous variables** in behavioural equations: lagged or expected returns and lagged inventories. Each year is solved separately with lags fixed [S6, S8].
   - *Programming or optimisation models* (GLOBIOM, IMPACT, MAGNET) are mostly **recursive comparative-static**. Each period is a static equilibrium at current prices, and a few **state variables** carry over: land cover and conversion, capital, trade reference. Exogenous drivers are updated per period [S9, S12, S15].
2. **Herd dynamics.** These are explicit only in the econometric models: a breeding-herd equation with lags, plus stock-flow identities [S6, S8, S17]. IMPACT explicitly has none [S9]. For GLOBIOM, the reviewed sources describe livestock production-system shifts, not cohort dynamics [S13].
3. **Perennial crops with planting and vintages** were not found in the documentation reviewed for Aglink-Cosimo, AGMEMOD, IMPACT or GLOBIOM. Vintage (age-structured) models exist in specialised literature. Example: Franklin, Knapp and Schwabe, a dynamic regional model of irrigated vineyards with an age distribution [S30]. A 2024 review calls perennial supply response under-researched, "the first literature review ... in more than 30 years" [S31].
4. **Expectations.** All verified PE outlook models use **backward-looking** expectations:
   - naive t-1 returns: Aglink area equations [S6]
   - moving averages: AGMEMOD [S8]
   - an expected-price equation on lagged price and yield deviation: FAPRI [S18]
   - adaptive error correction: GTAP-Dyn and MAGNET investment [S16]
   - myopic current-period payoffs: GLOBIOM [S12]

   None of the reviewed sector models uses rational or perfect-foresight expectations for supply.
5. **Technology and yield.** In every model reviewed this is an **exogenous trend or shifter**, sometimes with a price response (IMPACT yields respond to current prices [S9]; AGMEMOD milk yield = trend + price [S8]).

---

## 2. Dynamic and recursive extensions of PMP

| Work | What it does | Src |
|---|---|---|
| Day (1963), *Recursive Programming and Production Response* | The classic recursive LP: each year's LP is solved with **flexibility constraints**, i.e. activity levels may move only within bounds around the previous year's levels. The ancestor of "recursive programming" | S35 (catalogue record; content from general knowledge, **[UNVERIFIED here]**) |
| Paris (2001), *Dynamic Positive Equilibrium Problem* (DPEP), UC Davis WP | Extends symmetric PMP (SPEP) to time series. It requires an estimated **equation of motion** and redefines marginal cost. Applied to 8 years of panel data on California annual crops. Dynamics come from **Nerlove-type adaptive price expectations** | S23 |
| Howitt, Msangi, Reynaud, Knapp (2005), *AJAE* 87(4) | Calibration/estimation of an **intertemporal (dynamic-programming) model** with recursive utility, applied to a reservoir rather than crop allocation. Methodological precedent for calibrating forward-looking models | S34 |
| Heckelei, Britz, Zhang (2012), *Bio-based and Applied Economics* 1(1) (PMP review) | Notes that models linked to outlooks "face the question if and how to update their PMP terms to a future point in time". Lists SILAS-Dyn as the only recursive-dynamic PMP model in its table (with capital stock); FARMIS and RAUMIS have continuous re-investment cost; investment restrictions are asymmetric (no disinvestment). Most PMP estimation is cross-sectional | S24 |
| Jansson and Heckelei (2011), *J. Agric. Econ.* 62(1) | Bayesian highest-posterior-density estimation of the **CAPRI regional crop PMP parameters from CAPRI time series** (219 regions, 23 crops). Static model, but it shows CAPRI time-series data can identify behavioural parameters; a natural basis for estimating adjustment speeds | S33 |
| Mack et al. (2015 IAAE; 2019/20 *BAE* 8(1)), SWISSland | **Ex-post validation of a recursive-dynamic PMP/LP agent model**: base 2003-05, forecast 2005-2012 against Swiss FADN. PMP for crops beats LP. A hybrid with **LP for livestock investment** plus PMP for crops is best over medium and long horizons | S25, S26 |
| Fragoso, Carvalho, Henriques (2011), *Int. J. Sustainable Society* | Calibrated to 2000, predicted 2004 under 2004 prices and subsidies, compared with observed data. The exogenous-elasticity PMP rule performed best | S28 |
| Mantziaris et al. (2024), *BAE* 13(4) | Recursive farm-level LP (Thessaly) with exit and expansion; simulates structural change over time | S29 |

**Not found** in this session: a peer-reviewed "recursive PMP" for an **EU-wide regional (NUTS2) supply
model** that carries herd or vintage states. Search terms tried: recursive / dynamic PMP; PMP with
investment; PMP with perennials. **[UNVERIFIED that none exists]**

### 2.1 CAPRI's own dynamic history and residues

- **CAPRI-Dynaspat** (FP6 no. 501981, Mar 2004 to Feb 2007, coordinated by Bonn) aimed to "render the
  system recursive-dynamic" [S1 intro; S3]. The current documentation still calls CAPRI comparative
  static [S1], and the JRC inventory states "comparative static approach without any intermediate steps"
  [S4]. **I found no documentation of a maintained recursive-dynamic CAPRI version.** Residues in
  star 3.0:
  - `capreg/set_global_variables.gms` l.106-108: `$SETGLOBAL RECDYN OFF` with the comment "Only used in
    gams\seamcap\gtaplink\shift_exog_main.gms => obsolete" [S2].
  - `capmod/create_sim_ini_gdx.gms` l.68-71: a comment that recursive-dynamic mode "is currently used for
    two purposes": ex-post calibration and policy shift (running the first year of the sequence base year
    → final year). No active code follows this comment [S2].
  - In CAPTRD, a labour bound: "Total labour must not deviate by more than 5% from forecasts based on
    coefficients estimated in an earlier study ('CAPRI-DYNASPAT')" [S1, §baseline].
- **CAPRI's `EXPOST` switch is not backcasting.** It sets SIM = BAS. In
  `capmod/load_base_data_and_trends.gms` l.653-656, `DATA(...,"TRD")` and `DATA(...,"Y")` are set to the
  `"BAS"` data. It is a calibration and reproduction check of the base year [S2].
- **Time-indexed elements already inside a comparative-static run:**
  - *Land-use transitions.* The supply model computes an annual Markov time path from the base year to the
    simulation year, LU_t = Σ_l P_lk · LU_{t−1} (`e_luOverTime`), with transition probabilities estimated
    from historical annual transitions (gamma-density "most likely" transition matrix) [S1, §land supply and
    transitions, eq. 5.37].
  - *Cattle herd flow.* On the data side (COCO) it is explicitly lagged: calves born in t enter raising,
    move to fattening or heifer raising in t+1, and become young cows for replacement in t+2. Average herd
    = 0.25·Dec(t−1) + 0.5·May/Jun(t) + 0.25·Dec(t) [S1, §3.4.2 and the herd-size section]. **In the
    simulation supply model the young-animal balance is same-year** (eq. 5.20-5.21: production + net trade
    = internal use), i.e. a steady-state herd [S1].
- **CAPRI-GLOBIOM links.** CAPRI imports GLOBIOM-related data (`global/convert_globiom.gms` exists
  locally) and is used alongside GLOBIOM in EU policy work. The precise form of any dynamic coupling was
  **[UNVERIFIED]** in this session.

---

## 3. How recursive-dynamic models are validated

| Practice | Who | Evidence |
|---|---|---|
| Expert "meltdown" review and outlook workshop; partial stochastics on yields and macro variables, with the success rate used to flag parameters for reassessment | Aglink-Cosimo (EU) | S6 §3.3 |
| Informal, case-by-case validation; an ex-post exercise in the OECD Outlook 2013 (Box 1.1); OECD peer review 2009-10 | Aglink-Cosimo | S5 (Box 1.1 itself **[UNVERIFIED]**) |
| Country-team validation reports; one EU validation workshop | AGMEMOD | S8 §2.4 |
| Historical period (2000 to latest statistics) "used as a validation/calibration period" | GLOBIOM | S11 (the same page also says "first 20 years of a scenario"; it is internally inconsistent) |
| Three criteria: structural design, parameters checked against several data sources, testing projections against historical data "when feasible" | IMPACT | S9 |
| Out-of-sample ex-post: 2005-2012 forecasts against FADN | SWISSland (PMP) | S25, S26 |
| Accuracy of USDA and FAPRI baselines since 1997: predictive value of most variables declines after about 4-5 years; neither system dominates | FAPRI / USDA | S19 |
| No ex-post validation ("Projections are not the main objective"); baseline compared with national models and inventories (TRUSTEE, 2013-17) | CAPRI | S4, S36 |
| No ex-post validation | IFM-CAP | S20 |

Common metrics in this literature are RMSE/MAPE, Theil's U against a naive no-change forecast, and
directional accuracy. The specific metric choice per study is **[UNVERIFIED]** except where cited.

---

## 4. Implications for capri-mod

**Framing.** A recursive-dynamic mode goes **beyond CAPRI**: CAPRI is comparative static by design, and its
results are "best interpreted as the long run outcome" [S1]. Everything below is therefore a proposal for
your decision, not CAPRI parity. **[MY VIEW]** throughout, with supporting sources.

### 4.1 Recommended architecture: recursive comparative statics with a small state vector

- Keep CAPRI's per-year equilibrium unchanged: regional PMP NLPs plus the Armington market, solved
  iteratively at current prices. Add a yearly loop where a **small, explicit state vector** from year t−1
  enters year t as fixed data. This is the GLOBIOM/IMPACT/MAGNET pattern [S9, S12, S15]. It also mirrors
  Aglink's rule "lagged values ... exogenous; each year solved separately" [S6].
- Rationale:
  - It preserves the CAPRI supply-market coupling. This is a project rule.
  - It reuses the existing solver path, and run time scales linearly with years. Speed is a priority.
  - It avoids perfect-foresight intertemporal NLPs. Those exist (Howitt et al. 2005 [S34]; FarmDyn [S32]),
    but they are infeasible at 248 regions × N years with IPOPT within acceptable run time.
- **Two internal-consistency tests to build first:**
  1. *Zero-shock reproduction.* A recursive run with the baseline drivers must reproduce the
     comparative-static baseline points (for example 2030) within tolerance. Otherwise the dynamics
     introduce drift that the calibration does not explain.
  2. *Long-run convergence.* With drivers frozen after a shock, the recursive path should converge to the
     comparative-static scenario result. This is consistent with CAPRI's "long run" reading of its
     elasticities [S1].

### 4.2 Dynamic links ranked by defensibility and data support

| # | Link | Precedent | Data for EU NUTS2 | Verdict |
|---|---|---|---|---|
| 1 | **Annual exogenous driver paths** (yield/technology trends, GDP, population, policy timeline, world prices of non-modelled goods) | All models [S6, S8, S9, S15] | CAPTRD-MOD would have to emit **annual** points, not only the target year; DG AGRI / OECD-FAO outlooks are annual | **Start here.** A prerequisite for everything else |
| 2 | **Land-use state and transitions** carried as LU_{t−1} | GLOBIOM conversion costs and caps [S12]; IMPACT land supply on lagged shadow prices [S9]; CAPRI's own Markov transition path [S1] | CAPRI transition matrices (UNFCCC categories) already estimated; CORINE/LUCAS for checks | **Start here.** Least new theory: CAPRI already has the annual Markov equation; recursive mode only makes the state persistent |
| 3 | **Partial adjustment of activity levels** (short-run vs long-run supply): either Day-type flexibility bounds around x_{t−1} [S35] or a quadratic adjustment cost added to the PMP objective, anchored at x_{t−1} | Day [S35]; lagged own shares in AGMEMOD [S8]; Aglink's t−1 returns [S6] | Adjustment speed estimable from CAPRI/CAPREG regional time series, in the way Jansson and Heckelei estimated PMP terms from CAPRI time series [S33] | **Start here, with care.** The PMP terms must be re-derived so the baseline path is still reproduced: the "how to update PMP terms to a future point in time" problem [S24]. Short-run elasticity = λ · long-run (Nerlove); CAPRI's `p_elasSupp` should be read as long-run |
| 4 | **Cattle herd stock-flow** (heifers raised in t−1 limit replacements in t; calves → raising → fattening with a 1-2 year lag) | Aglink lagged cow inventories [S6]; AGMEMOD stock identities [S8]; FAPRI breeding-herd equation [S17]; CAPRI COCO herd flow already lagged t / t+1 / t+2 [S1] | Eurostat December livestock surveys, which CAPRI already uses for herd sizes [S1]; CAPRI young-animal coefficients | **Second step.** Data-supported and needs only a change to one balance: same-year young-animal balance (eq. 5.20-5.21) → lagged balance. Pigs, poultry and small ruminants can stay same-year, as in CAPRI's own herd flow ("all interactions happen in the same year") [S1] |
| 5 | **Price expectations** (naive t−1, moving average, or Nerlove adaptive) in the supply objective, with markets clearing at realised prices | Aglink [S6], AGMEMOD [S8], FAPRI [S18], Paris DPEP [S23] | Expectation parameters need time-series estimation; no CAPRI precedent | **Optional switch, later.** It changes CAPRI's simultaneous supply-market logic into a cobweb structure; a deliberate departure from CAPRI. Recommend as a scenario switch, default off |
| 6 | **Perennial crop vintages** (planting, non-bearing years, uprooting) | Specialised only [S30, S31]; not found in the main PE models reviewed | Weak: EU permanent-crop structure surveys are periodic, not annual **[UNVERIFIED frequency and codes]** | **Defer.** Interim: asymmetric adjustment bounds on permanent-crop area (slow expansion, slow removal) under link 3 |
| 7 | **Capital and investment** (buildings, machinery, stable places) | MAGNET/GTAP-Dyn [S15, S16], SWISSland [S27], FarmDyn [S32], SILAS-Dyn [S24]; none of the regional PE models | FADN capital not mapped to CAPRI activities; investment would need mixed-integer or cost-of-adjustment methods | **Defer.** Beyond what regional PE models do; Mack et al. suggest LP-style investment works better than PMP for livestock investment at farm level [S25] |
| 8 | Endogenous structural change (farm exit, size classes) | Farm or agent models [S21, S27, S29] | Needs farm-type layer | **Out of scope** for a NUTS2 model |

### 4.3 Minimum viable recursive mode (proposal)

1. Annual driver path from CAPTRD-MOD (link 1), with year-specific PMP-term or shifter calibration so that
   a zero-shock recursive run reproduces the baseline points. This is the Aglink r-factor logic [S5] or the
   GLOBIOM per-period calibration [S12].
2. Persistent land-use state, reusing CAPRI's Markov transition probabilities (link 2).
3. Partial adjustment on crop and animal activity levels around t−1 (link 3), with λ estimated from
   CAPREG time series. Report short-run and long-run elasticities side by side.
4. Cattle young-animal balance lagged by one year (link 4), with initial cohort stocks from the base year
   and the year before.

These four links need **no new data source** beyond what CAPRI/CAPREG already holds plus annual baseline
points. Expectations, vintages and investment remain optional extensions, each flagged as beyond CAPRI.

### 4.4 Validation plan

- **Backcast**, a capability CAPRI itself does not provide [S4]. Calibrate to an early base year (for
  example a 2008-2010 average), drive with *observed* exogenous variables and policy, run annually to
  about 2020, and compare with Eurostat/CAPREG regional data.
- Metrics: RMSE, MAPE and Theil's U against a naive no-change forecast, as in the SWISSland ex-post
  design [S25].
- Judge mainly the 1-5-year horizon: baseline accuracy degrades after 4-5 years [S19].
- Run the zero-shock and long-run convergence tests (§4.1) in CI.
- Compare annual adjustment paths with the DG AGRI medium-term outlook (Aglink-based) [S6], acknowledging
  that it is a projection, not data.

### 4.5 Risks and open issues

- **Double counting of dynamics.** If CAPTRD-MOD trends already embed historical adjustment, adding partial
  adjustment on top may slow responses twice. λ must be estimated jointly with, or consistently with, the
  trend model.
- **PMP re-calibration each year** can absorb any discrepancy and hide misspecification. Keep calibration
  shifters reported and bounded; this is the project's "no silent plausible-but-wrong" rule.
- **Cobweb instability** if naive expectations are used with elastic supply. Aglink notes "cobweb-like
  market adjustments" [S5]. Use moving-average or adaptive expectations and test for damping.
- **Run time.** N years × the current per-year solve. Warm-start each year from t−1 (a natural benefit of
  recursion).

---

## 5. Sources

Local (project) sources:
- **S1** CAPRI model documentation, Jan 2022, `/mnt/user-data/uploads/caprijan2022.pdf` (project doc
  `caprijan2022.pdf`). Sections used: Introduction (comparative static; CAPRI-Dynaspat history), §3.4.2
  (herd flow), herd-size data section, supply model eq. 5.20-5.21, CAPTRD bounds, land supply and
  transitions (eq. 5.37).
- **S2** CAPRI star-3.0 GAMS code, `/home/claude/work/allgms/gams/`:
  - `capreg/set_global_variables.gms` l.106-108
  - `seamcap/gtaplink/shift_exog_main.gms` l.94
  - `capmod/create_sim_ini_gdx.gms` l.68-71
  - `capmod/load_base_data_and_trends.gms` l.653-656
  - `global/convert_globiom.gms`

Web sources:
- **S3** CORDIS, CAPRI-DynaSpat (FP6 501981): https://cordis.europa.eu/project/id/501981
- **S4** JRC Policy Model Inventory, CAPRI: https://web.jrc.ec.europa.eu/policy-model-inventory/explore/models/model-capri-print
- **S5** JRC Policy Model Inventory, Aglink-Cosimo: https://web.jrc.ec.europa.eu/policy-model-inventory/explore/models/model-aglink-cosimo-print
- **S6** Araujo Enciso S.R. et al. (2015), *Documentation of the European Commission's EU module of the Aglink-Cosimo modelling system*, EUR 27138: https://publications.jrc.ec.europa.eu/repository/handle/JRC92618 (PDF: https://publications.jrc.ec.europa.eu/repository/bitstream/JRC92618/jrc92618%20online.pdf)
- **S7** Charlebois P. et al. (2017), *Enhancing the Brazilian land use module in Aglink-Cosimo* (beef cow inventory linked to land use): https://publications.jrc.ec.europa.eu/repository/handle/JRC106885
- **S8** Salamon P. et al. (2017), *Unveiling diversity in agricultural markets projections ... AGMEMOD*: https://publications.jrc.ec.europa.eu/repository/handle/JRC109115
- **S9** Robinson S. et al. (2015), *IMPACT: Model Description for Version 3*, IFPRI DP 01483: https://ideas.repec.org/p/fpr/ifprid/1483.html (text: https://cgspace.cgiar.org/server/api/core/bitstreams/1050eaa3-b532-484c-ba1a-ea6c1f8483f2/content)
- **S10** IAMC wiki, Land-use, MESSAGE-GLOBIOM: https://www.iamcdocumentation.eu/Land-use_-_MESSAGE-GLOBIOM ; also https://message-doc.readthedocs.io/en/stable/land_use/index.html
- **S11** JRC Policy Model Inventory, GLOBIOM: https://web.jrc.ec.europa.eu/policy-model-inventory/explore/models/model-globiom-print
- **S12** GLOBIOM forest-sector module, supplementary material (now publishers 112.00000504; article title not verified): https://nowpublishers.com/article/details/supplementary-info/112.00000504_supp.pdf
- **S13** Havlík P. et al. (2011), *Production system based global livestock sector modeling*, EAAE Congress: https://ageconsearch.umn.edu/record/114552
- **S14** JRC Policy Model Inventory, MAGNET: https://web.jrc.ec.europa.eu/policy-model-inventory/explore/models/model-magnet
- **S15** Woltjer G., Kuiper M. et al. (2014), *The MAGNET Model: Module description*, LEI Report 14-057: https://edepot.wur.nl/310764
- **S16** GTAP, *A New Treatment for Investment* (GTAP-Dyn; Ianchovichina and McDougall): https://www.gtap.agecon.purdue.edu/models/Dynamic/dynamic_inv.asp
- **S17** FAPRI/CARD International Livestock and Poultry Model (agrimod inventory): https://agrimod.hutton.ac.uk/node/282.html
- **S18** Westhoff P. (2004), *FAPRI modeling of farm program impacts on U.S. area planted*: https://www.farmfoundation.org/wp-content/uploads/attachments/273-westhoff.pdf
- **S19** Bora S., Katchova A. (2021), *The Accuracy and Informativeness of Agricultural Baselines*: https://u.osu.edu/aede/?p=249
- **S20** JRC Policy Model Inventory, IFM-CAP: https://web.jrc.ec.europa.eu/policy-model-inventory/explore/models/model-ifm-cap-print
- **S21** Thünen, IFM-CAP structural change project (2016-17): https://www.thuenen.de/en/institutes/farm-economics/projects/explaining-predicting-and-linking-european-farm-structural-change-with-the-european-farm-supply-model-ifm-cap
- **S22** Jayet P.-A. et al. (2025), *The European agro-economic model AROPAj*, HAL wp hal-04109872: https://ideas.repec.org/p/hal/wpaper/hal-04109872.html
- **S23** Paris Q. (2001), *Dynamic Positive Equilibrium Problem*, UC Davis ARE WP: https://ideas.repec.org/p/ags/ucdavw/11956.html
- **S24** Heckelei T., Britz W., Zhang Y. (2012), *Positive Mathematical Programming Approaches – Recent Developments ...*, Bio-based and Applied Economics 1(1):109-124: https://oaj.fupress.net/index.php/bae/article/view/3221 (PDF: https://ageconsearch.umn.edu/record/125722/files/10567-18319-1-PB.pdf)
- **S25** Mack G. et al. (2019/20), *How did farmers act? Ex-post validation of LP and PMP ... SWISSland*, BAE 8(1): https://oaj.fupress.net/index.php/bae/article/view/8144
- **S26** Mack G. et al. (2015), IAAE Milan conference version: https://ideas.repec.org/p/ags/iaae15/212201.html
- **S27** Agroscope, SWISSland model design: https://www.agroscope.admin.ch/agroscope/en/home/topics/economics-technology/economic-modelling-policy-analysis/swissland/modelldesign.html
- **S28** Fragoso R. et al. (2011), *Assessing the prediction capacity of an agricultural supply PMP model*, IJSSOC 3(2): https://inderscience.com/filter.php?aid=39922
- **S29** Mantziaris S. et al. (2024), *Simulating farm structural change dynamics in Thessaly ... recursive programming model*, BAE 13(4): https://oaj.fupress.net/index.php/bae/article/view/14790
- **S30** Franklin B., Knapp K., Schwabe K. (2012), *A Dynamic Regional Model of Irrigated Perennial Production*, AAEA: https://ideas.repec.org/p/ags/aaea12/125212.html
- **S31** Siegle J. et al. (2024), *Estimating perennial crop supply response: A methodology literature review*, Agricultural Economics 55(2): https://ideas.repec.org/a/bla/agecon/v55y2024i2p159-180.html
- **S32** FarmDyn, Univ. Bonn: https://www.ilr1.uni-bonn.de/en/research/research-groups/economic-modeling-of-agricultural-systems/farmdyn (docs: https://farmdyn.github.io/documentation/)
- **S33** Jansson T., Heckelei T. (2011), *Estimating a Primal Model of Regional Crop Supply in the EU*, J. Agric. Econ. 62(1):137-152: https://research.slu.se/en/publications/estimating-a-primal-model-of-regional-crop-supply-in-the-european/
- **S34** Howitt R., Msangi S., Reynaud A., Knapp K. (2005), *Estimating Intertemporal Preferences for Natural Resource Allocation*, AJAE 87(4): https://ideas.repec.org/a/oup/ajagec/v87y2005i4p969-983.html
- **S35** Day R.H. (1963), *Recursive Programming and Production Response* (catalogue record): https://catalogo.biblio.unc.edu.ar/Record/economicas.33813/Details
- **S36** Thünen, TRUSTEE task: validation of the CAPRI baseline: https://thuenen.de/en/institutes/farm-economics/projects/trustee-task-validation-of-the-implementation-logic-of-rd-measures-and-the-baseline-in-the-capri-model
- **S37** Grethe H. (ed.) (2012), *ESIM documentation* (landing page only): https://apo.uni-hohenheim.de/en/organization/publication/european-simulation-model-esim-documentation-model-code-parameterization-database-version-of-december-11-2012
