"""Rerun-or-label inventory of preregistration v2 (docs/preregistration_v2_addendum.md §9).

Every macro, table and figure used in the paper, grouped by the result file it comes from, with that file's
disposition: "rerun in v2" (with its queue) or "kept as labelled earlier-configuration result" (with the
section where the label appears). The disposition of a file of the frozen configuration before the v2 re-freeze
is its `v2` entry in config/provenance.yaml; files declared earlier before v2 keep their existing label (section
below). Exits 1 if any used source has no disposition.

    python3 scripts/v2_inventory.py > /tmp/inventory.md
"""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
# files labelled earlier before v2, and the place of their label
EARLIER_BEFORE_V2 = {
    "results/p1/bound_speed_subband.json": "Fig. 2 caption (Section 4.2)",
    "results/p1/fe_direct.json": "Table 4 caption and Section 4.2",
    "results/p2/debias_check.json": "Fig. 3 caption (Section 3)",
    "results/p2/partial_coherence_bound.json": "Table 16 caption (Section 4.7)",
    "results/p2/partial_coherence_mc.json": "Table 16 caption (Section 4.7)",
    "results/p2/partial_indep.json": "Table 16 caption and Section 4.7 Repeated passes",
    "results/p2/relative_change.json": "Fig. 6 caption (moves to Appendix A)",
    "results/p2/relative_coest_drift.json": "Table 10 caption (moves to Appendix A)",
    "results/p2/relative_intervals.json": "Table 10 and Fig. 6 captions (move to Appendix A)",
    "results/p2/scope_p2_hysteretic.json": "Table 17 and Fig. 7 captions, Section 4.7 Track-side use",
    "results/p2/wheel_lines_bound.json": "Table 13 caption and Section 4.5.4 Wheel roughness",
    "results/p2/wheel_lines_mc.json": "Table 13 caption (Section 4.5.4)",
    "results/p3/calibration.json": "Table 11 caption (moves to Appendix A)",
    "results/p3/robust_se.json": "Table 11 caption (moves to Appendix A)",
}
NONRESULT = {"config/params.yaml", "config/track.yaml", "experiments/p1_fe_direct.py"}


def main():
    M = json.loads((ROOT / "paper/generated/macro_sources.json").read_text())
    T = json.loads((ROOT / "results/tables/manifest.json").read_text())
    F = json.loads((ROOT / "figures/manifest.json").read_text())
    reg = yaml.safe_load((ROOT / "config/provenance.yaml").read_text())["files"]
    tex = "".join(re.sub(r"(?<!\\)%.*", "", Path(f).read_text()) for f in sorted(glob.glob(str(ROOT / "paper/*.tex"))))
    used_m = sorted(m for m in M if re.search(r"\\" + m + r"(?![A-Za-z])", tex))
    used_t = sorted(set(re.findall(r"\\inputtable\{(\w+)\}", tex)))
    used_f = sorted(set(re.findall(r"includegraphics(?:\[[^]]*\])?\{(\w+)\}", tex)))
    by = {}
    for m in used_m:
        by.setdefault(M[m], {"m": [], "t": [], "f": []})["m"].append(m)
    for t in used_t:
        for s in T.get(t, {}).get("sources", []):
            by.setdefault(s, {"m": [], "t": [], "f": []})["t"].append(t)
    for f in used_f:
        for s in F.get(f, []):
            by.setdefault(s, {"m": [], "t": [], "f": []})["f"].append(f)
    rows, missing = [], []
    for src in sorted(by):
        e = reg.get(src, {})
        if src in NONRESULT:
            disp = "configuration (re-frozen in v2: hash e7e594eacc87)" if src.startswith("config/") else "simulation design constants (unchanged)"
        elif e.get("v2"):
            v = e["v2"]
            disp = ("rerun in v2: " + v[len("rerun"):].lstrip(" :")) if v.startswith("rerun") else ("kept as labelled earlier-configuration result: " + v[len("earlier:"):].strip())
        elif e.get("config") == "pinned":
            disp = "kept as labelled pinned-configuration result: " + e.get("note", "pinned headline configuration")
        elif src in EARLIER_BEFORE_V2:
            disp = "kept as labelled earlier-configuration result: " + EARLIER_BEFORE_V2[src]
        else:
            disp = "UNASSIGNED"
            missing.append(src)
        it = by[src]
        rows.append(f"| `{src}` | {', '.join(it['t']) or '–'} | {', '.join(it['f']) or '–'} | "
                    f"{len(it['m'])}: {', '.join(it['m']) or '–'} | {disp} |")
    print("| Source | Tables | Figures | Macros (count: names) | Disposition |")
    print("|---|---|---|---|---|")
    print("\n".join(rows))
    if missing:
        print("\nUNASSIGNED: " + ", ".join(missing), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
