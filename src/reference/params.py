"""Load config/params.yaml into plain values and derived quantities.

``rotation_frequency`` is the single place where r0 enters every order frequency
(Child A hook: r0 and a speed bias become inverse targets later).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[2]
DEFAULT_PARAMS = REPO / "config" / "params.yaml"
G = 9.80665


def _values(node: Any) -> Any:
    """Strip {value, unit, source} wrappers recursively."""
    if isinstance(node, dict):
        if "value" in node and "source" in node:
            return _num(node["value"])
        return {k: _values(v) for k, v in node.items()}
    return node


def _num(x: Any) -> Any:
    """YAML 1.1 reads exponents without a sign (2.1e11) as strings; convert those."""
    if isinstance(x, list):
        return [_num(v) for v in x]
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            return x
    return x


def load_raw(path: str | Path = DEFAULT_PARAMS) -> dict:
    return yaml.safe_load(Path(path).read_text())


def rotation_frequency(V: float, r0: float) -> float:
    """Wheel rotation frequency f_r = V / (2 pi r0) in Hz."""
    return V / (2 * math.pi * r0)


@dataclass
class Params:
    raw: dict
    v: dict = field(init=False)

    def __post_init__(self) -> None:
        self.v = _values(self.raw)
        m = self.v["material"]
        if m["kappa"] is None:
            m["kappa"] = 6 * (1 + m["nu"]) / (7 + 6 * m["nu"])
        m["Gs"] = m["E"] / (2 * (1 + m["nu"]))

    # ---- convenience accessors
    @property
    def V(self) -> float:
        return float(self.v["operation"]["V"])

    @property
    def r0(self) -> float:
        return float(self.v["wheel"]["r0"])

    @property
    def f_r(self) -> float:
        return rotation_frequency(self.V, self.r0)

    def kB(self, kB0: float, W: float, load_exp: float | None = None, clearance_growth_um: float = 0.0) -> float:
        """Effective support stiffness k_B(W) (W in t, same unit as W0).

        bearing.stiffness_law = "power" (default): kB0 (W/W0)^load_exp; load_exp defaults to the config
        value. clearance_growth_um is ignored.
        "series": roller contacts (src/reference/bearing.py, Eqs. 10-14 of the wheelset document) in
        series with the housing/adapter, k_B = [1/k_contact(W, c) + 1/k_housing]^-1 with
        c = c_d0 + clearance growth. k_housing is set so that k_B(W0, c_d0) = kB0, i.e. kB0 remains the
        effective support stiffness at the reference load and clearance; load_exp is ignored.
        """
        b = self.v["bearing"]
        if b.get("stiffness_law", "power") == "series":
            kc0 = self._k_contact(self.v["payload"]["W0"], 0.0)
            if kB0 >= kc0:
                raise ValueError(f"series law needs kB0 < k_contact(W0, c_d0) = {kc0:.3g} N/m")
            k_h = 1.0 / (1.0 / kB0 - 1.0 / kc0)
            return 1.0 / (1.0 / self._k_contact(W, clearance_growth_um) + 1.0 / k_h)
        return kB0 * (W / self.v["payload"]["W0"]) ** (b["load_exponent"] if load_exp is None else load_exp)

    def _k_contact(self, W: float, growth_um: float) -> float:
        """Cage-averaged roller-contact stiffness at axle load W (t) and diametral clearance c_d0 + growth."""
        key = (round(float(W), 9), round(float(growth_um), 9))
        cache = self.__dict__.setdefault("_kc_cache", {})
        if key not in cache:
            from src.reference.bearing import RollerBearing
            bg, v = self.v["bearing_geometry"], self.v
            brg = RollerBearing(int(bg["rollers_per_row"]), bg["roller_length"], bg["contact_angle"], bg["K_contact_coeff"])
            rho = v["material"]["rho"]
            xs = [0.0] + [sec[0] for sec in v["axle"]["sections"]]
            m_axle = 2 * sum(rho * math.pi * sec[1] ** 2 / 4 * (xs[i + 1] - xs[i]) for i, sec in enumerate(v["axle"]["sections"]))
            F = (W * 1000 - 2 * v["wheel"]["mass"] - m_axle) * G / 2
            cache[key] = brg.k_mean(F, (bg["clearance_d0"] + growth_um) * 1e-6)["k_mean"]
        return cache[key]

    # ---- forcing variables (zeta_2): order matters and is fixed
    def forcing_variables(self) -> list[dict]:
        """One entry per Gaussian forcing variable: name, angular frequency, std scale, phase factor.

        Contact displacement z_c(t) = sum_j zeta_j * scale_j * Re[phase_j * exp(i w_j t)],
        phase = 1 for cosine coefficients and -i for sine coefficients.
        """
        f = self.v["forcing"]
        out = []
        Omega = 2 * math.pi * self.f_r
        for n, s in zip(f["oor_orders"], f["oor_std"]):
            out.append({"name": f"oor_a{n}", "group": "oor", "omega": n * Omega, "scale": s, "phase": 1.0 + 0j})
            out.append({"name": f"oor_b{n}", "group": "oor", "omega": n * Omega, "scale": s, "phase": -1j})
        for k, (Om, dOm) in enumerate(zip(*self.track_wavenumbers())):
            sp = self.track_psd(Om)
            amp = math.sqrt(sp * dOm)
            w = Om * self.V
            out.append({"name": f"track_A{k + 1}", "group": "track", "omega": w, "scale": amp, "phase": 1.0 + 0j})
            out.append({"name": f"track_B{k + 1}", "group": "track", "omega": w, "scale": amp, "phase": -1j})
        return out

    def track_wavenumbers(self) -> tuple[np.ndarray, np.ndarray]:
        """Spatial angular wavenumbers Omega_k = 2 pi / lambda_k and log-bin widths dOmega_k."""
        lam = np.array(self.v["forcing"]["track_wavelengths"], float)
        Om = np.sort(2 * np.pi / lam)
        mids = np.sqrt(Om[1:] * Om[:-1])
        lo = np.concatenate([[Om[0] ** 2 / mids[0]], mids])
        hi = np.concatenate([mids, [Om[-1] ** 2 / mids[-1]]])
        return Om, hi - lo

    def track_psd(self, Om: float) -> float:
        t = self.v["forcing"]["track_spectrum"]
        return t["A_v"] * t["Omega_c"] ** 2 / ((Om**2 + t["Omega_r"] ** 2) * (Om**2 + t["Omega_c"] ** 2))

    def unique_omegas(self) -> np.ndarray:
        return np.unique(np.round([fv["omega"] for fv in self.forcing_variables()], 12))

    # ---- priors in standard coordinates u in [-1, 1]
    def theta_from_u(self, u_kB: np.ndarray, u_cB: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        b = self.v["bearing"]
        h = b["prior_log_halfwidth"]
        return b["kB0"] * np.exp(h * np.asarray(u_kB)), b["cB"] * np.exp(h * np.asarray(u_cB))

    def W_from_u(self, u_W: np.ndarray) -> np.ndarray:
        p = self.v["payload"]
        return p["W_min"] + (np.asarray(u_W) + 1) / 2 * (p["W_max"] - p["W_min"])


def load_params(path: str | Path = DEFAULT_PARAMS) -> Params:
    return Params(load_raw(path))
