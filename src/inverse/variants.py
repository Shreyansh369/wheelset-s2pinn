"""Likelihood variants of the multi-pass Whittle estimator (tasks (b) and (c)).

WheelLineWhittle (b-ii, tachometer): a periodic wheel-roughness profile puts a deterministic line at
every order bin k = 20 n of an angle-synchronous 20-revolution record. With a once-per-revolution
tachometer the record starts at the same wheel angle on every pass, so order n contributes the same
complex roughness coefficient w_n to every pass:
    c_ik ~ CN(H_ik w_n, v_ik)  at order bins,   c_ik ~ CN(0, v_ik) elsewhere,
with v_ik the rail-roughness + floor variance of the base model. The w_n (2 real each) are shared
nuisance parameters, profiled in closed form (weighted least squares across passes).
(b-i, notch) needs no new likelihood: drop the order bins with a mask.

SharedSectionWhittle (c): repeated passes over the same section. With records aligned in position
(same start point, 20 revolutions = same length L), DFT bin k of every pass samples the same spatial
Fourier coefficient R_k ~ CN(0, s_k) of the rail roughness, s_k = 2 G_iso(gamma_k) dgamma g_s(k):
    c_.k = h_.k R_k + noise,   Sigma_k = s_k h h^H + E,  E = diag(e_i)
(rank one plus diagonal). log det and the quadratic form follow from Sherman-Morrison:
    nll_k = log(1 + s a) - s |u|^2 / (1 + s a) + sum_i (log e_i + |c_i|^2 / e_i),
    a = sum_i |h_i|^2 / e_i,  u = sum_i conj(h_i) c_i / e_i.
Nuisances (log g per sub-band, log W per pass) are profiled with L-BFGS on the analytic gradient.
Expected Fisher: I_ab = sum_k tr(S^-1 dS_a S^-1 dS_b) with dS_a = s (x_a h^H + h x_a^H), which gives
s^2 [2 Re(p_a p_b) + 2 q Re(r_ab)], p_a = h^H S^-1 x_a, q = h^H S^-1 h, r_ab = x_a^H S^-1 x_b.
"""

from __future__ import annotations

import math
import time

import numpy as np
from scipy.optimize import minimize

from src.inverse.multipass import N_REVS, MultiPassWhittle, Table


# --------------------------------------------------------------------------- (b) wheel lines, tachometer
class WheelLineWhittle(MultiPassWhittle):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.line = [p.k % N_REVS == 0 for p in self.P]
        orders = np.unique(np.concatenate([p.k[m] // N_REVS for p, m in zip(self.P, self.line)]))
        self.orders = orders
        self.oidx = [np.searchsorted(orders, p.k[m] // N_REVS) for p, m in zip(self.P, self.line)]
        self.L = orders.size
        self.w_hat = np.zeros(self.L, complex)

    def _lines(self, H, logg, lw):
        num, den = np.zeros(self.L, complex), np.zeros(self.L)
        for i, p in enumerate(self.P):
            m = self.line[i]
            v = np.abs(H[i][m]) ** 2 * p.base[m] * np.exp(logg[p.sub[m]]) + p.e
            np.add.at(num, self.oidx[i], np.conj(H[i][m]) * p.c[m] / v)
            np.add.at(den, self.oidx[i], np.abs(H[i][m]) ** 2 / v)
        return np.where(den > 0, num / np.maximum(den, 1e-300), 0.0)

    def _mean(self, i, H_i, w):
        mu = np.zeros(H_i.size, complex)
        m = self.line[i]
        mu[m] = H_i[m] * w[self.oidx[i]]
        return mu

    def _nuisance_solve(self, tab: Table, logg, lw, tol=1e-7, max_it=120):
        N = len(self.P)
        for it in range(max_it):
            H, dH = self._H(tab, lw, deriv=True)
            w = self._lines(H, logg, lw)
            gnum, gden, wstep = np.zeros(self.S), np.zeros(self.S), np.zeros(N)
            for i, p in enumerate(self.P):
                g = np.exp(logg[p.sub])
                a = np.abs(H[i]) ** 2 * p.base * g
                v = a + p.e
                res = p.c - self._mean(i, H[i], w)
                r = np.abs(res) ** 2 / v - 1
                gnum += np.bincount(p.sub, a / v * r, minlength=self.S)
                gden += np.bincount(p.sub, (a / v) ** 2, minlength=self.S)
                da = 2 * np.real(np.conj(H[i]) * dH[i]) * p.base * g / v
                dmu = self._mean(i, dH[i], w)
                score = da @ r + np.sum(2 * np.real(np.conj(res) * dmu) / v) - (lw[i] - self.lw_meas[i]) / self.sW**2
                info = da @ da + np.sum(2 * np.abs(dmu) ** 2 / v) + 1 / self.sW**2
                wstep[i] = score / info
            gstep = np.where(gden > 0, gnum / np.maximum(gden, 1e-300), 0.0)
            logg = logg + np.clip(gstep, -2, 2)
            lw = lw + np.clip(wstep, -0.1, 0.1)
            if max(np.abs(gstep).max(), np.abs(wstep).max()) < tol:
                break
        H = self._H(tab, lw)
        self.w_hat = self._lines(H, logg, lw)
        return logg, lw, it + 1

    def _nll(self, tab, logg, lw):
        H = self._H(tab, lw)
        w = self._lines(H, logg, lw)
        out = 0.0
        for i, p in enumerate(self.P):
            v = np.abs(H[i]) ** 2 * p.base * np.exp(logg[p.sub]) + p.e
            out += np.sum(np.log(v) + np.abs(p.c - self._mean(i, H[i], w)) ** 2 / v)
        return float(out + 0.5 * np.sum(((lw - self.lw_meas) / self.sW) ** 2))

    def expected_fisher(self, phi, logg, lw, w_true=None, h: float = 1e-4) -> dict:
        """Parameters: globals, sub-band levels, per-pass log W, Re w_n, Im w_n (shared lines)."""
        phi = np.asarray(phi, float)
        d = phi.size
        w = np.asarray(w_true, complex)
        tab0 = self.fam.table(self.theta(phi))
        H, dHw = self._H(tab0, lw, deriv=True)
        dHt = []
        for a in range(d):
            e = np.eye(d)[a] * h
            Hp, Hm = self._H(self.fam.table(self.theta(phi + e)), lw), self._H(self.fam.table(self.theta(phi - e)), lw)
            dHt.append([(x - y) / (2 * h) for x, y in zip(Hp, Hm)])
        N, used, L = len(self.P), self.used, self.L
        smap = -np.ones(self.S, int)
        smap[used] = np.arange(used.size)
        o_w = d + used.size + N
        n = o_w + 2 * L
        J = np.zeros((n, n))
        for i, p in enumerate(self.P):
            g = np.exp(logg[p.sub])
            v = np.abs(H[i]) ** 2 * p.base * g + p.e
            nb = p.f.size
            D = np.zeros((nb, n))  # variance part (d log v)
            for a in range(d):
                D[:, a] = 2 * np.real(np.conj(H[i]) * dHt[a][i]) * p.base * g / v
            D[np.arange(nb), d + smap[p.sub]] = np.abs(H[i]) ** 2 * p.base * g / v
            D[:, d + used.size + i] = 2 * np.real(np.conj(H[i]) * dHw[i]) * p.base * g / v
            J += D.T @ D
            m = self.line[i]
            if m.any():  # mean part: 2 Re(dmu_a^* dmu_b) / v at the order bins
                wl = w[self.oidx[i]]
                sv = np.sqrt(2 / v[m])
                Dm = np.zeros((m.sum(), n), complex)
                for a in range(d):
                    Dm[:, a] = dHt[a][i][m] * wl
                Dm[:, d + used.size + i] = dHw[i][m] * wl
                Dm[np.arange(m.sum()), o_w + self.oidx[i]] = H[i][m]
                Dm[np.arange(m.sum()), o_w + L + self.oidx[i]] = 1j * H[i][m]
                Dm *= sv[:, None]
                J += np.real(Dm.conj().T @ Dm)
        J[d + used.size:o_w, d + used.size:o_w] += np.eye(N) / self.sW**2
        dg = np.diag(J).copy()
        keep = dg > 0
        sc = np.zeros(n)
        sc[keep] = 1 / np.sqrt(dg[keep])
        Js = (J * np.outer(sc, sc))[np.ix_(keep, keep)]
        Ci = np.linalg.inv(Js) * np.outer(sc[keep], sc[keep])
        return {"crb_log": [float(math.sqrt(Ci[a, a])) for a in range(d)], "n_params": int(keep.sum())}


# --------------------------------------------------------------------------- (c) shared section
class SharedSectionWhittle(MultiPassWhittle):
    """Repeated passes over one section: rank-one-plus-noise covariance per spatial bin."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        ks = np.unique(np.concatenate([p.k for p in self.P]))
        self.ks = ks
        N = len(self.P)
        self.pos = [np.searchsorted(ks, p.k) for p in self.P]
        self.present = np.zeros((ks.size, N), bool)
        self.C = np.zeros((ks.size, N), complex)
        self.Einv = np.zeros((ks.size, N))
        base = np.zeros((ks.size, N))
        sub = -np.ones(ks.size, int)
        for i, p in enumerate(self.P):
            self.present[self.pos[i], i] = True
            self.C[self.pos[i], i] = p.c
            self.Einv[self.pos[i], i] = 1.0 / p.e
            base[self.pos[i], i] = p.base
            sub[self.pos[i]] = p.sub
        nb = self.present.sum(1)
        self.base_k = base.sum(1) / np.maximum(nb, 1)  # per-pass bases differ by T rounding only (~1e-4)
        self.sub_k = sub
        self.const = float(sum(np.sum(np.log(p.e) + p.c2 / p.e) for p in self.P))

    def _Hmat(self, tab, lw, deriv=False):
        out = self._H(tab, lw, deriv)
        H, dH = (out if deriv else (out, None))
        Hm = np.zeros((self.ks.size, len(self.P)), complex)
        dHm = np.zeros_like(Hm) if deriv else None
        for i in range(len(self.P)):
            Hm[self.pos[i], i] = H[i]
            if deriv:
                dHm[self.pos[i], i] = dH[i]
        return Hm, dHm

    def _terms(self, Hm, logg):
        s = self.base_k * np.exp(logg[self.sub_k])
        a = np.sum(np.abs(Hm) ** 2 * self.Einv, 1)
        u = np.sum(np.conj(Hm) * self.C * self.Einv, 1)
        D = 1 + s * a
        return s, a, u, D

    def _obj(self, x, tab):
        S, N = self.S, len(self.P)
        logg, lw = x[:S], x[S:]
        Hm, dHm = self._Hmat(tab, lw, deriv=True)
        s, a, u, D = self._terms(Hm, logg)
        u2 = np.abs(u) ** 2
        f = np.sum(np.log(D) - s * u2 / D) + 0.5 * np.sum(((lw - self.lw_meas) / self.sW) ** 2)
        dfds = a / D - u2 / D**2
        gg = np.bincount(self.sub_k, s * dfds, minlength=S)
        dfda = s / D + s**2 * u2 / D**2
        dfdu2 = -s / D
        da = 2 * np.real(np.conj(Hm) * dHm) * self.Einv                      # (nk, N)
        du2 = 2 * np.real(np.conj(u)[:, None] * np.conj(dHm) * self.C * self.Einv)
        gw = dfda @ da + dfdu2 @ du2 + (lw - self.lw_meas) / self.sW**2
        return f, np.concatenate([gg, gw])

    def _nuisance_solve(self, tab: Table, logg, lw, tol=1e-7, max_it=500):
        x0 = np.concatenate([logg, lw])
        r = minimize(self._obj, x0, args=(tab,), jac=True, method="L-BFGS-B",
                     options={"maxiter": max_it, "gtol": 1e-6, "ftol": 1e-13})
        return r.x[:self.S], r.x[self.S:], int(r.nit)

    def _nll(self, tab, logg, lw):
        f, _ = self._obj(np.concatenate([logg, lw]), tab)
        return float(f + self.const)

    def expected_fisher(self, phi, logg, lw, h: float = 1e-4) -> dict:
        phi = np.asarray(phi, float)
        d, N, S = phi.size, len(self.P), self.S
        tab0 = self.fam.table(self.theta(phi))
        Hm, dHw = self._Hmat(tab0, lw, deriv=True)
        dHt = []
        for a in range(d):
            e = np.eye(d)[a] * h
            Hp, _ = self._Hmat(self.fam.table(self.theta(phi + e)), lw)
            Hn, _ = self._Hmat(self.fam.table(self.theta(phi - e)), lw)
            dHt.append((Hp - Hn) / (2 * h))
        used = np.unique(self.sub_k)
        smap = -np.ones(S, int)
        smap[used] = np.arange(used.size)
        n = d + used.size + N
        J = np.zeros((n, n))
        s, a_, u, D = self._terms(Hm, logg)
        for kk in range(self.ks.size):
            pr = self.present[kk]
            h_ = Hm[kk, pr]
            ei = self.Einv[kk, pr]
            sk = s[kk]
            Winv = np.diag(ei) - sk * np.outer(ei * h_, np.conj(ei * h_)) / (1 + sk * np.sum(np.abs(h_) ** 2 * ei))
            q = float(np.real(np.conj(h_) @ Winv @ h_))
            # columns x_a (vectors over present passes)
            X = np.zeros((pr.sum(), n), complex)
            for a in range(d):
                X[:, a] = dHt[a][kk, pr]
            X[:, d + smap[self.sub_k[kk]]] = h_ / 2
            idx_w = d + used.size + np.nonzero(pr)[0]
            X[np.arange(pr.sum()), idx_w] = dHw[kk, pr]
            p = np.conj(h_) @ Winv @ X            # (n,)
            R = X.conj().T @ Winv @ X             # (n, n)
            J += sk**2 * (2 * np.real(np.outer(p, p)) + 2 * q * np.real(R))
        J[d + used.size:, d + used.size:] += np.eye(N) / self.sW**2
        dg = np.diag(J).copy()
        keep = dg > 0
        sc = np.zeros(n)
        sc[keep] = 1 / np.sqrt(dg[keep])
        Ci = np.linalg.inv((J * np.outer(sc, sc))[np.ix_(keep, keep)]) * np.outer(sc[keep], sc[keep])
        return {"crb_log": [float(math.sqrt(Ci[a, a])) for a in range(d)], "n_params": int(keep.sum())}
