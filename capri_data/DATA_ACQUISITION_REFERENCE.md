# CAPRI-mod — Data Acquisition Reference

Everything needed to retrieve updated/real data: exact filenames, where they live,
how to access them, and the honest answer on APIs. Verified against CAPRI's own
source tree and current (2025/26) CAPRI documentation.

---

## 0. The API question — answered honestly

**There is no data API/webservice for CAPRI.** I checked CAPRI's entire GAMS source:
the only URLs in it are documentation/citation links (PDFs), never a REST/service
endpoint. CAPRI is distributed as **files over SVN** (Apache Subversion) plus
**zip downloads** from the website. So auth credentials for an "API" don't apply —
what credentials get you is **SVN repository access**. See §3.

---

## 1. What to retrieve (priority order)

| Need | Why | Priority |
|---|---|---|
| STAR **database** zip (`results_2.8.zip`) | Compiled, calibrated baseline — replaces synthetic files + gives consistent newer base | HIGHEST |
| STAR **code** zip (`STAR_2.8.zip`) | Raw data + build routines (self-contained) | HIGH |
| Newer `fao_agg` / market GDX | Newer base-year prices+balances+elasticities | optional |

The STAR **database** alone resolves the two synthetic files AND vintage consistency,
because it is CAPRI's own mutually-compatible data.

---

## 2. Exact filenames & locations (inside a CAPRI installation / STAR release)

Paths are relative to the CAPRI system folder. Files are **GDX** (GAMS binary) —
export the listed **symbol** to CSV/XLSX (via GAMS `gdxdump` or the GUI export), as
was done for `fao_agg_17`.

### 2a. To replace the TWO synthetic files (highest value)

| Model file (synthetic now) | CAPRI source file | GDX symbol to export |
|---|---|---|
| `feed_requirements.csv` | `dat/coco/feed_agri.gdx` | `p_AgriProd` (feed rows: PMEA,PPAS,TGRA,FPEG,FLUC,FPGO,FAGO,MAIF) |
| ″ (feed input coeffs) | `results/` feed build output | `p_feedInpCoeff`, `p_feedDetail` |
| `nutrient_coefs.csv` | `dat/arm/nutrient_cont_usda.gdx` | `p_nutrientCont` |

### 2b. Regional base data (areas, yields, herds) — for a newer base year

| Data | CAPRI source file | GDX symbol |
|---|---|---|
| Regional DB (2015 base) | `dat/capreg/p_regiodata2015.gdx` | `p_regioData` |
| Regional DB (2009 base) | `dat/capreg/p_regiodata2009.gdx` | `p_regioData` |
| Regional time series | `results/capreg/res_time_series.gdx` | (time-series regional) |
| 2019 update | `dat/capreg/update_2019_regiodata.gdx` | `p_regioData` |

### 2c. Market / prices / balances — for a newer base year

| Data | CAPRI source file | Note |
|---|---|---|
| Market SUA (prices, balances) | `results/fao/fao_dataMarket.gdx` | newer analogue of `fao_agg_17` |
| Global raw market | `results/global/data_market_raw.gdx` | |
| AGLINK baseline (biofuel too) | `dat/baseline/aglink2024_oriEUdata.gdx` | 2024 vintage present; also 2019–2023 |

### 2d. Environment / GHG (if refreshing those)

| Data | CAPRI source file |
|---|---|
| GHG/gas results | `results/envind/GASES.gdx` |
| Energy indicators | `results/enerind/ENER_new.gdx` |

---

## 3. How to access — SVN + downloads (this is where credentials apply)

### Route A — Website zip downloads (simplest, no credentials for public Stars)
- Go to **capri-model.org** → "get CAPRI" / "getting started" page.
- In the table of releases, click **"Code"** (e.g. `STAR_2.8.zip`) and **"Database"**
  (e.g. `results_2.8.zip`).
- Star 2.8 embeds GAMS + Java (no separate install). Latest recommended.

### Route B — SVN repository (this is the "API + credentials" analogue)
CAPRI installation/management is SVN-based. Verified mechanism:
- SVN server host: **`https://svn1.agp.uni-bonn.de/svn/<TAG>`**
  (documented example tag `TS2015_1`, with example user/pass `ts2015`/`ts2015`
  for that public teaching repo).
- **Developer releases** need a **CAPRI SVN account** (your credentials) — request via
  the CAPRI network. With it, `svn checkout` the release tag to get `dat/`, `gams/`,
  `GUI/` folders including all raw data.
- Client: any SVN client (TortoiseSVN on Windows, or `svn` CLI).

```
svn checkout https://svn1.agp.uni-bonn.de/svn/<RELEASE_TAG> capri_src
#   -> prompts for username / password (your CAPRI SVN credentials)
```

> If you have credentials, they are **SVN credentials for `svn1.agp.uni-bonn.de`**,
> not an API key. That is the auth you can help with.

### Route C — Contact / registration
Full COCO database access follows "the procedure described on the CAPRI website"
and "could imply a specific procedure or a fee." Network/course participation
(Humboldt/Thünen CAPRI course) is a common access path. For code access, the
INMS record lists **Adrian Leip (JRC)** as a contact; the model is hosted at
**Bonn University / EuroCARE**.

---

## 4. Also-public alternative datasets (not from CAPRI folders)

| Source | What | Where |
|---|---|---|
| Scientific Data (2026) | EU disaggregated CAPRI data: crops, livestock, N, timeseries 2000–2018 (Eurostat to 2024) | nature.com/articles/s41597-026-06919-8 |
| Eurostat | Crop (`APRO_CPSHR`) & animal (`AGR_R_ANIMAL`) production, NUTS0/1/2, 2000–2024 | ec.europa.eu/eurostat |
| FAOSTAT | Producer prices, commodity balances, bilateral trade (already used) | fao.org/faostat |

**Note:** Eurostat *does* have a real REST/JSON API (unlike CAPRI). If a data API is
what you want, Eurostat's is the one to target for EU quantities/prices — but its
vintages/units must be reconciled to a CAPRI base (the validator guards this).

---

## 5. Once you have any of it

Export the listed GDX **symbol** to CSV/XLSX (GAMS `gdxdump File.gdx symb=SYMBOL
format=csv`, or the CAPRI GUI export), upload it, and it gets wired in the same way
as the 2017 `fao_agg`. The validator then confirms vintage consistency before any run.
