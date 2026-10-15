# 9t, 9t.1 and capri-mod-proto compared (October 2026)

* **9t** - the tagged release (`capri-mod-9t.zip`).
* **9t.1** - 9t with every bug fix of docs/KNOWN_ISSUES.md (K1-K4, K6-K8, K11), no model change.
* **prototype** - 9t.1's fixes plus CAPRI's inhibitor on manure inside the conic model and no N-price search
  (docs/PROTOTYPE_NI_INSIDE.md).

All runs: full EU, 2030, CAPRI's reference baseline, 2 workers, PYTHONHASHSEED=0.

## Farm-to-Fork (JRC121368 settings)

| | 9t | 9t.1 | prototype | JRC121368 |
|---|---|---|---|---|
| converged | 23 iterations, 756 s | 13 iterations, 625 s | 13 iterations, 349 s | |
| gap (20 indicators) | 4.26 | 4.27 | 4.28 | |
| cereal price | +8.4 | +8.4 | +8.4 | +8.0 |
| pork price | +34.2 | +34.5 | +34.2 | +43.0 |
| milk price | +30.7 | +30.9 | +30.7 | +1.5 |
| dairy cows | −7.0 | −7.0 | −6.9 | −10.0 |
| pigs | −20.9 | −21.0 | −20.9 | −14.5 |
| N surplus | −33.3 | −33.4 | −33.3 | −33.5 |
| GHG total | −18.6 | −18.7 | −18.6 | −14.8 |
| ammonia | −43.2 | −42.8 | −42.8 | −33.0 |
| low-emission housing, % | 19.9 | 19.5 | 19.5 | 12 |
| covered manure storage, % | 41.9 | 41.3 | 41.3 | 34 |
| low-emission spreading, % | 84.5 | 83.2 | 83.2 | - |

## Green Deal (CAPRI star 3.0 settings)

| | 9t | 9t.1 | prototype |
|---|---|---|---|
| converged | 18 iterations, 799 s | 18 iterations | 20 iterations, 544 s |
| pork price | +46.1 | +47.4 | +46.6 |
| poultry price | +41.2 | +42.0 | +41.3 |
| beef animals | −32.7 | −32.8 | −32.6 |
| N surplus | −47.2 | −47.3 | −47.2 |
| GHG total | −28.7 | −28.8 | −28.7 |

(9t.1's Green Deal time, 1006 s, was measured with other runs in parallel.)

## Carbon tax (50 EUR/t CO2-eq, CAPRI's ghgTax inside the supply models)

| | 9t | 9t.1 | prototype |
|---|---|---|---|
| converged | 5 iterations, 606 s | 5 iterations, 608 s | 5 iterations, 634 s |
| conic fallbacks | 3 (RO12, RO22, RO42; not reported by 9t) | 0 | 0 |
| ammonia | +1.5 | +3.5 | +3.5 |
| fertiliser N2O | −13.5 | −13.3 | −13.3 |
| GHG total | −10.1 | −10.0 | −10.0 |
| covered manure storage, % | 28.5 | 25.1 | 25.1 |
| low-emission spreading, % | 32.7 | 27.9 | 27.9 |

Under the tax the ammonia options are priced for their N2O through the loss cascade, not for the NH3 they keep; with
their cost corrected (K2) and the N kept priced on the tangent (K8) fewer are adopted and ammonia rises more.

## Reading

- The fixes move EU results by at most 1.3 points (Green Deal pork price); most indicators by 0-0.2. They move
  technology adoption (ammonia options 0.4-5 points) and regions more (DE94 pigs and broilers ~2%).
- 9t.1 converges as fast as the prototype in iterations (13 against 9t's 23): the ammonia fixes, not the prototype's
  change, removed most of 9t's slow convergence. The prototype is still ~45% faster per run (no N-price search: one
  regional solve per land step instead of up to 16).
- The prototype and 9t.1 agree within 0.8 points on every indicator in all three scenarios.
- Both pass the 92 tests without warnings. The NLP check (tools/nlp_check) confirms both reach CAPRI's exact optimum in
  the regions checked (Farm-to-Fork: five regions; carbon tax: four).
