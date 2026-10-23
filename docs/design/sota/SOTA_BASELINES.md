# State of the art: how agricultural sector models build baselines (focus 2018-2026)

Prepared 22 Oct 2026 for the CAPTRD-MOD design. Scope: CAPRI/CAPTRD after 2022, the EU Agricultural Outlook,
Aglink-Cosimo, AGMEMOD, ESIM, FAPRI, GLOBIOM and MAGNET, plus critiques and comparable estimators.
Every claim has a source tag [Sx], and the source list is at the end. **[UNVERIFIED]** marks anything I could
not confirm from a primary text in this session. Several OECD pages and PDFs were blocked (Cloudflare or
robots), so for the Aglink-Cosimo process I relied on the 2021-2030 Methodology annex (FAO-hosted PDF) and
the 2025-2034 Box 1.1. I could not read the 2026-2035 annex.

---

## 1. CAPRI / CAPTRD: what changed after the Jan-2022 documentation

**Bottom line: I found no published evidence of a methodological change to CAPTRD after 2022.** The changes
are in how the tool is used: the vintage of its supports, long-run horizons, and Green-Deal and SSP baselines.

- **The online manual is unchanged in substance.** The "Baseline generation" chapter of the CAPRI wiki
  still describes the same steps [S1]:
  - Step 1 fits weighted trends with c ≤ 1.2, and the trend variable is used as the weight.
  - Step 2 builds supports from an R²-weighted mix of the trend and a 3-year average. The objective is
    normalised by the step-1 error variance. Bounds include, for example, yields at ±2.5 %/yr.
  - Expert supports enter with a mean and a "trust level" from 1 to 10.
  - Step 3 adds Aglink supports for the EU15 and EU12 aggregates. The default trust level for "DGAgri"
    supports is 5. Trust 5 means X lies within ±27.5 % of the mean with probability 99.9 %, and trust 10
    means ±5.5 %.
  - Step 4 breaks the results down to NUTS2.
  - The PDF version linked from the manual is still "2022 January" [S2].
  - The wiki's recent-changes log for 2023-2026 shows edits to the database chapter (2026-03) and to the
    supply chapter (2023-09, price-dependent yields). The visible page of the log shows no edit to the
    baseline chapter [S3]. The log is paginated, so this is not exhaustive.
- **The long run is handled by blending supports, not by a new estimator.** The manual describes how the
  2050 horizon is handled: "a weighting scheme ... gives an increasing weight to our 'long run' sources
  (FAO/IFPRI) as the projection horizon approaches 2050" [S1].
  - DG CLIMA's CAPRI methodology note (Sept 2021) states:
    - Step 3 uses "expert information on aggregate EU markets, generally from the AGLINK and GLOBIOM
      models".
    - GLOBIOM projections serve as target values and prior information.
    - The weight of AGLINK relative to GLOBIOM decreases over a "longer-term projection horizon
      (2030-2070)".
    - Parameters are not specified for runs beyond 2070 [S4].
- **Current teaching material lists the same external inputs** [S5][S6]:
  - AGLINK/COSIMO for market balances and prices.
  - PRIMES and POLES for bio-energy.
  - IMPACT and GLOBIOM for long-term trends.
  - The 2026 Thünen CAPRI course (16 Apr 2026, Gocht) gives the baseline horizon as "2030/2050" [S5].
  - Witzke (EuroCARE, Dec 2024) describes CAPRI in baseline mode as "more a statistical projection tool
    than an economic model", using trends as "fallback priors" merged with external model inputs under
    technical consistency [S6].
  - Neither source mentions a new trend tool, or Bayesian or stochastic features.
- **There is a vintage lag behind the DG AGRI outlook.**
  - EU Agricultural Outlook 2023-35: "The reference scenario (S0) is a CAPRI projection for 2030 aligned
    with the 2020 Medium-term Outlook" [S7].
  - EU Agricultural Outlook 2024-35: the environmental charts use "the 2024 CAPRI MTO baseline [2035; MTO
    2023]" [S8]. The CAPRI baseline is therefore re-aligned annually, or near-annually, to the previous
    December's MTO, now with horizon 2035.
- **There are 2050 baselines with Green Deal measures and SSPs.** A Thünen project builds "a new baseline for
  CAPRI ... until 2050 that also accounts for the Green Deal measures" and quantifies SSPs for European
  agriculture [S9]. The method is not documented on that page **[UNVERIFIED how CAPTRD was used]**.
- **CAPRI feeds other modelling networks.**
  - The 2040 climate-target impact assessment (SWD/2024/63) lists CAPRI, GLOBIOM and G4M among the models
    "involved in baseline and assessment of policy options" [S10].
  - The Thünen-Baseline 2024-2034 combines MAGNET, AGMEMOD, CAPRI, RAUMIS and FARMIS into "a harmonised
    overall outcome" [S11].
- **There is a historical comparison of baseline approaches.** Himics et al. (2014) calibrated CAPRI and
  ESIM to the DG AGRI outlook [S12]:
  - CAPTRD "minimizes weighted deviation from the support points subject to ... consistency constraints".
  - CAPRI results were "relatively close to AGLINK-COSIMO results", but consistency constraints force
    deviations from the targets.
  - Validation at Member State level was a bottleneck.

## 2. EU Agricultural Outlook (DG AGRI + JRC)

- **The latest edition is EU Agricultural Outlook 2025-35**, published 16 Dec 2025 [S13][S14]. The
  medium-term page still links the 2024-35 PDF as the newest download, although it describes 2025-35
  [S15].
- **Model**: "the AGLINK-COSIMO agro-economic model used by the European Commission to run the baseline
  simulation" [S14].
  - The global environment comes from the OECD-FAO Outlook 2025-2034.
  - MAGNET supplies the food-security and inequality indicators.
  - AGMEMOD supplies Member-State outlooks for fruit, vegetables and olive oil.
  - POTEnCIA (JRC) supplies the biofuel projections [S14].
  - In the 2024 edition, the environmental indicators came from the CAPRI MTO baseline [S8].
- **The annual process** is documented in the EU-module documentation of Aglink-Cosimo [S16, pp. 4-5]:
  1. Start from the June OECD-FAO baseline.
  2. Recalibrate the EU component with updated medium-term macro projections and the DG AGRI short-term
     outlook (a 6-18-month forecast from the market units).
  3. Review by commodity experts for arable crops, sugar/biofuels, meat and dairy.
  4. Test at an October workshop with stakeholders.
  5. Publish in December.
  6. The result then feeds the next OECD-FAO Outlook.
- **2025 edition specifics** [S14]:
  - Workshop held 22-23 Oct 2025.
  - Production and trade data up to end-September 2025, market intelligence up to end-October 2025.
  - Macro: short-term from AMECO and the ECB (Sept 2025), medium-term from S&P Global and OECD-FAO.
  - CAP 2027 payment levels are carried to 2035, and the 2028-34 MFF/CAP proposals are excluded.
  - The outlook "should not be interpreted as a forecast, but as a baseline".
- **Uncertainty**: stochastic simulations on macro variables and crop yields. The 2024 edition states "a
  thousand stochastic simulations" [S8]. The method follows Araujo-Enciso et al. (2017) [S17].
- **EU disaggregation in Aglink's EU module** [S16, pp. 2, 10]:
  - Two supply/demand regions: E14 (pre-2004 members excluding the UK) and NMS (13 newer members).
  - Trade, stocks and biofuel use are endogenous at the EU level (EUN).
  - Trade is modelled at EU-27 level.
  - The JRC inventory page says "the EU is treated as a single market" [S18]. This holds for
    price formation, not for supply.
- **Published data and format**:
  - The report is a PDF.
  - Balance sheets are visualised in the Agri-food data portal "Medium-term outlook" dashboard, an iframe
    app [S19]. Sankey flows are on the JRC DataM portal [S15]. **[UNVERIFIED]** whether the dashboard offers
    CSV or Excel export. The page does not mention it, and I found no static table files.
  - **A usable machine-readable route**: the OECD SDMX API serves the full OECD-FAO Outlook, including the
    EU aggregate, as CSV. Dataflows exist from `DSD_AGR@DF_OUTLOOK_2021_2030` to
    `DSD_AGR@DF_OUTLOOK_2026_2035`. I tested this, for example with `.../data/OECD.TAD.ATM,DSD_AGR@DF_OUTLOOK_2026_2035,/EU.A.CPC_0111...?format=csvfilewithlabels`,
    which returns EU wheat feed/food/... to 2035 [S20].
  - Per [S16], the EU numbers in OECD-FAO year N come from DG AGRI's December N-1 outlook. Treat this as a
    vintage, not as identical to the latest MTO.

## 3. Aglink-Cosimo (OECD-FAO): baseline construction

- **Process** (2021-2030 Methodology annex, verbatim structure) [S21]:
  1. "Starting values" are gathered.
     - OECD side: "an annual questionnaire is circulated in November to national administrations" on
       expected commodity developments and policies.
     - FAO side: "model-based projections and consultations with FAO commodity specialists".
     - Macro inputs come from the IMF, the World Bank and the UN.
  2. Aglink-Cosimo is used "to facilitate a consistent integration of the initial data and to derive an
     initial baseline", ensuring global consumption equals production.
  3. Review.
     - OECD countries: results are "compared with the questionnaire replies" and any issues are discussed
       bilaterally.
     - FAO modules: results are reviewed by in-house and international experts.
  4. A "second baseline" follows, based on the consensus of both Secretariats.
  5. Discussion in the OECD Group on Commodity Markets, then data revisions, then the final baseline.
  6. The annex states that the projections "are a combination of projections and expert knowledge". It
     adds that "the use of a formal modelling framework reconciles inconsistencies between individual
     country projections".
  - The 2025-2034 edition's Box 1.1 confirms that the questionnaire process and the multi-tier review are
    unchanged in outline. Data and policies are as of Dec 2024, and macro input comes from Oxford
    Economics [S22].
- **Structure**:
  - Recursive-dynamic and partial equilibrium, with 10-year projections. "Outcomes for one year influence
    those for the next years (e.g. through herd sizes)" [S21].
  - It is not spatial: commodities are homogeneous, and imports and exports are determined separately
    [S21].
  - The full model covers 35 countries, 12 regional aggregates and 29 world prices [S23].
- **Equations and calibration** (EU module, 2021 version) [S16]:
  - Double-log behavioural equations with additive residual "R-factors".
  - "Constants are chosen such that the average of the residuals is zero in the calibration period". The
    R-factors replicate history exactly, are endogenous during calibration and are fixed during simulation.
  - The yield equation is a profit-margin term (lagged price) plus a **linear time trend** ("disembodied
    Hicks-neutral technological change") plus the R-factor.
  - Food demand includes a time trend and is homogeneous of degree zero.
- **What carries between years** [S16]:
  - Lagged producer prices and costs in the yield equation.
  - A weighted 3-year revenue average for area incentives (0.5/0.3/0.2).
  - Lagged pasture and fodder land.
  - Private stocks, driven by lagged stocks. Intervention stocks are exogenous.
- **Expert adjustment mechanism**: year-specific changes in R-factors or exogenous values [S18]. This is how
  expert or questionnaire targets are imposed. It is a manual, iterative adjustment, not a statistical
  estimator.
- **Partial stochastic analysis** [S21]:
  - (i) Detrend history with a Hodrick-Prescott filter, applied to yield levels and to year-on-year
    changes for macro variables.
  - (ii) Generate 1 000 sets: for each projection year, draw one historical year (1995-2020) and apply
    that year's relative deviation from trend. All variables take the same historical year, with macro
    and yields drawn separately.
  - (iii) Run the model for each set. Running 1 000 sets gave 98 % successful solves.
  - The JRC methods paper compares cubic-trend, VAR and copula approaches [S17].

## 4. Other models, briefly

| Model | Baseline approach | Key source |
|---|---|---|
| **AGMEMOD** (EU Member-State PE, recursive) | **Behavioural / econometric**: "the system has been econometrically estimated at individual Member State level"; parameters are calibrated where estimation is impossible. It assumes "steady demand and yield trends". Macro inputs come from the EU Outlook. EU aggregates are matched to AGLINK through a scaling procedure, and the model is calibrated to world prices. **Expert validation**: country experts rate results from "much too high" to "much too low", followed by a European workshop of about 50 experts. | [S24] |
| **ESIM** (EU PE, comparative static) | **Externally imposed** (DG AGRI outlook). Step 1 builds Member-State target balances from Aglink % changes. Step 2 shifts behavioural curves (technical-progress parameter, demand shifters) to reproduce them. Known problems: shifted yields became implausible (rapeseed EU-N12), and a static model over-reacts compared with dynamic Aglink. Documentation dates from 2012. **[UNVERIFIED]** whether ESIM is still used in current EC baselines. | [S12][S25] |
| **FAPRI-MU** (US multi-market PE) | **Behavioural + expert**. Econometric parameters "where practical", otherwise literature and judgement. A preliminary 10-yr baseline is reviewed at an annual workshop (USDA, universities, private sector) and then revised. A **stochastic baseline** varies weather, energy and other exogenous drivers. The 2025 baseline used January 2025 information and S&P Global macro data. **[UNVERIFIED]** number of stochastic draws (commonly cited as 500). | [S26][S27] |
| **USDA Long-term Projections** (comparison) | **Behavioural + consensus**. Econometric and process models produce initial projections, which are iterated by an interagency committee. Results are "a composite of analytical tools and judgment-based analyses". 2026 edition: OCE-2026-1, data to the Nov-2025 WASDE. | [S28][S29] |
| **GLOBIOM** (global PE, LP, recursive) | **Driver-based (behavioural / biophysical), externally imposed drivers**. 10-yr steps up to 2050/2100. Population, GDP and technical progress are exogenous. Demand elasticities come from USDA. Crop parameters come from EPIC. The base year is 2000, and the first ~20 years serve for validation, per the IIASA and JRC pages. **[UNVERIFIED]** later base-year updates in current EU versions. Used as long-run supports in CAPRI. | [S30][S31][S4] |
| **MAGNET** (global CGE, recursive) | **Driver-based, externally imposed**. GDP is targeted by swapping it with an endogenous technology variable, and population and labour come from external projections. "Land productivity is assumed to follow exogenous yield projections" (IMAGE/FAO-based in older documentation). The JRC inventory lists the EU mid-term outlook among baseline drivers. In SCENAR 2040, the MAGNET baseline is "consistent with" the 2023 EU Outlook. | [S32][S33][S34] |
| **Thünen-Baseline** (DE network) | Several models (MAGNET, AGMEMOD, CAPRI, RAUMIS, FARMIS) produce "a harmonised overall outcome". Macro and world-market inputs come from the EU Outlook 2023-35. Preliminary results are discussed with federal and state ministries. Biennial, horizon 2034. | [S11] |

Earlier harmonisation work in the SUPREMA project (H2020, about 2018-2021) produced harmonised CAPRI,
GLOBIOM, MAGNET, AGMEMOD and IFM-CAP baselines for 2030 and 2050 (JRC dataset) [S35]. I could not access
its baseline deliverable D3.1 **[UNVERIFIED details]**.

## 5. Critiques, comparisons and similar estimators

- **Adenäuer (2008, EAAE)** compared the two philosophies. CAPRI uses "generic and automatic procedures
  whenever possible", while Aglink-Cosimo relies more on expert knowledge. The paper argues that combining
  them would improve both [S36]. This predates 2018, but it is the only direct CAPRI-vs-Aglink baseline
  comparison I found.
- **Bora, Katchova & Kuethe (2023, AJAE 105(4))** evaluated USDA and FAPRI baselines ex post [S37]:
  - Error and bias grow with the horizon.
  - Predictive content for most variables fades after about 4-5 years.
  - Neither baseline dominates the other.
  - This is the main recent peer-reviewed evidence on the accuracy of medium-term baselines.
- **von Lampe et al. (2014, Agricultural Economics, AgMIP)**: harmonising drivers narrows but does not
  remove inter-model spread. Elasticities and variable definitions explain much of the remaining
  divergence [S38]. This is pre-2018 but foundational for "baseline consistency".
- **The Bayesian reading of CAPTRD.** The CAPRI manual uses "prior information" language for supports and
  variance-normalised penalties [S1].
  - Heckelei, Mittelhammer & Jansson (2008) show that a Bayesian (HPD-type) formulation can replace
    GME/GCE for underdetermined, constrained problems [S39].
  - Step 2 with trust-level variances is formally close to a posterior-mode estimator with Gaussian priors
    under constraints. **This is my interpretation.** The manual itself applies the term HPD explicitly
    only to the market-model calibration [S1].
- **Constrained forecast reconciliation (statistics literature, 2019-2024)** solves almost the same problem
  as CAPTRD step 2.
  - Base forecasts are projected onto a linear constraint space: ỹ = (I − W C′(C W C′)⁻¹ C) ŷ.
  - MinT (Wickramasuriya, Athanasopoulos & Hyndman 2019, JASA) estimates W from the forecast-error
    covariance and is MSE-optimal under unbiasedness [S40].
  - Girolimetto & Di Fonzo (2024, Statistical Methods & Applications) generalise this to **any linear
    constraints**, such as accounting identities (GDP income/expenditure/output), with point and
    probabilistic versions [S41].
- **Open-source implementations**:
  - R `FoReco` [S42] and Python `hierarchicalforecast` (Nixtla), which includes non-negative
    reconciliation [S43].
  - These handle linear constraints only. CAPTRD has bilinear identities (production = yield × level) and
    bounds, so they need an NLP or iterative linearisation.
  - I found **no open-source implementation of a CAPTRD-like nonlinear constrained trend system for
    agriculture**, apart from CAPRI's own GAMS code. A public repository "nuvolaTeam/CAPRI-MOD" (Python)
    appeared in search results [S44]; I did not inspect it.

## 6. Implications for CAPTRD-MOD

1. **Keep CAPTRD's three-layer logic. It is still the CAPRI method of record.** No source shows a post-2022
   replacement [S1][S5][S6]. Long-run (2050) handling is horizon-dependent blending of medium-run supports
   (Aglink/MTO) with long-run supports (GLOBIOM, IMPACT, FAO) [S1][S4]. Implement the blending weights as a
   CSV-driven schedule by year, not as code constants.
2. **Supports ingestion: use the OECD SDMX CSV as the machine-readable source of Aglink-Cosimo EU
   projections** [S20]. The DG AGRI MTO is published only as PDF plus dashboard [S15][S19].
   - Record the vintage explicitly, for example "OECD-FAO 2026-35 = DG AGRI MTO Dec-2025" per [S16].
   - CAPRI itself runs with a lag: MTO 2023 was used for the 2024 CAPRI baseline [S8], and the 2020 MTO
     was used in a 2023 analysis [S7].
3. **Make the support aggregates configurable.** CAPRI's step 3 uses EU15 and EU12 supports [S1], whereas
   the current Aglink EU module uses E14 and NMS (13) [S16]. The mapping from support regions to Member
   States should be a CSV table.
4. **Reproduce the trust-level mapping exactly as documented** before considering alternatives [S1]: levels
   1-10, ±55 %·(1/trust) of the mean at 99.9 %, and DG AGRI default 5. Keep trust levels and the ±2.5 %/yr
   style bounds in CSV. The ESIM experience (shifted yields becoming implausible [S12]) argues for keeping
   those bounds and for reporting every binding bound.
5. **Validation benchmark: for linear sub-blocks, step 2 can be cross-checked against forecast
   reconciliation** [S41][S42][S43]. This is a test oracle, not a replacement.
   - **Proposed "beyond CAPRI" option, for the user to decide**: estimate W from step-1 residual
     covariances (MinT-style [S40]) instead of the diagonal R²/variance weights. Cross-series correlations
     would then inform the adjustment.
6. **Add ex-post skill reporting, beyond CAPRI.** Bora et al. find informativeness fades after about 4-5
   years [S37]. A rolling-origin backtest of step-1 trends (fit to t0, compare t0+1…t0+10) would quantify
   where trends or supports should dominate. It would also justify the R²-based fallback empirically.
7. **Optional stochastic baseline, beyond CAPRI.** The Aglink PSA recipe is simple and documented [S21]: HP
   detrend, resample whole historical years jointly (1 000 draws), then rerun.
   - In CAPTRD-MOD, step-1 residuals could be resampled jointly by historical year, and the step 2/3 system
     re-solved to give bands. DG AGRI already publishes such bands [S8][S14].
8. **Produce an expert-review package.** Every institution iterates a preliminary baseline with experts:
   OECD questionnaires and bilateral review [S21], the DG AGRI October workshop [S14][S16], AGMEMOD expert
   ratings [S24], the FAPRI workshop [S27] and Thünen ministry discussions [S11].
   - Output per-series diagnostics as CSV: step-1 versus final values, support pull, binding constraints
     and implied growth rates.
   - Accept expert supports back as CSV with mean and trust level, which mirrors CAPRI step 2.2 [S1].
9. **Do not adopt Aglink's R-factor approach.** Aglink imposes expert views by manually editing residuals
   [S16][S18], which is not reproducible. CAPTRD's explicit, weighted supports are the more transparent
   design. Adenäuer [S36] makes the same contrast.
10. **Scope note.** GLOBIOM and MAGNET baselines are driver-based (GDP, population, exogenous yields)
    [S30][S32]. If CAPTRD-MOD later needs SSP-consistent 2050 runs (as in the Thünen project [S9]), they
    should enter as long-run supports, not replace step 1. That matches the CAPRI practice in [S1][S4].

## Sources

- [S1] CAPRI online manual, "Baseline generation": https://www.capri-model.org/dokuwiki_help/doku.php?id=baseline_generation
- [S2] CAPRI manual start page (PDF "2022 January"): https://www.capri-model.org/dokuwiki_help
- [S3] CAPRI wiki recent changes: https://www.capri-model.org/dokuwiki_help/doku.php?id=start&do=recent
- [S4] DG CLIMA, "Methodology underlying the CAPRI model" (21 Sep 2021): https://climate.ec.europa.eu/system/files/2021-10/policy_strategies_analysis_models_capri_model_methodology_en.pdf
- [S5] Gocht, General Introduction to CAPRI (Thünen course, 16 Apr 2026): https://bw-pages.thuenen.de/capri/course/pdf/Day1/1_1_General%20Introduction%20to%20CAPRI_full.pdf
- [S6] Witzke, "CAPRI modelling system" (Tools4CAP, 3 Dec 2024): https://www.tools4cap.eu/wp-content/uploads/2024/12/5_CAPRI-modelling-system.pdf
- [S7] EU Agricultural Outlook 2023-35 (copy): https://cdn.nieuweoogst.nu/public/file/235977.pdf
- [S8] EU Agricultural Outlook 2024-35: https://agriculture.ec.europa.eu/document/download/48b04248-de6c-4608-bbcf-f2c9e0ed9d2b_en
- [S9] Thünen, long-term climate mitigation policies for the agri-food sector (CAPRI 2050 baseline): https://thuenen.de/en/cross-institutional-projects/agricultural-long-term-policies-for-climate-mitigation-agrilop-1
- [S10] JRC model inventory, SWD/2024/63: https://web.jrc.ec.europa.eu/policy-model-inventory/explore/ias/ia-ce3b1673934f3608adfa84fc976ea13e
- [S11] Haß et al. (2024), Thünen-Baseline 2024-2034, Thünen Report 117: https://ageconsearch.umn.edu/record/348230/files/dn068888.pdf
- [S12] Himics, Artavia, Hélaine (2014), JRC72882: https://joint-research-centre.ec.europa.eu/system/files/2014-05/JRC72882_Calibration_report_CAPRI_ESIM.pdf
- [S13] DG AGRI news, EU agricultural outlook 2025-35 (16 Dec 2025): https://agriculture.ec.europa.eu/media/news/eu-agricultural-outlook-2025-35-eu-agriculture-navigates-challenges-while-embracing-opportunities-2025-12-16_en
- [S14] EU Agricultural Outlook 2025-35 (copy): https://www.ypaithros.gr/wp-content/uploads/2025/12/eu_agricultural_outlook.pdf
- [S15] DG AGRI medium-term outlook page: https://agriculture.ec.europa.eu/data-and-analysis/markets/outlook/medium-term_en
- [S16] Pieralli, Chatzopoulos, Elleby, Pérez Domínguez (2022), EU module of Aglink-Cosimo 2021, JRC130965: https://publications.jrc.ec.europa.eu/repository/bitstream/JRC130965/JRC130965_01.pdf
- [S17] Araujo-Enciso, Pieralli, Pérez Domínguez (2017), Partial stochastic analysis with Aglink-Cosimo, JRC108837: https://publications.jrc.ec.europa.eu/repository/handle/JRC108837
- [S18] JRC model inventory, Aglink-Cosimo: https://web.jrc.ec.europa.eu/policy-model-inventory/explore/models/model-aglink-cosimo-print
- [S19] Agri-food data portal, outlook: https://agridata.ec.europa.eu/extensions/DataPortal/outlook.html
- [S20] OECD SDMX dataflows (tested 22 Oct 2026): https://sdmx.oecd.org/public/rest/dataflow/OECD.TAD.ATM
- [S21] OECD-FAO Agricultural Outlook 2021-2030, Methodology annex (FAO-hosted PDF): https://openknowledge.fao.org/server/api/core/bitstreams/313b0161-6176-4a76-b505-6f6d3836b9c7/content
- [S22] OECD-FAO Agricultural Outlook 2025-2034, Ch. 1, Box 1.1 (FAO-hosted): https://openknowledge.fao.org/server/api/core/bitstreams/2d11baa7-2cf7-44b1-9fc7-28ce69943b1d/content
- [S23] JRC130965 record/abstract: https://ideas.repec.org/p/ipt/iptwpa/jrc130965.html
- [S24] Salamon et al. (2019), AGMEMOD Outlook 2018-2030, Thünen WP 114: https://ageconsearch.umn.edu/record/281305/files/dn060597.pdf
- [S25] Grethe (ed.) (2012), ESIM documentation: https://apo.uni-hohenheim.de/en/organization/publication/european-simulation-model-esim-documentation-model-code-parameterization-database-version-of-december-11-2012
- [S26] FAPRI-MU 2025 baseline release (Beef Magazine, 7 Apr 2025): https://www.beefmagazine.com/farm-business-management/mizzou-institute-releases-baseline-food-and-agricultural-outlook-report
- [S27] USDA NIFA project page, FAPRI-MU modelling system: https://portal.nifa.usda.gov/web/crisprojectpages/0233869-economic-analysis-of-agricultural-and-biofuel-markets-and-policies-to-inform-public-policy.html
- [S28] USDA ERS Agricultural Baseline Database documentation: https://www.ers.usda.gov/data-products/agricultural-baseline-database/documentation
- [S29] USDA Agricultural Projections to 2035 (OCE-2026-1): https://ageconsearch.umn.edu/record/393820/files/OCE-2026-1.pdf
- [S30] JRC model inventory, GLOBIOM: https://web.jrc.ec.europa.eu/policy-model-inventory/explore/models/model-globiom-print
- [S31] IIASA GLOBIOM page: https://iiasa.ac.at/web/home/research/modelsData/GLOBIOM/GLOBIOM.en.html
- [S32] MAGNET documentation (WUR): https://edepot.wur.nl/310764
- [S33] JRC model inventory, MAGNET: https://web.jrc.ec.europa.eu/policy-model-inventory/explore/models/model-magnet
- [S34] JRC DataM, SCENAR 2040: https://datam.jrc.ec.europa.eu/datam/mashup/SCENAR2040/
- [S35] SUPREMA dataset (JRC, 2020): https://agris.fao.org/search/en/records/67a0c55420478411b0270cdd
- [S36] Adenäuer (2008), CAPRI versus AGLINK-COSIMO, EAAE: https://ideas.repec.org/p/ags/eaae08/44120.html
- [S37] Bora, Katchova, Kuethe (2023), AJAE 105(4): https://ideas.repec.org/a/wly/ajagec/v105y2023i4p1116-1148.html
- [S38] von Lampe et al. (2014), Agricultural Economics 45(1): https://www.rti.org/publication/why-do-global-long-term-scenarios-agriculture-differ-overview-agmip-global-economic
- [S39] Heckelei, Mittelhammer, Jansson (2008), Bonn DP: https://ideas.repec.org/p/ags/ubfred/56973.html
- [S40] Wickramasuriya, Athanasopoulos, Hyndman (2019), JASA 114(526): https://research.monash.edu/en/publications/optimal-forecast-reconciliation-for-hierarchical-and-grouped-time/
- [S41] Girolimetto & Di Fonzo (2024), Stat. Methods & Applications, doi:10.1007/s10260-023-00738-6: https://research.unipd.it/handle/11577/3502532 (preprint https://ar5iv.labs.arxiv.org/html/2305.05330)
- [S42] FoReco (CRAN): https://cran.r-project.org/web/packages/FoReco/index.html
- [S43] HierarchicalForecast (Nixtla): https://arxiv.org/html/2207.03517v6 ; non-negative example: https://nixtlaverse.nixtla.io/hierarchicalforecast/examples/nonnegativereconciliation.html.md
- [S44] GitHub nuvolaTeam/CAPRI-MOD (seen in search, not inspected): https://github.com/nuvolaTeam/CAPRI-MOD

### Could not verify / not accessed
- The OECD-FAO 2025-34 and 2026-35 Methodology annexes: oecd.org was blocked, so the 2021-30 annex and the
  2025-34 Box 1.1 were used instead.
- Whether the DG AGRI MTO dashboard exports CSV or Excel.
- The FAPRI number of stochastic draws.
- GLOBIOM base-year updates beyond 2000 in current EU versions.
- SUPREMA D3.1 details.
- How the Thünen 2050 CAPRI baseline used CAPTRD.
- Whether ESIM is still in active EC use.
- Any CAPTRD code change after 2022. The CAPRI SVN trunk was not inspected.
