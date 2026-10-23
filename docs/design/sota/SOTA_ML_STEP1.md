# State of the art: statistical and ML methods for multi-year projection of short annual agricultural series

*Research note for CAPTRD-MOD step 1 (alternative to CAPRI's x = a + b·t^c WLS trend). Compiled 22 Oct 2026.*

## Evidence tags

- **[PR]**: peer-reviewed journal or conference paper.
- **[PP]**: preprint with no confirmed peer review.
- **[DOC]**: model card, package metadata or official documentation.
- **[BLOG]**: blog or press item. Treat it as a claim only.
- **[NF]**: a standard reference whose content I did **not** re-fetch in this session. I give it from prior knowledge, with a DOI or URL so you can check it.

Numbers are quoted only where I read them in a fetched source. Where a source could not be fetched (ScienceDirect, PMC captcha, HAL bot block), I say so.

## 0. Framing: why CAPTRD's problem is unusual

- The series are annual and short (20–35 points). The horizons are long: from a 2020 data end to 2030–2035 is h = 10–15. The series also sit inside a constrained system.
- Most benchmark evidence on yearly data is for **h = 6** (M3 and M4 yearly) or h = 4 (Tourism yearly). **No large public benchmark I found tests yearly series at h = 10–15.** Any claim of superiority at CAPRI horizons therefore has to come from our own back-casting.
- In the yield ML literature, "beats trend" usually means **in-season** forecasting with current-year weather or remote sensing (§3). That information does not exist 10 years ahead, so those results do not carry over to baseline projection.

## 1. Methods: state of the art and what is known for short annual series

### 1.1 Classical and statistical methods

- **Exponential smoothing with damped trend, Theta, ARIMA with drift.** These are the standard strong benchmarks for yearly data.
  - Makridakis et al. (2018) tested 8 statistical and 10 ML methods on 1,045 M3 monthly series, horizons 1–18. Statistical methods beat ML at every horizon on sMAPE and MASE. Theta, the combination method (Comb) and ARIMA did best, and Naive2 beat about half the ML methods. Better in-sample fit did not predict out-of-sample accuracy, which points to ML overfitting. [PR] https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0194889
  - Caveat: that study used monthly series, not yearly. The authors themselves warn that results may not generalise.
- **Theta** amounts to simple exponential smoothing (SES) with drift (Hyndman & Billah 2003, IJF 19(2), doi:10.1016/S0169-2070(01)00143-1) [PR][NF]. On M3 yearly (sMAPE, h = 6), Theta scored 16.90 and the automatic ARIMA 17.73. The table also lists Naive2 at 17.88, Comb S-H-D at 17.07, ForecastPro at 17.14 and DOTM (dynamic optimised Theta) at 15.94. [PR, figures from Table 14 of N-BEATS] https://arxiv.org/pdf/1905.10437v4
- **Bayesian exponential smoothing with a "global" trend (LGT).** The trend combines a global term γ·l_t^ρ, a power of the *level* lying between linear and exponential growth, with a damped local trend. It uses Student-t errors and level-dependent variance.
  - On M3 yearly (645 series, h = 6), LGT scored sMAPE 15.18 and MASE 2.48. Comparators: Theta 16.75/2.77, ETS 17.00/2.86, best original M3 entry 16.42/2.63.
  - Removing the global trend term caused the largest loss (sMAPE 16.23).
  - Intervals were better calibrated than ETS and ARIMA, but still too narrow.
  - Cost: about 50 s per series with Stan, or about 4 s with a Gibbs sampler.
  - Venue not confirmed (arXiv). [PP] https://arxiv.org/html/2309.13950v3
  - Of the benchmarked methods, this is the conceptually closest relative of CAPRI's t^c curvature. Note: ρ acts on the level, not on time.
- **Dynamic linear (local linear trend) models for yields.** Michel & Makowski (2013) compared eight models on FAO and French regional wheat yields. Holt-Winters and dynamic linear models were the most accurate and performed equally well. DLMs also give uncertainty and a retrospective trend. [PR] https://ideas.repec.org/a/plo/pone00/0078615.html (abstract only; the validation design was not checked)
- **Linear versus compound (exponential) yield trend.** Grassini et al. (2013) found that linear trajectories describe historical cereal yields adequately, so relative growth rates decline. Compound-growth projections were often too optimistic. Plateaus were found for, among others, NW-European wheat. [PR] https://ideas.repec.org/a/nat/natcom/v4y2013i1d10.1038_ncomms3918.html
  - This matters for CAPRI's t^c with c > 1 versus c < 1. Plateau detection argues for damped or saturating forms.
- **Shrinkage and partial pooling across regions (hierarchical Bayesian or empirical Bayes trends).** For short panels, pooling slope and curvature parameters across NUTS2 regions within a country, or across countries per product, is the classical remedy for overfitting short series.
  - I found **no** large out-of-sample benchmark of this specifically for EU agricultural series. Recommending it is my judgement, not an established result.
  - The closest evidence is the "global model" literature in §1.2: pooling across series reduces the gap between in-sample and out-of-sample error.

### 1.2 Machine learning: global models, boosting, deep learning

- **Local versus global.** Montero-Manso & Hyndman (2021, IJF 37(4)) showed that global models fitted across many series can beat per-series models even when the series are unrelated. They also showed that short series make local models prone to overfitting.
  - On M4 yearly, a single global polynomial AR(12) reached MASE 3.01, which they state would have ranked 2nd in M4.
  - Scale normalisation is important. [PR] https://arxiv.org/pdf/2008.00444 , https://ideas.repec.org/a/eee/intfor/v37y2021i4p1632-1653.html
  - This is the main theoretical argument for gradient boosting or NNs on pooled, scaled CAPRI series. With roughly 10³–10⁴ series of 25–35 points, we are in the "many short series" regime where global models help.
- **Size matters.** Cerqueira, Torgo & Soares argue that ML only loses to statistical methods when samples are very small, and that ML gains as sample size grows (learning curves). [PR, J. Intell. Inf. Syst. 2022 per search listing; abstract read on arXiv] https://arxiv.org/abs/1909.13316v1
  - Our per-series samples are at the very small end. Only pooling changes this.
- **Hybrid statistical and NN methods (ES-RNN, N-BEATS).** M4 winner Smyl combined per-series exponential smoothing with a global dilated LSTM, with yearly series truncated to the last 60 years. [BLOG, by the author] https://www.uber.com/blog/m4-forecasting-competition
  - N-BEATS (pure DL, ICLR 2020), on **M4 yearly sMAPE**:

    | Method | sMAPE |
    |---|---|
    | Best pure ML entry | 14.397 |
    | Best statistical entry | 13.366 |
    | Smyl hybrid | 13.176 |
    | N-BEATS ensemble | 12.913 |

    [PR] https://arxiv.org/pdf/1905.10437v4
  - On Tourism yearly (MAPE, h = 4), N-BEATS scored 21.44, Theta 23.45 and damped trend 28.15 (same source).
  - DL gains on yearly data are therefore real but modest: about 2–4% sMAPE over the best statistical method. They also require training on tens of thousands of series.
- **LSTM, transformers trained from scratch, random forests.** I found no evidence that these beat damped-trend or Theta on *short annual* series at multi-year horizons. Tree models (RF, GBM) cannot extrapolate a trend beyond the training range unless the target is differenced or detrended. This is a design issue, not an empirical finding.
- **Time-series foundation models (zero-shot).**
  - **Chronos** (Ansari et al., TMLR 2024; tokenised T5) [PR] https://arxiv.org/html/2403.07815v3
    - The paper notes that quantisation makes series with strong trends "theoretically infeasible" to model. This is relevant for trending yields and areas.
    - I could not extract the per-dataset yearly results from the fetched text. *Unverified* whether M4 yearly was in the training or the zero-shot set.
  - **Chronos-2** (Oct 2025) [DOC] https://huggingface.co/amazon/chronos-2
    - Apache-2.0. Supports covariates and multivariate or cross-series learning.
    - The vendor claims state-of-the-art zero-shot accuracy on fev-bench, GIFT-Eval and Chronos Benchmark II.
  - **TimesFM 2.5** (ICML 2024 paper for v1) [DOC] https://huggingface.co/google/timesfm-2.5-200m-pytorch
    - Weights Apache-2.0.
    - A blog claims the newer TimesFM 3.0 weights are non-commercial. [BLOG, unverified] https://www.beri.net/article/timesfm-vs-chronos-vs-moirai-time-series-foundation-model-licence-bigquery-sagemaker-cost-2026
    - The PyPI package `timesfm` 3.0.2 is Apache-2.0 (code).
  - **Moirai 1.1 and 2.0**: weights **CC BY-NC 4.0**, "research purposes only". [DOC] https://huggingface.co/Salesforce/moirai-2.0-R-small , https://huggingface.co/Salesforce/moirai-1.1-R-base
  - **Lag-Llama**: Apache-2.0. Trained with context 32. The card says it "performs best when finetuned". [DOC] https://huggingface.co/time-series-foundation-models/Lag-Llama
  - **GIFT-Eval** (Aksu et al.; NeurIPS 2024 workshop) [PP/workshop] https://arxiv.org/html/2410.10393v2
    - Its annual subset has 22,974 series at h = 6, which is almost certainly M4 yearly (dataset list not verified).
    - It states that "from daily to yearly frequencies, foundation models consistently outperform other approaches".
    - It also states that the pre-training data of TimesFM, Chronos and Moirai show "partial data leakage" relative to GIFT-Eval.
  - **fev-bench** (Shchur et al. 2025, Amazon authors) [PP] https://arxiv.org/html/2509.26468v2
    - 4 yearly datasets.
    - On scaled quantile loss, all pretrained models beat the best statistical approach (the SCUM ensemble of ETS, ARIMA, Theta and CES). Win rates: Chronos-2 91.4%, TimesFM-2.5 77.6%, SCUM 45.5%.
    - Self-reported leakage: Moirai-2.0 28%, TimesFM-2.5 10%, Chronos-2 0%.
    - These results are aggregated over all frequencies. I could not isolate the yearly-only results.
  - **Caveats for CAPTRD, which are my assessment:**
    - (a) Benchmark authors are often the model vendors.
    - (b) Yearly evidence is at h ≤ 6.
    - (c) Back-cast leakage risk is serious. If pre-training corpora contain FAOSTAT, Eurostat or World Bank annual series, then a back-cast from origin 2005 may have "seen" 2006–2020. We cannot audit this, and it would bias the comparison against CAPRI's trend in favour of the foundation model.
    - (d) The models are opaque, and their outputs are not reproducible without pinning weights.

### 1.3 Combinations

- In M4, 12 of the 17 most accurate methods were combinations. None of the 6 pure ML methods beat the Comb benchmark (SES/Holt/damped), and only one beat Naive2. The 95% intervals of the top two methods had near-nominal coverage. [Secondary: Wikipedia summary of Makridakis et al. 2020, IJF 36(1):54–74, doi:10.1016/j.ijforecast.2019.04.014; the primary paper was not fetchable (ScienceDirect robots block)] https://en.wikipedia.org/wiki/Makridakis_Competitions
- In M5 (daily, hierarchical retail, many covariates), pure ML (LightGBM, DNN ensembles) won. This is not comparable to short annual series. (Same source.)

## 2. Competitions and benchmarks: what works for short annual series at long horizons

| Evidence | Yearly setting | Finding | Type |
|---|---|---|---|
| M3 (Makridakis & Hibon 2000) | 645 series, ≥14 obs, h = 6 | Simple methods and combinations are competitive. On sMAPE: Theta 16.90, auto-ARIMA 17.73, Naive2 17.88 | [PR][NF] via the N-BEATS table above |
| M4 (2018–2020) | about 23,000 yearly series, h = 6 | Best statistical 13.37 vs best pure ML 14.40 sMAPE. Hybrid ES-RNN 13.18 | [PR] figures via N-BEATS |
| Post-M4 DL (N-BEATS) | M4/M3/Tourism yearly | Pure DL beats statistical methods by a small margin when trained on the large pooled set | [PR] |
| LGT (Bayesian ETS) | M3 yearly | Best sMAPE and MASE among methods compared (15.18 / 2.48) | [PP] |
| Global linear AR | M4 yearly | MASE 3.01 (≈2nd place) with 24 parameters | [PR] |
| GIFT-Eval / fev-bench | M4-like yearly, h = 6 | Foundation models ahead; leakage partly present | [PP] |
| Monash archive (Godahewa et al., NeurIPS 2021 D&B) | Includes M1/M3/M4/Tourism yearly | Benchmark repository; useful for pre-testing our pipeline | [PR][NF] https://arxiv.org/abs/2105.06643 |

What this adds up to:

- At h ≤ 6, on large pools of yearly series, a well-designed hybrid or global model, or a foundation model, can beat damped trend and Theta by a few per cent.
- Pure ML per series, or naive DL, does not.
- At h = 10–15, the evidence is absent. Uncertainty compounds there, and trend form (linear, damped or saturating) is likely to dominate.
- How long official agricultural projections stay informative is itself limited. Bora & Katchova assessed USDA and FAPRI baselines since 1997 and found that "most variables lose predictive value after about 4–5 years". [BLOG summary of a working report] https://u.osu.edu/aede/?p=249

## 3. Agricultural applications

- **JRC MARS / MCYFS** is operational, in-season and regression-based.
  - Paudel et al. (2021, Agric. Syst. 187:103016) built a reproducible ML baseline. Its error was comparable to MCYFS in some crops and countries, and about twice MCYFS in others (e.g. FR potatoes and sugar beet). [PR] https://ideas.repec.org/a/eee/agisys/v187y2021ics0308521x20308775.html
  - Paudel et al. (2022, Field Crops Res. 276:108377) covered 35 case studies. Regional ML had lower NRMSE than a **linear trend model** (Wilcoxon p ≈ 2e-7), and was similar to the operational system at national level. [PR] https://research.wur.nl/en/publications/machine-learning-for-regional-crop-yield-forecasting-in-europe/
  - **Not transferable:** the gain comes from current-season weather and remote sensing, not from better trend extrapolation.
- **JRC ASAP yield-forecast methodology.** The "trend" model uses the previous 3 years' yields, fitted with ridge or Gaussian-process regression, as a benchmark against which agro-meteorological models must prove added value. [DOC] https://agricultural-production-hotspots.ec.europa.eu/files/yield_forecast-methodology_summary_v1.0.pdf
- **CY-Bench** (Kallenberg, Paudel et al., ESSD 18:3997, 2026) is a sub-national maize and wheat benchmark. It uses **leave-one-year-out** validation and NRMSE/MAPE/R². ML results are "only illustrative". [PR] https://essd.copernicus.org/articles/18/3997/2026/
  - LOYO is fine for in-season prediction but **not** for trend projection: it uses the future to fit the trend.
- **OECD-FAO Aglink-Cosimo.** The baseline is built from country questionnaire projections, with log-linear behavioural equations calibrated through r-factors. Uncertainty comes from a partial stochastic module (Araujo-Enciso et al. 2017). [DOC] https://web.jrc.ec.europa.eu/policy-model-inventory/explore/models/model-aglink-cosimo-annex4
  - I did not find an ML trend step in Aglink. The detail of yield-trend construction was not verified.
- **Yield trend form.** Linear trends are often adequate. There are plateaus for NW-European wheat, and compound growth is too optimistic (Grassini 2013, above).
  - Schauberger et al. (2018, Sci. Rep.) analyse French yield trends and stagnation over more than a century. [PR; abstract not fetched, bot block] https://hal.inrae.fr/hal-02620950v1
- **Livestock numbers and supply/use balance items.** I found no recent peer-reviewed benchmark of ML versus trend for long-horizon projection of herd sizes or balance items. *Gap.*

### 3.1 Hierarchical and coherent forecasting (relevant to CAPTRD step 2)

- **MinT** (Wickramasuriya, Athanasopoulos & Hyndman 2019, JASA 114(526):804–819) finds the coherent forecasts that minimise total MSE, given the base-forecast error covariance W. It has a closed-form GLS projection. [PR] https://research.monash.edu/en/publications/optimal-forecast-reconciliation-for-hierarchical-and-grouped-time/
  - CAPRI's step 2 has the same structure as MinT-WLS with extra constraints: minimise weighted deviations from priors subject to identities. This is my analogy, not a published equivalence.
  - Variants:
    - OLS: W = I.
    - WLS: W diagonal, e.g. in-sample error variances. This is analogous to CAPRI's variance weights.
    - MinT-shrink.
- **Review:** Athanasopoulos, Hyndman, Kourentzes & Panagiotelis (2024, IJF 40(2):430–456) cover cross-sectional, temporal and cross-temporal reconciliation, plus general linear constraints and probabilistic methods. [PR] https://ideas.repec.org/a/eee/intfor/v40y2024i2p430-456.html
- **General linear constraints**, not just sums (e.g. national accounts and multi-side balances). Girolimetto & Di Fonzo, arXiv 2305.05330, use a zero-constraint form Γx = 0 with real-valued coefficients. This matches market-balance identities better than a pure hierarchy. [PP; journal version not verified] https://ar5iv.labs.arxiv.org/html/2305.05330
  - R package FoReco: https://cran.ma.ic.ac.uk/web/packages/FoReco/index.html
- **Non-negative reconciliation:** Wickramasuriya, Turlach & Hyndman (2020, Stat. Comput. 30:1167–1182). [PR][NF]
- **Implication.** Reconciliation literature shows that the *quality of W*, the base-error covariance, matters as much as the base forecasts. A step-1 alternative should therefore deliver **horizon-specific error variances**, not just point priors. It should also be judged **after** step 2 as well as before.

## 4. Back-testing and validation protocols

- **Rolling or expanding origin.** Tashman (2000, IJF 16(4):437–450, doi:10.1016/S0169-2070(00)00065-0) [PR][NF]; Hyndman & Athanasopoulos, *FPP3*, §5.10 "time series cross-validation" [DOC][NF] https://otexts.com/fpp3/tscv.html
  - k-fold CV is only valid for purely autoregressive models with uncorrelated errors (Bergmeir, Hyndman & Koo 2018, CSDA 120:70–83). [PR][NF] It is not valid for trend models, so CAPTRD needs forward origins.
- **Scale-free errors.**
  - MASE (Hyndman & Koehler 2006, IJF 22(4):679–688) [PR][NF].
  - RMSSE, used in M5.
  - sMAPE as a secondary measure only: it is unstable near zero, which matters for small balance items.
  - Report errors **per horizon** h = 1…15 and in buckets (1–5, 6–10, 11–15), plus **bias** (mean signed error). Bias is critical for baselines.
- **Probabilistic evaluation.** Empirical coverage of 80% and 95% intervals, the interval (Winkler) score, and CRPS or quantile loss (as in fev-bench's SQL). The CAPRI trend gives a variance, so it can be scored on the same footing.
- **Significance testing.** Diebold–Mariano with the Harvey–Leybourne–Newbold small-sample correction for pairs [PR][NF], and MCB or Nemenyi ranks across many series (as used in M4) [NF].
  - My caveat: EU regional series share common shocks such as CAP reforms, prices and weather years. Errors are therefore cross-correlated, and naïve tests overstate significance. Use a block or cluster bootstrap over origin years.
- **Leakage controls.** Use the same data vintage for every method. Fit all hyper-parameters only on data before each origin. Exclude foundation models from the headline comparison unless pre-training data provably excludes the evaluation window (§1.2).
- **Pre-test the pipeline.** Reproduce published M3 or Tourism yearly numbers (e.g. Theta ≈ 16.9 sMAPE on M3 yearly) before trusting results on CAPRI data.

## 5. Open-source Python tooling

Licences and versions were checked on PyPI on 22 Oct 2026, unless marked otherwise.

| Package | Version | Licence | Use for CAPTRD |
|---|---|---|---|
| statsforecast (Nixtla) | 2.1.1 | Apache-2.0 | AutoETS (damped), AutoTheta/DOTM, AutoARIMA, AutoCES, Naive/RWD. Fast, with built-in cross-validation |
| hierarchicalforecast (Nixtla) | 1.5.3 | Apache-2.0 | BottomUp, MinT (ols/wls/shrink), ERM; useful to compare against CAPRI step 2 |
| mlforecast (Nixtla) | 1.1.0 | Apache-2.0 | Global LightGBM/XGB with lag and difference features |
| neuralforecast (Nixtla) | 3.3.0 | Apache-2.0 | N-BEATS, N-HiTS, global DL |
| darts (Unit8) | 0.48.1 | Apache-2.0 | Unified API, back-testing, wrappers for foundation models |
| sktime | 1.2.0 | BSD-3-Clause | Unified API, evaluation and splitters |
| statsmodels | 0.15.0 | BSD-3-Clause | UnobservedComponents (structural local-linear-trend), ETS, SARIMAX; transparent maximum likelihood |
| pymc | 6.3.2 | Apache-2.0 | Hierarchical Bayesian trend with partial pooling across regions |
| orbit-ml (Uber) | 1.1.5.1 | Apache-2.0 | DLT/LGT-type Bayesian ETS (Python counterpart of the LGT idea; equivalence not verified) |
| gluonts | 0.17.0 | Apache-2.0 | Probabilistic DL; evaluation tools |
| autogluon.timeseries | 1.6.3 | Apache-2.0 | Ensembles including Chronos |
| chronos-forecasting | 2.3.2 | Apache-2.0 (code). Chronos-2 weights Apache-2.0 [DOC] | Zero-shot foundation model, exploratory |
| timesfm | 3.0.2 | Apache-2.0 (code). 2.5 weights Apache-2.0 [DOC]; 3.0 weights reportedly non-commercial [BLOG, unverified] | Exploratory |
| uni2ts (Moirai) | 2.0.0 | Apache-2.0 (code). **Weights CC BY-NC 4.0** [DOC] | Avoid for a public tool |
| prophet | 1.5.0 | MIT | Not recommended here: built for sub-daily or daily seasonality (my opinion) |
| lightgbm | 4.7.0 | MIT [NF: PyPI field empty; MIT per repository, not verified this session] | Engine for the global GBM |
| FoReco | n/a (R package) | GPL-3 [NF] | General-linear-constraint reconciliation, reference implementation |

## 6. Implications for CAPTRD-MOD step 1

### 6.1 What the evidence supports

- Simple trend-family methods and their combinations are hard to beat on yearly data. This covers damped trend, Theta/DOTM, Bayesian ETS with global trend, and linear or curved trends.
- ML gains appear only with **pooled (global)** training over very many series, and they are small: a few per cent at h ≤ 6.
- There is **no published evidence at h = 10–15** for short annual series.
- In-season yield ML successes (MARS, CY-Bench) do not apply to 10-year baselines.

### 6.2 Recommended candidate set

Every method produces both a point prior and a horizon-specific variance for step 2.

| # | Candidate | Rationale | Tool |
|---|---|---|---|
| C0 | **CAPRI trend a + b·t^c (WLS)**, the reference | Acceptance anchor | own code |
| B1 | Random walk with drift | Floor benchmark; also the MASE scaling | statsforecast |
| B2 | Linear trend (OLS) | Tests whether c ≠ 1 adds value | statsmodels |
| S1 | ETS, additive damped trend (AutoETS restricted to A,Ad,N) | Strongest classical yearly benchmark; damping counters runaway t^c | statsforecast |
| S2 | Theta / DOTM | Top M3/M4 yearly statistical method | statsforecast |
| S3 | Local linear trend structural model (UnobservedComponents) | DLM result for yields; gives a variance directly | statsmodels |
| S4 | **Combination**: median or mean of C0, S1, S2 (and S3) | Most robust finding in M3/M4. Combining with C0 keeps CAPRI's logic | own code |
| H1 | **Hierarchical Bayesian trend**: CAPRI's functional form, with partial pooling of b and c across NUTS2 within a country and across countries per item; optional damping | Treats the short-series problem without leaving CAPRI's form. **Unbenchmarked; my proposal** | pymc |
| G1 | Global LightGBM on scaled, first-differenced series, with direct multi-horizon targets (one model per h-bucket) and features for item, country, region and lags | Montero-Manso & Hyndman globality argument. Tree models need differenced targets to extrapolate | mlforecast |
| F1 (exploratory only) | Chronos-2 and/or TimesFM-2.5, zero-shot | Apache-2.0 weights. Report separately because of the leakage and auditability issues in §1.2 | chronos-forecasting, timesfm |

Methods **not** recommended:

- Per-series LSTM or transformer fitted from scratch: no supporting evidence for n ≈ 30.
- Random forests on levels: they cannot extrapolate trends.
- Moirai: non-commercial licence.
- Prophet: designed for high-frequency seasonality (my opinion).

**Where I would depart from CAPRI.** These are my own judgements, flagged for your decision.

- (i) **S4 combination including C0.** Combination is the best-supported finding in forecasting competitions. It keeps CAPRI's curve as one component instead of replacing it.
- (ii) **H1 partial pooling.** CAPRI fits each series independently, as far as I know (unverified against the CAPTRD GAMS code in this session). Pooling should stabilise c for short NMS series that start in 2004–2007.
- (iii) **Calibrated step-2 weights.** Derive step-2 weights from **back-cast error variances by horizon** rather than from in-sample residual variance. This mirrors the MinT emphasis on a good W.

### 6.3 Validation protocol

- **Data.** Use the same CSV vintage for every method. Series run 1985 to t_end, with t_end ≈ 2020–2023. NMS series are shorter, so report them separately.
- **Origins (expanding window).** T0 ∈ {2003, 2004, …, t_end − 5}.
  - Require at least 15 observations before an origin. Otherwise use C0's fallback rule for every method alike.
  - Forecast h = 1…min(15, t_end − T0).
  - Horizons above 10 have few origins (e.g. h = 15 only from T0 ≤ 2005–2008). Report the n behind each horizon cell.
- **Two stages.**
  - (a) Step-1 back-cast against actuals.
  - (b) Full pipeline: step 1 feeding the unchanged step 2, against actuals. An alternative is accepted only if it wins at stage (b) as well. Reconciliation can remove or reverse step-1 gains.
- **Metrics.** Use the same metrics at both stages.
  - Primary: MASE (scaled by the in-sample one-step random-walk MAE up to T0), by horizon bucket (1–5, 6–10, 11–15).
  - Secondary: RMSSE, mean signed scaled error (bias), and sMAPE only for strictly positive series.
  - Probabilistic: 80% and 95% coverage, and interval score.
  - Aggregate by item group (yields, areas, herds, balance items), by country or region, and overall. Use a geometric mean of relative MASE against C0.
- **Inference.** Use a block bootstrap over origin years with clusters by item × country, so that common shocks are kept together. Report 95% CIs of relative MASE against C0. Do **not** rely on per-series DM tests alone.
- **Acceptance rule (proposed).** An alternative is switched on for an item group only if all of these hold:
  - (1) The upper CI of relative MASE against C0 is below 1 in the 6–10 and 11–15 buckets at stage (b).
  - (2) Absolute bias is not worse.
  - (3) 80% coverage is within ±10 percentage points of nominal.
  - (4) The result holds when the earliest and latest third of origins are dropped, as a stability check.
- **Sanity checks.**
  - Reproduce M3 yearly Theta ≈ 16.9 sMAPE with the same code path.
  - Run placebo origins.
  - For F1, run a leakage probe: compare origins before and after the model's known pre-training cut-off. If the cut-off is unknown, report F1 as "not admissible".

## 7. Uncertainties and gaps

- The M4 per-frequency numbers here come from the N-BEATS tables, not from the M4 paper itself, which could not be fetched.
- I did not verify whether M4 yearly or FAOSTAT-like data are in the Chronos, TimesFM or Moirai pre-training corpora.
- There is no long-horizon (h > 6) yearly benchmark, and none specific to livestock or balance items.
- The LGT and Girolimetto–Di Fonzo journal venues are not confirmed; I read only arXiv versions.
- The fev-bench and GIFT-Eval findings come from vendor-affiliated authors and are aggregated across frequencies.

## Sources

**Peer-reviewed or accepted**

- Makridakis, Spiliotis, Assimakopoulos (2018), PLoS ONE: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0194889
- Oreshkin et al., N-BEATS (ICLR 2020), with M3/M4/Tourism yearly tables: https://arxiv.org/pdf/1905.10437v4
- Montero-Manso & Hyndman (2021), IJF: https://arxiv.org/pdf/2008.00444 ; https://ideas.repec.org/a/eee/intfor/v37y2021i4p1632-1653.html
- Cerqueira, Torgo, Soares: https://arxiv.org/abs/1909.13316v1
- Ansari et al., Chronos (TMLR 2024): https://arxiv.org/html/2403.07815v3
- Wickramasuriya, Athanasopoulos, Hyndman (2019), JASA: https://research.monash.edu/en/publications/optimal-forecast-reconciliation-for-hierarchical-and-grouped-time/
- Athanasopoulos et al. (2024), IJF review: https://ideas.repec.org/a/eee/intfor/v40y2024i2p430-456.html
- Michel & Makowski (2013), PLoS ONE: https://ideas.repec.org/a/plo/pone00/0078615.html
- Grassini, Eskridge, Cassman (2013), Nat. Commun.: https://ideas.repec.org/a/nat/natcom/v4y2013i1d10.1038_ncomms3918.html
- Paudel et al. (2021), Agric. Syst.: https://ideas.repec.org/a/eee/agisys/v187y2021ics0308521x20308775.html
- Paudel et al. (2022), Field Crops Res.: https://research.wur.nl/en/publications/machine-learning-for-regional-crop-yield-forecasting-in-europe/
- Kallenberg et al. (2026), CY-Bench, ESSD: https://essd.copernicus.org/articles/18/3997/2026/
- Schauberger et al. (2018), Sci. Rep. (not fetched): https://hal.inrae.fr/hal-02620950v1

**Preprints and workshop papers**

- Smyl et al., LGT: https://arxiv.org/html/2309.13950v3
- GIFT-Eval: https://arxiv.org/html/2410.10393v2
- fev-bench: https://arxiv.org/html/2509.26468v2
- Girolimetto & Di Fonzo: https://ar5iv.labs.arxiv.org/html/2305.05330
- Monash archive (not fetched): https://arxiv.org/abs/2105.06643

**Documentation and model cards**

- Chronos-2: https://huggingface.co/amazon/chronos-2
- TimesFM 2.5: https://huggingface.co/google/timesfm-2.5-200m-pytorch
- Moirai 2.0: https://huggingface.co/Salesforce/moirai-2.0-R-small
- Moirai 1.1: https://huggingface.co/Salesforce/moirai-1.1-R-base
- Lag-Llama: https://huggingface.co/time-series-foundation-models/Lag-Llama
- JRC ASAP yield methodology: https://agricultural-production-hotspots.ec.europa.eu/files/yield_forecast-methodology_summary_v1.0.pdf
- Aglink-Cosimo (JRC model inventory): https://web.jrc.ec.europa.eu/policy-model-inventory/explore/models/model-aglink-cosimo-annex4
- FoReco: https://cran.ma.ic.ac.uk/web/packages/FoReco/index.html
- FPP3: https://otexts.com/fpp3/tscv.html
- PyPI metadata: https://pypi.org/project/statsforecast/ (and the equivalent pages for the other packages)

**Blogs and secondary sources**

- Smyl, Uber blog on M4: https://www.uber.com/blog/m4-forecasting-competition
- Wikipedia, Makridakis Competitions: https://en.wikipedia.org/wiki/Makridakis_Competitions
- Bora & Katchova, OSU blog: https://u.osu.edu/aede/?p=249
- beri.net licence article (unverified claims): https://www.beri.net/article/timesfm-vs-chronos-vs-moirai-time-series-foundation-model-licence-bigquery-sagemaker-cost-2026

**Cited from prior knowledge, not fetched [NF]**

- Makridakis et al. (2020), IJF 36(1):54–74, doi:10.1016/j.ijforecast.2019.04.014
- Makridakis & Hibon (2000), IJF 16(4)
- Hyndman & Billah (2003), IJF 19(2)
- Tashman (2000), IJF 16(4)
- Hyndman & Koehler (2006), IJF 22(4)
- Bergmeir, Hyndman, Koo (2018), CSDA 120
- Wickramasuriya, Turlach, Hyndman (2020), Stat. Comput. 30
