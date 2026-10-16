"""Generator check: the time-domain (nonlinear-contact) generator with linear contact against the
frequency-domain model on identical inputs.

One pass (V = 85 km/h, W = 14 t, current config, 4-wheel layout): the time-domain generator's own
roughness inputs z_k(t) and its linear-contact acceleration y_TD(t) (noise-free, full padded record) are
compared with y_FD(t) = IFFT[H(f) Z_j(f)], where H is the frequency-domain model of the estimator's data
generator (MultiWheelModel.reference_H: direct solves, exact phase factors) and Z_j the spectrum of the
instrumented wheel's input. Reported over the kept record: relative L2 misfit; the spectral ratio
|Y_TD/Y_FD| over the support band (300-550 Hz) and the analysis band; and the apparent damping of the
support mode from each output spectrum (half-power width of the smoothed |Y/Z_j|^2 peak), plus the
complex-eigenvalue damping of the wheelset support mode. Also: the operator-level misfit between the
generator's modal operators and reference_H on the same frequency grid.
Writes results/p4/generator_check.json.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.p1_fe_direct import TRUTH  # noqa: E402
from experiments.p2_common import setup  # noqa: E402
from experiments.p2_multiwheel import KMH, models  # noqa: E402
from src.analysis.bound_scan import support_mode  # noqa: E402
from src.inverse.multipass import F_HI, F_LO, FS, N_REVS  # noqa: E402
from src.reference.time_domain_contact import NonlinearContactGenerator  # noqa: E402
from src.utils.results import save_result  # noqa: E402

V, W = 85.0 * KMH, 14.0


def half_power(f, p, lo=300.0, hi=550.0):
    sel = (f >= lo) & (f <= hi)
    ff, pp = f[sel], p[sel]
    k = int(np.argmax(pp))
    half = pp[k] / 2
    i = k
    while i > 0 and pp[i] > half:
        i -= 1
    j = k
    while j < pp.size - 1 and pp[j] > half:
        j += 1
    return float(ff[k]), float((ff[j] - ff[i]) / (2 * ff[k]))     # peak, zeta ~ bandwidth / (2 f)


def smooth(x, n=41):
    return np.convolve(x, np.ones(n) / n, mode="same")


def main():
    sm, thb, rough, _ = setup()
    mw = models(sm)[0]["4"]
    th = dict(thb, **TRUTH)
    gen = NonlinearContactGenerator(mw, th)
    rng = np.random.default_rng(7)
    g = np.ones(rough.n_sub)
    # --- reproduce the generator's linear solution with its own inputs (noise-free)
    T = N_REVS * 2 * np.pi * th["r0"] / V
    n2 = int(round(T * FS))
    T = n2 / FS
    nrec = int(round(T * gen.fs))
    npad = int(round(gen.pad * gen.fs))
    nfft = int(2 ** math.ceil(math.log2(nrec + 2 * npad)))
    B, Ainv, kH, Hca, w = gen._operators(W, nfft)
    dt = 1 / gen.fs
    span = gen.d.max() - gen.d.min()
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
    rx = np.fft.irfft(Z * nx / 2, n=nx)
    x0 = -gen.d.min() + 0.5
    t = np.arange(nfft) * dt
    xg = np.arange(nx) * dx
    z = np.stack([np.interp(x0 + V * t + gen.d[k], xg, rx) for k in range(gen.N)])
    Zf = np.fft.rfft(z, axis=1).T
    Ff = np.einsum("fij,fj->fi", Ainv, kH * Zf)
    y_td = np.fft.irfft(-(w**2) * Hca * Ff[:, mw.j], n=nfft)
    # --- frequency-domain model on the same input (instrumented wheel's roughness spectrum)
    f = np.fft.rfftfreq(nfft, dt)
    H = mw.reference_H(dict(th, W=W), V, np.arange(1.0, 1001.0, 0.25))(np.clip(f, 1.0, 1000.0))
    H[(f < F_LO - 5) | (f > 1000.0)] = 0.0
    y_fd = np.fft.irfft(H * Zf[:, mw.j], n=nfft)
    keep = slice(npad, npad + nrec)
    a, b = y_td[keep], y_fd[keep]
    rel_l2 = float(np.linalg.norm(a - b) / np.linalg.norm(b))
    Ya, Yb = np.fft.rfft(a), np.fft.rfft(b)
    fk = np.fft.rfftfreq(a.size, dt)
    sb = (fk >= 300) & (fk <= 550)
    ab = (fk >= F_LO) & (fk <= F_HI)
    ratio_support = float(np.sqrt(np.sum(np.abs(Ya[sb]) ** 2) / np.sum(np.abs(Yb[sb]) ** 2)))
    ratio_band = float(np.sqrt(np.sum(np.abs(Ya[ab]) ** 2) / np.sum(np.abs(Yb[ab]) ** 2)))
    # apparent support-mode damping: single wheel (no coupling ripple), output/input on the full record
    mw1 = models(sm)[0]["1"]
    g1 = NonlinearContactGenerator(mw1, th)
    B1, A1, kH1, Hca1, _ = g1._operators(W, nfft)
    H_td1 = -(w**2) * Hca1 * (A1[:, 0, 0] * kH1)
    H_fd1 = mw1.reference_H(dict(th, W=W), V, np.arange(1.0, 1001.0, 0.25))(np.clip(f, 1.0, 1000.0))
    op_misfit = float(np.max(np.abs(H_td1[ab[: 0] if False else (f >= F_LO) & (f <= F_HI)] - H_fd1[(f >= F_LO) & (f <= F_HI)])
                             / np.abs(H_fd1[(f >= F_LO) & (f <= F_HI)])))
    pk_td, z_td = half_power(f, smooth(np.abs(H_td1) ** 2))
    pk_fd, z_fd = half_power(f, smooth(np.abs(H_fd1) ** 2))
    ms = support_mode(sm.modes(dict(th, W=W), 16))
    out = {"V_kmh": V / KMH, "W_t": W, "rel_L2_misfit_record": rel_l2, "spectral_ratio_support_300_550": ratio_support,
           "spectral_ratio_analysis_band": ratio_band, "operator_max_rel_misfit_single_wheel": op_misfit,
           "support_peak_hz_td": pk_td, "support_zeta_halfpower_td": z_td, "support_peak_hz_fd": pk_fd,
           "support_zeta_halfpower_fd": z_fd, "support_mode_eig_hz": ms["f_hz"], "support_mode_eig_zeta": ms["zeta"]}
    save_result("p4/generator_check", out, cfg={"pass": "85 km/h, 14 t, 4 wheels (record) / 1 wheel (damping)",
                                               "contact": "linear", "fs_sim": gen.fs}, seed=7)
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
