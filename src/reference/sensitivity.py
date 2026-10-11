"""P1.6 identifiability early warning for L1-lin.

* Modal map of the constrained system (wheel w prescribed): frequencies, axlebox share of
  kinetic energy, symmetry, modal damping ratio.
* Log-sensitivities of the per-order axlebox acceleration power to log kB0, log cB, log W.
* Fisher information and Cramer-Rao bounds for (log kB0, log cB [, log W]) from N passes of
  per-order complex amplitudes c_k ~ CN(0, v_k(theta)) plus least-squares estimation noise.
* Pi = s / zeta for the modes, with s the natural-frequency CoV over the prior on (kB0, W).
"""

from __future__ import annotations

import math

import numpy as np
from scipy.linalg import eigh

from src.reference.frequency_domain import ForcingMap, unit_responses
from src.reference.params import Params
from src.reference.timoshenko_fe import L1LinModel


def modal_map(mdl: L1LinModel, kB0: float, cB: float, W: float, n_modes: int = 8) -> list[dict]:
    m = mdl.matrices(kB0, cB, W)
    f = m.free
    Mf, Kf, Cf = m.M[np.ix_(f, f)], m.K[np.ix_(f, f)], m.C[np.ix_(f, f)]
    w2, V = eigh(Kf, Mf)
    ibl, ibr = (int(np.where(f == i)[0][0]) for i in mdl.ib)
    out = []
    for k in range(n_modes):
        v = V[:, k]
        ke = v * (Mf @ v)
        w = math.sqrt(w2[k])
        out.append({"f_hz": w / (2 * math.pi), "axlebox_ke_frac": float((ke[ibl] + ke[ibr]) / ke.sum()),
                    "symmetric": bool(np.sign(v[ibl]) == np.sign(v[ibr]) or abs(v[ibl]) < 1e-12),
                    "zeta_modal": float(v @ Cf @ v / (2 * w * (v @ Mf @ v)))})
    return out


def order_power(mdl: L1LinModel, fm: ForcingMap, kB0: float, cB: float, W: float) -> np.ndarray:
    """v_k = E|c_k|^2 of left-axlebox acceleration per forcing frequency (no noise)."""
    Xh = unit_responses(mdl, fm, kB0, cB, W)
    acc = -(fm.omegas**2) * Xh[:, mdl.ib[0]]
    s2 = np.zeros(fm.omegas.size)
    for j in range(fm.n_vars):
        s2[fm.index[j]] += abs(fm.coef[j]) ** 2
    return np.abs(acc) ** 2 * s2


def log_sensitivities(mdl, fm, kB0, cB, W, h: float = 1e-3) -> dict:
    base = np.log(order_power(mdl, fm, kB0, cB, W))
    out = {}
    for name, f in (("log_kB0", lambda e: (kB0 * e, cB, W)), ("log_cB", lambda e: (kB0, cB * e, W)),
                    ("log_W", lambda e: (kB0, cB, W * e))):
        up = np.log(order_power(mdl, fm, *f(math.exp(h))))
        dn = np.log(order_power(mdl, fm, *f(math.exp(-h))))
        out[name] = (up - dn) / (2 * h)
    out["log_power"] = base
    return out


def fisher_crb(p: Params, mdl, fm, kB0, cB, W, n_passes: int, snr_db: float, params=("log_kB0", "log_cB")) -> dict:
    s = log_sensitivities(mdl, fm, kB0, cB, W)
    v = np.exp(s["log_power"])
    sen = p.v["sensor"]
    n_samp = int(sen["n_revs"] / p.f_r * sen["fs"])
    p_sig = 0.5 * v.sum()  # mean power of the multi-tone signal
    sig_n2 = p_sig / 10 ** (snr_db / 10)
    e_noise = 4 * sig_n2 / n_samp  # E|c_hat - c|^2 for LS from n_samp real samples
    vt = v + e_noise
    G = np.stack([s[k] * v / vt for k in params], 1)  # d log(v_total) / d param
    I = n_passes * G.T @ G
    cov = np.linalg.pinv(I)
    return {"params": list(params), "fisher": I.tolist(), "crb_std": np.sqrt(np.diag(cov)).tolist(),
            "cond": float(np.linalg.cond(I)), "noise_power_per_order": e_noise, "n_samples_per_pass": n_samp,
            "corr": (cov / np.sqrt(np.outer(np.diag(cov), np.diag(cov)))).tolist()}


def pi_over_prior(p: Params, mdl, n: int, seed: int, n_modes: int = 6) -> dict:
    rng = np.random.default_rng(seed)
    uk, uc, uw = rng.uniform(-1, 1, (3, n))
    kB0, cB = p.theta_from_u(uk, uc)
    W = p.W_from_u(uw)
    fr = np.empty((n, n_modes))
    zt = np.empty((n, n_modes))
    for i in range(n):
        mm = modal_map(mdl, kB0[i], cB[i], W[i], n_modes)
        fr[i] = [x["f_hz"] for x in mm]
        zt[i] = [x["zeta_modal"] for x in mm]
    s = fr.std(0) / fr.mean(0)
    zeta_med = np.median(zt, 0)
    return {"mean_f_hz": fr.mean(0).tolist(), "freq_cov_s": s.tolist(), "zeta_median": zeta_med.tolist(),
            "Pi": (s / zeta_med).tolist(), "n": n}
