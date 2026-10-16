"""Two-period detection limits at the current configuration (bound-based).

For N = 50 and 200 passes per period and SNR 20 and 40 dB: the Cramer-Rao bound of log k_B0 for the
co-estimating fit (k_B0, c_B, k_f, k_H0 free; 4-wheel rail-coupled model, config nominal, 60-110 km/h,
payload 5.5-22.5 t, roughness levels free, debiased likelihood, expected Fisher information) and the
minimum detectable decrease between two periods, one-sided 5% false alarm and 90% detection,
MDC = exp(-(1.645 + 1.282) sqrt(2) CRB) -> reported as a percentage decrease (same as mdc_under with no
bias). Writes results/p4/mdc_bounds.json, read by experiments/p3_calibrated.py.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p2_common import WIM, setup  # noqa: E402
from experiments.p2_multiwheel import dataset as mw_dataset, models  # noqa: E402
from experiments.p2_relative_coest_drift import EST, SPEEDS, families, mdc_under, phi  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.utils.results import save_result  # noqa: E402


def main():
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    fams = families(mw, thb)
    rows = []
    for N in (50, 200):
        for snr in (20.0, 40.0):
            P, Wm, Ws, g = mw_dataset(sm, thb, rough, mw, (43, N, int(snr)), N=N, snr=snr, speeds=SPEEDS, g_sd=0.0)
            for e in ("nominal", "coest"):
                est = MultiPassWhittle(P, Ws, WIM, rough, fams[e], debias=True)
                crb = est.expected_fisher(phi(EST[e]), np.zeros(est.S), est.lw_meas.copy())["crb_log"][0]
                s0 = math.sqrt(2) * crb
                rows.append({"N": N, "snr_db": snr, "estimator": e, "crb_kB0_pct": 100 * crb, "mdc_pct": mdc_under(0.0, 0.0, s0)})
                print(rows[-1], flush=True)
    save_result("p4/mdc_bounds", {"rows": rows}, cfg={"model": "4-wheel rail-coupled, config nominal", "speeds_kmh": SPEEDS,
                                                     "test": "one-sided decrease, alpha 0.05, detection 90%"}, seed=43)


if __name__ == "__main__":
    main()
