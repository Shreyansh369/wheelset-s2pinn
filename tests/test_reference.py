"""G1 verification of the L1-lin reference solver (thresholds from config/gates.yaml)."""

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
import pytest
import yaml

from src.reference.frequency_domain import ForcingMap, harmonic_solution, unit_responses
from src.reference.params import REPO, load_params
from src.reference.sensors import add_noise, get_sensor, order_amplitudes
from src.reference.verify import fd_cases, fd_td_energy_check, freefree_check, model_for

G1 = yaml.safe_load((REPO / "config" / "gates.yaml").read_text())["G1"]
P = load_params()


@pytest.mark.parametrize("n", [20, 30, 40])
def test_freefree_timoshenko_matches_exact(n):
    r = freefree_check(P, d=0.175, L=2.18, n_elements=[n])
    assert r["fe"][str(n)]["max_rel_err"] <= G1["freefree_timoshenko_rel_err_max"]


@pytest.mark.parametrize("case", fd_cases(P), ids=lambda c: c["name"])
def test_energy_balance_and_fd_vs_td(case):
    r = fd_td_energy_check(P, case, T=0.5)
    assert r["energy"]["rel_residual"] <= G1["energy_balance_rel_residual_max"]
    assert r["fd_vs_td_rel_l2"] <= G1["fd_vs_td_rel_l2_max"]


def test_response_is_linear_in_forcing():
    mdl, fm = model_for(P, False), ForcingMap(P)
    b = P.v["bearing"]
    rng = np.random.default_rng(3)
    z1, z2 = rng.standard_normal(fm.n_vars), rng.standard_normal(fm.n_vars)
    s1 = harmonic_solution(mdl, fm, b["kB0"], b["cB"], 10.0, z1)
    s2 = harmonic_solution(mdl, fm, b["kB0"], b["cB"], 10.0, z2)
    s12 = harmonic_solution(mdl, fm, b["kB0"], b["cB"], 10.0, 2 * z1 - z2)
    assert np.allclose(s12.Q, 2 * s1.Q - s2.Q, rtol=1e-12, atol=1e-18)


def test_rail_sdof_tends_to_rigid_track():
    import copy

    from src.reference.params import Params
    from src.reference.timoshenko_fe import L1LinModel

    raw = copy.deepcopy(P.raw)
    raw["rail_sdof"]["enabled"]["value"] = True
    raw["rail_sdof"]["k_r"]["value"] = 1e15
    raw["rail_sdof"]["c_r"]["value"] = 0.0
    raw["rail_sdof"]["m_r"]["value"] = 0.0
    fm = ForcingMap(P)
    b = P.v["bearing"]
    rigid = unit_responses(model_for(P, False), fm, b["kB0"], b["cB"], 22.5)
    stiff = unit_responses(L1LinModel(Params(raw)), fm, b["kB0"], b["cB"], 22.5)
    ib = model_for(P, False).ib[0]
    assert np.allclose(stiff[:, ib], rigid[:, ib], rtol=1e-5)


def test_order_amplitudes_recover_noiseless_signal():
    mdl, fm = model_for(P, False), ForcingMap(P)
    b = P.v["bearing"]
    sol = harmonic_solution(mdl, fm, b["kB0"], b["cB"], 22.5, np.random.default_rng(4).standard_normal(fm.n_vars))
    sen = get_sensor("axlebox_left")
    fs, T = 1000.0, 20 / P.f_r
    t = np.arange(0, T, 1 / fs)
    c = order_amplitudes(t, sen.signal(mdl, sol, t), fm.omegas)
    assert np.allclose(c, sen.amplitudes(mdl, fm.omegas, sol.Q), rtol=1e-6, atol=1e-12)
    y, sigma = add_noise(sen.signal(mdl, sol, t), 40.0, np.random.default_rng(5))
    assert sigma > 0
