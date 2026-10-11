"""Exploratory (not a gate): how the effective support stiffness kB0 moves the axlebox mode and
the Cramer-Rao bound. Informs the R1 remedy decision. Writes results/p1/sensitivity_kB_scan.json."""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import copy  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reference.frequency_domain import ForcingMap  # noqa: E402
from src.reference.params import Params, load_params  # noqa: E402
from src.reference.sensitivity import fisher_crb, log_sensitivities, modal_map  # noqa: E402
from src.reference.timoshenko_fe import L1LinModel  # noqa: E402
from src.utils.results import save_result  # noqa: E402


def main() -> None:
    base = load_params()
    rows = []
    for kB0 in (1e9, 3e8, 1e8, 3e7, 1e7, 5e6):
        raw = copy.deepcopy(base.raw)
        raw["bearing"]["kB0"]["value"] = kB0
        p = Params(raw)
        mdl, fm = L1LinModel(p), ForcingMap(p)
        cB, W = p.v["bearing"]["cB"], p.v["payload"]["W_max"]
        mm = modal_map(mdl, kB0, cB, W, n_modes=8)
        ax = max((m for m in mm if m["symmetric"]), key=lambda m: m["axlebox_ke_frac"])
        s = log_sensitivities(mdl, fm, kB0, cB, W)
        crb = fisher_crb(p, mdl, fm, kB0, cB, W, n_passes=50, snr_db=40.0)
        rows.append({"kB0": kB0, "sym_axlebox_mode_hz": ax["f_hz"], "axlebox_ke_frac": ax["axlebox_ke_frac"],
                     "zeta_modal": ax["zeta_modal"],
                     "max_abs_dlogP_dlogkB0": float(abs(s["log_kB0"]).max()),
                     "max_abs_dlogP_dlogcB": float(abs(s["log_cB"]).max()),
                     "crb_rel_std_kB0_snr40_N50": crb["crb_std"][0], "crb_rel_std_cB_snr40_N50": crb["crb_std"][1]})
        print({k: (f"{v:.3g}" if isinstance(v, float) else v) for k, v in rows[-1].items()})
    save_result("p1/sensitivity_kB_scan", {"rows": rows, "note": "exploratory; cB, kp, masses at placeholder values; "
                                                                 "forcing <= 29 Hz as configured"})


if __name__ == "__main__":
    main()
