"""Why the debiased Whittle likelihood is needed with multi-wheel cross terms (paper Fig. 3).

Setup of experiments/p2_scope_p2.py (CT23 12-wheel lumped vehicle, resilient track, hysteretic truth
kf = 7.7 MN/m^2, 62 m records), one speed (16 m/s), 300 independent realisations at 60 dB SNR. The
mean periodogram is compared with the estimator's own signal-variance models (MultiPassWhittle._A):
bin-sampled |H(f_k)|^2 S(f_k) and debiased (Fejer-kernel convolution). Writes
results/p2/debias_check.json (arrays for the figure and rms log-ratio summaries).
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

import experiments.p2_scope_p2 as S  # noqa: E402
from experiments.p1_bound_robustness import ISO3095_FIG2_DB  # noqa: E402
from src.inverse.multipass import MultiPassWhittle, generate_pass  # noqa: E402
from src.inverse.whittle import Roughness  # noqa: E402
from src.reference.track import RailTrack, load_track_config  # noqa: E402
from src.utils.results import Timer, save_result  # noqa: E402

V, NREP, SNR = 16.0, 300, 60.0


def main():
    cfg = load_track_config()
    rail = {k: cfg["rail_BS113A"][k] for k in ("E", "G", "kappa", "rho", "A", "I")}
    veh = {k: cfg["vehicle_CT23"][k] for k in ("m_w", "k1", "c1", "kH")}
    pos = np.array(cfg["layout_CT23"]["positions"])
    truth = S.LumpedTrackModel(RailTrack(kf=7.7e6, eta_f=0.2, **rail), pos, 4, veh)
    fam = S.KfFamily(rail, pos, 4, veh)
    bands = dict(ISO3095_FIG2_DB)
    sl = ISO3095_FIG2_DB[0.4] - ISO3095_FIG2_DB[0.315]
    for i, lam in enumerate((0.5, 0.63, 0.8, 1.0)):
        bands[lam] = ISO3095_FIG2_DB[0.4] + sl * (i + 1)
    b = np.array(sorted(bands))
    rough = Roughness(b, np.array([bands[x] for x in b]), K=4)
    fg = np.arange(S.F_LO - 6, S.F_HI + 1.0, 0.05)
    Hf = truth.H_fn(V, fg)
    rng = np.random.default_rng(1)
    with Timer() as tm:
        acc, P0 = 0.0, None
        for _ in range(NREP):
            p = generate_pass(Hf, rough, np.ones(rough.n_sub), V, S.R0_EFF, SNR, rng, f_lo=S.F_LO, f_hi=S.F_HI)
            acc = acc + np.abs(p["c"]) ** 2
            P0 = p if P0 is None else P0
        mean_c2 = acc / NREP
        out = {}
        for tag, deb in (("bin_sampled", False), ("debiased", True)):
            est = MultiPassWhittle([dict(P0)], np.ones(1), 0.03, rough, fam, debias=deb, support=(S.F_LO - 5, S.F_HI))
            A = est._A(fam.table({"kf": 7.7e6}), np.zeros(1), np.zeros(est.S))[0]
            out[tag] = A + est.P[0].e
        f = est.P[0].f
        keep = np.isin(P0["f"], f)
        mc = mean_c2[keep]
        sel = (f > 25) & (f < 140)
        summ = {tag: {"rms_log_ratio": float(np.sqrt(np.mean(np.log(mc[sel] / v[sel]) ** 2))),
                      "mean_ratio": float(np.mean(mc[sel] / v[sel]))} for tag, v in out.items()}
        summ["sampling_noise_rms_log_expected"] = 1 / math.sqrt(NREP)
    print(summ)
    save_result("p2/debias_check", {"f_hz": f.tolist(), "mean_periodogram": mc.tolist(),
                                    "model_bin_sampled": out["bin_sampled"].tolist(), "model_debiased": out["debiased"].tolist(),
                                    "summary_25_140hz": summ},
                cfg={"setup": "CT23 12-wheel lumped vehicle, resilient track kf 7.7 MN/m^2 (hysteretic), 62 m records",
                     "speed_ms": V, "realisations": NREP, "snr_db": SNR}, seed=1, wall_seconds=tm.seconds)


if __name__ == "__main__":
    main()
