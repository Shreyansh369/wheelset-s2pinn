"""Paper-only surrogate assessment: how compressible is H(f; kB0, W) in the forms a surrogate would use?

No surrogate is trained. Using the exact FE transfer function of scenario (a) (left-axlebox
acceleration per unit roughness, 50-700 Hz, cB = 5e3), we compute:

1. Separable (CP / SVD) rank. Matrix H[f_j, (kB0, W)_k] over the prior (kB0 log-uniform factor 2
   around 1e9, i.e. 0.5e9-2e9; W 5.5-22.5 t). The best rank-R approximation in (f) x (theta) is the
   truncated SVD (the CP rank of a two-way split equals the matrix rank), so its relative error
   bounds from below any separable surrogate with R terms in that split. Reported: R needed for
   relative Frobenius errors of 1e-1/1e-2/1e-3, also for E = 1, 2, 4, 8 elements in log kB0
   (multi-element: a separate CP per element).
2. Modal form. H = -w^2 sum_m r_m(theta) / (i w - lambda_m(theta)) over the observable modes.
   Poles and residues of the excited modes are tracked over the prior (eigenvector overlap). We fit
   each lambda_m and r_m with a tensor Legendre polynomial in (log kB0, log W) of degree p and report
   the resulting relative error of H over the band, against the number of modes kept.
3. Cost: one eigendecomposition (all modes, exact) and one direct solve per frequency.

Writes results/p1/surrogate_rank.json. Single-threaded.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from numpy.polynomial import legendre as L  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analysis.bound_scan import Scenario, ScenarioModel  # noqa: E402
from src.inverse.whittle import ModalH  # noqa: E402
from src.reference.params import load_params  # noqa: E402
from src.utils.results import Timer, save_result  # noqa: E402

KB_RANGE = (0.5e9, 2.0e9)
W_RANGE = (5.5, 22.5)
F = np.arange(50.0, 700.25, 0.5)
TOLS = (1e-1, 1e-2, 1e-3)


def svd_ranks(Hm: np.ndarray) -> dict:
    s = np.linalg.svd(Hm, compute_uv=False)
    tail = np.sqrt(np.maximum(np.cumsum((s**2)[::-1])[::-1], 0)) / np.sqrt(np.sum(s**2))
    tail = np.append(tail[1:], 0.0)  # tail[R-1] = rel. Frobenius error of the rank-R truncation
    return {f"R_for_{t:g}": int(np.argmax(tail <= t) + 1) for t in TOLS}


def truncation_bias(sm, thb, Hcube, lk, lW, w, N: int = 50, snr_db: float = 40.0, seed: int = 7) -> dict:
    """Asymptotic kB0 bias of the Whittle ML estimator when H is replaced by its rank-R SVD truncation.

    Design: N passes, speeds uniform 60-110 km/h, payloads on the W grid nodes, kB0 at the grid node
    nearest 0.85e9, roughness ISO shape with K = 16 free sub-band levels, WIM prior 3%. Misspecified-model
    bias to first order: b = -J^-1 D^T delta, delta_k = log v_R - log v_true per bin, D = d log v / d params.
    The SVD truncation is the optimal R-term separable approximation (Frobenius) on this grid, so a
    trained CP surrogate with R terms in the (f) x (theta) split can only do worse.
    """
    from src.inverse.whittle import Roughness
    from experiments.p1_bound_robustness import ISO3095_FIG2_DB
    bands = np.array(sorted(ISO3095_FIG2_DB))
    rough = Roughness(bands, np.array([ISO3095_FIG2_DB[b] for b in bands]), K=16)
    rng = np.random.default_rng(seed)
    a0 = int(np.argmin(np.abs(lk - math.log(0.85e9))))
    nk, nw, nf = Hcube.shape
    Vs = rng.uniform(60, 110, N) / 3.6
    Wi = np.arange(N) % nw
    h = 1e-4
    th0 = dict(thb, kB0=math.exp(lk[a0]))
    # exact derivatives at the truth for every payload node
    dH = {}
    for b in range(nw):
        t = dict(th0, W=math.exp(lW[b]))
        d = []
        for nm in ("kB0", "cB", "W"):
            u, m = dict(t), dict(t)
            u[nm] *= math.exp(h)
            m[nm] *= math.exp(-h)
            d.append((sm.axlebox_accel_per_unit_input(u, w) - sm.axlebox_accel_per_unit_input(m, w)) / (2 * h))
        dH[b] = d
    fgrid = w / (2 * np.pi)

    def at(fk, z):
        return np.interp(fk, fgrid, z.real) + 1j * np.interp(fk, fgrid, z.imag)
    passes = []
    for V, b in zip(Vs, Wi):
        T = 20 * 2 * np.pi * thb["r0"] / V
        n = int(round(T * 2000.0))
        T = n / 2000.0
        fk = np.arange(math.ceil(50 * T), math.floor(700 * T) + 1) / T
        Om = 2 * np.pi * fk / V
        s = rough.subband(Om)
        ok = s >= 0
        fk, Om, s = fk[ok], Om[ok], s[ok]
        base = 2 * rough.density(Om) * (2 * np.pi / T / V)
        passes.append((fk, s, base, b, n))
    used = np.unique(np.concatenate([p[1] for p in passes]))
    smap = -np.ones(rough.n_sub, int)
    smap[used] = np.arange(used.size)
    npar = 2 + used.size + N  # [log kB0, log cB, sub-band levels, per-pass log W]
    J = np.zeros((npar, npar))
    Ds, vs = [], []
    for i, (fk, s, base, b, n) in enumerate(passes):
        H = at(fk, Hcube[a0, b])
        sig = np.abs(H) ** 2 * base
        e = 4 * (0.5 * sig.sum()) / 10 ** (snr_db / 10) / n
        v = sig + e
        D = np.zeros((fk.size, npar))
        D[:, 0] = 2 * np.real(np.conj(H) * at(fk, dH[b][0])) * base / v
        D[:, 1] = 2 * np.real(np.conj(H) * at(fk, dH[b][1])) * base / v
        D[np.arange(fk.size), 2 + smap[s]] = sig / v
        D[:, 2 + used.size + i] = 2 * np.real(np.conj(H) * at(fk, dH[b][2])) * base / v
        J += D.T @ D
        Ds.append(D)
        vs.append((H, base, e, v))
    J[2 + used.size:, 2 + used.size:] += np.eye(N) / 0.03**2
    d = 1 / np.sqrt(np.diag(J))
    Ji = np.linalg.inv(J * np.outer(d, d)) * np.outer(d, d)
    crb = float(math.sqrt(Ji[0, 0]))
    out = {"crb_rel_kB0": crb, "N": N, "snr_db": snr_db, "kB0_truth": float(math.exp(lk[a0])), "rows": []}
    M = Hcube.reshape(-1, nf).T  # f x (kB0, W), full prior, E = 1
    U, S, Vh = np.linalg.svd(M, full_matrices=False)
    E4 = np.linspace(0, nk, 5).astype(int)
    e4 = int(np.searchsorted(E4, a0, side="right") - 1)
    blk = Hcube[E4[e4]:E4[e4 + 1]].reshape(-1, nf).T
    U4, S4, Vh4 = np.linalg.svd(blk, full_matrices=False)
    for R in (3, 5, 8, 10, 13, 16, 20):
        for tag, (Uu, Ss, Vv, a_off) in {"E1": (U, S, Vh, 0), "E4": (U4, S4, Vh4, E4[e4])}.items():
            MR = (Uu[:, :R] * Ss[:R]) @ Vv[:R]
            HR = MR.T.reshape(-1, nw, nf)
            g = np.zeros(npar)
            maxrel = 0.0
            for i, (fk, s, base, b, n) in enumerate(passes):
                H, base_, e, v = vs[i]
                HRk = at(fk, HR[a0 - a_off, b])
                maxrel = max(maxrel, float(np.max(np.abs(HRk - H) / np.abs(H))))
                delta = np.log(np.abs(HRk) ** 2 * base + e) - np.log(v)
                g += Ds[i].T @ delta
            bias = -(Ji @ g)[0]
            fro = float(np.sqrt(np.sum(Ss[R:] ** 2) / np.sum(Ss**2)))
            out["rows"].append({"elements": tag, "R": R, "rel_frobenius_err": fro, "max_rel_err_at_truth_bins": maxrel,
                                "bias_rel_kB0": float(bias), "bias_over_crb": float(abs(bias) / crb)})
    return out


def main() -> None:
    p = load_params()
    sm = ScenarioModel(p, Scenario(name="a", kB0=1e9, cB=5e3, contact="hertz_rail", band_hz=700, fs=2000,
                                   forcing_spec={}, targets=[], kH0=1.4e9))
    thb = {"kB0": 1e9, "cB": 5e3, "k_r": 1e8, "r0": p.r0}
    w = 2 * np.pi * F
    nk, nw = 48, 12
    lk = np.linspace(math.log(KB_RANGE[0]), math.log(KB_RANGE[1]), nk)
    lW = np.linspace(math.log(W_RANGE[0]), math.log(W_RANGE[1]), nw)
    out = {}
    with Timer() as tm:
        # ---- exact H on the grid
        t0 = time.perf_counter()
        Hcube = np.empty((nk, nw, F.size), complex)
        for a, x in enumerate(lk):
            for b, y in enumerate(lW):
                Hcube[a, b] = sm.axlebox_accel_per_unit_input(dict(thb, kB0=math.exp(x), W=math.exp(y)), w)
        t_direct = (time.perf_counter() - t0) / (nk * nw)
        # ---- 1. separable rank, full prior and multi-element in log kB0
        sep = {}
        for E in (1, 2, 4, 8):
            edges = np.linspace(0, nk, E + 1).astype(int)
            per = []
            for e in range(E):
                blk = Hcube[edges[e]:edges[e + 1]].reshape(-1, F.size).T  # f x (kB0, W)
                per.append(svd_ranks(blk))
            sep[f"E{E}"] = {k: int(max(r[k] for r in per)) for k in per[0]}
            sep[f"E{E}"]["kB0_ratio_per_element"] = float((KB_RANGE[1] / KB_RANGE[0]) ** (1 / E))
        # same with W fixed (theta = kB0 only), to separate the payload contribution
        sep["E1_W_fixed_14t"] = svd_ranks(np.stack([sm.axlebox_accel_per_unit_input(
            dict(thb, kB0=math.exp(x), W=14.0), w) for x in lk], 1))
        out["separable_rank"] = sep
        # ---- 1b. what kB0 bias does the best rank-R separable surrogate cause? (linearised ML bias)
        out["separable_bias"] = truncation_bias(sm, thb, Hcube, lk, lW, w)
        # ---- 2. modal form with tracked poles/residues
        mh = ModalH(sm, np.array([14.0]), F)
        t0 = time.perf_counter()
        lam0, res0 = mh.poles_residues(dict(thb, kB0=1e9, W=14.0))
        t_eig = time.perf_counter() - t0
        up = lam0.imag > 0
        fr0 = lam0.imag / (2 * np.pi)
        obs = np.where(up & (np.abs(res0) > 1e-6 * np.abs(res0[up]).max()) & (fr0 < 1500))[0]
        obs = obs[np.argsort(fr0[obs])]
        modes_info = [{"f_hz": float(fr0[i]), "zeta": float(-lam0[i].real / abs(lam0[i])), "abs_res": float(abs(res0[i]))}
                      for i in obs]
        # track by nearest pole among the excited modes
        lam_g = np.empty((nk, nw, obs.size), complex)
        res_g = np.empty((nk, nw, obs.size), complex)
        rest_g = np.empty((nk, nw, F.size), complex)  # contribution of all other modes (exact)
        min_sep = np.inf
        for a, x in enumerate(lk):
            for b, y in enumerate(lW):
                lam, res = mh.poles_residues(dict(thb, kB0=math.exp(x), W=math.exp(y)))
                prev = lam_g[a - 1, b] if a > 0 else (lam_g[a, b - 1] if b > 0 else lam0[obs])
                # candidates: excited modes only (antisymmetric modes have ~zero residue at symmetric input
                # and cross the symmetric ones exactly; including them breaks nearest-pole tracking)
                cand = np.where((lam.imag > 0) & (np.abs(res) > 1e-6 * np.abs(res).max()))[0]
                pick = []
                for m in range(obs.size):
                    d = np.abs(lam[cand] - prev[m])
                    j = cand[np.argmin(d)]
                    pick.append(j)
                    srt = np.sort(d)
                    min_sep = min(min_sep, float(srt[1] / max(srt[0], 1e-12)))
                pick = np.array(pick)
                lam_g[a, b], res_g[a, b] = lam[pick], res[pick]
                full = -(w**2) * (res[None, :] / (1j * w[:, None] - lam[None, :])).sum(1)
                kept = -(w**2) * (res[pick][None, :] / (1j * w[:, None] - lam[pick][None, :])
                                  + np.conj(res[pick])[None, :] / (1j * w[:, None] - np.conj(lam[pick])[None, :])).sum(1)
                rest_g[a, b] = full - kept
        out["modal_tracking"] = {"modes_kept_at_nominal": modes_info,
                                 "min_ratio_second_nearest_over_nearest_pole": min_sep,
                                 "rest_rel_norm_max": float(np.max(np.linalg.norm(rest_g, axis=2) /
                                                                   np.linalg.norm(Hcube, axis=2)))}
        # polynomial fits of lambda_m, r_m (and the smooth remainder) in (log kB0, log W)
        X = 2 * (lk - lk[0]) / (lk[-1] - lk[0]) - 1
        Y = 2 * (lW - lW[0]) / (lW[-1] - lW[0]) - 1
        modal = {}
        for deg in (2, 3, 4, 6, 8):
            Vx, Vy = L.legvander(X, deg), L.legvander(Y, min(deg, 4))
            Vfull = np.kron(Vx, Vy)  # (nk*nw) x n_coef
            pinv = np.linalg.pinv(Vfull)

            def fitq(q):
                Q = q.reshape(nk * nw, -1)
                return (Vfull @ (pinv @ Q)).reshape(q.shape)
            lam_f, res_f, rest_f = fitq(lam_g), fitq(res_g), fitq(rest_g)
            Hf = -(w**2)[None, None, :] * ((res_f[..., None, :] / (1j * w[None, None, :, None] - lam_f[..., None, :])) +
                                           (np.conj(res_f)[..., None, :] / (1j * w[None, None, :, None] - np.conj(lam_f)[..., None, :]))).sum(-1)
            Hf = Hf + rest_f
            rel = np.linalg.norm(Hf - Hcube, axis=2) / np.linalg.norm(Hcube, axis=2)
            pole_err = np.max(np.abs(lam_f - lam_g) / np.abs(lam_g.real))  # in units of the pole's own decay rate
            modal[f"deg_kB{deg}_W{min(deg, 4)}"] = {"H_rel_err_max": float(rel.max()), "H_rel_err_median": float(np.median(rel)),
                                                     "pole_err_over_decay_rate_max": float(pole_err),
                                                     "n_coef_per_function": int(Vfull.shape[1]),
                                                     "n_real_functions": int(2 * 2 * obs.size + 2 * F.size)}
        out["modal_fit"] = modal
        out["cost"] = {"direct_solve_s_per_theta_band": t_direct, "direct_solve_s_per_freq": t_direct / F.size,
                       "eig_s_per_theta": t_eig, "n_dof": int(sm.system(dict(thb, W=14.0))[0][0].shape[0]),
                       "n_freq_band": int(F.size)}
        print(out, flush=True)
    save_result("p1/surrogate_rank", out, cfg={"kB0_range": KB_RANGE, "W_range_t": W_RANGE, "cB": 5e3,
                                               "f_grid_hz": [50, 700, 0.5], "grid": [nk, nw], "tols": TOLS},
                wall_seconds=tm.seconds)


if __name__ == "__main__":
    main()
