"""Can the load exponent of the support stiffness be identified, and does clearance growth move it enough?

Bound: 4-wheel rail-coupled headline design (BS113A, kf 154e6, debiased Whittle), payload uniform over
W_RANGE, speeds 60-110 km/h, SNR 40 dB, N = 50 and 200, globals (k_B0, c_B, p) with the power law
k_B = k_B0 (W/W0)^p (bearing.stiffness_law = power). Expected-Fisher CRB of p in absolute units,
evaluated at p = 0.1 (config) and at the effective exponent of the series model (reading B).

Signal: series model (reading B; bearing.stiffness_law = series, k_housing set so the total at W0, c_d0
is the config nominal 1e9 N/m, a placeholder): effective exponent p_eff = least-squares slope of ln k_B against ln W over the payload
range, at clearance growth 0, 10 and 20 um. Shift dp = p_eff(g) - p_eff(0).

Detection of a shift between a baseline and a later period of N passes each: the difference of two
independent estimates has sd sqrt(2) CRB_p; one-sided 5% false alarm and 90% detection need
dp >= (1.645 + 1.282) sqrt(2) CRB_p. Writes results/p3/exponent_bound.json.
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

from experiments.p1_fe_direct import TRUTH, W_RANGE, WIM  # noqa: E402
from experiments.p2_common import setup  # noqa: E402
from experiments.p2_multiwheel import dataset, models  # noqa: E402
from src.analysis.multiwheel import MultiWheelFamily  # noqa: E402
from src.inverse.multipass import MultiPassWhittle  # noqa: E402
from src.reference.params import Params, load_raw  # noqa: E402
from src.utils.results import Timer, save_result  # noqa: E402

GROWTH = (0.0, 10.0, 20.0)
Z_DET = 1.645 + 1.2816


def series_exponents():
    raw = load_raw()
    raw["bearing"]["stiffness_law"]["value"] = "series"
    P = Params(raw)
    Wg = np.linspace(*W_RANGE, 41)
    out = {}
    for g in GROWTH:
        k = np.array([P.kB(P.v["bearing"]["kB0"], W, clearance_growth_um=g) for W in Wg])
        slope = float(np.polyfit(np.log(Wg), np.log(k), 1)[0])
        out[g] = {"p_eff_lsq": slope, "p_eff_two_point": float(math.log(k[-1] / k[0]) / math.log(Wg[-1] / Wg[0])),
                  "kB_at_W0_rel": float(k[-1] / P.v["bearing"]["kB0"]), "kB_empty": float(k[0]), "kB_loaded": float(k[-1])}
    pc = P._k_contact(W_RANGE[1], 0.0)
    return out, {"k_contact_W0": pc, "k_housing": 1 / (1 / P.v["bearing"]["kB0"] - 1 / pc), "kB0_nominal": P.v["bearing"]["kB0"]}


def main():
    sig, ser = series_exponents()
    print(sig, ser, flush=True)
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    rows = []
    with Timer() as tm:
        for p in (0.1, sig[0.0]["p_eff_lsq"]):
            fam = MultiWheelFamily(mw, dict(thb, load_exp=p), names=("kB0", "cB", "load_exp"))
            fam2 = MultiWheelFamily(mw, dict(thb, load_exp=p), names=("kB0", "cB"))
            for N in (50, 200):
                P, Wm, Ws, g = dataset(sm, dict(thb, load_exp=p), rough, mw, (20261013, N), N=N, g_sd=0.0)
                est = MultiPassWhittle(P, Wm, WIM, rough, fam, debias=True)
                c = est.expected_fisher(np.log([TRUTH["kB0"], TRUTH["cB"], p]), np.zeros(est.S), np.log(Ws))
                est2 = MultiPassWhittle(P, Wm, WIM, rough, fam2, debias=True)
                c2 = est2.expected_fisher(np.log([TRUTH["kB0"], TRUTH["cB"]]), np.zeros(est2.S), np.log(Ws))
                crb_p = p * c["crb_log"][2]
                row = {"p_true": p, "N": N, "snr_db": 40.0, "crb_p_abs": crb_p, "crb_kB0_rel_p_free": c["crb_log"][0],
                       "crb_kB0_rel_p_fixed": c2["crb_log"][0], "mdc_dp_two_periods": Z_DET * math.sqrt(2) * crb_p}
                for gr in GROWTH[1:]:
                    dp = sig[gr]["p_eff_lsq"] - sig[0.0]["p_eff_lsq"]
                    row[f"dp_{int(gr)}um"] = dp
                    row[f"z_single_{int(gr)}um"] = abs(dp) / crb_p
                    row[f"detectable_two_periods_{int(gr)}um"] = bool(abs(dp) >= row["mdc_dp_two_periods"])
                rows.append(row)
                print(row, flush=True)
    save_result("p3/exponent_bound", {"series_signal": {str(k): v for k, v in sig.items()}, "series_model": ser, "rows": rows},
                cfg={"design": "4-wheel rail-coupled, N passes, 60-110 km/h, payload uniform W_RANGE, 40 dB, roughness levels free",
                     "payload_t": list(W_RANGE), "wim_sigma": WIM, "growth_um": list(GROWTH),
                     "detection": "one-sided 5% false alarm, 90% detection, two periods"}, seed=20261013, wall_seconds=tm.seconds)


if __name__ == "__main__":
    main()
