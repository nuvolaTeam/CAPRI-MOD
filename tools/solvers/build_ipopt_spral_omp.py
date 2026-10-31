"""IPOPT with SPRAL in OpenMP, for CasADi's IPOPT interface (supply.nlp_ipopt_library; register BEYOND-11).

CasADi's wheel carries IPOPT with SPRAL built without OpenMP (CasADi 3.8.1's CMakeLists.txt configures SPRAL with
--disable-openmp), so SPRAL factorises on one thread there. This script builds the same IPOPT with SPRAL's OpenMP
factorisation into a folder of its own, outside the repository (the binaries are not committed):

  1. GKlib and METIS 5.2.1 (KarypisLab), 32-bit indices, without -march=native (portable binaries), one static archive
  2. OpenBLAS 0.3.30 with OpenMP (USE_OPENMP=1: the same OpenMP runtime as SPRAL, so BLAS called inside SPRAL's
     parallel regions runs on the calling thread, no second thread pool), every x86-64 kernel (DYNAMIC_ARCH=1),
     static
  3. SPRAL v2025.09.18 (ralna) with OpenMP, static, without GPU (hwloc where the system has it)
  4. IPOPT 3.14.19.mod, the source CasADi 3.8.1 builds (github.com/jgillis/Ipopt-1: IPOPT 3.14.19 with two fixes,
     an array one element longer in IpTSymLinearSolver and RTLD_DEEPBIND when loading an HSL library), with SPRAL as its
     linear solver and the run-time loader of HSL libraries; no MUMPS (CasADi's own IPOPT keeps it)

Everything is compiled by the system's gcc, g++ and gfortran, and the result needs only the system's runtime
libraries (libgfortran, libgomp, libquadmath, libstdc++): no runtime library of CasADi's wheel is mixed in. The static
OpenBLAS, METIS and SPRAL are linked into libipopt with their symbols hidden (--exclude-libs), so other libraries in
the process (CasADi's MUMPS with its METIS 4, numpy's and scipy's OpenBLAS) cannot bind to them;
capri_mod/supply/ipopt_library.py loads the library RTLD_LOCAL | RTLD_DEEPBIND so its own calls go to its own runtimes.

    python tools/solvers/build_ipopt_spral_omp.py [--prefix DIR] [--jobs N]

Built on the machine that runs it, against that machine's runtime libraries under their own names. Shipped to other
machines as a binary (a wheel or a package), it would have to go through auditwheel repair in a manylinux container
instead: libgomp and libgfortran renamed and carried with it, as CasADi's wheel does, and a glibc baseline older than
this machine's (a build on Ubuntu 24.04 needs glibc 2.39 or newer).

The default prefix is ~/capri-solvers/ipopt-spral-omp; the library is PREFIX/lib/libipopt.so.3, the value to give
supply.nlp_ipopt_library. Needs git (the sources come from GitHub), make, cmake, meson (pip install meson), ninja, gcc,
g++, gfortran. Each step leaves a stamp file in PREFIX/stamps and is skipped when it is there; --clean removes the
build folder first. Linux only (the library loading of capri_mod/supply/ipopt_library.py is Linux's).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

#: the sources: (folder, git repository, tag)
SOURCES = {
    "GKlib": ("https://github.com/KarypisLab/GKlib", "METIS-v5.1.1-DistDGL-0.5"),
    "METIS": ("https://github.com/KarypisLab/METIS", "v5.2.1"),
    "OpenBLAS": ("https://github.com/OpenMathLib/OpenBLAS", "v0.3.30"),
    "spral": ("https://github.com/ralna/spral", "v2025.09.18"),
    "Ipopt": ("https://github.com/jgillis/Ipopt-1", "3.14.19.mod"),
}
TOOLS = ("git", "make", "cmake", "meson", "ninja", "gcc", "g++", "gfortran", "ar", "nm", "ldd")


def run(cmd, cwd, log, env=None):
    print("  $", " ".join(str(c) for c in cmd), flush=True)
    with open(log, "a", encoding="utf-8") as fh:
        fh.write("\n$ " + " ".join(str(c) for c in cmd) + "\n")
        fh.flush()
        r = subprocess.run([str(c) for c in cmd], cwd=cwd, stdout=fh, stderr=subprocess.STDOUT,
                           env={**os.environ, **(env or {})})
    if r.returncode:
        sys.exit(f"failed ({r.returncode}): see {log}")


def step(prefix: Path, name: str):
    """True when the step is still to do (no stamp file)."""
    return not (prefix / "stamps" / name).exists()


def done(prefix: Path, name: str):
    (prefix / "stamps").mkdir(parents=True, exist_ok=True)
    (prefix / "stamps" / name).write_text("done\n")


def fetch(src: Path, log: Path):
    for d, (url, tag) in SOURCES.items():
        if not (src / d).exists():
            run(["git", "clone", "--depth", "1", "-b", tag, url, d], src, log)


def build_metis(src: Path, prefix: Path, jobs: int, log: Path):
    if step(prefix, "gklib"):
        run(["make", "config", f"prefix={prefix}"], src / "GKlib", log)
        run(["make", f"-j{jobs}", "install"], src / "GKlib", log)
        done(prefix, "gklib")
    if step(prefix, "metis"):
        m = src / "METIS"
        conf = m / "conf" / "gkbuild.cmake"
        t = conf.read_text()
        conf.write_text(t.replace('  set(GK_COPTIONS "${GK_COPTIONS} -march=native")',
                                  "  # -march=native left out (portable binaries)"))
        run(["make", "config", f"gklib_path={prefix}", f"prefix={prefix}"], m, log)   # 32-bit idx_t and real_t
        run(["make", f"-j{jobs}", "install"], m, log)
        lib = prefix / "lib"
        # METIS's archive needs GKlib's symbols: one archive with both (SPRAL's build links one library for METIS)
        (lib / "libmetis.a").rename(lib / "libmetis_only.a")
        subprocess.run(["ar", "-M"], cwd=lib, check=True, text=True,
                       input="create libmetis.a\naddlib libmetis_only.a\naddlib libGKlib.a\nsave\nend\n")
        done(prefix, "metis")


def build_openblas(src: Path, prefix: Path, jobs: int, log: Path):
    if step(prefix, "openblas"):
        opts = ["USE_OPENMP=1", "DYNAMIC_ARCH=1", "NO_SHARED=1", "NO_LAPACKE=1", "NUM_THREADS=64", "NO_AFFINITY=1"]
        run(["make", f"-j{jobs}", *opts, "libs", "netlib"], src / "OpenBLAS", log)
        run(["make", *opts, f"PREFIX={prefix}", "install"], src / "OpenBLAS", log)
        done(prefix, "openblas")


def build_spral(src: Path, prefix: Path, jobs: int, log: Path):
    if step(prefix, "spral"):
        s = src / "spral"
        lib = prefix / "lib"
        run(["meson", "setup", "build", f"--prefix={prefix}", "--buildtype=release", "-Ddefault_library=static",
             "-Db_staticpic=true", "-Dtests=false", "-Dexamples=false", "-Dmodules=false", "-Dgpu=false",
             "-Dopenmp=true", "-Dlibblas=openblas", "-Dliblapack=openblas", f"-Dlibblas_path={lib}",
             f"-Dliblapack_path={lib}", "-Dlibmetis=metis", f"-Dlibmetis_path={lib}", "-Dlibmetis_version=5"],
            s, log)                                  # hwloc where the system has it (optional for SPRAL)
        run(["meson", "compile", "-C", "build", "-j", str(jobs)], s, log)
        run(["meson", "install", "-C", "build"], s, log)
        done(prefix, "spral")


def build_ipopt(src: Path, prefix: Path, jobs: int, log: Path):
    if step(prefix, "ipopt"):
        i = src / "Ipopt"
        b = i / "build"
        b.mkdir(exist_ok=True)
        lib = prefix / "lib"
        rt = "-lgfortran -lquadmath -lgomp -lm"
        run([i / "configure", f"--prefix={prefix}", "--disable-java", "--disable-sipopt", "--without-asl",
             "--without-mumps", "--without-hsl",
             f"--with-lapack-lflags=-L{lib} -lopenblas {rt}",
             f"--with-spral-cflags=-I{prefix / 'include'}",
             f"--with-spral-lflags=-L{lib} -lspral -lmetis -lopenblas {rt} -lstdc++",
             # the static OpenBLAS, METIS and SPRAL inside libipopt with their symbols hidden: nothing else in the
             # process binds to them (CasADi's MUMPS has its own METIS 4 under the same names)
             "LDFLAGS=-fopenmp -Wl,--exclude-libs,ALL"], b, log)
        run(["make", f"-j{jobs}"], b, log)
        run(["make", "install"], b, log)
        done(prefix, "ipopt")


def check(prefix: Path):
    """The library's soname and its linked libraries: IPOPT's, no runtime library of CasADi's wheel."""
    so = prefix / "lib" / "libipopt.so.3"
    if not so.exists():
        sys.exit(f"{so} was not built")
    out = subprocess.run(["ldd", so], capture_output=True, text=True).stdout
    print(out)
    bad = [l for l in out.splitlines() if "casadi" in l or "not found" in l]
    if bad:
        sys.exit("unexpected libraries: " + "; ".join(bad))
    # the hidden symbols: libipopt exports IPOPT's own, not BLAS's, METIS's or SPRAL's
    syms = subprocess.run(["nm", "-D", "--defined-only", so], capture_output=True, text=True).stdout.split()
    leaked = sorted({s for s in syms if s in ("dgemm_", "dpotrf_", "METIS_NodeND", "spral_ssids_factor",
                                                "spral_ssids_analyse")})
    if leaked:
        sys.exit("symbols not hidden: " + ", ".join(leaked))
    print(f"built {so}: supply.nlp_ipopt_library = \"{so}\"")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prefix", type=Path, default=Path.home() / "capri-solvers" / "ipopt-spral-omp")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--clean", action="store_true", help="remove the build folder (the sources) first")
    a = ap.parse_args()
    if not sys.platform.startswith("linux"):
        sys.exit("Linux only")
    missing = [t for t in TOOLS if shutil.which(t) is None]
    if missing:
        sys.exit("missing build tools: " + ", ".join(missing) + " (meson: pip install meson)")
    prefix = a.prefix.expanduser().resolve()
    src = prefix / "build"
    if a.clean and src.exists():
        shutil.rmtree(src)
    src.mkdir(parents=True, exist_ok=True)
    log = prefix / "build.log"
    print(f"building into {prefix} (log {log})")
    fetch(src, log)
    build_metis(src, prefix, a.jobs, log)
    build_openblas(src, prefix, a.jobs, log)
    build_spral(src, prefix, a.jobs, log)
    build_ipopt(src, prefix, a.jobs, log)
    check(prefix)


if __name__ == "__main__":
    main()
