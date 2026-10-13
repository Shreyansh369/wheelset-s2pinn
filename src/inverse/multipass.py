"""General multi-pass Whittle likelihood (FE-direct), generalising src/inverse/whittle.py.

What is general here:
* any set of global parameters estimated in log units (``Family.names``), e.g. (kB0, cB), or
  (kB0, cB, kH0, k_r) when the contact and track stiffness are co-estimated;
* a transfer function that may depend on pass speed through wheel-layout phases:
  H(f; V, W) = sum_k G_k(f; W) exp(i 2 pi f d_k / V), where G_k is smooth in f and W (one term,
  d = 0, for a single wheelset). The multi-wheel family (Carrigan & Talbot 2023, Eq. 5) uses
  several terms; the exponentials are applied exactly at the DFT bins;
* bin masks (e.g. notching wheel-order bins);
* profile-likelihood intervals for one parameter, alongside Wald intervals from the observed
  profile information.

Model per pass i and kept DFT bin k (independent sections): c_ik ~ CN(0, v_ik),
v_ik = |H(f_ik; V_i, W_i)|^2 * 2 G_iso(Omega_ik) dOmega_i * g_s(ik) + e_i, with g_s one level per
roughness sub-band, W_i the true payload (prior: lognormal around the WIM measurement, sigma_W)
and e_i the measured out-of-band floor. NLL = -log L (complex Gaussian; no factor 1/2).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.linalg import eig
from scipy.optimize import minimize, minimize_scalar
from scipy.stats import chi2

from src.inverse.whittle import F_HI, F_LO, FS, N_REVS, NOISE_BAND, Roughness  # noqa: F401  (re-exported)


# --------------------------------------------------------------------------- transfer families
@dataclass
class Table:
    """G[lw node, f grid, term] for one value of the global parameters, splined in log W."""
    lw: np.ndarray
    f: np.ndarray
    G: np.ndarray              # complex, shape (nW, nf, nterm)
    d: np.ndarray              # wheel offsets (m) relative to the instrumented wheel, shape (nterm,)

    def __post_init__(self):
        self.spl = CubicSpline(self.lw, self.G, axis=0)


class Family:
    """Interface: ``names`` (global parameters, log scale), ``fixed`` (all other inputs), ``table``."""
    names: tuple[str, ...]
    fixed: dict

    def table(self, theta: dict) -> Table:  # pragma: no cover - interface
        raise NotImplementedError


class SingleWheelsetFamily(Family):
    """Scenario (a): one FE wheelset, linearised Hertz contact, rail oscillator (bound_scan.ScenarioModel).

    H by exact complex-modal summation (state-space eigendecomposition, all modes) at log-spaced
    payload nodes; one term, d = 0.
    """

    def __init__(self, sm, fixed: dict, names=("kB0", "cB"), W_nodes=None, f_grid=None):
        self.sm, self.fixed, self.names = sm, dict(fixed), tuple(names)
        self.W_nodes = np.exp(np.linspace(math.log(5.0), math.log(24.0), 25)) if W_nodes is None else W_nodes
        self.f = np.arange(45.0, 702.0, 0.5) if f_grid is None else f_grid
        self.w = 2 * np.pi * self.f

    def poles_residues(self, th: dict):
        (M, C, K), f = self.sm.system(th)
        n = M.shape[0]
        Mi = np.linalg.inv(M)
        A = np.block([[np.zeros((n, n)), np.eye(n)], [-Mi @ K, -Mi @ C]])
        b = np.concatenate([np.zeros(n), Mi @ f])
        lam, VL, VR = eig(A, left=True, right=True)
        num = (VL.conj().T @ b) / np.einsum("ij,ij->j", VL.conj(), VR)
        return lam, VR[self.sm.ibL, :] * num

    def table(self, theta: dict) -> Table:
        G = np.empty((self.W_nodes.size, self.f.size, 1), complex)
        for i, W in enumerate(self.W_nodes):
            lam, res = self.poles_residues(dict(self.fixed, **theta, W=float(W)))
            G[i, :, 0] = -(self.w**2) * (res[None, :] / (1j * self.w[:, None] - lam[None, :])).sum(1)
        return Table(np.log(self.W_nodes), self.f, G, np.zeros(1))


# --------------------------------------------------------------------------- data generation
def generate_pass(H_fn, rough: Roughness, g_true: np.ndarray, V: float, r0: float, snr_db: float,
                  rng: np.random.Generator, Z_shared: dict | None = None, wheel_lines: dict | None = None,
                  df_fine_factor: int = 4, f_lo: float = F_LO, f_hi: float = F_HI, return_y: bool = False) -> dict:
    """One synthetic pass from a reference transfer function.

    H_fn(f) -> complex H at frequencies f (Hz) for this pass (reference model: direct solves, any
    speed-dependent phases included). Roughness is realised on a grid 4x finer than the DFT bins;
    the 4T response is truncated to the 20-revolution record T (leakage is realistic), white noise
    at the stated SNR is added, and the record is FFT'd (rectangular window).

    Z_shared: if given, {"Z": complex array} of unit-variance fine-grid roughness Fourier coefficients
    shared by every pass over the same section (index m <-> wavenumber 2 pi m / (4 L));
    otherwise a fresh realisation is drawn (independent section).
    wheel_lines: if given, {"orders": n array, "w": complex amplitude per order (m)}, a periodic
    wheel-roughness profile; its lines sit exactly at bins 20 n (angle-synchronous record, i.e.
    after tachometer resampling), with the phase referenced to the record start.
    """
    T = N_REVS * 2 * np.pi * r0 / V
    n = int(round(T * FS))
    T = n / FS
    nf = df_fine_factor * n
    f_fine = np.arange(nf // 2 + 1) * FS / nf
    band = (f_fine >= max(f_lo - 5, 0.1)) & (f_fine <= f_hi)
    kb = np.nonzero(band)[0]
    fb = f_fine[band]
    Om = 2 * np.pi * fb / V
    s = rough.subband(Om)
    ok = s >= 0
    dOm = 2 * np.pi * (FS / nf) / V
    var = np.zeros(fb.size)
    var[ok] = 2 * rough.density(Om[ok]) * g_true[s[ok]] * dOm
    if Z_shared is None:
        Z = np.sqrt(var / 2) * (rng.standard_normal(fb.size) + 1j * rng.standard_normal(fb.size))
    else:  # same section: same spatial Fourier coefficients (unit-variance draws scaled by var);
        # fine-grid index m <-> wavenumber 2 pi m / (4 L) for every pass (L = 20 wheel circumferences)
        Z = Z_shared["Z"][kb] * np.sqrt(var / 2)
    H = H_fn(fb)
    X = np.zeros(f_fine.size, complex)
    X[band] = (nf / 2) * H * Z
    if wheel_lines is not None:
        for nn, w in zip(wheel_lines["orders"], wheel_lines["w"]):
            kk = df_fine_factor * N_REVS * int(nn)  # exact bin of order n on the fine grid
            if kk < f_fine.size and f_lo - 5 <= f_fine[kk] <= f_hi:
                # periodic profile: its 4T synthesis repeats 4 times, so it stays a pure line in T
                X[kk] += (nf / 2) * H_fn(np.array([f_fine[kk]]))[0] * w
    x = np.fft.irfft(X, n=nf)[:n]
    sigma = math.sqrt(np.mean(x**2) / 10 ** (snr_db / 10))
    y = x + sigma * rng.standard_normal(n)
    C = 2 * np.fft.rfft(y) / n
    fk = np.arange(C.size) / T
    nb = (fk >= NOISE_BAND[0]) & (fk <= NOISE_BAND[1])
    keep = (fk >= f_lo) & (fk <= f_hi)
    out = {"f": fk[keep], "c": C[keep], "k": np.arange(C.size)[keep], "V": V, "T": T,
           "e_noise": float(np.mean(np.abs(C[nb]) ** 2)), "e_noise_true": 4 * sigma**2 / n, "c_noise": C[nb]}
    if return_y:
        out["y"] = y
    return out


def shared_section(rng: np.random.Generator, n_coeff: int = 40000) -> dict:
    """Unit-variance complex Fourier coefficients of one track section, indexed by fine-grid index."""
    return {"Z": rng.standard_normal(n_coeff) + 1j * rng.standard_normal(n_coeff)}


# --------------------------------------------------------------------------- likelihood
@dataclass
class PassPrep:
    f: np.ndarray
    k: np.ndarray
    sub: np.ndarray
    base: np.ndarray
    c: np.ndarray
    c2: np.ndarray
    e: float
    V: float
    i0: np.ndarray = field(default=None)
    wt: np.ndarray = field(default=None)
    ph: np.ndarray = field(default=None)
    c2n: np.ndarray = field(default=None)   # out-of-band (noise-only) bins, used when the floor is profiled


class MultiPassWhittle:
    """Independent-section Whittle likelihood across passes; nuisances profiled by Fisher scoring.

    debias=True replaces the bin-sampled signal variance |H(f_k)|^2 S(f_k) by the exact expected
    periodogram of the rectangular-window record, i.e. |H|^2 S convolved with the Fejer kernel
    T sinc^2((f - f_k) T) (the debiased Whittle likelihood, Sykulski, Olhede, Guillaumin, Lilly & Early, Biometrika 106(2), 2019). This
    matters when H has structure on the bin scale (e.g. multi-wheel cross terms with ripple period
    V/d close to 1/T). The kernel is evaluated on a grid M times finer than the bins, truncated at
    +-Kb bins, over the analysis support (the band the record was filtered to).
    """

    def __init__(self, passes: list[dict], W_meas, sigma_W: float, rough: Roughness, family: Family,
                 mask=None, debias: bool = False, M: int = 4, Kb: int = 120, support=(F_LO - 5, F_HI),
                 fit_noise: bool = False, exact_subband: bool = False, smooth_sigma_db: float | None = None):
        """mask(pass dict) -> boolean array over the pass's bins (True = keep); None keeps all.

        fit_noise: the per-pass noise floor e_i is a profiled nuisance, estimated jointly from the
        in-band bins and the record's out-of-band (noise-only) bins, instead of being plugged in
        from the out-of-band mean.

        exact_subband (debias only): the roughness-level scoring step uses the exact derivative of each
        bin's kernel-smoothed variance with respect to every sub-band level (the kernel mixes neighbouring
        sub-bands) and the full sub-band Fisher matrix, instead of attributing a bin's variance to its
        own sub-band. Its fixed point is then the exact profile maximum.

        smooth_sigma_db (debias only; implies exact_subband): Gaussian random-walk prior on the log
        sub-band levels, log g_{s+1} - log g_s ~ N(0, sigma^2) with sigma given in dB of power. It
        regularises the K-per-third-octave nuisance levels without reducing K.
        """
        self.smooth_prec = None
        if smooth_sigma_db is not None and debias:
            sig = smooth_sigma_db * math.log(10) / 10
            Dd = np.diff(np.eye(rough.n_sub), axis=0)
            self.smooth_L = (Dd.T @ Dd) / sig**2
            self.smooth_prec = 1 / sig**2
            exact_subband = True
        self.exact_subband = exact_subband and debias
        self.fit_noise = fit_noise
        self.fam = family
        self.rough = rough
        self.lw_meas = np.log(np.asarray(W_meas, float))
        self.sW = sigma_W
        self.S = rough.n_sub
        self.debias = debias
        self.P: list[PassPrep] = []
        for p in passes:
            Om = 2 * np.pi * p["f"] / p["V"]
            s = rough.subband(Om)
            ok = s >= 0
            if mask is not None:
                ok &= mask(p)
            dOm = 2 * np.pi * (1 / p["T"]) / p["V"]
            pp = PassPrep(p["f"][ok], p["k"][ok], s[ok], 2 * rough.density(Om[ok]) * dOm, p["c"][ok],
                          np.abs(p["c"][ok]) ** 2, p["e_noise"], p["V"])
            if fit_noise:
                pp.c2n = np.abs(p["c_noise"]) ** 2
            if debias:
                T = p["T"]
                m0 = int(math.ceil(max(support[0], pp.f.min() - Kb / T) * M * T))
                m1 = int(math.floor(min(support[1], pp.f.max() + Kb / T) * M * T))
                fm = np.arange(m0, m1 + 1) / (M * T)
                Omm = 2 * np.pi * fm / p["V"]
                sm_ = rough.subband(Omm)
                inb = sm_ >= 0
                basem = np.zeros(fm.size)
                basem[inb] = 2 * rough.density(Omm[inb]) * dOm
                from scipy.sparse import csr_matrix
                rows, cols, vals = [], [], []
                for r, fk in enumerate(pp.f):
                    lo = np.searchsorted(fm, fk - Kb / T)
                    hi = np.searchsorted(fm, fk + Kb / T, side="right")
                    rows.append(np.full(hi - lo, r))
                    cols.append(np.arange(lo, hi))
                    vals.append(np.sinc((fm[lo:hi] - fk) * T) ** 2 / M)
                pp.fm, pp.subm, pp.basem = fm, np.where(inb, sm_, 0), basem
                pp.K = csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                                  shape=(pp.f.size, fm.size))
                if exact_subband:
                    pp.E = csr_matrix((np.ones(int(inb.sum())), (np.flatnonzero(inb), sm_[inb])), shape=(fm.size, rough.n_sub))
            self.P.append(pp)
        self.used = np.unique(np.concatenate([p.sub for p in self.P]))
        self._grid_ready = False
        self.n_eval, self.t_eval, self._warm = 0, 0.0, None

    # -- H at the bins (or on the fine grid, debias) of every pass
    def _prep_grid(self, tab: Table):
        for p in self.P:
            j = np.clip(np.searchsorted(tab.f, p.f) - 1, 0, tab.f.size - 2)
            p.i0, p.wt = j, (p.f - tab.f[j]) / (tab.f[j + 1] - tab.f[j])
            p.ph = np.exp(1j * 2 * np.pi * p.f[:, None] * tab.d[None, :] / p.V)
            if self.debias:
                j = np.clip(np.searchsorted(tab.f, p.fm) - 1, 0, tab.f.size - 2)
                p.i0m, p.wtm = j, (p.fm - tab.f[j]) / (tab.f[j + 1] - tab.f[j])
                p.phm = np.exp(1j * 2 * np.pi * p.fm[:, None] * tab.d[None, :] / p.V)
        self._grid_ready = True

    def _H(self, tab: Table, lw: np.ndarray, deriv: bool = False, fine: bool = False):
        if not self._grid_ready:
            self._prep_grid(tab)
        Gs = tab.spl(lw)
        dGs = tab.spl(lw, 1) if deriv else None
        H, dH = [], []
        for i, p in enumerate(self.P):
            i0, wt, ph = (p.i0m, p.wtm, p.phm) if fine else (p.i0, p.wt, p.ph)
            g = (1 - wt)[:, None] * Gs[i, i0] + wt[:, None] * Gs[i, i0 + 1]
            H.append((g * ph).sum(1))
            if deriv:
                dg = (1 - wt)[:, None] * dGs[i, i0] + wt[:, None] * dGs[i, i0 + 1]
                dH.append((dg * ph).sum(1))
        return (H, dH) if deriv else H

    def _A(self, tab: Table, lw: np.ndarray, logg: np.ndarray, deriv: bool = False):
        """Signal part of the bin variance, a_k, and d a_k / d log W, for every pass."""
        out = self._H(tab, lw, deriv=deriv, fine=self.debias)
        H, dH = out if deriv else (out, None)
        A, dA = [], []
        for i, p in enumerate(self.P):
            if self.debias:
                q = p.basem * np.exp(logg[p.subm])
                if self.exact_subband:
                    p._wfine = np.abs(H[i]) ** 2 * q
                A.append(p.K @ (np.abs(H[i]) ** 2 * q))
                if deriv:
                    dA.append(p.K @ (2 * np.real(np.conj(H[i]) * dH[i]) * q))
            else:
                q = p.base * np.exp(logg[p.sub])
                A.append(np.abs(H[i]) ** 2 * q)
                if deriv:
                    dA.append(2 * np.real(np.conj(H[i]) * dH[i]) * q)
        return (A, dA) if deriv else A

    def _nuisance_solve(self, tab: Table, logg, lw, tol=1e-7, max_it=80):
        """Fisher scoring; with debias each bin's signal variance is attributed to its own sub-band."""
        N = len(self.P)
        for it in range(max_it):
            A, dA = self._A(tab, lw, logg, deriv=True)
            gnum, gden, wstep = np.zeros(self.S), np.zeros(self.S), np.zeros(N)
            Fg = np.zeros((self.S, self.S)) if self.exact_subband else None
            for i, p in enumerate(self.P):
                a = A[i]
                v = a + p.e
                r = p.c2 / v - 1
                if self.exact_subband:   # D[k, s] = d a_k / d log g_s (exact, kernel mixes sub-bands)
                    D = (p.K.multiply(p._wfine[None, :]) @ p.E).tocsr()
                    gnum += D.T @ (r / v)
                    Dv = D.multiply((1 / v)[:, None]).tocsr()
                    Fg += (Dv.T @ Dv).toarray()
                else:
                    gnum += np.bincount(p.sub, a / v * r, minlength=self.S)
                    gden += np.bincount(p.sub, (a / v) ** 2, minlength=self.S)
                da = dA[i] / v
                wstep[i] = (da @ r - (lw[i] - self.lw_meas[i]) / self.sW**2) / (da @ da + 1 / self.sW**2)
            if self.exact_subband:
                if self.smooth_prec is not None:
                    gnum -= self.smooth_L @ logg
                    Fg += self.smooth_L
                act = np.diag(Fg) > 0
                gstep = np.zeros(self.S)
                Fa = Fg[np.ix_(act, act)]
                gstep[act] = np.linalg.solve(Fa + 1e-12 * np.trace(Fa) / max(act.sum(), 1) * np.eye(act.sum()), gnum[act])
            else:
                gstep = np.where(gden > 0, gnum / np.maximum(gden, 1e-300), 0.0)
            logg = logg + np.clip(gstep, -2, 2)
            lw = lw + np.clip(wstep, -0.1, 0.1)
            estep = np.zeros(N)
            if self.fit_noise:  # Fisher scoring on log e_i (in-band bins + noise-only bins)
                for i, p in enumerate(self.P):
                    v = A[i] + p.e
                    q = p.e / v
                    sc = q @ (p.c2 / v - 1) + np.sum(p.c2n / p.e - 1)
                    estep[i] = np.clip(sc / (q @ q + p.c2n.size), -1, 1)
                    p.e = p.e * math.exp(estep[i])
            if max(np.abs(gstep).max(), np.abs(wstep).max(), np.abs(estep).max()) < tol:
                break
        return logg, lw, it + 1

    def _nll(self, tab, logg, lw):
        A = self._A(tab, lw, logg)
        out = 0.0
        for i, p in enumerate(self.P):
            v = A[i] + p.e
            out += np.sum(np.log(v) + p.c2 / v)
            if self.fit_noise:
                out += np.sum(math.log(p.e) + p.c2n / p.e)
        if self.smooth_prec is not None:
            out += 0.5 * float(logg @ self.smooth_L @ logg)
        return float(out + 0.5 * np.sum(((lw - self.lw_meas) / self.sW) ** 2))

    def theta(self, phi) -> dict:
        return {nm: math.exp(x) for nm, x in zip(self.fam.names, phi)}

    def profile_nll(self, phi, return_state=False):
        t0 = time.perf_counter()
        tab = self.fam.table(self.theta(phi))
        logg0, lw0 = (np.zeros(self.S), self.lw_meas.copy()) if self._warm is None else self._warm
        logg, lw, nit = self._nuisance_solve(tab, logg0.copy(), lw0.copy())
        if self._warm is not None:
            self._warm = (logg, lw)
        nll = self._nll(tab, logg, lw)
        self.n_eval += 1
        self.t_eval += time.perf_counter() - t0
        return (nll, {"logg": logg, "lw": lw, "inner_iters": nit}) if return_state else nll

    def fit(self, phi0, steps=None) -> dict:
        t0 = time.perf_counter()
        phi0 = np.asarray(phi0, float)
        d = phi0.size
        steps = np.r_[0.15, 0.3, [0.2] * (d - 2)][:d] if steps is None else np.asarray(steps)
        self._warm = None
        _, st = self.profile_nll(phi0, return_state=True)
        self._warm = (st["logg"], st["lw"])
        simplex = np.vstack([phi0] + [phi0 + np.eye(d)[j] * steps[j] for j in range(d)])
        res = minimize(self.profile_nll, phi0, method="Nelder-Mead",
                       options={"xatol": 1e-4, "fatol": 1e-3, "maxiter": 200 * d, "initial_simplex": simplex})
        phi = res.x
        f0, st = self.profile_nll(phi, return_state=True)
        self._warm = (st["logg"], st["lw"])
        Hs = self._hessian(phi, f0)
        ev = np.linalg.eigvalsh(Hs)
        se = np.sqrt(np.diag(np.linalg.inv(Hs))) if ev.min() > 0 else np.full(d, np.inf)
        self.phi_hat, self.nll_hat, self.se_hat = phi, f0, se
        return {"phi": phi.tolist(), "se_log": se.tolist(), "nll": float(f0), "n_iter": int(res.nit),
                "converged": bool(res.success), "wall_fit_s": time.perf_counter() - t0, "n_eval": self.n_eval,
                "s_per_eval": self.t_eval / max(self.n_eval, 1), "profile_hessian": Hs.tolist(),
                "logg": st["logg"].tolist(), "lw": st["lw"].tolist()}

    def _hessian(self, phi, f0):
        d = phi.size
        h = np.r_[0.005, 0.03, [0.01] * (d - 2)][:d]
        Hs = np.zeros((d, d))
        E = np.eye(d)
        for a in range(d):
            Hs[a, a] = (self.profile_nll(phi + E[a] * h[a]) - 2 * f0 + self.profile_nll(phi - E[a] * h[a])) / h[a] ** 2
        for a in range(d):
            for b in range(a + 1, d):
                ea, eb = E[a] * h[a], E[b] * h[b]
                Hs[a, b] = Hs[b, a] = (self.profile_nll(phi + ea + eb) - self.profile_nll(phi + ea - eb)
                                       - self.profile_nll(phi - ea + eb) + self.profile_nll(phi - ea - eb)) / (4 * h[a] * h[b])
        return Hs

    # -- profile-likelihood interval for one parameter
    def _pl(self, a: int, x: float, start: np.ndarray) -> tuple[float, np.ndarray]:
        """min over the other globals of the profile NLL with phi[a] = x."""
        d = start.size
        others = [j for j in range(d) if j != a]

        def f(z):
            phi = start.copy()
            phi[a] = x
            phi[others] = z
            return self.profile_nll(phi)
        if not others:
            phi = start.copy()
            phi[a] = x
            return float(self.profile_nll(phi)), phi
        if len(others) == 1:
            z0 = start[others[0]]
            r = minimize_scalar(lambda z: f(np.array([z])), bracket=(z0 - 0.05, z0 + 0.05), tol=1e-5)
            zbest = np.array([r.x])
            val = r.fun
        else:
            r = minimize(f, start[others], method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-4})
            zbest, val = r.x, r.fun
        out = start.copy()
        out[a] = x
        out[others] = zbest
        return float(val), out

    def profile_interval(self, a: int = 0, level: float = 0.90, max_iter: int = 6) -> dict:
        """Interval {x: 2 [pl(x) - nll_hat] <= chi2_1(level)} by quadratic-corrected secant steps."""
        crit = chi2.ppf(level, 1) / 2.0
        phi, f0, se = self.phi_hat, self.nll_hat, self.se_hat[a]
        z = math.sqrt(2 * crit)
        bounds = []
        n0 = self.n_eval
        for side in (-1, 1):
            x = phi[a] + side * z * se
            start = phi.copy()
            pts = []
            for _ in range(max_iter):
                val, start = self._pl(a, x, start)
                dv = val - f0
                pts.append((x, dv))
                if abs(dv - crit) < 0.005:
                    break
                if dv <= 0:
                    x = phi[a] + 2 * (x - phi[a])
                    continue
                x = phi[a] + (x - phi[a]) * math.sqrt(crit / dv)
            bounds.append(pts[-1][0] if abs(pts[-1][1] - crit) < 0.05 else float("nan"))
        return {"lo": bounds[0], "hi": bounds[1], "level": level, "n_eval": self.n_eval - n0}

    # -- expected Fisher information (CRB) under this observation model
    def _fisher_parts(self, phi, logg, lw, h: float = 1e-4, exact_sub: bool = False):
        """Expected Fisher J over (globals, used sub-band levels, per-pass log W) and per-pass (D, v).

        exact_sub (debias only): the sub-band columns use the exact kernel-mixed derivative
        d v_k / d log g_s instead of attributing each bin to its own sub-band.
        """
        phi = np.asarray(phi, float)
        d = phi.size
        tab0 = self.fam.table(self.theta(phi))
        A, dAw = self._A(tab0, lw, logg, deriv=True)
        dAt = []
        for a in range(d):
            e = np.eye(d)[a] * h
            Ap = self._A(self.fam.table(self.theta(phi + e)), lw, logg)
            Am = self._A(self.fam.table(self.theta(phi - e)), lw, logg)
            dAt.append([(x - y) / (2 * h) for x, y in zip(Ap, Am)])
        N, used = len(self.P), self.used
        smap = -np.ones(self.S, int)
        smap[used] = np.arange(used.size)
        ne = N if self.fit_noise else 0
        n = d + used.size + N + ne
        J = np.zeros((n, n))
        parts = []
        for i, p in enumerate(self.P):
            v = A[i] + p.e
            D = np.zeros((p.f.size, n))
            for a in range(d):
                D[:, a] = dAt[a][i] / v
            if exact_sub and self.debias:
                from scipy.sparse import csr_matrix
                q = p.basem * np.exp(logg[p.subm])
                Hf = self._H(tab0, lw, fine=True)[i]
                inb = (p.basem > 0) & (smap[p.subm] >= 0)   # sub-bands reached only through the kernel stay fixed
                E = csr_matrix((np.ones(int(inb.sum())), (np.flatnonzero(inb), smap[p.subm[inb]])), shape=(p.fm.size, used.size))
                Dsub = (p.K.multiply((np.abs(Hf) ** 2 * q)[None, :]) @ E).toarray()
                D[:, d:d + used.size] = Dsub / v[:, None]
            else:
                D[np.arange(p.f.size), d + smap[p.sub]] = A[i] / v
            D[:, d + used.size + i] = dAw[i] / v
            if self.fit_noise:
                D[:, d + used.size + N + i] = p.e / v
                J[d + used.size + N + i, d + used.size + N + i] += p.c2n.size
            J += D.T @ D
            parts.append((D, v))
        J[d + used.size:d + used.size + N, d + used.size:d + used.size + N] += np.eye(N) / self.sW**2
        if self.smooth_prec is not None:
            J[d:d + used.size, d:d + used.size] += self.smooth_L[np.ix_(used, used)]
        return J, parts, d, n

    def misspec_bias(self, phi, logg, lw, fam_true: Family, theta_true: dict, h: float = 1e-4) -> dict:
        """First-order bias of the ML estimate when the data come from fam_true(theta_true).

        theta_hat - theta ~= J^-1 E[score at the truth], E[score] = sum_k D_k (v_true,k / v_k - 1),
        with all nuisances (sub-band levels, per-pass log W) free; returns the bias of the globals (log
        units) and the CRB of the fitted model.
        """
        J, parts, d, n = self._fisher_parts(phi, logg, lw, h)
        At = self._A(fam_true.table(theta_true), lw, logg)
        sc = np.zeros(n)
        for (D, v), a_t, p in zip(parts, At, self.P):
            sc += D.T @ ((a_t + p.e) / v - 1.0)
        s_ = 1 / np.sqrt(np.diag(J))
        Ci = np.linalg.inv(J * np.outer(s_, s_)) * np.outer(s_, s_)
        b = Ci @ sc
        return {"bias_log": b[:d].tolist(), "crb_log": [float(math.sqrt(Ci[a, a])) for a in range(d)]}

    def pseudo_true(self, fam_true: Family, theta_true: dict, logg, lw, phi0, steps=None) -> dict:
        """Asymptotic (KL) limit of the estimate when the data come from fam_true(theta_true).

        Every periodogram value |c|^2 is replaced by its expectation under the true model (same bins,
        floors, payloads; W measured exactly), and the profile likelihood is maximised: the result is
        the large-sample limit of the ML estimate, without linearisation. Returns the fit dict.
        """
        At = self._A(fam_true.table(theta_true), np.asarray(lw, float), np.asarray(logg, float))
        saved = [p.c2 for p in self.P], self.lw_meas.copy()
        for p, a in zip(self.P, At):
            p.c2 = a + p.e
        self.lw_meas = np.asarray(lw, float).copy()
        try:
            return self.fit(phi0, steps=steps)
        finally:
            for p, c2 in zip(self.P, saved[0]):
                p.c2 = c2
            self.lw_meas = saved[1]

    def sandwich_cov(self, phi, logg, lw, cluster: str = "bin", h: float = 1e-4, block_bins: int = 61,
                     exact_sub: bool = False, clusters_list=None) -> dict:
        """Robust (sandwich) covariance of the globals, J^-1 M J^-1 over all parameters.

        Per-bin score contributions s_ik = D_ik (|c_ik|^2 / v_ik - 1) (plus the WIM-prior score of each
        pass as its own cluster) are summed within clusters: cluster="bin" groups the same DFT bin
        (same spatial wavenumber) across passes, which is where a shared roughness profile correlates
        passes; cluster="pass" groups by pass; cluster="block" groups runs of block_bins adjacent bins
        within each pass (correlation between neighbouring bins of one record, e.g. through the window
        kernel). M = sum over clusters of s s^T; J is the expected Fisher. clusters_list evaluates several
        clusterings at once (one Fisher computation) and returns a dict keyed by "<cluster>" or
        "block<B>".
        """
        J, parts, d, n = self._fisher_parts(phi, logg, lw, h, exact_sub=exact_sub)
        if clusters_list is not None:
            return {name: self._sandwich_from(J, parts, d, n, c, b, lw) for name, c, b in clusters_list}
        return self._sandwich_from(J, parts, d, n, cluster, block_bins, lw)

    def _sandwich_from(self, J, parts, d, n, cluster, block_bins, lw):
        clusters: dict = {}
        N = len(self.P)
        off_w = n - N - (N if self.fit_noise else 0)
        for i, ((D, v), p) in enumerate(zip(parts, self.P)):
            S = D * (p.c2 / v - 1)[:, None]
            if cluster == "pass":
                clusters[("pass", i)] = clusters.get(("pass", i), 0) + S.sum(0)
            elif cluster == "block":
                blk = (np.asarray(p.k) - int(p.k[0])) // block_bins
                for b_ in np.unique(blk):
                    clusters[("blk", i, int(b_))] = S[blk == b_].sum(0)
            else:
                for kk, row in zip(p.k, S):
                    clusters[int(kk)] = clusters.get(int(kk), 0) + row
            pr = np.zeros(n)
            pr[off_w + i] = -(lw[i] - self.lw_meas[i]) / self.sW**2
            clusters[("prior", i)] = pr
        Sm = np.array([np.asarray(v, float) if np.ndim(v) else np.zeros(n) for v in clusters.values()])
        M = Sm.T @ Sm
        sc = 1 / np.sqrt(np.diag(J))
        Ci = np.linalg.inv(J * np.outer(sc, sc)) * np.outer(sc, sc)
        V = Ci @ M @ Ci
        return {"se_log_sandwich": [float(math.sqrt(max(V[a, a], 0))) for a in range(d)],
                "se_log_model": [float(math.sqrt(Ci[a, a])) for a in range(d)], "n_clusters": len(clusters)}

    def expected_fisher(self, phi, logg, lw, h: float = 1e-4) -> dict:
        J, parts, d, n = self._fisher_parts(phi, logg, lw, h)
        sc = 1 / np.sqrt(np.diag(J))
        Ci = np.linalg.inv(J * np.outer(sc, sc)) * np.outer(sc, sc)
        return {"crb_log": [float(math.sqrt(Ci[a, a])) for a in range(d)], "n_params": int(n),
                "cov_globals": Ci[:d, :d].tolist()}
