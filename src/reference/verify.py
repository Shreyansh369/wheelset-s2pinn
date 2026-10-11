"""G1 verification checks, shared by experiments/p1_verify.py and tests/test_reference.py."""

from __future__ import annotations

import copy
import math

import numpy as np
from scipy.linalg import eigh

from src.reference.closed_form import timoshenko_freefree_freqs
from src.reference.energy import energy_residual_window
from src.reference.frequency_domain import ForcingMap, harmonic_solution
from src.reference.params import Params
from src.reference.time_domain import newmark, rel_l2
from src.reference.timoshenko_fe import L1LinModel, section_props, timoshenko_element


def freefree_check(p: Params, d: float, L: float, n_elements: list[int], n_modes: int = 4) -> dict:
    """FE vs exact free-free frequencies of a uniform Timoshenko beam (G1a)."""
    m = p.v["material"]
    A, I = section_props(d)
    exact = timoshenko_freefree_freqs(m["E"], m["Gs"], m["kappa"], m["rho"], A, I, L, n_modes)
    out = {"d": d, "L": L, "exact_hz": (exact / (2 * math.pi)).tolist(), "fe": {}}
    for n in n_elements:
        x = np.linspace(0, L, n + 1)
        N = 2 * (n + 1)
        K, M = np.zeros((N, N)), np.zeros((N, N))
        for e in range(n):
            ke, me = timoshenko_element(m["E"], m["Gs"], m["kappa"], m["rho"], A, I, x[e + 1] - x[e])
            K[2 * e:2 * e + 4, 2 * e:2 * e + 4] += ke
            M[2 * e:2 * e + 4, 2 * e:2 * e + 4] += me
        w = np.sqrt(np.abs(eigh(K, M, eigvals_only=True)))[2:2 + n_modes]  # skip 2 rigid modes
        err = np.abs(w - exact) / exact
        out["fe"][str(n)] = {"hz": (w / (2 * math.pi)).tolist(), "rel_err": err.tolist(), "max_rel_err": float(err.max())}
    out["max_rel_err_all"] = max(v["max_rel_err"] for v in out["fe"].values())
    return out


def fd_cases(p: Params) -> list[dict]:
    b = p.v["bearing"]
    pay = p.v["payload"]
    return [
        {"name": "nominal_loaded", "kB0": b["kB0"], "cB": b["cB"], "W": pay["W_max"], "seed": 0, "rail": False},
        {"name": "soft_damped_empty", "kB0": 0.5 * b["kB0"], "cB": 2.0 * b["cB"], "W": pay["W_min"], "seed": 1, "rail": False},
        {"name": "stiff_light_mid", "kB0": 2.0 * b["kB0"], "cB": 0.5 * b["cB"], "W": 0.5 * (pay["W_min"] + pay["W_max"]),
         "seed": 2, "rail": False},
    ]


def model_for(p: Params, rail: bool, n_elements: int | None = None) -> L1LinModel:
    if not rail:
        return L1LinModel(p, n_elements)
    raw = copy.deepcopy(p.raw)
    raw["rail_sdof"]["enabled"]["value"] = True
    return L1LinModel(Params(raw), n_elements)


def fd_td_energy_check(p: Params, case: dict, T: float = 1.0, dt: float = 2e-5) -> dict:
    mdl = model_for(p, case["rail"])
    fm = ForcingMap(p)
    zeta = np.random.default_rng(case["seed"]).standard_normal(fm.n_vars)
    sol = harmonic_solution(mdl, fm, case["kB0"], case["cB"], case["W"], zeta)
    en = energy_residual_window(mdl, sol, 0.0, T)
    td = newmark(mdl, sol, T=T, dt=dt, out_every=10)
    f = td["free"]
    qf = sol.q(td["t"])[:, f]
    af = sol.qdd(td["t"])[:, f]
    ib = int(np.where(f == mdl.ib[0])[0][0])
    return {**case, "T": T, "dt": dt, "energy": en,
            "rel_l2_displacement_free_dofs": rel_l2(td["u"], qf),
            "rel_l2_axlebox_accel_left": rel_l2(td["a"][:, ib], af[:, ib]),
            "fd_vs_td_rel_l2": max(rel_l2(td["u"], qf), rel_l2(td["a"][:, ib], af[:, ib]))}


def mesh_convergence(p: Params, n_list: list[int]) -> dict:
    """Constrained-system frequencies and nominal axlebox response vs mesh size."""
    b = p.v["bearing"]
    fm = ForcingMap(p)
    out = {}
    for n in n_list:
        mdl = L1LinModel(p, n)
        m = mdl.matrices(b["kB0"], b["cB"], p.v["payload"]["W_max"])
        f = m.free
        w2 = eigh(m.K[np.ix_(f, f)], m.M[np.ix_(f, f)], eigvals_only=True)
        from src.reference.frequency_domain import unit_responses

        Xh = unit_responses(mdl, fm, b["kB0"], b["cB"], p.v["payload"]["W_max"])
        acc = -(fm.omegas**2) * Xh[:, mdl.ib[0]]
        out[str(n)] = {"n_elements_actual": mdl.mesh.x.size - 1, "modes_hz": (np.sqrt(w2[:6]) / (2 * math.pi)).tolist(),
                       "axlebox_accel_per_unit_contact_abs": np.abs(acc).tolist()}
    ref = out[str(n_list[-1])]
    for k, v in out.items():
        v["max_rel_diff_modes_vs_finest"] = float(np.max(np.abs(np.array(v["modes_hz"]) - ref["modes_hz"]) / ref["modes_hz"]))
        v["max_rel_diff_response_vs_finest"] = float(np.max(np.abs(np.array(v["axlebox_accel_per_unit_contact_abs"])
                                                               - ref["axlebox_accel_per_unit_contact_abs"])
                                                        / np.array(ref["axlebox_accel_per_unit_contact_abs"])))
    return out
