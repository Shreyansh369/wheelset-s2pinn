"""G1: verification of the L1-lin reference solver. Writes results/p1/verification.json.

Checks (thresholds in config/gates.yaml):
  a) FE free-free frequencies of a uniform Timoshenko beam vs the exact frequency equation;
  b) windowed energy-balance residual (doc Eq. 28) of the frequency-domain solution;
  c) frequency-domain vs Newmark time integration on 3 cases.
Also: mesh convergence of the stepped axle (20/32/40 elements), an extra rail_sdof case,
and the gyroscopic-neglect ratio Omega / omega_1.
Runs single-threaded so a concurrent training job keeps the remaining cores.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import yaml  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reference.params import REPO, load_params  # noqa: E402
from src.reference.verify import fd_cases, fd_td_energy_check, freefree_check, mesh_convergence  # noqa: E402
from src.utils.results import Timer, save_result  # noqa: E402


def main() -> None:
    p = load_params()
    g1 = yaml.safe_load((REPO / "config" / "gates.yaml").read_text())["G1"]
    with Timer() as tm:
        ff = freefree_check(p, d=0.175, L=p.v["axle"]["length"], n_elements=[20, 30, 32, 40])
        cases = [fd_td_energy_check(p, c, T=1.0, dt=2e-5) for c in fd_cases(p)]
        b, pay = p.v["bearing"], p.v["payload"]
        rail_case = fd_td_energy_check(p, {"name": "nominal_loaded_rail_sdof", "kB0": b["kB0"], "cB": b["cB"],
                                           "W": pay["W_max"], "seed": 0, "rail": True}, T=1.0, dt=2e-5)
        mc = mesh_convergence(p, [20, 32, 40])
    w1 = 2 * math.pi * mc["32"]["modes_hz"][0]
    payload = {
        "a_freefree": ff,
        "b_energy": {c["name"]: c["energy"] for c in cases},
        "c_fd_vs_td": {c["name"]: {k: c[k] for k in ("rel_l2_displacement_free_dofs", "rel_l2_axlebox_accel_left",
                                                     "fd_vs_td_rel_l2", "T", "dt", "kB0", "cB", "W")} for c in cases},
        "extra_rail_sdof_case": {"energy": rail_case["energy"], "fd_vs_td_rel_l2": rail_case["fd_vs_td_rel_l2"]},
        "mesh_convergence": mc,
        "gyroscopic_neglect": {"Omega_rad_s": 2 * math.pi * p.f_r, "omega1_constrained_rad_s": w1,
                               "ratio": 2 * math.pi * p.f_r / w1},
        "gate": {
            "a_pass": ff["max_rel_err_all"] <= g1["freefree_timoshenko_rel_err_max"],
            "b_pass": bool(max(c["energy"]["rel_residual"] for c in cases) <= g1["energy_balance_rel_residual_max"]),
            "c_pass": max(c["fd_vs_td_rel_l2"] for c in cases) <= g1["fd_vs_td_rel_l2_max"],
            "a_max_rel_err": ff["max_rel_err_all"],
            "b_max_rel_residual": max(c["energy"]["rel_residual"] for c in cases),
            "c_max_rel_l2": max(c["fd_vs_td_rel_l2"] for c in cases),
            "thresholds": g1,
        },
    }
    save_result("p1/verification", payload, cfg={"params": p.raw, "threads": 1}, wall_seconds=tm.seconds)
    import json

    print(json.dumps(payload["gate"], indent=1, default=float))
    print("gyro ratio", payload["gyroscopic_neglect"]["ratio"])


if __name__ == "__main__":
    main()
