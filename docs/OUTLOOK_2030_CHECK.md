# The 2030 baseline against the EU agricultural outlook 2020-2030

*An independent check of the 2030 baseline: DG AGRI's medium-term outlook (EC 2020, *EU agricultural outlook for
markets, income and environment 2020-2030*, doi:10.2762/252413), Annex tables 8.8-8.44, next to CAPRI star 3.0's own
2030 reference (the baseline CAPRI-mod is calibrated to). Data: `capri_data/validation/eu_outlook_2020_2030.csv`
(`tools/build_eu_outlook_2030.py`, 435 rows, every year 2016-2030); table: `tools/compare_outlook_2030.py RUN.pkl`.*

## How to read it

Three columns per item: the outlook's 2030, CAPRI's 2030 reference, CAPRI-mod's 2030 baseline. Where CAPRI-mod
follows CAPRI and both differ from the outlook, the difference is between CAPRI's reference and the outlook (two
baselines of different vintage and model), not CAPRI-mod's: rapeseed area +31% and production +40%, pulses area -37%,
common wheat +10%, cereal net exports, eggs +11%. Where CAPRI-mod departs from CAPRI it is the model's to explain.

## What it found

**K12 (docs/KNOWN_ISSUES.md): 2030 livestock output per head stayed at 2017.** Since Sprint 9p (13 October) dairy
cows gave 2017 milk - 6.97 t per cow against CAPRI's 7.79 and the outlook's 8.30; EU cow milk 139.6 Mt against
154.3 and 159.6. CAPRI's 2030 reference reports the model's livestock only as intensity variants, so the projection
found no yield factor. Fixed: CAPRI-mod now 157.2 Mt (CAPRI +1.9%, outlook -1.5%); poultry, eggs, suckler cows and
sheep meat closer to CAPRI as well.

Left after the fix (CAPRI-mod against CAPRI's reference):
- dairy products (cheese -3%, butter 0%, SMP +1%) did not move with 10% more raw milk: the dairy block keeps CAPRI's
  2030 product balances (K13);
- oilseed oil -25% against CAPRI's OILP (CAPRI's aggregate includes other oils; rape, sun and soya oil together -5%: 17.3 Mt against 18.3);
- durum wheat production +3.6%, sheep and goat meat +4.6%, olive oil +7%.

## Table (Farm-to-Fork run of the prototype, its 2030 baseline; 15 October 2026)

```
item                                       unit    outlook  CAPRI ref  CAPRI-mod  mod/outl CAPRI/outl
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
cereals net exports                      1000 t      17700      29287      29289                       CAPRI-mod: wheat incl. durum, rye/oats in OCER
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

Trade is compared as net exports: CAPRI's IMPT / EXPT include intra-EU trade, the outlook's are extra-EU.
