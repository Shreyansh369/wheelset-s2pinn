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


LAST = ["config/params.yaml"]      # most recently loaded source: macros set after a load are attributed to it


class Macros(dict):
    def __init__(self):
        super().__init__()
        self.src = {}

    def __setitem__(self, k, v):
        super().__setitem__(k, v)
        self.src[k] = LAST[0]


def load(rel):
    LAST[0] = f"results/{rel}"
    fp = RESULTS_DIR / rel
    return json.loads(fp.read_text())["payload"] if fp.exists() else None


def main():
    m = Macros()
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
    try:                                  # observation design: noise band, record length, ISO 3095 table range
        from experiments.p1_bound_robustness import ISO3095_FIG2_DB
        from src.inverse.multipass import F_HI, F_LO, FS, N_REVS, NOISE_BAND
        L = N_REVS * 2 * math.pi * v["wheel"]["r0"]
        nb = [int((NOISE_BAND[1] - NOISE_BAND[0]) * L / (V / 3.6)) for V in (110.0, 60.0)]
        m["NoiseLo"], m["NoiseHi"] = f"{NOISE_BAND[0]:.0f}", f"{NOISE_BAND[1]:.0f}"
        m["NoiseBinsMin"], m["NoiseBinsMax"] = str(nb[0]), str(nb[1])
        m["NoiseRelSEMax"] = f"{100 / math.sqrt(nb[0]):.0f}"
        m["SampleRate"], m["BandLo"], m["BandHi"] = f"{FS:.0f}", f"{F_LO:.0f}", f"{F_HI:.0f}"
        m["RecordLength"] = f"{L:.1f}"
        m["ISOLambdaMax"], m["ISOLambdaMinMM"] = f"{max(ISO3095_FIG2_DB):.2f}", f"{1000 * min(ISO3095_FIG2_DB):.2f}"
        m["ISONBands"] = str(len(ISO3095_FIG2_DB))
        m["LambdaMinCM"] = f"{100 * 60 / 3.6 / F_HI:.1f}"
        m["LambdaMaxM"] = f"{110 / 3.6 / F_LO:.2f}"
    except Exception as e:  # noqa: BLE001
        print("observation-design macros:", e)
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
             r"\providecommand{\missing}[1]{\textbf{[missing: \texttt{\detokenize{#1}}]}}"]
    lines += [rf"\newcommand{{\{k}}}{{{val}}}" for k, val in sorted(m.items())]
    OUT.write_text("\n".join(lines) + "\n")
    (OUT.parent / "macro_sources.json").write_text(json.dumps(dict(sorted(m.src.items())), indent=0))
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
        P = [c[x]["kB0_pooled"] for x in (20, 40)]
        m["HLBiasAbsMax"] = _f(max(abs(100 * p["bias_rel"]) for p in P), 2)
        m["HLRMSEMin"], m["HLRMSEMax"] = _f(min(100 * p["rmse_rel"] for p in P)), _f(max(100 * p["rmse_rel"] for p in P))
        m["HLCRBMin"], m["HLCRBMax"] = _f(min(100 * p["crb_rel"] for p in P)), _f(max(100 * p["crb_rel"] for p in P))
        m["HLRatioCRBMax"] = _f(max(p["rmse_over_crb"] for p in P))
    hl_src = "p3/headline_v2_kb120_attr_freight.json" if load("p3/headline_v2_kb120_attr_freight.json") else "p3/headline_v2_kb120_attr.json"
    block(hl_src, headline, [f"HL{w}{k}" for w in ("Twenty", "Forty") for k in
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
        for sp, w in (("split_A", "A"), ("split_B", "B")):
            t = h20[sp]["test_calibrated"]
            m[f"CalTwentySplit{w}Cov"], m[f"CalTwentySplit{w}k"], m[f"CalTwentySplit{w}n"] = _f(t["coverage"]), str(t["covered"]), str(t["n"])
            m[f"CalTwentySplit{w}Lo"], m[f"CalTwentySplit{w}Hi"] = _f(t["ci95"][0]), _f(t["ci95"][1])
        k = d["kappa_replicates"]
        load("p3/validation_mc.json")     # attribution: the kappa replicates (earlier configuration), calibrated
        m["KapCalCovered"], m["KapCalN"] = str(k["calibrated_kappa"]["covered"]), str(k["calibrated_kappa"]["n"])
        m["KapCalLo"], m["KapCalHi"] = _f(k["calibrated_kappa"]["ci95"][0]), _f(k["calibrated_kappa"]["ci95"][1])
        kc = k["calibrated_kappa"]
        m["KapCalNAll"], m["KapCalNSing"] = str(kc.get("n_all", kc["n"])), str(len(kc.get("singular_reps", [])))
        load("p3/calibrated.json")
        md = {(x["N"], x["snr_db"]): x for x in d["mdc"]}
        for (N, snr), w in (((50, 40), "FiftyForty"), ((50, 20), "FiftyTwenty"), ((200, 40), "TwoHundredForty"), ((200, 20), "TwoHundredTwenty")):
            m[f"MDC{w}"], m[f"MDCCal{w}"] = _f(md[(N, snr)]["mdc_pct"]), _f(md[(N, snr)]["mdc_calibrated_pct"])
        for N, w in ((50, "Fifty"), (200, "TwoHundred")):
            v = [md[(N, snr)]["mdc_calibrated_pct"] for snr in (20, 40)]
            m[f"MDCCal{w}Min"], m[f"MDCCal{w}Max"] = _f(min(v)), _f(max(v))
        mb = load("p4/mdc_bounds.json")    # uncalibrated MDC straight from the bounds (frozen configuration)
        if mb:
            r = {(x["N"], x["snr_db"]): x for x in mb["rows"] if x["estimator"] == "coest"}
            for (N, snr), w in (((50, 40), "FiftyForty"), ((50, 20), "FiftyTwenty"), ((200, 40), "TwoHundredForty"), ((200, 20), "TwoHundredTwenty")):
                m[f"MDC{w}"] = _f(r[(N, float(snr))]["mdc_pct"])
    block("p3/calibrated.json", calib, ["CalBiasForty", "CalInflForty", "CalTwentyRawCov", "KapCalCovered", "KapCalN", "KapCalLo", "KapCalHi",
                                        "KapCalNAll", "KapCalNSing"]
          + [f"CalSplit{w}{k}" for w in "AB" for k in ("Cov", "k", "n", "Lo", "Hi", "Infl")]
          + [f"MDC{a}{w}" for a in ("", "Cal") for w in ("FiftyForty", "FiftyTwenty", "TwoHundredForty", "TwoHundredTwenty")])

    def ignc(d):
        m["IgnoreCouplingForty"], m["IgnoreCouplingFortySE"] = _f(d["bias_pct"], 1), _f(d["bias_se_pct"], 1)
        m["IgnoreCouplingN"], m["IgnoreCouplingCovered"] = str(d["n"]), str(d["covered_90"])
    block("p4/ignore_coupling.json", ignc, ["IgnoreCouplingForty", "IgnoreCouplingFortySE", "IgnoreCouplingN", "IgnoreCouplingCovered"])

    def mwb(d):
        r = [x["crb_rel_kB0"] for x in d["rows"] if x["speeds"] == "uniform_60_110"]
        m["MWCRBMin"], m["MWCRBMax"] = _f(100 * min(r), 3), _f(100 * max(r), 3)
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

    def budf(d):                          # current configuration: overrides the absolute budget above
        from experiments.budget import budget
        b = budget(d)
        for e, w in (("nominal", "Nominal"), ("coest", "Coest")):
            m[f"Budget{w}"], m[f"Budget{w}MassOne"] = _f(b[e]["rss_pct"], 1), _f(b[e]["rss_mass1_pct"], 1)
        m["BudgetMassSigmaPct"] = _f(b["mass_sigma_pct"], 0)
    if (load("p2/model_form_mw_sensitivity.json") or {}).get("budget"):
        block("p2/model_form_mw_sensitivity.json", budf, [])

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

    def driftf(d):                       # current configuration: overrides the drift values above
        dr = {(x["estimator"], x["kf_factor_later"]): x for x in d["table"]}
        m["DriftSoftTenApparent"] = _f(dr[("nominal", 0.9)]["apparent_change_no_true_change_pct"])
        m["DriftSoftTwentyApparent"] = _f(dr[("nominal", 0.8)]["apparent_change_no_true_change_pct"])
        m["DriftSoftTenFA"] = _f(dr[("nominal", 0.9)]["false_alarm_rate"])
        m["DriftStiffTenMDC"] = _f(dr[("nominal", 1.1)]["mdc_pct"], 1)
        m["DriftStiffTwentyMDC"] = _f(dr[("nominal", 1.2)]["mdc_pct"], 1)
        if ("coest", 0.8) in dr:
            m["DriftCoestMDC"] = _f(dr[("coest", 0.8)]["mdc_pct"])
            m["DriftCoestTwentyApparent"] = _f(abs(dr[("coest", 0.8)]["apparent_change_no_true_change_pct"]))
            m["DriftCoestMaxAbsApparent"] = _f(max(abs(x["apparent_change_no_true_change_pct"]) for x in d["table"] if x["estimator"] == "coest"))
        m["DriftNoDriftCoestMDC"] = _f(d["no_drift_reference"]["coest"]["mdc_pct"]) if "coest" in d["no_drift_reference"] else "--"
    if load("p2/drift_freight.json"):
        block("p2/drift_freight.json", driftf, [])

    def vmc(d):
        k = d["kappa_coest"]
        m["KapCoestCovered"], m["KapCoestN"] = str(round(k["coverage"] * k["n"])), str(k["n"])
        m["KapCoestLo"], m["KapCoestHi"] = _f(k["coverage_ci95"][0]), _f(k["coverage_ci95"][1])
        m["KapCoestRMS"], m["KapCoestMean"] = _f(k["rms_change_error_frac"], 3), _f(k["mean_change_error_frac"], 3)
        m["KapCoestKfMin"], m["KapCoestKfMax"] = _f(k["kf_draw_range"][0]), _f(k["kf_draw_range"][1])
        m["KapCoestNAll"], m["KapCoestNSing"] = str(k.get("n_all", k["n"])), str(len(k.get("singular_reps", [])))
        sm = k.get("coverage_singular_as_not_covered_ci95", k["coverage_ci95"])
        m["KapCoestCovSingMiss"] = _f(k.get("coverage_singular_as_not_covered", k["coverage"]))
        m["KapCoestCovSingMissLo"], m["KapCoestCovSingMissHi"] = _f(sm[0]), _f(sm[1])
        # rank and count of the factor actually used (pre-registered rule: all replicates when that factor is larger)
        if k.get("inflation_for_90pct_all") is not None and k.get("inflation_conservative") == k["inflation_for_90pct_all"]:
            m["KapInflRank"], m["KapInflOf"] = str(k["inflation_rank_all"]), str(k["n_all"])
        else:
            m["KapInflRank"], m["KapInflOf"] = str(k.get("inflation_rank", math.ceil(0.9 * k["n"]))), str(k["n"])
        if k.get("sing_se_check"):
            m["KapSingSECheckMaxDev"] = _f(max(abs(x["ratio"] - 1) for x in k["sing_se_check"]), 3)
        at = d.get("kappa_coest_attribution")
        if at:
            m["KapAttrAxleCorr"] = _f(at["pearson_error_frac_vs_log_factor"]["axle_damp_scale"])
            m["KapAttrAxleRsq"], m["KapAttrAllRsq"] = _f(at["r2_axle_damp_only"]), _f(at["r2_all_five"])
            m["KapAttrAxleSlope"] = _f(at["slope_axle_damp_per_log"])
            m["KapAttrResidRMS"] = _f(at["resid_rms_error_frac_after_axle_damp"], 3)
            m["KapCBBoundN"] = str(at["cb_lower_bound_n"])
        cur = any(x.get("file", "").endswith("_freight.jsonl") for x in d["drift_mc"])   # current config if present
        dm = {(x["estimator"], x["kf_factor"]): x for x in d["drift_mc"]
              if (x.get("file", "").endswith("_freight.jsonl") if cur else not x.get("file", "").endswith("_freight.jsonl"))}
        m["DriftMCCurrentConfig"] = "1" if cur else "0"
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
                                         "KapCoestKfMax", "KapCoestNAll", "KapCoestNSing", "KapCoestCovSingMiss", "KapCoestCovSingMissLo",
                                         "KapCoestCovSingMissHi", "KapInflRank", "KapInflOf"]
          + [f"DriftMC{w}{k}" for w in ("Nom", "Coest") for k in ("FA", "N", "Lo", "Hi", "Mean")])
    for k in ("KapAttrAxleCorr", "KapAttrAxleRsq", "KapAttrAllRsq", "KapAttrAxleSlope", "KapAttrResidRMS", "KapCBBoundN",
              "KapSingSECheckMaxDev"):
        if k not in m:
            m[k] = miss("p3/validation_mc.json (kappa_coest_attribution)")

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

    def pdamp(d):
        p = d["pseudo_true"]
        m["PDNominalBias"], m["PDCoestBias"] = _f(p["nominal"]["bias_pct"]), _f(p["coest"]["bias_pct"])
        if "pairs" in d:
            x = d["pairs"]
            m["PDPairsN"], m["PDPairsFA"] = str(x["n"]), str(x["false_alarms_raw"])
            m["PDPairsMean"] = _f(x["D_mean_pct"])
            m["PDLevelBias"] = _f(x["level_bias_mean_pct"])
            az = [abs(z) for z in x.get("z", [])]
            if az:
                m["PDPairsAbsZMin"], m["PDPairsAbsZMax"] = _f(min(az), 1), _f(max(az), 1)
                m["PDLevelMin"], m["PDLevelMax"] = _f(x["level_err_min_pct"], 1), _f(x["level_err_max_pct"], 1)
                m["PDPairsSE"] = _f(x["se_median_pct"])
    block("p4/primary_damping.json", pdamp, ["PDNominalBias", "PDCoestBias", "PDPairsN", "PDPairsFA", "PDPairsMean"])

    def banded(d):
        B = {(r["band"], r["N"], int(r["snr_db"])): r for r in d["bounds"]}
        for b, w in (("empty", "Empty"), ("laden", "Laden")):
            for N, n in ((50, "Fifty"), (200, "TwoHundred")):
                v = [B[(b, N, s)]["mdc_pct"] for s in (20, 40) if (b, N, s) in B]
                if v:
                    m[f"Band{w}MDC{n}Min"], m[f"Band{w}MDC{n}Max"] = _f(min(v)), _f(max(v))
                for s_, sn in ((20, "Twenty"), (40, "Forty")):
                    if (b, N, s_) in B:
                        m[f"Band{w}MDC{n}{sn}"] = _f(B[(b, N, s_)]["mdc_pct"])
                        m[f"Band{w}CRB{n}{sn}"] = _f(B[(b, N, s_)]["crb_kB0_pct"])
            if b in d.get("pseudo_true", {}):
                m[f"Band{w}Pseudo"] = _f(d["pseudo_true"][b])
            if b in d.get("pairs", {}):
                x = d["pairs"][b]
                m[f"Band{w}PairsN"], m[f"Band{w}PairsFA"] = str(x["n"]), str(x["false_alarms"])
                m[f"Band{w}PairsFALo"], m[f"Band{w}PairsFAHi"] = _f(x["rate_ci95"][0]), _f(x["rate_ci95"][1])
                zz = x.get("z_median_se_fallback", x["z"])
                m[f"Band{w}ZMin"], m[f"Band{w}ZMax"] = _f(min(zz), 1), _f(max(zz), 1)
                m[f"Band{w}NFiniteSE"] = str(x.get("n_finite_se", x["n"]))
                m[f"Band{w}NSingular"] = str(x["n"] - x.get("n_finite_se", x["n"]))
                m[f"Band{w}DMax"] = _f(max(x.get("D_pct", [0.0])), 1)
                m[f"Band{w}ZPos"] = str(sum(z > 0 for z in zz))
                m[f"Band{w}MeanD"] = _f(x["D_mean_pct"])
                m[f"Band{w}SE"] = _f(x["se_median_pct"])
                m[f"Band{w}LevelMean"], m[f"Band{w}LevelSD"] = _f(x["level_err_mean_pct"]), _f(x["level_err_sd_pct"])
    block("p4/banded.json", banded, ["BandEmptyMDCFiftyMin"])

    def banded_extra(d):                  # laden band with c_B fixed; within-band calibration of the empty band
        x = d.get("pairs_laden_cbfix")
        if x:
            m["BandLadenFixPairsN"], m["BandLadenFixPairsFA"] = str(x["n"]), str(x["false_alarms"])
            m["BandLadenFixPairsFAHi"] = _f(x["rate_ci95"][1])
            m["BandLadenFixZMin"], m["BandLadenFixZMax"] = _f(min(x["z"]), 1), _f(max(x["z"]), 1)
            m["BandLadenFixDMax"], m["BandLadenFixSE"] = _f(max(x["D_pct"]), 1), _f(x["se_median_pct"])
        ps = d.get("pseudo_laden_cbfix") or {}
        for k, w in (("1.0", "One"), ("0.5", "Half"), ("2.0", "Two")):
            if k in ps:
                m[f"BandLadenFixPseudo{w}"] = _f(ps[k])
        le = d.get("lean_empty")
        if le:
            m["LeanN"], m["LeanMean"], m["LeanMeanSE"] = str(le["n"]), _f(le["D_mean_pct"]), _f(le["D_mean_se_pct"])
            m["LeanZMean"], m["LeanZSD"], m["LeanSDOverSE"] = _f(le["z_mean"]), _f(le["z_sd"]), _f(le["sd_over_mean_se"])
            m["LeanNPos"] = str(le["n_positive"])
            m["LeanCorrMax"] = _f(max(abs(le[k]) for k in ("corr_D_dW", "corr_D_dV", "corr_D_dg")))
            m["LeanSDPct"], m["LeanSEPct"] = _f(le["D_sd_pct"]), _f(le["se_mean_pct"])
            m["LeanMeanZ"] = _f(le["D_mean_pct"] / le["D_mean_se_pct"], 1)
            for k, w in (("first_run", "One"), ("replication", "Two")):
                b = le.get(k)
                if b:
                    m[f"Lean{w}Mean"], m[f"Lean{w}SE"] = _f(b["D_mean_pct"]), _f(b["D_mean_se_pct"])
                    m[f"Lean{w}Pos"], m[f"Lean{w}N"] = str(b["n_positive"]), str(b["n"])
                    m[f"Lean{w}Z"] = _f(b["D_mean_pct"] / b["D_mean_se_pct"], 1)
            from scipy.stats import t as _t
            m["LeanMeanP"] = _f(2 * _t.sf(abs(le["D_mean_pct"] / le["D_mean_se_pct"]), le["n"] - 1), 2)
    block("p4/banded.json", banded_extra, [])

    def bdy(d):                           # bias diagnosis on the headline datasets (pinned headline configuration)
        v = d.get("variants", {})
        h, h42 = d["headline_seed123"], d["headline_seed42"]
        m["BDYHeadBias"], m["BDYHeadBiasSE"], m["BDYHeadRatio"] = _f(h["bias_pct"], 2), _f(h["bias_se_pct"], 2), _f(h["rmse_over_crb"])
        m["BDYSFBias"], m["BDYSFRatio"] = _f(h42["bias_pct"], 2), _f(h42["rmse_over_crb"])
        if "snr60" in v:
            m["BDYSixtyMax"] = _f(v["snr60"]["max_abs_diff_vs_headline_pp"], 3)
        if "kb30" in v:
            m["BDYKbMean"], m["BDYKbMax"] = _f(v["kb30"]["mean_diff_vs_headline_pp"], 2), _f(v["kb30"]["max_abs_diff_vs_headline_pp"], 2)
            m["BDYKbLower"] = str(v["kb30"]["n_lower_than_headline"])
        if "K4" in v:
            m["BDYKFourRatio"], m["BDYKFourBias"] = _f(v["K4"]["rmse_over_crb"]), _f(v["K4"]["bias_pct"], 2)
        if "K1" in v:
            m["BDYKOneRatio"], m["BDYKOneCov"] = _f(v["K1"]["rmse_over_crb"]), _f(v["K1"]["coverage90_wald"])
        rs = d.get("robust_se_40db")
        if rs:
            m["RSEYN"] = str(rs["n"])
            m["RSEYModelSE"], m["RSEYModelCov"] = _f(rs["model"]["se_median_pct"], 3), _f(rs["model"]["coverage90"])
            m["RSEYBlockSE"], m["RSEYBlockCov"] = _f(rs["block61"]["se_median_pct"], 3), _f(rs["block61"]["coverage90"])
        rg = d.get("regression")
        if rg:
            m["BRegYN"], m["BRegYRsq"], m["BRegYP"] = str(rg["n"]), _f(rg["r2"]), _f(rg["p_F"])
        if "exact" in v:
            e = v["exact"]
            m["ScoreExactMaxDiff"], m["ScoreExactMeanDiff"] = _f(e["max_abs_diff_vs_headline_pp"], 3), _f(e["mean_diff_vs_headline_pp"], 3)
            m["ScoreExactSERatio"] = _f(e["se_ratio_vs_headline_mean"], 3)
    block("p4/bias_diag_y25.json", bdy, ["ScoreExactMaxDiff", "ScoreExactMeanDiff", "ScoreExactSERatio"])
    for k in ("ScoreExactMaxDiff", "ScoreExactMeanDiff", "ScoreExactSERatio"):
        if k not in m:
            m[k] = miss("p4/bias_diag_y25.json (exact variant)")

    def conservative(v):                  # detection limits allowing for simultaneous model errors
        bd = load("p4/banded.json")
        kc = load("p3/validation_mc.json")["kappa_coest"]                           # attribution: kappa replicates
        # pre-registered rule (docs/paper1_outline.md): max(finite-SE inflation, inflation over all replicates with
        # the c_B-fixed sensitivity SEs); the finite-SE value alone when the sensitivity SEs are missing
        r = kc.get("inflation_conservative", kc["inflation_for_90pct"])
        m["KapInflNinety"] = _f(r)
        m["KapInflIncludesSing"] = "1" if kc.get("inflation_conservative_includes_singular") else "0"
        for b, w in (("empty", "Empty"), ("laden", "Laden")):
            for N, n in ((50, "Fifty"), (200, "TwoHundred")):
                v = [r * x["mdc_pct"] for x in bd["bounds"] if x["band"] == b and x["N"] == N]
                m[f"Band{w}MDC{n}ConsMin"], m[f"Band{w}MDC{n}ConsMax"] = _f(min(v)), _f(max(v))
    if load("p4/banded.json") and (load("p3/validation_mc.json") or {}).get("kappa_coest", {}).get("inflation_for_90pct"):
        conservative(None)

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
        if "fd" in d:
            m["ICFDN"], m["ICFDBias"], m["ICFDcBBias"] = str(d["fd"]["n"]), _f(d["fd"]["bias_pct"]), _f(d["fd"]["cB_bias_pct"], 1)
        for mode, w in (("nl", "NL"), ("lin", "Lin")):
            if mode in d:
                m[f"IC{w}cBBias"] = _f(d[mode]["cB_bias_pct"], 1)
        if "lin_minus_fd" in d:
            x = d["lin_minus_fd"]
            m["GenN"], m["GenkB"], m["GenkBSE"] = str(x["n"]), _f(x["kB0_mean_pp"]), _f(x["kB0_se_pp"])
            m["GencB"], m["GencBSE"] = _f(x["cB_mean_pp"], 0), _f(x["cB_se_pp"], 0)
        if "lin_pad1.6_minus_fd" in d:
            x = d["lin_pad1.6_minus_fd"]
            m["GenPadN"], m["GenPadkB"], m["GenPadkBSE"] = str(x["n"]), _f(x["kB0_mean_pp"]), _f(x["kB0_se_pp"])
            m["GenPadcB"], m["GenPadcBSE"] = _f(x["cB_mean_pp"], 0), _f(x["cB_se_pp"], 0)
        gc = load("p4/generator_check.json")
        if gc:
            m["GenBuildupMs"] = _f(1000 / (gc["support_mode_eig_zeta"] * 2 * math.pi * gc["support_mode_eig_hz"]), 0)
            m["GenOpMisfitPct"] = _f(100 * gc["operator_max_rel_misfit_single_wheel"], 1)
            m["GenRecMisfitPct"] = _f(100 * gc["rel_L2_misfit_record"], 2)
            m["GenZetaHP"] = _f(gc["support_zeta_halfpower_td"], 3)
        ge = load("p4/generator_expper.json")
        if ge:
            r = next(x for x in ge["rows"] if x["band_hz"] == [480, 550])
            m["GenPgramN"] = str(ge["realisations"])
            m["GenPgramDiff"], m["GenPgramDiffSE"] = _f(abs(100 * r["mean_log_ratio_td_fd"]), 1), _f(100 * r["log_ratio_se"], 1)
        if "pairs" in d:
            x = d["pairs"]
            m["ICPairsN"], m["ICPairsFA"], m["ICPairsFACal"] = str(x["n"]), str(x["false_alarms_raw"]), str(x["false_alarms_calibrated"])
            m["ICPairsFACalLo"], m["ICPairsFACalHi"] = _f(x["rate_calibrated_ci95"][0]), _f(x["rate_calibrated_ci95"][1])
    block("p4/inverse_crime.json", icrime, ["ICNLN", "ICNLBias", "ICNLRMSE", "ICNLCovCal", "ICDiffMean", "ICPairsN", "ICPairsFACal"])


if __name__ == "__main__":
    main()
