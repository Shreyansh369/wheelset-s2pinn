"""Post-process results/p0/h1_sdof.json: local slopes and degree/Pi ratios.

Writes results/p0/h1_sdof_summary.json. Reads only the saved sweep.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.results import load_result, save_result  # noqa: E402


def main() -> None:
    rows = load_result("p0/h1_sdof")["payload"]["rows"]
    out: dict = {}
    for fam in ("legendre", "hermite"):
        sel = [r for r in rows if r["family"] == fam and r["p_req_at_mean"]]
        # local log-log slopes between consecutive Pi along each damping level (all grids merged)
        local = []
        for z in sorted({r["zeta"] for r in sel}):
            rz = sorted([r for r in sel if r["zeta"] == z], key=lambda r: r["Pi"])
            for a, b in zip(rz[:-1], rz[1:]):
                if a["p_req_at_mean"] >= 3 and b["p_req_at_mean"] > a["p_req_at_mean"]:
                    local.append({"zeta": z, "Pi_mid": float(np.sqrt(a["Pi"] * b["Pi"])),
                                  "slope": float(np.log(b["p_req_at_mean"] / a["p_req_at_mean"]) / np.log(b["Pi"] / a["Pi"]))})
        bins = [(0.5, 2), (2, 5), (5, 10), (10, 40)]
        out[fam] = {
            "local_slope_by_Pi_bin": {
                f"[{lo},{hi})": {"median": float(np.median([l["slope"] for l in local if lo <= l["Pi_mid"] < hi])),
                                 "n": int(sum(lo <= l["Pi_mid"] < hi for l in local))}
                for lo, hi in bins if any(lo <= l["Pi_mid"] < hi for l in local)
            },
            "p_over_Pi_by_Pi_bin": {
                f"[{lo},{hi})": float(np.median([r["p_req_at_mean"] / r["Pi"] for r in sel if lo <= r["Pi"] < hi]))
                for lo, hi in bins if any(lo <= r["Pi"] < hi for r in sel)
            },
            "p_over_Pi2_by_Pi_bin": {
                f"[{lo},{hi})": float(np.median([r["p_req_at_mean"] / r["Pi"] ** 2 for r in sel if lo <= r["Pi"] < hi]))
                for lo, hi in bins if any(lo <= r["Pi"] < hi for r in sel)
            },
            # collapse check: spread of p_req among cases with Pi within 2% of each other
            "collapse_pairs": [
                {"Pi": [a["Pi"], b["Pi"]], "zeta": [a["zeta"], b["zeta"]], "cov_k": [a["cov_k"], b["cov_k"]],
                 "p_req": [a["p_req_at_mean"], b["p_req_at_mean"]]}
                for i, a in enumerate(sel) for b in sel[i + 1:]
                if a["grid"] == b["grid"] == "primary" and abs(a["Pi"] / b["Pi"] - 1) < 0.02 and a["zeta"] != b["zeta"]
            ],
        }
        # degree that G2's Pi^2 <= 2 would need (Pi <= sqrt 2), from the sweep
        near = [r for r in sel if 1.2 <= r["Pi"] <= 1.6]
        out[fam]["p_req_for_Pi_in_[1.2,1.6]"] = sorted({r["p_req_at_mean"] for r in near})
    save_result("p0/h1_sdof_summary", out)
    import json

    print(json.dumps(out, indent=1)[:4000])


if __name__ == "__main__":
    main()
