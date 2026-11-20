# The equation book: CAPRI's equations and CAPRI-MOD

CAPRI-MOD reimplements CAPRI's equations in Python. This folder keeps the mathematics visible: each page takes one
block of CAPRI's model and sets out, equation by equation,

1. **CAPRI's equation as written in its GAMS code**, quoted with its file and line numbers (CAPRI star 3.0, the copy
   this project is calibrated against);
2. **the same equation in mathematical notation**, with the notation stated on the page;
3. **where CAPRI-MOD builds it** (module, function, line numbers) and **how**: its status, one of
   - *ported*: the same equation;
   - *ported in another form*: the same relation written differently (for example several of CAPRI's equations
     substituted into one row), with the reason;
   - *departure*: deliberately different, with its entry in docs/DEPARTURES_FROM_CAPRI.md (DEP-n);
   - *not built*: with its entry in docs/KNOWN_ISSUES.md;
4. **its values in both models**: at the 2030 base, and in a scenario where that shows how the block works.

The equations and their design are the work of the CAPRI developers (the CAPRI Network, www.capri-model.org); the GAMS
text is quoted for comparison. CAPRI's results are used to check CAPRI-MOD, not to set it.

## Pages

| # | Page | CAPRI's equations | Status |
|---|---|---|---|
| 1 | [The regional nitrogen balance](01_regional_n_balance.md) | e_SURTOTHa, e_EXCRET, ManureNPK_, e_MINFERT, e_MTRADEHa, e_BIOFIX, e_ATMOSD, e_CRESID, e_EXPPRD, SURTOT_REST_ (surptot.gms) | draft, 18 November 2026 |

Planned, in the order of the diagnosis work: the crops' nutrient need balance and the inner fertiliser model
(NUTNED_, fertDistMine_, fertDistExcr_, fertDistCres_, e_focFertDist); the manure pools and trade (ManureNPK_, the
manure market); the technology mix (T1/T2, p_technFact).

## Conventions

- Each page states the runs its values come from (run file, code commit, CAPRI's result files).
- Line numbers refer to the code at the page's date; a page is updated when the code it cites changes.
- Money in CAPRI-MOD's terms (2017 prices) unless the page says otherwise; CAPRI's values over its deflator where
  compared.
