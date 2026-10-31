"""CasADi 3.8.1 as a Python wheel with SPRAL's OpenMP factorisation (register BEYOND-11; the project lead's choice of a full
CasADi build, 1 November 2026, for Red Hat 9.8, glibc 2.34).

PyPI's CasADi 3.8.1 (cp311-abi3-manylinux_2_28_x86_64) builds SPRAL with --disable-openmp (CMakeLists.txt l. 1899),
so IPOPT's SPRAL runs on one thread there. This script repeats CasADi's own release build of that wheel
(.github/workflows/binaries.yml: jobs swig, core-dockcross, python-dockcross; manylinux_2_28-x64; Python 3.11 limited
API) with one change, tools/solvers/casadi_3.8.1_spral_openmp.patch:

  - SPRAL configured without --disable-openmp, and -lgomp added to IPOPT's SPRAL link flags;
  - SWIG_IMPORT on (binaries.yml's swig job does the same with sed before packing the source).

Everything else is CasADi's: the same images (ghcr.io/casadi/ci-swig for the SWIG sources, ghcr.io/jgillis/
manylinux_2_28-x64:production for the build), the same build_flags (read from binaries.yml at the tag, so every plugin
of PyPI's wheel), the solver mockups (github.com/casadi/mockups at v116, built from source here: their release zip is a
github.com download, not reachable from the build machine), the grafting of the runtime libraries into the package
(github.com/jgillis/universal_grafter: jgillis's auditwheel fork renames libgomp, libgfortran and the others with hashed
names, as in PyPI's wheel) and the wheel packer (misc/create_wheel_local.py). The wheel's version is 3.8.1+spral.omp, so
pip and the run manifest tell it from PyPI's.

    python tools/solvers/build_casadi_spral_omp_wheel.py WORKDIR [--jobs N]

Needs Docker (a daemon), git, and network access to github.com (git), ghcr.io, coin-or-tools.github.io (CasADi's MUMPS
and METIS 4 sources) and gitlab.com (Eigen). The steps leave stamp files in WORKDIR/stamps and are skipped when there;
the build takes hours on two cores and about 6 GB of disk. The wheel is written to WORKDIR/dist. Not committed; the
library inside it is loaded by CasADi itself, so supply.nlp_ipopt_library stays "" with it and
supply.nlp_linear_solver = "spral" selects SPRAL (capri_mod/supply/ipopt_library.py's OpenMP rules apply: the threads
of a process that forks its workers).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASADI_TAG = "3.8.1"
MOCKUPS_TAG = "v116"
BUILD_IMAGE = "ghcr.io/jgillis/manylinux_2_28-x64:production"
SWIG_IMAGE = "ghcr.io/casadi/ci-swig:latest"
PY = "311"                      # CasADi's wheel: Python 3.11 limited API (abi3), for Python 3.11 and later
VERSION = "3.8.1+spral.omp"
#: the environment passed into the containers (a proxy, its CA bundle) when the host has one
PASS_ENV = ("HTTPS_PROXY", "https_proxy", "NO_PROXY", "no_proxy")


def sh(cmd, cwd=None, log=None):
    print("  $", " ".join(map(str, cmd)), flush=True)
    with open(log, "a") if log else open(os.devnull, "w") as fh:
        r = subprocess.run([str(c) for c in cmd], cwd=cwd, stdout=fh if log else None,
                           stderr=subprocess.STDOUT if log else None)
    if r.returncode:
        sys.exit(f"failed ({r.returncode}){': see ' + str(log) if log else ''}")


def docker(work: Path, image: str, script: str, log: Path):
    env = []
    for k in PASS_ENV:
        if os.environ.get(k):
            env += ["-e", f"{k}={os.environ[k]}"]
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("CURL_CA_BUNDLE")
    mounts = ["-v", f"{work}:/work"]
    if ca and os.path.isfile(ca):
        mounts += ["-v", f"{ca}:/ca.crt:ro"]
        env += ["-e", "SSL_CERT_FILE=/ca.crt", "-e", "CURL_CA_BUNDLE=/ca.crt", "-e", "GIT_SSL_CAINFO=/ca.crt",
                "-e", "REQUESTS_CA_BUNDLE=/ca.crt"]
    sh(["docker", "run", "--rm", "--network", "host", *env, *mounts, "-w", "/work", image, "bash", "-ec", script],
       log=log)


def stamp(work: Path, name: str) -> bool:
    return (work / "stamps" / name).exists()


def done(work: Path, name: str):
    (work / "stamps").mkdir(parents=True, exist_ok=True)
    (work / "stamps" / name).write_text("done\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work", type=Path)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    a = ap.parse_args()
    work = a.work.expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)
    log = work / "build.log"
    print(f"building in {work} (log {log})")

    if not stamp(work, "sources"):
        if not (work / "casadi").exists():
            sh(["git", "clone", "--depth", "1", "-b", CASADI_TAG, "--recurse-submodules", "--shallow-submodules",
                "https://github.com/casadi/casadi", "casadi"], cwd=work, log=log)
        if not (work / "mockups").exists():
            sh(["git", "clone", "--depth", "1", "-b", MOCKUPS_TAG, "https://github.com/casadi/mockups", "mockups"],
               cwd=work, log=log)
        if not (work / "universal_grafter").exists():
            sh(["git", "clone", "--depth", "1", "https://github.com/jgillis/universal_grafter", "universal_grafter"],
               cwd=work, log=log)
        sh(["git", "apply", HERE / "casadi_3.8.1_spral_openmp.patch"], cwd=work / "casadi", log=log)
        y = (work / "casadi" / ".github" / "workflows" / "binaries.yml").read_text()
        flags = re.search(r'^  build_flags: "([^"]+)"', y, re.M).group(1)
        (work / "build_flags.txt").write_text(flags + "\n")
        done(work, "sources")

    if not stamp(work, "swig"):
        # binaries.yml's swig job (Python 3, GIL release on, as the build's flags)
        docker(work, SWIG_IMAGE, "cd casadi && mkdir -p build_swig && cd build_swig && cmake -DWITH_SELFCONTAINED=ON "
               "-DWITH_PYTHON=ON -DSWIG_EXPORT=ON -DWITH_COMMON=OFF -DWITH_PYTHON_GIL_RELEASE=ON .. "
               "&& make python_source && cd .. && rm -rf build_swig", log)
        done(work, "swig")

    if not stamp(work, "mockups"):
        docker(work, BUILD_IMAGE, "cd mockups && cmake -B build_mock -DCMAKE_BUILD_TYPE=Release "
               "-DCMAKE_INSTALL_PREFIX=/work/mockups_install . && cmake --build build_mock -j2 "
               "&& cmake --install build_mock", log)
        done(work, "mockups")

    if not stamp(work, "core"):
        # binaries.yml's core-dockcross job
        docker(work, BUILD_IMAGE, "cd casadi && rm -f build/CMakeCache.txt && cmake -Bbuild -DCMAKE_BUILD_TYPE=Release "
               "-DWITH_SELFCONTAINED=ON $(cat /work/build_flags.txt) -DCMAKE_PREFIX_PATH=/work/mockups_install/cmake "
               f"-H. && cmake --build build -j{a.jobs}", log)
        done(work, "core")

    if not stamp(work, "python"):
        # binaries.yml's python-dockcross job, its Build step
        docker(work, BUILD_IMAGE, "cd casadi && PYINC=$(ls -d /opt/python/cp%s*/include/python* | head -n 1) && "
               "cmake -Bbuild -DWITH_PYTHON=ON -DPYTHON_INCLUDE_DIR=$PYINC -USWIG_IMPORT "
               "-DCMAKE_INSTALL_PREFIX=/work/install -DSKIP_CONFIG_H_GENERATION=ON "
               "-DWITH_PYTHON_LIMITED_API=ON -DPYTHON_LIMITED_API_TARGET=%s.%s && "
               "cmake --build build --target install -j%d" % (PY, PY[0], PY[1:], a.jobs), log)
        done(work, "python")

    if not stamp(work, "graft"):
        # universal_grafter's Linux steps: RPATH $ORIGIN, a dummy wheel of the package, jgillis's auditwheel repair
        # (the runtime libraries copied in under hashed names), the result unpacked over the package
        docker(work, BUILD_IMAGE, "cd install/casadi && (chrpath -l -k -r '$ORIGIN' * || true) && rm -f spral_ssids && "
               "cd /work && W=$(/opt/python/cp39-cp39/bin/python universal_grafter/create_wheel_local.py 64 "
               "manylinux_2_28-x64 install/casadi) && cp universal_grafter/graft_manylinux.sh . && "
               "./graft_manylinux.sh $W 'libknitro:libhsl:libworhp:libsnopt7:libut:libmex:libmx:libeng:"
               "libmadnlp_c:libMad:libmosek64:libxprs:libonnxruntime:libipmc:libconopt:libconopt.so.4:"
               "libonnxruntime.so.1' && rm graft_manylinux.sh && /opt/python/cp39-cp39/bin/python -c "
               "\"import zipfile,shutil,glob,os; z=zipfile.ZipFile('$W'); z.extractall('install/casadi'); "
               "[shutil.copytree(p, os.path.join('install/casadi', os.path.basename(p)), dirs_exist_ok=True) "
               "for p in glob.glob('install/casadi/dummy/*')]; shutil.rmtree('install/casadi/dummy'); "
               "[shutil.rmtree(p) for p in glob.glob('install/casadi/dummy-*.dist-info')]\"", log)
        done(work, "graft")

    if not stamp(work, "wheel"):
        docker(work, BUILD_IMAGE, "mkdir -p dist && cd dist && /opt/python/cp311-cp311/bin/python "
               f"/work/casadi/misc/create_wheel_local.py {VERSION} {PY} linux 64 manylinux_2_28-x64 /work/install/ "
               "--abi3", log)
        done(work, "wheel")
    print("wheel:", *sorted((work / "dist").glob("*.whl")))


if __name__ == "__main__":
    main()
