"""FE-direct identification of kB0 (and cB) by a Whittle likelihood across passes (scenario a, option iv).

Physics: L1-lin FE (src/reference) with linearised Hertz contact + rail oscillator
(src/analysis/bound_scan.ScenarioModel); observation = left-axlebox acceleration DFT bins of a
20-revolution record, 50-700 Hz. Roughness = wavenumber PSD with the ISO 3095:2013 Fig. 2 shape
times an unknown level per sub-band (K per one-third octave). Speed known per pass; payload measured
per pass with relative error sigma_W (3%).

* ``generate_pass``: synthetic record from the reference FE model (direct solves on a fine frequency
  grid). Roughness is realised on a wavenumber grid 4x finer than the DFT bins; the response is
  synthesised as a 4T time series, truncated to T (so leakage is realistic), white noise is added at
  the stated SNR, and the record is FFT'd. Independent of the estimator's H.
* ``ModalH``: exact complex-modal transfer function (state-space eigendecomposition, all modes) at a
  grid of payloads (25 log-spaced nodes, 5-24 t), interpolated in log W (cubic spline; max error
  6.6e-5 against direct solves) and frequency (linear on 0.5 Hz).
* ``WhittleFit``: profile likelihood. For fixed (log kB0, log cB): Fisher scoring to convergence on
  per-sub-band log roughness levels and per-pass log W (WIM prior); the outer 2-D problem is solved
  by Nelder-Mead. Uncertainty from the numerical Hessian of the profile negative log-likelihood;
  ``expected_fisher`` gives the matching Cramer-Rao bound with all nuisances free.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.linalg import eig
from scipy.optimize import minimize

from src.analysis.bound_scan import ScenarioModel

F_LO, F_HI, FS, N_REVS = 50.0, 700.0, 2000.0, 20
NOISE_BAND = (750.0, 950.0)
EDGE = 2 ** (1 / 6)


# --------------------------------------------------------------------------- roughness model
@dataclass
class Roughness:
    bands_m: np.ndarray        # one-third-octave centre wavelengths (m)
    level_db: np.ndarray       # ISO 3095 Fig. 2 levels (dB re 1 um)
    K: int                     # sub-bands per one-third octave

    def __post_init__(self):
        self.om_c = 2 * np.pi / self.bands_m
        self.om_lo = self.om_c.min() / EDGE
        self.om_hi = self.om_c.max() * EDGE
        self.n_sub = int(round(math.log(self.om_hi / self.om_lo) / (math.log(EDGE**2) / self.K)))

    def density(self, Om: np.ndarray) -> np.ndarray:
        """Smooth ISO-shaped wavenumber PSD (m^2 per rad/m), band integrals match the ISO levels."""
        rms2 = 1e-12 * 10 ** (self.level_db / 10)
        dens_c = rms2 / (self.om_c * (EDGE - 1 / EDGE))
        o = np.argsort(self.om_c)
        return np.exp(np.interp(np.log(Om), np.log(self.om_c[o]), np.log(dens_c[o])))

    def subband(self, Om: np.ndarray) -> np.ndarray:
        s = np.floor(np.log(Om / self.om_lo) / (math.log(EDGE**2) / self.K)).astype(int)
        s[(Om < self.om_lo) | (Om >= self.om_hi)] = -1
        return s


# --------------------------------------------------------------------------- data generation
def generate_pass(sm: ScenarioModel, th: dict, rough: Roughness, g_true: np.ndarray, V: float, W_true: float,
                  snr_db: float, rng: np.random.Generator, df_fine_factor: int = 4) -> dict:
    """One synthetic pass: returns DFT-bin complex amplitudes and the noise-floor estimate."""
    r0 = th["r0"]
    T = N_REVS * 2 * np.pi * r0 / V
    n = int(round(T * FS))
    T = n / FS
    nf = df_fine_factor * n  # long record 4T
    f_fine = np.arange(nf // 2 + 1) * FS / nf
    band = (f_fine >= F_LO - 5) & (f_fine <= F_HI)
    fb = f_fine[band]
    Om = 2 * np.pi * fb / V
    s = rough.subband(Om)
    ok = s >= 0
    dOm = 2 * np.pi * (FS / nf) / V
    var = np.zeros(fb.size)
    var[ok] = 2 * rough.density(Om[ok]) * g_true[s[ok]] * dOm  # E|Z|^2 per fine component
    Z = np.sqrt(var / 2) * (rng.standard_normal(fb.size) + 1j * rng.standard_normal(fb.size))
    # reference FE: direct solves on a 0.25 Hz grid (the estimator uses a different, modal H on 0.5 Hz)
    fg = np.arange(F_LO - 6, F_HI + 1.0, 0.25)
    Hg = sm.axlebox_accel_per_unit_input(dict(th, W=W_true), 2 * np.pi * fg)
    H = np.interp(fb, fg, Hg.real) + 1j * np.interp(fb, fg, Hg.imag)
    X = np.zeros(f_fine.size, complex)
    X[band] = (nf / 2) * H * Z
    x = np.fft.irfft(X, n=nf)[:n]  # truncate the 4T record to T
    sig_pow = np.mean(x**2)
    sigma = math.sqrt(sig_pow / 10 ** (snr_db / 10))
    y = x + sigma * rng.standard_normal(n)
    C = 2 * np.fft.rfft(y) / n
    fk = np.arange(C.size) / T
    nb = (fk >= NOISE_BAND[0]) & (fk <= NOISE_BAND[1])
    keep = (fk >= F_LO) & (fk <= F_HI)
    # e_noise is the out-of-band floor measured from the record itself (noise + leakage of the
    # rectangular 20-revolution window); the estimator uses it as a known additive floor.
    return {"f": fk[keep], "c": C[keep], "e_noise": float(np.mean(np.abs(C[nb]) ** 2)), "V": V, "T": T,
            "e_noise_true": 4 * sigma**2 / n}


# --------------------------------------------------------------------------- modal transfer function
class ModalH:
    """Exact complex-modal H(w) of left-axlebox acceleration per unit roughness input."""

    def __init__(self, sm: ScenarioModel, W_nodes: np.ndarray, f_grid: np.ndarray):
        self.sm = sm
        self.lw = np.log(W_nodes)
        self.f = f_grid
        self.w = 2 * np.pi * f_grid

    def poles_residues(self, th: dict) -> tuple[np.ndarray, np.ndarray]:
        (M, C, K), f = self.sm.system(th)
        n = M.shape[0]
        Mi = np.linalg.inv(M)
        A = np.block([[np.zeros((n, n)), np.eye(n)], [-Mi @ K, -Mi @ C]])
        b = np.concatenate([np.zeros(n), Mi @ f])
        lam, VL, VR = eig(A, left=True, right=True)
        num = (VL.conj().T @ b) / np.einsum("ij,ij->j", VL.conj(), VR)
        res = VR[self.sm.ibL, :] * num
        return lam, res

    def H_grid(self, kB0: float, cB: float, th_base: dict) -> np.ndarray:
        """H on [W nodes, f grid]."""
        out = np.empty((self.lw.size, self.w.size), complex)
        for i, lw in enumerate(self.lw):
            lam, res = self.poles_residues(dict(th_base, kB0=kB0, cB=cB, W=float(np.exp(lw))))
            out[i] = -(self.w**2) * (res[None, :] / (1j * self.w[:, None] - lam[None, :])).sum(1)
        return out


# --------------------------------------------------------------------------- Whittle fit
class WhittleFit:
    """Whittle likelihood across passes. Bin model: c ~ CN(0, v), v = |H(f; kB0, cB, W_i)|^2 G_s dOm g_s + e_i.

    Unknowns: phi = (log kB0, log cB); nuisances: log g_s per sub-band (flat prior) and log W_i per pass
    (Gaussian prior, sd sigma_W, around the measured value). e_i is the measured out-of-band floor.
    NLL = sum_bins [log v + |c|^2 / v] + sum_i (log W_i - log W_meas_i)^2 / (2 sigma_W^2).
    """

    def __init__(self, passes: list[dict], W_meas: np.ndarray, sigma_W: float, rough: Roughness, mh: ModalH,
                 th_base: dict):
        self.P = passes
        self.lw_meas = np.log(np.asarray(W_meas, float))
        self.sW = sigma_W
        self.rough = rough
        self.mh = mh
        self.thb = th_base
        self.sub, self.base, self.c2, self.f, self.e = [], [], [], [], []
        for p in passes:
            Om = 2 * np.pi * p["f"] / p["V"]
            s = rough.subband(Om)
            ok = s >= 0
            dOm = 2 * np.pi * (1 / p["T"]) / p["V"]
            self.sub.append(s[ok])
            self.f.append(p["f"][ok])
            self.base.append(2 * rough.density(Om[ok]) * dOm)
            self.c2.append(np.abs(p["c"][ok]) ** 2)
            self.e.append(p["e_noise"])
        self.S = rough.n_sub
        self.used = np.unique(np.concatenate(self.sub))
        self.n_eval = 0
        self.t_eval = 0.0
        self._warm = None

    # -- transfer function per pass (and its log-W derivative) from the modal grid
    def _interp(self, i: int, row: np.ndarray) -> np.ndarray:
        return np.interp(self.f[i], self.mh.f, row.real) + 1j * np.interp(self.f[i], self.mh.f, row.imag)

    def _H_all(self, spl: CubicSpline, lw: np.ndarray, deriv: bool = False):
        Hf = spl(lw)
        H = [self._interp(i, Hf[i]) for i in range(len(self.P))]
        if not deriv:
            return H
        dHf = spl(lw, 1)
        return H, [self._interp(i, dHf[i]) for i in range(len(self.P))]

    def _nuisance_solve(self, spl: CubicSpline, logg: np.ndarray, lw: np.ndarray, tol: float = 1e-7,
                        max_it: int = 60):
        """Fisher scoring on (log g, log W) for fixed phi, alternating blocks until steps < tol."""
        N = len(self.P)
        for it in range(max_it):
            H, dH = self._H_all(spl, lw, deriv=True)
            gnum = np.zeros(self.S)
            gden = np.zeros(self.S)
            wstep = np.zeros(N)
            for i in range(N):
                g = np.exp(logg[self.sub[i]])
                a = np.abs(H[i]) ** 2 * self.base[i] * g
                v = a + self.e[i]
                r = self.c2[i] / v - 1
                gnum += np.bincount(self.sub[i], a / v * r, minlength=self.S)
                gden += np.bincount(self.sub[i], (a / v) ** 2, minlength=self.S)
                da = 2 * np.real(np.conj(H[i]) * dH[i]) * self.base[i] * g / v  # d log v / d log W
                score = da @ r - (lw[i] - self.lw_meas[i]) / self.sW**2
                info = da @ da + 1 / self.sW**2
                wstep[i] = score / info
            gstep = np.where(gden > 0, gnum / np.maximum(gden, 1e-300), 0.0)
            logg = logg + np.clip(gstep, -2, 2)
            lw = lw + np.clip(wstep, -0.1, 0.1)
            if max(np.abs(gstep).max(), np.abs(wstep).max()) < tol:
                break
        return logg, lw, it + 1

    def _nll(self, spl: CubicSpline, logg: np.ndarray, lw: np.ndarray) -> float:
        H = self._H_all(spl, lw)
        out = 0.0
        for i in range(len(self.P)):
            v = np.abs(H[i]) ** 2 * self.base[i] * np.exp(logg[self.sub[i]]) + self.e[i]
            out += np.sum(np.log(v) + self.c2[i] / v)
        return float(out + 0.5 * np.sum(((lw - self.lw_meas) / self.sW) ** 2))

    def spline(self, phi: np.ndarray) -> CubicSpline:
        Hg = self.mh.H_grid(math.exp(phi[0]), math.exp(phi[1]), self.thb)
        return CubicSpline(self.mh.lw, Hg, axis=0)

    def profile_nll(self, phi: np.ndarray, return_state: bool = False):
        t0 = time.perf_counter()
        spl = self.spline(phi)
        if self._warm is None:
            logg0, lw0 = np.zeros(self.S), self.lw_meas.copy()
        else:
            logg0, lw0 = self._warm
        logg, lw, nit = self._nuisance_solve(spl, logg0.copy(), lw0.copy())
        if self._warm is not None:
            self._warm = (logg, lw)  # warm start the next inner solve (inner tol 1e-7: path effect negligible)
        nll = self._nll(spl, logg, lw)
        self.n_eval += 1
        self.t_eval += time.perf_counter() - t0
        if return_state:
            return nll, {"logg": logg, "lw": lw, "inner_iters": nit}
        return nll

    def fit(self, phi0: np.ndarray) -> dict:
        t0 = time.perf_counter()
        phi0 = np.asarray(phi0, float)
        # cold solve at phi0, then each inner solve starts from the previous one
        self._warm = None
        _, st = self.profile_nll(phi0, return_state=True)
        self._warm = (st["logg"], st["lw"])
        res = minimize(self.profile_nll, phi0, method="Nelder-Mead",
                       options={"xatol": 1e-4, "fatol": 1e-3, "maxiter": 300, "initial_simplex":
                                np.array([phi0, phi0 + [0.15, 0.0], phi0 + [0.0, 0.3]])})
        phi = res.x
        f0, st = self.profile_nll(phi, return_state=True)
        self._warm = (st["logg"], st["lw"])
        # observed profile information: central-difference Hessian of the profile NLL (log units).
        # NLL here is -log L exactly (complex Gaussian), so information = Hessian.
        h = np.array([0.005, 0.03])
        Hs = np.zeros((2, 2))
        fp = {}
        for a in range(2):
            ea = np.eye(2)[a] * h[a]
            fp[(a, 1)] = self.profile_nll(phi + ea)
            fp[(a, -1)] = self.profile_nll(phi - ea)
            Hs[a, a] = (fp[(a, 1)] - 2 * f0 + fp[(a, -1)]) / h[a] ** 2
        e0, e1 = np.eye(2)[0] * h[0], np.eye(2)[1] * h[1]
        Hs[0, 1] = Hs[1, 0] = (self.profile_nll(phi + e0 + e1) - self.profile_nll(phi + e0 - e1)
                               - self.profile_nll(phi - e0 + e1) + self.profile_nll(phi - e0 - e1)) / (4 * h[0] * h[1])
        ev = np.linalg.eigvalsh(Hs)
        se = np.sqrt(np.diag(np.linalg.inv(Hs))) if ev.min() > 0 else np.array([np.inf, np.inf])
        return {"phi": phi.tolist(), "se_log": se.tolist(), "nll": float(f0), "n_iter": int(res.nit),
                "converged": bool(res.success), "inner_iters_at_opt": int(st["inner_iters"]),
                "wall_fit_s": time.perf_counter() - t0, "n_eval": self.n_eval,
                "s_per_eval": self.t_eval / max(self.n_eval, 1), "profile_hessian": Hs.tolist()}

    def expected_fisher(self, phi: np.ndarray, logg: np.ndarray, lw: np.ndarray, h: float = 1e-4) -> dict:
        """Expected Fisher information at (phi, g, W) under this observation model (same bins, floors).

        Parameters [log kB0, log cB, log g_s (sub-bands seen), log W_i]; WIM prior included.
        Returns the Cramer-Rao bound (log units ~ relative) for kB0 and cB with all nuisances free.
        """
        spl0 = self.spline(phi)
        dspl = []
        for a in range(2):
            e = np.eye(2)[a] * h
            dspl.append((self.spline(phi + e), self.spline(phi - e)))
        N, used = len(self.P), self.used
        smap = -np.ones(self.S, int)
        smap[used] = np.arange(used.size)
        n = 2 + used.size + N
        J = np.zeros((n, n))
        H, dHw = self._H_all(spl0, lw, deriv=True)
        dHt = [[(p(lw[i:i + 1])[0], m(lw[i:i + 1])[0]) for (p, m) in dspl] for i in range(N)]
        for i in range(N):
            g = np.exp(logg[self.sub[i]])
            v = np.abs(H[i]) ** 2 * self.base[i] * g + self.e[i]
            cols = []
            for a in range(2):
                dHa = (self._interp(i, dHt[i][a][0]) - self._interp(i, dHt[i][a][1])) / (2 * h)
                cols.append(2 * np.real(np.conj(H[i]) * dHa) * self.base[i] * g / v)
            ds = np.abs(H[i]) ** 2 * self.base[i] * g / v
            dw = 2 * np.real(np.conj(H[i]) * dHw[i]) * self.base[i] * g / v
            D = np.zeros((self.f[i].size, n))
            D[:, 0], D[:, 1] = cols
            D[np.arange(self.f[i].size), 2 + smap[self.sub[i]]] = ds
            D[:, 2 + used.size + i] = dw
            J += D.T @ D
        J[2 + used.size:, 2 + used.size:] += np.eye(N) / self.sW**2
        d = 1 / np.sqrt(np.diag(J))
        Ci = np.linalg.inv(J * np.outer(d, d)) * np.outer(d, d)
        return {"crb_log": [float(math.sqrt(Ci[0, 0])), float(math.sqrt(Ci[1, 1]))],
                "corr_kB0_cB": float(Ci[0, 1] / math.sqrt(Ci[0, 0] * Ci[1, 1])), "n_params": int(n)}
