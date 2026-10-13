"""Static roller-contact stiffness of a double-row roller bearing (wheelset doc Section 6, Eqs. 10-14).

Pure radial journal load F (vertical), symmetric rows, no tilt: the axial components of the two rows
cancel and the journal moves by Delta along the load. Roller j of row r at cage angle theta_j:
    delta_j = Delta cos(theta_j) cos(alpha) - c_d / 2                              (Eq. 10, radial part)
    Q_j     = K_n [delta_j]_+^(10/9),  K_n = (K_i^-9/10 + K_o^-9/10)^-10/9          (Eqs. 12-13)
    F       = sum_r sum_j Q_j cos(theta_j) cos(alpha)                               (Eq. 14)
The tangent stiffness k = dF/dDelta at the static point is the linearised bearing support stiffness,
averaged over cage position (the roller-passage variation is reported separately).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq


@dataclass
class RollerBearing:
    Z: int                 # rollers per row
    l_mm: float            # effective contact length
    alpha_deg: float       # contact angle
    K_coeff: float = 8.06e4  # Eq. (13) coefficient, N mm^-10/9 per mm^(8/9)
    rows: int = 2

    @property
    def Kn(self) -> float:
        """Series inner/outer line-contact constant, N mm^-10/9 (Eq. 13 with K_i = K_o)."""
        K = self.K_coeff * self.l_mm ** (8 / 9)
        return (2 * K ** (-0.9)) ** (-10 / 9)

    def _terms(self, delta_m: float, cd_m: float, theta_c: float):
        th = theta_c + 2 * np.pi * np.arange(self.Z) / self.Z
        cz = np.cos(th) * math.cos(math.radians(self.alpha_deg))
        d_mm = np.maximum(delta_m * cz - cd_m / 2, 0.0) * 1e3
        return cz, d_mm

    def force(self, delta_m: float, cd_m: float, theta_c: float = 0.0) -> float:
        cz, d = self._terms(delta_m, cd_m, theta_c)
        return self.rows * float(np.sum(self.Kn * d ** (10 / 9) * cz))          # N

    def stiffness(self, delta_m: float, cd_m: float, theta_c: float = 0.0) -> float:
        cz, d = self._terms(delta_m, cd_m, theta_c)
        # dQ/dDelta = (10/9) K_n d^(1/9) cz, with d in mm and Delta in m (factor 1e3)
        return self.rows * float(np.sum((10 / 9) * self.Kn * d ** (1 / 9) * cz**2)) * 1e3   # N/m

    def static(self, F: float, cd_m: float, theta_c: float = 0.0) -> dict:
        lo = cd_m / 2 / math.cos(math.radians(self.alpha_deg))
        hi = lo + 1e-6
        while self.force(hi, cd_m, theta_c) < F:
            hi = lo + 2 * (hi - lo)
        d = brentq(lambda x: self.force(x, cd_m, theta_c) - F, lo, hi, xtol=1e-15, rtol=1e-13)
        _, dj = self._terms(d, cd_m, theta_c)
        return {"Delta_m": d, "k": self.stiffness(d, cd_m, theta_c), "n_loaded_per_row": int(np.sum(dj > 0)),
                "Qmax_N": float(self.Kn * dj.max() ** (10 / 9))}

    def k_mean(self, F: float, cd_m: float, n_cage: int = 16) -> dict:
        """Stiffness averaged over cage position within one roller pitch, with its min and max."""
        ks = [self.static(F, cd_m, t)["k"] for t in np.linspace(0, 2 * np.pi / self.Z, n_cage, endpoint=False)]
        s0 = self.static(F, cd_m, 0.0)
        return {"k_mean": float(np.mean(ks)), "k_min": float(np.min(ks)), "k_max": float(np.max(ks)),
                "Delta_um": s0["Delta_m"] * 1e6, "n_loaded_per_row": s0["n_loaded_per_row"], "Qmax_kN": s0["Qmax_N"] / 1e3}
