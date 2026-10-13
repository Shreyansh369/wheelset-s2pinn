"""Health relevance of k_B0: roller-contact stiffness against diametral clearance growth.

Roller-contact model of the wheelset document (Eqs. 10-14; src/reference/bearing.py) with the static
load shared over the rollers. Bearing geometry is a placeholder (config/params.yaml: bearing_geometry).
Journal load per bearing = (W - m_wheels - m_axle) g / 2 at the empty and loaded axle loads.
Clearance growth 0-50 um diametral on top of c_d0 (placeholder 20 um; 0 and 50 um as sensitivity).

Reports: k vs growth, % change per 10 um (secant over the first 10 um and mean slope over 0-50 um), and
the growth at which |dk/k| reaches the 0.71% detection limit (MDC, N = 50, 40 dB, co-estimating fit,
results/p2/relative_coest_drift.json). Also reported: the change diluted by series compliance if the
identified k_B0 (placeholder 1e9 N/m) is the contact stiffness in series with the rest of the support.
Writes results/p3/bearing_clearance.json.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reference.bearing import RollerBearing  # noqa: E402
from src.reference.params import G, Params, load_raw  # noqa: E402
from src.utils.results import RESULTS_DIR, Timer, save_result  # noqa: E402

GROWTH_UM = np.arange(0.0, 50.01, 1.0)


def mdc_pct():
    d = json.loads((RESULTS_DIR / "p2/relative_coest_drift.json").read_text())["payload"]
    return d["drift"]["no_drift_reference"]["coest"]["mdc_pct"]


def main():
    P = Params(load_raw())
    bg, v = P.v["bearing_geometry"], P.v
    brg = RollerBearing(int(bg["rollers_per_row"]), bg["roller_length"], bg["contact_angle"], bg["K_contact_coeff"])
    rho = v["material"]["rho"]
    xs = [0.0] + [s[0] for s in v["axle"]["sections"]]
    m_axle = 2 * sum(rho * math.pi * s[1] ** 2 / 4 * (xs[i + 1] - xs[i]) for i, s in enumerate(v["axle"]["sections"]))
    m_wheels = 2 * v["wheel"]["mass"]
    loads = {"empty": v["payload"]["W_min"], "loaded": v["payload"]["W_max"]}
    kB0_model = v["bearing"]["kB0"]
    mdc = mdc_pct()
    out = {"geometry": bg, "Kn_N_per_mm10_9": brg.Kn, "m_axle_kg": m_axle, "m_wheels_kg": m_wheels, "mdc_pct": mdc,
           "kB0_model_placeholder": kB0_model, "cases": []}
    with Timer() as tm:
        for cd0 in (bg["clearance_d0"], 0.0, 50.0):
            for lname, W in loads.items():
                F = (W * 1000 - m_wheels - m_axle) * G / 2
                rows = [dict(growth_um=g, **brg.k_mean(F, (cd0 + g) * 1e-6)) for g in GROWTH_UM]
                k = np.array([r["k_mean"] for r in rows])
                rel = (k / k[0] - 1) * 100
                i10 = int(np.argmin(np.abs(GROWTH_UM - 10)))
                cross = next((float(np.interp(-mdc, rel[i:i + 2][::-1], GROWTH_UM[i:i + 2][::-1]))
                              for i in range(len(rel) - 1) if rel[i] > -mdc >= rel[i + 1]), None)
                dil = k[0] and kB0_model / k[0]          # k_eff / k_contact if in series; < 1 dilutes the change
                keff = 1 / (1 / kB0_model - 1 / k[0] + 1 / k) if kB0_model < k[0] else None
                rel_eff = (keff / keff[0] - 1) * 100 if keff is not None else None
                cross_eff = None
                if rel_eff is not None:
                    cross_eff = next((float(np.interp(-mdc, rel_eff[i:i + 2][::-1], GROWTH_UM[i:i + 2][::-1]))
                                      for i in range(len(rel_eff) - 1) if rel_eff[i] > -mdc >= rel_eff[i + 1]), None)
                case = {"clearance_d0_um": cd0, "load": lname, "W_t": W, "F_bearing_kN": F / 1e3,
                        "k0_contact_N_per_m": float(k[0]), "n_loaded_per_row_at_0": rows[0]["n_loaded_per_row"],
                        "pct_change_first_10um": float(rel[i10]),
                        "pct_change_per_10um_mean_0_50": float(rel[-1] / 5),
                        "pct_change_at_50um": float(rel[-1]),
                        "growth_um_at_mdc": cross,
                        "roller_passage_k_ripple_pct_at_0": float((rows[0]["k_max"] - rows[0]["k_min"]) / rows[0]["k_mean"] * 100),
                        "series_dilution_factor": float(dil),
                        "pct_change_first_10um_effective": float(rel_eff[i10]) if rel_eff is not None else None,
                        "growth_um_at_mdc_effective": cross_eff,
                        "curve": [{"growth_um": r["growth_um"], "k": r["k_mean"], "k_min": r["k_min"], "k_max": r["k_max"],
                                   "Delta_um": r["Delta_um"], "n_loaded_per_row": r["n_loaded_per_row"]} for r in rows]}
                out["cases"].append(case)
                print({kk: vv for kk, vv in case.items() if kk != "curve"}, flush=True)
    save_result("p3/bearing_clearance", out, cfg={"model": "wheelset doc Eqs. 10-14, static radial load, rows symmetric, no tilt",
                                                 "growth_um": [0, 50], "cage_positions": 16}, seed=0, wall_seconds=tm.seconds)


if __name__ == "__main__":
    main()
