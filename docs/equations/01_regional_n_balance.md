# The regional nitrogen balance: CAPRI's equations and CAPRI-MOD

Draft, 18 November 2026; the line numbers updated on 19 November 2026 (CAPRI star 3.0's supply_model.gms, 5,631
lines; CAPRI-MOD's code after the refactor's block N4, d1fd725). Page 1 of the equation book (docs/equations/README.md): each of CAPRI's equations as written
in its GAMS code, the same equation in mathematical notation, where CAPRI-MOD builds it, how (status), and its value at
the 2030 base in both models.

Values: CAPRI-MOD's full-EU Green Deal run runs/full_gd_k179.pkl (code e7be740, K178 and K179; K180 and K181, later the
same day, leave the 2030 base unchanged outside Slovakia); CAPRI's 2030 reference (res_2_1730greendeal_refdefaulta)
and its Green Deal run (res_2_1730greendeal_lnds8_org18_pest20_mine13crp_surp30_diet00_oth00defaultA), dataOut.

The GAMS text is quoted from CAPRI star 3.0 (`supply/supply_model.gms`, `pol_input/greendeal/surptot.gms`) for
comparison; the equations and their design are the work of the CAPRI developers (CAPRI Network,
www.capri-model.org). Conditional blocks (`$iftheni ... $endif`) are shown where they are active in the 2030 Green Deal
runs (`ghgAbatement` on, `ManureTradeNew` on, `PEST_DISAGG` off).

Notation: $r$ a supply region; $L_r = \sum_{t \in \text{landTypesNoSlak}} x_{r,t}$ its land (1000 ha); $x_{r,a}$ the level
of activity $a$ (1000 ha or 1000 head); $d_{r,a,i}$ CAPRI's coefficient `%data%(r,a,i,"Y")`; $\tau_{r,a,i}$ the
technology factor `p_technFact`; every balance item is in kg N per ha of $L_r$, every flow in 1000 t
($\text{kg/ha} \times 1000\ \text{ha} \times 10^{-3} = 1000\ \text{t}$).

---

## 1. e_SURTOTHa: the gross N surplus per hectare

GAMS (supply_model.gms l. 1463-1475):

```gams
   e_SURTOTHa(runr,fnut)  ..
       v_nutSurTot(RUNR,FNUT) =E= 0
            + v_minfert(runr,fnut)
            + v_excret(runr,fnut)
            - v_manureNetExportHa(runr,fnut)
            + v_biofix(runr,fnut)
            + v_atmosd(runr,fnut)
            + v_Cresid(runr,fnut)
            - v_expprd(runr,fnut)
;
```

$$
\text{SURTOT}_r = \text{MINFERT}_r + \text{EXCRET}_r - \text{MTRADE}_r + \text{BIOFIX}_r + \text{ATMOSD}_r + \text{CRESID}_r - \text{EXPPRD}_r
$$

The surplus is the gross balance: all inputs (mineral fertiliser, manure excreted net of its net export, biological
fixation, deposition, crop residues) less the N removed with the crops, per hectare of the region's land.

CAPRI-MOD: one row of the regional NLP, `N_balance`, written as the levels times their N coefficients (the sum of the
terms below, substituted) against the target times the current land:
- the activities' coefficients: `capri_mod/environmental/nitrogen.py` (`unit_nitrogen_balance`, l. 300), the region's
  constant part (`nitrogen_balance_constants`, l. 320);
- the row: `capri_mod/supply/supply_module.py` (`_build_constraints`, the `N_balance` row, l. 1271-1368); per
  hectare of current land, CAPRI's denominator $L_r$ = ARAC + GRAS + FRUN: `capri_mod/supply/land.py` l. 186-208;
- with the fertilisation block, the mineral part replaced by the purchases $v\_netPutQuant$ (e_MINFERT below):
  `capri_mod/supply/capri_regional_nlp.py` (`_fert_block`, l. 819-834) with
  `capri_mod/supply/equations/supply_model/n_surplus.py` (`SURTOT_REST_`).

Status: ported in another form (one row with the items substituted, rather than one variable and equation per item;
the same relation). docs/SUPPLY_MODEL_MAP.md l. 91, 94.

Values at the 2030 base (kt N; CAPRI-MOD: the full-EU Green Deal run of 18 November 2026, its baseline; CAPRI: its
2030 reference, SURTOT):

| | CAPRI-MOD | CAPRI |
|---|---:|---:|
| EU | 10,883 | 11,059 |
| FR52 | 297.4 | 299.6 |
| DE21 | 55.1 | 56.8 |
| ES41 | 327.7 | 341.7 |
| ES42 | 179.9 | 187.1 |
| ES51 | 134.8 | 135.8 |
| ES62 | 24.4 | 24.8 |

---

## 2. e_EXCRET and ManureNPK_: excretion

GAMS (supply_model.gms l. 1305-1317):

```gams
   e_EXCRET(Runr,FNUT)  ..
         (v_excret(runr,FNUT) *sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001 )
         =e=
     v_ManureNPK(RUNR,FNUT)
    + (v_manureNetExportHa(runr,fnut) *sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001)
    + (v_gasrunani(runr,fnut) *sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001);
```

$$
\text{EXCRET}_r\,L_r\,10^{-3} = \text{ManureNPK}_r + \left(\text{MTRADE}_r + \text{GASRUNANI}_r\right) L_r\,10^{-3}
$$

with the manure net of losses (ManureNPK_ and manExportOrAppl_, l. 927-970: manure applied plus net exports) and the
losses (e_GASRUNANI, l. 1322-1343) both built on $\sum_{a} x_{r,a}\, d_{r,a,\text{MANN}}\,(1+\tau_{r,a,\text{MANN}})$
times one minus the loss share $\ell_{r,a}$ (`v_emiLoss` GasRunTot) or the share itself, and the mitigation options'
factors $\prod_o (1 + s_{r,a,o}\, e_{r,a,o})$ (low-N feeding, breeding). So gross excretion is

$$
\text{EXCRET}_r\,L_r\,10^{-3} = \sum_{a \in \text{MAACT}} x_{r,a}\, d_{r,a,\text{MANN}}\,(1+\tau_{r,a,\text{MANN}}) \prod_o (1 + s_{r,a,o}\,e_{r,a,o})\; 10^{-3}
$$

$d_{r,a,\text{MANN}}$, the manure N per head, is computed by CAPRI from the simulation year's rations before it solves
(capmod.gms l. 1090, `feed/req_or_man_fnc.gms` 'man').

CAPRI-MOD: the herd's coefficient in the row, manure N per model head of the year: data["livestock_manure_n_coef"]
(2030: CAPRI's 2030 coefficients, `tools/build/build_livestock_manure_2030.py`, KNOWN_ISSUES K179), read by
`capri_mod/environmental/ghg.py` (`_n_excretion`); the options' factors on the herd's coefficient
(`capri_mod/supply/livestock.py`, `_genetics_columns`: d_mann_rel); the losses and the manure applied: the N cascade
(`capri_mod/supply/equations/supply_model/n_flow.py`, docs/dev/N_CASCADE_SPEC.md) and the fertilisation block
(ManureNPK_: `capri_mod/supply/equations/supply_model/nutrients.py`, `ManureNPK_trade`, `ManureNPK_ammKept`).

Status: ported (per model head; K179 since 18 November 2026; the heads of bulls and heifers CAPRI's full herds, K180).

Value at the 2030 base: CAPRI's EXCRET in every member state (EU 8,985.6 kt N in both; FR52 393.4).

---

## 3. e_MINFERT and e_MTRADEHa: mineral fertiliser and net manure exports

GAMS (supply_model.gms l. 1287-1302; the pool market's terms are inside `$iftheni.ManureTradeNew`, on in these runs):

```gams
   e_MINFERT(runr,fnut)  ..
         v_minfert(runr,fnut) *sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001 =e= - v_netPutQuant(runr,fnut)
 ;
   e_MTRADEHa(runr,fnut)  ..
       v_manureNetExportHa(runr,fnut) *sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001 =e= 0
        + SUM( FOUT_T_N(FOUT,FNUT), v_manureExports(runr,fout) - v_manureImports(runr,fout))
```

$$
\text{MINFERT}_r\,L_r\,10^{-3} = -\,v^{\text{netPut}}_{r,\text{NITF}}, \qquad
\text{MTRADE}_r\,L_r\,10^{-3} = E^{\text{man}}_{r} - I^{\text{man}}_{r}
$$

(the purchases enter CAPRI's netput with a negative sign; the manure pool market's exports less imports).

CAPRI-MOD: the purchases of the fertilisation block (`capri_mod/supply/capri_regional_nlp.py`, the NUTNED_ and
fertDistMine_ block, `_fert_block`; the row's mineral part replaced by them, l. 819-834); the manure trade: the pool market
(docs/MANURE_MARKET.md) with the base trade a level of the region (KNOWN_ISSUES K167, K176).

Status: ported.

Value at the 2030 base: mineral N is CAPRI's by calibration (EU 9,463 against 9,468 kt; FR52 81.1, ES41 193.7 in both).

---

## 4. e_BIOFIX, e_ATMOSD, e_CRESID, e_EXPPRD: the crops' terms

GAMS (supply_model.gms l. 1381-1461, the 2030 Green Deal blocks):

```gams
   e_ATMOSD(runr,FNUT)  ..
         v_atmosd(runr,FNUT) * sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001 =e= 0
    + SUM( FOUT_T_N(FOUT,FNUT),
       SUM( (MCACT,A) $ p_technFact(RUNR,MCACT,"LEVL",A), v_actLevl(RUNR,MCACT,A) * p_nitrBalance(RUNR,"AtmDep")))
         * 0.001;

   e_EXPPRD(runr,FNUT)  ..
         v_expprd(runr,fnut) * sum(landTypesNoSlak,v_actLevl(RUNR,landTypesNoSlak,"T"))*.001 =e= 0
       + SUM( (MCACT,A) $ p_technFact(RUNR,MCACT,"LEVL",A), v_actLevl(RUNR,MCACT,A)
                  * %data%(RUNR,MCACT,FNUT,"Y") * (p_technFact(RUNR,MCACT,FNUT,A)+1.)
             * v_yldMit(RUNR,MCACT)
            ) * 0.001 ;
```

(e_CRESID and e_BIOFIX: l. 1393-1414 and l. 1438-1461.)

$$
\text{ATMOSD}_r\,L_r\,10^{-3} = \sum_{c,A} x_{r,c,A}\,\delta_r\,10^{-3}, \qquad
\text{EXPPRD}_r\,L_r\,10^{-3} = \sum_{c,A} x_{r,c,A}\, d_{r,c,\text{NITF}}\,(1+\tau_{r,c,\text{NITF},A})\, y^{\text{mit}}_{r,c}\,10^{-3}
$$

$$
(\text{CRESID}_r + \text{ATMOSD}_r)\,L_r\,10^{-3} = \sum_{c,A} x_{r,c,A}\left[d_{r,c,\text{MANN}} + \left(d_{r,c,\text{MANN}} - \delta_r - \mu_r\right)(y^{\text{mit}}_{r,c} - 1)\right](1+\tau_{r,c,\text{MANN},A})\,10^{-3}
$$

$$
\text{BIOFIX}_r\,L_r\,10^{-3} = \beta^{\text{catch}}_r\,x_{r,\text{CATC}} + \sum_{c,A} x_{r,c,A}\, d_{r,c,\text{NITF}}\,(1+\tau_{r,c,\text{NITF},A})\, y^{\text{mit}}_{r,c}\, \phi_{r,c}\,(1 + \lambda_{r,c})\,10^{-3}
$$

with $\delta_r$ the deposition and $\mu_r$ the mineralisation per ha (`p_nitrBalance`), $y^{\text{mit}}$ the yield factor
of the mitigation options (`v_yldMit`), $\phi$ the fixation share (`p_nitrFact` BioFix), $\lambda$ the legume-share
option (OFAR only), $\beta^{\text{catch}}$ the catch crops' fixation.

CAPRI-MOD: per crop in the row's coefficients (`capri_mod/environmental/nitrogen.py`; removal and residues follow the
yield, as CAPRI's $y^{\text{mit}}$ and the need-yield rule, `capri_mod/fert/npk.need_yield_factor`); the catch crops'
fixation in the row (`capri_regional_nlp.py`, `catc_n`, the last argument of `SURTOT_REST_`).

Values at the 2030 base (kt N, CAPRI-MOD / CAPRI): fixation EU 1,654 / 1,654; deposition 1,829 / 1,833; removal
20,361 / 20,086 (FR52 295.4 / 291.5, ES41 388.9 / 366.1: the removal is to be checked item by item where it is 4-6%
above CAPRI's).

Status: ported in another form (the items as coefficients of the levels in one row). To check line by line before the
book is final: the residue term's mitigation part (CRESID with $y^{\text{mit}}$) and the legume-share factor
$\lambda$ (LegSh is deferred: KNOWN_ISSUES, the decision of 9 November 2026).

The same residues, $d_{r,c,\text{MANN}}(1+\tau_{r,c,\text{MANN},A})$, are also what the crops' nutrient need balance
distributes (fertDistCres_, l. 1041-1080): a page of its own (planned); there the technology factor is CAPRI's since
KNOWN_ISSUES K181 (18 November 2026).

---

## 5. SURTOT_REST_ and surptot.gms: the Green Deal's surplus cap

GAMS (supply_model.gms l. 1867-1871; pol_input/greendeal/surptot.gms l. 25-56):

```gams
    SURTOT_REST_(RUNR) $ (p_envConst(RUNR,"all","all","SURTOT") or %data%(runr,"SURTOT","MAXS","Y"))..
    v_nutSurTot(RUNR,"NITF") =L= ( p_envConst(RUNR,"all","all","SURTOT")
                                 + %data%(runr,"SURTOT","MAXS","Y") $ (not p_envConst(RUNR,"all","all","SURTOT"))) *1000;

  data(srnuts2,"SURTOT","MAXS","Y") $ (  SUM(R_RAGG(rall1,"EU27yr19"), R_RAGG(srnuts2,rall1))
                                        $ (p_baselineDataout(srnuts2,"perHa","SURTOT","NITF","%simy%") gt 0))
   = max(0, ...
         p_baselineDataout(srnuts2,"perHa","SURTOT","NITF","%simy%")*(1-%homogeneous_target%/100)
        ) * 0.001;
```

(the relaxations in the elided lines apply only in 2090 or later.)

$$
\text{SURTOT}_r \le \overline{S}_r, \qquad \overline{S}_r = \max\!\left(0,\; S^{\text{base}}_r\,(1 - \rho/100)\right)
\quad \text{for } r \in \text{EU27},\ S^{\text{base}}_r > 0
$$

with $S^{\text{base}}_r$ the baseline surplus per ha and $\rho$ the reduction (surpRedu: 30 in the 2030 Green Deal run).

CAPRI-MOD: the target per ha from the model's own baseline surplus (`capri_mod/supply/supply_module.py` l. 3038-3056,
rule "star3"), the cap on the `N_balance` row (section 1).

Status: ported. The target is the model's own baseline surplus less 30%, as CAPRI takes its own: where the two
baselines' surpluses differ, the targets differ too.

In the Green Deal (kt N, Green Deal against the 2030 reference, CAPRI-MOD / CAPRI): the EU's surplus -29.1% / -28.6%
(10,883 -> 7,713 against 11,059 -> 7,895), mineral N -34.2% / -33.9%, removal -12.6% / -14.3%, manure -12.4% (CAPRI-MOD's
manure applied) / -12.2% (CAPRI's EXCRET). By region:

| | surplus | mineral N | manure applied | removal |
|---|---:|---:|---:|---:|
| FR52 | -86.2 / -84.7 | -15.6 / -9.1 | -72.1 / -76.6 | -45.3 / -49.4 |
| DE21 | -15.8 / -16.0 | -15.9 / -15.6 | -4.8 / -4.8 | -20.7 / -24.6 |
| ES41 | -96.4 / -98.3 | -42.8 / -49.1 | -73.6 / -71.9 | -39.0 / -49.3 |
| ES42 | -53.8 / -53.6 | -38.4 / -32.4 | -30.7 / -34.7 | -23.4 / -19.9 |
| ES51 | -38.7 / -36.8 | -18.0 / -19.3 | -24.1 / -22.3 | -14.0 / -17.1 |
| ES62 | -7.0 / -6.8 | -15.3 / -14.5 | +5.7 / +5.7 | -4.0 / -3.5 |

(manure applied: CAPRI's EXCRET less its net exports, MTRADE.)

---

## Open points on this page

- The crops' N removal at the 2030 base: CAPRI-MOD's is 4-6% above CAPRI's in ES41 and FR52 (EU +1.4%): to be
  checked item by item (crop, technology, $y^{\text{mit}}$).
- Section 4: the residue term's mitigation part and the legume-share factor, line by line.
