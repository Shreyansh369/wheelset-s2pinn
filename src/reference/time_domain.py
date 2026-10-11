"""Newmark (average-acceleration) time integration of L1-lin, used to cross-check the FD solver (G1c).

The prescribed wheel displacement z(t) enters through
    M_ff a_f + C_ff v_f + K_ff u_f = -(M_fp zdd + C_fp zd + K_fp z)
(or as the rail-oscillator force when rail_sdof is on). Initial conditions are taken from
the frequency-domain steady state at t = 0, so no start-up transient pollutes the comparison.
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import lu_factor, lu_solve


def newmark(model, sol, T: float, dt: float, out_every: int = 10, gamma: float = 0.5, beta: float = 0.25) -> dict:
    m = sol.mats
    f = m.free if not model.rail else np.arange(model.n)
    pz = m.presc
    Mff, Cff, Kff = m.M[np.ix_(f, f)], m.C[np.ix_(f, f)], m.K[np.ix_(f, f)]
    if model.rail:
        r = model.p.v["rail_sdof"]
        wd = np.searchsorted(f, model.wheel_w_dofs())

        def force(t):
            z, zd, zdd = sol.z(t, 0)[0], sol.z(t, 1)[0], sol.z(t, 2)[0]
            F = np.zeros(f.size)
            F[wd] = r["k_r"] * z + r["c_r"] * zd + r["m_r"] * zdd
            return F
    else:
        Mfp, Cfp, Kfp = m.M[np.ix_(f, pz)], m.C[np.ix_(f, pz)], m.K[np.ix_(f, pz)]
        ones = np.ones(pz.size)

        def force(t):
            z, zd, zdd = sol.z(t, 0)[0], sol.z(t, 1)[0], sol.z(t, 2)[0]
            return -(Mfp @ (zdd * ones) + Cfp @ (zd * ones) + Kfp @ (z * ones))

    u = sol.q(0.0)[0, f]
    v = sol.qd(0.0)[0, f]
    a = np.linalg.solve(Mff, force(0.0) - Cff @ v - Kff @ u)  # consistent initial acceleration
    lu = lu_factor(Mff + gamma * dt * Cff + beta * dt**2 * Kff)
    n_steps = int(round(T / dt))
    ts, us, vs, as_ = [0.0], [u.copy()], [v.copy()], [a.copy()]
    for k in range(1, n_steps + 1):
        t = k * dt
        up = u + dt * v + (0.5 - beta) * dt**2 * a
        vp = v + (1 - gamma) * dt * a
        a = lu_solve(lu, force(t) - Cff @ vp - Kff @ up)
        u = up + beta * dt**2 * a
        v = vp + gamma * dt * a
        if k % out_every == 0:
            ts.append(t)
            us.append(u.copy())
            vs.append(v.copy())
            as_.append(a.copy())
    return {"t": np.array(ts), "u": np.array(us), "v": np.array(vs), "a": np.array(as_), "free": f}


def rel_l2(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b) / np.linalg.norm(b))
