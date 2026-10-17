"""docs/compute_cost.md: recorded single-core wall time of every Monte Carlo run file behind a result at the
frozen or pinned headline configuration (sum of the per-row wall times stored in the .jsonl run files)."""

from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIES = {  # study -> run-file globs (frozen or pinned headline configuration)
    "Headline Monte Carlo (pinned)": ["results/p3/headline_v2_runs/kb120_attr_freight.jsonl"],
    "Ignore-coupling fits": ["results/p4/ignore_coupling_runs.jsonl"],
    "Drift Monte Carlo": ["results/p3/drift_mc_runs/kf0.8_freight.jsonl"],
    "Model-form sensitivity (pseudo-true)": ["results/p2/model_form_mw_runs_freight/*.jsonl"],
    "Drift (pseudo-true)": ["results/p2/relative_change_runs/drift_pseudo_freight.jsonl"],
    "Nonlinear contact and generator check": ["results/p4/inverse_crime_runs/*.jsonl"],
    "Primary suspension stress test": ["results/p4/primary_damping_runs/*.jsonl"],
    "Payload bands": ["results/p4/banded_runs/*.jsonl"],
    "Bias diagnosis (headline datasets)": ["results/p4/bias_diag_y25_runs/*.jsonl"],
    "Multi-wheel Monte Carlo": ["results/p2/multiwheel_runs/*_y25.jsonl"],
    "Parameter sweep": ["results/p4/sweep_runs.jsonl"],
}


def wall(r):
    w = r.get("wall_s") or r.get("wall_fit_s") or 0.0
    if not w and "correct" in r:
        w = r.get("wall_generate_s", 0.0) + sum(r[k].get("wall_fit_s", 0.0) for k in ("correct", "single_wheelset") if k in r)
    return float(w)


def main():
    out = ["# Compute cost", "", "Recorded single-core wall time (sum of per-row wall times in the run files), "
           "on the 4-core cloud machine used, often with all cores busy. Regenerate with "
           "`python3 experiments/make_compute_cost.py`.", "", "| Study | Rows | Core-hours |", "|---|---|---|"]
    tot = 0.0
    for s, pats in STUDIES.items():
        n, h = 0, 0.0
        for p in pats:
            for f in glob.glob(str(ROOT / p)):
                for line in Path(f).read_text().splitlines():
                    if line.strip():
                        n += 1
                        h += wall(json.loads(line)) / 3600
        tot += h
        out.append(f"| {s} | {n} | {h:.1f} |")
    out += [f"| **Total** | | **{tot:.1f}** |", ""]
    (ROOT / "docs/compute_cost.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
