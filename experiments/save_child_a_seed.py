"""Save scenario (d) of the P1 bound scan as the starting point for Child A (not built yet).

Copies the scenario definition and its Cramer-Rao bounds from results/p1/bound_scan.json into
results/child_a/scenario_d_seed.json, so Child A starts from recorded numbers.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.results import load_result, save_result  # noqa: E402


def main() -> None:
    bs = load_result("p1/bound_scan")
    d = bs["payload"]["d_inband_oor_r0_kr_hertz_rail_150Hz"]
    dplus = bs["payload"]["d_plus_support_targets"]
    save_result("child_a/scenario_d_seed", {
        "definition": {
            "model": "realistic kB0 = 1e9 N/m; linearised Hertz contact kH = 1.4e9 (W/W0)^(1/3) + rail oscillator "
                     "(m_r 150 kg, k_r 1e8 N/m, c_r 1e5 N s/m); band <= 150 Hz; fs 1 kHz; 20 revolutions per pass",
            "forcing": "wheel OOR orders 1-15 (std 1e-4/n m), German track irregularity at 12 wavelengths 25-0.2 m",
            "targets": ["log OOR amplitude orders 1-3", "log r0", "log k_r (track / rail-pad stiffness via P2)"],
            "source_files": ["src/analysis/bound_scan.py", "experiments/p1_bound_scan.py"],
            "bound_scan_commit": bs["provenance"]["git_commit"],
        },
        "crb": d["crb"], "Pi_prior_P2": d["Pi_prior"], "p2_mode": d.get("p2_mode"),
        "crb_with_support_targets": dplus["crb"],
        "open_items_for_child_A": ["speed-measurement bias confounds r0 (frequency channel assumes exact V)",
                                   "payload measured per pass (as in the parent) instead of one unknown constant",
                                   "OOR as deterministic per wheel with tachometer vs random phase"],
    })


if __name__ == "__main__":
    main()
