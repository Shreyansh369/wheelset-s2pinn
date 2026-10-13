"""Numbers quoted in the paper text, as LaTeX macros (paper/generated/numbers.tex).

Every macro is read from results/ JSON or config/ (the only derived values are unit conversions and the
single-mass axlebox frequency sqrt(k/m)/2pi, computed here from stored values). A missing source writes
\\missing{<file>} so the gap shows in the PDF.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.reference.params import Params, load_raw  # noqa: E402
from src.utils.results import RESULTS_DIR  # noqa: E402

OUT = ROOT / "paper" / "generated" / "numbers.tex"


def load(rel):
    fp = RESULTS_DIR / rel
    return json.loads(fp.read_text())["payload"] if fp.exists() else None


def main():
    m: dict[str, str] = {}
    miss = lambda f: rf"\missing{{{f}}}"  # noqa: E731
    P = Params(load_raw())
    v = P.v
    m["NumRevs"] = f"{int(v['sensor']['n_revs'])}"
    m["WIMsigmaPct"] = miss("experiments/p1_fe_direct.py: WIM")
    try:
        from experiments.p1_fe_direct import W_RANGE, WIM
        m["WIMsigmaPct"] = f"{100 * WIM:.0f}"
        m["PayloadMin"], m["PayloadMax"] = f"{W_RANGE[0]:g}", f"{W_RANGE[1]:g}"
    except Exception:  # noqa: BLE001
        pass
    m["kBnom"] = f"{v['bearing']['kB0'] / 1e9:g}"
    m["LoadExp"] = f"{v['bearing']['load_exponent']:g}"
    m["AxleboxMass"] = f"{v['axlebox']['mass']:g}"
    m["AxleboxModeNomHz"] = f"{math.sqrt(v['bearing']['kB0'] / v['axlebox']['mass']) / (2 * math.pi):.0f}"

    d = load("p2/debias_check.json")
    if d:
        s = d["summary_25_140hz"]
        m["DebiasBin"] = f"{s['bin_sampled']['rms_log_ratio']:.2f}"
        m["DebiasDeb"] = f"{s['debiased']['rms_log_ratio']:.2f}"
        m["DebiasNoise"] = f"{s['sampling_noise_rms_log_expected']:.2f}"
        m["DebiasRecords"] = f"{json.loads((RESULTS_DIR / 'p2/debias_check.json').read_text())['config']['realisations']}"
    else:
        for k in ("DebiasBin", "DebiasDeb", "DebiasNoise", "DebiasRecords"):
            m[k] = miss("p2/debias_check.json")

    b = load("p3/bearing_clearance.json")
    if b:
        c0 = v["bearing_geometry"]["clearance_d0"]
        cs = {(c["clearance_d0_um"], c["load"]): c for c in b["cases"]}
        lo, em = cs[(c0, "loaded")], cs[(c0, "empty")]
        m["KcontactLoaded"] = f"{lo['k0_contact_N_per_m'] / 1e9:.1f}"
        m["KcontactEmpty"] = f"{em['k0_contact_N_per_m'] / 1e9:.1f}"
        m["AxleboxModeContactHz"] = f"{math.sqrt(lo['k0_contact_N_per_m'] / v['axlebox']['mass']) / (2 * math.pi):.0f}"
        m["ContactPctTenLoaded"] = f"{lo['pct_change_first_10um']:.1f}"
        m["ContactPctTenEmpty"] = f"{em['pct_change_first_10um']:.1f}"
        m["EffPctTenLoaded"] = f"{lo['pct_change_first_10um_effective']:.2f}"
        m["EffPctTenEmpty"] = f"{em['pct_change_first_10um_effective']:.1f}"
        m["DilutionLoaded"] = f"{lo['series_dilution_factor']:.2f}"
        m["DilutionEmpty"] = f"{em['series_dilution_factor']:.2f}"
        m["ClearanceZero"] = f"{c0:g}"
        m["RollersPerRow"] = f"{int(v['bearing_geometry']['rollers_per_row'])}"
    else:
        for k in ("KcontactLoaded", "KcontactEmpty", "AxleboxModeContactHz", "ContactPctTenLoaded", "ContactPctTenEmpty",
                  "EffPctTenLoaded", "EffPctTenEmpty", "DilutionLoaded", "DilutionEmpty", "ClearanceZero", "RollersPerRow"):
            m[k] = miss("p3/bearing_clearance.json")

    e = load("p3/exponent_bound.json")
    keys = ("PeffSeries", "ExpCRBFifty", "ExpCRBTwoHundred", "ExpMDCFifty", "ExpMDCTwoHundred", "ExpShiftTen", "ExpShiftTwenty",
            "KBCRBExpFree", "KBCRBExpFixed")
    if e:
        m["PeffSeries"] = f"{e['series_signal']['0.0']['p_eff_lsq']:.3f}"
        rows = {r["N"]: r for r in e["rows"] if abs(r["p_true"] - 0.1) < 1e-9}
        m["ExpCRBFifty"], m["ExpCRBTwoHundred"] = f"{rows[50]['crb_p_abs']:.4f}", f"{rows[200]['crb_p_abs']:.4f}"
        m["ExpMDCFifty"], m["ExpMDCTwoHundred"] = f"{rows[50]['mdc_dp_two_periods']:.4f}", f"{rows[200]['mdc_dp_two_periods']:.4f}"
        m["ExpShiftTen"], m["ExpShiftTwenty"] = f"{rows[50]['dp_10um']:.4f}", f"{rows[50]['dp_20um']:.4f}"
        m["KBCRBExpFree"], m["KBCRBExpFixed"] = f"{100 * rows[50]['crb_kB0_rel_p_free']:.2f}", f"{100 * rows[50]['crb_kB0_rel_p_fixed']:.2f}"
    else:
        for k in keys:
            m[k] = miss("p3/exponent_bound.json")

    import inspect
    from src.inverse.multipass import MultiPassWhittle
    m["KernelHalfWidth"] = str(inspect.signature(MultiPassWhittle.__init__).parameters["Kb"].default)
    m["KernelFine"] = str(inspect.signature(MultiPassWhittle.__init__).parameters["M"].default)

    ver = load("p1/verification.json")
    if ver:
        m["GyroRatio"] = f"{ver['gyroscopic_neglect']['ratio']:.2f}"
        m["NElements"] = f"{int(v['axle']['n_elements'])}"
    else:
        m["GyroRatio"] = m["NElements"] = miss("p1/verification.json")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["% generated by experiments/make_paper_numbers.py from results/ and config/; do not edit",
             r"\providecommand{\missing}[1]{\textbf{[missing: \texttt{#1}]}}"]
    lines += [rf"\newcommand{{\{k}}}{{{val}}}" for k, val in sorted(m.items())]
    OUT.write_text("\n".join(lines) + "\n")
    print(OUT.read_text())


if __name__ == "__main__":
    main()
