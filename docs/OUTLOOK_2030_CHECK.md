# The 2030 baseline against the EU agricultural outlook 2020-2030

Status: revised 20 October 2026 against the code. The method and data are current; the table and the numbers in
"Findings" are historical: they come from the 2030 baseline of a Farm-to-Fork run of 15 October 2026 (conic supply
form), before the NLP form became the default. They have not been re-run with the current default.

An independent check of the 2030 baseline: DG AGRI's medium-term outlook (EC 2020, *EU agricultural outlook for
markets, income and environment 2020-2030*, doi:10.2762/252413), Annex tables 8.8-8.44, next to CAPRI star 3.0's own
2030 reference (the baseline capri-mod is calibrated to; docs/BASELINE_REPRODUCTION.md).

- Data: `capri_data/validation/eu_outlook_2020_2030.csv` (`tools/build/build_eu_outlook_2030.py`; 435 rows, years
  2016-2030).
- Table: `python tools/check/compare_outlook_2030.py RUN.pkl [OUT.csv]`, with RUN.pkl a run saved by
  `tools/run/run_f2f_2030.py`.

## How to read it

Three columns per item: the outlook's 2030, CAPRI's 2030 reference, capri-mod's 2030 baseline. Where capri-mod
follows CAPRI and both differ from the outlook, the difference is between CAPRI's reference and the outlook (two
baselines of different vintage and model), not capri-mod's: in the table below rapeseed area +31% and production
+40%, pulses area −37%, common wheat production +10%, cereal net exports, eggs +11%. Where capri-mod departs from
CAPRI the difference is the model's to explain.

Trade is compared as net exports: CAPRI's IMPT / EXPT include intra-EU trade, the outlook's are extra-EU.

## Findings (15 October 2026)

**KNOWN_ISSUES K12: 2030 livestock output per head had stayed at 2017** (found with this check, fixed). Dairy cows gave
2017 milk: 6.97 t per cow against CAPRI's 7.79 and the outlook's 8.30; EU cow milk 139.6 Mt against 154.3 and 159.6.
CAPRI's 2030 reference reports the livestock activities only as intensity variants, so the projection found no yield
factor. After the fix (yield factors from CAPRI's components): 157.2 Mt (CAPRI +1.9%, outlook −1.5%); poultry, eggs,
suckler cows and sheep meat closer to CAPRI as well.

Left after the fix (capri-mod against CAPRI's reference, in the table below):

- dairy products (cheese −3%, butter 0%, SMP +1%) did not move with the 10% more raw milk the fix brought: the dairy block keeps
  CAPRI's 2030 product balances (K13);
- oilseed oil −25% against CAPRI's OILP: CAPRI's aggregate includes other oils; rape, sun and soya oil together are
  17.3 Mt against 18.3 (−5%);
- durum wheat production +3.6%, sheep and goat meat +4.6%, olive oil +7%.

## Table (2030 baseline of the Farm-to-Fork run of 15 October 2026)

```
item                                       unit    outlook  CAPRI ref  capri-mod  mod/outl CAPRI/outl
common wheat area                       1000 ha      21000      21476      21537     +2.6%      +2.3%
durum wheat area                        1000 ha       2000       2047       2125     +6.3%      +2.3%
barley area                             1000 ha      10400      10121      10289     -1.1%      -2.7%
maize area                              1000 ha       8800       8181       8164     -7.2%      -7.0%
rye area                                1000 ha       2100       2214       2239     +6.6%      +5.4%  CAPRI RYEM = rye and meslin
rapeseed area                           1000 ha       5300       6976       6968    +31.5%     +31.6%
sunflower area                          1000 ha       4300       4351       4330     +0.7%      +1.2%
soya area                               1000 ha       1000        996       1009     +0.9%      -0.4%
sugar beet area                         1000 ha       1400       1412       1428     +2.0%      +0.8%
pulses area                             1000 ha       2900       1756       1815    -37.4%     -39.5%
rice area                               1000 ha        400        356        356    -10.9%     -11.0%
common wheat production                  1000 t     120900     133529     133724    +10.6%     +10.4%
durum wheat production                   1000 t       7100       7889       8174    +15.1%     +11.1%
barley production                        1000 t      51700      53152      54023     +4.5%      +2.8%
maize production                         1000 t      68000      66632      66532     -2.2%      -2.0%
cereals production                       1000 t     278100     299943     299464     +7.7%      +7.9%  outlook: excl. rice
cereals net exports                      1000 t      17700      29287      29289                       capri-mod: wheat incl. durum, rye/oats in OCER
rapeseed production                      1000 t      16000      22440      22442    +40.3%     +40.2%
sunflower seed production                1000 t      10600      10659      10626     +0.2%      +0.6%
soya bean production                     1000 t       3500       2933       2978    -14.9%     -16.2%
oilseed meal production                  1000 t      29300      32311      29615     +1.1%     +10.3%
oilseed oil production                   1000 t      15800      23251      17337     +9.7%     +47.2%
sugar beet production                    1000 t     108000     105931     107153     -0.8%      -1.9%
sugar production                         1000 t      16200      16553      16751     +3.4%      +2.2%
dairy cows                           1000 heads      19200      19801      20019     +4.3%      +3.1%
suckler cows                         1000 heads       9900      10649      10759     +8.7%      +7.6%
cow milk production                      1000 t     159600     154291     157239     -1.5%      -3.3%  milk of dairy cows
cheese production                        1000 t      11253      10838      10503     -6.7%      -3.7%
butter production                        1000 t       2476       2271       2282     -7.8%      -8.3%
SMP production                           1000 t       1872       1758       1774     -5.2%      -6.1%
WMP production                           1000 t        697        489        492    -29.4%     -29.8%  CAPRI WMIO includes other milk powders
beef production                      1000 t cwe       6612       6071       6265     -5.2%      -8.2%
pigmeat production                   1000 t cwe      21995      21346      21393     -2.7%      -2.9%
poultry meat production              1000 t cwe      14076      13676      13852     -1.6%      -2.8%
sheep and goat meat production       1000 t cwe        629        630        659     +4.7%      +0.1%
egg production                           1000 t       6774       7493       7643    +12.8%     +10.6%
pigmeat net exports                  1000 t cwe       3719       3818       3800
poultry net exports                  1000 t cwe       1606       2808       2798
beef net exports                     1000 t cwe        256        623        618
olive oil production                     1000 t       2434       2328       2495     +2.5%      -4.4%
wine production                1000 t (= 10 hl)      16000      15756      15858     -0.9%      -1.5%  outlook in million hl
apple production                         1000 t      11815      11997      12420     +5.1%      +1.5%
tomato production                        1000 t      16861      17948      17758     +5.3%      +6.4%
```

Since this run the market gained markets of their own for rye, oats, table grapes, tobacco, table olives, textile
crops and palm and other vegetable oils (17-18 October 2026), and the supply models moved to the NLP form. A current
run of `tools/check/compare_outlook_2030.py` may therefore differ from this table beyond the model's results; read its
'note' column.
