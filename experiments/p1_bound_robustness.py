"""Robustness of the kB0 Cramer-Rao bound for scenario (a), as modified by the user (2026-10-11).

Model: realistic kB0 (1e9 N/m), linearised Hertz contact k_H = k_H0 (W/W0)^(1/3) + rail oscillator,
band <= 700 Hz, sampled at 2 kHz over 20 wheel revolutions.
Forcing: wheel OOR orders 1-3, German track irregularity (4 wavelengths), and rail roughness in the
one-third-octave bands 0.4 m ... 0.04 m at the ISO 3095:2013 Fig. 2 limit levels (6.2.5; values as
transcribed in the MIT-licensed `phonometry` library, commit af9d770, which notes they equal the
2007 TSI limit listed in EN 15610:2009 Annex B.9.2), shifted by an offset.

Health target: log kB0 only (clearance/wear-driven stiffness loss). Nuisances: log cB (unknown,
constant), and either
  * "levels_known": forcing spectrum levels known exactly, or
  * "levels_unknown" (primary): roughness level offset and slope, track irregularity level and
    OOR amplitudes estimated jointly.
Payload: measured per pass by weigh-in-motion with relative 1-sigma error sigma_W (3% or 10%);
each pass's true log W is a nuisance with a Gaussian prior centred on the measurement. Passes are
spread evenly over W in [5.5, 22.5] t.
Tachometer: without it, OOR phase is random per pass (variance channel only); with it the wheel
phase is known, so OOR enters as a deterministic complex amplitude Z_n (unknown, constant over
passes) that gives each pass a non-zero mean at the order frequencies.

Per pass and order: c_k ~ CN(mu_k, v_k), Fisher I_ab = 2 Re(d_a mu* d_b mu)/v + d_a v d_b v / v^2.
The per-pass log W nuisance is removed by a Schur complement with its WIM prior; the global CRB
for log kB0 treats all other globals as nuisances. Writes results/p1/bound_robustness.json.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import copy  # noqa: E402
import itertools  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analysis.bound_scan import Scenario, ScenarioModel, support_mode  # noqa: E402
from src.reference.params import Params, load_params  # noqa: E402
from src.utils.results import Timer, save_result  # noqa: E402

ISO3095_FIG2_DB = {0.4: 17.1, 0.315: 15.0, 0.25: 13.0, 0.2: 11.0, 0.16: 9.0, 0.125: 7.0, 0.1: 4.9, 0.08: 2.9,
                   0.063: 0.9, 0.05: -1.1, 0.04: -3.2, 0.0315: -5.0, 0.025: -5.6, 0.02: -6.2, 0.016: -6.8,
                   0.0125: -7.4, 0.01: -8.0, 0.008: -8.6, 0.0063: -9.2, 0.005: -9.8, 0.004: -10.4, 0.00315: -11.0}
ISO_SOURCE = ("ISO 3095:2013, 6.2.5, Figure 2 (reference-track rail roughness limit, dB re 1 um, one-third "
              "octave); values as transcribed in jmrplens/phonometry af9d770 "
              "(src/phonometry/environment/sources/rolling_stock_noise.py, REFERENCE_TRACK_ROUGHNESS_LIMIT_DB), "
              "equal to the 2007 TSI limit in EN 15610:2009 Annex B.9.2")
BAND_HZ, FS, N_PASSES = 700.0, 2000.0, 50
W_GRID = np.linspace(5.5, 22.5, 10)  # passes spread evenly over the payload range (5 per point)


def forcing_set(p: Params) -> dict:
    V = p.V
    om, var, kind, lam_r, order = [], [], [], [], []
    for n, s in zip(p.v["forcing"]["oor_orders"], p.v["forcing"]["oor_std"]):
        om.append(n * 2 * math.pi * p.f_r); var.append(2 * s**2); kind.append("oor"); lam_r.append(np.nan); order.append(n)
    Om, dOm = p.track_wavenumbers()
    for o, d in zip(Om, dOm):
        om.append(o * V); var.append(2 * p.track_psd(o) * d); kind.append("track"); lam_r.append(np.nan); order.append(0)
    for lam, L in ISO3095_FIG2_DB.items():
        f = V / lam
        if f <= BAND_HZ:
            rms = 1e-6 * 10 ** (L / 20)
            om.append(2 * math.pi * f); var.append(2 * rms**2); kind.append("rough"); lam_r.append(lam); order.append(0)
    i = np.argsort(om)
    return {k: np.asarray(v)[i] for k, v in (("omega", om), ("var", var), ("kind", kind), ("lam", lam_r),
                                              ("order", order))}


def transfer(sm: ScenarioModel, th: dict, omegas: np.ndarray, h: float = 1e-4) -> dict:
    """H and its log-parameter derivatives (kB0, cB, W) at the forcing frequencies."""
    H = sm.axlebox_accel_per_unit_input(th, omegas)
    d = {}
    for name in ("kB0", "cB", "W"):
        up = dict(th); up[name] = th[name] * math.exp(h)
        dn = dict(th); dn[name] = th[name] * math.exp(-h)
        d[name] = (sm.axlebox_accel_per_unit_input(up, omegas) - sm.axlebox_accel_per_unit_input(dn, omegas)) / (2 * h)
    return {"H": H, "d": d}


def pass_fisher(T: dict, F: dict, rough_db: float, snr_db: float, levels: str, tacho: bool) -> tuple[np.ndarray, list]:
    """Fisher over [globals..., logW] for one pass."""
    H, dH = T["H"], T["d"]
    var = F["var"].copy()
    rough = F["kind"] == "rough"
    var[rough] *= 10 ** (rough_db / 10)
    oor = F["kind"] == "oor"
    Zoor = np.sqrt(var[oor])  # deterministic OOR amplitude when the phase is known (|Z|^2 = E|Z|^2)
    rand_var = var.copy()
    if tacho:
        rand_var[oor] = 0.0
    sig_pow = 0.5 * np.sum(np.abs(H) ** 2 * var)
    f_r = F["omega"][F["order"] == 1][0] / (2 * math.pi)
    n_samp = int(20 * FS / f_r)  # 20 wheel revolutions at FS
    e_noise = 4 * sig_pow / 10 ** (snr_db / 10) / n_samp
    v = np.abs(H) ** 2 * rand_var + e_noise
    names = ["log_kB0", "log_cB"]
    dv = {"log_kB0": 2 * np.real(np.conj(H) * dH["kB0"]) * rand_var,
          "log_cB": 2 * np.real(np.conj(H) * dH["cB"]) * rand_var,
          "log_W": 2 * np.real(np.conj(H) * dH["W"]) * rand_var}
    dmu = {"log_kB0": np.zeros_like(H), "log_cB": np.zeros_like(H), "log_W": np.zeros_like(H)}
    if tacho:
        for nm, key in (("log_kB0", "kB0"), ("log_cB", "cB"), ("log_W", "W")):
            dmu[nm][oor] = dH[key][oor] * Zoor
    if levels.startswith("band_prior_") or levels == "free_per_band":  # stress test: every roughness band level free, plus track and OOR levels
        names += ["log_track_level"]
        dv["log_track_level"] = np.where(F["kind"] == "track", np.abs(H) ** 2 * rand_var, 0.0)
        if levels.startswith("band_prior_"):  # keep the smooth offset + slope too
            lam = F["lam"]
            names += ["rough_offset_db", "rough_slope_db_per_decade"]
            dv["rough_offset_db"] = np.where(rough, np.abs(H) ** 2 * rand_var * math.log(10) / 10, 0.0)
            dv["rough_slope_db_per_decade"] = np.where(rough, np.abs(H) ** 2 * rand_var * math.log(10) / 10
                                                       * np.log10(np.where(rough, lam, 1.0) / 0.1), 0.0)
        for k in np.where(rough)[0]:
            nm = f"log_rough_band_{F['lam'][k]:g}"
            names.append(nm)
            dv[nm] = np.zeros_like(v)
            dv[nm][k] = np.abs(H[k]) ** 2 * rand_var[k]
        for k in np.where(oor)[0]:
            n = int(F["order"][k])
            if tacho:
                for part, fac in (("re", 1.0), ("im", 1j)):
                    nm = f"oor{n}_{part}"
                    names.append(nm)
                    dv[nm] = np.zeros_like(v)
                    dmu[nm] = np.zeros_like(H)
                    dmu[nm][k] = H[k] * fac
            else:
                nm = f"log_oor{n}_amp"
                names.append(nm)
                dv[nm] = np.zeros_like(v)
                dv[nm][k] = 2 * np.abs(H[k]) ** 2 * rand_var[k]
    if levels == "unknown":
        lam = F["lam"]
        names += ["rough_offset_db", "rough_slope_db_per_decade", "log_track_level"]
        dv["rough_offset_db"] = np.where(rough, np.abs(H) ** 2 * rand_var * math.log(10) / 10, 0.0)
        dv["rough_slope_db_per_decade"] = np.where(rough, np.abs(H) ** 2 * rand_var * math.log(10) / 10
                                                   * np.log10(np.where(rough, lam, 1.0) / 0.1), 0.0)
        dv["log_track_level"] = np.where(F["kind"] == "track", np.abs(H) ** 2 * rand_var, 0.0)
        for k in np.where(oor)[0]:
            n = int(F["order"][k])
            if tacho:  # complex OOR amplitude: Re and Im nuisances
                for part, fac in (("re", 1.0), ("im", 1j)):
                    nm = f"oor{n}_{part}"
                    names.append(nm)
                    dv[nm] = np.zeros_like(v)
                    dmu[nm] = np.zeros_like(H)
                    dmu[nm][k] = H[k] * fac
            else:
                nm = f"log_oor{n}_amp"
                names.append(nm)
                dv[nm] = np.zeros_like(v)
                dv[nm][k] = 2 * np.abs(H[k]) ** 2 * rand_var[k]
    for nm in names + ["log_W"]:
        dv.setdefault(nm, np.zeros_like(v))
        dmu.setdefault(nm, np.zeros_like(H))
    allp = names + ["log_W"]
    J = np.zeros((len(allp), len(allp)))
    for a, pa in enumerate(allp):
        for b, pb in enumerate(allp):
            J[a, b] = np.sum(2 * np.real(np.conj(dmu[pa]) * dmu[pb]) / v + dv[pa] * dv[pb] / v**2)
    return J, names


def band_prior_info(names: list, levels: str, n_passes_scale: float) -> np.ndarray:
    """Prior information on per-band log-level deviations (added once, not per pass)."""
    P = np.zeros((len(names), len(names)))
    if levels.startswith("band_prior_"):
        sig_db = float(levels.split("_")[-1].replace("dB", ""))
        sig_log = sig_db * math.log(10) / 10
        for i, nm in enumerate(names):
            if nm.startswith("log_rough_band_"):
                P[i, i] = 1 / sig_log**2
    return P


def robust_crb(J: np.ndarray, target: int = 0) -> float:
    d = 1 / np.sqrt(np.maximum(np.diag(J), 1e-300))
    Js = J * np.outer(d, d)
    lam, V = np.linalg.eigh(Js)
    good = lam > 1e-10
    if ((V[:, ~good] ** 2).sum(1)[target] if (~good).any() else 0.0) > 1e-6:
        return float("inf")
    return float(d[target] * np.sqrt((V[target, good] ** 2 / lam[good]).sum()))


def main() -> None:
    base = load_params()
    F = forcing_set(base)
    th0 = {"kB0": 1e9, "cB": 5e3, "k_r": 1e8, "r0": base.r0}
    grid = {"rough_offset_db": [-10.0, 0.0, 10.0], "axle_damping_factor": [0.5, 1.0, 2.0],
            "kH0_factor": [0.7, 1.0, 1.3], "tacho": [False, True], "wim_sigma": [0.03, 0.10],
            "snr_db": [20.0, 40.0], "levels": ["unknown", "known", "band_prior_0.5dB", "band_prior_1dB", "band_prior_2dB", "band_prior_4dB", "band_prior_6dB", "free_per_band"]}
    rows = []
    with Timer() as tm:
        cache = {}
        for dfac, kfac in itertools.product(grid["axle_damping_factor"], grid["kH0_factor"]):
            raw = copy.deepcopy(base.raw)
            raw["axle"]["damping_zeta"]["value"] = base.v["axle"]["damping_zeta"] * dfac
            p = Params(raw)
            sc = Scenario(name="a_mod", kB0=1e9, cB=5e3, contact="hertz_rail", band_hz=BAND_HZ, fs=FS,
                          forcing_spec={}, targets=["log_kB0"], kH0=1.4e9 * kfac)
            sm = ScenarioModel(p, sc)
            Ts = [transfer(sm, dict(th0, W=float(W)), F["omega"]) for W in W_GRID]
            # support-mode damping ratio and its log-gradient (for reporting zeta_s, not bearing damping)
            thn = dict(th0, W=22.5)
            z0 = support_mode(sm.modes(thn))
            gz = []
            for nm in ("kB0", "cB"):
                u = dict(thn); u[nm] *= math.exp(1e-4)
                dd = dict(thn); dd[nm] *= math.exp(-1e-4)
                gz.append((math.log(support_mode(sm.modes(u))["zeta"]) - math.log(support_mode(sm.modes(dd))["zeta"])) / 2e-4)
            cache[(dfac, kfac)] = (Ts, z0, np.array(gz))
        for rdb, dfac, kfac, tacho, sw, snr, lev in itertools.product(*grid.values()):
            Ts, z0, gz = cache[(dfac, kfac)]
            Jtot = None
            for T in Ts:
                J, names = pass_fisher(T, F, rdb, snr, lev, tacho)
                g = len(names)
                Jgg, Jgw, Jww = J[:g, :g], J[:g, g], J[g, g] + 1 / sw**2
                Jeff = (N_PASSES / len(W_GRID)) * (Jgg - np.outer(Jgw, Jgw) / Jww)
                Jtot = Jeff if Jtot is None else Jtot + Jeff
            Jtot = Jtot + band_prior_info(names, lev, 1.0)
            crb_k = robust_crb(Jtot, 0)
            # zeta_s (support-mode damping ratio) via the delta method on (log kB0, log cB)
            try:
                cov2 = np.linalg.inv(Jtot)[:2, :2]
                crb_z = float(math.sqrt(max(gz @ cov2 @ gz, 0)))
            except np.linalg.LinAlgError:
                crb_z = float("inf")
            rows.append({"rough_offset_db": rdb, "axle_damping_factor": dfac, "kH0_factor": kfac, "tacho": tacho,
                         "wim_sigma": sw, "snr_db": snr, "levels": lev, "crb_rel_kB0": crb_k,
                         "crb_rel_zeta_s": crb_z, "support_mode_hz": z0["f_hz"], "zeta_s": z0["zeta"],
                         "dlogzeta_dlogcB": float(gz[1])})
    prim = [r for r in rows if r["levels"] == "unknown"]
    summ = {
        "primary_levels_unknown": {"max_crb_rel_kB0": max(r["crb_rel_kB0"] for r in prim),
                                   "min_crb_rel_kB0": min(r["crb_rel_kB0"] for r in prim),
                                   "all_below_5pct": all(r["crb_rel_kB0"] < 0.05 for r in prim),
                                   "worst_case": max(prim, key=lambda r: r["crb_rel_kB0"])},
        "levels_known": {"max_crb_rel_kB0": max(r["crb_rel_kB0"] for r in rows if r["levels"] == "known"),
                         "all_below_5pct": all(r["crb_rel_kB0"] < 0.05 for r in rows if r["levels"] == "known")},
    }
    for lv in ("band_prior_0.5dB", "band_prior_1dB", "band_prior_2dB", "band_prior_4dB", "band_prior_6dB"):
        sel = [r for r in rows if r["levels"] == lv]
        summ[f"intermediate_{lv}"] = {"max_crb_rel_kB0": max(r["crb_rel_kB0"] for r in sel),
                                      "min_crb_rel_kB0": min(r["crb_rel_kB0"] for r in sel),
                                      "all_below_5pct": all(r["crb_rel_kB0"] < 0.05 for r in sel),
                                      "frac_below_5pct": float(np.mean([r["crb_rel_kB0"] < 0.05 for r in sel]))}
    fb = [r for r in rows if r["levels"] == "free_per_band"]
    summ["stress_free_per_band_levels"] = {
        "max_crb_rel_kB0": max(r["crb_rel_kB0"] for r in fb), "min_crb_rel_kB0": min(r["crb_rel_kB0"] for r in fb),
        "all_below_5pct": all(r["crb_rel_kB0"] < 0.05 for r in fb), "worst_case": max(fb, key=lambda r: r["crb_rel_kB0"]),
        "max_by_wim_sigma": {str(v): max(r["crb_rel_kB0"] for r in fb if r["wim_sigma"] == v) for v in grid["wim_sigma"]},
        "max_by_tacho": {str(v): max(r["crb_rel_kB0"] for r in fb if r["tacho"] == v) for v in grid["tacho"]},
        "frac_below_5pct": float(np.mean([r["crb_rel_kB0"] < 0.05 for r in fb])),
    }
    for key in ("rough_offset_db", "axle_damping_factor", "kH0_factor", "tacho", "wim_sigma", "snr_db"):
        summ[f"max_by_{key}"] = {str(v): max(r["crb_rel_kB0"] for r in prim if r[key] == v) for v in grid[key]}
    save_result("p1/bound_robustness", {"summary": summ, "rows": rows, "forcing_hz": (F["omega"] / (2 * math.pi)).tolist(),
                                        "forcing_kind": F["kind"].tolist()},
                cfg={"grid": grid, "N_passes": N_PASSES, "W_grid_t": W_GRID.tolist(), "band_hz": BAND_HZ, "fs": FS,
                     "roughness_source": ISO_SOURCE, "kH0_nominal": 1.4e9,
                     "wim_sigma_meaning": "relative 1-sigma error of the per-pass payload measurement"},
                wall_seconds=tm.seconds)
    import json

    print(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
