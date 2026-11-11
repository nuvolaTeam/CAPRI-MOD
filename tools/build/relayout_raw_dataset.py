"""Lay out nuvolaTeam/capri-mod-raw as CAPRI's installation (the project lead, 11 November 2026): the Parquet of each
CAPRI file under capri/<its folder in CAPRI>/<file name without extension>/, and no originals (the Parquet are the
originals, in Parquet: each file's metadata names the source file and its SHA-256, and tools/check/
check_capri_gdx_parquet.py checked every record against it before the upload).

CAPRI's folders: dat/<subfolder> (CAPRI's dat folder), results/<module> (output/results), temp (the scratch directory
%scrdir%, where CAPRI writes its debug dumps); the folder of each file from where CAPRI's code reads or writes it
(LOCATIONS: the GAMS statement), or "inferred" where the code does not name it (LOCATION_INFERRED).

The move is made on the server (copies of the LFS files, the small _symbols.csv uploaded again), then the old paths
and the originals deleted, in commits of at most CHUNK operations; the manifest (tools/pipeline/capri_raw_manifest.json)
is rewritten: files (the new paths), sources (per Parquet folder: the source file's name, SHA-256 and size, where its
location comes from, whether the project lead trusts it).

    python tools/build/relayout_raw_dataset.py [--apply]     without --apply: the mapping only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "build"))
from make_raw_manifest import OUT, REPO  # noqa: E402

#: the files' folders in CAPRI's installation, by a pattern of the file name, with the GAMS statement that names it
LOCATIONS = [
    (r"^(AD_basedata|LitRevFertTech|gains_ad|holdingsLSU)$", "dat/scen/ghgtech",
     "%datdir%/scen/ghgtech/<file>.gdx (supply/ghg technology code)"),
    (r"^(GHGinvData|mirror_.*_norway)$", "dat/miterra", "%datdir%/miterra/<file>.gdx"),
    (r"^(landscape_nuts2|soc_data|nvz|transition_matrix_EU28|waterMetersPerHa)$", "dat/envind",
     "%datdir%/envind/<file>.gdx"),
    (r"^dataFSS_1990_2013$", "dat/water", "../dat/water/dataFSS_1990_2013.gdx"),
    (r"^(allpop|nutrient_cont_usda)$", "dat/arm", "../dat/arm/<file>.gdx"),
    (r"^(?i:aglink20\d\d.*|data_SSPV3_update|recent_mlk_yld)$", "dat/baseline", "../dat/baseline/<file>.gdx"),
    (r"^POTENCIA_", "dat/biofuel/POTENCIA_processing", "../dat/biofuel/POTENCIA_processing/<file>.gdx"),
    (r"^(fossilFuel|primes_ref_\d+)$", "dat/biofuel", "../dat/bioFuel/<file>.gdx"),
    (r"^Agri_Prod$", "dat/coco", "../dat/coco/Agri_Prod.gdx"),
    (r"^(GLOBIOM-EU_|globiom_eu_)", "dat/global", "..\\dat\\global\\%GLOfilename% (global/convert_globiom.gms)"),
    (r"^(cost_amm_|costsavings_)", "results/envind", "%results_out%/envind/<file>.gdx"),
    (r"^(data_market_|trends_\d+|results_\d+$)", "results/baseline", "%results_in%/baseline/<file>.gdx"),
    (r"^priFertDist_", "results/fert", "%RESULTS_IN%/fert/priFertDist_<MS><BAS>.gdx"),
    (r"^(reqrel_\d\d|res_\d\d|res_time_series_\d\d)[A-Z]+$", "results/capreg", "%results_in%/capreg/<file>.gdx"),
    (r"^res_2_", "results/capmod", "%CAPRIScenResults%/res_2_<...>.gdx"),
    (r"^res_.*_21730$", "results/permits", "capmod.gms l. 1641-1645: results\\permits\\res_<scenario>_21730.gdx"),
    (r"^(GLOBIOM_(EU|GL)_longrun_|longrun_info_fac_)", "results/global", "%results_out%/global/<file>.gdx"),
    (r"^sim_ini_", "results/simini", "%results_out%/simini/sim_ini_<...>.gdx"),
    (r"^\d{13}_(data_cur|cur_step|market_model|iy)$|^supply_model$", "temp", "%scrdir%/<file>.gdx"),
]
#: where CAPRI's code does not name the file's folder: the folder it was delivered in, as the best guess
LOCATION_INFERRED = [
    (r"^[A-Z]{2,3}_17$", "results/capreg/Capreg_tseries",
     "delivered as Capreg_tseries/<CC>_17.gdx (upload Capreg_tseries.zip); CAPRI's folder not confirmed"),
    (r"^chk_market_data_", "results/arm", "written to %results_out%/ (arm); delivered from results/arm"),
    (r"^PACT_201020_IFS$", "dat/ifm_cap", "not read by CAPRI's code (IFM-CAP's activity mapping); folder chosen here"),
]
#: data the project lead does not trust (the market model's debug dumps of an earlier run)
UNTRUSTED = re.compile(r"^(\d{13}_(data_cur|cur_step|market_model|iy)|supply_model)$")
CHUNK = 2000


def location(stem: str):
    for pat, folder, why in LOCATIONS:
        if re.search(pat, stem):
            return folder, "code: " + why
    for pat, folder, why in LOCATION_INFERRED:
        if re.search(pat, stem):
            return folder, "inferred: " + why
    raise SystemExit(f"{stem}: no CAPRI folder known")


def plan(man):
    """{old Parquet folder: (new folder, source entry)} from the manifest's originals and their Parquet folders."""
    folders = {str(PurePosixPath(k).parent) for k in man["files"] if k.startswith("capri/")}
    out = {}
    for k, e in man["files"].items():
        if not k.startswith("originals/"):
            continue
        rel = PurePosixPath(k[len("originals/"):])
        stem = rel.stem
        cands = [f"capri/{rel.with_suffix('')}", f"capri/results/{stem}"]
        old = next((c for c in cands if c in folders), None)
        if old is None:
            raise SystemExit(f"{k}: no Parquet folder")
        folder, why = location(stem)
        new = f"capri/{folder}/{re.sub(r'^[0-9]{13}_', '', stem)}"      # the upload's time stamp prefix dropped
        out[old] = (new, {"file": rel.name, "sha256": e["sha256"], "size": e["size"], "location": why,
                          "trusted": not UNTRUSTED.search(stem), "version": e["version"]})
    news = [v[0] for v in out.values()]
    if len(set(news)) != len(news):
        raise SystemExit("two files would share a folder")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    man = json.loads(OUT.read_text())
    mp = plan(man)
    moves = {}
    for k, e in man["files"].items():
        if k.startswith("capri/"):
            old = str(PurePosixPath(k).parent)
            if old not in mp:
                raise SystemExit(f"{k}: its folder has no original")
            moves[k] = mp[old][0] + "/" + PurePosixPath(k).name
    by_new = {}
    for old, (new, src) in mp.items():
        top = "/".join(new.split("/")[1:3])
        by_new[top] = by_new.get(top, 0) + 1
    print(f"{len(mp)} CAPRI files, {len(moves)} Parquet files to move; folders:", dict(sorted(by_new.items())))
    for old, (new, src) in sorted(mp.items(), key=lambda x: x[1][0]):
        if src["location"].startswith("inferred") or not src["trusted"]:
            print(f"  {new}: {src['location'][:90]}{'' if src['trusted'] else ' [untrusted]'}")
    if not a.apply:
        return
    from huggingface_hub import CommitOperationAdd, CommitOperationCopy, CommitOperationDelete, HfApi, hf_hub_download
    api = HfApi()
    lfs = {}
    for f in api.list_repo_tree(REPO, repo_type="dataset", recursive=True):
        if getattr(f, "lfs", None):
            lfs[f.path] = True
    ops = []
    with tempfile.TemporaryDirectory() as tmp:
        for k, new in sorted(moves.items()):
            if lfs.get(k):
                ops.append(CommitOperationCopy(src_path_in_repo=k, path_in_repo=new))
            else:
                p = hf_hub_download(REPO, k, repo_type="dataset", local_dir=tmp)
                ops.append(CommitOperationAdd(path_in_repo=new, path_or_fileobj=p))
        for i in range(0, len(ops), CHUNK):
            api.create_commit(REPO, repo_type="dataset", operations=ops[i:i + CHUNK],
                              commit_message=f"Layout of CAPRI's installation: copies {i + 1}-{min(i + CHUNK, len(ops))}")
            print(f"copied {min(i + CHUNK, len(ops))} of {len(ops)}", flush=True)
    dels = [CommitOperationDelete(path_in_repo=k) for k in man["files"] if k.startswith("originals/")]
    dels += [CommitOperationDelete(path_in_repo=k) for k in moves if moves[k] != k]
    for i in range(0, len(dels), CHUNK):
        api.create_commit(REPO, repo_type="dataset", operations=dels[i:i + CHUNK],
                          commit_message=f"Layout of CAPRI's installation: old paths and originals removed "
                                         f"{i + 1}-{min(i + CHUNK, len(dels))}")
        print(f"deleted {min(i + CHUNK, len(dels))} of {len(dels)}", flush=True)
    files = {moves[k]: e for k, e in man["files"].items() if k in moves}
    man["files"] = dict(sorted(files.items()))
    man["sources"] = dict(sorted((new, src) for old, (new, src) in mp.items()))
    man["layout"] = ("capri/<CAPRI folder: dat/<subfolder>, results/<module>, temp>/<file name>/<symbol>.parquet "
                     "and _symbols.csv; no originals (11 November 2026)")
    OUT.write_text(json.dumps(man, indent=1) + "\n")
    print(f"{OUT.relative_to(ROOT)}: {len(man['files'])} files, {len(man['sources'])} sources")


if __name__ == "__main__":
    main()
