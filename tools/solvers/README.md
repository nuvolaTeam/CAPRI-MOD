# CasADi with SPRAL in OpenMP: building it yourself (Red Hat 9)

PyPI's CasADi 3.8.1 builds IPOPT's SPRAL solver without OpenMP, so SPRAL runs on one thread. These instructions
build CasADi 3.8.1 the way CasADi builds its own PyPI wheel, with one change: SPRAL is compiled with OpenMP. The
result is a wheel you install with pip in place of PyPI's CasADi.

- Script: `build_casadi_spral_omp_wheel.py`.
- Patch: `casadi_3.8.1_spral_openmp.patch`.
- Status: on Red Hat 9 the steps have run through the sources, SWIG and most of the core build (to 84%, in parallel
  runs that stopped at the problems fixed below; not yet rerun with the fixes). The Python, graft and wheel steps follow
  CasADi's release workflow but have not been run end to end.
  If a step fails, the log says which one, and running the script again resumes there.
- Fixed on 11 November 2026, from your Red Hat logs:
  - SWIG step: "No SOURCES given to target: _casadi" (the patch switches SWIG_IMPORT on before the wrappers exist; the
    step now passes `-DSWIG_IMPORT=OFF`, as CasADi's workflow generates them before switching it).
  - WORHP plugin: `Params` has no `ScaledKKT`. The solver mockups' master branch (v114 on) dropped it. With the build
    flags' `WITH_MOCKUP_*`, the core build clones the mockups itself, and the script now passes
    `-DBUILD_MOCKUPS_VERSION=v111` (the release CasADi 3.8.1 was built against) and removes an earlier run's copy.
    The separate mockups build is still needed: the MATLAB IPC plugin finds its MATLAB mockup there (the run without
    it stopped at "MATLAB not found"). It is now cloned, built and installed inside the container, into
    `mockups_v111` and `mockups_v111_install`: an earlier run's `mockups` folder, most likely only partly removed by
    the host (files the container wrote are root's), had stopped a run with "/work/mockups does not appear to
    contain CMakeLists.txt".
  - SPRAL: "Cannot open module file 'spral_matrix_util.mod'", then 'spral_ssids_contrib.mod'. SPRAL's Makefile misses
    module dependencies (CasADi's workflow calls it a known parallel-build race). The patch builds SPRAL with
    `make -j1`, and the whole build is now serial by default, as CasADi's.
  - The script applies a changed patch again by itself and repeats the core build. Rerun the same command on the
    same work folder; the old `mockups` and `mockups_install` folders there (without the `_v111`) are no longer
    used and can be deleted (with `sudo` if the container wrote them as root).

## What you need

- Red Hat 9, x86-64 (the wheel needs glibc 2.28 or newer; Red Hat 9 has 2.34).
- `sudo dnf install -y git podman python3`. podman is Red Hat's container engine and the script uses it like Docker;
  Docker also works.
- About 15 GB of free disk: 7 GB for the two build images, about 8 GB for the build.
- Network access to:
  - `github.com` (git clones);
  - `ghcr.io` and `pkg-containers.githubusercontent.com` (the build images);
  - `coin-or-tools.github.io` (MUMPS and METIS sources);
  - `gitlab.com` (Eigen);
  - `pypi.org` and `files.pythonhosted.org` (two small tools inside the container).
- Time: several hours (the build is serial by default, as CasADi's own workflow runs it).

## Steps

1. Put the two files in one folder; the script reads the patch from beside itself:

   ```
   mkdir -p ~/casadi-omp && cd ~/casadi-omp
   # copy build_casadi_spral_omp_wheel.py and casadi_3.8.1_spral_openmp.patch here
   ```

2. Run the build:

   ```
   python3 build_casadi_spral_omp_wheel.py ~/casadi-omp/work
   ```

   It builds serially, as CasADi's own release workflow does (`cmake --build` without `-j`). `--jobs N` runs N jobs
   in parallel and is faster, but leaves the path CasADi tests: some external projects' Makefiles miss dependencies
   (SPRAL's did, and the patch now builds SPRAL serially in any case).

   The script:
   - clones CasADi 3.8.1 and its library grafter, and applies the patch;
   - builds CasADi's solver mockups (v111) for the MATLAB IPC plugin;
   - pulls `ghcr.io/casadi/ci-swig` and `ghcr.io/jgillis/manylinux_2_28-x64:production`, CasADi's own build images;
   - generates the Python wrappers, builds the core with every plugin of PyPI's wheel (the core clones and builds the
     solver mockups itself, pinned to v111), and the Python 3.11 limited-API module;
   - grafts the runtime libraries (libgomp, libgfortran, ...) into the package under renamed names, as PyPI's wheel
     has them, and packs the wheel.

   Progress and errors go to `~/casadi-omp/work/build.log`. Each finished step leaves a file in
   `~/casadi-omp/work/stamps`, so a rerun skips it. With SELinux enforcing, the script adds `:Z` to its bind mounts.

3. The wheel is `~/casadi-omp/work/dist/casadi-3.8.1+spral.omp-cp311-abi3-manylinux_2_28_x86_64.whl` (Python 3.11 or
   newer). Install it in the environment that runs capri-mod:

   ```
   pip install --force-reinstall --no-deps ~/casadi-omp/work/dist/casadi-3.8.1+spral.omp-*.whl
   ```

4. Check that SPRAL runs with OpenMP:

   ```
   python3 - <<'EOF'
   import os
   os.environ.update(OMP_CANCELLATION="TRUE", OMP_NUM_THREADS="2")   # read by OpenMP when CasADi loads IPOPT
   import casadi as ca
   x = ca.MX.sym("x", 2000)
   S = ca.nlpsol("S", "ipopt", {"x": x, "f": ca.sumsqr(x - 1) + ca.sumsqr(x[1:] - x[:-1]), "g": ca.sum1(x)},
                 {"ipopt.linear_solver": "spral", "ipopt.print_level": 0, "print_time": 0})
   r = S(x0=0, lbg=1, ubg=1)
   print(S.stats()["return_status"], ca.__version__)
   print([l.split()[-1] for l in open("/proc/self/maps") if "libgomp" in l][:1])
   EOF
   ```

   It should print `Solve_Succeeded 3.8.1+spral.omp` and a libgomp inside CasADi's folder.

5. In capri-mod's settings (a file passed with `--settings`, or `--set supply.nlp_linear_solver=spral` and so on); the
   model sets the OpenMP environment itself (capri_mod/utils/ipopt_library.py), nothing to export:

   ```
   [supply]
   nlp_linear_solver = "spral"
   nlp_omp_threads = 2        # per worker process; workers x threads should not exceed your cores
   nlp_ipopt_library = ""     # CasADi's own IPOPT is the OpenMP one
   ```

   The main process stays on one thread whenever it forks workers, and the workers take `nlp_omp_threads`. GNU OpenMP
   hangs forked children of a process that has run on several threads, so this rule is needed.

To go back to PyPI's build: `pip install --force-reinstall casadi==3.8.1`.

## A smaller alternative

`build_ipopt_spral_omp.py` builds only IPOPT 3.14.19 with SPRAL in OpenMP (METIS 5, OpenBLAS), natively, with no
container, in about an hour. capri-mod loads it next to PyPI's CasADi through `supply.nlp_ipopt_library`. It needs
`gcc-c++ gcc-gfortran cmake ninja-build make git`, meson from pip, and on Red Hat the CodeReady Builder repository
for some of them. A library built this way works on the machine that built it.
