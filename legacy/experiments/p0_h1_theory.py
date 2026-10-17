"""Compare the measured H1 degrees with leading-order approximation-theory predictions.

For each SDOF case in results/p0/h1_sdof.json, locate the FRF pole in the
standardised random variable xi at the evaluation frequency w = 1, then:

* Legendre (uniform k): the pole z_p fixes the Bernstein ellipse parameter
  rho = |z_p + sqrt(z_p^2 - 1)|; orthonormal coefficients decay like rho^-n, so
  the relative variance tail after degree p is ~ rho^(-2p) and
  p_pred = ln(1/eps) / (2 ln rho).  For small damping, z_p = -2i zeta/(sqrt3 CoV),
  rho ~ 1 + 1/(sqrt3 Pi) and p_pred ~ (sqrt3/2) Pi ln(1/eps).
* Hermite (log-normal k): f is analytic in the strip |Im xi| < tau with
  tau = |Im xi_p| = atan(2 zeta)/sigma_L. Hille's theorem gives Hermite-*function*
  coefficients decaying like exp(-tau' sqrt(2n+1)) for analyticity in |Im u| < tau'.
  The probabilists' basis He_n(x) under N(0,1) maps to Hermite functions in
  u = x/sqrt2, so tau' = tau/sqrt2 and the decay is exp(-tau sqrt(n)): the
  variance tail is ~ exp(-2 tau sqrt(p)) and p_pred = ln(1/eps)^2 / (4 tau^2)
  ~ Pi^2 ln(1/eps)^2 / 4.

These are leading-order rates without algebraic prefactors; the script reports
the measured/predicted ratio. Writes results/p0/h1_theory_check.json.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.results import load_result, save_result  # noqa: E402


def legendre_pred(zeta: float, cov: float, eps: float) -> tuple[float, float]:
    k_pole = 1 - 2j * zeta  # k - w^2 + i c w = 0 at w = 1 with c = 2 zeta
    z = (k_pole - 1) / (math.sqrt(3) * cov)
    w = z + np.sqrt(z * z - 1 + 0j)
    rho = max(abs(w), 1 / abs(w))
    return math.log(1 / eps) / (2 * math.log(rho)), rho


def hermite_pred(zeta: float, cov: float, eps: float) -> tuple[float, float]:
    sig = math.sqrt(math.log1p(cov**2))
    tau = abs(math.atan2(-2 * zeta, 1.0)) / sig  # |Im xi_p| from ln(1 - 2i zeta) = sig xi - sig^2/2
    return math.log(1 / eps) ** 2 / (4 * tau**2), tau


def main() -> None:
    rec = load_result("p0/h1_sdof")
    eps = rec["config"]["tol_rel_variance_error"]
    rows = []
    for r in rec["payload"]["rows"]:
        if r["p_req_at_mean"] is None:
            continue
        f = legendre_pred if r["family"] == "legendre" else hermite_pred
        p_pred, geom = f(r["zeta"], r["cov_k"], eps)
        rows.append({**{k: r[k] for k in ("family", "grid", "zeta", "cov_k", "Pi", "p_req_at_mean")},
                     "p_pred_leading_order": p_pred, "ratio_meas_over_pred": r["p_req_at_mean"] / p_pred,
                     "rho_or_tau": geom})
    bins = [(0.5, 2), (2, 5), (5, 10), (10, 40)]
    summary = {"ln_1_over_eps": math.log(1 / eps), "sqrt3_over_2_ln_1_over_eps": math.sqrt(3) / 2 * math.log(1 / eps),
               "ln2_1_over_eps_over_4": math.log(1 / eps) ** 2 / 4}
    for fam in ("legendre", "hermite"):
        sel = [x for x in rows if x["family"] == fam and x["p_req_at_mean"] >= 3]
        summary[fam] = {
            f"[{lo},{hi})": {
                "median_ratio_meas_over_pred": float(np.median([x["ratio_meas_over_pred"] for x in sel if lo <= x["Pi"] < hi])),
                "median_p_over_Pi": float(np.median([x["p_req_at_mean"] / x["Pi"] for x in sel if lo <= x["Pi"] < hi])),
                "median_p_over_Pi2": float(np.median([x["p_req_at_mean"] / x["Pi"] ** 2 for x in sel if lo <= x["Pi"] < hi])),
                "n": int(sum(lo <= x["Pi"] < hi for x in sel)),
            }
            for lo, hi in bins if any(lo <= x["Pi"] < hi for x in sel)
        }
    # G2 reworded: Pi <= 1.5 for uniform inputs -> degree needed (measured near Pi = 1.5 and predicted at 1.5)
    leg = [x for x in rows if x["family"] == "legendre"]
    near = sorted(leg, key=lambda x: abs(x["Pi"] - 1.5))[:3]
    summary["G2_Pi_le_1.5_uniform"] = {
        "measured_p_req_nearest_cases": [{"Pi": x["Pi"], "p_req": x["p_req_at_mean"]} for x in near],
        "max_measured_p_req_for_Pi_le_1.5": max(x["p_req_at_mean"] for x in leg if x["Pi"] <= 1.5),
        "predicted_p_at_Pi_1.5_leading_order": math.sqrt(3) / 2 * 1.5 * math.log(1 / eps),
        "eps_rel_variance": eps,
    }
    save_result("p0/h1_theory_check", {"summary": summary, "rows": rows}, cfg={"eps": eps})
    import json

    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
