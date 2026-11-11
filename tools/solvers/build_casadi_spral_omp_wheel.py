"""CasADi 3.8.1 as a Python wheel with SPRAL's OpenMP factorisation (register BEYOND-11; the project lead's choice of a full
CasADi build, 1 November 2026, for Red Hat 9.8, glibc 2.34).

PyPI's CasADi 3.8.1 (cp311-abi3-manylinux_2_28_x86_64) builds SPRAL with --disable-openmp (CMakeLists.txt l. 1899),
so IPOPT's SPRAL runs on one thread there. This script repeats CasADi's own release build of that wheel
(.github/workflows/binaries.yml: jobs swig, core-dockcross, python-dockcross; manylinux_2_28-x64; Python 3.11 limited
API) with one change, tools/solvers/casadi_3.8.1_spral_openmp.patch:

  - SPRAL configured without --disable-openmp, and -lgomp added to IPOPT's SPRAL link flags;
  - SPRAL built with make -j1: its Makefile.am (ralna/spral d385d2c, CasADi's BUILD_SPRAL_VERSION) misses module
    dependencies (interfaces/C/matrix_util.o on src/matrix_util.o, src/ssids/contrib_free.o on src/ssids/contrib.o), so
    a parallel make may compile a file before the module it uses ("Cannot open module file 'spral_matrix_util.mod'",
    then 'spral_ssids_contrib.mod', on Red Hat 9, 11 November 2026; binaries.yml's own comment calls it SPRAL's
    "Fortran-module parallel-build race" and leaves SPRAL out of its native and macOS builds); in the file order a
    serial make follows (Makefile.am's libspral_a_SOURCES), both modules come before their users;
  - SWIG_IMPORT on by default (binaries.yml's swig job does the same with sed before packing the source, after it has
    generated the wrappers: the generation step here passes -DSWIG_IMPORT=OFF, else CMake looks for the wrappers it is
    to generate and stops with "No SOURCES given to target: _casadi", found on Red Hat 9 on 11 November 2026).

Everything else is CasADi's: the same images (ghcr.io/casadi/ci-swig for the SWIG sources, ghcr.io/jgillis/
manylinux_2_28-x64:production for the build), the same build_flags (read from binaries.yml at the tag, so every plugin
of PyPI's wheel), the solver mockups (github.com/casadi/mockups at v111, built from source here: their release zip is a
github.com download, not reachable from the build machine), the grafting of the runtime libraries into the package
(github.com/jgillis/universal_grafter: jgillis's auditwheel fork renames libgomp, libgfortran and the others with hashed
names, as in PyPI's wheel) and the wheel packer (misc/create_wheel_local.py). The wheel's version is 3.8.1+spral.omp, so
pip and the run manifest tell it from PyPI's.

    python tools/solvers/build_casadi_spral_omp_wheel.py WORKDIR [--jobs N]

Needs a container engine (Docker, or podman: Red Hat's, used as docker; SELinux's relabelling of the bind mounts is
added when it is enforcing), git, Python 3, and network access to github.com (git), ghcr.io, coin-or-tools.github.io (CasADi's MUMPS
and METIS 4 sources) and gitlab.com (Eigen). The steps leave stamp files in WORKDIR/stamps and are skipped when there;
the build takes hours on two cores and about 8 GB of disk (the images 7 GB more). Tested on 1 November 2026 up to the
core build's first external projects (sources, SWIG, mockups, the start of the core); the python, graft and wheel
steps follow binaries.yml and universal_grafter but have not run yet. The wheel is written to WORKDIR/dist. Not committed; the
library inside it is loaded by CasADi itself, so supply.nlp_ipopt_library stays "" with it and
supply.nlp_linear_solver = "spral" selects SPRAL (capri_mod/utils/ipopt_library.py's OpenMP rules apply: the threads
of a process that forks its workers).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASADI_TAG = "3.8.1"
#: the mockups release CasADi 3.8.1 (16 September 2026) was built against: binaries.yml uses casadi/mockups@master, whose
#: action downloaded v111 then; v114 on (15 October 2026) regenerated the WORHP mockup without Params.ScaledKKT, which
#: 3.8.1's worhp_interface.cpp l. 409 reads (the build stopped there on Red Hat 9, 11 November 2026). The build_flags'
#: WITH_MOCKUP_* make the core build clone and build the mockups itself too (CMakeLists.txt l. 1231-1324, its
#: BUILD_MOCKUPS_VERSION defaulting to master), and its WORHP plugin compiles against that copy: the tag is passed there
MOCKUPS_TAG = "v111"
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


def engine() -> str:
    """The container engine: docker, or podman (Red Hat's; its command line is docker's)."""
    import shutil
    for e in ("docker", "podman"):
        if shutil.which(e):
            return e
    sys.exit("no container engine: install podman (dnf install podman) or docker")


def _selinux() -> bool:
    try:
        return Path("/sys/fs/selinux/enforce").read_text().strip() == "1"
    except OSError:
        return False


def docker(work: Path, image: str, script: str, log: Path):
    z = ":Z" if _selinux() else ""             # SELinux (Red Hat): the bind mounts relabelled for the container
    env = []
    for k in PASS_ENV:
        if os.environ.get(k):
            env += ["-e", f"{k}={os.environ[k]}"]
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("CURL_CA_BUNDLE")
    mounts = ["-v", f"{work}:/work{z}"]
    if ca and os.path.isfile(ca):
        mounts += ["-v", f"{ca}:/ca.crt:ro{',Z' if z else ''}"]
        env += ["-e", "SSL_CERT_FILE=/ca.crt", "-e", "CURL_CA_BUNDLE=/ca.crt", "-e", "GIT_SSL_CAINFO=/ca.crt",
                "-e", "REQUESTS_CA_BUNDLE=/ca.crt"]
    sh([engine(), "run", "--rm", "--network", "host", *env, *mounts, "-w", "/work", image, "bash", "-ec", script],
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
        y = (work / "casadi" / ".github" / "workflows" / "binaries.yml").read_text()
        flags = re.search(r'^  build_flags: "([^"]+)"', y, re.M).group(1)
        (work / "build_flags.txt").write_text(flags + "\n")
        done(work, "sources")

    # the patch, applied over CasADi's own CMakeLists.txt (again when it has changed since an earlier run, whose patch
    # git checkout takes away); the core build and the steps after it are then repeated
    patch = HERE / "casadi_3.8.1_spral_openmp.patch"
    digest = hashlib.sha256(patch.read_bytes()).hexdigest()
    patchfile = work / "stamps" / "patch_sha256"
    if not patchfile.exists() or patchfile.read_text().strip() != digest:
        sh(["git", "checkout", "--", "CMakeLists.txt"], cwd=work / "casadi", log=log)
        sh(["git", "apply", patch], cwd=work / "casadi", log=log)
        patchfile.write_text(digest + "\n")
        for st in ("core", "python", "graft", "wheel"):
            (work / "stamps" / st).unlink(missing_ok=True)

    wrapper = work / "casadi" / "swig" / "python" / "target3" / "source" / "casadiPYTHON_wrap_gil_release.cxx"
    if not stamp(work, "swig") or not wrapper.exists():
        # binaries.yml's swig job (Python 3, GIL release on, as the build's flags), with SWIG_IMPORT off: the patch
        # has switched its default on already (binaries.yml switches it after this step)
        docker(work, SWIG_IMAGE, "cd casadi && rm -rf build_swig && mkdir build_swig && cd build_swig && cmake "
               "-DWITH_SELFCONTAINED=ON -DWITH_PYTHON=ON -DSWIG_EXPORT=ON -DSWIG_IMPORT=OFF -DWITH_COMMON=OFF "
               "-DWITH_PYTHON_GIL_RELEASE=ON .. && make python_source && cd .. && rm -rf build_swig", log)
        if not wrapper.exists():
            sys.exit(f"the SWIG step did not write {wrapper}: see {log}")
        done(work, "swig")

    tagfile = work / "stamps" / "mockups_tag"
    stale = tagfile.read_text().strip() != MOCKUPS_TAG if tagfile.exists() else stamp(work, "mockups")
    if (work / "mockups").exists() and stale:
        # an earlier run's mockups of another release: cloned and built again
        for d in (work / "mockups", work / "mockups_install"):
            shutil.rmtree(d, ignore_errors=True)
        (work / "stamps" / "mockups").unlink(missing_ok=True)
    if not (work / "mockups").exists():
        sh(["git", "clone", "--depth", "1", "-b", MOCKUPS_TAG, "https://github.com/casadi/mockups", "mockups"],
           cwd=work, log=log)
    if not stamp(work, "mockups"):
        docker(work, BUILD_IMAGE, "cd mockups && cmake -B build_mock -DCMAKE_BUILD_TYPE=Release "
               "-DCMAKE_INSTALL_PREFIX=/work/mockups_install . && cmake --build build_mock -j2 "
               "&& cmake --install build_mock", log)
        done(work, "mockups")
        tagfile.write_text(MOCKUPS_TAG + "\n")

    if not stamp(work, "core"):
        # binaries.yml's core-dockcross job, the core's own mockups at MOCKUPS_TAG (an earlier run's copy of another
        # release removed, so that it is cloned again)
        core_tag = work / "stamps" / "core_mockups_tag"
        clean = "" if core_tag.exists() and core_tag.read_text().strip() == MOCKUPS_TAG else (
            "rm -rf build/external_projects/src/mockups-external build/external_projects/src/mockups-external-build "
            "build/external_projects/src/mockups-external-stamp build/external_projects/mockups && ")
        docker(work, BUILD_IMAGE, f"cd casadi && {clean}rm -f build/CMakeCache.txt && cmake -Bbuild "
               "-DCMAKE_BUILD_TYPE=Release -DWITH_SELFCONTAINED=ON $(cat /work/build_flags.txt) "
               f"-DBUILD_MOCKUPS_VERSION={MOCKUPS_TAG} -DCMAKE_PREFIX_PATH=/work/mockups_install/cmake "
               f"-H. && cmake --build build -j{a.jobs}", log)
        core_tag.write_text(MOCKUPS_TAG + "\n")
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
        # (the action runs chrpath -r '$ORIGIN' on its host; the image has patchelf: the same RPATH where one is set)
        docker(work, BUILD_IMAGE, "cd install/casadi && for f in *; do [ -f \"$f\" ] && r=$(patchelf --print-rpath "
               "\"$f\" 2>/dev/null) && [ -n \"$r\" ] && patchelf --force-rpath --set-rpath '$ORIGIN' \"$f\" || true; "
               "done && rm -f spral_ssids && /opt/python/cp39-cp39/bin/pip install -q pyelftools wheel==0.31.1 && "
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
