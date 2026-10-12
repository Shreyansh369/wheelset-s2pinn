"""Exploratory Cramer-Rao scan of forcing/target scenarios (does not modify the reference solver).

Builds on the L1-lin matrices (src/reference/timoshenko_fe.py) and optionally replaces rigid
quasi-static contact by a linearised Hertz spring k_H = k_H0 (W/W0)^(1/3) between each wheel and a
rail oscillator (m_r, k_r, c_r). The input is a roughness/irregularity displacement z(t) acting
across the contact (the same under both wheels).

Observation model per pass: the left-axlebox acceleration complex amplitudes at the forcing
frequencies, c_k ~ CN(0, v_k(theta)), plus least-squares noise from a white-noise record at the
stated SNR. Fisher information per pass: sum_k grad(log v_k) grad(log v_k)^T, with
v_k -> v_k + e_noise. For r0, the order frequencies n V / r0 also carry frequency information
(sinusoid frequency CRB), which is added. "Payload unknown" treats W as one unknown constant,
so the bound is optimistic compared with W varying from pass to pass.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field

import numpy as np
from scipy.linalg import eig

from src.reference.params import Params
from src.reference.timoshenko_fe import L1LinModel


@dataclass
class Forcing:
    omega: np.ndarray       # rad/s, unique
    var: np.ndarray         # total variance of contact displacement at each frequency (m^2) = 2 * scale^2
    group: list             # e.g. "oor1", "track", "rough"
    order: np.ndarray       # wheel order n (0 if not wheel-locked)


@dataclass
class Scenario:
    name: str
    kB0: float
    cB: float
    contact: str            # "rigid" or "hertz_rail"
    band_hz: float
    fs: float
    forcing_spec: dict
    targets: list
    priors: dict = field(default_factory=dict)
    kH0: float = 1.4e9      # placeholder: linearised Hertz stiffness at W0 wheel load
    m_r: float = 150.0
    k_r: float = 1.0e8
    c_r: float = 1.0e5


def make_forcing(p: Params, spec: dict, r0: float, band_hz: float) -> Forcing:
    V = p.V
    f_r = V / (2 * math.pi * r0)
    om, var, grp, order = [], [], [], []
    for n in spec.get("oor_orders", []):
        w = n * 2 * math.pi * f_r
        if w / (2 * math.pi) <= band_hz:
            s = spec["oor_std"](n)
            om.append(w); var.append(2 * s**2); grp.append(f"oor{n}"); order.append(n)
    for lam in spec.get("track_wavelengths", []):
        Om = 2 * math.pi / lam
        w = Om * V
        if w / (2 * math.pi) <= band_hz:
            dOm = Om * spec.get("track_rel_bin", 0.5)
            s2 = p.track_psd(Om) * dOm
            om.append(w); var.append(2 * s2); grp.append("track"); order.append(0)
    for lam in spec.get("rough_wavelengths", []):  # 1/3-octave roughness bands, level in dB re 1 um
        w = 2 * math.pi * V / lam
        if w / (2 * math.pi) <= band_hz:
            rms = 1e-6 * 10 ** (spec["rough_level_db"](lam) / 20)
            om.append(w); var.append(2 * rms**2); grp.append("rough"); order.append(0)  # E|Z|^2 = 2 rms^2
    i = np.argsort(om)
    return Forcing(np.array(om)[i], np.array(var)[i], [grp[j] for j in i], np.array(order)[i])


class ScenarioModel:
    def __init__(self, p: Params, sc: Scenario):
        raw = copy.deepcopy(p.raw)
        raw["bearing"]["kB0"]["value"] = sc.kB0
        raw["bearing"]["cB"]["value"] = sc.cB
        self.p = Params(raw)
        self.sc = sc
        self.base = L1LinModel(self.p)
        self.wheels = [2 * j for j in self.base.mesh.wheel_nodes]
        self.ibL = self.base.ib[0]

    def wheelset_matrices(self, th: dict):
        """Wheelset-only (M, C, K) (no contact, no rail). Optional (model-form tests): th["axle_damp_scale"]
        scales the axle's stiffness-proportional damping; th["unsprung_scale"] scales the whole wheelset
        mass matrix (axle, wheels, axleboxes)."""
        m = self.base.matrices(th["kB0"], th["cB"], th["W"])
        M, C, K = m.M * th.get("unsprung_scale", 1.0), m.C.copy(), m.K
        s = th.get("axle_damp_scale", 1.0)
        if s != 1.0:
            nb = self.base.ib[0]
            C[:nb, :nb] += (s - 1.0) * self.base.C0[:nb, :nb]
        return M, C, K

    def system(self, th: dict):
        """Full (M, C, K) and the unit-input force pattern; th: kB0, cB, W, k_r, r0.

        Optional th keys (default: the Scenario's values): kH0, m_r, c_r, axle_damp_scale.
        """
        if self.sc.contact == "rigid":
            return self.base.matrices(th["kB0"], th["cB"], th["W"]), None
        Mw, Cw, Kw = self.wheelset_matrices(th)
        n0 = self.base.n
        n = n0 + 2
        M, C, K = (np.zeros((n, n)) for _ in range(3))
        M[:n0, :n0], C[:n0, :n0], K[:n0, :n0] = Mw, Cw, Kw
        kH = th.get("kH0", self.sc.kH0) * (th["W"] / self.p.v["payload"]["W0"]) ** (1 / 3)
        f = np.zeros(n)
        for i, (wdof, rdof) in enumerate(zip(self.wheels, (n0, n0 + 1))):
            M[rdof, rdof] += th.get("m_r", self.sc.m_r)
            K[rdof, rdof] += th["k_r"]
            C[rdof, rdof] += th.get("c_r", self.sc.c_r)
            for (a, b), s in (((wdof, wdof), 1), ((rdof, rdof), 1), ((wdof, rdof), -1), ((rdof, wdof), -1)):
                K[a, b] += s * kH
            # contact force kH (u_rail + z - w): +kH z on the wheel, -kH z on the rail
            f[wdof] += kH
            f[rdof] -= kH
        return (M, C, K), f

    def axlebox_accel_per_unit_input(self, th: dict, omegas: np.ndarray) -> np.ndarray:
        sysm, f = self.system(th)
        out = np.empty(omegas.size, complex)
        for i, w in enumerate(omegas):
            if f is None:
                from src.reference.frequency_domain import unit_response

                X = unit_response(self.base, sysm, w)
            else:
                M, C, K = sysm
                X = np.linalg.solve(K - w**2 * M + 1j * w * C, f.astype(complex))
            out[i] = -(w**2) * X[self.ibL]
        return out

    def order_power(self, th: dict) -> tuple[np.ndarray, Forcing]:
        F = make_forcing(self.p, self.sc.forcing_spec, th["r0"], self.sc.band_hz)
        var = F.var.copy()
        for k, g in enumerate(F.group):  # OOR amplitude scale targets multiply the order-n variance
            if g.startswith("oor"):
                var[k] *= th.get(f"s_{g}", 1.0) ** 2
        a = self.axlebox_accel_per_unit_input(th, F.omega)
        return np.abs(a) ** 2 * var, F

    def modes(self, th: dict, n_modes: int = 12) -> list[dict]:
        sysm, f = self.system(th)
        if f is None:
            M, C, K = sysm.M, sysm.C, sysm.K
            idx = sysm.free
        else:
            M, C, K = sysm
            idx = np.arange(M.shape[0])
        Mf, Cf, Kf = (A[np.ix_(idx, idx)] for A in (M, C, K))
        from scipy.linalg import eigh

        w2, V = eigh(Kf, Mf)
        loc = {int(np.where(idx == d)[0][0]): name for d, name in
               [(self.base.ib[0], "axlebox"), (self.base.ib[1], "axlebox")] + [(w, "wheel") for w in self.wheels
                                                                                 if w in set(idx)]}
        if f is not None:
            loc.update({M.shape[0] - 2: "rail", M.shape[0] - 1: "rail"})
        out = []
        for k in range(n_modes):
            v = V[:, k]
            ke = v * (Mf @ v)
            w = math.sqrt(max(w2[k], 0))
            share = {}
            for i, nm in loc.items():
                share[nm] = share.get(nm, 0) + ke[i] / ke.sum()
            ibl = int(np.where(idx == self.base.ib[0])[0][0])
            ibr = int(np.where(idx == self.base.ib[1])[0][0])
            out.append({"f_hz": w / (2 * math.pi), "zeta": float(v @ Cf @ v / (2 * w * (v @ Mf @ v))) if w > 0 else 0.0,
                        "share": {k2: float(v2) for k2, v2 in share.items()},
                        "symmetric": bool(np.sign(v[ibl]) == np.sign(v[ibr]))})
        return out


def support_mode(modes: list[dict]) -> dict:
    sym = [m for m in modes if m["symmetric"]]
    return max(sym, key=lambda m: m["share"].get("axlebox", 0))


def p2_mode(modes: list[dict]) -> dict:
    sym = [m for m in modes if m["symmetric"] and 20 <= m["f_hz"] <= 200]
    return max(sym, key=lambda m: m["share"].get("wheel", 0) + m["share"].get("rail", 0))


def _perturb(th: dict, name: str, eps: float) -> dict:
    t = dict(th)
    key = name.replace("log_", "")
    t[key] = th[key] * math.exp(eps)
    return t


def fisher_info(sm: ScenarioModel, th: dict, params: list[str], n_passes: int, snr_db: float, h: float = 1e-4) -> dict:
    v, F = sm.order_power(th)
    n_samp = int(sm.p.v["sensor"]["n_revs"] / (sm.p.V / (2 * math.pi * th["r0"])) * sm.sc.fs)
    p_sig = 0.5 * v.sum()
    sig2 = p_sig / 10 ** (snr_db / 10)
    e_noise = 4 * sig2 / n_samp
    vt = v + e_noise
    G = []
    for name in params:
        up, _ = sm.order_power(_perturb(th, name, h))
        dn, _ = sm.order_power(_perturb(th, name, -h))
        G.append((up - dn) / (2 * h) / vt)  # d log v_total / d param
    G = np.array(G).T  # [K, P]
    I = n_passes * G.T @ G
    if "log_r0" in params:  # frequency channel: order frequencies n V / r0
        dt = 1 / sm.sc.fs
        iw = params.index("log_r0")
        wl = F.order > 0
        I_w = np.sum(F.omega[wl] ** 2 * v[wl] * dt**2 * n_samp * (n_samp**2 - 1) / (12 * sig2))
        I[iw, iw] += n_passes * I_w
    return {"I": I, "v": v, "F": F, "e_noise": e_noise}


def crb_report(sm: ScenarioModel, th: dict, params: list[str], n_passes: int, snr_db: float,
               reparam_zeta: bool = True) -> dict:
    """CRB std of log-parameters; log_cB is replaced by log zeta_s (support-mode damping ratio)."""
    fi = fisher_info(sm, th, params, n_passes, snr_db)
    I = fi["I"]
    names = list(params)
    dzeta = None
    if reparam_zeta and "log_cB" in params:
        # zeta_s = f(kB0, cB, W, ...): Jacobian of (log params) w.r.t. (log params with cB -> zeta_s)
        h = 1e-4
        row = np.zeros(len(params))
        for j, nm in enumerate(params):
            zu = math.log(support_mode(sm.modes(_perturb(th, nm, h)))["zeta"])
            zd = math.log(support_mode(sm.modes(_perturb(th, nm, -h)))["zeta"])
            row[j] = (zu - zd) / (2 * h)
        ic = params.index("log_cB")
        dzeta = dict(zip(params, row.tolist()))
        A = np.eye(len(params))
        A[ic] = row  # d(new)/d(old)
        J = np.linalg.inv(A)  # d(old)/d(new)
        I_cb = I.copy()
        I = J.T @ I @ J
        names[ic] = "log_zeta_s"
    # CRB with explicit handling of (near-)singular directions. Scale by the diagonal first so that
    # very different information levels (e.g. the r0 frequency channel) do not mask each other; a
    # parameter is unidentifiable (std = inf) if it loads on a direction with scaled eigenvalue < 1e-10.
    def _crb(Imat):
        d = 1 / np.sqrt(np.maximum(np.diag(Imat), 1e-300))
        Is = Imat * np.outer(d, d)
        lam, V = np.linalg.eigh(Is)
        good = lam > 1e-10
        var_s = (V[:, good] ** 2 / lam[good]).sum(1)
        bad = (V[:, ~good] ** 2).sum(1) if (~good).any() else np.zeros(Imat.shape[0])
        st = np.where((bad > 1e-6) | (np.diag(Imat) <= 0), np.inf, d * np.sqrt(var_s))
        cv = (V[:, good] / lam[good]) @ V[:, good].T
        return st, cv / np.sqrt(np.outer(np.diag(cv), np.diag(cv)) + 1e-300), lam, good

    std, corr, lam, good = _crb(I)
    extra = {}
    if dzeta is not None:
        std_cb, _, _, _ = _crb(I_cb)
        extra = {"dlogzeta_s_dlogparam": dzeta, "crb_std_log_cB_equivalent": float(std_cb[ic])}
    return {"params": names, "crb_std_log": dict(zip(names, [float(x) for x in std])),
            "scaled_eig_min": float(lam.min()), "n_unidentifiable_directions": int((~good).sum()),
            "corr": corr.tolist(), "n_orders": int(fi["F"].omega.size), "e_noise": fi["e_noise"],
            "max_freq_hz": float(fi["F"].omega.max() / (2 * math.pi)), **extra}


def pi_over_prior(sm: ScenarioModel, th: dict, prior: dict, which: str, n: int = 200, seed: int = 11) -> dict:
    """Pi = s / zeta of the support mode (or P2 mode) over a log-uniform/uniform prior."""
    rng = np.random.default_rng(seed)
    fr, zt = [], []
    for _ in range(n):
        t = dict(th)
        for k, (kind, a, b) in prior.items():
            t[k] = th[k] * math.exp(rng.uniform(-a, a)) if kind == "log" else rng.uniform(a, b)
        md = sm.modes(t)
        m = support_mode(md) if which == "support" else p2_mode(md)
        fr.append(m["f_hz"]); zt.append(m["zeta"])
    fr, zt = np.array(fr), np.array(zt)
    s = fr.std() / fr.mean()
    return {"mode": which, "mean_f_hz": float(fr.mean()), "freq_cov": float(s), "zeta_median": float(np.median(zt)),
            "Pi": float(s / np.median(zt)), "n": n}
