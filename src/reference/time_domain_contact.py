"""Multi-wheel generator with nonlinear Hertzian contact (inverse-crime check).

Everything except the contact law is the linear rail-coupled model of src/analysis/multiwheel.py: FE
wheelsets (instrumented and neighbours), the infinite Timoshenko rail on a hysteretic foundation and the
same wheel layout. Contact at wheel k:

    delta_k(t) = z_k(t) - (B F)_k(t),     B = A^w + A^r (wheel and rail receptances), z_k(t) = r(V t + d_k),
    F_k(t)     = C_H [delta_0 + delta_k(t)]_+^(3/2) - F_0                 (dynamic part of the contact force),

with F_0 = W g / 2, delta_0 = (F_0 / C_H)^(2/3), and C_H set so that the linearisation
1.5 C_H^(2/3) F_0^(1/3) equals the frequency-domain k_H(W) = k_H0 (W/W0)^(1/3).

The hysteretic foundation is not causal, so the linear operators are applied in the frequency domain over
the whole (padded) record, and the nonlinearity is handled by a fixed-point (harmonic-balance) iteration:
writing F = k_H delta + F_nl(delta),
    F = (I + k_H B)^-1 (k_H z + F_nl(delta)),   delta = z - B F,
starting from F_nl = 0 (the linear solution) and evaluating F_nl pointwise in time. With F_nl = 0 the
result is exactly the frequency-domain model. The record is padded on both sides by `pad` seconds and the
middle N_REVS revolutions are kept, so wrap-around transients have decayed.

Roughness is synthesised in space with the per-bin variance of generate_pass (E|Z|^2 = 2 G(Omega) g_s
dOmega, only inside the analysis band at the pass speed). The axle-box acceleration is -w^2 H_ca F_j;
noise is added at the stated SNR with the generate_pass convention; the same pass dictionary is returned.
"""

from __future__ import annotations

import math

import numpy as np

from src.inverse.multipass import F_HI, F_LO, FS, N_REVS, NOISE_BAND

G0 = 9.80665


class NonlinearContactGenerator:
    def __init__(self, mw, th: dict, fs_sim: float = 8000.0, pad: float = 0.8):
        self.mw, self.th, self.fs, self.pad = mw, dict(th), fs_sim, pad
        self.N = mw.layout.size
        self.d = mw.d.copy()
        self._rail = {}

    def _operators(self, W: float, nfft: int):
        th = dict(self.th, W=float(W))
        f = np.fft.rfftfreq(nfft, 1 / self.fs)
        w = 2 * np.pi * f
        w0 = w.copy()
        w0[0] = w[1] * 1e-3
        if nfft not in self._rail:
            self._rail[nfft] = self.mw.rail(w0, th)
        R = self._rail[nfft]
        Hw_i, Hca = self.mw.wheelset_modal(th, w0)
        Hw_n, _ = self.mw.wheelset_modal(dict(th, **self.mw.neigh), w0)
        B = R.copy()
        for k in range(self.N):
            B[:, k, k] += Hw_i if k == self.mw.j else Hw_n
        kH = self.mw.kH(th)
        Ainv = np.linalg.inv(np.eye(self.N)[None] + kH * B)
        return B, Ainv, kH, Hca, w

    def simulate(self, rough, g, V: float, W: float, r0: float, snr_db: float, rng, contact: str = "hertz",
                 tol: float = 1e-10, max_it: int = 300) -> dict:
        T = N_REVS * 2 * np.pi * r0 / V
        n2 = int(round(T * FS))
        T = n2 / FS
        nrec = int(round(T * self.fs))
        npad = int(round(self.pad * self.fs))
        ntot = nrec + 2 * npad
        nfft = int(2 ** math.ceil(math.log2(ntot)))
        B, Ainv, kH, Hca, w = self._operators(W, nfft)
        F0 = W * 1000.0 * G0 / 2
        CH = (kH / 1.5) ** 1.5 / math.sqrt(F0)
        d0 = (F0 / CH) ** (2 / 3)
        # roughness in space (generate_pass variance convention), analysis band at this speed
        dt = 1 / self.fs
        span = self.d.max() - self.d.min()
        dx = V * dt / 4
        nx = int(2 ** math.ceil(math.log2((V * nfft * dt + span + 1.0) / dx)))
        dOm = 2 * np.pi / (nx * dx)
        Om = np.arange(nx // 2 + 1) * dOm
        fb = Om * V / (2 * np.pi)
        band = (fb >= max(F_LO - 5, 0.1)) & (fb <= F_HI)
        s = rough.subband(Om[band])
        ok = s >= 0
        var = np.zeros(band.sum())
        var[ok] = 2 * rough.density(Om[band][ok]) * g[s[ok]] * dOm
        Z = np.zeros(Om.size, complex)
        Z[band] = np.sqrt(var / 2) * (rng.standard_normal(var.size) + 1j * rng.standard_normal(var.size))
        rx = np.fft.irfft(Z * nx / 2, n=nx)                             # r(x) = Re sum Z e^{i Om x}
        x0 = -self.d.min() + 0.5
        t = np.arange(nfft) * dt
        xg = np.arange(nx) * dx
        z = np.stack([np.interp(x0 + V * t + self.d[k], xg, rx) for k in range(self.N)])
        Zf = np.fft.rfft(z, axis=1).T                                      # (nf, N)
        # fixed-point iteration
        Fnl = np.zeros_like(z)
        it, err, relax, prev = 0, 0.0, 1.0, np.inf
        for it in range(1, max_it + 1):
            rhs = kH * Zf + np.fft.rfft(Fnl, axis=1).T
            Ff = np.einsum("fij,fj->fi", Ainv, rhs)
            delta = np.fft.irfft((Zf - np.einsum("fij,fj->fi", B, Ff)).T, n=nfft, axis=1)
            if contact != "hertz":
                break
            c = np.maximum(d0 + delta, 0.0)
            new = CH * c**1.5 - F0 - kH * delta
            err = float(np.max(np.abs(new - Fnl)) / F0)
            if err > prev:                         # under-relax when the fixed point stops contracting
                relax = max(relax * 0.5, 0.05)
            prev = err
            Fnl = Fnl + relax * (new - Fnl)
            if err < tol:
                break
        Fj_f = Ff[:, self.mw.j]
        acc = np.fft.irfft(-(w**2) * Hca * Fj_f, n=nfft)
        y = acc[npad:npad + nrec]
        dl = delta[self.mw.j, npad:npad + nrec]
        C8 = 2 * np.fft.rfft(y) / nrec
        fk = np.arange(C8.size) / T
        inband = (fk >= max(F_LO - 5, 0.1)) & (fk <= F_HI)
        Ps = 0.5 * np.sum(np.abs(C8[inband]) ** 2)
        en = 4 * (Ps / 10 ** (snr_db / 10)) / n2
        keep = (fk >= F_LO) & (fk <= F_HI)
        nb = (fk >= NOISE_BAND[0]) & (fk <= NOISE_BAND[1])
        c = C8[keep] + np.sqrt(en / 2) * (rng.standard_normal(keep.sum()) + 1j * rng.standard_normal(keep.sum()))
        cn = np.sqrt(en / 2) * (rng.standard_normal(nb.sum()) + 1j * rng.standard_normal(nb.sum()))
        return {"f": fk[keep], "c": c, "k": np.arange(C8.size)[keep], "V": V, "T": T, "e_noise": float(np.mean(np.abs(cn) ** 2)),
                "e_noise_true": en, "c_noise": cn, "contact": contact, "iterations": it, "fixed_point_err": err,
                "converged": bool(contact != "hertz" or err < tol),
                "delta0_um": d0 * 1e6, "delta_rms_um": float(np.std(dl) * 1e6), "delta_min_ratio": float(np.min(d0 + dl) / d0),
                "contact_loss_fraction": float(np.mean(d0 + dl <= 0))}
