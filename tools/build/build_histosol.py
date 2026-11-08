"""CAPRI's histosols (drained organic soils) per model region: emission factors and the fallowing option.

CAPRI (envind/prep_lulucf_carbon.gms, calc_lulucf_carbon.gms, gases.gms, no_histosols.gms):
  * share of cropland and grassland on organic soil: p_shareOrganicSoil(crop) = p_OrgSoilOri(soc_regN2_rk),
    (grslnd) = sog_regN2_rk of the region; a missing record is zero (EU, UK, Norway: p_OrgSoilNoGap); the Western
    Balkans and Turkey fill it: the country's JRC share, else FAO's peat share, else p_peatsh_def / 100, grassland
    taking the cropland share;
  * emissions per ha of the land-use class (p_BioHisBur, t per ha):
        share x sum_climzone p_sharClim(climzone, class) x p_emifacOrganicSoil(class, climzone, gas) x 0.001
        x 44/28 (N2O) or 44/12 (CO2, CH4 as CAPRI writes it);
    climate-zone shares from FAO land use 2000 by country (cropland: cropland + cropland_per;
    grassland: grassland + shrubland; all land where a class has none), IPCC 2013 Wetlands Supplement
    factors by aggregated zone (boreal, temperate, tropical). N2OHIS is agriculture (UNFCCC sector 3);
    CO2HIS and CH4HIS are land use (sector 4);
  * fallowing (FALLOW, iHisCr / iHisGr): a share s of the histosol area of cropland / productive grassland is
    idled; it still occupies its land; its emissions fall by s x (1 - QEmitt), QEmitt = 1 - p_ghgTechHisto = 0
    in the Green Deal runs (refpol_endotech_*). Cost per ha of histosol area (GHG_Mit_Cost_):
        (costParLin + pmpParLin) s + 0.5 pmpParSqr s^2,   costParLin = 216 EUR/ha (base-year money),
    PMP terms from CAPRI's calibration runs (costsaving0/1 = v_Miti marginal / (class area x share) in the ini
    and max runs) with no_histosols.gms's relSubs rules; MaxShare = max-run level + 2e-6.

Written: capri_data/2017/environment/histosol.csv, per model region and class (crop, grass):
  share_<c>         organic-soil share of the class
  ef_n2o_<c>        kg N2O-N per ha of histosol (climate-weighted IPCC factor)
  n2o_t_ha_<c>      t N2O per ha of the class (share x factor), as CAPRI's p_BioHisBur; grassland without a
                    share takes the cropland value (gases.gms N2OHIS on GRAE, GRAI)
  co2_t_ha_<c>, ch4_t_ha_<c>   the same for CO2HIS and CH4HIS (reported, land use)
  cs0_<c>, cs1_<c>, maxshare_<c>, pmp_lin_<c>, pmp_sqr_<c>, cost_lin_<c>   (EUR per ha of histosol,
                    2017 money: CAPRI's 2030 marginals over its 2030/2017 input deflator)

Sources: sources/raw/capri/dat/envind/orgsoil_share_p_orgsoilori.parquet, ipcc_wetlands_p_emifacOrganicSoil_ori.parquet,
sources/raw/capri/dat/envind/fao_peatland/fao_peatland_P.parquet and lulucf_emissions_original_source_p_PEATSH_def.parquet (the fallbacks of the
Western Balkans and Turkey; the WBA6 set from sets.gms),
fao_landuse_2000_P.parquet (the project lead's gdxdumps, converted by tools/build/convert_sources.py); FAO
country codes from the GAMS source (global/fao_codes_new.gms FAORegions_map); sources/intermediate/ghgtech/capri_costsavings_2030.parquet; CROP and GRAS 2030 levels
from validation/greendeal_2030/capri_marginal_terms_ini_2030.csv.xz; deflator from
trajectories/capri_price_ratios_2030.csv.

    python tools/build/build_histosol.py [--gams-dir capri_sources/gams]
"""
from __future__ import annotations
import argparse, csv, importlib.util, json, re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

import functools as _ft
import sys  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))  # tools/lib/paths.py
from paths import SOURCES  # noqa: E402  (CAPRI's material outside the repository)
from _sources_io import read_source, source_records, write_source  # noqa: E402  (capri_data/sources: Parquet)
_read_csv = _ft.partial(pd.read_csv, float_precision="round_trip")   # floats to the last digit (K82)
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "capri_data" / "sources"
ZONE_AGG = {"Boreal": "boreal", "CoolTempDry": "temperate", "CoolTempWet": "temperate", "WarmTempDry": "temperate",
            "WarmTempWet": "temperate", "TropicalDry": "tropical", "TropicalMoist": "tropical",
            "TropicalWet": "tropical", "TropicalMont": "tropical"}
CLASS_LU = {"crop": ("Cropland", "Cropland_per"), "grslnd": ("Grassland", "Shrubland")}
COST_PAR_LIN = 216.0           # no_histosols.gms, EUR/ha, inflated from the base year by CAPRI
TAG = {"crop": "crop", "grslnd": "grass"}


#: Until 30 October 2026 this builder parsed the gdxdump text with a pattern that missed each dump's last record (the
#: line ending in "/;"): p_OrgSoilOri('NO011000', 'sof_regN2_rk'), P('299', 'TropicalDry', 'Forest_be30') and
#: p_emifacOrganicSoil_ori('N2O', 'grslnd', 'tropical') = 5; an extraction error of capri-mod, found when the dumps were
#: converted to CSV. Every record is read now.


def _records(name):
    """The records of a gdxdump converted to CSV (capri_data/sources/raw/capri/dat/envind, tools/build/convert_sources.py)."""
    return source_records(SRC / "raw" / "capri" / "dat" / "envind" / name)


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def fao_map(gams_dir: Path) -> dict:
    """{CAPRI country: FAO codes}, CAPRI's Map_FAO_reg (envind/prep_lulucf_carbon.gms l. 28-32): FAORegions_map of
    global/fao_codes_new.gms (Turkey's code TUR included since 4 November 2026), and FAO's former Serbia and Montenegro
    (186) for Serbia, Montenegro and Kosovo, FAO's Serbia (272) for Serbia and Kosovo."""
    txt = open(gams_dir / "global" / "fao_codes_new.gms", errors="ignore").read()
    i = txt.index("SET FAORegions_map(")
    out = defaultdict(set)
    for line in txt[i:].splitlines()[1:]:
        if line.strip().startswith("/;"):
            break
        m = re.match(r"^\s*([A-Z]{2}000000|TUR)\.\(([^)]*)\)", line)
        if m:
            for code in m.group(2).split(","):
                out[m.group(1)].add(code.strip())
    for ms in ("CS000000", "MO000000", "KO000000"):
        out[ms].add("186")
    for ms in ("CS000000", "KO000000"):
        out[ms].add("272")
    return out


def gap_countries(gams_dir: Path) -> set:
    """CAPRI's countries whose missing organic-soil share is filled (not p_OrgSoilNoGap, prep_lulucf_carbon.gms l. 252):
    the Western Balkans (sets.gms NUTS0_WBA6) and Turkey; elsewhere a missing JRC record is zero."""
    txt = open(gams_dir / "sets.gms", errors="ignore").read()
    m = re.search(r"SET\s+NUTS0_WBA6\s*/(.*?)/\s*;", txt, re.S | re.I)
    return {ln.split()[0] for ln in m.group(1).splitlines() if ln.strip() and not ln.strip().startswith("*")} | {"TUR"}


def relsubs_pmp(cs0, cs1, cpl, ini, mx):
    """no_histosols.gms (premCapMitTech off): relSubs0/1, pmpParSqr, pmpParLin."""
    rs0 = 0.01 * np.sign(cpl - cs0)
    rs1 = -0.2 if (cpl - cs1) < 0 else 1.0
    if cpl != cs1:
        ratio = 1.0 - (cpl - cs0) / (cpl - cs1) * (1.0 - rs0)
        if cpl < cs1:
            rs1 = min(rs1 * (rs0 < 0) - rs1 * (rs0 > 0), ratio - 0.1)
        elif cpl > cs1:
            rs1 = max(rs1 * (rs0 > 0) - rs1 * (rs0 < 0), ratio + 0.1)
    sqr = (max(0.01 * abs(cs0), -cs0 * (1 - rs0) + cs1 * (1 - rs1) + cpl * (rs1 - rs0)) / (mx - ini)
           if mx > ini else 0.0)
    lin = (cs0 - cpl) * (1 - rs0) - sqr * ini
    return rs0, rs1, sqr, lin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gams-dir", type=Path, default=SOURCES / "gams")
    a = ap.parse_args()
    org = defaultdict(dict)
    for r in _records("orgsoil_share_p_orgsoilori.parquet"):
        org[r["region"]][r["item"]] = float(r["value"])
    ef = {(r["gas"], r["land_use"], r["climate_zone"]): float(r["value"])
          for r in _records("ipcc_wetlands_p_emifacOrganicSoil_ori.parquet")}
    lu = defaultdict(lambda: defaultdict(float))
    for r in _records("fao_landuse_2000_P.parquet"):
        lu[r["fao_code"]][(r["climate_zone"], r["land_use"])] += float(r["value"])
    c2f = fao_map(a.gams_dir)
    clim = defaultdict(lambda: defaultdict(float))        # MS -> (zone, lu) -> area
    for ms, codes in c2f.items():
        for code in codes:
            for k, v in lu.get(code, {}).items():
                clim[ms][k] += v
    gap = gap_countries(a.gams_dir)
    peat = {r["fao_code"]: float(r["value"]) for r in source_records(
        SRC / "raw" / "capri" / "dat" / "envind" / "fao_peatland" / "fao_peatland_P.parquet")}
    peat_def = {r["region"]: float(r["value"]) for r in source_records(
        SRC / "raw" / "capri" / "dat_local" / "envind" / "lulucf_emissions_original_source_p_PEATSH_def.parquet")}

    def national_crop_share(ms):
        """CAPRI's cropland share of a country that fills its gaps (prep_lulucf_carbon.gms l. 245-259): its JRC record,
        else FAO's peat share of its FAO regions, else p_peatsh_def / 100."""
        v = org.get(ms, {}).get("soc_regN2_rk", 0.0)
        if not v:
            v = sum(peat.get(c, 0.0) for c in c2f.get(ms, ()))
        if not v:
            v = peat_def.get(ms, 0.0) / 100.0
        return v

    def zone_shares(ms, cls):
        rec = clim.get(ms, {})
        z = defaultdict(float)
        for (zone, l), v in rec.items():
            if l in CLASS_LU[cls]:
                z[zone] += v
        if sum(z.values()) <= 0:
            for (zone, l), v in rec.items():
                z[zone] += v
        t = sum(z.values())
        return {k: v / t for k, v in z.items()} if t > 0 else {}

    cs = read_source(SRC / "intermediate" / "ghgtech" / "capri_costsavings_2030.parquet")
    cs = cs[cs["technology"] == "FALLOW"]
    terms = _read_csv(ROOT / "capri_data" / "validation" / "greendeal_2030" / "capri_marginal_terms_ini_2030.csv.xz",
                        header=None, names=["region", "act", "item", "value"], dtype=str)
    terms = terms[(terms["item"] == "LEVL") & terms["act"].isin(["CROP", "GRAS"])]
    lev = {(r.region, r.act): float(r.value) for r in terms.itertuples()}
    pr = _read_csv(ROOT / "capri_data" / "trajectories" / "capri_price_ratios_2030.csv")
    defl = float(pr["deflator"].median())

    mr = _load(ROOT / "tools" / "lib" / "_model_regions.py")
    import importlib.util as _ilu_
    _sp_ = _ilu_.spec_from_file_location("_mr_", ROOT / "tools" / "lib" / "_model_regions.py")
    _mr_ = _ilu_.module_from_spec(_sp_); _sp_.loader.exec_module(_mr_)
    to_c8 = _mr_.region_to_capri()          # correspondence + NUTS splits and merges (tools/lib/_model_regions.py)
    rows = []
    for reg in mr.model_regions():
        # every supply region: the histosol emissions are CAPRI's in all of them; the fallowing outside the EU is a run
        # setting (fallowInAllRmssup, capri_mod/policy/endotech.py). Until 4 November 2026 EU units only.
        ms = mr.national_code(reg)
        c8 = to_c8.get(reg)
        # CAPRI: the JRC share of the region; a missing record is zero for every NUTS 0 of the EU, the UK and Norway
        # (p_OrgSoilNoGap, prep_lulucf_carbon.gms l. 243-266). Until 4 November 2026 a region with neither share took
        # its member state's (65 regions, 41 of them with a non-zero national share), where CAPRI's 2030 results have
        # zero: a reproduction error of capri-mod (KNOWN_ISSUES K112).
        src = c8
        sh = {"crop": org.get(src, {}).get("soc_regN2_rk"), "grslnd": org.get(src, {}).get("sog_regN2_rk")}
        if ms in gap:
            # the Western Balkans and Turkey (prep_lulucf_carbon.gms l. 261-266): a region without either share takes
            # its country's cropland share; grassland without a share takes the cropland one ("questionable fall back,
            # but no better information", CAPRI's comment)
            if not (sh["crop"] or sh["grslnd"]):
                sh["crop"], src = national_crop_share(ms), ms
            if not sh["grslnd"]:
                sh["grslnd"] = sh["crop"]
        rec = {"region": reg, "capri_region": src}
        for cls in ("crop", "grslnd"):
            t = TAG[cls]
            s_ = float(sh[cls] or 0.0)
            zs = zone_shares(ms, cls)
            for gas, fac in (("N2O", 44.0 / 28.0), ("CO2", 44.0 / 12.0), ("CH4", 44.0 / 12.0)):
                e = sum(w * ef.get((gas, cls, ZONE_AGG[z]), 0.0) for z, w in zs.items())
                if gas == "N2O":
                    rec[f"ef_n2o_{t}"] = e
                rec[f"{gas.lower()}_t_ha_{t}"] = s_ * e * 0.001 * fac
            rec[f"share_{t}"] = s_
            # fallowing: CAPRI's calibration on its 2030 ini and max runs
            act = "IHISCR" if cls == "crop" else "IHISGR"
            area = lev.get((c8 if (c8, "CROP") in lev else ms, "CROP" if cls == "crop" else "GRAS"))
            g = cs[(cs["region"] == (c8 if c8 in set(cs["region"]) else ms)) & (cs["activity"] == act)]
            gi, gm = g[g["run"] == "ini"], g[g["run"] == "max"]
            if s_ > 0 and area and len(gi) and len(gm) and pd.notna(gi["marginal"].iloc[0]) and pd.notna(gm["marginal"].iloc[0]):
                base = area * s_
                cs0 = float(gi["marginal"].iloc[0]) / base / defl
                cs1 = float(gm["marginal"].iloc[0]) / base / defl
                mx = min(1.0, float(gm["level"].iloc[0]) + 2e-6)
                rs0, rs1, sqr, lin = relsubs_pmp(cs0, cs1, COST_PAR_LIN, 0.0, mx)
                rec.update({f"cs0_{t}": cs0, f"cs1_{t}": cs1, f"maxshare_{t}": mx, f"cost_lin_{t}": COST_PAR_LIN,
                            f"pmp_lin_{t}": lin, f"pmp_sqr_{t}": sqr})
        # CAPRI's N2OHIS of the grass activities (gases.gms l. 676-686): every crop activity, GRAE and GRAI included
        # (MCACT holds GRSACT), takes the cropland factor, overwritten by the grassland one where that is non-zero; so a
        # region with a cropland share and no grassland share (Greece's: no JRC grassland record) gives its grassland
        # the cropland N2O per ha, as CAPRI's 2030 results show (KNOWN_ISSUES K112). CO2HIS and CH4HIS stay per class
        # (calc_lulucf_carbon.gms), as the fallowing (its MaxShare is the grassland share).
        if rec["n2o_t_ha_grass"] == 0.0 and rec["n2o_t_ha_crop"] > 0.0:
            rec["n2o_t_ha_grass"] = rec["n2o_t_ha_crop"]
        rows.append(rec)
    out = pd.DataFrame(rows).set_index("region")
    # the declared column order (capri_data/schema/17_environment.sql), whichever region comes first
    cols = ["capri_region"] + [f"{k}_{t}" for t in ("crop", "grass") for k in ("ef_n2o", "n2o_t_ha", "co2_t_ha",
                                                                                "ch4_t_ha", "share")]
    cols += [f"{k}_{t}" for t in ("grass", "crop") for k in ("cs0", "cs1", "maxshare", "cost_lin", "pmp_lin", "pmp_sqr")]
    out = out[cols]
    dest = ROOT / "capri_data" / "2017" / "environment" / "histosol.csv"
    out.to_csv(dest)
    print(f"wrote {dest.name}: {len(out)} regions; cropland share median {out.share_crop.median():.4f}, "
          f"grassland {out.share_grass.median():.4f}; N2O factor crop {out.ef_n2o_crop.median():.1f}, grass "
          f"{out.ef_n2o_grass.median():.1f} kg N2O-N/ha; fallowing calibrated: crop "
          f"{int(out.get('pmp_sqr_crop', pd.Series(dtype=float)).notna().sum())}, grass "
          f"{int(out.get('pmp_sqr_grass', pd.Series(dtype=float)).notna().sum())} regions")


if __name__ == "__main__":
    main()
