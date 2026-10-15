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
    hkeys = ("KcontactLoaded", "KcontactEmpty", "AxleboxModeContactHz", "ContactPctTenLoaded", "ContactPctTenEmpty", "EffPctTenLoaded",
             "EffPctTenEmpty", "DilutionLoaded", "DilutionEmpty", "ClearanceZero", "RollersPerRow", "RollerLength")
    if b and "variant" in b["cases"][0]:
        c0 = v["bearing_geometry"]["clearance_d0"]
        cs = {(c["geometry"], c["variant"], c["clearance_d0_um"], c["load"]): c for c in b["cases"]}
        lo, em = cs[("cylindrical", "nominal geometry", c0, "loaded")], cs[("cylindrical", "nominal geometry", c0, "empty")]
        m["KcontactLoaded"] = f"{lo['k0_contact_N_per_m'] / 1e9:.1f}"
        m["KcontactEmpty"] = f"{em['k0_contact_N_per_m'] / 1e9:.1f}"
        m["AxleboxModeContactHz"] = f"{math.sqrt(lo['k0_contact_N_per_m'] / v['axlebox']['mass']) / (2 * math.pi):.0f}"
        m["ContactPctTenLoaded"] = f"{lo['pct_change_first_10um']:.1f}"
        m["ContactPctTenEmpty"] = f"{em['pct_change_first_10um']:.1f}"
        m["EffPctTenLoaded"] = f"{lo['pct_change_first_10um_effective']:.2f}"
        m["EffPctTenEmpty"] = f"{em['pct_change_first_10um_effective']:.2f}"
        m["DilutionLoaded"] = f"{lo['series_dilution_factor']:.2f}"
        m["DilutionEmpty"] = f"{em['series_dilution_factor']:.2f}"
        m["ClearanceZero"] = f"{c0:g}"
        m["RollersPerRow"] = f"{int(v['bearing_geometry']['rollers_per_row'])}"
        m["RollerLength"] = f"{v['bearing_geometry']['roller_length']:g}"
        m["HealthMDC"] = _f(b["mdc_pct"])
        for geom, G_ in (("cylindrical", "Cyl"), ("tapered", "Tap")):
            for ld, L in (("empty", "Empty"), ("loaded", "Loaded")):
                C = [c for c in b["cases"] if c["geometry"] == geom and c["load"] == ld]
                eff = [c["pct_change_first_10um_effective"] for c in C if c["pct_change_first_10um_effective"] is not None]
                gm = [c["growth_um_at_mdc_effective"] for c in C if c["growth_um_at_mdc_effective"] is not None]
                if eff:
                    m[f"{G_}EffTen{L}Min"], m[f"{G_}EffTen{L}Max"] = _f(min(eff)), _f(max(eff))
                if gm:
                    m[f"{G_}GrowthMDC{L}Min"], m[f"{G_}GrowthMDC{L}Max"] = _f(min(gm), 0), _f(max(gm), 0)
                m[f"{G_}GrowthMDC{L}Censored"] = str(sum(c["growth_um_at_mdc_effective"] is None for c in C))
            nomc = [c for c in b["cases"] if c["geometry"] == geom and c["variant"] in ("nominal geometry", "proxy geometry")
                    and c["clearance_d0_um"] == (c0 if geom == "cylindrical" else v["bearing_geometry_tapered"]["clearance_d0"])]
            for c in nomc:
                L = "Empty" if c["load"] == "empty" else "Loaded"
                m[f"{G_}GrowthMDC{L}Nom"] = "--" if c["growth_um_at_mdc_effective"] is None else _f(c["growth_um_at_mdc_effective"], 0)
                m[f"{G_}EffTen{L}Nom"] = _f(c["pct_change_first_10um_effective"])
    else:
        for k in hkeys:
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

    section4(m, miss)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["% generated by experiments/make_paper_numbers.py from results/ and config/; do not edit",
             r"\providecommand{\missing}[1]{\textbf{[missing: \texttt{#1}]}}"]
    lines += [rf"\newcommand{{\{k}}}{{{val}}}" for k, val in sorted(m.items())]
    OUT.write_text("\n".join(lines) + "\n")
    print(OUT.read_text())


def _f(x, nd=2):
    return f"{x:.{nd}f}"


def section4(m, miss):
    """Macros for Section 4 (results). Each block degrades to \\missing{file} if its source is absent."""
    def block(src, fn, keys):
        d = load(src)
        if d is None:
            for k in keys:
                m[k] = miss(src)
            return
        fn(d)

    def headline(d):
        c = {x["snr_db"]: x for x in d["cells"]}
        for snr, w in ((20, "Twenty"), (40, "Forty")):
            p = c[snr]["kB0_pooled"]
            m[f"HL{w}Bias"], m[f"HL{w}BiasSE"] = _f(100 * p["bias_rel"], 2), _f(100 * p["bias_rel_se"], 2)
            m[f"HL{w}RMSE"], m[f"HL{w}CRB"] = _f(100 * p["rmse_rel"], 2), _f(100 * p["crb_rel"], 2)
            m[f"HL{w}RatioCRB"], m[f"HL{w}RatioSE"] = _f(p["rmse_over_crb"]), _f(c[snr]["rmse_over_median_se"])
            m[f"HL{w}Cov"] = _f(p["coverage90_wald"])
            m[f"HL{w}CovLo"], m[f"HL{w}CovHi"] = _f(p["coverage90_wald_ci95"][0]), _f(p["coverage90_wald_ci95"][1])
            m[f"HL{w}cBBias"] = _f(100 * c[snr]["cB_pooled"]["bias_rel"], 1)
        m["HLN"] = str(c[20]["kB0_pooled"]["n"])
    block("p3/headline_v2_kb120_attr.json", headline, [f"HL{w}{k}" for w in ("Twenty", "Forty") for k in
          ("Bias", "BiasSE", "RMSE", "CRB", "RatioCRB", "RatioSE", "Cov", "CovLo", "CovHi", "cBBias")] + ["HLN"])

    def calib(d):
        h = {x["snr_db"]: x for x in d["headline"]}[40]
        m["CalBiasForty"], m["CalInflForty"] = _f(h["all_seeds"]["bias_pct"], 2), _f(h["all_seeds"]["inflation_rmse_over_se"])
        for sp, w in (("split_A", "A"), ("split_B", "B")):
            t = h[sp]["test_calibrated"]
            m[f"CalSplit{w}Cov"], m[f"CalSplit{w}k"], m[f"CalSplit{w}n"] = _f(t["coverage"]), str(t["covered"]), str(t["n"])
            m[f"CalSplit{w}Lo"], m[f"CalSplit{w}Hi"] = _f(t["ci95"][0]), _f(t["ci95"][1])
            m[f"CalSplit{w}Infl"] = _f(h[sp]["inflation"])
        h20 = {x["snr_db"]: x for x in d["headline"]}[20]
        m["CalTwentyRawCov"] = _f(h20["uncalibrated"]["coverage"])
        k = d["kappa_replicates"]
        m["KapCalCovered"], m["KapCalN"] = str(k["calibrated_kappa"]["covered"]), str(k["calibrated_kappa"]["n"])
        m["KapCalLo"], m["KapCalHi"] = _f(k["calibrated_kappa"]["ci95"][0]), _f(k["calibrated_kappa"]["ci95"][1])
        md = {(x["N"], x["snr_db"]): x for x in d["mdc"]}
        for (N, snr), w in (((50, 40), "FiftyForty"), ((50, 20), "FiftyTwenty"), ((200, 40), "TwoHundredForty"), ((200, 20), "TwoHundredTwenty")):
            m[f"MDC{w}"], m[f"MDCCal{w}"] = _f(md[(N, snr)]["mdc_pct"]), _f(md[(N, snr)]["mdc_calibrated_pct"])
    block("p3/calibrated.json", calib, ["CalBiasForty", "CalInflForty", "CalTwentyRawCov", "KapCalCovered", "KapCalN", "KapCalLo", "KapCalHi"]
          + [f"CalSplit{w}{k}" for w in "AB" for k in ("Cov", "k", "n", "Lo", "Hi", "Infl")]
          + [f"MDC{a}{w}" for a in ("", "Cal") for w in ("FiftyForty", "FiftyTwenty", "TwoHundredForty", "TwoHundredTwenty")])

    def oldhl(d):
        c = {x["snr_db"]: x for x in d["cells"]}
        m["IgnoreCouplingForty"] = _f(100 * c[40]["ignore_coupling_seed42"]["bias_rel"], 1)
        m["IgnoreCouplingTwenty"] = _f(100 * c[20]["ignore_coupling_seed42"]["bias_rel"], 1)
    block("p2/headline_mw.json", oldhl, ["IgnoreCouplingForty", "IgnoreCouplingTwenty"])

    def mwb(d):
        r = [x["crb_rel_kB0"] for x in d["rows"] if x["speeds"] == "uniform_60_110"]
        m["MWCRBMin"], m["MWCRBMax"] = _f(100 * min(r)), _f(100 * max(r))
        f = [x["crb_rel_kB0"] for x in d["rows"] if x["speeds"] == "fixed_100"]
        m["MWCRBFixedMin"], m["MWCRBFixedMax"] = _f(100 * min(f)), _f(100 * max(f))
    block("p2/multiwheel_bound.json", mwb, ["MWCRBMin", "MWCRBMax", "MWCRBFixedMin", "MWCRBFixedMax"])

    def mwmc(d):
        c = {x["wheels"]: x for x in d["cells"]}
        for nw, w in ((2, "Two"), (4, "Four"), (8, "Eight")):
            m[f"MWSingleBias{w}"] = _f(100 * c[nw]["single_wheelset"]["bias_rel_kB0"], 1)
            m[f"MWCorrectBias{w}"] = _f(100 * c[nw]["correct"]["bias_rel_kB0"], 2)
            m[f"MWCorrectBiasSE{w}"] = _f(100 * c[nw]["correct"]["bias_rel_kB0_se"], 2)
    block("p2/multiwheel_mc.json", mwmc, [f"MW{a}{w}" for a in ("SingleBias", "CorrectBias", "CorrectBiasSE") for w in ("Two", "Four", "Eight")])

    def fed(d):
        c = {x["cell"]: x for x in d["cells"]}
        for key, w in (("N50_fixed_100_snr40", "Fixed"), ("N50_uniform_95_105_snr40", "Narrow"), ("N50_uniform_60_110_snr40", "Wide"),
                       ("N200_uniform_60_110_snr40", "WideTwoHundred")):
            m[f"SpeedCRB{w}"] = _f(100 * c[key]["kB0"]["crb_rel_mean"])
    block("p1/fe_direct.json", fed, [f"SpeedCRB{w}" for w in ("Fixed", "Narrow", "Wide", "WideTwoHundred")])

    def bud(d):
        b = d["abs_budget_mass"]
        m["BudgetNominal"], m["BudgetNominalMassOne"] = _f(b["nominal_mass3pct"]["rss_pct"], 1), _f(b["nominal_mass1pct"]["rss_pct"], 1)
        m["BudgetCoest"], m["BudgetCoestMassOne"] = _f(b["coest_mass3pct"]["rss_pct"], 1), _f(b["coest_mass1pct"]["rss_pct"], 1)
        m["KappaNominal"] = _f(d["kappa_mass3"]["kappa"])
        m["KappaKfTerm"] = _f(d["kappa_mass3"]["terms"]["kf"])
    block("p2/relative_intervals.json", bud, ["BudgetNominal", "BudgetNominalMassOne", "BudgetCoest", "BudgetCoestMassOne", "KappaNominal", "KappaKfTerm"])

    def sens(d):
        t = {(x["estimator"], x["param"]): x for x in d["table"]}
        m["SensUnsprung"] = _f(t[("nominal", "unsprung_scale")]["sens_pct_per_10pct"], 1)
        m["SensKf"] = _f(t[("nominal", "kf")]["sens_pct_per_10pct"], 2)
    block("p2/model_form_mw_sensitivity.json", sens, ["SensUnsprung", "SensKf"])

    def rcd(d):
        m["KappaCoest"] = _f(d["coest_relative"]["kappa_coest"], 3)
        km = d["kappa_mc"]
        m["KapNomCov"], m["KapNomN"] = _f(km["coverage_kappa"]), str(km["n"])
        m["KapNomLo"], m["KapNomHi"] = _f(km["coverage_kappa_ci95"][0]), _f(km["coverage_kappa_ci95"][1])
        m["KapNomGainErr"] = _f(km["rel_gain_error_rms"])
        dr = {(x["estimator"], x["kf_factor_later"]): x for x in d["drift"]["table"]}
        m["DriftSoftTenApparent"] = _f(dr[("nominal", 0.9)]["apparent_change_no_true_change_pct"])
        m["DriftSoftTwentyApparent"] = _f(dr[("nominal", 0.8)]["apparent_change_no_true_change_pct"])
        m["DriftSoftTenFA"] = _f(dr[("nominal", 0.9)]["false_alarm_rate"])
        m["DriftStiffTenMDC"] = _f(dr[("nominal", 1.1)]["mdc_pct"], 1)
        m["DriftStiffTwentyMDC"] = _f(dr[("nominal", 1.2)]["mdc_pct"], 1)
        m["DriftCoestMDC"] = _f(dr[("coest", 0.8)]["mdc_pct"])
    block("p2/relative_coest_drift.json", rcd, ["KappaCoest", "KapNomCov", "KapNomN", "KapNomLo", "KapNomHi", "KapNomGainErr", "DriftSoftTenApparent",
                                                "DriftSoftTwentyApparent", "DriftSoftTenFA", "DriftStiffTenMDC", "DriftStiffTwentyMDC", "DriftCoestMDC"])

    def vmc(d):
        k = d["kappa_coest"]
        m["KapCoestCovered"], m["KapCoestN"] = str(round(k["coverage"] * k["n"])), str(k["n"])
        m["KapCoestLo"], m["KapCoestHi"] = _f(k["coverage_ci95"][0]), _f(k["coverage_ci95"][1])
        m["KapCoestRMS"], m["KapCoestMean"] = _f(k["rms_change_error_frac"], 3), _f(k["mean_change_error_frac"], 3)
        m["KapCoestKfMin"], m["KapCoestKfMax"] = _f(k["kf_draw_range"][0]), _f(k["kf_draw_range"][1])
        dm = {(x["estimator"], x["kf_factor"]): x for x in d["drift_mc"]}
        for e, w in (("nominal", "Nom"), ("coest", "Coest")):
            x = dm[(e, 0.8)]
            m[f"DriftMC{w}FA"], m[f"DriftMC{w}N"] = str(x["false_alarms"]), str(x["n"])
            m[f"DriftMC{w}Lo"], m[f"DriftMC{w}Hi"] = _f(x["rate_ci95"][0]), _f(x["rate_ci95"][1])
            m[f"DriftMC{w}Mean"] = _f(x["D_hat_mean_pct"])
        bd = {(x["seed"], x["variant"], x["snr_db"]): x for x in d["bias_diag"]}
        for (sd, v, snr), w in (((123, "base", 40.0), "BaseForty"), ((123, "base", 60.0), "BaseSixty"), ((123, "refined", 40.0), "Exact"),
                                ((123, "kb120", 40.0), "Wide"), ((123, "kb120_K4", 40.0), "KFour"), ((123, "kb120_K1", 40.0), "KOne"),
                                ((42, "base", 40.0), "SFtwoForty")):
            if (sd, v, snr) in bd:
                m[f"BD{w}Bias"], m[f"BD{w}Ratio"] = _f(bd[(sd, v, snr)]["bias_pct"], 3), _f(bd[(sd, v, snr)]["rmse_over_crb"])
    block("p3/validation_mc.json", vmc, ["KapCoestCovered", "KapCoestN", "KapCoestLo", "KapCoestHi", "KapCoestRMS", "KapCoestMean", "KapCoestKfMin",
                                         "KapCoestKfMax"] + [f"DriftMC{w}{k}" for w in ("Nom", "Coest") for k in ("FA", "N", "Lo", "Hi", "Mean")])

    def breg(d):
        j = d["joint_ols"]
        m["BRegRsq"], m["BRegP"] = _f(j["r2"]), _f(j["p_F"], 3)
        m["BRegPayloadP"] = _f(j["p"]["payload_sd_t"], 3)
        p = d["seed123_paired"]
        m["BDMaxDiffSNR"], m["BDMaxDiffExact"] = _f(p["max_abs_diff_60_vs_40"], 2), _f(p["max_abs_diff_refined_vs_base"], 2)
    block("p3/bias_regression.json", breg, ["BRegRsq", "BRegP", "BRegPayloadP", "BDMaxDiffSNR", "BDMaxDiffExact"])

    def cal_slope(d):
        m["CalSlope"] = f"{d['coest']['slope']:.5f}"
    block("p3/calibration.json", cal_slope, ["CalSlope"])

    def rse(d):
        h = {x["snr_db"]: x for x in d["headline"]}[40]
        m["RSEBlockCovForty"], m["RSEModelCovForty"] = _f(h["block61"]["coverage90"]), _f(h["model"]["coverage90"])
        m["RSEBlockSEForty"], m["RSEModelSEForty"] = _f(h["block61"]["se_median_pct"], 3), _f(h["model"]["se_median_pct"], 3)
    block("p3/robust_se.json", rse, ["RSEBlockCovForty", "RSEModelCovForty", "RSEBlockSEForty", "RSEModelSEForty"])

    def wl(d):
        r = {(x["speeds"], x["delta_db"], x["method"]): x["crb_kB0"] for x in d["rows"]}
        base = r[("uniform_60_110", None, "no_wheel_roughness")]
        m["WLNotchCost"] = _f(100 * (r[("uniform_60_110", 0.0, "notch")] / base - 1), 0)
        m["WLTachoZero"] = _f(100 * r[("uniform_60_110", 0.0, "tacho")])
        m["WLTachoTen"] = _f(100 * r[("uniform_60_110", 10.0, "tacho")])
        m["WLNone"] = _f(100 * base)
    block("p2/wheel_lines_bound.json", wl, ["WLNotchCost", "WLTachoZero", "WLTachoTen", "WLNone"])

    def part(d):
        c = d["cells"]
        m["PCBiasMax"] = _f(100 * max(x["bias_rel"] for x in c), 2)
        m["PCModelRatioMin"], m["PCModelRatioMax"] = _f(min(x["se_obs"]["rmse_over_median_se"] for x in c)), _f(max(x["se_obs"]["rmse_over_median_se"] for x in c))
        m["PCSandRatioMin"], m["PCSandRatioMax"] = _f(min(x["se_sandwich_bin"]["rmse_over_median_se"] for x in c)), _f(max(x["se_sandwich_bin"]["rmse_over_median_se"] for x in c))
    block("p2/partial_indep.json", part, ["PCBiasMax", "PCModelRatioMin", "PCModelRatioMax", "PCSandRatioMin", "PCSandRatioMax"])

    def p2(d):
        s = d["summary"]
        m["PTwoCTMedianCorr"] = _f(s["corrugation"]["ct23_median_MN"])
        m["PTwoCTOutsideCorr"] = _f(100 * s["corrugation"]["ct23_frac_outside_x0.7_x1.43_of_ref"], 0)
        m["PTwoCTOutsideClean"] = _f(100 * s["clean"]["ct23_frac_outside_x0.7_x1.43_of_ref"], 0)
        m["PTwoWhMedianCorr"] = _f(s["corrugation"]["whittle_median_MN"])
        m["PTwoWhMedianClean"] = _f(s["clean"]["whittle_median_MN"])
        m["PTwoWhCovCorr"], m["PTwoWhCovClean"] = _f(s["corrugation"]["whittle_profile_covers_truth"]), _f(s["clean"]["whittle_profile_covers_truth"])
    block("p2/scope_p2_hysteretic.json", p2, ["PTwoCTMedianCorr", "PTwoCTOutsideCorr", "PTwoCTOutsideClean", "PTwoWhMedianCorr", "PTwoWhMedianClean",
                                              "PTwoWhCovCorr", "PTwoWhCovClean"])

    def hertz(d):
        m["KHZeroHertz"] = _f(d["kH0_nominal"] / 1e9, 2)
        m["KHZeroLo"], m["KHZeroHi"] = _f(d["kH0_range"][0] / 1e9, 2), _f(d["kH0_range"][1] / 1e9, 2)
    block("p4/contact_hertz.json", hertz, ["KHZeroHertz", "KHZeroLo", "KHZeroHi"])

    def sweep(d):
        n, T = d["nominal"], d["table"]
        m["SweepNomMode"], m["SweepNomCRB"], m["SweepNomMDC"] = _f(n["support_mode_hz"], 0), _f(n["crb_kB0_pct"]), _f(n["mdc_pct"])
        core = [r for r in T if r["param"] != "kB0_ext"]
        crb = [r[f"crb_kB0_pct_{q}"] for r in core for q in ("low", "high")]
        mdc = [r[f"mdc_pct_{q}"] for r in core for q in ("low", "high")]
        mode = [r[f"support_mode_hz_{q}"] for r in core for q in ("low", "high")]
        m["SweepCRBMin"], m["SweepCRBMax"] = _f(min(crb)), _f(max(crb))
        m["SweepMDCMin"], m["SweepMDCMax"] = _f(min(mdc)), _f(max(mdc))
        m["SweepModeMin"], m["SweepModeMax"] = _f(min(mode), 0), _f(max(mode), 0)
        R = {r["param"]: r for r in T}
        for key, w in (("kB0", "KB"), ("cp", "Cp"), ("kB0_ext", "KBExt"), ("W_min", "Wmin"), ("cB", "CB"),
                       ("wheel_diametral_inertia", "Inertia"), ("axle_damping_zeta", "Zeta"),
                       ("wheelset_mass_wheels", "WsWheels"), ("wheelset_mass_journals", "WsJournals"), ("axlebox_mass", "Axlebox"),
                       ("kf", "Kf")):
            if key in R:
                for q, Q in (("low", "Lo"), ("high", "Hi")):
                    m[f"Sweep{w}MDC{Q}"] = _f(R[key][f"mdc_pct_{q}"])
                    m[f"Sweep{w}Mode{Q}"] = _f(R[key][f"support_mode_hz_{q}"], 0)
                    m[f"Sweep{w}CRB{Q}"] = _f(R[key][f"crb_kB0_pct_{q}"])
    block("p4/sweep.json", sweep, ["SweepNomMode", "SweepNomCRB", "SweepNomMDC", "SweepCRBMin", "SweepCRBMax", "SweepMDCMin", "SweepMDCMax",
                                   "SweepModeMin", "SweepModeMax"])

    def icrime(d):
        for mode, w in (("nl", "NL"), ("lin", "Lin")):
            if mode in d:
                c = d[mode]
                m[f"IC{w}N"], m[f"IC{w}Bias"], m[f"IC{w}BiasSE"] = str(c["n"]), _f(c["bias_pct"]), _f(c["bias_se_pct"])
                m[f"IC{w}RMSE"], m[f"IC{w}CovCal"] = _f(c["rmse_pct"]), _f(c["coverage_calibrated"])
                m[f"IC{w}CovCalLo"], m[f"IC{w}CovCalHi"] = _f(c["coverage_calibrated_ci95"][0]), _f(c["coverage_calibrated_ci95"][1])
        if "nl" in d:
            m["ICDeltaRmsMax"] = _f(100 * d["nl"]["delta_rms_over_delta0_max"], 1)
            m["ICContactLossMax"] = _f(100 * d["nl"]["contact_loss_max"], 2)
        if "nl_minus_lin" in d:
            x = d["nl_minus_lin"]
            m["ICDiffMean"], m["ICDiffSE"], m["ICDiffMax"] = _f(x["mean_pp"], 3), _f(x["se_pp"] or 0, 3), _f(x["max_abs_pp"], 3)
        if "pairs" in d:
            x = d["pairs"]
            m["ICPairsN"], m["ICPairsFA"], m["ICPairsFACal"] = str(x["n"]), str(x["false_alarms_raw"]), str(x["false_alarms_calibrated"])
            m["ICPairsFACalLo"], m["ICPairsFACalHi"] = _f(x["rate_calibrated_ci95"][0]), _f(x["rate_calibrated_ci95"][1])
    block("p4/inverse_crime.json", icrime, ["ICNLN", "ICNLBias", "ICNLRMSE", "ICNLCovCal", "ICDiffMean", "ICPairsN", "ICPairsFACal"])


if __name__ == "__main__":
    main()
