"""P1.6: identifiability early warning. Writes results/p1/sensitivity.json. Single-threaded."""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reference.frequency_domain import ForcingMap  # noqa: E402
from src.reference.params import load_params  # noqa: E402
from src.reference.sensitivity import fisher_crb, log_sensitivities, modal_map, pi_over_prior  # noqa: E402
from src.reference.timoshenko_fe import L1LinModel  # noqa: E402
from src.utils.results import Timer, save_result  # noqa: E402


def main() -> None:
    p = load_params()
    mdl, fm = L1LinModel(p), ForcingMap(p)
    b, pay = p.v["bearing"], p.v["payload"]
    k0, c0, Wl, We = b["kB0"], b["cB"], pay["W_max"], pay["W_min"]
    with Timer() as tm:
        corners = {
            "nominal_loaded": (k0, c0, Wl), "nominal_empty": (k0, c0, We),
            "soft_x0.5_loaded": (0.5 * k0, c0, Wl), "stiff_x2_loaded": (2 * k0, c0, Wl),
        }
        modes = {k: modal_map(mdl, *v, n_modes=8) for k, v in corners.items()}
        sens = log_sensitivities(mdl, fm, k0, c0, Wl)
        crb = {}
        for snr in (20.0, 40.0):
            for N in (20, 50, 200):
                crb[f"snr{int(snr)}_N{N}_W_known"] = fisher_crb(p, mdl, fm, k0, c0, Wl, N, snr)
                crb[f"snr{int(snr)}_N{N}_W_unknown"] = fisher_crb(p, mdl, fm, k0, c0, Wl, N, snr,
                                                                  params=("log_kB0", "log_cB", "log_W"))
        pi = pi_over_prior(p, mdl, n=400, seed=7)
    g3 = crb["snr40_N50_W_known"]["crb_std"]
    payload = {
        "freq_hz": (fm.omegas / (2 * math.pi)).tolist(),
        "modal_map": modes,
        "log_sensitivity_nominal_loaded": {k: np.asarray(v).tolist() for k, v in sens.items()},
        "max_abs_dlogpower_dlogkB0": float(np.max(np.abs(sens["log_kB0"]))),
        "max_abs_dlogpower_dlogcB": float(np.max(np.abs(sens["log_cB"]))),
        "max_abs_dlogpower_dlogW": float(np.max(np.abs(sens["log_W"]))),
        "crb": crb,
        "G3_feasibility_snr40_N50_W_known": {"crb_rel_std_kB0": g3[0], "crb_rel_std_cB": g3[1],
                                             "target_kB0": 0.05, "target_cB": 0.15,
                                             "note": "CRB on log-parameters ~ relative std; a lower bound for any unbiased estimator"},
        "Pi_over_prior": pi,
        "band_max_hz": p.v["sensor"]["band_max"],
    }
    save_result("p1/sensitivity", payload, cfg={"threads": 1}, wall_seconds=tm.seconds)
    print("modes nominal:", [(round(m["f_hz"], 1), round(m["axlebox_ke_frac"], 3), m["symmetric"]) for m in modes["nominal_loaded"]])
    print("dlogP/dlogkB0:", np.round(sens["log_kB0"], 6))
    print("dlogP/dlogcB :", np.round(sens["log_cB"], 8))
    print("dlogP/dlogW  :", np.round(sens["log_W"], 6))
    print("CRB snr40 N50 W known:", g3, "| W unknown:", crb["snr40_N50_W_unknown"]["crb_std"])
    print("Pi over prior:", np.round(pi["Pi"], 3), "freq CoV", np.round(pi["freq_cov_s"], 4), "zeta", np.round(pi["zeta_median"], 4))


if __name__ == "__main__":
    main()
