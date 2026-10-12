"""Rail receptance (Timoshenko / Euler on a continuous foundation) and multi-wheel coupling checks."""

import numpy as np
import pytest

from src.reference.track import (RailTrack, receptance_ct_eq11, receptance_euler, receptance_numeric,
                                 receptance_timoshenko)

T = RailTrack(E=207e9, G=81e9, kappa=0.34, rho=7850, A=7.17e-3, I=2.35e-5, kf=154e6, eta_f=0.2)
W = 2 * np.pi * np.array([30.0, 100.0, 400.0, 900.0])
X = np.array([0.0, 0.65, 2.05, 10.1])


def test_timoshenko_matches_ct_eq11():
    a, b = receptance_timoshenko(W, X, T), receptance_ct_eq11(W, X, T)
    assert np.max(np.abs(a - b) / np.abs(a)) < 1e-9


@pytest.mark.parametrize("f,x", [(30.0, 0.0), (100.0, 2.05), (400.0, 0.65), (900.0, 2.05)])
def test_timoshenko_matches_numeric_transform(f, x):
    w = 2 * np.pi * f
    ref = receptance_numeric(w, x, T, kmax=4000.0, nk=8_000_001)
    got = receptance_timoshenko(np.array([w]), np.array([x]), T)[0, 0]
    assert abs(got - ref) / abs(got) < 2e-3


def test_euler_matches_numeric_transform():
    w = 2 * np.pi * 100.0
    k = np.linspace(-400, 400, 800001)
    D = T.E * T.I * k**4 - T.rho * T.A * w**2 + T.kf * (1 + 1j * T.eta_f)
    for x in (0.0, 2.05):
        ref = np.trapezoid(np.exp(1j * k * x) / D, k) / (2 * np.pi)
        got = receptance_euler(np.array([w]), np.array([x]), T)[0, 0]
        assert abs(got - ref) / abs(got) < 1e-6
    assert receptance_euler(W, X, T).shape == (W.size, X.size)


def test_timoshenko_tends_to_euler_without_shear_and_rotary_inertia():
    # same EI and rho A; shear rigid (G -> inf) and rotary inertia rho I -> 0 (I -> 0 with E I fixed)
    I_small = 1e-18
    tt = RailTrack(E=T.E * T.I / I_small, G=1e22, kappa=T.kappa, rho=T.rho, A=T.A, I=I_small, kf=T.kf, eta_f=T.eta_f)
    w = 2 * np.pi * np.array([50.0, 300.0])
    a = receptance_timoshenko(w, np.array([0.0, 1.0]), tt)
    b = receptance_euler(w, np.array([0.0, 1.0]), T)
    assert np.max(np.abs(a - b) / np.abs(b)) < 1e-4


def _setup_mw():
    from src.analysis.bound_scan import Scenario, ScenarioModel
    from src.reference.params import load_params
    p = load_params()
    sm = ScenarioModel(p, Scenario(name="a", kB0=1e9, cB=5e3, contact="hertz_rail", band_hz=700, fs=2000,
                                   forcing_spec={}, targets=[], kH0=1.4e9))
    return p, sm


def test_single_wheel_coupling_reproduces_rail_oscillator_model():
    from src.analysis.multiwheel import MultiWheelModel
    p, sm = _setup_mw()
    th = {"kB0": 0.85e9, "cB": 6e3, "k_r": 1e8, "r0": p.r0, "W": 14.0}

    def osc(omega, x, t):  # rail oscillator as a point receptance (scenario (a) rail)
        return (1.0 / (th["k_r"] - omega**2 * sm.sc.m_r + 1j * omega * sm.sc.c_r))[:, None] * np.ones((1, len(x)))
    mw = MultiWheelModel(sm, T, [0.0], 0, kH0=1.4e9, receptance=osc)
    w = 2 * np.pi * np.array([60.0, 250.0, 540.0, 610.0])
    a = (mw.components(th, w, "direct")).sum(1)
    b = sm.axlebox_accel_per_unit_input(th, w)
    assert np.max(np.abs(a - b) / np.abs(b)) < 1e-9


def test_multiwheel_modal_matches_direct():
    from src.analysis.multiwheel import MultiWheelModel
    p, sm = _setup_mw()
    th = {"kB0": 0.85e9, "cB": 6e3, "r0": p.r0, "W": 9.0}
    mw = MultiWheelModel(sm, T, [0.0, 2.05, 6.52, 8.57], 0)
    w = 2 * np.pi * np.array([60.0, 250.0, 540.0, 610.0])
    a, b = mw.components(th, w, "direct"), mw.components(th, w, "modal")
    assert np.max(np.abs(a - b) / np.abs(a).max(1, keepdims=True)) < 1e-8
