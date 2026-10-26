# Feed rations: data, calibration and use

Status: revised 20 October 2026 against the code. The build history (an EU ration chosen outside the supply models,
its wiring and convergence diagnoses, response tests of that stage) was removed: since K42 the ration is chosen only
inside the regional supply models. Rations are always on (the `use_ration` switch was removed on 26 October 2026: CAPRI always has the feeding block).

## How CAPRI does it

Outside the EU, feed demand is a market function with feed-price elasticities (`p_ElasFeed`); in capri-mod
`feed_demand_nonEU.json` (`tools/build/build_feed_demand_nonEU.py`, CAPRI's 2030 calibration, K43).

In the EU there is no feed-demand elasticity: the ration is chosen inside each regional supply model
(`supply/supply_model.gms`). For every region and animal activity the feed input coefficients `v_feedInpCoeff(feed)`
are variables, with the feeds' cost and CAPRI's feed PMP term (QUADRF_) in the objective, and FEDUSE_ (feed use =
per-head feed x herd) linking them to the fodder balances and the feed markets. In star 3.0's simulation (feed version
`_pw`) the only requirement constraints are REQSE_, energy and crude protein, as equalities;
REQSN_, MAXSHR_ and MINSHR_ (dry matter and feed shares) are left out of the model
(supply_model_e_list_linear.gms:48-51). Feed demand for the EU market is the sum over regions and animals of heads x
chosen coefficients, so it responds to relative feed prices while the requirements tie the total to herd sizes.

CAPRI's requirements change with mitigation options (low-N feeding on protein, breeding for feed efficiency, milk-yield
genetics, nitrate replacing protein, linseed supplying energy and protein); in capri-mod these are columns of the
regional model that act on the requirement rows (`docs/MITIGATION_IN_SUPPLY.md`).

## Data (CAPRI 2017 regional results, `res_17*`)

Built by `tools/build/build_feed_ration.py` (`capri_data/2017/feed/feed_ration_2017.json`): per region and CAPRI animal
activity, the base ration per head per year (kg of fresh feed by feed group: grass `FGRA`, fodder maize `FMAI`, other
fodder `FOFA`, roots `FROO`, straw `FSTR`, cereals `FCER`, protein-rich `FPRO`, energy-rich `FENE`, milk feeds `FMIL`,
other `FOTH`, ...), the requirements per head per day (energy `ENNE`, crude protein `CRPR`, dry matter `DRMN`/`DRMX`)
and `DAYS`; per member state (and region where present) the nutrient contents per kg of fresh feed (`ENNE`, `CRPR`,
dry matter `DRMA`) and unit values (`UVAG`). The model's aggregated activities (dairy = low + high yield, pigs, ...)
take summed requirements (REGISTERED aggregation).

Identity check of the data (made when the data were built, over 4,518 region x animal cases): ration x contents /
days = requirement to a median of 0.00% for energy and protein; fattening bulls and heifers carry a surplus of about
2%.

Base intake can lie above CAPRI's dry-matter maximum. CAPRI does not impose raw bounds: at calibration it trims the
requirements to the data (`p_trimFeed` turns `p_animReq` into `v_animReq` in REQSN_/REQSE_), so the observed base
ration is feasible by construction. capri-mod does the same: each requirement is set to include the base ration
(in the NLP form the requirement equals the base ration's supply). The dry-matter maximum also bounds each single feed
at 10 x (`set_supply_bounds.gms`).

## Feed PMP (`pmp_terms/define_const_pmp_param.gms`, Part I)

Each feed coefficient carries a cost x (CNST + 1/2 SLOP x):

- SLOP: CAPRI's own calibrated slope where `pmppar_17XX.gdx` has one (`p_pmpFeedInpCoeff`, aggregated to the model's
  animals), else CAPRI's formula, SLOP = (1 / |eps_feed|) x max(price, 10% of the cereal price) / x_ref, with x_ref
  the base feeding (CAPRI: at least 10% of the sector's dry-matter share; identical for feeds with at least 10% of dry
  matter; REGISTERED). CAPRI adds these terms to the profit it maximises: that reading explains marginal feed costs by
  nutrient prices to a median 4.6% residual, the opposite reading 54.5% (check made when the slopes were received).
- Assumed own-price feed elasticities (`supply/pmp_elas.gms`): cereals and fodder -10, protein-rich -5, other -1,
  energy-rich, milk feeds and straw -0.5 (the in-code comment says 0.1; the values are what count).
- CNST from the first-order conditions at base, so the observed base ration is optimal at base prices.
- Feeds with no assumed elasticity in CAPRI (FRMI, FPRI, FENI) have no PMP term; capri-mod holds them at their base
  quantity per head.

## Use in the model

`capri_mod/feed/ration.py` builds one `Ration` per region and animal (feeds, base ration, contents, trimmed
requirements, share limits, PMP terms). These are the data of the feeding block inside the regional models, and the
ration is chosen only there (as CAPRI):

- NLP form (default): REQSE_ equalities for energy and protein, FEDUSE_ bilinear, QUADRF_ per head, feed bounds; no
  dry-matter or share rows, as CAPRI's `_pw` simulation. The CNST are recalibrated so that the base ration is optimal
  under REQSE_ alone (`capri_regional_nlp.calibrate_feed_terms`), and the regional calibration makes the whole base a
  first-order point.
- Conic form (removed 26 October 2026): requirements as inequalities, plus the dry-matter and share rows below, with
  total feed as the variable.

Feed prices: tradable bulks (FCER, FPRO, FENE, FOTH, FMIL) at the member state's bulk price index (CAPRI's
`feedBlkPrice_`, `docs/FEED_MARKETS.md`); home-grown fodder is not priced but valued through its balance
(`docs/FODDER_BALANCE.md`).

The older path without feeding inside (an EU ration chosen outside the supply models at current feed prices, with the
share rules) was removed with the conic form on 26 October 2026.

## Feed-share rules (`feed/req_or_man_fnc.gms`)

On a dry-matter basis, relative to the current total intake (`share_rules` in `ration.py`); used in the conic form,
in the outside ration and in the rations' calibration, not in the NLP form:

- fixed rules: ruminants protein <= 0.3, energy-rich <= 0.1; dairy cows, fattening bulls, calves cereals >= 0.2,
  protein >= 0.1; heifers cereals and protein >= 0.05; suckler cows cereals >= 0.05; non-ruminants cereals >= 0.6,
  protein <= 0.2 (sows 0.3), energy-rich 0.05-0.15, no fodder; other feeds >= 0.005 (0.001 sheep, suckler cows);
- data-driven rules: fibre-rich minimums from the region's fodder-energy shares (CAPRI's factors; calves and sheep and
  goats take the mean factor of their two CAPRI activities, REGISTERED), straw 0.01-0.05 for ruminants where straw is
  produced, sheep's non-fodder feeds <= 0.2, calves' milk feeds and COMF, and the member state's maximum share of other
  feeds;
- bounds the base violates are widened to the base share (relative tolerance 1e-6); the dry-matter bounds likewise.

Requirements per year are CAPRI's per-day requirements x CAPRI's `DAYS` (`tools/build/build_feed_ration.py`).

REGISTERED: nutrient shadow prices at base fitted by non-negative least squares to feed prices (standing in for the
duals of CAPRI's calibration step).
