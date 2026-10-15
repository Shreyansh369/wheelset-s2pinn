"""Linearised wheel-rail contact stiffness k_H0 from Hertz theory (S1002 wheel on UIC60 rail).

Elliptical Hertz contact (Johnson, Contact Mechanics, 1985, Sect. 4.2): with A < B the half-sums of the
principal relative curvatures, e^2 = 1 - (b/a)^2 solves B/A = [E(e)/(1-e^2) - K(e)] / [K(e) - E(e)],
the semi-axis a = [F (K - E) / ((2/3) pi A E* e^2)]^(1/3), b = a sqrt(1 - e^2), p0 = 3F/(2 pi a b) and the
approach delta = p0 b K(e) / E*, with E* = E / (2 (1 - nu^2)) for two steel bodies. Then
C_H = F / delta^(3/2) and the linearised stiffness k_H = dF/d delta = 1.5 F / delta.

Geometry: wheel rolling radius 0.46 m (Dusza et al. 2024, S1002 wheels on UIC60 rail), rail crown radius
0.30 m (UIC60 head), rail longitudinal radius infinite. The transverse radius of the S1002 tread at the
nominal contact point was not found; it is taken as infinite (conical tread) and swept over convex
(+0.5, +1.0 m) and concave (-1.0 m, worn) values. Wheel load at the reference axle load W0 = 22.5 t:
F0 = W0 g / 2. Cross-check: the 1.4-2.3e9 N/m spread of published values (Hasan 2020).
Writes results/p4/contact_hertz.json.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.special import ellipe, ellipk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reference.params import G, load_params  # noqa: E402
from src.utils.results import save_result  # noqa: E402

R_WHEEL = 0.46                        # rolling radius (m)
R_RAIL_CROWN = 0.30                   # UIC60 crown radius (m)
R_WHEEL_TRANSVERSE = (np.inf, 1.0, 0.5, -1.0)   # nominal first (m; negative = concave)


def hertz(F, curv_x, curv_y, E, nu):
    """Elliptical Hertz contact for relative curvatures curv_x, curv_y (1/m) under normal load F (N)."""
    Es = E / (2 * (1 - nu**2))
    A, B = sorted([curv_x / 2, curv_y / 2])
    if np.isclose(A, B):
        a = (3 * F / (4 * Es * 2 * A)) ** (1 / 3)            # circular: R = 1/(2A)
        return {"a_mm": a * 1e3, "b_mm": a * 1e3, "p0_MPa": 3 * F / (2 * np.pi * a * a) / 1e6, "delta_um": a**2 * 2 * A * 1e6}
    e2 = brentq(lambda x: (ellipe(x) / (1 - x) - ellipk(x)) / (ellipk(x) - ellipe(x)) - B / A, 1e-12, 1 - 1e-12)
    Kc, Ec = ellipk(e2), ellipe(e2)
    a = (F * (Kc - Ec) / ((2 / 3) * np.pi * A * Es * e2)) ** (1 / 3)
    b = a * np.sqrt(1 - e2)
    p0 = 3 * F / (2 * np.pi * a * b)
    d = p0 * b * Kc / Es
    return {"a_mm": a * 1e3, "b_mm": b * 1e3, "p0_MPa": p0 / 1e6, "delta_um": d * 1e6}


def main():
    p = load_params()
    E, nu = p.v["material"]["E"], p.v["material"]["nu"]
    W0, Wmin = p.v["payload"]["W0"], p.v["payload"]["W_min"]
    rows = []
    for rwt in R_WHEEL_TRANSVERSE:
        cx = 1 / R_WHEEL
        cy = 1 / R_RAIL_CROWN + (0.0 if np.isinf(rwt) else 1 / rwt)
        for lab, W in (("W0", W0), ("empty", Wmin)):
            F = W * 1000 * G / 2
            h = hertz(F, cx, cy, E, nu)
            d = h["delta_um"] * 1e-6
            rows.append({"wheel_transverse_radius_m": None if np.isinf(rwt) else rwt, "load": lab, "W_t": W, "F_kN": F / 1e3, **h,
                         "kH_N_per_m": 1.5 * F / d, "C_H_N_per_m1p5": F / d**1.5})
    nom = next(r for r in rows if r["wheel_transverse_radius_m"] is None and r["load"] == "W0")
    k0 = [r["kH_N_per_m"] for r in rows if r["load"] == "W0"]
    out = {"kH0_nominal": nom["kH_N_per_m"], "C_H_nominal": nom["C_H_N_per_m1p5"], "kH0_range": [min(k0), max(k0)],
           "cross_check_published_range": [1.4e9, 2.3e9], "rows": rows}
    save_result("p4/contact_hertz", out, cfg={"R_wheel_m": R_WHEEL, "R_rail_crown_m": R_RAIL_CROWN,
                                             "R_wheel_transverse_m": [str(r) for r in R_WHEEL_TRANSVERSE], "E": E, "nu": nu}, seed=0)
    for r in rows:
        print(r)
    print("kH0 nominal %.4g N/m, C_H %.4g N/m^1.5, range %.4g-%.4g" % (out["kH0_nominal"], out["C_H_nominal"], *out["kH0_range"]))


if __name__ == "__main__":
    main()
