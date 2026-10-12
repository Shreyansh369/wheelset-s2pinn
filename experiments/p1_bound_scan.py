"""Exploratory Cramer-Rao scan of the three candidate forcing/target models (user request, 2026-10-11).

(a) realistic kB0 ~ 1e9, linearised Hertz contact + rail oscillator, band to 700 Hz, short-wave rail
    roughness (EN 15610-style 1/3-octave bands, 4-10 cm) in addition to the existing forcing;
(b) kB0 ~ 1e7 (adapter pad), quasi-static rigid contact, forcing extended to 150 Hz
    (wheel orders 1-15, track irregularity down to 0.2 m);
(d) in-band targets with realistic kB0, Hertz + rail oscillator, band 150 Hz: wheel OOR order
    amplitudes (orders 1-3), r0, and track/rail-pad stiffness k_r via the P2 resonance.
c_B is not a target; the support-mode damping ratio zeta_s replaces it where a support target is used.
Each: CRB at N = 50 passes, SNR 20/40 dB, payload W known and unknown, and Pi over the prior.
Placeholders: roughness level (0 dB re 1 um per band), k_H0, rail oscillator, OOR spectrum std_n = 1e-4/n m.
Writes results/p1/bound_scan.json. Single-threaded. The reference solver is not modified.
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

from src.analysis.bound_scan import Scenario, ScenarioModel, crb_report, p2_mode, pi_over_prior, support_mode  # noqa: E402
from src.reference.params import load_params  # noqa: E402
from src.utils.results import Timer, save_result  # noqa: E402

N_PASSES = 50
LN2 = math.log(2)


def track_wavelengths_clear_of_orders(p, lam_max, lam_min, n, r0, n_orders=15, min_gap_hz=1.0):
    f_r = p.V / (2 * math.pi * r0)
    out = []
    for lam in np.geomspace(lam_max, lam_min, n):
        for _ in range(50):
            f = p.V / lam
            if all(abs(f - k * f_r) >= min_gap_hz for k in range(1, n_orders + 1)):
                break
            lam *= 1.02
        out.append(float(lam))
    return out


def main() -> None:
    p = load_params()
    r0 = p.r0
    base_th = {"kB0": 1e9, "cB": 5e3, "W": 22.5, "k_r": 1e8, "r0": r0, "s_oor1": 1.0, "s_oor2": 1.0, "s_oor3": 1.0}
    oor_std_default = dict(zip(p.v["forcing"]["oor_orders"], p.v["forcing"]["oor_std"]))
    track_150 = track_wavelengths_clear_of_orders(p, 25.0, 0.2, 12, r0)
    spec_150 = {"oor_orders": list(range(1, 16)), "oor_std": lambda n: 1e-4 / n,
                "track_wavelengths": track_150, "track_rel_bin": 0.44}
    scenarios = {
        "a_realistic_kB_hertz_rail_700Hz": (Scenario(
            name="a", kB0=1e9, cB=5e3, contact="hertz_rail", band_hz=700.0, fs=2000.0,
            forcing_spec={"oor_orders": [1, 2, 3], "oor_std": lambda n: oor_std_default[n],
                          "track_wavelengths": p.v["forcing"]["track_wavelengths"], "track_rel_bin": 0.5,
                          "rough_wavelengths": [0.10, 0.08, 0.063, 0.05, 0.04], "rough_level_db": lambda lam: 0.0},
            targets=["log_kB0", "log_cB"]), {"kB0": ("log", LN2, None), "W": ("uni", 5.5, 22.5)}, "support"),
        "b_pad_kB1e7_rigid_150Hz": (Scenario(
            name="b", kB0=1e7, cB=5e3, contact="rigid", band_hz=150.0, fs=1000.0, forcing_spec=spec_150,
            targets=["log_kB0", "log_cB"]), {"kB0": ("log", LN2, None), "W": ("uni", 5.5, 22.5)}, "support"),
        "d_inband_oor_r0_kr_hertz_rail_150Hz": (Scenario(
            name="d", kB0=1e9, cB=5e3, contact="hertz_rail", band_hz=150.0, fs=1000.0, forcing_spec=spec_150,
            targets=["log_s_oor1", "log_s_oor2", "log_s_oor3", "log_r0", "log_k_r"]),
            {"k_r": ("log", LN2, None), "W": ("uni", 5.5, 22.5)}, "p2"),
        "d_plus_support_targets": (Scenario(
            name="d+", kB0=1e9, cB=5e3, contact="hertz_rail", band_hz=150.0, fs=1000.0, forcing_spec=spec_150,
            targets=["log_s_oor1", "log_s_oor2", "log_s_oor3", "log_r0", "log_k_r", "log_kB0", "log_cB"]),
            {"k_r": ("log", LN2, None), "W": ("uni", 5.5, 22.5)}, "p2"),
    }
    out = {}
    with Timer() as tm:
        for key, (sc, prior, which) in scenarios.items():
            th = dict(base_th, kB0=sc.kB0, cB=sc.cB)
            sm = ScenarioModel(p, sc)
            md = sm.modes(th, 14)
            res = {"modes": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()} for m in md[:10]],
                   "support_mode": support_mode(md), "crb": {}}
            if sc.contact == "hertz_rail":
                res["p2_mode"] = p2_mode(md)
            for snr in (20.0, 40.0):
                for wk in ("W_known", "W_unknown"):
                    params = list(sc.targets) + (["log_W"] if wk == "W_unknown" else [])
                    res["crb"][f"snr{int(snr)}_{wk}"] = crb_report(sm, th, params, N_PASSES, snr)
            res["Pi_prior"] = pi_over_prior(sm, th, prior, which, n=150)
            if which == "p2":
                res["Pi_prior_support_mode"] = pi_over_prior(sm, th, {"kB0": ("log", LN2, None), "W": ("uni", 5.5, 22.5)},
                                                             "support", n=150)
            out[key] = res
            c = res["crb"]["snr40_W_known"]
            print(key, "| support mode %.1f Hz zeta %.3f" % (res["support_mode"]["f_hz"], res["support_mode"]["zeta"]),
                  "| orders", c["n_orders"], "max f %.0f" % c["max_freq_hz"])
            for kk, cc in res["crb"].items():
                print("   ", kk, {k: f"{v:.3g}" for k, v in cc["crb_std_log"].items()},
                      "| cB-equiv %.3g" % cc.get("crb_std_log_cB_equivalent", float("nan")),
                      "| dlogz/dlogcB %.3g" % cc.get("dlogzeta_s_dlogparam", {}).get("log_cB", float("nan")),
                      "| null dirs", cc["n_unidentifiable_directions"])
            print("    Pi:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in res["Pi_prior"].items()})
    save_result("p1/bound_scan", out, cfg={"N_passes": N_PASSES, "track_wavelengths_150": track_150,
                                           "placeholders": "roughness 0 dB re 1um/band; kH0=1.4e9 N/m at W0; rail "
                                                           "m_r=150 kg, k_r=1e8 N/m, c_r=1e5 N s/m; OOR std 1e-4/n m",
                                           "note": "exploratory; reference solver unchanged"}, wall_seconds=tm.seconds)


if __name__ == "__main__":
    main()
