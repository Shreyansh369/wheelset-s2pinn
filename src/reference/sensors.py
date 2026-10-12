"""Sensor operators (doc §12) with a registry, so sensors are pluggable (Child A hook).

The default sensor is axlebox vertical acceleration with h_s = identity. Order-wise
statistics use the complex amplitude at each known forcing frequency:
y(t) ~ sum_w Re[c(w) e^{i w t}], estimated by least squares from a sampled record.
"""

from __future__ import annotations

from typing import Callable, Protocol

import numpy as np


class SensorOperator(Protocol):
    name: str

    def amplitudes(self, model, omegas: np.ndarray, Q: np.ndarray) -> np.ndarray:
        """Complex output amplitude per forcing frequency from DOF amplitudes Q [n_w, n_dof]."""

    def signal(self, model, sol, t: np.ndarray) -> np.ndarray:
        """Time signal from a HarmonicSolution."""


class AxleboxAccel:
    def __init__(self, side: str = "left"):
        self.side = side
        self.name = f"axlebox_accel_{side}"

    def _dof(self, model) -> int:
        return model.ib[0 if self.side == "left" else 1]

    def amplitudes(self, model, omegas, Q):
        return -(omegas**2) * Q[..., self._dof(model)]

    def signal(self, model, sol, t):
        return sol.qdd(t)[:, self._dof(model)]


SENSORS: dict[str, Callable[[], SensorOperator]] = {
    "axlebox_left": lambda: AxleboxAccel("left"),
    "axlebox_right": lambda: AxleboxAccel("right"),
}


def get_sensor(name: str) -> SensorOperator:
    return SENSORS[name]()


def add_noise(y: np.ndarray, snr_db: float, rng: np.random.Generator) -> tuple[np.ndarray, float]:
    """White Gaussian noise at SNR = signal power / noise power over the record."""
    sigma = np.sqrt(np.mean(y**2) / 10 ** (snr_db / 10))
    return y + sigma * rng.standard_normal(y.shape), float(sigma)


def order_amplitudes(t: np.ndarray, y: np.ndarray, omegas: np.ndarray, with_dc: bool = True) -> np.ndarray:
    """Least-squares complex amplitudes c(w) with y ~ c0 + sum Re[c(w) e^{i w t}]."""
    cols = [np.cos(np.outer(t, omegas)), -np.sin(np.outer(t, omegas))]
    B = np.hstack(cols + ([np.ones((t.size, 1))] if with_dc else []))
    coef, *_ = np.linalg.lstsq(B, y, rcond=None)
    n = omegas.size
    return coef[:n] + 1j * coef[n:2 * n]
